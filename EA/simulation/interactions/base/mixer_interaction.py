import weakreffrom protocolbuffers import Sims_pb2 as protocolsfrom animation import posture_manifestfrom element_utils import build_critical_section_with_finallyfrom event_testing.results import TestResultfrom interactions import ParticipantTypefrom interactions.aop import AffordanceObjectPairfrom interactions.base.interaction import Interaction, TargetTypefrom interactions.base.interaction_constants import InteractionQueuePreparationStatusfrom interactions.constraints import RequiredSlotSinglefrom interactions.context import InteractionContext, QueueInsertStrategyfrom interactions.interaction_finisher import FinishingTypefrom interactions.utils.interaction_liabilities import LockGuaranteedOnSIWhileRunning, LOCK_GUARANTEED_ON_SI_WHILE_RUNNINGfrom interactions.utils.outcome import TunableOutcomefrom sims4.geometry import ANIMATION_SLOT_EPSILONfrom sims4.localization import TunableLocalizedStringFactoryfrom sims4.tuning.instances import lock_instance_tunablesfrom sims4.tuning.tunable import Tunable, TunableTuple, TunableReference, OptionalTunable, TunableInterval, TunableSimMinute, TunableList, TunableRange, TunableEnumEntryfrom sims4.tuning.tunable_base import GroupNamesfrom sims4.utils import flexmethod, classproperty, flexpropertyfrom singletons import DEFAULT, EMPTY_SETimport gsi_handlers.interaction_archive_handlersimport gsi_handlers.sim_timeline_handlersimport interactions.constraintsimport performance.countersimport servicesimport sims4.logimport sims4.resourceslogger = sims4.log.Logger('MixerInteraction')
class MixerInteraction(Interaction):
    INSTANCE_TUNABLES = {'display_name_target': TunableLocalizedStringFactory(description="\n                Display text of target of mixer interaction. Example: Sim A\n                queues 'Tell Joke', Sim B will see in their queue 'Be Told\n                Joke'\n                ", allow_none=True, tuning_group=GroupNames.UI), 'sub_action': TunableTuple(description="\n                Sub-Action scoring: base_weight is the base autonomy weight for\n                mixer interaction.\n                \n                If mixer is NOT from social super interaction, following formula is applied:\n                Formula: autonomy weight = base_weight * StaticCommodity.desires multiplied together\n                    autonomy_weight = cls.sub_action.base_weight\n                    for static_commodity_data in cls.static_commodities_data:\n                        if sim.get_stat_instance(static_commodity_data.static_commodity):\n                    autonomy_weight *= static_commodity_data.desire\n                \n                If mixer is from a social super interaction, following formula\n                is applied to get the autonomy weight.\n                Formula: autonomy weight = autonomy_weight(from above) * SubactionAutonomyContentScoreUtilityCurve(front_page_score).y\n                \n                SubactionAutonomyContentScoreUtilityCurve maps from\n                front_page_score to a score between 0-100\n                \n                if test_gender_preference and fails,\n                   front_page_base_score = SocialMixerInteraction.GENDER_PREF_CONTENT_SCORE_PENALTY\n                otherwise:\n                   fornt_page_base_score = (socialmixerinteraction.base_score) +\n                                   shot term preference score that satisify group +\n                                   mood preference score that can apply to sim + \n                                   sum of buff preference that can apply to sim +\n                                   sum of trait preference that can apply to sim +\n                                   sum of relationship bit preference that apply to sim +\n                \n                front_page_score = fornt_page_base_score + \n                                   sum of topic preference that can apply to sim to target +\n                                   sum of sim's buffs game modifier that can apply to mixer affordance + \n                                   sum of club front page bonus for mixer that can apply for sim and mixer affordance + \n                                   front page cooldown score if tuned and can be applied\n\n                If super interaction from mixer will cause sim to change posture following multiplier is applied\n                front_page_score = front_page_socre * ContentSetTuning.POSTURE_PENALTY_MULTIPLIER.\n                ", base_weight=TunableRange(description='\n                    The base weight of the subaction.\n                    ', tunable_type=int, minimum=0, default=1), mixer_group=TunableEnumEntry(description='\n                    The group this mixer belongs to.  This will directly affect\n                    the scoring of subaction autonomy.  When subaction autonomy\n                    runs and chooses the mixer provider for the sim to express,\n                    the sim will gather all mixers for that provider.  She will\n                    then choose one of the categories based on a weighted\n                    random, then score the mixers only in that group.  The\n                    weights are tuned in autonomy_modes with the\n                    SUBACTION_GROUP_WEIGHTING tunable mapping.\n                    \n                    Example: Say you have two groups: DEFAULT and IDLES.  You\n                    could set up the SUBACTION_GROUP_WEIGHTING mapping such\n                    that DEFAULT has a weight of 3 and IDLES has a weight of 7.\n                    When a sim needs to decide which set of mixers to pull\n                    from, 70% of the time she will choose mixers tagged with\n                    IDLES and 30% of the time she will choose mixers tagged\n                    with DEFAULT.\n                    ', tunable_type=interactions.MixerInteractionGroup, needs_tuning=True, default=interactions.MixerInteractionGroup.DEFAULT), tuning_group=GroupNames.AUTONOMY), 'optional': Tunable(description="\n                Most mixers are expected to always be valid.  Thus this should\n                be False. When setting to True, we will test this mixer for\n                compatibility with the current SIs the sim is in. This can be\n                used to ensure general tuning for things like socials can all\n                always be there, but a couple socials that won't work with the\n                treadmill will be tested out such that the player cannot choose\n                them.\n                ", tunable_type=bool, default=False, tuning_group=GroupNames.MIXER), 'lock_out_time': OptionalTunable(description='\n                Enable to prevent this mixer from being run repeatedly.\n                ', tunable=TunableTuple(interval=TunableInterval(description='\n                        Time in sim minutes in which this affordance will not\n                        be valid for.\n                        ', tunable_type=TunableSimMinute, default_lower=1, default_upper=1, minimum=0), target_based_lock_out=Tunable(bool, False, description='\n                        If True, this lock out time will be enabled on a per\n                        Sim basis. i.e. locking it out on Sim A will leave it\n                        available to Sim B.\n                        ')), tuning_group=GroupNames.MIXER), 'lock_out_time_initial': OptionalTunable(description='\n                Enable to prevent this mixer from being run immediately.\n                ', tunable=TunableInterval(description='\n                    Time in sim minutes to delay before running this mixer for\n                    the first time.\n                    ', tunable_type=TunableSimMinute, default_lower=1, default_upper=1, minimum=0), tuning_group=GroupNames.MIXER), 'lock_out_affordances': OptionalTunable(TunableList(description='\n                Additional affordances that will be locked out if lock out time\n                has been set.\n                ', tunable=TunableReference(manager=services.get_instance_manager(sims4.resources.Types.INTERACTION), class_restrictions=('MixerInteraction',))), tuning_group=GroupNames.MIXER), '_interruptible': OptionalTunable(description='\n                If disabled, this Mixer Interaction will be interruptible if\n                the content is looping, and not if the content is one shot.  To\n                override this behavior, enable this tunable and set the bool.\n                ', tunable=Tunable(description='\n                    This interaction represents idle-style behavior and can\n                    immediately be interrupted by more important interactions.\n                    Set this to True for passive, invisible mixer interactions\n                    like stand_Passive.\n                    ', tunable_type=bool, default=False), tuning_group=GroupNames.MIXER), 'skip_safe_tests_on_execute': Tunable(description='\n            Most mixers should skip safe tests on execute, and this should be\n            set to True. When set to False, we will reevaluate the result of\n            safe to skip tests when executing this mixer. This should be used\n            when mixers can be queued at the same time, but running one mixer\n            changes the result of a test of the following mixer such that it\n            is no longer valid to run.\n            ', tunable_type=bool, default=True, tuning_group=GroupNames.MIXER), 'outcome': TunableOutcome(tuning_group=GroupNames.CORE)}

    def __init__(self, target, context, *args, push_super_on_prepare=False, **kwargs):
        super().__init__(target, context, *args, **kwargs)
        self._target_sim_refs_to_remove_interaction = None
        self._push_super_on_prepare = push_super_on_prepare
        self.duration = None
        self.push_super_affordance_target = None

    def get_animation_context_liability(self):
        if self.super_interaction is not None:
            animation_liability = self.super_interaction.get_animation_context_liability()
            return animation_liability
        raise RuntimeError('Mixer Interaction {} has no associated Super Interaction. [tastle]'.format(self))

    @property
    def animation_context(self):
        animation_liability = self.get_animation_context_liability()
        return animation_liability.animation_context

    def register_additional_event_handlers(self, animation_context):
        if self.super_interaction is not None:
            self.super_interaction.register_additional_event_handlers(animation_context)
        else:
            raise RuntimeError('Mixer Interaction {} has no associated Super Interaction. [tastle]'.format(self))

    def store_event_handler(self, callback, handler_id=None):
        if self.super_interaction is not None:
            self.super_interaction.store_event_handler(callback, handler_id=handler_id)
        else:
            raise RuntimeError('Mixer Interaction {} has no associated Super Interaction. [tastle]'.format(self))

    @property
    def carry_target(self):
        carry_target = super().carry_target
        if self.super_interaction is not None:
            carry_target = self.super_interaction.carry_target
        return carry_target

    @flexmethod
    def skip_test_on_execute(cls, inst):
        inst_or_cls = inst if inst is not None else cls
        return inst_or_cls.skip_safe_tests_on_execute

    @flexproperty
    def stat_from_skill_loot_data(cls, inst):
        if inst is None or cls.skill_loot_data.stat is not None:
            return cls.skill_loot_data.stat
        elif inst.super_interaction is not None:
            return inst.super_interaction.stat_from_skill_loot_data

    @flexproperty
    def skill_effectiveness_from_skill_loot_data(cls, inst):
        if inst is None or cls.skill_loot_data.effectiveness is not None:
            return cls.skill_loot_data.effectiveness
        elif inst.super_interaction is not None:
            return inst.super_interaction.skill_effectiveness_from_skill_loot_data

    @flexproperty
    def level_range_from_skill_loot_data(cls, inst):
        if inst is None or cls.skill_loot_data.level_range is not None:
            return cls.skill_loot_data.level_range
        elif inst.super_interaction is not None:
            return inst.super_interaction.level_range_from_skill_loot_data

    @classmethod
    def _test(cls, target, context, **kwargs):
        if cls.optional and not cls.is_mixer_compatible(context.sim, target, participant_type=ParticipantType.Actor):
            return TestResult(False, 'Optional MixerInteraction ({}) was not compatible with current posture ({})', cls, context.sim.posture_state)
        return super()._test(target, context, **kwargs)

    @classmethod
    def potential_interactions(cls, target, sa, si, **kwargs):
        yield AffordanceObjectPair(cls, target, sa, si, **kwargs)

    @classmethod
    def filter_mixer_targets(cls, super_interaction, potential_targets, actor, affordance=None):
        if cls.target_type & TargetType.ACTOR:
            targets = (None,)
        elif cls.target_type & TargetType.TARGET or cls.target_type & TargetType.OBJECT:
            targets = [x for x in potential_targets if x is not actor and (actor.is_sub_action_locked_out(affordance, target=x) or x.supports_affordance(cls))]
        elif cls.target_type & TargetType.GROUP:
            targets = [x for x in potential_targets if x and not x.is_sim]
            if not targets:
                targets = (None,)
        else:
            targets = (None,)
        return targets

    @classmethod
    def calculate_autonomy_weight(cls, sim):
        final_weight = cls.sub_action.base_weight
        for static_commodity_data in cls.static_commodities_data:
            if sim.get_stat_instance(static_commodity_data.static_commodity):
                final_weight *= static_commodity_data.desire
        return final_weight

    @classproperty
    def interruptible(cls):
        if cls._interruptible is not None:
            return cls._interruptible
        return False

    @classproperty
    def involves_carry(cls):
        return False

    @classmethod
    def get_mixer_key_override(cls, target):
        pass

    def should_cancel_on_si_cancel(self, interaction):
        if self.interruptible:
            return True
        elif self.super_interaction is interaction:
            return self.looping
        return False

    def should_insert_in_queue_on_append(self):
        if self.super_interaction is not None:
            return True
        return False

    def _must_push_super_interaction(self):
        if self._push_super_on_prepare and self.super_interaction is not None:
            return False
        for interaction in self.sim.running_interactions_gen(self.super_affordance):
            if interaction.is_finishing:
                pass
            else:
                if not self.target is interaction.target:
                    if self.target in interaction.get_potential_mixer_targets():
                        self.super_interaction = interaction
                        self.sim.ui_manager.set_interaction_super_interaction(self, self.super_interaction.id)
                        return False
                self.super_interaction = interaction
                self.sim.ui_manager.set_interaction_super_interaction(self, self.super_interaction.id)
                return False
        return True

    def notify_queue_head(self):
        if self.is_finishing:
            return
        super().notify_queue_head()
        if self._must_push_super_interaction():
            self._push_super_on_prepare = False
            context = InteractionContext(self.sim, self.source, self.priority, insert_strategy=QueueInsertStrategy.FIRST, bucket=self.context.bucket, preferred_objects=self.context.preferred_objects)
            interaction_parameters = dict()
            for interaction_parameter_key in ('picked_item_ids', 'associated_club'):
                if interaction_parameter_key in self.interaction_parameters:
                    interaction_parameters[interaction_parameter_key] = self.interaction_parameters[interaction_parameter_key]
            if self.is_social:
                picked_object = self.picked_object
            else:
                picked_object = None
            result = self.sim.push_super_affordance(self.super_affordance, self.target or self.push_super_affordance_target, context, picked_object=picked_object, **interaction_parameters)
            if result:
                self.super_interaction = result.interaction
                guaranteed_lock_liability = LockGuaranteedOnSIWhileRunning(self.super_interaction)
                self.add_liability(LOCK_GUARANTEED_ON_SI_WHILE_RUNNING, guaranteed_lock_liability)
                self.sim.ui_manager.set_interaction_super_interaction(self, self.super_interaction.id)
            else:
                self.cancel(FinishingType.KILLED, 'Failed to push the SI associated with this mixer!')

    def prepare_gen(self, timeline):
        if self.allow_with_unholsterable_carries or not self.cancel_incompatible_carry_interactions(can_defer_putdown=False):
            return InteractionQueuePreparationStatus.NEEDS_DERAIL
        return InteractionQueuePreparationStatus.SUCCESS

    def _get_required_sims(self, *args, **kwargs):
        sims = set()
        if self.target_type & TargetType.GROUP:
            sims.update(self.get_participants(ParticipantType.AllSims, listener_filtering_enabled=True))
        elif self.target_type & TargetType.TARGET:
            sims.update(self.get_participants(ParticipantType.Actor))
            sims.update(self.get_participants(ParticipantType.TargetSim))
        elif self.target_type & TargetType.ACTOR or self.target_type & TargetType.OBJECT:
            sims.update(self.get_participants(ParticipantType.Actor))
        return sims

    def get_asm(self, *args, **kwargs):
        if self.super_interaction is not None:
            return self.super_interaction.get_asm(*args, **kwargs)
        return super().get_asm(*args, **kwargs)

    def on_added_to_queue(self, *args, **kwargs):
        super().on_added_to_queue(*args, **kwargs)
        if self._aop:
            self._aop.lifetime_in_steps = 0

    def build_basic_elements(self, sequence=()):
        sequence = super().build_basic_elements(sequence=sequence)
        for sim in self.required_sims():
            for social_group in sim.get_groups_for_sim_gen():
                sequence = social_group.with_social_focus(self.sim, social_group._group_leader, (sim,), sequence)
        suspended_modifiers_dict = self._generate_suspended_modifiers_dict()
        if gsi_handlers.interaction_archive_handlers.is_archive_enabled(self):
            start_time = services.time_service().sim_now
        else:
            start_time = None

        def interaction_start(_):
            self._suspend_modifiers(suspended_modifiers_dict)
            self.apply_interaction_cost()
            performance.counters.add_counter('PerfNumSubInteractions', 1)
            self._add_interaction_to_targets()
            if gsi_handlers.interaction_archive_handlers.is_archive_enabled(self):
                gsi_handlers.interaction_archive_handlers.archive_interaction(self.sim, self, 'Start')

        def interaction_end(_):
            if start_time is not None:
                self.duration = (services.time_service().sim_now - start_time).in_minutes()
            self._remove_interaction_from_targets()
            self.sim.update_last_used_interaction(self)
            self._resume_modifiers(suspended_modifiers_dict)

        return build_critical_section_with_finally(interaction_start, sequence, interaction_end)

    def _generate_suspended_modifiers_dict(self):
        suspended_modifiers_dict = {}
        for sim in self.required_sims():
            for (handle, autonomy_modifier_entry) in sim.sim_info.get_statistic_modifiers_gen():
                autonomy_modifier = autonomy_modifier_entry.autonomy_modifier
                if autonomy_modifier.exclusive_si and autonomy_modifier.exclusive_si is not self.super_interaction:
                    if sim.sim_info not in suspended_modifiers_dict:
                        suspended_modifiers_dict[sim.sim_info] = []
                    suspended_modifiers_dict[sim.sim_info].append((autonomy_modifier.exclusive_si, handle))
        return suspended_modifiers_dict

    def _suspend_modifiers(self, modifiers_dict):
        for (sim_info, handle_list) in modifiers_dict.items():
            for (si, handle) in handle_list:
                (result, reason) = sim_info.suspend_statistic_modifier(handle)
                if result or reason is not None:
                    logger.error('Failed to suspend modifier of exclusive si: {}\n   On Sim: {}\n   Running: {}\n   Reason: {}', si, sim_info, self, reason, owner='msantander')

    def _resume_modifiers(self, modifiers_dict):
        for (sim_info, handle_list) in modifiers_dict.items():
            for (_, handle) in handle_list:
                sim_info.resume_statistic_modifier(handle)

    def apply_interaction_cost(self):
        pass

    def cancel(self, finishing_type, cancel_reason_msg, **kwargs):
        if hasattr(self.super_interaction, 'context_handle'):
            context_handle = self.super_interaction.context_handle
            ret = super().cancel(finishing_type, cancel_reason_msg, **kwargs)
            if ret:
                from server_commands import interaction_commands
                interaction_commands.send_reject_response(self.sim.client, self.sim, context_handle, protocols.ServerResponseFailed.REJECT_CLIENT_SELECT_MIXERINTERACTION)
            return ret
        return super().cancel(finishing_type, cancel_reason_msg, **kwargs)

    def cancel_parent_si_for_participant(self, participant_type, finishing_type, cancel_reason_msg, **kwargs):
        self.super_interaction.cancel(finishing_type, cancel_reason_msg, **kwargs)

    def apply_posture_state(self, *args, **kwargs):
        pass

    def _pre_perform(self):
        result = super()._pre_perform()
        if self.is_user_directed:
            self._update_autonomy_timer()
        return result

    @flexmethod
    def is_mixer_compatible(cls, inst, sim, target, error_on_fail=False, participant_type=DEFAULT):
        posture_state = sim.posture_state
        inst_or_cls = inst if inst is not None else cls
        si = inst.super_interaction if inst is not None else None
        mixer_constraint_tentative = inst_or_cls.constraint_intersection(sim=sim, target=target, posture_state=None, participant_type=participant_type)
        with posture_manifest.ignoring_carry():
            mixer_constraint = mixer_constraint_tentative.apply_posture_state(posture_state, inst_or_cls.get_constraint_resolver(posture_state, sim=sim, target=target))
            posture_state_constraint = posture_state.constraint_intersection
            no_geometry_posture_state = posture_state_constraint.generate_alternate_geometry_constraint(None)
            no_geometry_mixer_state = mixer_constraint.generate_alternate_geometry_constraint(None)
            test_intersection = no_geometry_posture_state.intersect(no_geometry_mixer_state)
            ret = test_intersection.valid
        if ret or error_on_fail and no_geometry_posture_state.valid:
            si_constraint_list = ''.join('\n        ' + str(c) for c in no_geometry_posture_state)
            mi_constraint_list = ''.join('\n        ' + str(c) for c in mixer_constraint_tentative)
            mx_constraint_list = ''.join('\n        ' + str(c) for c in no_geometry_mixer_state)
            to_constraint_list = ''.join('\n        ' + str(c) for c in test_intersection)
            logger.error("{} more restrictive than {}!\n                The mixer interaction's constraint is more restrictive than its\n                Super Interaction. Since this mixer is not tuned to be optional,\n                this is a tuning or animation error as the interaction's\n                animation may not play correctly or at all. \n                \n                If it is okay for this mixer to only be available part of the\n                time, set Optional to True.\n\n                SI constraints No Geometry: \t{} \n\n                Effective Mixer constraints No Geometry: \t{} \n\n                Original Mixer constraints: \t{} \n\n                Total constraints: \t{}\n                ", type(inst_or_cls).__name__, type(si).__name__, si_constraint_list, mx_constraint_list, mi_constraint_list, to_constraint_list, trigger_breakpoint=True)
        return ret

    def _validate_posture_state(self):
        for sim in self.required_sims():
            participant_type = self.get_participant_type(sim)
            if participant_type is None:
                pass
            else:
                constraint_tentative = self.constraint_intersection(sim=sim, participant_type=participant_type)
                resolver = self.get_constraint_resolver(sim.posture_state, participant_type=participant_type)
                constraint = constraint_tentative.apply_posture_state(sim.posture_state, resolver)
                sim_transform_constraint = interactions.constraints.Transform(sim.transform, routing_surface=sim.routing_surface)
                geometry_intersection = constraint.intersect(sim_transform_constraint)
                if not geometry_intersection.valid:
                    containment_transform = None
                    if isinstance(constraint, RequiredSlotSingle):
                        containment_transform = constraint.containment_transform.translation
                        if sims4.math.vector3_almost_equal_2d(sim.transform.translation, containment_transform, epsilon=ANIMATION_SLOT_EPSILON):
                            pass
                        else:
                            logger.error("Interaction Constraint Error: Interaction's constraint is incompatible with the Sim's current position \n                    Interaction: {}\n                    Sim: {}, \n                    Constraint: {}\n                    Sim Position: {}\n                    Interaction Target Position: {},\n                    Target Containment Transform: {}", self, sim, constraint, sim.position, self.target.position if self.target is not None else None, containment_transform, owner='MaxR', trigger_breakpoint=True)
                            return False
                    else:
                        logger.error("Interaction Constraint Error: Interaction's constraint is incompatible with the Sim's current position \n                    Interaction: {}\n                    Sim: {}, \n                    Constraint: {}\n                    Sim Position: {}\n                    Interaction Target Position: {},\n                    Target Containment Transform: {}", self, sim, constraint, sim.position, self.target.position if self.target is not None else None, containment_transform, owner='MaxR', trigger_breakpoint=True)
                        return False
        return True

    def pre_process_interaction(self):
        self.sim.ui_manager.transferred_to_si_state(self)

    def post_process_interaction(self):
        self.sim.ui_manager.remove_from_si_state(self)

    def perform_gen(self, timeline):
        with gsi_handlers.sim_timeline_handlers.archive_sim_timeline_context_manager(self.sim, 'Mixer', 'Perform', self):
            result = yield from super().perform_gen(timeline)
            return result

    def _add_interaction_to_targets(self):
        if not self.visible_as_interaction:
            return
        social_group = self.social_group
        if social_group is not None:
            icon_info = self.get_icon_info()
            if icon_info.icon_resource is None:
                if icon_info.obj_instance is not None:
                    icon_info._replace(obj_instance=self.sim)
                else:
                    icon_info.obj_instance = self.sim
            for target_sim in self.required_sims():
                if target_sim == self.sim:
                    pass
                else:
                    target_si = social_group.get_si_registered_for_sim(target_sim)
                    if target_si is None:
                        pass
                    else:
                        name = self.display_name_target(target_sim, self.sim)
                        target_sim.ui_manager.add_running_mixer_interaction(target_si.id, self, icon_info, name)
                        if gsi_handlers.interaction_archive_handlers.is_archive_enabled(self):
                            gsi_handlers.interaction_archive_handlers.archive_interaction(target_sim, self, 'Start')
                        if self._target_sim_refs_to_remove_interaction is None:
                            self._target_sim_refs_to_remove_interaction = weakref.WeakSet()
                        self._target_sim_refs_to_remove_interaction.add(target_sim)

    def _remove_interaction_from_targets(self):
        if self._target_sim_refs_to_remove_interaction:
            for target_sim in self._target_sim_refs_to_remove_interaction:
                target_sim.ui_manager.remove_from_si_state(self)
                if gsi_handlers.interaction_archive_handlers.is_archive_enabled(self):
                    gsi_handlers.interaction_archive_handlers.archive_interaction(target_sim, self, 'Complete')
lock_instance_tunables(MixerInteraction, basic_reserve_object=None, _false_advertisements=EMPTY_SET, _hidden_false_advertisements=EMPTY_SET, _require_current_posture=False, time_overhead=10)