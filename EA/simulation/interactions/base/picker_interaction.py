from _collections import defaultdictimport functoolsimport randomfrom event_testing.resolver import SingleObjectResolver, InteractionResolver, SingleSimResolver, DoubleSimAndObjectResolverfrom event_testing.tests import TunableTestSetfrom filters.tunable import TunableSimFilterfrom fishing.fishing_tuning import FishingTuningfrom interactions import ParticipantType, ParticipantTypeSinglefrom interactions.aop import AffordanceObjectPairfrom interactions.base.immediate_interaction import ImmediateSuperInteractionfrom interactions.base.picker_strategy import SimPickerEnumerationStrategy, LotPickerEnumerationStrategy, ObjectPickerEnumerationStrategyfrom interactions.base.super_interaction import SuperInteractionfrom interactions.context import InteractionContext, QueueInsertStrategy, InteractionSourcefrom interactions.picker.picker_pie_menu_interaction import _PickerPieMenuProxyInteractionfrom interactions.utils.localization_tokens import LocalizationTokensfrom interactions.utils.object_definition_or_tags import ObjectDefinitonsOrTagsVariantfrom interactions.utils.outcome import InteractionOutcomefrom interactions.utils.tunable import TunableContinuationfrom objects.auto_pick import AutoPick, AutoPickRandomfrom objects.components.inventory_enums import InventoryTypefrom objects.components.statistic_types import StatisticComponentGlobalTuningfrom objects.hovertip import TooltipFieldsfrom objects.object_tests import ObjectTypeFactory, ObjectTagFactory, ObjectCriteriaSingleObjectSpecificTest, ObjectCriteriaTestfrom objects.terrain import get_venue_instance_from_pick_locationfrom plex.plex_enums import PlexBuildingTypefrom sims4.localization import TunableLocalizedStringFactory, LocalizationHelperTuning, TunableLocalizedStringFactoryVariantfrom sims4.random import pop_weightedfrom sims4.tuning.instances import lock_instance_tunablesfrom sims4.tuning.tunable import TunableEnumEntry, OptionalTunable, TunableVariant, Tunable, TunableTuple, TunableReference, TunableSet, TunableList, TunableFactory, TunableThreshold, TunableMapping, TunableRange, HasTunableSingletonFactory, AutoFactoryInitfrom sims4.tuning.tunable_base import GroupNamesfrom sims4.tuning.tunable_hash import TunableStringHash32from sims4.utils import flexmethod, classpropertyfrom singletons import DEFAULTfrom snippets import TunableVenueListReferencefrom tunable_multiplier import TunableMultiplierfrom ui.ui_dialog import PhoneRingTypefrom ui.ui_dialog_notification import TunableUiDialogNotificationSnippetfrom ui.ui_dialog_picker import logger, TunablePickerDialogVariant, SimPickerRow, ObjectPickerRow, ObjectPickerTuningFlags, PurchasePickerRow, LotPickerRowfrom world import regionfrom world.world_tests import DistanceTestimport build_buyimport enumimport event_testing.resultsimport gsi_handlersimport servicesimport simsimport sims4.resourcesimport tag
class _TunablePieMenuOptionTuple(TunableTuple):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, show_disabled_item=Tunable(description='\n                If checked, the disabled item will show as disabled in the Pie\n                Menu with a greyed-out tooltip. Otherwise the disabled item will\n                not show up in the pie menu.\n                ', tunable_type=bool, default=False), pie_menu_category=TunableReference(description="\n                If set, then the generated Pie Menu interaction will be\n                categorized under this Pie Menu category, as opposed to using\n                the interaction's Pie Menu category.\n                ", manager=services.get_instance_manager(sims4.resources.Types.PIE_MENU_CATEGORY), allow_none=True, tuning_group=GroupNames.UI), pie_menu_name=TunableLocalizedStringFactory(description="\n                The localized name for the pie menu item. The content should\n                always have {2.String} to wrap picker row data's name.\n                "), **kwargs)

class PickerSuperInteractionMixin:
    INSTANCE_TUNABLES = {'picker_dialog': TunablePickerDialogVariant(description='\n            The object picker dialog.\n            ', tuning_group=GroupNames.PICKERTUNING), 'pie_menu_option': OptionalTunable(description='\n            Whether use Pie Menu to show choices other than picker dialog.\n            ', tunable=_TunablePieMenuOptionTuple(), disabled_name='use_picker', enabled_name='use_pie_menu', tuning_group=GroupNames.PICKERTUNING), 'pie_menu_test_tooltip': OptionalTunable(description='\n            If enabled, then a greyed-out tooltip will be displayed if there\n            are no valid choices. When disabled, the test to check for valid\n            choices will run first and if it fail any other tuned test in the\n            interaction will not get run. When enabled, the tooltip will be the\n            last fallback tooltip, and if other tuned interaction tests have\n            tooltip, those tooltip will show first. [cjiang/scottd]\n            ', tunable=TunableLocalizedStringFactory(description='\n                The tooltip text to show in the greyed-out tooltip when no valid\n                choices exist.\n                '), tuning_group=GroupNames.PICKERTUNING)}

    @classmethod
    def _test(cls, *args, **kwargs):
        result = super()._test(*args, **kwargs)
        if not result:
            return result
        if not cls.has_valid_choice(*args, **kwargs):
            disabled_tooltip = cls.get_disabled_tooltip(*args, **kwargs)
            return event_testing.results.TestResult(False, 'This picker SI has no valid choices.', tooltip=disabled_tooltip)
        return event_testing.results.TestResult.TRUE

    @flexmethod
    def _get_name(cls, inst, *args, **kwargs):
        inst_or_cls = inst if inst is not None else cls
        text = super(__class__, inst_or_cls)._get_name(*args, **kwargs)
        if inst_or_cls._use_ellipsized_name():
            text = LocalizationHelperTuning.get_ellipsized_text(text)
        return text

    @flexmethod
    def _use_ellipsized_name(cls, inst):
        return True

    @classmethod
    def has_valid_choice(cls, target, context, **kwargs):
        return True

    @classmethod
    def get_disabled_tooltip(cls, *args, **kwargs):
        return cls.pie_menu_test_tooltip

    @classmethod
    def use_pie_menu(cls):
        if cls.pie_menu_option is not None:
            return True
        return False

    def _show_picker_dialog(self, owner, **kwargs):
        if self.use_pie_menu():
            return
        dialog = self._create_dialog(owner, **kwargs)
        dialog.show_dialog()

    def _create_dialog(self, owner, target_sim=None, target=None, **kwargs):
        if self.picker_dialog.title is None:
            title = lambda *_, **__: self.get_name(apply_name_modifiers=False)
        else:
            title = self.picker_dialog.title
        dialog = self.picker_dialog(owner, title=title, resolver=self.get_resolver())
        self._setup_dialog(dialog, **kwargs)
        dialog.set_target_sim(target_sim)
        dialog.set_target(target)
        dialog.add_listener(self._on_picker_selected)
        return dialog

    @classmethod
    def potential_interactions(cls, target, context, **kwargs):
        if cls.use_pie_menu():
            if context.source == InteractionSource.AUTONOMY and not cls.allow_autonomous:
                return
            recipe_ingredients_map = {}
            for row_data in cls.picker_rows_gen(target, context, recipe_ingredients_map=recipe_ingredients_map, **kwargs):
                if not row_data.available_as_pie_menu:
                    pass
                else:
                    affordance = _PickerPieMenuProxyInteraction.generate(cls, picker_row_data=row_data)
                    for aop in affordance.potential_interactions(target, context, recipe_ingredients_map=recipe_ingredients_map, **kwargs):
                        yield aop
        else:
            yield from super().potential_interactions(target, context, **kwargs)

    @flexmethod
    def picker_rows_gen(cls, inst, target, context, **kwargs):
        raise NotImplementedError

    def _setup_dialog(self, dialog, **kwargs):
        for row in self.picker_rows_gen(self.target, self.context, **kwargs):
            dialog.add_row(row)

    def _on_picker_selected(self, dialog):
        if dialog.multi_select:
            tag_objs = dialog.get_result_tags()
            self.on_multi_choice_selected(tag_objs, ingredient_check=dialog.ingredient_check)
        else:
            tag_obj = dialog.get_single_result_tag()
            self.on_choice_selected(tag_obj, ingredient_check=dialog.ingredient_check)

    def on_multi_choice_selected(self, picked_choice, **kwargs):
        raise NotImplementedError

    def on_choice_selected(self, picked_choice, **kwargs):
        raise NotImplementedError

class PickerSuperInteraction(PickerSuperInteractionMixin, ImmediateSuperInteraction):
    INSTANCE_SUBCLASSES_ONLY = True

    @classmethod
    def _verify_tuning_callback(cls):
        if cls.allow_user_directed or cls.pie_menu_option is not None:
            logger.error('{} is tuned to be disallowed user directed but has Pie Menu options. Suggestion: allow the interaction to be user directed.', cls.__name__)
        return super()._verify_tuning_callback()

    def __init__(self, *args, choice_enumeration_strategy=None, **kwargs):
        super().__init__(*args, **kwargs)
        self._choice_enumeration_strategy = choice_enumeration_strategy
        if self.allow_autonomous and self._choice_enumeration_strategy is None:
            logger.error('{} is a new PickerSuperInteraction that was added without also adding an appropriate ChoiceEnumerationStrategy.  The owner of this SI should set up a new strategy or use an existing one.  See me if you have any questions.'.format(self), owner='rez')
lock_instance_tunables(PickerSuperInteraction, outcome=InteractionOutcome())
class PickerSingleChoiceSuperInteraction(PickerSuperInteraction):
    INSTANCE_SUBCLASSES_ONLY = True
    INSTANCE_TUNABLES = {'single_choice_display_name': OptionalTunable(tunable=TunableLocalizedStringFactory(description="\n                The name of the interaction if only one option is available. There\n                should be a single token for the item that's used. The token will\n                be replaced with the name of a Sim in Sim Pickers, or an object\n                for recipes, etc.\n                 \n                Picked Sim/Picked Object participants can be used as display\n                name tokens.\n                ", default=None), tuning_group=GroupNames.UI)}

    @classmethod
    def potential_interactions(cls, target, context, **kwargs):
        if context.source == InteractionSource.AUTONOMY and not cls.allow_autonomous:
            return
        single_row = None
        (_, single_row) = cls.get_single_choice_and_row(context=context, target=target, **kwargs)
        if cls.single_choice_display_name is not None and single_row is None:
            yield from super().potential_interactions(target, context, **kwargs)
        else:
            picked_item_ids = () if single_row is None else (single_row.tag,)
            yield AffordanceObjectPair(cls, target, cls, None, picked_item_ids=picked_item_ids, picked_row=single_row, **kwargs)

    @flexmethod
    def _get_name(cls, inst, target=DEFAULT, context=DEFAULT, picked_row=None, **interaction_parameters):
        inst_or_cls = inst if inst is not None else cls
        context = inst_or_cls.context if context is DEFAULT else context
        target = inst_or_cls.target if target is DEFAULT else target
        if inst_or_cls.single_choice_display_name is not None and picked_row is not None:
            (override_tunable, _) = inst_or_cls.get_name_override_and_test_result(target=target, context=context, **interaction_parameters)
            loc_string = override_tunable.new_display_name if override_tunable is not None else None
            if loc_string is None:
                loc_string = inst_or_cls.single_choice_display_name
            display_name = inst_or_cls.create_localized_string(loc_string, picked_row.name, target=target, context=context, **interaction_parameters)
            return display_name
        return super(PickerSingleChoiceSuperInteraction, inst_or_cls)._get_name(target=target, context=context, **interaction_parameters)

    @flexmethod
    def get_single_choice_and_row(cls, inst, context=None, target=None, **kwargs):
        return (None, None)

    def _show_picker_dialog(self, owner, target_sim=None, target=None, choices=(), **kwargs):
        if self.use_pie_menu():
            return
        picked_item_ids = self.interaction_parameters.get('picked_item_ids')
        picked_item_ids = list(picked_item_ids) if picked_item_ids is not None else None
        if picked_item_ids and len(choices) == 1 and choices[0].sim_info.sim_id == picked_item_ids[0]:
            self.on_choice_selected(picked_item_ids[0])
            return
        dialog = self._create_dialog(owner, target_sim=None, target=target, **kwargs)
        dialog.show_dialog()

class AutonomousPickerSuperInteraction(SuperInteraction):

    def __init__(self, *args, choice_enumeration_strategy=None, **kwargs):
        super().__init__(*args, **kwargs)
        self._choice_enumeration_strategy = choice_enumeration_strategy
lock_instance_tunables(AutonomousPickerSuperInteraction, allow_user_directed=False, basic_reserve_object=None, disable_transitions=True)
class SimPickerLinkContinuation(enum.Int):
    NEITHER = 0
    ACTOR = 1
    PICKED = 2
    ALL = 3
    TARGET = 4

