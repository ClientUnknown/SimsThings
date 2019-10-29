import collectionsimport refrom balloon.tunable_balloon import TunableBalloonfrom event_testing.resolver import SingleSimResolver, AffordanceResolverfrom interactions import ParticipantTypefrom interactions.context import InteractionContextfrom interactions.utils.tunable import TunableAffordanceLinkListfrom sims4.collections import frozendictfrom sims4.sim_irq_service import yield_to_irqfrom sims4.tuning.geometric import TunableCurvefrom sims4.tuning.tunable import TunableRange, HasTunableFactory, TunableList, TunableMapping, TunableTuple, OptionalTunable, TunableEnumEntry, TunableIntervalfrom singletons import DEFAULTfrom snippets import TunableAffordanceListReferencefrom statistics.statistic import Statisticimport gsi_handlers.content_set_handlersimport posturesimport sims4.logimport sims4.reloadlogger = sims4.log.Logger('Content Sets')with sims4.reload.protected(globals()):
    _mixer_name_list = []CONTENT_SET_GENERATION_CACHE_GROUP = 'CSG'MINIMUM_TARGETS_TO_TEST_AFFORDANCE_EARLY = 2
class ContentSet(HasTunableFactory):

    @staticmethod
    def _verify_tunable_callback(source, *_, affordance_lists, phase_affordances, **__):
        for affordance_list in affordance_lists:
            for affordance in affordance_list:
                if affordance.is_super:
                    logger.error('Content set from {} contains a super affordance: {} has {}', source, affordance_list, affordance)
        for value_type in phase_affordances.values():
            for affordances in value_type:
                for affordance_list in affordances.affordance_lists:
                    for affordance in affordance_list:
                        if affordance.is_super:
                            logger.error('Content set from {} contains a super affordance: {} has {}', source, affordance_list, affordance)

    FACTORY_TUNABLES = {'description': ' \n           This is where you tune any sub actions of this interaction.\n           \n           The interactions here can be tuned as reference to individual\n           affordances, lists of affordances, or phase affordances.\n           \n           Sub actions are affordances that can be run anytime this \n           interaction is active. Autonomy will choose which interaction\n           runs.\n           \n           Using phase affordances you can also tune Quick Time or \n           optional affordances that can appear.\n           ', 'affordance_links': TunableAffordanceLinkList(class_restrictions=('MixerInteraction',)), 'affordance_lists': TunableList(TunableAffordanceListReference(pack_safe=True)), 'phase_affordances': TunableMapping(description='\n            A mapping of phase names to affordance links and affordance lists. \n                      \n            This is also where you can specify an affordance is Quick Time (or\n            an optional affordance) and how many steps are required before an\n            option affordance is made available.\n            ', value_type=TunableList(TunableTuple(affordance_links=TunableAffordanceLinkList(class_restrictions=('MixerInteraction',)), affordance_lists=TunableList(TunableAffordanceListReference(pack_safe=True))))), 'phase_tuning': OptionalTunable(TunableTuple(description='\n            When enabled, statistic will be added to target and is used to\n            determine the phase index to determine which affordance group to use\n            in the phase affordance.\n            ', turn_statistic=Statistic.TunableReference(description='\n                The statistic used to track turns during interaction.\n                Value will be reset to 0 at the start of each phase.\n                '), target=TunableEnumEntry(description='\n                The participant the affordance will target.\n                ', tunable_type=ParticipantType, default=ParticipantType.Actor))), 'verify_tunable_callback': _verify_tunable_callback}
    EMPTY_LINKS = None

    def __init__(self, affordance_links, affordance_lists, phase_affordances, phase_tuning):
        self._affordance_links = affordance_links
        self._affordance_lists = affordance_lists
        self.phase_tuning = phase_tuning
        self._phase_affordance_links = []
        for key in sorted(phase_affordances.keys()):
            self._phase_affordance_links.append(phase_affordances[key])
        self._mixer_interaction_groups = set()
        for affordance in self.all_affordances_gen():
            self._mixer_interaction_groups.add(affordance.sub_action.mixer_group)

    def get_mixer_interaction_groups(self):
        return self._mixer_interaction_groups

    def _get_all_affordance_for_phase_gen(self, phase_affordances):
        for affordance in phase_affordances.affordance_links:
            yield affordance
        for affordance_list in phase_affordances.affordance_lists:
            for affordance in affordance_list:
                yield affordance

    def all_affordances_gen(self, phase_index=None):
        if phase_index is not None and self._phase_affordance_links:
            phase_index = min(phase_index, len(self._phase_affordance_links) - 1)
            phase = self._phase_affordance_links[phase_index]
            for phase_affordances in phase:
                for affordance in self._get_all_affordance_for_phase_gen(phase_affordances):
                    yield affordance
        else:
            for phase in self._phase_affordance_links:
                for phase_affordances in phase:
                    for affordance in self._get_all_affordance_for_phase_gen(phase_affordances):
                        yield affordance
            for link in self._affordance_links:
                yield link
            for l in self._affordance_lists:
                for link in l:
                    yield link

    @property
    def num_phases(self):
        return len(self._phase_affordance_links)

    def has_affordances(self):
        return bool(self._affordance_links) or (bool(self._affordance_lists) or bool(self._phase_affordance_links))