class SimPickerMixin:
    INSTANCE_TUNABLES = {'actor_continuation': TunableContinuation(description='\n            If specified, a continuation to push on the actor when a picker\n            selection has been made.\n            ', locked_args={'actor': ParticipantType.Actor}, tuning_group=GroupNames.PICKERTUNING), 'target_continuation': TunableContinuation(description='\n            If specified, a continuation to push on the target sim when a picker\n            selection has been made.\n            ', locked_args={'actor': ParticipantType.TargetSim}, tuning_group=GroupNames.PICKERTUNING), 'picked_continuation': TunableContinuation(description='\n            If specified, a continuation to push on each sim selected in the\n            picker.\n            ', locked_args={'actor': ParticipantType.Actor}, tuning_group=GroupNames.PICKERTUNING), 'continuations_are_sequential': Tunable(description='\n            This specifies that the continuations tuned in picked_continuation\n            are applied sequentially to the list of picked sims.\n            \n            e.g. The first continuation will be pushed on the first picked sim.\n            The second continuation will be pushed on the second picked sim,\n            etc. Note: There should never be more picked sims than\n            continuations, however, there can be less picked sims than\n            continuations, to allow for cases where the number of sims is a\n            range.\n            ', tunable_type=bool, default=False, tuning_group=GroupNames.PICKERTUNING), 'link_continuation': TunableEnumEntry(description='\n            Which, if any, continuation should cancel if the other interaction\n            is canceled.\n            \n            e.g. if "ACTOR" is selected, then if any of the picked continuation\n            is canceled the actor continuation will also be canceled.\n            ', tunable_type=SimPickerLinkContinuation, default=SimPickerLinkContinuation.NEITHER, tuning_group=GroupNames.PICKERTUNING), 'sim_filter': OptionalTunable(description='\n            Optional Sim Filter to run Sims through. Otherwise we will just get\n            all Sims that pass the tests.\n            ', tunable=TunableSimFilter.TunableReference(description='\n                Sim Filter to run all Sims through before tests.\n                ', pack_safe=True), disabled_name='no_filter', enabled_name='sim_filter_selected', tuning_group=GroupNames.PICKERTUNING), 'sim_filter_household_override': OptionalTunable(description="\n            Sim filter by default uses the actor's household for household-\n            related filter terms, such as the In Family filter term. If this is\n            enabled, a different participant's household will be used. If the\n            participant is an object instead of a Sim, the object's owner\n            household will be used.\n            ", tunable=TunableEnumEntry(tunable_type=ParticipantTypeSingle, default=ParticipantTypeSingle.TargetSim, invalid_enums=(ParticipantTypeSingle.Actor,)), tuning_group=GroupNames.PICKERTUNING), 'sim_filter_requesting_sim': TunableEnumEntry(description='\n            Determine which Sim filter requests are relative to. For example, if\n            you want all Sims in a romantic relationship with the target, tune\n            TargetSim here, and then a relationship filter.\n            \n            NOTE: Tuning filters is, performance-wise, preferable to tests.\n            ', tunable_type=ParticipantTypeSingle, default=ParticipantTypeSingle.Actor, tuning_group=GroupNames.PICKERTUNING), 'create_sim_if_no_valid_choices': Tunable(description='\n            If checked, this picker will generate a sim that matches the tuned\n            filter if no other matching sims are available. This sim will match\n            the tuned filter, but not necessarily respect other rules of this \n            picker (like radius, tests, or instantiation). If you need one of\n            those things, see a GPE about improving this option.\n            ', tunable_type=bool, default=False, tuning_group=GroupNames.PICKERTUNING), 'sim_tests': event_testing.tests.TunableTestSet(description='\n            A set of tests that are run against the prospective sims. At least\n            one test must pass in order for the prospective sim to show. All\n            sims will pass if there are no tests. Picked_sim is the participant\n            type for the prospective sim.\n            ', tuning_group=GroupNames.PICKERTUNING), 'include_uninstantiated_sims': Tunable(description='\n            If unchecked, uninstantiated sims will never be available in the\n            picker. if checked, they must still pass the filters and tests This\n            is an optimization tunable.\n            ', tunable_type=bool, default=True, tuning_group=GroupNames.PICKERTUNING), 'include_instantiated_sims': Tunable(description='\n            If unchecked, instantiated sims will never be available in the\n            picker. if checked, they must still pass the filters and tests.\n            ', tunable_type=bool, default=True, tuning_group=GroupNames.PICKERTUNING), 'include_actor_sim': Tunable(description='\n            If checked then the actor sim can be included in the picker options\n            and will not be blacklisted.\n            ', tunable_type=bool, default=False, tuning_group=GroupNames.PICKERTUNING), 'include_target_sim': Tunable(description='\n            If checked then the target sim can be included in the picker options\n            and will not be blacklisted.\n            ', tunable_type=bool, default=False, tuning_group=GroupNames.PICKERTUNING), 'radius': OptionalTunable(description='\n            If enabled then Sim must be in a certain range for consideration.\n            This should only be enabled when include_instantiated_sims is True\n            and include_uninstantiated_sims is False.\n            ', tunable=TunableRange(description='\n                Sim must be in a certain range for consideration.\n                ', tunable_type=int, default=5, minimum=1, maximum=50), tuning_group=GroupNames.PICKERTUNING)}

    @classmethod
    def _verify_tuning_callback(cls):
        super()._verify_tuning_callback()
        if cls.include_instantiated_sims and cls.include_uninstantiated_sims and cls.radius is not None:
            logger.error('Tuning: If include_instantiated_sims is False or include_uninstantiated_sims is True, radius should be disabled: {}', cls)

    @flexmethod
    def _get_requesting_sim_info_for_picker(cls, inst, context, *, target, **kwargs):
        inst_or_cls = inst if inst is not None else cls
        return inst_or_cls.get_participant(inst_or_cls.sim_filter_requesting_sim, sim=context.sim, target=target, **kwargs)

    @flexmethod
    def _get_actor_for_picker(cls, inst, context, *, target, **kwargs):
        sim = inst.sim if inst is not None else context.sim
        if sim is not None:
            return sim.sim_info

    @flexmethod
    def get_sim_filter_gsi_name(cls, inst):
        inst_or_cls = inst if inst is not None else cls
        return str(inst_or_cls)

    @flexmethod
    def _get_valid_sim_choices_gen(cls, inst, target, context, test_function=None, min_required=1, **kwargs):
        inst_or_cls = inst if inst is not None else cls
        requesting_sim_info = inst_or_cls._get_requesting_sim_info_for_picker(context, target=target, **kwargs)
        if requesting_sim_info is None:
            return
        actor_sim_info = inst_or_cls._get_actor_for_picker(context, target=target, **kwargs)
        household_id = None
        resolver = inst_or_cls.get_resolver(target=target, context=context)
        participant = resolver.get_participant(inst_or_cls.sim_filter_household_override)
        if participant.is_sim:
            household_id = participant.household_id
        else:
            household_id = participant.get_household_owner_id()
            household_id = 0
        sim_info_manager = services.sim_info_manager()
        sim_infos = sim_info_manager.get_all()
        pre_filtered_sim_infos = inst_or_cls.sim_filter.get_pre_filtered_sim_infos(requesting_sim_info=requesting_sim_info)
        sim_infos = pre_filtered_sim_infos
        valid_sims_found = 0
        for sim_info in sim_infos:
            if not sim_info.can_instantiate_sim:
                pass
            elif inst_or_cls.include_actor_sim or sim_info is actor_sim_info:
                pass
            elif inst_or_cls.include_target_sim or (not target is not None or not target.is_sim) or sim_info is target.sim_info:
                pass
            elif inst_or_cls.include_uninstantiated_sims or not sim_info.is_instanced():
                pass
            elif inst_or_cls.include_instantiated_sims or sim_info.is_instanced():
                pass
            elif inst_or_cls.radius is not None:
                sim = sim_info.get_sim_instance()
                if not sim is None:
                    if actor_sim_info is None:
                        pass
                    else:
                        actor_sim = actor_sim_info.get_sim_instance()
                        if actor_sim is None:
                            pass
                        else:
                            delta = actor_sim.intended_position - sim.intended_position
                            if delta.magnitude() > inst_or_cls.radius:
                                pass
                            else:
                                results = services.sim_filter_service().submit_filter(inst_or_cls.sim_filter, None, sim_constraints=(sim_info.sim_id,), requesting_sim_info=requesting_sim_info.sim_info, allow_yielding=False, household_id=household_id, gsi_source_fn=inst_or_cls.get_sim_filter_gsi_name)
                                if not results:
                                    pass
                                else:
                                    if inst:
                                        interaction_parameters = inst.interaction_parameters.copy()
                                    else:
                                        interaction_parameters = kwargs.copy()
                                    interaction_parameters['picked_item_ids'] = {sim_info.sim_id}
                                    resolver = InteractionResolver(cls, inst, target=target, context=context, **interaction_parameters)
                                    if not inst_or_cls.sim_tests or not inst_or_cls.sim_tests.run_tests(resolver):
                                        pass
                                    elif test_function is not None:
                                        sim = sim_info.get_sim_instance()
                                        if not sim is None:
                                            if not test_function(sim):
                                                pass
                                            else:
                                                valid_sims_found += 1
                                                yield results[0]
                                    else:
                                        valid_sims_found += 1
                                        yield results[0]
            else:
                results = services.sim_filter_service().submit_filter(inst_or_cls.sim_filter, None, sim_constraints=(sim_info.sim_id,), requesting_sim_info=requesting_sim_info.sim_info, allow_yielding=False, household_id=household_id, gsi_source_fn=inst_or_cls.get_sim_filter_gsi_name)
                if not results:
                    pass
                else:
                    if inst:
                        interaction_parameters = inst.interaction_parameters.copy()
                    else:
                        interaction_parameters = kwargs.copy()
                    interaction_parameters['picked_item_ids'] = {sim_info.sim_id}
                    resolver = InteractionResolver(cls, inst, target=target, context=context, **interaction_parameters)
                    if not inst_or_cls.sim_tests or not inst_or_cls.sim_tests.run_tests(resolver):
                        pass
                    elif test_function is not None:
                        sim = sim_info.get_sim_instance()
                        if not sim is None:
                            if not test_function(sim):
                                pass
                            else:
                                valid_sims_found += 1
                                yield results[0]
                    else:
                        valid_sims_found += 1
                        yield results[0]
        number_required_sims_not_found = min_required - valid_sims_found
        if inst_or_cls.sim_filter_household_override is not None and participant is not None and inst_or_cls.sim_filter is not None and pre_filtered_sim_infos is not None and inst_or_cls.create_sim_if_no_valid_choices and number_required_sims_not_found > 0:
            results = services.sim_filter_service().submit_matching_filter(number_of_sims_to_find=number_required_sims_not_found, sim_filter=inst_or_cls.sim_filter, requesting_sim_info=requesting_sim_info.sim_info, allow_yielding=False, household_id=household_id, gsi_source_fn=inst_or_cls.get_sim_filter_gsi_name)
            if results:
                yield from results

    def _push_continuation(self, sim, tunable_continuation, sim_ids, insert_strategy, picked_zone_set):
        continuation = None
        picked_item_set = {target_sim_id for target_sim_id in sim_ids if target_sim_id is not None}
        self.interaction_parameters['picked_item_ids'] = frozenset(picked_item_set)
        self.push_tunable_continuation(tunable_continuation, insert_strategy=insert_strategy, picked_item_ids=picked_item_set, picked_zone_ids=picked_zone_set)
        new_continuation = sim.queue.find_pushed_interaction_by_id(self.group_id)
        while new_continuation is not None:
            continuation = new_continuation
            new_continuation = sim.queue.find_continuation_by_id(continuation.id)
        return continuation

    def _push_continuations(self, sim_ids, zone_datas=None):
        if not self.picked_continuation:
            insert_strategy = QueueInsertStrategy.LAST
        else:
            insert_strategy = QueueInsertStrategy.NEXT
        picked_zone_set = None
        if zone_datas is not None:
            try:
                picked_zone_set = {zone_data.zone_id for zone_data in zone_datas if zone_data is not None}
            except TypeError:
                picked_zone_set = {zone_datas.zone_id}
            self.interaction_parameters['picked_zone_ids'] = frozenset(picked_zone_set)
        actor_continuation = None
        target_continuation = None
        picked_continuations = []
        if self.actor_continuation:
            actor_continuation = self._push_continuation(self.sim, self.actor_continuation, sim_ids, insert_strategy, picked_zone_set)
        if self.target_continuation:
            target_sim = self.get_participant(ParticipantType.TargetSim)
            if target_sim is not None:
                target_continuation = self._push_continuation(target_sim, self.target_continuation, sim_ids, insert_strategy, picked_zone_set)
        if self.picked_continuation:
            num_continuations = len(self.picked_continuation)
            for (index, target_sim_id) in enumerate(sim_ids):
                if target_sim_id is None:
                    pass
                else:
                    logger.info('SimPicker: picked Sim_id: {}', target_sim_id, owner='jjacobson')
                    target_sim = services.object_manager().get(target_sim_id)
                    if target_sim is None:
                        logger.error("You must pick on lot sims for a tuned 'picked continuation' to function.", owner='jjacobson')
                    else:
                        self.interaction_parameters['picked_item_ids'] = frozenset((target_sim_id,))
                        if self.continuations_are_sequential:
                            if index < num_continuations:
                                continuation = (self.picked_continuation[index],)
                            else:
                                logger.error('There are not enough tuned picked continuations for the interaction {}, so picked sim {} and all others afterwards will be skipped.', self, target_sim, owner='johnwilkinson')
                                break
                        else:
                            continuation = self.picked_continuation
                        self.push_tunable_continuation(continuation, insert_strategy=insert_strategy, actor=target_sim, picked_zone_ids=picked_zone_set)
                        picked_continuation = target_sim.queue.find_pushed_interaction_by_id(self.group_id)
                        if picked_continuation is not None:
                            new_continuation = target_sim.queue.find_continuation_by_id(picked_continuation.id)
                            while new_continuation is not None:
                                picked_continuation = new_continuation
                                new_continuation = target_sim.queue.find_continuation_by_id(picked_continuation.id)
                            picked_continuations.append(picked_continuation)
        if self.link_continuation != SimPickerLinkContinuation.NEITHER:
            if actor_continuation is not None:
                if target_continuation is not None and (self.link_continuation == SimPickerLinkContinuation.TARGET or self.link_continuation == SimPickerLinkContinuation.ALL):
                    actor_continuation.attach_interaction(target_continuation)
                for interaction in picked_continuations:
                    if self.link_continuation == SimPickerLinkContinuation.ACTOR or self.link_continuation == SimPickerLinkContinuation.ALL:
                        interaction.attach_interaction(actor_continuation)
                    if not self.link_continuation == SimPickerLinkContinuation.PICKED:
                        if self.link_continuation == SimPickerLinkContinuation.ALL:
                            actor_continuation.attach_interaction(interaction)
                    actor_continuation.attach_interaction(interaction)
            if target_continuation is not None:
                if actor_continuation is not None and (self.link_continuation == SimPickerLinkContinuation.ACTOR or self.link_continuation == SimPickerLinkContinuation.ALL):
                    target_continuation.attach_interaction(actor_continuation)
                for interaction in picked_continuations:
                    if self.link_continuation == SimPickerLinkContinuation.TARGET or self.link_continuation == SimPickerLinkContinuation.ALL:
                        interaction.attach_interaction(target_continuation)
                    if not self.link_continuation == SimPickerLinkContinuation.PICKED:
                        if self.link_continuation == SimPickerLinkContinuation.ALL:
                            target_continuation.attach_interaction(interaction)
                    target_continuation.attach_interaction(interaction)

class SimPickerInteraction(SimPickerMixin, PickerSingleChoiceSuperInteraction):
    INSTANCE_TUNABLES = {'picker_dialog': TunablePickerDialogVariant(description='The object picker dialog.', available_picker_flags=ObjectPickerTuningFlags.SIM, tuning_group=GroupNames.PICKERTUNING), 'default_selection_tests': OptionalTunable(description='\n            If enabled, any Sim who passes these tests will be selected by\n            default when the picker pops up.\n            ', tunable=event_testing.tests.TunableTestSet(description='\n                A set of tests that will automatically select Sims that pass\n                when the Sim Picker pops up.\n                '), tuning_group=GroupNames.PICKERTUNING), 'default_selections_sort_to_front': Tunable(description='\n            If checked then any Sim that passes the default selection tests\n            will be sorted to the top of the list.\n            ', tunable_type=bool, default=False), 'carry_item_from_inventory': OptionalTunable(description='\n            If enabled continuations will set the carry target on the \n            interaction context to an object with the specified tag found on\n            the inventory of the Sim running this interaction.\n            ', tunable=tag.TunableTags(description='\n                The set of tags that are used to determine which objects to highlight.\n                '))}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, choice_enumeration_strategy=SimPickerEnumerationStrategy(), **kwargs)

    def _run_interaction_gen(self, timeline):
        choices = tuple(self._get_valid_sim_choices_gen(self.target, self.context, min_required=self.picker_dialog.min_selectable))
        if self.picker_dialog.min_selectable == 0 and not choices:
            self._on_successful_picker_selection()
            return True
        if len(choices) == 1:
            self._kwargs['picked_item_ids'] = (choices[0].sim_info.sim_id,)
        self._show_picker_dialog(self.sim, target_sim=self.sim, target=self.target, choices=choices)
        return True

    def _setup_dialog(self, dialog, **kwargs):
        super()._setup_dialog(dialog, **kwargs)
        if self.default_selections_sort_to_front:
            dialog.sort_selected_items_to_front()

    @flexmethod
    def create_row(cls, inst, tag, select_default=False):
        return SimPickerRow(sim_id=tag, tag=tag, select_default=select_default)

    @flexmethod
    def get_single_choice_and_row(cls, inst, context=None, target=None, **kwargs):
        inst_or_cls = inst if inst is not None else cls
        if context is None:
            return (None, None)
        single_choice = None
        for choice in inst_or_cls._get_valid_sim_choices_gen(target, context, **kwargs):
            if single_choice is not None:
                return (None, None)
            else:
                single_choice = choice
                if single_choice is not None:
                    return (single_choice.sim_info, inst_or_cls.create_row(single_choice.sim_info.sim_id))
        if single_choice is not None:
            return (single_choice.sim_info, inst_or_cls.create_row(single_choice.sim_info.sim_id))
        return (None, None)

    @classmethod
    def has_valid_choice(cls, target, context, **kwargs):
        if cls.picker_dialog is not None and cls.picker_dialog.min_selectable == 0:
            return True
        choice_count = 0
        if cls.create_sim_if_no_valid_choices:
            return True
        for _ in cls._get_valid_sim_choices_gen(target, context, **kwargs):
            if cls.picker_dialog is None:
                return True
            choice_count += 1
            if choice_count >= cls.picker_dialog.min_selectable:
                return True
        return False

    @flexmethod
    def picker_rows_gen(cls, inst, target, context, **kwargs):
        inst_or_cls = inst if inst is not None else cls
        interaction_parameters = {}
        resolver = InteractionResolver(cls, inst, target=target, context=context, **interaction_parameters)
        for filter_result in inst_or_cls._get_valid_sim_choices_gen(target, context, **kwargs):
            sim_id = filter_result.sim_info.id
            logger.info('SimPicker: add sim_id:{}', sim_id)
            interaction_parameters['picked_item_ids'] = {sim_id}
            resolver.interaction_parameters = interaction_parameters
            if not inst_or_cls.default_selection_tests is not None or inst_or_cls.default_selection_tests.run_tests(resolver):
                select_default = True
            else:
                select_default = False
            row = inst_or_cls.create_row(sim_id, select_default=select_default)
            yield row

    def _on_picker_selected(self, dialog):
        if dialog.accepted:
            results = dialog.get_result_tags()
            if len(results) >= dialog.min_selectable:
                self._on_successful_picker_selection(results)

    def _on_successful_picker_selection(self, results=()):
        self._push_continuations(results)

    def _set_inventory_carry_target(self):
        if self.carry_item_from_inventory is not None:
            for obj in self.sim.inventory_component:
                if any(obj.definition.has_build_buy_tag(tag) for tag in self.carry_item_from_inventory):
                    self.context.carry_target = obj
                    break

    def _push_continuations(self, *args, **kwargs):
        self._set_inventory_carry_target()
        super()._push_continuations(*args, **kwargs)

    def on_choice_selected(self, choice_tag, **kwargs):
        sim = choice_tag
        if sim is not None:
            self._push_continuations((sim,))

class PickerTravelHereSuperInteraction(SimPickerInteraction):
    INSTANCE_TUNABLES = {'get_display_name_from_destination': Tunable(description='\n            If checked then we will attempt to get the Travel With Interaction\n            Name from the venue we are trying to travel to and use that instead\n            of display name.\n            ', tunable_type=bool, default=True, tuning_group=GroupNames.PICKERTUNING)}

    @flexmethod
    def _get_name(cls, inst, target=DEFAULT, context=DEFAULT, **interaction_parameters):
        inst_or_cls = inst if inst is not None else cls
        target = inst_or_cls.target if target is DEFAULT else target
        context = inst_or_cls.context if context is DEFAULT else context
        zone_id = context.pick.get_zone_id_from_pick_location()
        if inst is not None:
            inst.interaction_parameters['picked_zone_ids'] = frozenset({zone_id})
        if inst_or_cls.get_display_name_from_destination:
            venue_instance = get_venue_instance_from_pick_location(context.pick)
            if venue_instance is not None and venue_instance.travel_with_interaction_name is not None:
                return venue_instance.travel_with_interaction_name(target, context)
        return super(__class__, inst_or_cls)._get_name(target=target, context=context, **interaction_parameters)

    @flexmethod
    def _get_valid_sim_choices_gen(cls, inst, target, context, **kwargs):
        zone_id = context.pick.get_zone_id_from_pick_location()
        for filter_result in super()._get_valid_sim_choices_gen(target, context, **kwargs):
            if filter_result.sim_info.zone_id != zone_id:
                yield filter_result

    @flexmethod
    def get_single_choice_and_row(cls, inst, context=None, target=None, **kwargs):
        return (None, None)

    def _on_picker_selected(self, dialog):
        if dialog.accepted:
            results = dialog.get_result_tags()
            self._on_successful_picker_selection(results)

    def _on_successful_picker_selection(self, results=()):
        zone_ids = self.interaction_parameters.get('picked_zone_ids', None)
        if zone_ids is None:
            zone_id = self.context.pick.get_zone_id_from_pick_location()
            zone_ids = frozenset({zone_id})
        zone_datas = []
        for zone_id in zone_ids:
            zone_data = services.get_persistence_service().get_zone_proto_buff(zone_id)
            if zone_data is not None:
                zone_datas.append(zone_data)
        self._push_continuations(results, zone_datas=zone_datas)
lock_instance_tunables(PickerTravelHereSuperInteraction, single_choice_display_name=None)
class AutonomousSimPickerSuperInteraction(SimPickerMixin, AutonomousPickerSuperInteraction):
    INSTANCE_TUNABLES = {'test_compatibility': Tunable(description='\n            If checked then the actor continuation will be tested for\n            interaction compatibility.\n            ', tunable_type=bool, default=False, tuning_group=GroupNames.PICKERTUNING)}

    def __init__(self, *args, choice_enumeration_strategy=None, **kwargs):
        if choice_enumeration_strategy is None:
            choice_enumeration_strategy = SimPickerEnumerationStrategy()
        super().__init__(*args, choice_enumeration_strategy=choice_enumeration_strategy, **kwargs)

    @classmethod
    def _test(cls, target, context, **interaction_parameters):
        if not cls.has_valid_choice(target, context, **interaction_parameters):
            return event_testing.results.TestResult(False, 'This picker SI has no valid choices.')
        return super()._test(target, context, **interaction_parameters)

    def _run_interaction_gen(self, timeline):
        continuation = self.actor_continuation[0]
        affordance = continuation.si_affordance_override if continuation.si_affordance_override is not None else continuation.affordance
        compatibility_func = functools.partial(self.are_affordances_linked, affordance, self.context) if self.test_compatibility else None
        self._choice_enumeration_strategy.build_choice_list(self, self.sim, test_function=compatibility_func)
        chosen_sim = self._choice_enumeration_strategy.find_best_choice(self)
        if chosen_sim is not None:
            chosen_sim = (chosen_sim,)
            self._push_continuations(chosen_sim)
        return True

    @classmethod
    def has_valid_choice(cls, target, context, **kwargs):
        continuation = cls.actor_continuation[0]
        affordance = continuation.si_affordance_override if continuation.si_affordance_override is not None else continuation.affordance
        compatibility_func = functools.partial(cls.are_affordances_linked, affordance, context) if cls.test_compatibility else None
        if cls.create_sim_if_no_valid_choices:
            return True
        for _ in cls._get_valid_sim_choices_gen(target, context, test_function=compatibility_func, **kwargs):
            return True
        return False

    @classmethod
    def are_affordances_linked(cls, affordance, context, chosen_sim):
        aop = AffordanceObjectPair(affordance, chosen_sim, affordance, None)
        chosen_sim_si_state = chosen_sim.si_state
        for existing_si in chosen_sim_si_state.all_guaranteed_si_gen(context.priority, group_id=context.group_id):
            if not aop.affordance.is_linked_to(existing_si.affordance):
                return False
        return True