ContentSet.EMPTY_LINKS = ContentSet((), (), {}, None)
class ContentSetWithOverrides(ContentSet):
    FACTORY_TUNABLES = {'balloon_overrides': OptionalTunable(TunableList(description='\n            Balloon Overrides lets you override the mixer balloons.\n            EX: Each of the comedy routine performances have a set of balloons.\n            However, the animation/mixer content is the same. We want to play\n            the same mixer content, but just have the balloons be different.\n            ', tunable=TunableBalloon())), 'additional_mixers_to_cache': TunableInterval(description="\n            Additional number of mixers to cache during a subaction request. For\n            mixer autonomy, we cache mixer for performance reasons. The baseline\n            cache size is determined by the mixer_interaction_cache_size tunable\n            on the Sim's autonomy component.\n            \n            An example for reason to add more mixers to cache if there are\n            large number of mixers tuned in this content set such as socials,\n            you may need to increase this number.  \n            \n            Please talk to GPE if you are about to add additional mixers.\n            ", tunable_type=int, minimum=0, default_lower=0, default_upper=0)}

    def __init__(self, balloon_overrides, additional_mixers_to_cache, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.balloon_overrides = balloon_overrides
        self.additional_mixers_to_cache = additional_mixers_to_cache

class ContentSetTuning:
    POSTURE_PENALTY_MULTIPLIER = TunableRange(description='\n        Multiplier applied to content score if sim will be removed from posture.\n        ', tunable_type=float, default=0.5, maximum=1)

def _verify_tunable_callback(instance_class, tunable_name, source, value):
    for point in value.points:
        y_val = point[1]
        if not y_val < 0:
            if y_val > 1:
                logger.error("Invalid number '{0}' found in {1} in content set tuning. All {1} Y values must be in the range [0 - 1].", y_val, tunable_name)
        logger.error("Invalid number '{0}' found in {1} in content set tuning. All {1} Y values must be in the range [0 - 1].", y_val, tunable_name)

class SuccessChanceTuning:
    SCORE_CURVE = TunableCurve(verify_tunable_callback=_verify_tunable_callback, description='A curve of score (X value) to percent chance of success (Y value). Percent chance should be in the range 0-1, while score is unbounded and may be negative.')

def aop_valid_for_scoring(aop, affordance, target, context, include_failed_aops_with_tooltip, considered=None):
    test_result = aop.test(context, skip_safe_tests=False)
    if considered is not None:
        considered[aop] = {'affordance': str(affordance), 'target': str(target), 'test': str(test_result)}
    if test_result:
        return test_result
    elif include_failed_aops_with_tooltip and test_result.tooltip is not None:
        return test_result

def get_valid_aops_gen(target, affordance, si_affordance, si, context, include_failed_aops_with_tooltip, push_super_on_prepare=False, considered=None, aop_kwargs=frozendict()):
    potential_interactions = affordance.potential_interactions(target, si_affordance, si, push_super_on_prepare=push_super_on_prepare, **aop_kwargs)
    for aop in potential_interactions:
        test_result = aop_valid_for_scoring(aop, affordance, target, context, include_failed_aops_with_tooltip, considered=considered)
        if test_result is not None:
            yield (aop, test_result)

def any_content_set_available(sim, super_affordance, super_interaction, context, potential_targets=(), include_failed_aops_with_tooltip=False):
    si_or_sa = super_interaction if super_interaction is not None else super_affordance
    if not si_or_sa.has_affordances():
        return False
    with sims4.callback_utils.invoke_enter_exit_callbacks(sims4.callback_utils.CallbackEvent.CONTENT_SET_GENERATE_ENTER, sims4.callback_utils.CallbackEvent.CONTENT_SET_GENERATE_EXIT):
        for_pie_menu = context.source == InteractionContext.SOURCE_PIE_MENU
        for affordance in si_or_sa.all_affordances_gen(context=context):
            if affordance.is_super:
                logger.error('Content set contains a super affordance: {} has {}', si_or_sa, affordance, owner='msantander')
            if for_pie_menu and not affordance.allow_user_directed:
                pass
            else:
                targets = _test_affordance_and_get_targets(affordance, super_interaction, potential_targets, sim)
                if targets is None:
                    pass
                else:
                    for target in targets:
                        for (_, test_result) in get_valid_aops_gen(target, affordance, super_affordance, super_interaction, context, include_failed_aops_with_tooltip):
                            if test_result:
                                return True
    return False

def generate_content_set(sim, super_affordance, super_interaction, context, potential_targets=(), scoring_gsi_handler=None, include_failed_aops_with_tooltip=False, push_super_on_prepare=False, mixer_interaction_group=DEFAULT, check_posture_compatibility=False, aop_kwargs=frozendict()):
    si_or_sa = super_interaction if super_interaction is not None else super_affordance
    if not si_or_sa.has_affordances():
        return ()
    else:
        yield_to_irq()
        phase_index = None
        if not _mixer_name_list:
            phase_index = super_interaction.phase_index
        valid = collections.defaultdict(list)
        if super_interaction and gsi_handlers.content_set_handlers.archiver.enabled:
            gsi_considered = {}
        else:
            gsi_considered = None
        if check_posture_compatibility and sim is not None and sim.posture.posture_type != postures.stand.StandSuperInteraction.STAND_POSTURE_TYPE:
            show_posture_incompatible_icon = True
        else:
            show_posture_incompatible_icon = False
        if si_or_sa.is_social and potential_targets:
            for_pie_menu = context.source == InteractionContext.SOURCE_PIE_MENU
            with sims4.callback_utils.invoke_enter_exit_callbacks(sims4.callback_utils.CallbackEvent.CONTENT_SET_GENERATE_ENTER, sims4.callback_utils.CallbackEvent.CONTENT_SET_GENERATE_EXIT):
                target_to_posture_icon_info = {}
                for affordance in si_or_sa.all_affordances_gen(context=context, phase_index=phase_index):
                    if affordance.is_super:
                        logger.error('Content set contains a super affordance: {} has {}', si_or_sa, affordance)
                    if for_pie_menu and not affordance.allow_user_directed:
                        if gsi_considered is not None:
                            gsi_considered[affordance] = {'affordance': str(affordance), 'target': 'Skipped look up', 'test': 'Not allowed user directed'}
                            if mixer_interaction_group is not DEFAULT and affordance.sub_action.mixer_group != mixer_interaction_group:
                                pass
                            else:
                                targets = _test_affordance_and_get_targets(affordance, super_interaction, potential_targets, sim, considered=gsi_considered)
                                if targets is None:
                                    pass
                                elif include_failed_aops_with_tooltip or len(targets) >= MINIMUM_TARGETS_TO_TEST_AFFORDANCE_EARLY:
                                    resolver = AffordanceResolver(affordance, sim)
                                    if affordance.test_globals.run_tests(resolver, skip_safe_tests=False, search_for_tooltip=False):
                                        if not affordance.tests.run_tests(resolver, skip_safe_tests=False, search_for_tooltip=False):
                                            pass
                                        elif context.source == InteractionContext.SOURCE_AUTONOMY and not affordance.test_autonomous.run_tests(resolver, skip_safe_tests=False, search_for_tooltip=False):
                                            pass
                                        else:
                                            for target in targets:
                                                valid_aops_gen = get_valid_aops_gen(target, affordance, super_affordance, super_interaction, context, include_failed_aops_with_tooltip, push_super_on_prepare=push_super_on_prepare, considered=gsi_considered, aop_kwargs=aop_kwargs)
                                                for (aop, test_result) in valid_aops_gen:
                                                    if not aop.affordance.is_super:
                                                        aop_show_posture_incompatible_icon = False
                                                        if show_posture_incompatible_icon:
                                                            aop_show_posture_incompatible_icon = show_posture_incompatible_icon
                                                            if target not in target_to_posture_icon_info:
                                                                if aop.compatible_with_current_posture_state(sim):
                                                                    aop_show_posture_incompatible_icon = False
                                                                target_to_posture_icon_info[target] = aop_show_posture_incompatible_icon
                                                            else:
                                                                aop_show_posture_incompatible_icon = target_to_posture_icon_info[target]
                                                        aop.show_posture_incompatible_icon = aop_show_posture_incompatible_icon
                                                        mixer_weight = aop.affordance.calculate_autonomy_weight(sim)
                                                    else:
                                                        mixer_weight = 0
                                                    valid[affordance].append((mixer_weight, aop, test_result))
                                else:
                                    for target in targets:
                                        valid_aops_gen = get_valid_aops_gen(target, affordance, super_affordance, super_interaction, context, include_failed_aops_with_tooltip, push_super_on_prepare=push_super_on_prepare, considered=gsi_considered, aop_kwargs=aop_kwargs)
                                        for (aop, test_result) in valid_aops_gen:
                                            if not aop.affordance.is_super:
                                                aop_show_posture_incompatible_icon = False
                                                if show_posture_incompatible_icon:
                                                    aop_show_posture_incompatible_icon = show_posture_incompatible_icon
                                                    if target not in target_to_posture_icon_info:
                                                        if aop.compatible_with_current_posture_state(sim):
                                                            aop_show_posture_incompatible_icon = False
                                                        target_to_posture_icon_info[target] = aop_show_posture_incompatible_icon
                                                    else:
                                                        aop_show_posture_incompatible_icon = target_to_posture_icon_info[target]
                                                aop.show_posture_incompatible_icon = aop_show_posture_incompatible_icon
                                                mixer_weight = aop.affordance.calculate_autonomy_weight(sim)
                                            else:
                                                mixer_weight = 0
                                            valid[affordance].append((mixer_weight, aop, test_result))
                    elif mixer_interaction_group is not DEFAULT and affordance.sub_action.mixer_group != mixer_interaction_group:
                        pass
                    else:
                        targets = _test_affordance_and_get_targets(affordance, super_interaction, potential_targets, sim, considered=gsi_considered)
                        if targets is None:
                            pass
                        elif include_failed_aops_with_tooltip or len(targets) >= MINIMUM_TARGETS_TO_TEST_AFFORDANCE_EARLY:
                            resolver = AffordanceResolver(affordance, sim)
                            if affordance.test_globals.run_tests(resolver, skip_safe_tests=False, search_for_tooltip=False):
                                if not affordance.tests.run_tests(resolver, skip_safe_tests=False, search_for_tooltip=False):
                                    pass
                                elif context.source == InteractionContext.SOURCE_AUTONOMY and not affordance.test_autonomous.run_tests(resolver, skip_safe_tests=False, search_for_tooltip=False):
                                    pass
                                else:
                                    for target in targets:
                                        valid_aops_gen = get_valid_aops_gen(target, affordance, super_affordance, super_interaction, context, include_failed_aops_with_tooltip, push_super_on_prepare=push_super_on_prepare, considered=gsi_considered, aop_kwargs=aop_kwargs)
                                        for (aop, test_result) in valid_aops_gen:
                                            if not aop.affordance.is_super:
                                                aop_show_posture_incompatible_icon = False
                                                if show_posture_incompatible_icon:
                                                    aop_show_posture_incompatible_icon = show_posture_incompatible_icon
                                                    if target not in target_to_posture_icon_info:
                                                        if aop.compatible_with_current_posture_state(sim):
                                                            aop_show_posture_incompatible_icon = False
                                                        target_to_posture_icon_info[target] = aop_show_posture_incompatible_icon
                                                    else:
                                                        aop_show_posture_incompatible_icon = target_to_posture_icon_info[target]
                                                aop.show_posture_incompatible_icon = aop_show_posture_incompatible_icon
                                                mixer_weight = aop.affordance.calculate_autonomy_weight(sim)
                                            else:
                                                mixer_weight = 0
                                            valid[affordance].append((mixer_weight, aop, test_result))
                        else:
                            for target in targets:
                                valid_aops_gen = get_valid_aops_gen(target, affordance, super_affordance, super_interaction, context, include_failed_aops_with_tooltip, push_super_on_prepare=push_super_on_prepare, considered=gsi_considered, aop_kwargs=aop_kwargs)
                                for (aop, test_result) in valid_aops_gen:
                                    if not aop.affordance.is_super:
                                        aop_show_posture_incompatible_icon = False
                                        if show_posture_incompatible_icon:
                                            aop_show_posture_incompatible_icon = show_posture_incompatible_icon
                                            if target not in target_to_posture_icon_info:
                                                if aop.compatible_with_current_posture_state(sim):
                                                    aop_show_posture_incompatible_icon = False
                                                target_to_posture_icon_info[target] = aop_show_posture_incompatible_icon
                                            else:
                                                aop_show_posture_incompatible_icon = target_to_posture_icon_info[target]
                                        aop.show_posture_incompatible_icon = aop_show_posture_incompatible_icon
                                        mixer_weight = aop.affordance.calculate_autonomy_weight(sim)
                                    else:
                                        mixer_weight = 0
                                    valid[affordance].append((mixer_weight, aop, test_result))
        if valid:
            return list(_select_affordances_gen(sim, super_interaction, valid, show_posture_incompatible_icon, gsi_considered, scoring_gsi_handler, **aop_kwargs))
    return ()

def get_buff_aops(sim, buff, super_interaction, context, potential_targets=(), gsi_considered=None):
    if buff.interactions is None:
        return
    actual_potential_targets = potential_targets
    if not potential_targets:
        actual_potential_targets = super_interaction.get_potential_mixer_targets()
    valid = {}
    for buff_affordance in buff.interactions.interaction_items:
        targets = _test_affordance_and_get_targets(buff_affordance, super_interaction, actual_potential_targets, sim, considered=gsi_considered)
        if targets is None:
            pass
        else:
            for target in targets:
                for (aop, test_result) in get_valid_aops_gen(target, buff_affordance, super_interaction.super_affordance, super_interaction, context, False, considered=gsi_considered):
                    interaction_constraint = aop.constraint_intersection(sim=sim, posture_state=None)
                    posture_constraint = sim.posture_state.posture_constraint_strict
                    constraint_intersection = interaction_constraint.intersect(posture_constraint)
                    if not constraint_intersection.valid:
                        pass
                    else:
                        si_weight = buff.interactions.weight
                        if buff_affordance not in valid:
                            valid[buff_affordance] = [(si_weight, aop, test_result)]
                        else:
                            valid[buff_affordance].append((si_weight, aop, test_result))
    return valid

def _test_affordance_and_get_targets(affordance, super_interaction, potential_targets, sim, considered=None):
    if _mixer_name_list and not any(name.match(affordance.__name__) for name in _mixer_name_list):
        return
    sim_specific_lockout = affordance.lock_out_time.target_based_lock_out if affordance.lock_out_time is not None else False
    if not sim_specific_lockout:
        if sim.is_sub_action_locked_out(affordance):
            if considered is not None:
                considered[affordance] = {'affordance': str(affordance), 'target': '', 'test': 'Locked out'}
            return
        return affordance.filter_mixer_targets(super_interaction, potential_targets, sim)
    targets = affordance.filter_mixer_targets(super_interaction, potential_targets, sim, affordance=affordance)
    if targets:
        return targets
    else:
        if considered is not None:
            target_strs = [str(x) for x in potential_targets]
            considered[affordance] = {'affordance': str(affordance), 'target': ', '.join(target_strs), 'test': 'Locked out'}
        return

def _select_affordances_gen(sim, super_interaction, valid, show_posture_incompatible_icon, gsi_considered, scoring_gsi_handler=None, **kwargs):
    gsi_results = {}
    scored = {}
    if gsi_handlers.content_set_handlers.archiver.enabled and super_interaction is not None:
        resolver = super_interaction.get_resolver()
    else:
        resolver = SingleSimResolver(sim)
    for (affordance, affordance_results) in valid.items():
        internal_aops = list(aop for (_, aop, _) in affordance_results)
        aop_score = affordance.get_content_score(sim, resolver, internal_aops, scoring_gsi_handler, **kwargs)
        scored[affordance] = aop_score
    for (affordance, score) in scored.items():
        score = scored[affordance]
        for (weight, aop, test_result) in valid[affordance]:
            aop.content_score = score
            gsi_considered[aop]['total_score'] = score
            gsi_considered[aop]['selected'] = True
            gsi_results[aop] = {'result_affordance': str(affordance), 'result_target': str(aop.target), 'result_loc_key': aop.affordance.display_name().hash, 'result_target_loc_key': aop.affordance.display_name_target().hash}
            yield (weight, aop, test_result)
    if gsi_handlers.content_set_handlers.archiver.enabled:
        gsi_handlers.content_set_handlers.archive_content_set(sim, super_interaction, gsi_considered, gsi_results, sim.get_topics_gen())

def lock_content_sets(mixer_name_list):
    global _mixer_name_list
    _mixer_name_list = []
    for name in mixer_name_list:
        name = name.replace('*', '.*')
        name += '$'
        _mixer_name_list.append(re.compile(name))