class LotPickerMixin:
    INSTANCE_TUNABLES = {'default_inclusion': TunableVariant(description='\n            This defines which venue types are valid for this picker.\n            ', include_all=TunableTuple(description='\n                This will allow all venue types to be valid, except those blacklisted.\n                ', include_all_by_default=Tunable(bool, True), exclude_venues=TunableList(tunable=TunableReference(manager=services.get_instance_manager(sims4.resources.Types.VENUE), tuning_group=GroupNames.VENUES, pack_safe=True), display_name='Blacklist Items'), exclude_lists=TunableList(TunableVenueListReference(), display_name='Blacklist Lists'), locked_args={'include_all_by_default': True}), exclude_all=TunableTuple(description='\n                This will prevent all venue types from being valid, except those whitelisted.\n                ', include_all_by_default=Tunable(bool, False), include_venues=TunableList(tunable=TunableReference(manager=services.get_instance_manager(sims4.resources.Types.VENUE), tuning_group=GroupNames.VENUES, pack_safe=True), display_name='Whitelist Items'), include_lists=TunableList(TunableVenueListReference(), display_name='Whitelist Lists'), locked_args={'include_all_by_default': False}), default='include_all', tuning_group=GroupNames.PICKERTUNING), 'building_types_excluded': TunableSet(description='\n            A set of building types to exclude for this map view picker. This\n            allows us to do things like exclude apartments or penthouses.\n            ', tunable=TunableEnumEntry(description='\n                The Plex Building Type we want to exclude. Default is standard\n                lots. Fully Contained Plexes are apartments, and Penthouses are\n                regular lots that sit on top of apartment buildings and have a\n                common area.\n                ', tunable_type=PlexBuildingType, default=PlexBuildingType.FULLY_CONTAINED_PLEX, invalid_enums=(PlexBuildingType.INVALID,)), tuning_group=GroupNames.PICKERTUNING), 'include_actor_home_lot': Tunable(description='\n            If checked, the actors home lot will always be included regardless\n            of venue tuning.  If unchecked, it will NEVER be included.\n            ', tunable_type=bool, default=False, tuning_group=GroupNames.PICKERTUNING), 'include_target_home_lot': Tunable(description='\n            If checked, the target(s) home lot will always be included regardless\n            of venue tuning.  If unchecked, it will NEVER be included.\n            ', tunable_type=bool, default=False, tuning_group=GroupNames.PICKERTUNING), 'include_active_lot': Tunable(description='\n            If checked, the active lot may or may not appear based on \n            venue/situation tuning. If not checked, the active lot will always \n            be excluded.\n            ', tunable_type=bool, default=False, tuning_group=GroupNames.PICKERTUNING), 'test_region_compatibility': Tunable(description="\n            If enabled, this picker will filter out regions that are\n            inaccessible from the actor sim's current region.\n            ", tunable_type=bool, default=True, tuning_group=GroupNames.PICKERTUNING), 'exclude_rented_zones': Tunable(description='\n            If enabled, this picker will filter out zones that have already\n            been rented. This should likely be restricted to interactions that\n            are attempting to rent a zone or join a vacation.\n            ', tunable_type=bool, default=False, tuning_group=GroupNames.PICKERTUNING), 'testable_region_inclusion': TunableMapping(description='\n            Mapping of region to tests that should be run to verify if region\n            should be added.\n            ', key_type=TunableReference(manager=services.get_instance_manager(sims4.resources.Types.VENUE), pack_safe=True), value_type=TunableTestSet(description='\n                A series of tests that must pass in order for the region to be\n                available for picking.\n                '), tuning_group=GroupNames.PICKERTUNING)}

    @flexmethod
    def _get_valid_lot_choices(cls, inst, target, context, target_list=None):
        inst_or_cls = inst if inst is not None else cls
        actor = context.sim
        if actor is None:
            return []
        target_zone_ids = []
        actor_zone_id = actor.household.home_zone_id
        results = []
        if target_list is None:
            if target.household is not None:
                target_zone_ids.append(target.household.home_zone_id)
        else:
            sim_info_manager = services.sim_info_manager()
            for target_sim_id in target_list:
                target_sim_info = sim_info_manager.get(target_sim_id)
                if target_sim_info is not None and target_sim_info.household is not None:
                    target_zone_ids.append(target_sim_info.household.home_zone_id)
        venue_manager = services.get_instance_manager(sims4.resources.Types.VENUE)
        active_zone_id = services.current_zone().id
        travel_group_manager = services.travel_group_manager()
        current_region = region.get_region_instance_from_zone_id(actor.zone_id)
        if current_region is None and inst_or_cls.test_region_compatibility:
            logger.error('Could not find region for Sim {}'.format(actor), owner='rmccord')
            return []
        plex_service = services.get_plex_service()
        persistence_service = services.get_persistence_service()
        for zone_data in persistence_service.zone_proto_buffs_gen():
            zone_id = zone_data.zone_id
            if inst_or_cls.include_active_lot or zone_id == active_zone_id:
                pass
            elif inst_or_cls.test_region_compatibility:
                dest_region = region.get_region_instance_from_zone_id(zone_id)
                if not current_region.is_region_compatible(dest_region):
                    pass
                elif inst_or_cls.exclude_rented_zones:
                    travel_group = travel_group_manager.get_travel_group_by_zone_id(zone_id)
                    if travel_group is not None and travel_group.played:
                        pass
                    elif inst_or_cls.building_types_excluded and plex_service.get_plex_building_type(zone_id) in inst_or_cls.building_types_excluded:
                        pass
                    elif zone_id == actor_zone_id:
                        if inst_or_cls.include_actor_home_lot:
                            results.append(zone_data)
                            if zone_id in target_zone_ids:
                                if inst_or_cls.include_target_home_lot:
                                    results.append(zone_data)
                                    venue_type_id = build_buy.get_current_venue(zone_id)
                                    if venue_type_id is None:
                                        pass
                                    else:
                                        venue_type = venue_manager.get(venue_type_id)
                                        if venue_type is None:
                                            pass
                                        else:
                                            region_tests = inst_or_cls.testable_region_inclusion.get(venue_type)
                                            if region_tests is not None:
                                                resolver = SingleSimResolver(actor.sim_info)
                                                if region_tests.run_tests(resolver):
                                                    results.append(zone_data)
                                                else:
                                                    default_inclusion = inst_or_cls.default_inclusion
                                                    if inst_or_cls.default_inclusion.include_all_by_default:
                                                        if venue_type in default_inclusion.exclude_venues:
                                                            pass
                                                        elif any(venue_type in venue_list for venue_list in default_inclusion.exclude_lists):
                                                            pass
                                                        else:
                                                            results.append(zone_data)
                                                    elif venue_type in default_inclusion.include_venues:
                                                        results.append(zone_data)
                                                    elif any(venue_type in venue_list for venue_list in default_inclusion.include_lists):
                                                        results.append(zone_data)
                                            else:
                                                default_inclusion = inst_or_cls.default_inclusion
                                                if inst_or_cls.default_inclusion.include_all_by_default:
                                                    if venue_type in default_inclusion.exclude_venues:
                                                        pass
                                                    elif any(venue_type in venue_list for venue_list in default_inclusion.exclude_lists):
                                                        pass
                                                    else:
                                                        results.append(zone_data)
                                                elif venue_type in default_inclusion.include_venues:
                                                    results.append(zone_data)
                                                elif any(venue_type in venue_list for venue_list in default_inclusion.include_lists):
                                                    results.append(zone_data)
                            else:
                                venue_type_id = build_buy.get_current_venue(zone_id)
                                if venue_type_id is None:
                                    pass
                                else:
                                    venue_type = venue_manager.get(venue_type_id)
                                    if venue_type is None:
                                        pass
                                    else:
                                        region_tests = inst_or_cls.testable_region_inclusion.get(venue_type)
                                        if region_tests is not None:
                                            resolver = SingleSimResolver(actor.sim_info)
                                            if region_tests.run_tests(resolver):
                                                results.append(zone_data)
                                            else:
                                                default_inclusion = inst_or_cls.default_inclusion
                                                if inst_or_cls.default_inclusion.include_all_by_default:
                                                    if venue_type in default_inclusion.exclude_venues:
                                                        pass
                                                    elif any(venue_type in venue_list for venue_list in default_inclusion.exclude_lists):
                                                        pass
                                                    else:
                                                        results.append(zone_data)
                                                elif venue_type in default_inclusion.include_venues:
                                                    results.append(zone_data)
                                                elif any(venue_type in venue_list for venue_list in default_inclusion.include_lists):
                                                    results.append(zone_data)
                                        else:
                                            default_inclusion = inst_or_cls.default_inclusion
                                            if inst_or_cls.default_inclusion.include_all_by_default:
                                                if venue_type in default_inclusion.exclude_venues:
                                                    pass
                                                elif any(venue_type in venue_list for venue_list in default_inclusion.exclude_lists):
                                                    pass
                                                else:
                                                    results.append(zone_data)
                                            elif venue_type in default_inclusion.include_venues:
                                                results.append(zone_data)
                                            elif any(venue_type in venue_list for venue_list in default_inclusion.include_lists):
                                                results.append(zone_data)
                    elif zone_id in target_zone_ids:
                        if inst_or_cls.include_target_home_lot:
                            results.append(zone_data)
                            venue_type_id = build_buy.get_current_venue(zone_id)
                            if venue_type_id is None:
                                pass
                            else:
                                venue_type = venue_manager.get(venue_type_id)
                                if venue_type is None:
                                    pass
                                else:
                                    region_tests = inst_or_cls.testable_region_inclusion.get(venue_type)
                                    if region_tests is not None:
                                        resolver = SingleSimResolver(actor.sim_info)
                                        if region_tests.run_tests(resolver):
                                            results.append(zone_data)
                                        else:
                                            default_inclusion = inst_or_cls.default_inclusion
                                            if inst_or_cls.default_inclusion.include_all_by_default:
                                                if venue_type in default_inclusion.exclude_venues:
                                                    pass
                                                elif any(venue_type in venue_list for venue_list in default_inclusion.exclude_lists):
                                                    pass
                                                else:
                                                    results.append(zone_data)
                                            elif venue_type in default_inclusion.include_venues:
                                                results.append(zone_data)
                                            elif any(venue_type in venue_list for venue_list in default_inclusion.include_lists):
                                                results.append(zone_data)
                                    else:
                                        default_inclusion = inst_or_cls.default_inclusion
                                        if inst_or_cls.default_inclusion.include_all_by_default:
                                            if venue_type in default_inclusion.exclude_venues:
                                                pass
                                            elif any(venue_type in venue_list for venue_list in default_inclusion.exclude_lists):
                                                pass
                                            else:
                                                results.append(zone_data)
                                        elif venue_type in default_inclusion.include_venues:
                                            results.append(zone_data)
                                        elif any(venue_type in venue_list for venue_list in default_inclusion.include_lists):
                                            results.append(zone_data)
                    else:
                        venue_type_id = build_buy.get_current_venue(zone_id)
                        if venue_type_id is None:
                            pass
                        else:
                            venue_type = venue_manager.get(venue_type_id)
                            if venue_type is None:
                                pass
                            else:
                                region_tests = inst_or_cls.testable_region_inclusion.get(venue_type)
                                if region_tests is not None:
                                    resolver = SingleSimResolver(actor.sim_info)
                                    if region_tests.run_tests(resolver):
                                        results.append(zone_data)
                                    else:
                                        default_inclusion = inst_or_cls.default_inclusion
                                        if inst_or_cls.default_inclusion.include_all_by_default:
                                            if venue_type in default_inclusion.exclude_venues:
                                                pass
                                            elif any(venue_type in venue_list for venue_list in default_inclusion.exclude_lists):
                                                pass
                                            else:
                                                results.append(zone_data)
                                        elif venue_type in default_inclusion.include_venues:
                                            results.append(zone_data)
                                        elif any(venue_type in venue_list for venue_list in default_inclusion.include_lists):
                                            results.append(zone_data)
                                else:
                                    default_inclusion = inst_or_cls.default_inclusion
                                    if inst_or_cls.default_inclusion.include_all_by_default:
                                        if venue_type in default_inclusion.exclude_venues:
                                            pass
                                        elif any(venue_type in venue_list for venue_list in default_inclusion.exclude_lists):
                                            pass
                                        else:
                                            results.append(zone_data)
                                    elif venue_type in default_inclusion.include_venues:
                                        results.append(zone_data)
                                    elif any(venue_type in venue_list for venue_list in default_inclusion.include_lists):
                                        results.append(zone_data)
                elif inst_or_cls.building_types_excluded and plex_service.get_plex_building_type(zone_id) in inst_or_cls.building_types_excluded:
                    pass
                elif zone_id == actor_zone_id:
                    if inst_or_cls.include_actor_home_lot:
                        results.append(zone_data)
                        if zone_id in target_zone_ids:
                            if inst_or_cls.include_target_home_lot:
                                results.append(zone_data)
                                venue_type_id = build_buy.get_current_venue(zone_id)
                                if venue_type_id is None:
                                    pass
                                else:
                                    venue_type = venue_manager.get(venue_type_id)
                                    if venue_type is None:
                                        pass
                                    else:
                                        region_tests = inst_or_cls.testable_region_inclusion.get(venue_type)
                                        if region_tests is not None:
                                            resolver = SingleSimResolver(actor.sim_info)
                                            if region_tests.run_tests(resolver):
                                                results.append(zone_data)
                                            else:
                                                default_inclusion = inst_or_cls.default_inclusion
                                                if inst_or_cls.default_inclusion.include_all_by_default:
                                                    if venue_type in default_inclusion.exclude_venues:
                                                        pass
                                                    elif any(venue_type in venue_list for venue_list in default_inclusion.exclude_lists):
                                                        pass
                                                    else:
                                                        results.append(zone_data)
                                                elif venue_type in default_inclusion.include_venues:
                                                    results.append(zone_data)
                                                elif any(venue_type in venue_list for venue_list in default_inclusion.include_lists):
                                                    results.append(zone_data)
                                        else:
                                            default_inclusion = inst_or_cls.default_inclusion
                                            if inst_or_cls.default_inclusion.include_all_by_default:
                                                if venue_type in default_inclusion.exclude_venues:
                                                    pass
                                                elif any(venue_type in venue_list for venue_list in default_inclusion.exclude_lists):
                                                    pass
                                                else:
                                                    results.append(zone_data)
                                            elif venue_type in default_inclusion.include_venues:
                                                results.append(zone_data)
                                            elif any(venue_type in venue_list for venue_list in default_inclusion.include_lists):
                                                results.append(zone_data)
                        else:
                            venue_type_id = build_buy.get_current_venue(zone_id)
                            if venue_type_id is None:
                                pass
                            else:
                                venue_type = venue_manager.get(venue_type_id)
                                if venue_type is None:
                                    pass
                                else:
                                    region_tests = inst_or_cls.testable_region_inclusion.get(venue_type)
                                    if region_tests is not None:
                                        resolver = SingleSimResolver(actor.sim_info)
                                        if region_tests.run_tests(resolver):
                                            results.append(zone_data)
                                        else:
                                            default_inclusion = inst_or_cls.default_inclusion
                                            if inst_or_cls.default_inclusion.include_all_by_default:
                                                if venue_type in default_inclusion.exclude_venues:
                                                    pass
                                                elif any(venue_type in venue_list for venue_list in default_inclusion.exclude_lists):
                                                    pass
                                                else:
                                                    results.append(zone_data)
                                            elif venue_type in default_inclusion.include_venues:
                                                results.append(zone_data)
                                            elif any(venue_type in venue_list for venue_list in default_inclusion.include_lists):
                                                results.append(zone_data)
                                    else:
                                        default_inclusion = inst_or_cls.default_inclusion
                                        if inst_or_cls.default_inclusion.include_all_by_default:
                                            if venue_type in default_inclusion.exclude_venues:
                                                pass
                                            elif any(venue_type in venue_list for venue_list in default_inclusion.exclude_lists):
                                                pass
                                            else:
                                                results.append(zone_data)
                                        elif venue_type in default_inclusion.include_venues:
                                            results.append(zone_data)
                                        elif any(venue_type in venue_list for venue_list in default_inclusion.include_lists):
                                            results.append(zone_data)
                elif zone_id in target_zone_ids:
                    if inst_or_cls.include_target_home_lot:
                        results.append(zone_data)
                        venue_type_id = build_buy.get_current_venue(zone_id)
                        if venue_type_id is None:
                            pass
                        else:
                            venue_type = venue_manager.get(venue_type_id)
                            if venue_type is None:
                                pass
                            else:
                                region_tests = inst_or_cls.testable_region_inclusion.get(venue_type)
                                if region_tests is not None:
                                    resolver = SingleSimResolver(actor.sim_info)
                                    if region_tests.run_tests(resolver):
                                        results.append(zone_data)
                                    else:
                                        default_inclusion = inst_or_cls.default_inclusion
                                        if inst_or_cls.default_inclusion.include_all_by_default:
                                            if venue_type in default_inclusion.exclude_venues:
                                                pass
                                            elif any(venue_type in venue_list for venue_list in default_inclusion.exclude_lists):
                                                pass
                                            else:
                                                results.append(zone_data)
                                        elif venue_type in default_inclusion.include_venues:
                                            results.append(zone_data)
                                        elif any(venue_type in venue_list for venue_list in default_inclusion.include_lists):
                                            results.append(zone_data)
                                else:
                                    default_inclusion = inst_or_cls.default_inclusion
                                    if inst_or_cls.default_inclusion.include_all_by_default:
                                        if venue_type in default_inclusion.exclude_venues:
                                            pass
                                        elif any(venue_type in venue_list for venue_list in default_inclusion.exclude_lists):
                                            pass
                                        else:
                                            results.append(zone_data)
                                    elif venue_type in default_inclusion.include_venues:
                                        results.append(zone_data)
                                    elif any(venue_type in venue_list for venue_list in default_inclusion.include_lists):
                                        results.append(zone_data)
                else:
                    venue_type_id = build_buy.get_current_venue(zone_id)
                    if venue_type_id is None:
                        pass
                    else:
                        venue_type = venue_manager.get(venue_type_id)
                        if venue_type is None:
                            pass
                        else:
                            region_tests = inst_or_cls.testable_region_inclusion.get(venue_type)
                            if region_tests is not None:
                                resolver = SingleSimResolver(actor.sim_info)
                                if region_tests.run_tests(resolver):
                                    results.append(zone_data)
                                else:
                                    default_inclusion = inst_or_cls.default_inclusion
                                    if inst_or_cls.default_inclusion.include_all_by_default:
                                        if venue_type in default_inclusion.exclude_venues:
                                            pass
                                        elif any(venue_type in venue_list for venue_list in default_inclusion.exclude_lists):
                                            pass
                                        else:
                                            results.append(zone_data)
                                    elif venue_type in default_inclusion.include_venues:
                                        results.append(zone_data)
                                    elif any(venue_type in venue_list for venue_list in default_inclusion.include_lists):
                                        results.append(zone_data)
                            else:
                                default_inclusion = inst_or_cls.default_inclusion
                                if inst_or_cls.default_inclusion.include_all_by_default:
                                    if venue_type in default_inclusion.exclude_venues:
                                        pass
                                    elif any(venue_type in venue_list for venue_list in default_inclusion.exclude_lists):
                                        pass
                                    else:
                                        results.append(zone_data)
                                elif venue_type in default_inclusion.include_venues:
                                    results.append(zone_data)
                                elif any(venue_type in venue_list for venue_list in default_inclusion.include_lists):
                                    results.append(zone_data)
            elif inst_or_cls.exclude_rented_zones:
                travel_group = travel_group_manager.get_travel_group_by_zone_id(zone_id)
                if travel_group is not None and travel_group.played:
                    pass
                elif inst_or_cls.building_types_excluded and plex_service.get_plex_building_type(zone_id) in inst_or_cls.building_types_excluded:
                    pass
                elif zone_id == actor_zone_id:
                    if inst_or_cls.include_actor_home_lot:
                        results.append(zone_data)
                        if zone_id in target_zone_ids:
                            if inst_or_cls.include_target_home_lot:
                                results.append(zone_data)
                                venue_type_id = build_buy.get_current_venue(zone_id)
                                if venue_type_id is None:
                                    pass
                                else:
                                    venue_type = venue_manager.get(venue_type_id)
                                    if venue_type is None:
                                        pass
                                    else:
                                        region_tests = inst_or_cls.testable_region_inclusion.get(venue_type)
                                        if region_tests is not None:
                                            resolver = SingleSimResolver(actor.sim_info)
                                            if region_tests.run_tests(resolver):
                                                results.append(zone_data)
                                            else:
                                                default_inclusion = inst_or_cls.default_inclusion
                                                if inst_or_cls.default_inclusion.include_all_by_default:
                                                    if venue_type in default_inclusion.exclude_venues:
                                                        pass
                                                    elif any(venue_type in venue_list for venue_list in default_inclusion.exclude_lists):
                                                        pass
                                                    else:
                                                        results.append(zone_data)
                                                elif venue_type in default_inclusion.include_venues:
                                                    results.append(zone_data)
                                                elif any(venue_type in venue_list for venue_list in default_inclusion.include_lists):
                                                    results.append(zone_data)
                                        else:
                                            default_inclusion = inst_or_cls.default_inclusion
                                            if inst_or_cls.default_inclusion.include_all_by_default:
                                                if venue_type in default_inclusion.exclude_venues:
                                                    pass
                                                elif any(venue_type in venue_list for venue_list in default_inclusion.exclude_lists):
                                                    pass
                                                else:
                                                    results.append(zone_data)
                                            elif venue_type in default_inclusion.include_venues:
                                                results.append(zone_data)
                                            elif any(venue_type in venue_list for venue_list in default_inclusion.include_lists):
                                                results.append(zone_data)
                        else:
                            venue_type_id = build_buy.get_current_venue(zone_id)
                            if venue_type_id is None:
                                pass
                            else:
                                venue_type = venue_manager.get(venue_type_id)
                                if venue_type is None:
                                    pass
                                else:
                                    region_tests = inst_or_cls.testable_region_inclusion.get(venue_type)
                                    if region_tests is not None:
                                        resolver = SingleSimResolver(actor.sim_info)
                                        if region_tests.run_tests(resolver):
                                            results.append(zone_data)
                                        else:
                                            default_inclusion = inst_or_cls.default_inclusion
                                            if inst_or_cls.default_inclusion.include_all_by_default:
                                                if venue_type in default_inclusion.exclude_venues:
                                                    pass
                                                elif any(venue_type in venue_list for venue_list in default_inclusion.exclude_lists):
                                                    pass
                                                else:
                                                    results.append(zone_data)
                                            elif venue_type in default_inclusion.include_venues:
                                                results.append(zone_data)
                                            elif any(venue_type in venue_list for venue_list in default_inclusion.include_lists):
                                                results.append(zone_data)
                                    else:
                                        default_inclusion = inst_or_cls.default_inclusion
                                        if inst_or_cls.default_inclusion.include_all_by_default:
                                            if venue_type in default_inclusion.exclude_venues:
                                                pass
                                            elif any(venue_type in venue_list for venue_list in default_inclusion.exclude_lists):
                                                pass
                                            else:
                                                results.append(zone_data)
                                        elif venue_type in default_inclusion.include_venues:
                                            results.append(zone_data)
                                        elif any(venue_type in venue_list for venue_list in default_inclusion.include_lists):
                                            results.append(zone_data)
                elif zone_id in target_zone_ids:
                    if inst_or_cls.include_target_home_lot:
                        results.append(zone_data)
                        venue_type_id = build_buy.get_current_venue(zone_id)
                        if venue_type_id is None:
                            pass
                        else:
                            venue_type = venue_manager.get(venue_type_id)
                            if venue_type is None:
                                pass
                            else:
                                region_tests = inst_or_cls.testable_region_inclusion.get(venue_type)
                                if region_tests is not None:
                                    resolver = SingleSimResolver(actor.sim_info)
                                    if region_tests.run_tests(resolver):
                                        results.append(zone_data)
                                    else:
                                        default_inclusion = inst_or_cls.default_inclusion
                                        if inst_or_cls.default_inclusion.include_all_by_default:
                                            if venue_type in default_inclusion.exclude_venues:
                                                pass
                                            elif any(venue_type in venue_list for venue_list in default_inclusion.exclude_lists):
                                                pass
                                            else:
                                                results.append(zone_data)
                                        elif venue_type in default_inclusion.include_venues:
                                            results.append(zone_data)
                                        elif any(venue_type in venue_list for venue_list in default_inclusion.include_lists):
                                            results.append(zone_data)
                                else:
                                    default_inclusion = inst_or_cls.default_inclusion
                                    if inst_or_cls.default_inclusion.include_all_by_default:
                                        if venue_type in default_inclusion.exclude_venues:
                                            pass
                                        elif any(venue_type in venue_list for venue_list in default_inclusion.exclude_lists):
                                            pass
                                        else:
                                            results.append(zone_data)
                                    elif venue_type in default_inclusion.include_venues:
                                        results.append(zone_data)
                                    elif any(venue_type in venue_list for venue_list in default_inclusion.include_lists):
                                        results.append(zone_data)
                else:
                    venue_type_id = build_buy.get_current_venue(zone_id)
                    if venue_type_id is None:
                        pass
                    else:
                        venue_type = venue_manager.get(venue_type_id)
                        if venue_type is None:
                            pass
                        else:
                            region_tests = inst_or_cls.testable_region_inclusion.get(venue_type)
                            if region_tests is not None:
                                resolver = SingleSimResolver(actor.sim_info)
                                if region_tests.run_tests(resolver):
                                    results.append(zone_data)
                                else:
                                    default_inclusion = inst_or_cls.default_inclusion
                                    if inst_or_cls.default_inclusion.include_all_by_default:
                                        if venue_type in default_inclusion.exclude_venues:
                                            pass
                                        elif any(venue_type in venue_list for venue_list in default_inclusion.exclude_lists):
                                            pass
                                        else:
                                            results.append(zone_data)
                                    elif venue_type in default_inclusion.include_venues:
                                        results.append(zone_data)
                                    elif any(venue_type in venue_list for venue_list in default_inclusion.include_lists):
                                        results.append(zone_data)
                            else:
                                default_inclusion = inst_or_cls.default_inclusion
                                if inst_or_cls.default_inclusion.include_all_by_default:
                                    if venue_type in default_inclusion.exclude_venues:
                                        pass
                                    elif any(venue_type in venue_list for venue_list in default_inclusion.exclude_lists):
                                        pass
                                    else:
                                        results.append(zone_data)
                                elif venue_type in default_inclusion.include_venues:
                                    results.append(zone_data)
                                elif any(venue_type in venue_list for venue_list in default_inclusion.include_lists):
                                    results.append(zone_data)
            elif inst_or_cls.building_types_excluded and plex_service.get_plex_building_type(zone_id) in inst_or_cls.building_types_excluded:
                pass
            elif zone_id == actor_zone_id:
                if inst_or_cls.include_actor_home_lot:
                    results.append(zone_data)
                    if zone_id in target_zone_ids:
                        if inst_or_cls.include_target_home_lot:
                            results.append(zone_data)
                            venue_type_id = build_buy.get_current_venue(zone_id)
                            if venue_type_id is None:
                                pass
                            else:
                                venue_type = venue_manager.get(venue_type_id)
                                if venue_type is None:
                                    pass
                                else:
                                    region_tests = inst_or_cls.testable_region_inclusion.get(venue_type)
                                    if region_tests is not None:
                                        resolver = SingleSimResolver(actor.sim_info)
                                        if region_tests.run_tests(resolver):
                                            results.append(zone_data)
                                        else:
                                            default_inclusion = inst_or_cls.default_inclusion
                                            if inst_or_cls.default_inclusion.include_all_by_default:
                                                if venue_type in default_inclusion.exclude_venues:
                                                    pass
                                                elif any(venue_type in venue_list for venue_list in default_inclusion.exclude_lists):
                                                    pass
                                                else:
                                                    results.append(zone_data)
                                            elif venue_type in default_inclusion.include_venues:
                                                results.append(zone_data)
                                            elif any(venue_type in venue_list for venue_list in default_inclusion.include_lists):
                                                results.append(zone_data)
                                    else:
                                        default_inclusion = inst_or_cls.default_inclusion
                                        if inst_or_cls.default_inclusion.include_all_by_default:
                                            if venue_type in default_inclusion.exclude_venues:
                                                pass
                                            elif any(venue_type in venue_list for venue_list in default_inclusion.exclude_lists):
                                                pass
                                            else:
                                                results.append(zone_data)
                                        elif venue_type in default_inclusion.include_venues:
                                            results.append(zone_data)
                                        elif any(venue_type in venue_list for venue_list in default_inclusion.include_lists):
                                            results.append(zone_data)
                    else:
                        venue_type_id = build_buy.get_current_venue(zone_id)
                        if venue_type_id is None:
                            pass
                        else:
                            venue_type = venue_manager.get(venue_type_id)
                            if venue_type is None:
                                pass
                            else:
                                region_tests = inst_or_cls.testable_region_inclusion.get(venue_type)
                                if region_tests is not None:
                                    resolver = SingleSimResolver(actor.sim_info)
                                    if region_tests.run_tests(resolver):
                                        results.append(zone_data)
                                    else:
                                        default_inclusion = inst_or_cls.default_inclusion
                                        if inst_or_cls.default_inclusion.include_all_by_default:
                                            if venue_type in default_inclusion.exclude_venues:
                                                pass
                                            elif any(venue_type in venue_list for venue_list in default_inclusion.exclude_lists):
                                                pass
                                            else:
                                                results.append(zone_data)
                                        elif venue_type in default_inclusion.include_venues:
                                            results.append(zone_data)
                                        elif any(venue_type in venue_list for venue_list in default_inclusion.include_lists):
                                            results.append(zone_data)
                                else:
                                    default_inclusion = inst_or_cls.default_inclusion
                                    if inst_or_cls.default_inclusion.include_all_by_default:
                                        if venue_type in default_inclusion.exclude_venues:
                                            pass
                                        elif any(venue_type in venue_list for venue_list in default_inclusion.exclude_lists):
                                            pass
                                        else:
                                            results.append(zone_data)
                                    elif venue_type in default_inclusion.include_venues:
                                        results.append(zone_data)
                                    elif any(venue_type in venue_list for venue_list in default_inclusion.include_lists):
                                        results.append(zone_data)
            elif zone_id in target_zone_ids:
                if inst_or_cls.include_target_home_lot:
                    results.append(zone_data)
                    venue_type_id = build_buy.get_current_venue(zone_id)
                    if venue_type_id is None:
                        pass
                    else:
                        venue_type = venue_manager.get(venue_type_id)
                        if venue_type is None:
                            pass
                        else:
                            region_tests = inst_or_cls.testable_region_inclusion.get(venue_type)
                            if region_tests is not None:
                                resolver = SingleSimResolver(actor.sim_info)
                                if region_tests.run_tests(resolver):
                                    results.append(zone_data)
                                else:
                                    default_inclusion = inst_or_cls.default_inclusion
                                    if inst_or_cls.default_inclusion.include_all_by_default:
                                        if venue_type in default_inclusion.exclude_venues:
                                            pass
                                        elif any(venue_type in venue_list for venue_list in default_inclusion.exclude_lists):
                                            pass
                                        else:
                                            results.append(zone_data)
                                    elif venue_type in default_inclusion.include_venues:
                                        results.append(zone_data)
                                    elif any(venue_type in venue_list for venue_list in default_inclusion.include_lists):
                                        results.append(zone_data)
                            else:
                                default_inclusion = inst_or_cls.default_inclusion
                                if inst_or_cls.default_inclusion.include_all_by_default:
                                    if venue_type in default_inclusion.exclude_venues:
                                        pass
                                    elif any(venue_type in venue_list for venue_list in default_inclusion.exclude_lists):
                                        pass
                                    else:
                                        results.append(zone_data)
                                elif venue_type in default_inclusion.include_venues:
                                    results.append(zone_data)
                                elif any(venue_type in venue_list for venue_list in default_inclusion.include_lists):
                                    results.append(zone_data)
            else:
                venue_type_id = build_buy.get_current_venue(zone_id)
                if venue_type_id is None:
                    pass
                else:
                    venue_type = venue_manager.get(venue_type_id)
                    if venue_type is None:
                        pass
                    else:
                        region_tests = inst_or_cls.testable_region_inclusion.get(venue_type)
                        if region_tests is not None:
                            resolver = SingleSimResolver(actor.sim_info)
                            if region_tests.run_tests(resolver):
                                results.append(zone_data)
                            else:
                                default_inclusion = inst_or_cls.default_inclusion
                                if inst_or_cls.default_inclusion.include_all_by_default:
                                    if venue_type in default_inclusion.exclude_venues:
                                        pass
                                    elif any(venue_type in venue_list for venue_list in default_inclusion.exclude_lists):
                                        pass
                                    else:
                                        results.append(zone_data)
                                elif venue_type in default_inclusion.include_venues:
                                    results.append(zone_data)
                                elif any(venue_type in venue_list for venue_list in default_inclusion.include_lists):
                                    results.append(zone_data)
                        else:
                            default_inclusion = inst_or_cls.default_inclusion
                            if inst_or_cls.default_inclusion.include_all_by_default:
                                if venue_type in default_inclusion.exclude_venues:
                                    pass
                                elif any(venue_type in venue_list for venue_list in default_inclusion.exclude_lists):
                                    pass
                                else:
                                    results.append(zone_data)
                            elif venue_type in default_inclusion.include_venues:
                                results.append(zone_data)
                            elif any(venue_type in venue_list for venue_list in default_inclusion.include_lists):
                                results.append(zone_data)
        return results

class MapViewPickerInteraction(LotPickerMixin, PickerSuperInteraction):
    INSTANCE_TUNABLES = {'picker_dialog': TunablePickerDialogVariant(description='\n            The object picker dialog.\n            ', available_picker_flags=ObjectPickerTuningFlags.MAP_VIEW, tuning_group=GroupNames.PICKERTUNING, dialog_locked_args={'text_cancel': None, 'text_ok': None, 'title': None, 'text': None, 'text_tokens': DEFAULT, 'icon': None, 'secondary_icon': None, 'phone_ring_type': PhoneRingType.NO_RING}), 'actor_continuation': TunableContinuation(description='\n            If specified, a continuation to push on the actor when a picker \n            selection has been made.\n            ', locked_args={'actor': ParticipantType.Actor}, tuning_group=GroupNames.PICKERTUNING), 'target_continuation': TunableContinuation(description='\n            If specified, a continuation to push on the sim targetted', tuning_group=GroupNames.PICKERTUNING), 'bypass_picker_on_single_choice': Tunable(description='\n            If this is checked, bypass the picker if only one option is available.\n            ', tunable_type=bool, default=False, tuning_group=GroupNames.PICKERTUNING)}

    def _push_continuations(self, zone_datas):
        if not self.target_continuation:
            insert_strategy = QueueInsertStrategy.LAST
        else:
            insert_strategy = QueueInsertStrategy.NEXT
        try:
            picked_zone_set = {zone_data.zone_id for zone_data in zone_datas if zone_data is not None}
        except TypeError:
            picked_zone_set = {zone_datas.zone_id}
        self.interaction_parameters['picked_zone_ids'] = frozenset(picked_zone_set)
        if self.actor_continuation:
            self.push_tunable_continuation(self.actor_continuation, insert_strategy=insert_strategy, picked_zone_ids=picked_zone_set)
        if self.target_continuation:
            self.push_tunable_continuation(self.target_continuation, insert_strategy=insert_strategy, actor=self.target, picked_zone_ids=picked_zone_set)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, choice_enumeration_strategy=LotPickerEnumerationStrategy(), **kwargs)

    def _create_dialog(self, owner, target_sim=None, target=None, **kwargs):
        traveling_sims = []
        picked_sims = self.get_participants(ParticipantType.PickedSim)
        if picked_sims:
            traveling_sims = list(picked_sims)
        elif target is not None and target.is_sim and target is not self.sim:
            traveling_sims.append(target)
        dialog = self.picker_dialog(owner, title=lambda *_, **__: self.get_name(), resolver=self.get_resolver(), traveling_sims=traveling_sims)
        self._setup_dialog(dialog, **kwargs)
        dialog.set_target_sim(target_sim)
        dialog.set_target(target)
        dialog.add_listener(self._on_picker_selected)
        return dialog

    def _run_interaction_gen(self, timeline):
        choices = self._get_valid_lot_choices(self.target, self.context)
        if self.bypass_picker_on_single_choice and len(choices) == 1:
            self._push_continuations(choices[0])
            return True
        self._show_picker_dialog(self.sim, target_sim=self.sim, target=self.target)
        return True

    @flexmethod
    def create_row(cls, inst, tag):
        return LotPickerRow(zone_data=tag, option_id=tag.zone_id, tag=tag)

    @classmethod
    def has_valid_choice(cls, target, context, **kwargs):
        if cls._get_valid_lot_choices(target, context):
            return True
        return False

    @flexmethod
    def picker_rows_gen(cls, inst, target, context, **kwargs):
        inst_or_cls = inst if inst is not None else cls
        for filter_result in inst_or_cls._get_valid_lot_choices(target, context):
            logger.info('LotPicker: add zone_data:{}', filter_result)
            yield LotPickerRow(zone_data=filter_result, option_id=filter_result.zone_id, tag=filter_result)

    def _on_picker_selected(self, dialog):
        results = dialog.get_result_tags()
        if results:
            self._push_continuations(results)

    def on_choice_selected(self, choice_tag, **kwargs):
        result = choice_tag
        if result is not None:
            self._push_continuations(result)

class ObjectPickerMixin:
    INSTANCE_TUNABLES = {'continuation': OptionalTunable(description='\n            If enabled, you can tune a continuation to be pushed.\n            PickedObject will be the object that was selected\n            ', tunable=TunableContinuation(description='\n                If specified, a continuation to push on the chosen object.'), tuning_group=GroupNames.PICKERTUNING), 'single_push_continuation': Tunable(description='\n            If enabled, only the first continuation that can be successfully\n            pushed will run. Otherwise, all continuations are pushed such that\n            they run in order.\n            ', tunable_type=bool, default=False, tuning_group=GroupNames.PICKERTUNING)}

    @flexmethod
    def _get_objects_gen(cls, inst, target, context, **kwargs):
        raise NotImplementedError

    @classmethod
    def has_valid_choice(cls, target, context, **kwargs):
        for _ in cls._get_objects_gen(target, context):
            return True
        return False

    def _push_continuation(self, obj):
        if obj is not None and self.continuation is not None:
            picked_item_set = set()
            picked_item_set.add(obj.id)
            self._push_picked_continuation(picked_item_set)

    def _push_continuations(self, objs):
        if objs is not None and self.continuation is not None:
            picked_item_set = set()
            for obj in objs:
                picked_item_set.add(obj.id)
            self._push_picked_continuation(picked_item_set)

    def _push_picked_continuation(self, picked_items):
        self.interaction_parameters['picked_item_ids'] = picked_items
        self.push_tunable_continuation(self.continuation, multi_push=not self.single_push_continuation, picked_item_ids=picked_items, insert_strategy=QueueInsertStrategy.LAST)

    @flexmethod
    def _test_continuation_for_object(cls, inst, object_id, gsi_affordance_results=None, context=DEFAULT, target=DEFAULT):
        inst_or_cls = inst if inst is not None else cls
        picked_item_set = {object_id}
        result = event_testing.results.TestResult.TRUE
        resolver = inst_or_cls.get_resolver(target=target, context=context, picked_object=target, picked_item_ids=picked_item_set)
        for continuation in inst_or_cls.continuation:
            local_actors = resolver.get_participants(continuation.actor)
            for local_actor in local_actors:
                if isinstance(local_actor, sims.sim_info.SimInfo):
                    local_actor = local_actor.get_sim_instance()
                    if local_actor is None:
                        result = event_testing.results.TestResult(False, "Actor isn't instantiated")
                    else:
                        local_context = context.clone_for_sim(local_actor)
                        if continuation.carry_target is not None:
                            local_context.carry_target = resolver.get_participant(continuation.carry_target)
                        if continuation.target != ParticipantType.Invalid:
                            local_targets = resolver.get_participants(continuation.target)
                            local_target = next(iter(local_targets), None)
                        else:
                            local_target = None
                        if local_target.is_sim:
                            if isinstance(local_target, sims.sim_info.SimInfo):
                                local_target = local_target.get_sim_instance()
                        elif local_target.is_part:
                            local_target = local_target.part_owner
                        affordance = continuation.affordance
                        if local_target is not None and affordance.is_super:
                            result = local_actor.test_super_affordance(affordance, local_target, local_context, picked_object=target, picked_item_ids=picked_item_set)
                        else:
                            if continuation.si_affordance_override is not None:
                                super_affordance = continuation.si_affordance_override
                                super_interaction = None
                                push_super_on_prepare = True
                            else:
                                logger.error("Picker interaction doesn't have affordance override set for continuation", owner='nbaker')
                            aop = AffordanceObjectPair(affordance, local_target, super_affordance, super_interaction, picked_object=target, push_super_on_prepare=push_super_on_prepare, picked_item_ids=picked_item_set)
                            result = aop.test(local_context)
                        if gsi_affordance_results is not None:
                            gsi_affordance_results.append((result, affordance.get_name))
                        if result:
                            return result
                else:
                    local_context = context.clone_for_sim(local_actor)
                    if continuation.carry_target is not None:
                        local_context.carry_target = resolver.get_participant(continuation.carry_target)
                    if continuation.target != ParticipantType.Invalid:
                        local_targets = resolver.get_participants(continuation.target)
                        local_target = next(iter(local_targets), None)
                    else:
                        local_target = None
                    if local_target.is_sim:
                        if isinstance(local_target, sims.sim_info.SimInfo):
                            local_target = local_target.get_sim_instance()
                    elif local_target.is_part:
                        local_target = local_target.part_owner
                    affordance = continuation.affordance
                    if local_target is not None and affordance.is_super:
                        result = local_actor.test_super_affordance(affordance, local_target, local_context, picked_object=target, picked_item_ids=picked_item_set)
                    else:
                        if continuation.si_affordance_override is not None:
                            super_affordance = continuation.si_affordance_override
                            super_interaction = None
                            push_super_on_prepare = True
                        else:
                            logger.error("Picker interaction doesn't have affordance override set for continuation", owner='nbaker')
                        aop = AffordanceObjectPair(affordance, local_target, super_affordance, super_interaction, picked_object=target, push_super_on_prepare=push_super_on_prepare, picked_item_ids=picked_item_set)
                        result = aop.test(local_context)
                    if gsi_affordance_results is not None:
                        gsi_affordance_results.append((result, affordance.get_name))
                    if result:
                        return result
        return result

    @flexmethod
    def _test_continuation(cls, inst, row_data, **kwargs):
        inst_or_cls = inst if inst is not None else cls
        if inst_or_cls.continuation is None:
            return
        if not row_data.object_id:
            return
        result = inst_or_cls._test_continuation_for_object(row_data.object_id, **kwargs)
        if not result:
            row_data.is_enable = False
            row_data.row_tooltip = result.tooltip

class ObjectPickerInteraction(ObjectPickerMixin, PickerSingleChoiceSuperInteraction):
    INSTANCE_SUBCLASSES_ONLY = True

    class _DescriptionFromTooltip(HasTunableSingletonFactory, AutoFactoryInit):
        FACTORY_TUNABLES = {'field': TunableEnumEntry(description='\n                Use an existing field from the tooltip component\n                ', tunable_type=TooltipFields, default=TooltipFields.recipe_description)}

        def get_description(self, row_object, context=None, target=None):
            return row_object.get_tooltip_field(self.field, context=context, target=target)

    class _DescriptionFromText(HasTunableSingletonFactory, AutoFactoryInit):
        FACTORY_TUNABLES = {'text': TunableLocalizedStringFactoryVariant(description='\n                Text that will be displayed as the objects description.\n                '), 'text_tokens': OptionalTunable(description="\n                If enabled, localization tokens to be passed into 'text' can be\n                explicitly defined. For example, you could use a participant that is\n                not normally used, such as a owned sim. Or you could also\n                pass in statistic and commodity values.\n                \n                Participants tuned here should only be relevant to objects.  If \n                you try to tune a participant which only exist when you run an \n                interaction (e.g. carry_target) tooltip wont show anything.\n                ", tunable=LocalizationTokens.TunableFactory())}

        def get_description(self, row_object, **kwargs):
            resolver = SingleObjectResolver(row_object)
            if self.text_tokens is not None:
                tokens = self.text_tokens.get_tokens(resolver)
            else:
                tokens = ()
            return self.text(*tokens)

    class _DescriptionFromFishingBait(HasTunableSingletonFactory, AutoFactoryInit):

        def get_description(self, row_object, context=None, target=None):
            return FishingTuning.get_fishing_bait_description(row_object)

    INSTANCE_TUNABLES = {'picker_dialog': TunablePickerDialogVariant(description='\n            The object picker dialog.\n            ', available_picker_flags=ObjectPickerTuningFlags.OBJECT, tuning_group=GroupNames.PICKERTUNING), 'auto_pick': AutoPick(description='\n            If enabled, this interaction will pick one of the choices\n            available and push the continuation on it. It will be like the\n            interaction was run autonomously - no picker dialog will show up.\n            ', tuning_group=GroupNames.PICKERTUNING), 'fallback_description': OptionalTunable(description='\n            The fallback description if there is no recipe or custom description.\n            If disabled, (or referencing an unused tooltip field) The final\n            fallback is the catalog description.\n            ', tunable=TunableVariant(description='\n                Types of fallback descriptions\n                ', from_tooltip=_DescriptionFromTooltip.TunableFactory(), from_text=_DescriptionFromText.TunableFactory(), from_fishing_bait=_DescriptionFromFishingBait.TunableFactory(), default='from_tooltip'), tuning_group=GroupNames.PICKERTUNING, enabled_by_default=True), 'object_name_override': OptionalTunable(description='\n            If enabled, we override object name (row name) from either tooltip field or Loc text\n            ', tunable=TunableVariant(description='\n                Sources of object name override.\n                ', from_tooltip=_DescriptionFromTooltip.TunableFactory(), from_text=_DescriptionFromText.TunableFactory(), default='from_tooltip'), tuning_group=GroupNames.PICKERTUNING), 'show_rarity': Tunable(description='\n            If checked, the rarity will also be shown in the object picker. If\n            there is no object rarity for this object, nothing will be shown.\n            ', tunable_type=bool, default=False, tuning_group=GroupNames.PICKERTUNING)}

    @flexmethod
    def _use_ellipsized_name(cls, inst):
        inst_or_cls = inst if inst is not None else cls
        return not inst_or_cls.auto_pick

    @flexmethod
    def create_row(cls, inst, row_obj, context=DEFAULT, target=DEFAULT):
        name = None
        row_description = None
        icon = None
        icon_info = row_obj.get_icon_info_data()
        inst_or_cls = inst if inst is not None else cls
        object_name_override = inst_or_cls.object_name_override
        if row_obj.has_custom_name():
            name = LocalizationHelperTuning.get_raw_text(row_obj.custom_name)
        elif row_obj.crafting_component is not None:
            crafting_process = row_obj.get_crafting_process()
            recipe = crafting_process.recipe
            name = recipe.get_recipe_name(crafting_process.crafter) if object_name_override is None else object_name_override.get_description(row_obj, context=context, target=target)
            row_description = recipe.recipe_description(crafting_process.crafter)
            icon = recipe.icon_override
        elif object_name_override is not None:
            name = object_name_override.get_description(row_obj, context=context, target=target)
        if row_description is None:
            if row_obj.has_custom_description():
                row_description = LocalizationHelperTuning.get_raw_text(row_obj.custom_description)
            elif inst_or_cls.fallback_description is not None:
                row_description = inst_or_cls.fallback_description.get_description(row_obj, context=context, target=target)
        rarity_text = row_obj.get_object_rarity_string() if inst_or_cls.show_rarity else None
        row = ObjectPickerRow(object_id=row_obj.id, name=name, row_description=row_description, icon=icon, def_id=row_obj.definition.id, count=inst_or_cls.get_stack_count(row_obj), icon_info=icon_info, tag=row_obj, rarity_text=rarity_text)
        inst_or_cls._test_continuation(row, context=context, target=target)
        return row

    @flexmethod
    def get_single_choice_and_row(cls, inst, context=DEFAULT, target=DEFAULT, **kwargs):
        if inst is not None:
            inst_or_cls = inst
        else:
            return (None, None)
        first_obj = None
        first_row = None
        for obj in inst_or_cls._get_objects_gen(target, context):
            if first_obj is not None and first_row is not None:
                return (None, None)
            row = inst_or_cls.create_row(obj, context=context, target=target)
            first_obj = obj
            first_row = row
        return (first_obj, first_row)

    @flexmethod
    def get_stack_count(cls, inst, obj):
        return obj.stack_count()

    def _run_interaction_gen(self, timeline):
        if self.context.source != InteractionContext.SOURCE_PIE_MENU or self.auto_pick:
            choices = list(self._get_objects_gen(self.target, self.context))
            if choices:
                if self.auto_pick:
                    obj = self.auto_pick.perform_auto_pick(choices)
                else:
                    obj = AutoPickRandom.perform_auto_pick(choices)
                self._push_continuation(obj)
                return True
            return False
        self._show_picker_dialog(self.sim, target_sim=self.sim, target=self.target)
        return True

    @classmethod
    def has_valid_choice(cls, target, context, **kwargs):
        obj_count = 0
        for _ in cls._get_objects_gen(target, context):
            obj_count += 1
            if cls.picker_dialog:
                if obj_count >= cls.picker_dialog.min_selectable:
                    return True
            return True
        return False

    @flexmethod
    def picker_rows_gen(cls, inst, target, context, **kwargs):
        inst_or_cls = inst if inst is not None else cls
        for obj in inst_or_cls._get_objects_gen(target, context):
            row = inst_or_cls.create_row(obj, context=context, target=target)
            yield row

    def on_choice_selected(self, choice_tag, **kwargs):
        obj = choice_tag
        if obj is not None:
            self._push_continuation(obj)

    def on_multi_choice_selected(self, choice_tags, **kwargs):
        if choice_tags is not None:
            self._push_continuations(choice_tags)

class AutonomousObjectPickerInteraction(ObjectPickerMixin, AutonomousPickerSuperInteraction):
    INSTANCE_SUBCLASSES_ONLY = True
    LOCKOUT_STR = 'lockout'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, choice_enumeration_strategy=ObjectPickerEnumerationStrategy(), **kwargs)

    @classmethod
    def _test(cls, target, context, **interaction_parameters):
        if not cls.has_valid_choice(target, context, **interaction_parameters):
            return event_testing.results.TestResult(False, 'This picker SI has no valid choices.')
        return super()._test(target, context, **interaction_parameters)

    @flexmethod
    def _get_objects_gen(cls, inst, target, context, **kwargs):
        inst_or_cls = inst if inst is not None else cls
        sim = inst.sim if inst is not None else context.sim
        for obj in inst_or_cls._get_objects_internal_gen(target, context, **kwargs):
            if sim.has_lockout(obj):
                pass
            elif not inst_or_cls._test_continuation_for_object(obj.id, context=context, target=target, **kwargs):
                pass
            else:
                yield obj

    @flexmethod
    def _get_objects_with_results_gen(cls, inst, target, context, **kwargs):
        inst_or_cls = inst if inst is not None else cls
        sim = inst.sim if inst is not None else context.sim
        for obj in inst_or_cls._get_objects_internal_gen(target, context, **kwargs):
            if sim.has_lockout(obj):
                yield (obj, cls.LOCKOUT_STR)
            gsi_results = []
            inst_or_cls._test_continuation_for_object(obj.id, gsi_affordance_results=gsi_results, context=context, target=target, **kwargs)
            yield (obj, gsi_results)

    @flexmethod
    def _get_objects_internal_gen(cls, inst, *args, **kwargs):
        raise NotImplementedError

    def _run_interaction_gen(self, timeline):
        gsi_enabled = gsi_handlers.picker_handler.picker_log_archiver.enabled
        self._choice_enumeration_strategy.build_choice_list(self, self.sim, get_all=gsi_enabled)
        chosen_obj = self._choice_enumeration_strategy.find_best_choice(self)
        if chosen_obj is not None:
            self._push_continuation(chosen_obj)
            if gsi_enabled:
                gen_objects = self._choice_enumeration_strategy.get_gen_objects()
                gsi_handlers.picker_handler.archive_picker_message(self.interaction, self._sim, self._target, chosen_obj, gen_objects)
        return True

class ActorsUrnstonePickerMixin:

    @flexmethod
    def _get_objects_gen(cls, inst, target, context, **kwargs):
        yield sims.ghost.Ghost.get_urnstone_for_sim_id(context.sim.sim_id)

class DuplicateObjectsSuppressionType(enum.Int):
    BY_DEFINITION_ID = 0
    BY_STACK_ID = 1

class ObjectInInventoryPickerMixin:
    INSTANCE_TUNABLES = {'inventory_subject': TunableEnumEntry(description='\n            Subject on which the inventory exists.\n            ', tunable_type=ParticipantType, default=ParticipantType.Actor, tuning_group=GroupNames.PICKERTUNING), 'inventory_item_test': TunableVariant(default='object', description='\n                A test to run on the objects in the inventory to determine\n                which objects will show up in the picker. An object test type\n                left un-tuned is considered any object.\n                ', object=ObjectTypeFactory.TunableFactory(), tag_set=ObjectTagFactory.TunableFactory(), tuning_group=GroupNames.PICKERTUNING), 'additional_item_test': TunableTestSet(description='\n            A set of tests to run on each object in the inventory that passes the\n            inventory_item_test. Each object must pass first the inventory_item_test\n            and then the additional_item_test before it will be shown in the picker dialog.\n            Only tests with ParticipantType.Object will work\n            ', tuning_group=GroupNames.PICKERTUNING), 'suppress_duplicate_objects': OptionalTunable(description='\n            If checked, only a single copy of objects with the same definition/stack id\n            will be shown.\n            ', tunable=TunableEnumEntry(description='\n                Objects can be suppressed by different ways.\n                ', tunable_type=DuplicateObjectsSuppressionType, default=DuplicateObjectsSuppressionType.BY_DEFINITION_ID), tuning_group=GroupNames.PICKERTUNING)}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._definition_id_stack_counts = defaultdict(int)

    def _setup_dialog(self, dialog, **kwargs):
        if self.suppress_duplicate_objects is not None:
            subject = self.get_participant(participant_type=self.inventory_subject, sim=self.context.sim, target=self.target, **kwargs)
            for obj in subject.inventory_component:
                key = self._get_object_key_for_suppression(obj=obj)
                self._definition_id_stack_counts[key] += obj.stack_count()
        super()._setup_dialog(dialog, **kwargs)

    @classmethod
    def _get_object_key_for_suppression(cls, obj):
        key = None
        if obj.inventoryitem_component is not None:
            key = obj.inventoryitem_component.get_stack_id()
        if cls.suppress_duplicate_objects is not None and cls.suppress_duplicate_objects == DuplicateObjectsSuppressionType.BY_STACK_ID and key is None:
            key = obj.definition.id
        return key

    @flexmethod
    def _get_objects_internal_gen(cls, inst, target, context, **kwargs):
        inst_or_cls = inst if inst is not None else cls
        inventory_subject = inst_or_cls.get_participant(participant_type=inst_or_cls.inventory_subject, sim=context.sim, target=target, **kwargs)
        used_object_keys = set()
        if inventory_subject.inventory_component is not None:
            actor_sim = inst_or_cls.get_participant(participant_type=ParticipantType.Actor, sim=context.sim, target=target, **kwargs)
            actor_sim_info = actor_sim.sim_info if actor_sim is not None else None
            target_sim = inst_or_cls.get_participant(participant_type=ParticipantType.TargetSim, sim=context.sim, target=target, **kwargs)
            target_sim_info = target_sim.sim_info if target_sim is not None else None
            for obj in inventory_subject.inventory_component:
                key = cls._get_object_key_for_suppression(obj=obj)
                if not inst_or_cls.suppress_duplicate_objects is not None or key in used_object_keys:
                    pass
                elif not inst_or_cls.inventory_item_test(obj):
                    pass
                elif inst_or_cls.additional_item_test:
                    resolver = DoubleSimAndObjectResolver(actor_sim_info, target_sim_info, obj, inst_or_cls)
                    if not inst_or_cls.additional_item_test.run_tests(resolver):
                        pass
                    else:
                        used_object_keys.add(key)
                        yield obj
                else:
                    used_object_keys.add(key)
                    yield obj

    @flexmethod
    def get_stack_count(cls, inst, obj):
        if cls.suppress_duplicate_objects is not None:
            key = cls._get_object_key_for_suppression(obj=obj)
            return inst._definition_id_stack_counts[key]
        else:
            return super().get_stack_count(obj)

class ObjectInInventoryPickerInteraction(ObjectInInventoryPickerMixin, ObjectPickerInteraction):

    @flexmethod
    def _get_objects_gen(cls, inst, *args, **kwargs):
        inst_or_cls = inst if inst is not None else cls
        yield from super(__class__, inst_or_cls)._get_objects_internal_gen(*args, **kwargs)

class AutonomousObjectInInventoryPickerInteraction(ObjectInInventoryPickerMixin, AutonomousObjectPickerInteraction):
    pass

class ObjectInSlotPickerMixin:
    INSTANCE_TUNABLES = {'subject_with_slots': TunableEnumEntry(description='\n            Subject on which the slots exist.\n            ', tunable_type=ParticipantType, default=ParticipantType.Object, tuning_group=GroupNames.PICKERTUNING), 'slot_obj_test': TunableTestSet(description='\n            A set of tests to run on each object in the parents slots before\n            it will be shown in the picker dialog. Only tests with\n            ParticipantType.Object will work.\n            ', tuning_group=GroupNames.PICKERTUNING), 'required_slot_types': OptionalTunable(description='\n            If enabled, the child object must be in one of these slot types in\n            order to show up in the picker.\n            ', tunable=TunableSet(description='\n                The child object must be parented to one of these slots in\n                order to show up in the picker.\n                ', tunable=TunableStringHash32(description='\n                    The hashed name of the slot.\n                    ', default='_ctnm_SimInteraction_'), minlength=1), tuning_group=GroupNames.PICKERTUNING)}

    @flexmethod
    def _get_objects_internal_gen(cls, inst, target, context, **kwargs):
        inst_or_cls = inst if inst is not None else cls
        slot_subject = inst_or_cls.get_participant(participant_type=inst_or_cls.subject_with_slots, sim=context.sim, target=target, **kwargs)
        if slot_subject.children:
            for child in slot_subject.children:
                if not inst_or_cls.required_slot_types is not None or child.location.slot_hash or child.location.joint_name_hash not in inst_or_cls.required_slot_types:
                    pass
                elif inst_or_cls.slot_obj_test:
                    resolver = SingleObjectResolver(child)
                    if not inst_or_cls.slot_obj_test.run_tests(resolver):
                        pass
                    else:
                        yield child
                else:
                    yield child

class AutonomousObjectInSlotPickerInteraction(ObjectInSlotPickerMixin, AutonomousObjectPickerInteraction):
    pass

class TunableObjectTaggedObjectFilterTestSet(event_testing.tests.TestListLoadingMixin):
    DEFAULT_LIST = event_testing.tests.TestList()

    def __init__(self, **kwargs):
        super().__init__(tunable=TunableVariant(object_criteria_test=ObjectCriteriaTest.TunableFactory(locked_args={'subject_specific_tests': ObjectCriteriaSingleObjectSpecificTest(ObjectCriteriaTest.TARGET_OBJECTS, ParticipantType.Object), 'tooltip': None, 'identity_test': None, 'test_events': ()}), distance_test=DistanceTest.TunableFactory()), **kwargs)

class AutonomousObjectTaggedPickerInteraction(AutonomousObjectPickerInteraction):
    INSTANCE_TUNABLES = {'whitelist_filter': ObjectDefinitonsOrTagsVariant(description='\n            Either a list of tags or definitions that objects can be considered.\n            ', tuning_group=GroupNames.PICKERTUNING), 'blacklist_filter': OptionalTunable(ObjectDefinitonsOrTagsVariant(description='\n            Either a list of tags or definitions that objects should be ignored.\n            '), tuning_group=GroupNames.PICKERTUNING), 'radius': OptionalTunable(description='\n            Ensures objects are within a tuned radius.\n            \n            NOTE: THIS SHOULD ONLY BE DISABLED IF APPROVED BY A GPE.\n            Disabling this can have a serious performance impact since most \n            pickers will end up with way too many objects in them.\n            ', tunable=TunableRange(description='\n                Object must be in a certain range for consideration.\n                ', tunable_type=int, default=5, minimum=1, maximum=50), tuning_group=GroupNames.PICKERTUNING, enabled_by_default=True), 'object_filter_test': TunableObjectTaggedObjectFilterTestSet(description='\n            A list of test to verify object is valid to be selected for autonomous use.\n            ', tuning_group=GroupNames.PICKERTUNING), 'require_on_offlot_parity': Tunable(description='\n            If checked then we will not consider objects that are off the lot\n            unless the Sim running this interaction is also off.  We will\n            always consider objects on the lot.\n            ', tunable_type=bool, default=False, tuning_group=GroupNames.PICKERTUNING), 'supress_outside_if_modifier': Tunable(description='\n            If checked then we will not considered objects that are outside\n            if an outside autonomy modifier is in effect.\n            \n            If unchecked then in addition to considering objects that are outside\n            we will always score the interaction as if all objects are outside, \n            however we will still prefer objects that are inside, if any.\n            ', tunable_type=bool, default=True, tuning_group=GroupNames.PICKERTUNING)}

    @classproperty
    def is_autonomous_picker_interaction(cls):
        return True

    def get_outside_score_multiplier_override(self):
        if self.counts_as_inside or self.supress_outside_if_modifier:
            return
        (_, outside_multiplier) = self.sim.sim_info.get_outside_object_score_modification()
        return outside_multiplier

    @flexmethod
    def _get_objects_internal_gen(cls, inst, target, context, **kwargs):
        inst_or_cls = inst if inst is not None else cls
        object_manager = services.object_manager()
        sim = context.sim
        sim_intended_postion = sim.intended_position
        sim_level = sim.level
        prevent_outside = False
        handle_outside = False
        skipped = []
        (prevent_outside, outside_multiplier) = sim.sim_info.get_outside_object_score_modification()
        handle_outside = outside_multiplier != 1.0 or prevent_outside
        should_do_outside_later = (inst_or_cls.counts_as_inside or not inst_or_cls.supress_outside_if_modifier) and not prevent_outside
        for obj in object_manager.get_objects_with_filter_gen(inst_or_cls.whitelist_filter):
            if sim_level != obj.level:
                pass
            elif not inst_or_cls.blacklist_filter is not None or inst_or_cls.blacklist_filter.matches(obj):
                pass
            elif inst_or_cls.radius is not None:
                delta = obj.intended_position - sim_intended_postion
                if delta.magnitude() > inst_or_cls.radius:
                    pass
                elif not handle_outside or obj.is_in_sim_inventory(sim) or obj.is_outside:
                    if should_do_outside_later:
                        skipped.append(obj)
                        if inst_or_cls._passes_post_skip_tests(sim, obj):
                            should_do_outside_later = False
                            skipped.clear()
                            yield obj
                elif inst_or_cls._passes_post_skip_tests(sim, obj):
                    should_do_outside_later = False
                    skipped.clear()
                    yield obj
            elif not handle_outside or obj.is_in_sim_inventory(sim) or obj.is_outside:
                if should_do_outside_later:
                    skipped.append(obj)
                    if inst_or_cls._passes_post_skip_tests(sim, obj):
                        should_do_outside_later = False
                        skipped.clear()
                        yield obj
            elif inst_or_cls._passes_post_skip_tests(sim, obj):
                should_do_outside_later = False
                skipped.clear()
                yield obj
        for obj in skipped:
            if inst_or_cls._passes_post_skip_tests(sim, obj):
                yield obj

    @flexmethod
    def _passes_post_skip_tests(cls, inst, sim, obj):
        inst_or_cls = inst if inst is not None else cls
        if inst_or_cls.require_on_offlot_parity and sim.is_on_active_lot(tolerance=StatisticComponentGlobalTuning.DEFAULT_OFF_LOT_TOLERANCE) and not obj.is_on_active_lot(tolerance=StatisticComponentGlobalTuning.DEFAULT_OFF_LOT_TOLERANCE):
            return False
        if inst_or_cls.object_filter_test:
            resolver = event_testing.resolver.SingleActorAndObjectResolver(sim.sim_info, obj, source='AutonomousObjectTaggedPickerInteraction')
            result = inst_or_cls.object_filter_test.run_tests(resolver)
            if not result:
                return False
            elif not obj.is_connected(sim):
                return False
        elif not obj.is_connected(sim):
            return False
        return True
lock_instance_tunables(AutonomousObjectTaggedPickerInteraction, pre_add_autonomy_commodities=None, pre_run_autonomy_commodities=None, post_guaranteed_autonomy_commodities=None, post_run_autonomy_commodities=None, basic_content=None, outfit_change=None, outfit_priority=None, joinable=None, object_reservation_tests=TunableTestSet.DEFAULT_LIST, ignore_group_socials=False)
class ActorUrnstonePickerInteraction(ActorsUrnstonePickerMixin, ObjectPickerInteraction):
    pass

class PurchasePickerData:

    def __init__(self):
        self.inventory_owner_id_to_purchase_to = 0
        self.inventory_owner_id_to_purchase_from = 0
        self.mailmain_delivery = False
        self.items_to_purchase = defaultdict(set)
        self.use_obj_ids_in_response = False

    def add_definition_to_purchase(self, definition, custom_price=None, obj=None):
        self.items_to_purchase[(definition, custom_price)].add(obj)

class DefinitionsFromTags(HasTunableSingletonFactory, AutoFactoryInit):
    FACTORY_TUNABLES = {'filter_tags': OptionalTunable(description='\n            An optional filter that if enabled will filter out the allowed items\n            based on the filter.\n            ', tunable=TunableSet(description='\n                A list of category tags to to search to build object picker\n                list.\n                ', tunable=TunableEnumEntry(description='\n                    What tag to test for\n                    ', tunable_type=tag.Tag, default=tag.Tag.INVALID), minlength=1), disabled_name='all_definitions', enabled_name='specific_definitions')}

    def get_items_gen(self):
        yield from self._get_items_internal_gen()

    def _get_items_internal_gen(self):
        definition_manager = services.definition_manager()
        if self.filter_tags is None:
            yield from definition_manager.loaded_definitions
        else:
            yield from definition_manager.get_definitions_for_tags_gen(self.filter_tags)

    def has_choices(self, inst_or_cls, **kwargs):
        for _ in self._get_items_internal_gen():
            return True
        return False

    def __call__(self, inst_or_cls, purchase_picker_data, **kwargs):
        for obj in self._get_items_internal_gen():
            purchase_picker_data.add_definition_to_purchase(obj)

class DefinitionsExplicit(HasTunableSingletonFactory, AutoFactoryInit):
    FACTORY_TUNABLES = {'item_list': TunableSet(description='\n            The list of items available for purchase.\n            ', tunable=TunableReference(manager=services.definition_manager(), pack_safe=True), minlength=1)}

    def get_items_gen(self):
        yield from self._get_items_internal_gen()

    def _get_items_internal_gen(self):
        yield from self.item_list

    def has_choices(self, inst_or_cls, **kwargs):
        for _ in self._get_items_internal_gen():
            return True
        return False

    def __call__(self, inst_or_cls, purchase_picker_data, **kwargs):
        for obj in self._get_items_internal_gen():
            purchase_picker_data.add_definition_to_purchase(obj)

class DefinitionsRandom(HasTunableSingletonFactory, AutoFactoryInit):
    FACTORY_TUNABLES = {'item_list': TunableList(description='\n            The list of items available for purchase.\n            ', tunable=TunableTuple(description='\n                A weighted list of items to be available.\n                ', item=TunableReference(description='\n                    An item that is potentially available.\n                    ', manager=services.definition_manager(), pack_safe=True), weight=TunableRange(description='\n                    How likely this item to be picked.\n                    ', tunable_type=int, minimum=1, default=1)), minlength=1), 'items_avaiable': TunableRange(description='\n            The number of items available.\n            ', tunable_type=int, minimum=1, default=1)}

    def _get_items_internal_gen(self):
        now = services.time_service().sim_now
        rand = random.Random(int(now.absolute_days()))
        possible_items = [(item.weight, item.item) for item in self.item_list]
        for _ in range(self.items_avaiable):
            chosen_item = pop_weighted(possible_items, random=rand)
            yield chosen_item

    def has_choices(self, inst_or_cls, **kwargs):
        return True

    def __call__(self, inst_or_cls, purchase_picker_data, **kwargs):
        for obj in self._get_items_internal_gen():
            purchase_picker_data.add_definition_to_purchase(obj)

class DefinitionsTested(HasTunableSingletonFactory, AutoFactoryInit):
    FACTORY_TUNABLES = {'item_list': TunableList(description='\n            The list of items available for purchase.\n            ', tunable=TunableTuple(description='\n                A pair of items and tests to run in order to see if those items would be available.\n                ', item=TunableReference(description='\n                    An item that is potentially available.\n                    ', manager=services.definition_manager(), pack_safe=True), tests=TunableTestSet(description='\n                    A set of tests to run to see if this item would be available.\n                    ')), minlength=1)}

    def _get_items_internal_gen(self, inst_or_cls, **interaction_kwargs):
        resolver = inst_or_cls.get_resolver(**interaction_kwargs)
        for potential_item in self.item_list:
            if potential_item.tests.run_tests(resolver):
                yield potential_item.item

    def has_choices(self, inst_or_cls, **interaction_kwargs):
        for _ in self._get_items_internal_gen(inst_or_cls, **interaction_kwargs):
            return True
        return False

    def __call__(self, inst_or_cls, purchase_picker_data, **interaction_kwargs):
        for obj in self._get_items_internal_gen(inst_or_cls, **interaction_kwargs):
            purchase_picker_data.add_definition_to_purchase(obj)
OBJ_REQUIREMENT_PURCHASABLE = 0OBJ_REQUIREMENT_STATE_THRESHOLD = 1PURCHASE_BY_DEFINITION = 0PURCHASE_BY_ITEM_COPY = 1
class PriceOption(enum.Int):
    USE_CURRENT_VALUE = 0
    USE_RETAIL_VALUE = 1

class InventoryItems(HasTunableSingletonFactory, AutoFactoryInit):
    FACTORY_TUNABLES = {'participant_type': TunableEnumEntry(description="\n            The participant type who's inventory will be used to list objects.\n            ", tunable_type=ParticipantType, default=ParticipantType.Object), 'object_requirement': OptionalTunable(description='\n            The requirements the object must meet to be added to the picker. If\n            this is disabled, all inventory items will be displayed.\n            ', tunable=TunableVariant(description='\n                The requirements for being added to the picker.\n                ', purchasable=TunableTuple(description='\n                    Only show items that are in the Purchasable Objects list for\n                    the targets inventory component.\n                    ', locked_args={'requirement_type': OBJ_REQUIREMENT_PURCHASABLE}), state_threshold=TunableTuple(description='\n                    Only show items that meet this state threshold.\n                    ', threshold=TunableThreshold(description='\n                        The state threshold the object must meet.\n                        ', value=TunableReference(manager=services.get_instance_manager(sims4.resources.Types.OBJECT_STATE), class_restrictions='ObjectStateValue')), locked_args={'requirement_type': OBJ_REQUIREMENT_STATE_THRESHOLD}))), 'purchase_option': TunableVariant(description='\n            Options for how we we want to purchase the items we found in the\n            inventory.\n            ', by_definition=TunableTuple(description="\n                Purchase the item by the definition id.  A new item will be\n                generated using the object's definition.  This will just use the\n                catalog price of the item to purchase it.\n                ", locked_args={'purchase_type': PURCHASE_BY_DEFINITION}), by_copy=TunableTuple(description='\n                Purchase the item by actually copying one of the instances of\n                the items in the inventory.  Objects will be grouped by price\n                within the picker.\n                ', price_option=TunableEnumEntry(description='\n                    The option for determining the price of the item.\n                    ', tunable_type=PriceOption, default=PriceOption.USE_CURRENT_VALUE), locked_args={'purchase_type': PURCHASE_BY_ITEM_COPY}), default='by_definition')}

    def _get_items_internal_gen(self, inst_or_cls, **interaction_kwargs):
        participant = inst_or_cls.get_participant(participant_type=self.participant_type, **interaction_kwargs)
        inventory_component = participant.inventory_component
        if inventory_component is not None:
            if self.object_requirement is None:
                yield from inventory_component
            elif self.object_requirement.requirement_type == OBJ_REQUIREMENT_PURCHASABLE:
                yield from inventory_component.purchasable_objects.objects
            elif self.object_requirement.requirement_type == OBJ_REQUIREMENT_STATE_THRESHOLD:
                desired_state = self.object_requirement.threshold.value.state
                for obj in inventory_component:
                    if obj.has_state(desired_state) and self.object_requirement.threshold.compare_value(obj.get_state(desired_state)):
                        yield obj

    def has_choices(self, inst_or_cls, **kwargs):
        for _ in self._get_items_internal_gen(inst_or_cls, **kwargs):
            return True
        return False

    def __call__(self, inst_or_cls, purchase_picker_data, **interaction_kwargs):
        objects_to_purchase = tuple(self._get_items_internal_gen(inst_or_cls, **interaction_kwargs))
        if self.purchase_option.purchase_type == PURCHASE_BY_DEFINITION:
            for obj in objects_to_purchase:
                purchase_picker_data.add_definition_to_purchase(obj.definition)
        elif self.purchase_option.purchase_type == PURCHASE_BY_ITEM_COPY:
            participant = inst_or_cls.get_participant(participant_type=self.participant_type, **interaction_kwargs)
            purchase_picker_data.inventory_owner_id_to_purchase_from = participant.id
            purchase_picker_data.use_obj_ids_in_response = True
            for obj in objects_to_purchase:
                if self.purchase_option.price_option == PriceOption.USE_CURRENT_VALUE:
                    price = int(obj.current_value)
                elif self.purchase_option.price_option == PriceOption.USE_RETAIL_VALUE:
                    price = int(obj.retail_component.get_sell_price())
                else:
                    logger.error('Trying to add items to the purchase picker with invalid price option.')
                    break
                purchase_picker_data.add_definition_to_purchase(obj.definition, custom_price=price, obj=obj)
        else:
            logger.error('Trying to fill purchase picker from inventory with invalid purchase option.', owner='jjacobson')
            return

class ParticipantInventoryCount(TunableFactory):

    @staticmethod
    def factory(interaction, definition, participant_type=ParticipantType.Object):
        participant = interaction.get_participant(participant_type)
        inventory_component = participant.inventory_component
        if inventory_component is None:
            return 0
        return inventory_component.get_count(definition)

    FACTORY_TYPE = factory

    def __init__(self, *args, **kwargs):
        super().__init__(participant_type=TunableEnumEntry(description="\n                The participant type who's inventory will be used to count the\n                number of objects owned of a specific definition.\n                ", tunable_type=ParticipantType, default=ParticipantType.Object), **kwargs)

class InventoryTypeCount(TunableFactory):

    @staticmethod
    def factory(_, definition, inventory_type=InventoryType.UNDEFINED):
        inventories = services.active_lot().get_object_inventories(inventory_type)
        return sum(inventory.get_count(definition) for inventory in inventories)

    FACTORY_TYPE = factory

    def __init__(self, *args, **kwargs):
        super().__init__(inventory_type=TunableEnumEntry(description='\n                The type of inventory that is used to count the number of\n                objects owned of a specific definition.\n                ', tunable_type=InventoryType, default=InventoryType.UNDEFINED), **kwargs)

class PurchaseToInventory(TunableFactory):

    @staticmethod
    def factory(interaction, purchase_picker_data, participant_type=ParticipantType.Object):
        participant = interaction.get_participant(participant_type)
        purchase_picker_data.inventory_owner_id_to_purchase_to = participant.id

    FACTORY_TYPE = factory

    def __init__(self, *args, **kwargs):
        super().__init__(participant_type=TunableEnumEntry(description="\n                The participant who's inventory we will put the purchased items\n                into.\n                ", tunable_type=ParticipantType, default=ParticipantType.Object), **kwargs)

class MailmanDelivery(TunableFactory):

    @staticmethod
    def factory(_, purchase_picker_data):
        purchase_picker_data.mailmain_delivery = True

    FACTORY_TYPE = factory

class PurchasePickerInteraction(PickerSuperInteraction):
    INSTANCE_TUNABLES = {'purchase_list_option': TunableList(description='\n            A list of methods that will be used to generate the list of objects that are available in the picker.\n            ', tunable=TunableVariant(description='\n                The method that will be used to generate the list of objects that\n                will populate the picker.\n                ', all_items=DefinitionsFromTags.TunableFactory(description='\n                    Look through all the items that are possible to purchase.\n                    \n                    This should be accompanied with specific filtering tags in\n                    Object Populate Filter to get a good result.\n                    '), specific_items=DefinitionsExplicit.TunableFactory(description='\n                    A list of specific items that will be purchasable through this\n                    dialog.\n                    '), inventory_items=InventoryItems.TunableFactory(description='\n                    Looks at the objects that are in the inventory of the desired\n                    participant and returns them based on some criteria.\n                    '), random_items=DefinitionsRandom.TunableFactory(description='\n                    Randomly selects items based on a weighted list.\n                    '), tested_items=DefinitionsTested.TunableFactory(description='\n                    Test items that are able to be displayed within the picker.\n                    '), default='all_items'), tuning_group=GroupNames.PICKERTUNING), 'purchase_notification': OptionalTunable(description='\n            If enabled, a notification is displayed should the purchase picker\n            dialog be accepted.\n            ', tunable=TunableUiDialogNotificationSnippet(description='\n                The notification to show when the purchase picker dialog is\n                accepted.\n                '), tuning_group=GroupNames.PICKERTUNING), 'price_multiplier': TunableMultiplier.TunableFactory(description='\n            Tested multipliers to apply to the price of the item.\n            ', tuning_group=GroupNames.PICKERTUNING, multiplier_options={'use_tooltip': True}), 'object_count_option': OptionalTunable(description='\n            If enabled then we will display a count next to each item of the\n            number owned.\n            ', tunable=TunableList(description='\n                A list of methods to used to count the number of instances of\n                specific objects.\n                ', tunable=TunableVariant(description='\n                    The method that will be used to determine the object count\n                    that is displayed in the UI next to each item.\n                    ', participant_inventory_count=ParticipantInventoryCount(description="\n                        We will count through the number of objects that are in\n                        the target's inventory and display that as the number\n                        owned in the UI.\n                        "), inventory_type_count=InventoryTypeCount(description='\n                        We will count through the number of objects that are in\n                        a specific inventory type (for example fridges) and\n                        display that as the number owned in the UI.\n                        '), default='participant_inventory_count')), tuning_group=GroupNames.PICKERTUNING), 'delivery_method': TunableVariant(description='\n            Where the objects purchased will be delivered.\n            ', purchase_to_inventory=PurchaseToInventory(description="\n                Purchase the objects directly into a participant's inventory.\n                "), mailman_delivery=MailmanDelivery(description='\n                Deliver the objects by the mailman.\n                '), default='purchase_to_inventory', tuning_group=GroupNames.PICKERTUNING), 'show_descriptions': Tunable(description='\n            If True then we will show descriptions of the objects in the picker.\n            ', tunable_type=bool, default=True, tuning_group=GroupNames.PICKERTUNING), 'show_discount': Tunable(description="\n            If enabled, the UI for the purchase picker will show a\n            strikethrough of the original price if it's different than the\n            final price.\n            ", tunable_type=bool, default=False, tuning_group=GroupNames.PICKERTUNING)}

    def _run_interaction_gen(self, timeline):
        self._show_picker_dialog(self.sim)
        return True

    @classmethod
    def has_valid_choice(cls, target, context, **kwargs):
        for purchase_method in cls.purchase_list_option:
            if purchase_method.has_choices(cls, target=target, context=context, sim=context.sim, **kwargs):
                return True
        return False

    def _setup_dialog(self, dialog, **kwargs):
        purchase_picker_data = PurchasePickerData()
        self.delivery_method(self, purchase_picker_data)
        for purchase_method in self.purchase_list_option:
            purchase_method(self, purchase_picker_data)
        dialog.inventory_object_id = purchase_picker_data.inventory_owner_id_to_purchase_from
        dialog.object_id = purchase_picker_data.inventory_owner_id_to_purchase_to
        dialog.mailman_purchase = purchase_picker_data.mailmain_delivery
        dialog.purchase_by_object_ids = purchase_picker_data.use_obj_ids_in_response
        dialog.show_description = self.show_descriptions
        resolver = self.get_resolver()
        (multiplier, tooltip) = self.price_multiplier.get_multiplier_and_tooltip(resolver)
        for ((definition, custom_price), objects) in purchase_picker_data.items_to_purchase.items():
            count = self._get_count_option(definition)
            if multiplier != 1:
                original_price = custom_price if custom_price is not None else definition.price
                custom_price = int(original_price*multiplier)
                tooltip = None
            row = PurchasePickerRow(def_id=definition.id, num_owned=count, tags=definition.build_buy_tags, custom_price=custom_price, objects=objects, row_tooltip=tooltip, show_discount=self.show_discount)
            dialog.add_row(row)

    def _get_count_option(self, item):
        if self.object_count_option is None:
            return 0
        return sum(count_method(self, item) for count_method in self.object_count_option)

    def _on_picker_selected(self, dialog):
        if dialog.accepted and self.purchase_notification is not None:
            notification_dialog = self.purchase_notification(self.sim, resolver=self.get_resolver())
            notification_dialog.show_dialog()
