import collectionsimport itertoolsimport operatorimport weakreffrom protocolbuffers import SimObjectAttributes_pb2 as protocolsfrom animation.awareness.awareness_tuning import AwarenessSourceRequestfrom animation.focus.focus_score import TunableFocusScoreVariantfrom animation.object_animation import ObjectPosefrom animation.tunable_animation_overrides import TunableAnimationObjectOverridesfrom audio.primitive import TunablePlayAudiofrom autonomy.autonomy_modifier import TunableAutonomyModifier, AutonomyModifierfrom broadcasters.broadcaster_request import BroadcasterRequestfrom broadcasters.environment_score.environment_score_state import EnvironmentScoreStatefrom crafting.change_painting_state import ChangePaintingStatefrom drama_scheduler.drama_node_tests import FestivalRunningTest, NextFestivalTestfrom element_utils import CleanupType, build_elementfrom element_utils import build_critical_section_with_finallyfrom event_testing import test_eventsfrom event_testing.resolver import SingleObjectResolver, DoubleObjectResolverfrom event_testing.tests import TunableTestSetfrom graph_algos import topological_sortfrom interactions import ParticipantTypefrom interactions.base.picker_tunables import TunableBuffWeightMultipliersfrom interactions.utils.audio import ApplyAudioEffectfrom interactions.utils.display_mixin import get_display_mixinfrom interactions.utils.periodic_loot_op import PeriodicLootOperationfrom interactions.utils.success_chance import SuccessChancefrom interactions.utils.tunable_icon import TunableIconfrom objects import TunableVisibilityState, TunableGeometryState, TunableMaterialState, TunableMaterialVariant, PaintingState, TunableModelSuiteStateIndexfrom objects.client_object_mixin import ClientObjectMixinfrom objects.collection_manager import ObjectCollectionDatafrom objects.components import Component, componentmethod, componentmethod_with_fallback, ComponentPriorityfrom objects.components.needs_state_value import NeedsStateValuefrom objects.components.state_change import StateChangefrom objects.components.types import STATE_COMPONENT, CANVAS_COMPONENT, FLOWING_PUDDLE_COMPONENT, VIDEO_COMPONENT, LIGHTING_COMPONENT, FOOTPRINT_COMPONENT, MANNEQUIN_COMPONENT, FOCUS_COMPONENTfrom objects.components.video import RESOURCE_TYPE_VP6from objects.fire.set_fire_state import SetFireStatefrom objects.glow import Glowfrom objects.helpers.user_footprint_helper import UserFootprintHelperfrom objects.hovertip import TooltipFieldsCompletefrom objects.mixins import SuperAffordanceProviderMixinfrom objects.object_enums import ResetReasonfrom objects.slots import SlotTypefrom objects.visibility.visibility_enums import VisibilityFlagsfrom routing import SurfaceTypefrom routing.route_events.route_event_provider import RouteEventProviderRequestfrom routing.walkstyle.walkstyle_request import WalkStyleRequestfrom server.live_drag_operations import LiveDragStateOperationfrom services import get_instance_managerfrom sims import household_utilitiesfrom sims.household_utilities.utility_operations import UtilityModifierStatefrom sims.suntan.suntan_tuning import ChangeTanLevelfrom sims4.callback_utils import CallableListfrom sims4.localization import TunableLocalizedStringfrom sims4.math import MAX_FLOATfrom sims4.random import random_chance, weighted_random_itemfrom sims4.tuning.instances import TunedInstanceMetaclassfrom sims4.tuning.tunable import HasTunableReference, TunableEnumEntry, TunableVariant, Tunable, OptionalTunable, TunableTuple, TunableMapping, TunableReference, TunableInterval, TunableList, TunableResourceKey, HasTunableFactory, TunableRange, TunableFactory, HasTunableSingletonFactory, AutoFactoryInit, TunableColor, TunableSimMinute, TunablePercent, TunableSet, TunableEnumFlags, TunablePackSafeReferencefrom sims4.tuning.tunable_hash import TunableStringHash32from sims4.utils import classproperty, Result, strformatterfrom singletons import DEFAULT, UNSETfrom situations.situation_guest_list import SituationGuestListfrom snippets import TunableColorSnippetfrom statistics.statistic_ops import ObjectStatisticChangeOp, TunableStatisticChange, StatisticOperationfrom tunable_utils.tunable_model import TunableModelOrDefaultfrom vfx import PlayMultipleEffects, PlayEffectfrom vfx.vfx_state import PlayEffectStateimport alarmsimport cachesimport clockimport enumimport event_testingimport gsi_handlersimport objectsimport placementimport servicesimport sims4.loglogger = sims4.log.Logger('StateComponent')
def get_supported_state(definition):
    state_component_tuning = definition.cls._components.state
    if state_component_tuning is None:
        return
    supported_states = set()
    tuning_states = set()
    for state in state_component_tuning.states:
        tuning_states.add(state.default_value)
    for tuned_state_value in tuning_states:
        if hasattr(tuned_state_value, 'state'):
            supported_states.add(tuned_state_value.state)
        else:
            state_from_list = None
            for weighted_state in tuned_state_value:
                state_value = weighted_state.state
                if state_from_list is None:
                    state_from_list = state_value.state
                    supported_states.add(state_value.state)
                elif state_from_list != state_value.state:
                    logger.error("Random state value {} on object {}, does'nt match the other states inside the random list.", state_value, definition, owner='camilogarcia')
    return supported_states

class OptionalTunableClientStateChangeItem(OptionalTunable):

    def __init__(self, tunable, **kwargs):
        super().__init__(disabled_value=UNSET, disabled_name='leave_unchanged', enabled_name='apply_new_value', tunable=tunable, **kwargs)

class OptionalTunableClientStateChangeItemWithDisable(OptionalTunable):

    def __init__(self, tunable, tunable_disabled_name=None, tunable_enabled_name=None, **kwargs):
        if tunable_disabled_name is None:
            tunable_disabled_name = 'No {}'.format(tunable)
        if tunable_enabled_name is None:
            tunable_enabled_name = str(tunable)
        super().__init__(disabled_value=UNSET, disabled_name='leave_unchanged', enabled_name='apply_new_value', tunable=OptionalTunable(tunable=tunable, disabled_name=tunable_disabled_name, enabled_name=tunable_enabled_name), **kwargs)

class StatisticModifierList(HasTunableFactory, AutoFactoryInit):
    FACTORY_TUNABLES = {'autonomy_modifiers': TunableList(description='\n            List of possible Modifiers that may happen when a statistic gets \n            hit, this will modify the objects statistics behavior.\n            ', tunable=TunableAutonomyModifier(locked_args={'relationship_multipliers': None})), 'periodic_statistic_change': TunableTuple(description='\n            The stat change apply on the target within the state value.\n            ', interval=TunableSimMinute(description='\n            The number of sim minutes in between each application of the tuned operations.\n            Note: This operation sets an alarm, which has performance implications,\n            so please see a GPE before setting to a number lower than 5 mins.\n            ', default=60), operations=TunableList(tunable=ObjectStatisticChangeOp.TunableFactory()))}

    def __init__(self, target, **kwargs):
        super().__init__(**kwargs)
        self.target = target
        self.handles = []
        self._alarm_handle = None
        self._operations_on_alarm = []

    def start(self):
        self.target.add_statistic_component()
        for modifier in self.autonomy_modifiers:
            self.handles.append(self.target.add_statistic_modifier(modifier))
        self._start_statistic_gains()

    def stop(self, *_, **__):
        self.target.add_statistic_component()
        for handle in self.handles:
            self.target.remove_statistic_modifier(handle)
        self._end_statistic_gains()

    def _start_statistic_gains(self):
        periodic_mods = {}
        interval = self.periodic_statistic_change.interval
        operations = self.periodic_statistic_change.operations
        inv_interval = 1/interval
        if operations:
            for stat_op in operations:
                stat = stat_op.stat
                if stat is not None and stat.continuous:
                    if stat not in periodic_mods.keys():
                        periodic_mods[stat] = 0
                    mod_per_sec = stat_op.get_value()*inv_interval
                    periodic_mods[stat] += mod_per_sec
                else:
                    self._operations_on_alarm.append(stat_op)
        auto_mod = AutonomyModifier(statistic_modifiers=periodic_mods)
        handle = self.target.add_statistic_modifier(auto_mod)
        self.handles.append(handle)
        time_span = clock.interval_in_sim_minutes(interval)
        if self._operations_on_alarm:
            self._alarm_handle = alarms.add_alarm(self, time_span, self._do_gain, repeating=True)
        return True

    def _end_statistic_gains(self):
        if self._alarm_handle is not None:
            alarms.cancel_alarm(self._alarm_handle)
            self._alarm_handle = None

    def _do_gain(self, _):
        for statistic_op in self._operations_on_alarm:
            statistic_op.apply_to_object(self.target)

class LotStatisticModifierList(HasTunableFactory, AutoFactoryInit):
    FACTORY_TUNABLES = {'statistic_changes': TunableList(description='\n            statistic changes to apply to lot when state gets set\n            ', tunable=ObjectStatisticChangeOp.TunableFactory())}

    def __init__(self, target, **kwargs):
        super().__init__(**kwargs)
        self.target = target

    def start(self):
        current_zone = services.current_zone()
        lot = current_zone.lot
        lot.add_statistic_component()
        for statistic_op in self.statistic_changes:
            statistic_op.apply_to_object(lot)

    def stop(self, *_, **__):
        current_zone = services.current_zone()
        lot = current_zone.lot
        lot.add_statistic_component()
        for statistic_op in self.statistic_changes:
            statistic_op.remove_from_object(lot)

class StateSituationRequest(HasTunableFactory, AutoFactoryInit):
    FACTORY_TUNABLES = {'situations_to_create': TunableList(description='\n            A list of situations that will be created while the object is in\n            this state.\n            ', tunable=TunableTuple(situation=TunableReference(description='\n                    A situation that will be created when this state is set.\n                    ', manager=services.get_instance_manager(sims4.resources.Types.SITUATION)), invite_only=Tunable(description='\n                    If this situation should use an invite only guest list or\n                    not.\n                    ', tunable_type=bool, default=True)))}

    def __init__(self, target, **kwargs):
        super().__init__(**kwargs)
        self.target = target
        self._situation_ids = []

    def start(self):
        situation_manager = services.get_zone_situation_manager()
        if situation_manager is None:
            return
        for situation_info in self.situations_to_create:
            situation = situation_info.situation
            guest_list = situation.get_predefined_guest_list()
            if guest_list is None:
                guest_list = SituationGuestList(invite_only=situation_info.invite_only)
            situation_id = situation_manager.create_situation(situation_type=situation, guest_list=guest_list, user_facing=False)
            situation_manager.disable_save_to_situation_manager(situation_id)
            self._situation_ids.append(situation_id)

    def stop(self, *_, **__):
        situation_manager = services.get_zone_situation_manager()
        if situation_manager is None:
            return
        for situation_id in self._situation_ids:
            situation_manager.destroy_situation_by_id(situation_id)

class UiMetadataList(HasTunableFactory, AutoFactoryInit, NeedsStateValue):
    FACTORY_TUNABLES = {'data': TunableMapping(description='\n        ', key_type=str, value_type=TunableVariant(other_value=TunableVariant(default='integral', boolean=Tunable(bool, False), string=TunableLocalizedString(), integral=Tunable(int, 0), icon=TunableIcon(), color=TunableColor()), state_value=TunableVariant(default='value', locked_args={'display_name': 'display_name', 'display_description': 'display_description', 'icon': 'icon', 'value': 'value'})))}

    def __init__(self, target, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.target = target
        self.handles = []

    def start(self):
        if self.target.state_component.hovertip_requested:
            for (name, value) in self.data.items():
                if isinstance(value, str):
                    value = getattr(self.state_value, value)
                handle = self.target.add_ui_metadata(name, value)
                self.handles.append(handle)
            self.target.update_ui_metadata()

    def stop(self, *_, **__):
        if self.target.state_component.hovertip_requested:
            while self.handles:
                self.target.remove_ui_metadata(self.handles.pop())
            self.target.update_ui_metadata()

class ObjectReplacementOperation(HasTunableSingletonFactory, AutoFactoryInit):
    FACTORY_TUNABLES = {'new_object': OptionalTunable(description="\n        A reference to the type of object which will be created in this\n        object's place.\n        ", tunable=TunableReference(manager=services.definition_manager())), 'destroy_original_object': Tunable(description='\n        If checked, the original object will be destroyed.  If\n        unchecked, the original object will be left around.\n        ', tunable_type=bool, default=True), 'transfer_sim_ownership': Tunable(description='\n        If checked, when ownership is enabled on both objects, \n        transfer the sim that is the owner to the new object.\n        ', tunable_type=bool, default=False)}
    RESULT_REPLACEMENT_FAILED = Result(True, 'Replacement failed.')
    RESULT_OBJECT_DESTROYED = Result(False, 'Object destroyed.')

    def __call__(self, target):
        if self.new_object is None:
            if not self.destroy_original_object:
                return self.RESULT_REPLACEMENT_FAILED
            if target.in_use:
                target.transient = True
                return self.RESULT_OBJECT_DESTROYED
            target.destroy(source=self, cause='Object replacement state operation, new_object is None', fade_duration=ClientObjectMixin.FADE_DURATION)
            return self.RESULT_OBJECT_DESTROYED
        new_location = None
        if target.parent_slot.is_valid_for_placement(definition=self.new_object, objects_to_ignore=(target,)):
            new_location = target.location
        if target.parent_slot is not None and new_location is None:
            if target.location.routing_surface is None:
                logger.error('Object {} in location {} is creating an object with an invalid routing surface', target, target.location, owner='camilogarcia')
                return self.RESULT_REPLACEMENT_FAILED
            search_flags = placement.FGLSearchFlag.STAY_IN_CONNECTED_CONNECTIVITY_GROUP | placement.FGLSearchFlag.CALCULATE_RESULT_TERRAIN_HEIGHTS | placement.FGLSearchFlag.DONE_ON_MAX_RESULTS | placement.FGLSearchFlag.ALLOW_GOALS_IN_SIM_POSITIONS
            starting_location = placement.create_starting_location(location=target.location)
            fgl_context = placement.create_fgl_context_for_object(starting_location, self.new_object, search_flags=search_flags, ignored_object_ids=(target.id,))
            (new_position, new_orientation) = placement.find_good_location(fgl_context)
            if new_position is None or new_orientation is None:
                logger.warn('No good location found for the object {} attempting to replace object {}.', self.new_object, target, owner='tastle')
                return self.RESULT_REPLACEMENT_FAILED
            new_location = sims4.math.Location(sims4.math.Transform(new_position, new_orientation), target.routing_surface)
        created_obj = objects.system.create_object(self.new_object)
        if created_obj is None:
            logger.error('State change attempted to replace object {} with a new object {}, but failed to create the new object.', target, self.definition, owner='tastle')
            return self.RESULT_REPLACEMENT_FAILED
        household_owner_id = target.get_household_owner_id()
        if household_owner_id:
            created_obj.set_household_owner_id(household_owner_id)
        if self.transfer_sim_ownership and target.ownable_component is not None and created_obj.ownable_component is not None:
            sim_owner_id = target.ownable_component.get_sim_owner_id()
            if sim_owner_id is not None:
                created_obj.ownable_component.update_sim_ownership(sim_owner_id)
                if created_obj.tooltip_component is not None:
                    created_obj.update_object_tooltip()
        created_obj.set_location(new_location)
        if self.destroy_original_object:
            target.remove_from_client()
            if target.self_or_part_in_use:
                target.transient = True
            else:
                target.destroy(source=self, cause='Object replacement state operation')
        return self.RESULT_OBJECT_DESTROYED

class GeometryStateOverrideOperation(HasTunableFactory, AutoFactoryInit):
    FACTORY_TUNABLES = {'geometry_state_overrides': TunableList(description='\n            A list of geometry state override operations to apply.\n            ', tunable=TunableTuple(original_geometry_state=Tunable(description='\n                    The geometry state that is to be overridden.\n                    ', tunable_type=str, default=''), override_geometry_state=Tunable(description='\n                    The geometry state to override original_geometry_state with.\n                    ', tunable_type=str, default='')))}

    def __init__(self, target, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.target = target

    def start(self):
        for geometry_state_override in self.geometry_state_overrides:
            self.target.add_geometry_state_override(geometry_state_override.original_geometry_state, geometry_state_override.override_geometry_state)

    def stop(self, *_, **__):
        for geometry_state_override in self.geometry_state_overrides:
            self.target.remove_geometry_state_override(geometry_state_override.original_geometry_state)

class ToggleFootprintOperation(HasTunableFactory, AutoFactoryInit):
    FACTORY_TUNABLES = {'toggles': TunableList(description='\n            List of footprints to toggle.\n            ', tunable=TunableTuple(enable=Tunable(description='\n                    If checked, we turn on the tuned footprint when entering\n                    the state changes. If not checked, we turn off the tuned\n                    footprint when entering the state.\n                    ', tunable_type=bool, default=False), footprint_hash=TunableStringHash32(description='\n                    Name of the footprint to toggle.\n                    '), push_sims=Tunable(description='\n                    If enabled, Sims will be pushed from this footprint when\n                    it is turned on.\n                    ', tunable_type=bool, default=True)))}

    def __init__(self, target, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.target = target
        self.footprints_enabled = False

    def start(self):
        footprint_component = self.target.get_component(FOOTPRINT_COMPONENT)
        if footprint_component is None:
            logger.error('Attempt to toggle a footprint on a target ({}) with no footprint component.', self.target, owner='nbaker')
            return
        if footprint_component.footprints_enabled:
            self.footprints_enabled = True
            enabled_footprints = set()
            for toggle in self.toggles:
                footprint_component.start_toggle_footprint(toggle.enable, toggle.footprint_hash)
                if toggle.enable and toggle.push_sims:
                    enabled_footprints.add(toggle.footprint_hash)
            self._try_push_sims(enabled_footprints)

    def stop(self, *_, **__):
        if self.footprints_enabled:
            footprint_component = self.target.get_component(FOOTPRINT_COMPONENT)
            if footprint_component is None:
                logger.error('Attempt to toggle a footprint on a target ({}) with no footprint component.', self.target, owner='nbaker')
                return
            enabled_footprints = set()
            for toggle in self.toggles:
                footprint_component.stop_toggle_footprint(toggle.enable, toggle.footprint_hash)
                if toggle.enable or toggle.push_sims:
                    enabled_footprints.add(toggle.footprint_hash)
            self._try_push_sims(enabled_footprints)

    def _try_push_sims(self, footprint_name_hashes):
        if not footprint_name_hashes:
            return
        compound_polygon = self.target.get_polygon_from_footprint_name_hashes(footprint_name_hashes)
        if compound_polygon is not None:
            UserFootprintHelper.force_move_sims_in_polygon(compound_polygon, self.target.routing_surface)

class ValueIncreaseFactory(AutoFactoryInit, HasTunableFactory):
    FACTORY_TUNABLES = {'apply_depreciation': Tunable(description='\n                Whether or not to apply initial depreciation when\n                this value change is applied.\n                \n                Example: if you are replacing an object that is\n                burned we want to make the value worth the full\n                value of the object again, but you also need to\n                apply the initial depreciation as if it was \n                purchased from buy mode.\n                ', tunable_type=bool, default=False)}

    def apply_new_value(self, target, value_change):
        target.state_component.state_based_value_mod += value_change

    def restore_value(self, target, value_change):
        target.state_component.state_based_value_mod -= value_change

class ValueDecreaseFactory(AutoFactoryInit, HasTunableFactory):
    FACTORY_TUNABLES = {'covered_by_insurance': Tunable(description="\n            If checked it means that the user will be awarded an insurance\n            payment for the value lost. Currently this only happens with\n            fire insurance and there is seperate tuning in the fire service\n            for how much of the reduction is awarded as part of the insurance.\n            \n            NOTE: There is a tunable percent of the value that get's tuned here\n            that actually gets added to the insurance tally. That tuning\n            exists on services.fire_service. The name of the tunable is\n            Fire Insurance Claim Percentage.                     \n            ", tunable_type=bool, default=True)}

    def apply_new_value(self, target, value_change):
        initial_value = target.current_value
        target.state_component.state_based_value_mod -= value_change
        if self.covered_by_insurance:
            fire_service = services.get_fire_service()
            if fire_service is not None:
                fire_service.increment_insurance_claim(initial_value - target.current_value, target)

    def restore_value(self, target, value_change):
        initial_value = target.current_value
        target.state_component.state_based_value_mod += value_change
        if self.covered_by_insurance:
            fire_service = services.get_fire_service()
            if fire_service is not None:
                fire_service.increment_insurance_claim(initial_value - target.current_value, target)

class ObjectValueChangeOperation(HasTunableFactory, AutoFactoryInit):
    FACTORY_TUNABLES = {'value_change_type': TunableVariant(decrease_value=ValueDecreaseFactory.TunableFactory(), increase_value=ValueIncreaseFactory.TunableFactory(), default='decrease_value'), 'change_percentage': TunablePercent(description='\n            A percentage of the catalog value to modify the current value of \n            the target. It will either decrease or increase the value of the \n            object based on the setting of reduce_value.\n            ', default=100)}

    def __init__(self, target, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._target = target

    def start(self):
        self._delta = self.value_change_type().apply_new_value(self._target, self.change_percentage)

    def stop(self, *_, **__):
        self.value_change_type().restore_value(self._target, self.change_percentage)

class StateComponentManagedDistributables:

    def __init__(self):
        self._distributables_map = {}
        self._client_state_suppressors = set()

    def cleanup(self):
        while self._distributables_map:
            (state, distributable) = self._distributables_map.popitem()
            logger.debug('Cleanup: {}', state)
            distributable.stop(immediate=True)

    def _can_apply_client_state(self, target, attr_name, state_owner):
        in_inventory = target.is_in_inventory()
        if in_inventory and attr_name in StateChangeOperation.INVENTORY_AFFECTED_DISTRIBUTABLES:
            forward_to_owner = target.inventoryitem_component.forward_client_state_change_to_inventory_owner
            if forward_to_owner:
                if attr_name not in forward_to_owner:
                    return False
                elif self._client_state_suppressors and state_owner not in self._client_state_suppressors:
                    return False
            else:
                return False
        elif self._client_state_suppressors and state_owner not in self._client_state_suppressors:
            return False
        return True

    def apply(self, target, attr_name, state, state_value, attr_value, immediate=False, post_load_distributable_only=False):
        state_owner = state.overridden_by or state
        distributable_key = (attr_name, state_owner)
        if distributable_key in self._distributables_map:
            self._distributables_map[distributable_key].stop(immediate=immediate)
            del self._distributables_map[distributable_key]
        if attr_value is not None:
            distributable = attr_value(target)
            logger.debug('    {} = {}', attr_name, distributable)
            if isinstance(distributable, Result):
                return distributable
            if isinstance(distributable, NeedsStateValue):
                distributable.set_distributable_manager(self)
                distributable.set_state_value(state_value)
            if self._can_apply_client_state(target, attr_name, state_owner):
                distributable.start()
            self._distributables_map[distributable_key] = distributable
        else:
            logger.debug('    {} = None', attr_name)

    def stop_inventory_distributables(self):
        for (distributable_key, distributable) in self._distributables_map.items():
            (attr_name, _) = distributable_key
            if attr_name in StateChangeOperation.INVENTORY_AFFECTED_DISTRIBUTABLES:
                distributable.stop(immediate=True)

    def restart_inventory_distributables(self):
        for (distributable_key, distributable) in self._distributables_map.items():
            (attr_name, _) = distributable_key
            if attr_name in StateChangeOperation.INVENTORY_AFFECTED_DISTRIBUTABLES:
                distributable.start()

    def add_client_state_suppressor(self, suppressor):
        if not self._client_state_suppressors:
            for (distributable_key, distributable) in self._distributables_map.items():
                (_, state_owner) = distributable_key
                if state_owner not in self._client_state_suppressors and state_owner is not suppressor:
                    distributable.stop(immediate=True)
        self._client_state_suppressors.add(suppressor)

    def remove_client_state_suppressor(self, suppressor):
        self._client_state_suppressors.discard(suppressor)
        if not self._client_state_suppressors:
            for distributable in self._distributables_map.values():
                distributable.start()

    @property
    def has_client_state_supressors(self):
        return bool(self._client_state_suppressors)

    def get_distributable(self, attr_name, state):
        distributable_key = (attr_name, state)
        if distributable_key in self._distributables_map:
            return self._distributables_map[distributable_key]

class StateChangeOperation(HasTunableSingletonFactory):
    FACTORY_TUNABLES = {StateChange.SET_FIRE: OptionalTunableClientStateChangeItem(tunable=SetFireState.TunableFactory()), StateChange.SITUATION: OptionalTunableClientStateChangeItem(description='\n            Create situations while this state is active.\n            ', tunable=StateSituationRequest.TunableFactory()), StateChange.PERIODIC_LOOT: OptionalTunableClientStateChangeItem(tunable=PeriodicLootOperation.TunableFactory()), StateChange.FOCUS_SCORE: OptionalTunableClientStateChangeItem(tunable=TunableFocusScoreVariant()), StateChange.LIVE_DRAG: OptionalTunableClientStateChangeItem(tunable=LiveDragStateOperation.TunableFactory()), StateChange.UTILITY_MODIFIERS: OptionalTunableClientStateChangeItem(tunable=UtilityModifierState.TunableFactory()), StateChange.MANNEQUIN_POSE: OptionalTunableClientStateChangeItem(tunable=ObjectPose.TunableReference()), StateChange.CHANGE_VALUE: OptionalTunable(disabled_value=UNSET, tunable=ObjectValueChangeOperation.TunableFactory()), StateChange.SCRATCHED: OptionalTunableClientStateChangeItem(description='\n            Change the state of this object appearing scratched.\n            ', tunable=Tunable(tunable_type=bool, default=True)), StateChange.TAN_LEVEL: OptionalTunableClientStateChangeItem(tunable=ChangeTanLevel.TunableFactory()), StateChange.GRUBBY: OptionalTunableClientStateChangeItem(tunable=Tunable(tunable_type=bool, default=True)), StateChange.SINGED: OptionalTunableClientStateChangeItem(tunable=Tunable(tunable_type=bool, default=True)), StateChange.LOT_MODIFIERS: OptionalTunableClientStateChangeItemWithDisable(tunable=LotStatisticModifierList.TunableFactory(), tunable_disabled_name='no_modifiers', tunable_enabled_name='apply_modifiers'), StateChange.LIGHT_MATERIAL_STATE: OptionalTunableClientStateChangeItem(description='\n            Override the material states to apply on the object when its light\n            is on or off.\n            ', tunable=TunableTuple(material_state_on=TunableVariant(description='\n                    If specified, override the material state for this light\n                    when the object is on.\n                    ', apply_new_value=Tunable(description='\n                        The material state for this light when the object is on.\n                        ', tunable_type=str, default='lightson'), locked_args={'set_to_default': DEFAULT, 'leave_unchanged': None}, default='leave_unchanged'), material_state_off=TunableVariant(description='\n                    If specified, override the material state for this light\n                    when the object is off.\n                    ', apply_new_value=Tunable(description='\n                        The material state for this light when the object is\n                        off.\n                        ', tunable_type=str, default='lightsoff'), locked_args={'set_to_default': DEFAULT, 'leave_unchanged': None}, default='leave_unchanged'))), StateChange.LIGHT_DIMMER_STATE: OptionalTunableClientStateChangeItem(tunable=TunableRange(float, 0, 0, 1, description='A dimmer value to apply')), StateChange.UI_METADATA: OptionalTunableClientStateChangeItem(tunable=UiMetadataList.TunableFactory()), StateChange.TOGGLE_FOOTPRINT: OptionalTunableClientStateChangeItem(tunable=ToggleFootprintOperation.TunableFactory()), StateChange.REPLACE_OBJECT: OptionalTunable(disabled_value=UNSET, tunable=ObjectReplacementOperation.TunableFactory()), StateChange.WALKSTYLE: OptionalTunableClientStateChangeItem(tunable=OptionalTunable(tunable=WalkStyleRequest.TunableFactory(), disabled_name='no_request', enabled_name='request_walkstyle')), StateChange.ROUTE_EVENT: OptionalTunableClientStateChangeItem(tunable=OptionalTunable(tunable=RouteEventProviderRequest.TunableFactory(locked_args={'participant': None}))), StateChange.BROADCASTER: OptionalTunableClientStateChangeItem(tunable=OptionalTunable(tunable=BroadcasterRequest.TunableFactory(locked_args={'participant': None, 'offset_time': None}), disabled_name='no_broadcaster', enabled_name='start_broadcaster')), StateChange.AWARENESS: OptionalTunableClientStateChangeItemWithDisable(tunable=AwarenessSourceRequest.TunableFactory(), tunable_disabled_name='no_awareness', tunable_enabled_name='start_awareness'), StateChange.AUTONOMY_MODIFIERS: OptionalTunableClientStateChangeItemWithDisable(tunable=StatisticModifierList.TunableFactory(), tunable_disabled_name='no_statistic_to_apply', tunable_enabled_name='apply_statistic_modifiers'), 'transient': OptionalTunableClientStateChangeItem(tunable=Tunable(bool, False, description='This is what the objects transient value is set to')), StateChange.VIDEO_STATE_LOOPING: OptionalTunableClientStateChangeItemWithDisable(tunable=TunableResourceKey(None, resource_types=[sims4.resources.Types.PLAYLIST]), tunable_disabled_name='no_video', tunable_enabled_name='start_video'), StateChange.VIDEO_STATE: OptionalTunableClientStateChangeItem(tunable=OptionalTunable(disabled_name='no_video', enabled_name='start_video', tunable=TunableTuple(description='\n                    List of clip names and append behavior.\n                    ', clip_list=TunableList(TunableResourceKey(None, resource_types=[RESOURCE_TYPE_VP6])), append_clip=Tunable(description='\n                        If enabled clip list will be appended to previous \n                        playing clip instead of interrupting the existing \n                        playlist.\n                        This should be tuned when the clips should have a \n                        smoother transition like a credits scene on a movie.\n                        ', tunable_type=bool, default=False), loop_last=Tunable(description="\n                        If enabled, the clip will loop. Otherwise, it's played\n                        once and stop on last frame.\n                        ", tunable_type=bool, default=True)))), StateChange.AUDIO_EFFECT_STATE: OptionalTunableClientStateChangeItemWithDisable(description='\n            A way to apply An audio effect (.effectx) to the object when state changes\n            ', tunable=ApplyAudioEffect.TunableFactory(), tunable_disabled_name='no_audio_effect', tunable_enabled_name='start_audio_effect'), StateChange.AUDIO_STATE: OptionalTunableClientStateChangeItemWithDisable(tunable=TunablePlayAudio(description='An audio state to apply'), tunable_disabled_name='no_audio', tunable_enabled_name='start_audio'), StateChange.GLOW: OptionalTunableClientStateChangeItemWithDisable(tunable=Glow.TunableFactory(), tunable_disabled_name='no_glow', tunable_enabled_name='start_glow'), StateChange.VFX_STATE: OptionalTunableClientStateChangeItem(description='\n            Define a visual effect state on any visual effects controlled by\n            this state.\n            ', tunable=PlayEffectState.TunableFactory()), StateChange.VFX: OptionalTunableClientStateChangeItemWithDisable(description='\n            Play one or more visual effects.\n            ', tunable=TunableVariant(description='\n                Define the type of visual effect to play.\n                ', single_effect=PlayEffect.TunableFactory(), multiple_effects=PlayMultipleEffects.TunableFactory(), default='single_effect'), tunable_disabled_name='no_vfx', tunable_enabled_name='start_vfx'), StateChange.FLOWING_PUDDLE_ENABLED: OptionalTunableClientStateChangeItem(tunable=Tunable(bool, False, description='If True, this object will start spawning puddles based on its PuddleSpawningComponentTuning.')), StateChange.PAINTING_STATE: OptionalTunableClientStateChangeItem(description='\n            Change the entire painting state.\n            ', tunable=ChangePaintingState.TunableFactory()), StateChange.PAINTING_REVEAL_LEVEL: OptionalTunableClientStateChangeItem(tunable=TunableRange(description='\n                A painting reveal level to apply.  Smaller values show less of\n                the final painting.  The maximum value fully reveals the\n                painting.\n                ', tunable_type=int, default=PaintingState.REVEAL_LEVEL_MIN, minimum=PaintingState.REVEAL_LEVEL_MIN, maximum=PaintingState.REVEAL_LEVEL_MAX)), StateChange.ENVIRONMENT_SCORE: OptionalTunableClientStateChangeItem(tunable=EnvironmentScoreState.TunableFactory()), 'multicolor': OptionalTunableClientStateChangeItem(tunable=TunableList(description='\n                List of colors to be applied to the object. \n                Currently only 3 colors are supported by the multicolor shader\n                and the order of these matter, so apply in the same order\n                as the layers are setup (this can been seen in medator or \n                contact your modeler).\n                If tuning RGB values, the Alpha will be ignored.\n                ', tunable=TunableColorSnippet(description='\n                    Color to be applied. \n                    '), maxlength=3)), 'pregnancy_progress': OptionalTunableClientStateChangeItem(tunable=TunableRange(float, 0, 0, 1, description='A pregnancy progress value to apply')), 'material_variant': OptionalTunableClientStateChangeItem(tunable=TunableMaterialVariant('materialVariantName', description='A material variant to apply')), 'model': OptionalTunableClientStateChangeItem(tunable=TunableModelOrDefault(description='A model state to apply')), 'material_state': OptionalTunableClientStateChangeItem(tunable=TunableMaterialState(description='A material state to apply')), StateChange.GEOMETRY_STATE_OVERRIDE: OptionalTunableClientStateChangeItem(description='\n            Apply a geometry state override to the object.\n            ', tunable=GeometryStateOverrideOperation.TunableFactory()), 'geometry_state': OptionalTunableClientStateChangeItem(tunable=TunableGeometryState(description='A geometry state to apply')), StateChange.MODEL_SUITE_STATE_INDEX: OptionalTunableClientStateChangeItem(description='\n            For object definitions that use a suite of models (each w/ its own\n            model, rig, slots, slot resources, and footprint), switch the index\n            used in the suite.\n            ', tunable=TunableModelSuiteStateIndex(description='Index to use.')), 'visibility_flags': OptionalTunableClientStateChangeItem(description='\n            If specified, apply visibility flag overrides for this object. For\n            example, control whether or not the object is reflected in mirrors\n            and water.\n            ', tunable=OptionalTunable(tunable=TunableEnumFlags(enum_type=VisibilityFlags, allow_no_flags=True), disabled_name='No_Flags')), 'visibility': OptionalTunableClientStateChangeItem(tunable=TunableVisibilityState(description='A visibility state to apply')), 'scale': OptionalTunableClientStateChangeItem(tunable=Tunable(float, 1, description='A scale to apply')), 'opacity': OptionalTunableClientStateChangeItem(tunable=TunableRange(float, 1, 0, 1, description='An opacity to apply')), 'tint': OptionalTunableClientStateChangeItem(tunable=TunableColorSnippet(description='A tint to apply'))}
    CUSTOM_DISTRIBUTABLE_CHANGES = (StateChange.AUDIO_EFFECT_STATE, StateChange.AUDIO_STATE, StateChange.AUTONOMY_MODIFIERS, StateChange.AWARENESS, StateChange.BROADCASTER, StateChange.ENVIRONMENT_SCORE, StateChange.REPLACE_OBJECT, StateChange.TOGGLE_FOOTPRINT, StateChange.UI_METADATA, StateChange.VFX, StateChange.VFX_STATE, StateChange.LOT_MODIFIERS, StateChange.CHANGE_VALUE, StateChange.GEOMETRY_STATE_OVERRIDE, StateChange.MODEL_SUITE_STATE_INDEX, StateChange.UTILITY_MODIFIERS, StateChange.PAINTING_STATE, StateChange.LIVE_DRAG, StateChange.WALKSTYLE, StateChange.PERIODIC_LOOT, StateChange.GLOW, StateChange.SITUATION, StateChange.TAN_LEVEL, StateChange.ROUTE_EVENT, StateChange.SET_FIRE)
    POST_LOAD_ENABLED_DISTRIBUTABLES = (StateChange.AUDIO_EFFECT_STATE, StateChange.AUDIO_STATE, StateChange.REPLACE_OBJECT, StateChange.TOGGLE_FOOTPRINT, StateChange.VFX, StateChange.VFX_STATE, StateChange.GEOMETRY_STATE_OVERRIDE, StateChange.MODEL_SUITE_STATE_INDEX, StateChange.PAINTING_STATE, StateChange.GLOW)
    INVENTORY_AFFECTED_DISTRIBUTABLES = (StateChange.AUDIO_EFFECT_STATE, StateChange.AUDIO_STATE, StateChange.VFX, StateChange.GLOW)
    USE_COMPONENT_FOR = {StateChange.FOCUS_SCORE: FOCUS_COMPONENT.instance_attr, StateChange.MANNEQUIN_POSE: MANNEQUIN_COMPONENT.instance_attr, StateChange.LIGHT_MATERIAL_STATE: LIGHTING_COMPONENT.instance_attr, StateChange.LIGHT_DIMMER_STATE: LIGHTING_COMPONENT.instance_attr, StateChange.VIDEO_STATE_LOOPING: VIDEO_COMPONENT.instance_attr, StateChange.VIDEO_STATE: VIDEO_COMPONENT.instance_attr, StateChange.FLOWING_PUDDLE_ENABLED: FLOWING_PUDDLE_COMPONENT.instance_attr, StateChange.PAINTING_REVEAL_LEVEL: CANVAS_COMPONENT.instance_attr}

    def __init__(self, **ops_tuning):
        self.ops = ops_tuning

    def apply(self, target, custom_distributables, state, state_value, immediate=False, post_load_distributable_only=False):
        for (attr_name, attr_value) in self.ops.items():
            if attr_value is UNSET:
                pass
            elif attr_name in self.CUSTOM_DISTRIBUTABLE_CHANGES:
                if post_load_distributable_only and attr_name not in self.POST_LOAD_ENABLED_DISTRIBUTABLES:
                    pass
                else:
                    result = custom_distributables.apply(target, attr_name, state, state_value, attr_value, immediate=immediate)
                    if result is not None and not result:
                        return result
                        if attr_name in self.USE_COMPONENT_FOR:
                            component_name = self.USE_COMPONENT_FOR[attr_name]
                            attr_target = getattr(target, component_name)
                            logger.debug('    {}.{} = {}', component_name, attr_name, attr_value)
                        else:
                            attr_target = target
                            logger.debug('    {} = {}', attr_name, attr_value)
                        if attr_target is not None:
                            setattr(attr_target, attr_name, attr_value)
            else:
                if attr_name in self.USE_COMPONENT_FOR:
                    component_name = self.USE_COMPONENT_FOR[attr_name]
                    attr_target = getattr(target, component_name)
                    logger.debug('    {}.{} = {}', component_name, attr_name, attr_value)
                else:
                    attr_target = target
                    logger.debug('    {} = {}', attr_name, attr_value)
                if attr_target is not None:
                    setattr(attr_target, attr_name, attr_value)
        return True

class ObjectStateMetaclass(TunedInstanceMetaclass):

    def __repr__(self):
        return self.__name__
ObjectStateValueDisplayMixin = get_display_mixin(has_description=True, has_icon=True)
class ObjectStateValue(HasTunableReference, ObjectStateValueDisplayMixin, SuperAffordanceProviderMixin, metaclass=ObjectStateMetaclass, manager=get_instance_manager(sims4.resources.Types.OBJECT_STATE)):
    INSTANCE_TUNABLES = {'value': TunableVariant(locked_args={'unordered': None}, boolean=Tunable(bool, True), integral=Tunable(int, 0), decimal=Tunable(float, 0)), 'anim_overrides': OptionalTunable(TunableAnimationObjectOverrides(description='\n            Tunable class to contain param/vfx/props overrides\n            ')), 'new_client_state': StateChangeOperation.TunableFactory(description='\n            Operations to perform on any object that ends up at this state\n            value.\n            '), 'allowances': TunableTuple(description='\n            A tuple of allowances for this state.\n            ', allow_in_carry=Tunable(description='\n                If checked, this state can be enabled when this object is being\n                carried, if unchecked, this state can never be enabled when\n                this object is being carried.\n                ', tunable_type=bool, default=True), allow_out_of_carry=Tunable(description='\n                If checked, this state can be enabled when this object is not\n                being carried, if unchecked, this state can never be enabled\n                when this object is not being carried.\n                ', tunable_type=bool, default=True), allow_inside=Tunable(description='\n                If checked, this state can be enabled when this object is\n                inside, if unchecked, this state can never be enabled when this\n                object is inside.\n                ', tunable_type=bool, default=True), allow_outside=Tunable(description='\n                If checked, this state can be enabled when this object is\n                outside, if unchecked, this state can never be enabled when\n                this object is outside.\n                ', tunable_type=bool, default=True), allow_on_natural_ground=Tunable(description='\n                If checked, this state can be enabled when this object is on\n                natural ground, if unchecked, this state can never be enabled\n                when this object is on natural ground.\n                ', tunable_type=bool, default=True), allow_off_natural_ground=Tunable(description='\n                If checked, this state can be enabled when this object is not\n                on natural ground, if unchecked, this state can never be\n                enabled when this object is not on natural ground.\n                ', tunable_type=bool, default=True)), 'buff_weight_multipliers': TunableBuffWeightMultipliers(), 'remove_from_crafting_cache': Tunable(description='\n            If True, this state will cause the object to be removed from the crafting cache.\n            This should be set if you plan to test out crafting interactions while in this \n            state.  For example, when the stove breaks, it is no longer available for the Sim \n            to craft with.  Marking this as True for that state will show all recipes that \n            require the stove as grayed out in the picker.\n            ', tunable_type=bool, default=False), 'crafting_types': OptionalTunable(description='\n            If enabled, contains a list of crafting types that an object with\n            this state value supports. This is useful for recipes that require\n            an upgraded object to craft them.\n            \n            Example: Espresso Machine can only craft the prework shot when the\n            object has been upgraded. The upgraded state will add a new\n            upgraded crafting type that is required by the recipe.\n            ', tunable=TunableList(description='\n                A list of crafting types that are added to the object with this\n                state.\n                ', tunable=TunableReference(description='\n                    This specifies the crafting object type that the object\n                    satisfies.\n                    ', manager=services.recipe_manager(), class_restrictions=('CraftingObjectType',)))), 'force_add_state': Tunable(description='\n            If True, this stateValue will always be added to an object when \n            set_state is called.  If False, this stateValue will only be set\n            on the object if it already has a state value for that state.\n            ', tunable_type=bool, default=False)}
    state = None

    @classmethod
    def calculate_autonomy_weight(cls, sim):
        total_weight = 1
        for (buff, weight) in cls.buff_weight_multipliers.items():
            if sim.has_buff(buff):
                total_weight *= weight
        return total_weight

class CommodityBasedObjectStateValue(ObjectStateValue):
    REMOVE_INSTANCE_TUNABLES = ('value',)
    INSTANCE_TUNABLES = {'range': TunableInterval(description="\n            The commodity range this state maps to. The ranges between the commodity\n            values must have some overlap in order for the state to transition properly.\n            For instance, let's say you have two states, DIRTY and CLEAN. If you set the\n            DIRTY state to have a range between 0 and 20, and you set CLEAN state to have\n            a range of 21 to 100, the states will not change properly because of the void\n            created (between 20 and 21). At the very least, the lower bounds of one needs\n            to be the same as the upper bound for the next (i.e. DIRTY from 0 to 20 and\n            CLEAN from 20 to 100).\n            ", tunable_type=float, default_lower=0, default_upper=0), 'default_value': OptionalTunable(Tunable(description='\n                default commodity value when set to this state.\n                If disabled use average of range', tunable_type=float, default=0), disabled_name='use_range_average', enabled_name='use_default_value')}

    @classmethod
    def _tuning_loaded_callback(cls):
        value = (cls.range.lower_bound + cls.range.upper_bound)/2
        if cls.default_value is None:
            cls.value = value
        else:
            cls.value = cls.default_value
        ninety_percent_interval = 0.9*(cls.range.upper_bound - cls.range.lower_bound)
        cls.low_value = value - ninety_percent_interval/2
        cls.high_value = value + ninety_percent_interval/2

class ChannelBasedObjectStateValue(ObjectStateValue):
    INSTANCE_SUBCLASSES_ONLY = True
    INSTANCE_TUNABLES = {'show_in_picker': Tunable(bool, True, description='If True than this channel will not be displayed to be chosen in the channel picker dialog.')}

    @classmethod
    def activate_channel(cls, *args, **kwargs):
        raise NotImplementedError

    @classmethod
    def test_channel(cls, target, context):
        raise NotImplementedError

class VideoChannel(ChannelBasedObjectStateValue):
    INSTANCE_TUNABLES = {'affordance': TunableReference(manager=services.get_instance_manager(sims4.resources.Types.INTERACTION), allow_none=True)}

    @classmethod
    def activate_channel(cls, interaction=None, push_affordances=True):
        if not push_affordances:
            return
        if not cls.affordance:
            return
        target_object = interaction.target
        push_affordance = interaction.generate_continuation_affordance(cls.affordance)
        context = interaction.context.clone_for_continuation(interaction)
        for aop in push_affordance.potential_interactions(target_object, context):
            aop.test_and_execute(context)

    @classmethod
    def test_channel(cls, target, context):
        return cls.affordance.test(target=target, context=context)

class AudioChannel(ChannelBasedObjectStateValue):
    INSTANCE_TUNABLES = {'listen_affordances': TunableList(description='\n            An ordered list of affordances that define "listening" to this\n            channel. The first succeeding affordance is used.\n            ', tunable=TunableReference(manager=services.get_instance_manager(sims4.resources.Types.INTERACTION), pack_safe=True))}

    @classmethod
    def get_provided_super_affordances_gen(cls):
        yield from cls.listen_affordances
        yield from super().get_provided_super_affordances_gen()

    @classmethod
    def activate_channel(cls, interaction=None, push_affordances=False, **kwargs):
        if push_affordances:
            cls.push_listen_affordance(interaction, interaction.context)
        elif interaction.target is not None:
            current_state = interaction.target.get_state(cls.state)
            if current_state is not cls.state:
                interaction.target.set_state(cls.state, cls)

    @classmethod
    def push_listen_affordance(cls, interaction, context):
        for listen_affordance in cls.listen_affordances:
            listen_affordance = interaction.generate_continuation_affordance(listen_affordance)
            for aop in listen_affordance.potential_interactions(interaction.target, context):
                result = aop.test_and_execute(context)
                if result:
                    return

    @classmethod
    def on_interaction_canceled_from_state_change(cls, interaction):
        continuation_context = interaction.context.clone_for_continuation(interaction)
        cls.push_listen_affordance(interaction, continuation_context)

    @classmethod
    def test_channel(cls, target, context):
        for listen_affordance in cls.listen_affordances:
            if listen_affordance.test(target=target, context=context):
                return True
        return False

class TunableStateValueReference(TunableReference):

    def __init__(self, class_restrictions=DEFAULT, **kwargs):
        if class_restrictions is DEFAULT:
            class_restrictions = ObjectStateValue
        super().__init__(manager=get_instance_manager(sims4.resources.Types.OBJECT_STATE), class_restrictions=class_restrictions, **kwargs)

class TunablePackSafeStateValueReference(TunablePackSafeReference):

    def __init__(self, class_restrictions=DEFAULT, **kwargs):
        if class_restrictions is DEFAULT:
            class_restrictions = ObjectStateValue
        super().__init__(manager=get_instance_manager(sims4.resources.Types.OBJECT_STATE), class_restrictions=class_restrictions, **kwargs)

class TestedStateValueReference(HasTunableSingletonFactory, AutoFactoryInit):
    FACTORY_TUNABLES = {'tested_states': TunableList(description='\n            The first test that passes will have its state applied.\n            ', tunable=TunableTuple(tests=event_testing.tests.TunableTestSet(), state=TunableStateValueReference(pack_safe=True))), 'fallback_state': OptionalTunable(description='\n            If all tests fail, this state will be applied.\n            ', tunable=TunableStateValueReference(pack_safe=True))}

class ObjectState(HasTunableReference, ObjectStateValueDisplayMixin, metaclass=ObjectStateMetaclass, manager=get_instance_manager(sims4.resources.Types.OBJECT_STATE)):
    INSTANCE_TUNABLES = {'overridden_by': OptionalTunable(TunableReference(manager=get_instance_manager(sims4.resources.Types.OBJECT_STATE), class_restrictions='ObjectState')), '_values': TunableList(TunableStateValueReference(reload_dependent=True, pack_safe=True)), 'persists_across_gallery': Tunable(description='\n            Check only if this state should be persisted when the object is \n            downloaded from the gallery.  If its unchecked and the object \n            comes from the gallery it will go to its default state.\n            Additionally any state with a linked stat needs to have that \n            linked stat also marked as gallery persisted.\n            i.e. Most states like dirty and broken are not meant to be saved \n            on the gallery, only states like crafted_quality or\n            ingredient quality should be saved.\n            Switching on this bit has performance implications when downloading \n            a lot from the gallery. Please discuss with a GPE when setting this \n            tunable.\n            ', tunable_type=bool, default=False), 'failed_to_load_state_value': OptionalTunable(description='\n            When loading states, if there is a load error of a\n            state value not found, by default it will always reset\n            to the default state value.  But if this is enabled, \n            it will be set to a custom state. \n            ', tunable=TunableStateValueReference(description='\n                A state value to be set on state load failure.\n                '), disabled_name='use_default_state', enabled_name='set_state')}
    _sorted_values = None
    linked_stat = None
    lot_based = None

    @classproperty
    def values(cls):
        if not cls._sorted_values:
            if cls._values and any(v.value is None for v in cls._values):
                cls._sorted_values = cls._values
            else:
                cls._sorted_values = tuple(sorted(cls._values, key=operator.attrgetter('value')))
        return cls._sorted_values

    @classmethod
    def _tuning_loaded_callback(cls):
        for value in cls._values:
            value.state = cls

    @classmethod
    def _verify_tuning_callback(cls):
        if cls.linked_stat is not None and cls.persists_across_gallery != cls.linked_stat.persists_across_gallery_for_state:
            logger.error('State {} and its linked statistic {} are not consistent on their gallery persistance', cls, cls.linked_stat, owner='camilogarcia')

class CommodityBasedObjectState(ObjectState):
    INSTANCE_TUNABLES = {'linked_stat': TunableReference(description='\n            The statistic to link to the state.\n            ', manager=get_instance_manager(sims4.resources.Types.STATISTIC)), '_values': TunableList(tunable=TunableStateValueReference(class_restrictions=CommodityBasedObjectStateValue), unique_entries=True, minlength=1), 'lot_based': Tunable(description='\n            Whether the state should check the linked stat on the active lot\n            instead of on the object itself.\n            ', tunable_type=bool, default=False)}

    @classmethod
    def get_value(cls, statistic_value):
        for state_value in cls._values:
            if statistic_value >= state_value.range.lower_bound:
                upper_bound = state_value.range.upper_bound
                if upper_bound == cls.linked_stat.max_value:
                    statisfy_upper = statistic_value <= upper_bound
                else:
                    statisfy_upper = statistic_value < upper_bound
                if statisfy_upper:
                    return state_value

    @classmethod
    def _verify_statistic_range_coverage(cls):
        stat_lower_bound = cls.linked_stat.min_value
        for state in cls.values:
            if state.range.lower_bound > stat_lower_bound:
                return strformatter('There is no coverage between {} and {}.', stat_lower_bound, state.range.lower_bound)
            if state.range.upper_bound >= cls.linked_stat.max_value:
                return
            if state.range.upper_bound > stat_lower_bound:
                stat_lower_bound = state.range.upper_bound
        return strformatter('There is no coverage after {}.', stat_lower_bound)

    @classmethod
    def _verify_tuning_callback(cls):
        super()._verify_tuning_callback()
        if cls.linked_stat.use_stat_value_on_initialization or cls.linked_stat.get_initial_value() != 0 and cls.linked_stat.initial_value_range is None:
            logger.error('{} has a linked stat {} that has initial tuning but Use Stat Value On Init is not checked.', cls, cls.linked_stat, owner='rmccord')
        coverage_error_msg = cls._verify_statistic_range_coverage()
        if coverage_error_msg is not None:
            logger.info('{}: There is a range coverage error for linked stat {}: {}', cls, cls.linked_stat.__name__, coverage_error_msg)

class TunableStateTypeReference(TunableReference):

    def __init__(self, class_restrictions=DEFAULT, **kwargs):
        if class_restrictions is DEFAULT:
            class_restrictions = ObjectState
        super().__init__(manager=get_instance_manager(sims4.resources.Types.OBJECT_STATE), class_restrictions=class_restrictions, **kwargs)

class StateComponent(Component, component_name=STATE_COMPONENT, persistence_key=protocols.PersistenceMaster.PersistableData.StateComponent, persistence_priority=ComponentPriority.PRIORITY_STATE, allow_dynamic=True):
    BROKEN_STATE_SET = TunableSet(description='\n        A set of state values that an object can be considered as broken (not usable) in the game.\n        ', tunable=TunableStateValueReference())
    _on_state_changed = None

    def __init__(self, owner, *, states=(), state_triggers=(), unique_state_changes=None, delinquency_state_changes=None, timed_state_triggers=None, overlapping_slot_states=None):
        super().__init__(owner)
        self._state_reset_values = {}
        self._state_reset_if_time_passes_values = {}
        self._commodity_states = {}
        self._client_states = {}
        self._tested_states_on_add = {}
        self._tested_states_on_location_changed = {}
        self._active_timed_triggers = {}
        self._stat_listeners = collections.defaultdict(list)
        self._state_triggers = state_triggers
        self._custom_distributables = StateComponentManagedDistributables()
        self._state_trigger_enabled = True
        self._unique_state_changes = unique_state_changes
        self._delinquency_state_changes = delinquency_state_changes
        self._timed_state_triggers = timed_state_triggers
        self._state_based_value_mod = 1.0
        self.overlapping_slot_states = overlapping_slot_states
        self.hovertip_requested = False
        self.states_before_delinquency = None
        if unique_state_changes is not None:
            self._verify_unique_state_changes()
        state_dict = {}
        for state_info in states:
            default_value = state_info.default_value
            if not default_value:
                logger.error('State {} on object {} attempting to load with an invalid default_value {}.', state_info, owner, default_value, owner='tastle')
            elif not isinstance(default_value, ObjectStateMetaclass):
                default_value = weighted_random_item([(entry.weight, entry.state) for entry in default_value])
                if default_value is None:
                    logger.error('State {} on object {} has un-tuned entries in its randomized default_value tuning.', state_info, owner, owner='tastle')
                else:
                    state = default_value.state
                    state_dict[state] = default_value
                    if state_info.reset_to_default:
                        self._state_reset_values[state] = default_value
                    if state_info.reset_on_load_if_time_passes:
                        self._state_reset_if_time_passes_values[state] = default_value
                    self._client_states[state] = state_info.client_states
                    if state_info.tested_states_on_add is not None:
                        self._tested_states_on_add[state] = state_info.tested_states_on_add
                    if state_info.tested_states_on_location_changed is not None:
                        self._tested_states_on_location_changed[state] = state_info.tested_states_on_location_changed
                    self._do_first_time_state_added_actions(state)
            else:
                state = default_value.state
                state_dict[state] = default_value
                if state_info.reset_to_default:
                    self._state_reset_values[state] = default_value
                if state_info.reset_on_load_if_time_passes:
                    self._state_reset_if_time_passes_values[state] = default_value
                self._client_states[state] = state_info.client_states
                if state_info.tested_states_on_add is not None:
                    self._tested_states_on_add[state] = state_info.tested_states_on_add
                if state_info.tested_states_on_location_changed is not None:
                    self._tested_states_on_location_changed[state] = state_info.tested_states_on_location_changed
                self._do_first_time_state_added_actions(state)
        if any(s.overridden_by is not None for s in state_dict):
            self._states = collections.OrderedDict()
            sorted_state_list = topological_sort(state_dict, lambda s: (s.overridden_by,))
        else:
            self._states = dict()
            sorted_state_list = state_dict
        self._states.update((state, state_dict[state]) for state in sorted_state_list)

    def on_add(self):
        zone = services.current_zone()
        if zone is None:
            return
        if not zone.is_zone_running:
            return
        self._apply_tested_states_on_add()

    def on_location_changed(self, old_location):
        if not self._tested_states_on_location_changed:
            return
        zone = services.current_zone()
        if zone is None:
            return
        if not zone.is_zone_running:
            return
        if self.owner.routing_component is not None and self.owner.routing_component.is_moving:
            return
        self._apply_tested_states_on_location_changed()

    def on_finalize_load(self):
        self._apply_tested_states_on_add()
        self._apply_tested_states_on_location_changed()
        if not self.apply_delinquent_states(from_load=True):
            self.clear_delinquent_states(from_load=True)

    def apply_delinquent_states(self, utility=None, from_load=False):
        if self._delinquency_state_changes is None:
            return False
        if not self.owner.is_on_active_lot:
            return False
        household = services.owning_household_of_active_lot()
        if household is None:
            return False
        for (state_utility, state_list) in self._delinquency_state_changes.items():
            if utility is not None:
                if state_utility is not utility:
                    pass
                else:
                    for state_value in state_list:
                        self.apply_delinquent_state(state_value, from_load=from_load)
            elif not household.bills_manager.is_utility_delinquent(state_utility):
                pass
            else:
                for state_value in state_list:
                    self.apply_delinquent_state(state_value, from_load=from_load)
            for state_value in state_list:
                self.apply_delinquent_state(state_value, from_load=from_load)
        return True

    def apply_delinquent_state(self, state_value, from_load=False):
        if self.state_value_active(state_value):
            return
        if self.states_before_delinquency is None:
            self.states_before_delinquency = []
        self.states_before_delinquency.append(self.get_state(state_value.state))
        self.set_state(state_value.state, state_value, from_init=from_load, immediate=from_load)

    def clear_delinquent_states(self, from_load=False):
        if self.states_before_delinquency is not None:
            for old_state in self.states_before_delinquency:
                self.set_state(old_state.state, old_state, from_init=from_load, immediate=from_load)
            self.states_before_delinquency = None

    def _do_first_time_state_added_actions(self, state):
        if state.linked_stat is not None:
            self._commodity_states[state.linked_stat] = state

    def _apply_tested_states_on_add(self):
        resolver = SingleObjectResolver(self.owner)
        for (state, value) in self._tested_states_on_add.items():
            test_passed = False
            for tested_state in value.tested_states:
                if tested_state.tests.run_tests(resolver):
                    self.set_state(state, tested_state.state)
                    test_passed = True
                    break
            if test_passed or value.fallback_state is not None:
                self.set_state(state, value.fallback_state)

    def _apply_tested_states_on_location_changed(self):
        resolver = SingleObjectResolver(self.owner)
        for (state, value) in self._tested_states_on_location_changed.items():
            test_passed = False
            for tested_state in value.tested_states:
                if tested_state.tests.run_tests(resolver):
                    self.set_state(state, tested_state.state)
                    test_passed = True
                    break
            if test_passed or value.fallback_state is not None:
                self.set_state(state, value.fallback_state)

    def _get_tracker(self, state):
        if state.lot_based:
            current_zone = services.current_zone()
            lot = current_zone.lot
            return lot.get_tracker(state.linked_stat)
        else:
            return self.owner.get_tracker(state.linked_stat)

    def pre_add(self, *_, **__):
        for (state, value) in self.items():
            if state.linked_stat is not None:
                tracker = self._get_tracker(state)
                add = state.linked_stat.added_by_default(min_range=value.range.lower_bound, max_range=value.range.upper_bound)
                linked_stat = tracker.get_statistic(state.linked_stat, add=add)
                if state.linked_stat.use_stat_value_on_initialization:
                    self.set_state_from_stat(state, linked_stat, preferred_value=value, force_update=True)
                else:
                    self.set_state(state, value, from_init=True)
            else:
                self.set_state(state, value, from_init=True)

    def on_remove_from_client(self, *_, **__):
        self._cleanup_client_state()

    def on_remove(self, *_, **__):
        if not (self.owner.is_sim or services.current_zone().is_zone_shutting_down):
            self._cleanup_client_state()
            for state in self._commodity_states.values():
                stat_listeners = self._stat_listeners.get(state)
                if stat_listeners is not None:
                    tracker = self._get_tracker(state)
                    for listener in stat_listeners:
                        tracker.remove_listener(listener)
        for listeners in self._stat_listeners.values():
            listeners.clear()
        self._stat_listeners.clear()

    def on_post_load(self, *_, **__):
        for (state, value) in self.items():
            self.owner.on_state_changed(state, value, value, False)
            if self._on_state_changed:
                self._on_state_changed(self.owner, state, value, value)
            if self._state_trigger_enabled:
                for state_trigger in self._state_triggers:
                    state_trigger.trigger_state(self.owner, value, value)
            self._apply_client_state(state, value, post_load_distributable_only=True)

    def _persist_accross_gallery(self, state):
        if self.owner.is_downloaded and not state.persists_across_gallery:
            return True
        return False

    def component_reset(self, reset_reason):
        if reset_reason == ResetReason.BEING_DESTROYED:
            return
        if not self.owner.valid_for_distribution:
            return
        self.reset_states_to_default()

    @componentmethod
    def reset_states_to_default(self):
        for (state, value) in self.items():
            new_value = self._state_reset_values.get(state, value)
            if new_value != value:
                self.set_state(state, new_value)
            else:
                self._trigger_on_state_changed(state, value, new_value)

    def reset_state_to_default(self, fallback_state):
        state = fallback_state.state
        value = self._states[state]
        new_value = self._state_reset_values.get(state, None)
        if new_value is None:
            new_value = fallback_state
        if new_value is not None:
            if new_value is not value:
                self.set_state(state, new_value)
            else:
                self._trigger_on_state_changed(state, value, new_value)

    def pre_parent_change(self, parent):
        if self.enter_carry_state is None and parent is not None and parent.is_sim:
            for value in self.values():
                if not value.allowances.allow_in_carry:
                    logger.error('Attempting to pick up object {} when its current state value {} is not compatible with carry.', self, value, owner='tastle')
        elif not (parent is None or parent.is_sim):
            for value in self.values():
                if not value.allowances.allow_out_of_carry:
                    logger.error('Attempting to put down object {} when its current state value {} is not compatible with put down.', self, value, owner='tastle')

    def on_parent_change(self, parent):
        if parent is not None and parent.is_sim:
            enter_carry_state = self.enter_carry_state
            if enter_carry_state is not None:
                self.set_state(enter_carry_state.state, enter_carry_state)
        elif parent is None or not parent.is_sim:
            exit_carry_state = self.exit_carry_state
            if exit_carry_state is not None:
                self.set_state(exit_carry_state.state, exit_carry_state)

    def _set_placed_outside(self):
        outside_placement_state = self.outside_placement_state
        if outside_placement_state is not None:
            self.set_state(outside_placement_state.state, outside_placement_state)

    def _set_placed_inside(self):
        inside_placement_state = self.inside_placement_state
        if inside_placement_state is not None:
            self.set_state(inside_placement_state.state, inside_placement_state)

    def _set_placed_on_natural_ground(self):
        on_natural_ground_placement_state = self.on_natural_ground_placement_state
        if on_natural_ground_placement_state is not None:
            self.set_state(on_natural_ground_placement_state.state, on_natural_ground_placement_state)

    def _set_placed_off_natural_ground(self):
        off_natural_ground_placement_state = self.off_natural_ground_placement_state
        if off_natural_ground_placement_state is not None:
            self.set_state(off_natural_ground_placement_state.state, off_natural_ground_placement_state)

    def on_placed_in_slot(self, slot_owner):
        resolver = DoubleObjectResolver(self.owner, slot_owner)
        if self._unique_state_changes:
            for state_tuning in self._unique_state_changes.slot_placement:
                if state_tuning.tests.run_tests(resolver):
                    self.set_state(state_tuning.state.state, state_tuning.state)

    def on_removed_from_slot(self, slot_owner):
        resolver = DoubleObjectResolver(self.owner, slot_owner)
        if self._unique_state_changes:
            for state_tuning in self._unique_state_changes.slot_removal:
                if state_tuning.tests.run_tests(resolver):
                    self.set_state(state_tuning.state.state, state_tuning.state)

    def _surface_type_changed(self):
        if self._unique_state_changes.surface_type_placement_states is not None:
            if self.owner.location.routing_surface is None:
                surface_type = SurfaceType.SURFACETYPE_WORLD
            else:
                surface_type = self.owner.location.routing_surface.type
            state_to_change = self._unique_state_changes.surface_type_placement_states.get(surface_type, None)
            if state_to_change is not None:
                self.set_state(state_to_change.state, state_to_change)

    def on_added_to_inventory(self):
        self._custom_distributables.stop_inventory_distributables()

    def on_removed_from_inventory(self):
        self._custom_distributables.restart_inventory_distributables()

    def component_super_affordances_gen(self, **kwargs):
        for state_value in self.values():
            yield from state_value.get_provided_super_affordances_gen()

    @componentmethod
    def add_state_changed_callback(self, callback):
        if not self._on_state_changed:
            self._on_state_changed = CallableList()
        self._on_state_changed.append(callback)

    @componentmethod
    def remove_state_changed_callback(self, callback):
        self._on_state_changed.remove(callback)
        if not self._on_state_changed:
            del self._on_state_changed

    @property
    def enter_carry_state(self):
        if self._unique_state_changes is not None:
            return self._unique_state_changes.enter_carry_state

    @property
    def exit_carry_state(self):
        if self._unique_state_changes is not None:
            return self._unique_state_changes.exit_carry_state

    @property
    def outside_placement_state(self):
        if self._unique_state_changes is not None:
            return self._unique_state_changes.outside_placement_state

    @property
    def inside_placement_state(self):
        if self._unique_state_changes is not None:
            return self._unique_state_changes.inside_placement_state

    @property
    def on_natural_ground_placement_state(self):
        if self._unique_state_changes is not None:
            return self._unique_state_changes.on_natural_ground_placement_state

    @property
    def off_natural_ground_placement_state(self):
        if self._unique_state_changes is not None:
            return self._unique_state_changes.off_natural_ground_placement_state

    @property
    def delinquency_state_changes(self):
        return self._delinquency_state_changes

    def keys(self):
        return self._states.keys()

    def items(self):
        return self._states.items()

    def values(self):
        return self._states.values()

    @componentmethod
    def get_client_states(self, state):
        return self._client_states[state].keys()

    @componentmethod_with_fallback(lambda state: False)
    def has_state(self, state):
        return state in self._states

    @componentmethod_with_fallback(lambda *_, **__: False)
    def state_value_active(self, state_value):
        return state_value is self._states.get(state_value.state)

    @componentmethod
    def get_state(self, state):
        return self._states[state]

    @componentmethod_with_fallback(lambda : None)
    def get_object_rarity_string(self):
        if not self.has_state(ObjectCollectionData.COLLECTED_RARITY_STATE):
            return
        rarity = ObjectCollectionData.COLLECTION_RARITY_MAPPING[self.get_state(ObjectCollectionData.COLLECTED_RARITY_STATE)].text_value
        return rarity

    @componentmethod
    def does_state_reset_on_load(self, state):
        return state in self._state_reset_if_time_passes_values

    @componentmethod
    def copy_state_values(self, other_object, state_list=DEFAULT):
        if other_object.has_component(STATE_COMPONENT):
            state_list = self._states.keys() if state_list is DEFAULT else state_list
            for state in list(state_list):
                if other_object.has_state(state):
                    state_value = other_object.get_state(state)
                    self.set_state(state, state_value)

    @componentmethod
    def is_object_usable(self):
        for state_value in StateComponent.BROKEN_STATE_SET:
            if self.state_value_active(state_value):
                return False
        return True

    @property
    def state_based_value_mod(self):
        return self._state_based_value_mod

    @state_based_value_mod.setter
    def state_based_value_mod(self, value):
        self._state_based_value_mod = value
        update_tooltip = self.owner.get_tooltip_field(TooltipFieldsComplete.simoleon_value) is not None
        self.owner.update_current_value(update_tooltip)

    def _verify_unique_state_changes(self):
        enter_carry_state = self.enter_carry_state
        exit_carry_state = self.exit_carry_state
        outside_placement_state = self.outside_placement_state
        inside_placement_state = self.inside_placement_state
        on_natural_ground_placement_state = self.on_natural_ground_placement_state
        off_natural_ground_placement_state = self.off_natural_ground_placement_state
        if not enter_carry_state.allowances.allow_in_carry:
            logger.error('Attempting to set enter_carry_state for {} to state value {} which is not compatible with carry. Please fix in tuning.', self.owner, enter_carry_state, owner='tastle')
            self._unique_state_changes.enter_carry_state = None
        if not exit_carry_state.allowances.allow_out_of_carry:
            logger.error('Attempting to set exit_carry_state for {} to state value {} which is not compatible with carry. Please fix in tuning.', self.owner, exit_carry_state, owner='tastle')
            self._unique_state_changes.exit_carry_state = None
        if not outside_placement_state.allowances.allow_outside:
            logger.error('Attempting to set outside_placement_state for {} to state value {} which is not compatible with outside placement. Please fix in tuning.', self.owner, outside_placement_state, owner='tastle')
            self._unique_state_changes.outside_placement_state = None
        if not inside_placement_state.allowances.allow_inside:
            logger.error('Attempting to set inside_placement_state for {} to state value {} which is not compatible with inside placement. Please fix in tuning.', self.owner, inside_placement_state, owner='tastle')
            self._unique_state_changes.inside_placement_state = None
        if not on_natural_ground_placement_state.allowances.allow_on_natural_ground:
            logger.error('Attempting to set on_natural_ground_placement_state for {} to state value {} which is not compatible with placement on natural ground. Please fix in tuning.', self.owner, on_natural_ground_placement_state, owner='tastle')
            self._unique_state_changes.on_natural_ground_placement_state = None
        if not off_natural_ground_placement_state.allowances.allow_off_natural_ground:
            logger.error('Attempting to set off_natural_ground_placement_state for {} to state value {} which is not compatible with placement off of natural ground. Please fix in tuning.', self.owner, off_natural_ground_placement_state, owner='tastle')
            self._unique_state_changes.off_natural_ground_placement_state = None

    def _check_allowances(self, new_value):
        if self.owner.manager is None:
            return True
        owner_parent = self.owner.parent
        if new_value.allowances.allow_in_carry or owner_parent is not None and owner_parent.is_sim:
            logger.error('Attempting to set the state of object {}, currently being carried by {} to state value {}, which is not allowed to be set during carry.', self.owner, owner_parent, new_value, owner='tastle')
            return False
        if new_value.allowances.allow_out_of_carry or owner_parent is None:
            logger.error('Attempting to set the state of object {}, currently not being carried to state value {}, which is not allowed to be set outside of carry.', self.owner, new_value, owner='tastle')
            return False
        is_outside = self.owner.is_outside
        if new_value.allowances.allow_outside or is_outside and is_outside is not None:
            logger.error('Attempting to set the state of object {}, currently outside to state value {}, which is not allowed to be set outside.', self.owner, new_value, owner='tastle')
            return False
        if new_value.allowances.allow_inside or is_outside or is_outside is not None:
            logger.error('Attempting to set the state of object {}, currently inside to state value {}, which is not allowed to be set inside.', self.owner, new_value, owner='tastle')
            return False
        is_on_natural_ground = self.owner.is_on_natural_ground()
        if is_on_natural_ground is None:
            return True
        if new_value.allowances.allow_on_natural_ground or is_on_natural_ground and is_on_natural_ground is not None:
            logger.error('Attempting to set the state of object {}, currently on natural ground to state value {}, which is not allowed to be set on natural ground.', self.owner, new_value, owner='tastle')
            return False
        elif new_value.allowances.allow_off_natural_ground or is_on_natural_ground or is_on_natural_ground is not None:
            logger.error('Attempting to set the state of object {}, currently not on natural ground to state value {}, which is not allowed to be set when not on natural ground.', self.owner, new_value, owner='tastle')
            return False
        return True

    @componentmethod
    def set_state_dynamically(self, state, new_value, seed_value, **kwargs):
        if state not in self._states:
            if state.overridden_by is not None:
                logger.error('It is unsupported to dynamically set a state that specifies overridden_by')
            self._states[state] = seed_value
        self.set_state(state, new_value, **kwargs)

    @componentmethod
    def set_state(self, state, new_value, from_stat=False, from_init=False, immediate=False, force_update=False):
        if not self._check_allowances(new_value):
            return
        value_force_added = False
        if state not in self._states:
            if new_value.force_add_state:
                self._states[state] = new_value
                self._do_first_time_state_added_actions(state)
                value_force_added = True
            else:
                logger.warn("Attempting to set the value of the '{}' state on object {}, but the object's definition ({}) isn't tuned to have that state, and force_add_state is false.", state.__name__, self.owner, self.owner.definition.name)
                return
        old_value = self._states[state]
        if not from_init:
            if new_value == old_value and not (force_update or value_force_added):
                return
            if not from_stat:
                stat_type = state.linked_stat
                if stat_type in self._commodity_states:
                    tracker = self._get_tracker(state)
                    if self.owner.is_locked(tracker.get_statistic(stat_type)):
                        return
            if new_value != old_value or value_force_added:
                current_zone_id = services.current_zone_id()
                if current_zone_id is not None:
                    services.get_event_manager().process_events_for_household(test_events.TestEvent.ObjectStateChange, household=services.owning_household_of_active_lot(), custom_keys=(new_value,))
        logger.debug('State change: {} -> {} ({})', old_value, new_value, 'from_init' if from_init else 'from_stat' if from_stat else 'normal')
        self._states[state] = new_value
        if new_value.super_affordances or old_value.super_affordances:
            affordance_provider = new_value if new_value.super_affordances else old_value
            self.owner.update_component_commodity_flags(affordance_provider=affordance_provider)
        if from_stat and from_init:
            self._set_stat_to_value(state, new_value, from_init=from_init)
        self._trigger_on_state_changed(state, old_value, new_value, immediate=immediate, from_init=from_init)
        caches.clear_all_caches()

    @componentmethod
    def get_state_value_from_stat_type(self, stat_type):
        for (state, value) in self.items():
            linked_stat = getattr(state, 'linked_stat', None)
            if linked_stat is not None and linked_stat is stat_type:
                return value

    @property
    def state_trigger_enabled(self):
        return self._state_trigger_enabled

    @state_trigger_enabled.setter
    def state_trigger_enabled(self, value):
        self._state_trigger_enabled = value

    def _trigger_on_state_changed(self, state, old_value, new_value, immediate=False, from_init=False):
        if not self._apply_client_state(state, new_value, immediate=immediate):
            return
        owner_id = self.owner.id
        if self.owner.is_in_inventory():
            manager = services.inventory_manager()
        elif self.owner.is_social_group:
            manager = services.social_group_manager()
        else:
            manager = services.object_manager()
        self._add_stat_listener(state, new_value)
        self.owner.on_state_changed(state, old_value, new_value, from_init)
        timed_state_trigger_on_load = False
        process_timed_state_triggers = True if self._timed_state_triggers is not None and new_value in self._timed_state_triggers else False
        if process_timed_state_triggers:
            timed_state_trigger_on_load = self._timed_state_triggers[new_value].trigger_on_load
        if owner_id not in manager:
            if timed_state_trigger_on_load:
                if old_value in self._active_timed_triggers:
                    self._active_timed_triggers[old_value].stop_active_alarm()
                    del self._active_timed_triggers[old_value]
                self._active_timed_triggers[new_value] = TimedStateChange(self, self.owner, new_value, self._timed_state_triggers[new_value].ops)
            return
        if self._on_state_changed:
            self._on_state_changed(self.owner, state, old_value, new_value)
        if self._state_trigger_enabled:
            for state_trigger in self._state_triggers:
                state_trigger.trigger_state(self.owner, old_value, new_value, immediate=immediate)
                if self.owner.state_component is None:
                    process_timed_state_triggers = False
                    break
        if old_value in self._active_timed_triggers:
            self._active_timed_triggers[old_value].stop_active_alarm()
            del self._active_timed_triggers[old_value]
        if process_timed_state_triggers:
            self._active_timed_triggers[new_value] = TimedStateChange(self, self.owner, new_value, self._timed_state_triggers[new_value].ops)

    def disable_timed_state_trigger(self, timed_state):
        if timed_state in self._active_timed_triggers:
            del self._active_timed_triggers[timed_state]
            return
        logger.error('Timed state {} finished its alarm but was not set as active for object {}', timed_state, self.owner, owner='camilogarcia')

    def is_state_timed_trigger_active(self, active_state):
        return active_state in self._active_timed_triggers

    def _get_values_for_state(self, state):
        if state in self._states:
            return state.values

    def _clear_stat_listeners(self, tracker, stat_listeners):
        if stat_listeners:
            for listener in stat_listeners:
                tracker.remove_listener(listener)
            del stat_listeners[:]

    def _add_stat_listener(self, state, new_value):
        stat_type = state.linked_stat
        if stat_type in self._commodity_states:
            value_list = self._get_values_for_state(state)
            tracker = self._get_tracker(state)
            stat_listeners = self._stat_listeners[state]
            self._clear_stat_listeners(tracker, stat_listeners)
            if tracker.has_statistic(stat_type) or stat_type.added_by_default():
                tracker.add_statistic(stat_type)
            lower_value = None
            upper_value = None
            value_index = value_list.index(new_value)
            if value_index > 0:
                lower_value = value_list[value_index - 1]
            if value_index < len(value_list) - 1:
                upper_value = value_list[value_index + 1]

            def add_listener(preferred_value, threshold):
                listener = None

                def callback(stat_type):
                    if listener is not None:
                        tracker.remove_listener(listener)
                        if listener in stat_listeners:
                            stat_listeners.remove(listener)
                    self.set_state_from_stat(state, stat_type, preferred_value=preferred_value)

                listener = tracker.create_and_add_listener(stat_type, threshold, callback)
                if listener is not None:
                    stat_listeners.append(listener)

            if lower_value is not None:
                threshold = sims4.math.Threshold()
                threshold.value = new_value.range.lower_bound
                threshold.comparison = operator.lt
                add_listener(lower_value, threshold)
            if upper_value is not None:
                threshold = sims4.math.Threshold()
                threshold.value = new_value.range.upper_bound
                threshold.comparison = operator.gt
                add_listener(upper_value, threshold)

    def _set_stat_to_value(self, state, state_value, from_init=False):
        stat_type = state.linked_stat
        if stat_type in self._commodity_states:
            tracker = self._get_tracker(state)
            self._clear_stat_listeners(tracker, self._stat_listeners[state])
            tracker.set_value(stat_type, state_value.value, add=True, from_init=from_init)
            return True

    @staticmethod
    def get_state_from_stat(obj, state, stat=DEFAULT, preferred_value=None):
        if stat is DEFAULT:
            stat = state.linked_stat
        stat_type = stat.stat_type
        tracker = obj.get_tracker(stat_type)
        stat_value = tracker.get_value(stat_type)
        min_d = MAX_FLOAT
        new_value = None
        for value in state.values:
            if value.range.lower_bound <= stat_value and stat_value <= value.range.upper_bound:
                if value is preferred_value:
                    new_value = value
                    break
                d = abs(stat_value - value.value)
                if d < min_d:
                    min_d = d
                    new_value = value
        if new_value is None:
            for value in state.values:
                d = abs(stat_value - value.value)
                if d < min_d:
                    min_d = d
                    new_value = value
            logger.warn("{}: State values don't have full coverage of the commodity range. {} has no corresponding state value.  Falling back to closest option, {}.", state, stat_value, new_value)
        return new_value

    def set_state_from_stat(self, state, stat, preferred_value=None, from_init=False, **kwargs):
        if state.lot_based:
            current_zone = services.current_zone()
            target = current_zone.lot
        else:
            target = self.owner
        if stat is None:
            stat = state.linked_stat
        new_value = self.get_state_from_stat(target, state, stat, preferred_value)
        if new_value is None:
            tracker = self._get_tracker(state)
            stat_value = tracker.get_value(stat)
            logger.warn('Statistic change {} with value {} does not correspond to a {} state', stat, stat_value, state)
        if self.owner.state_component is None:
            logger.error('set_state_from_stat with owner not having state component.\nOwner: {}\nState: {}\nValue: {}\nStat: {}', self.owner, state, new_value, stat, owner='nabaker', trigger_breakpoint=True)
            return
        logger.debug('Statistic change triggering state change: {} --> {}', stat, new_value)
        self.set_state(state, new_value, from_stat=True, from_init=from_init, **kwargs)

    def _client_states_gen(self, value):
        yield value.new_client_state
        if value.state in self._client_states:
            client_states_for_state = self._client_states[value.state]
            if value in client_states_for_state:
                new_client_state = client_states_for_state[value]
                if new_client_state is not None:
                    yield new_client_state

    @componentmethod
    def get_component_managed_state_distributable(self, attr_name, state):
        return self._custom_distributables.get_distributable(attr_name, state)

    def _apply_client_state(self, state, value, immediate=False, post_load_distributable_only=False):
        target = self.owner if not self.owner.is_social_group else self.owner.anchor
        for new_client_state in self._client_states_gen(value):
            result = new_client_state.apply(target, self._custom_distributables, state, value, immediate=immediate, post_load_distributable_only=post_load_distributable_only)
            if not result:
                return result
        if state.overridden_by is not None and self.has_state(state.overridden_by):
            self._apply_client_state(state.overridden_by, self.get_state(state.overridden_by), immediate=immediate)
        return True

    def _cleanup_client_state(self):
        self._custom_distributables.cleanup()

    def component_anim_overrides_gen(self):
        for state_value in self._states.values():
            if state_value.anim_overrides is not None:
                yield state_value.anim_overrides

    def on_hovertip_requested(self):
        if not self.hovertip_requested:
            self.hovertip_requested = True
            return_val = False
            for state in self.keys():
                distributeable = self._custom_distributables.get_distributable('ui_metadata', state)
                if distributeable is not None:
                    return_val = True
                    distributeable.start()
            return return_val
        return False

    @componentmethod
    def add_client_state_suppressor(self, suppressor):
        self._custom_distributables.add_client_state_suppressor(suppressor)
        self.owner.on_client_suppressor_added()

    @componentmethod
    def remove_client_state_suppressor(self, suppressor):
        self._custom_distributables.remove_client_state_suppressor(suppressor)
        self.owner.on_client_suppressor_removed(self._custom_distributables.has_client_state_supressors)

    def handle_overlapping_slots(self, child, location=None, new_parent=None):
        if child.is_prop:
            return
        slot_types = set(self.overlapping_slot_states.keys())
        if self.owner is child:
            if location is None:
                return
            parent = location.parent
        else:
            parent = self.owner.parent
        runtime_slots = list(parent.get_runtime_slots_gen(slot_types=slot_types, bone_name_hash=None))
        parenting = location is not None
        for slot in runtime_slots:
            if not parenting:
                if slot.slot_name_hash == child.location.slot_hash:
                    break
                    if slot.slot_name_hash == location.slot_hash:
                        break
            elif slot.slot_name_hash == location.slot_hash:
                break
        slot = None
        if slot is not None:
            for slot_type in slot.slot_types:
                state_tuning = self.overlapping_slot_states.get(slot_type, None)
                if state_tuning is None:
                    pass
                elif parenting:
                    self.set_state(state_tuning.state_value_reference, state_tuning.state_to_apply_on_parent)
                elif new_parent is UNSET:
                    self.set_state(state_tuning.state_value_reference, state_tuning.state_to_apply_on_deletion)
                elif new_parent is not None and new_parent.is_sim:
                    self.set_state(state_tuning.state_value_reference, state_tuning.state_to_apply_on_unparent_by_sim)
                else:
                    self.set_state(state_tuning.state_value_reference, state_tuning.state_to_apply_on_unparent)

    def _save_state_data(self):
        states_data = []
        states_before_delinquency_data = []

        def save_state_and_value(state, value):
            save = protocols.StateComponentState()
            new_value = self._state_reset_if_time_passes_values.get(state, value)
            save.state_name_hash = state.guid64
            save.value_name_hash = new_value.guid64
            return save

        for (state, value) in self._states.items():
            save = save_state_and_value(state, value)
            states_data.append(save)
            logger.info('[PERSISTENCE]: state {}({}).', state, value)
        if self.states_before_delinquency is not None:
            for state in self.states_before_delinquency:
                save = save_state_and_value(state.state, state)
                states_before_delinquency_data.append(save)
                logger.info('[PERSISTENCE]: state before delinquency{}({}).', state.state, state)
        return (states_data, states_before_delinquency_data)

    def save(self, persistence_master_message):
        persistable_data = protocols.PersistenceMaster.PersistableData()
        persistable_data.type = protocols.PersistenceMaster.PersistableData.StateComponent
        state_save = persistable_data.Extensions[protocols.PersistableStateComponent.persistable_data]
        logger.info('[PERSISTENCE]: ----Start saving state component of {0}.', self.owner)
        (states_data, states_before_delinquency_data) = self._save_state_data()
        state_save.states.extend(states_data)
        state_save.states_before_delinquency.extend(states_before_delinquency_data)
        persistence_master_message.data.extend([persistable_data])
        logger.info('[PERSISTENCE]: ----End saving state component of {0}.', self.owner)

    def _load_state_and_value(self, state_info):
        object_state_manager = get_instance_manager(sims4.resources.Types.OBJECT_STATE)
        state = object_state_manager.get(state_info.state_name_hash)
        if state is None:
            logger.info('Trying to load unavailable OBJECT_STATE resource: {}', state_info.state_name_hash)
            return (None, None)
        value = object_state_manager.get(state_info.value_name_hash)
        if value is None:
            if state.failed_to_load_state_value is None:
                logger.warn("Attempting to load an invalid object state value on {0}. Likely means out of date tuning was persisted. Leaving state '{1}' set to default.", self.owner, state.__name__)
                return (None, None)
            value = state.failed_to_load_state_value
        if state not in self._states:
            logger.warn("Loading a state {} that is valid but not part of the Object Component. Likely means out dated tuning for {}'s state component was persisted.", str(state), self.owner)
            linked_stat = state.linked_stat
            if linked_stat is not None:
                tracker = self.owner.get_tracker(linked_stat)
                if tracker is not None:
                    if tracker.statistics_to_skip_load is None:
                        tracker.statistics_to_skip_load = set()
                    tracker.statistics_to_skip_load.add(linked_stat)
            return (None, None)
        return (state, value)

    def load(self, state_component_message):
        state_component_data = state_component_message.Extensions[protocols.PersistableStateComponent.persistable_data]
        logger.info('[PERSISTENCE]: ----Start loading state component of {0}.', self.owner)
        for state_info in state_component_data.states:
            (state, value) = self._load_state_and_value(state_info)
            if not state is None:
                if value is None:
                    pass
                elif self._persist_accross_gallery(state):
                    pass
                else:
                    logger.info('[PERSISTENCE]: {}({}).', state, value)
                    self.set_state(state, value)
        if state_component_data.states_before_delinquency:
            self.states_before_delinquency = []
            for state_info in state_component_data.states_before_delinquency:
                (state, value) = self._load_state_and_value(state_info)
                if not state is None:
                    if value is None:
                        pass
                    else:
                        logger.info('[PERSISTENCE]: {}({}).', state, value)
                        self.states_before_delinquency.append(value)
        logger.info('[PERSISTENCE]: ----End loading state component of {0}.', self.owner)

    @classmethod
    def on_failed_to_load_component(cls, owner, persistable_data):
        state_component_data = persistable_data.Extensions[protocols.PersistableStateComponent.persistable_data]
        object_state_manager = get_instance_manager(sims4.resources.Types.OBJECT_STATE)
        for state_info in itertools.chain(state_component_data.states, state_component_data.states_before_delinquency):
            state = object_state_manager.get(state_info.state_name_hash)
            if state is None:
                pass
            else:
                linked_stat = state.linked_stat
                if linked_stat is None:
                    pass
                else:
                    tracker = owner.get_tracker(linked_stat)
                    if tracker.statistics_to_skip_load is None:
                        tracker.statistics_to_skip_load = set()
                    tracker.statistics_to_skip_load.add(linked_stat)

class StateTriggerOperation(enum.Int):
    AND = 0
    OR = 1
    NONE = 2

class TunableStateTriggerTestVariant(TunableVariant):

    def __init__(self, description='A single tunable test.', **kwargs):
        super().__init__(object_criteria=objects.object_tests.ObjectCriteriaTest.TunableFactory(locked_args={'tooltip': None}), festival_running=FestivalRunningTest.TunableFactory(locked_args={'tooltip': None}), next_festival=NextFestivalTest.TunableFactory(locked_args={'tooltip': None}), description=description, **kwargs)

class TunableStateTriggerTestSet(event_testing.tests.TestListLoadingMixin):
    DEFAULT_LIST = event_testing.tests.TestList()

    def __init__(self, description=None, **kwargs):
        if description is None:
            description = 'A list of tests.  All tests must succeed to pass the TestSet.'
        super().__init__(description=description, tunable=TunableStateTriggerTestVariant(), **kwargs)

class StateTrigger(HasTunableSingletonFactory, AutoFactoryInit):

    @staticmethod
    def _verify_tunable_callback(instance_class, tunable_name, source, value):
        if value.set_random_state is None and value.set_states is None and (value.statistic_operations or value.set_on_children is None):
            logger.error('Object {} has trigger state values at states {} that does nothing.', instance_class, value.at_states, owner='rmccord')
        if any(state_value.state.linked_stat in value.statistic_operations for state_value in value.at_states if state_value is not None):
            logger.error('Statistic Operation linked to state this trigger is listening for. This could cause circular triggers.')

    FACTORY_TUNABLES = {'set_states': OptionalTunable(description='\n            If enabled it will trigger the states tuned on the list.\n            Either this list or set random state needs to be tuned on a state\n            trigger.\n            ', tunable=TunableList(description='\n                List of states to be applied.\n                ', tunable=TunableStateValueReference(pack_safe=True), minlength=1), enabled_name='Set_state_list', disabled_name='No_state_list'), 'at_states': TunableList(TunablePackSafeStateValueReference(), allow_none=True), 'set_random_state': OptionalTunable(description='\n            If enabled it will trigger a random state value out of the possible\n            weighted list.\n            This can be combined with set_state so either or both of them \n            can apply on a state triggered. \n            If a chance of nothing happening is desired you can tune an empty \n            field on the trigger_random_state list. \n            ', tunable=TunableList(description='\n                List of weighted states to be triggered.\n                ', tunable=TunableTuple(description='\n                    Pairs of states and weights to be randomly selected.\n                    ', weight=Tunable(description='\n                        ', tunable_type=int, default=1), tests=TunableStateTriggerTestSet(), state_value=TunableStateValueReference())), disabled_name='No_random_states', enabled_name='Trigger_random_state'), 'prohibited_states': TunableList(description='\n            List of prohibited states. If the object has one of this state,\n            it will not trigger the target state.\n            ', tunable=TunableStateValueReference(description='\n                Prohibited state.\n                ', pack_safe=True)), 'statistic_operations': TunableList(description="\n            A list of statistic operations that will be applied when the\n            trigger is thrown. \n            \n            BEWARE: if a State being applied above is linked to a stat in this\n            list, they may collide, and the statistic here will take precedent.\n            Also, if a state this trigger is listening to is linked to a stat\n            tuned here, then it's possible this will get in a circular loop\n            forever. Please be smart about how you use this power.\n            ", tunable=TunableStatisticChange(description='\n                A statistic change operation.\n                ', locked_args={'advertise': False, 'chance': SuccessChance.ONE, 'tests': None, 'subject': ParticipantType.Object}, statistic_override=StatisticOperation.get_statistic_override(pack_safe=True), include_relationship_ops=False)), 'set_on_children': OptionalTunable(description='\n            If enabled, will apply states and/or stats to children of this\n            object.\n            ', tunable=TunableTuple(description='\n                Lists of states and stats to apply to children.\n                ', set_states=TunableSet(description='\n                    List of States to set on children.\n                    ', tunable=TunableStateValueReference(pack_safe=True)), statistic_ops=TunableList(description='\n                    List of statistic ops to apply to children.\n                    ', tunable=TunableStatisticChange(description='\n                        A statistic change operation to apply to all chilren of\n                        this object.\n                        ', locked_args={'advertise': False, 'chance': SuccessChance.ONE, 'tests': None, 'subject': ParticipantType.Object}, include_relationship_ops=False))), enabled_name='set_on_children', disabled_name='leave_children_alone'), 'trigger_operation': TunableEnumEntry(description='\n            The operation to apply on the at_states to decide if we can trigger\n            the at_state. \n            AND:  trigger the new state only if the object is in all the listed \n                  states at the same time. \n            OR:   trigger the new state if the object is in any of the listed \n                  states. \n            NONE: trigger the new state only if the object is in none of the \n                  listed states.\n            ', tunable_type=StateTriggerOperation, default=StateTriggerOperation.AND), 'trigger_chance': OptionalTunable(TunableRange(description='\n                The chance to trigger the target state when we reach the at_state.', tunable_type=float, default=100, minimum=0, maximum=100)), 'verify_tunable_callback': _verify_tunable_callback}

    def is_trigger_state_valid(self, owner, at_state, state_to_trigger):
        if at_state is state_to_trigger:
            return False
        if owner.state_component is None:
            logger.exception('{} does not have a state component but we are testing a state trigger value at_state={}, state_to_trigger={}', owner, at_state, state_to_trigger)
            return False
        elif owner.state_component.state_value_active(state_to_trigger):
            return False
        return True

    def trigger_state(self, owner, old_value, at_state, immediate=False):
        trigger_states = []
        if self.set_states is not None:
            for state_to_trigger in self.set_states:
                if self.is_trigger_state_valid(owner, at_state, state_to_trigger):
                    trigger_states.append(state_to_trigger)
        if self._check_triggerable(owner, at_state):
            try:
                for state in trigger_states:
                    logger.debug('TriggerState: {}, from {}', state, at_state)
                    owner.set_state(state.state, state, immediate=immediate)
                resolver = SingleObjectResolver(owner)
                if self.set_random_state and old_value is not at_state:
                    weight_pairs = [(data.weight, data.state_value) for data in self.set_random_state if data.tests.run_tests(resolver)]
                    random_state_value = weighted_random_item(weight_pairs)
                    if random_state_value:
                        owner.set_state(random_state_value.state, random_state_value, immediate=immediate)
                for stat_op in self.statistic_operations:
                    stat_op.apply_to_resolver(resolver)
                if owner.children:
                    for child in owner.children:
                        for state in self.set_on_children.set_states:
                            child.set_state(state.state, state, immediate=immediate)
                        child_resolver = SingleObjectResolver(child)
                        for stat_op in self.set_on_children.statistic_ops:
                            stat_op.apply_to_resolver(child_resolver)
            except:
                logger.exception('Failed to trigger state. Object: {}, State: {}, Exception: {}', owner, at_state)

    def _archive_state_trigger(self, obj, state_value, at_state, source=''):
        if gsi_handlers.state_handlers.state_trigger_archiver.enabled:
            gsi_handlers.state_handlers.archive_state_trigger(obj, state_value, at_state, self.at_states, source=source)

    def _check_triggerable(self, owner, at_state):
        if not self._check_chance():
            return False
        if not self._check_prohibited_states(owner):
            return False
        if self.trigger_operation == StateTriggerOperation.AND:
            return self._check_and(owner, at_state)
        if self.trigger_operation == StateTriggerOperation.OR:
            return self._check_or(owner, at_state)
        elif self.trigger_operation == StateTriggerOperation.NONE:
            return self._check_none(owner, at_state)
        return False

    def _check_and(self, owner, at_state):
        if at_state not in self.at_states:
            return False
        for state_value in self.at_states:
            if state_value is None:
                return False
            if not owner.state_component.state_value_active(state_value):
                return False
        return True

    def _check_or(self, owner, at_state):
        return at_state in self.at_states

    def _check_none(self, owner, at_state):
        if at_state in self.at_states:
            return False
        for state_value in self.at_states:
            if state_value is None:
                pass
            elif owner.state_component.state_value_active(state_value):
                return False
        return True

    def _check_chance(self):
        if self.trigger_chance is None:
            return True
        return random_chance(self.trigger_chance)

    def _check_prohibited_states(self, owner):
        return not any(owner.state_component.state_value_active(s) for s in self.prohibited_states)

class TunableStateComponent(TunableFactory):

    @staticmethod
    def _verify_tunable_callback(instance_class, tunable_name, source, states=None, timed_state_triggers=None, **kwargs):
        if timed_state_triggers is not None:
            for timed_trigger in timed_state_triggers.values():
                lowest_trigger = -1
                for trigger_item in timed_trigger.ops:
                    if trigger_item.states_to_trigger is not None:
                        for state_value in trigger_item.states_to_trigger:
                            if state_value.state is None:
                                logger.error("State value '{}' triggered in the timed state triggers of Object {} has no tuned state.", state_value, instance_class, owner='shipark')
                            if state_value is not None and state_value.state not in [object_state.default_value.state for object_state in states]:
                                logger.error("Object {} triggers the state '{}' in its timed state triggers but isn't tuned in the states list of the state component.", instance_class, state_value.state, owner='shipark')
                    if trigger_item.trigger_time <= lowest_trigger:
                        logger.error('Object {} has a list of trigger trigger_item {} is lower than previous trigger {}', instance_class, trigger_item, lowest_trigger, owner='camilogarcia')
                    lowest_trigger = trigger_item.trigger_time

    FACTORY_TYPE = StateComponent

    def __init__(self, description='Allow persistent state to be saved for this object.', **kwargs):
        super().__init__(states=TunableList(description='\n                Supported states for this object\n                ', tunable=TunableTuple(description='\n                    A supported state for this object\n                    ', default_value=TunableVariant(description='\n                        The default value for the state.\n                        ', reference=TunableStateValueReference(pack_safe=True), random=TunableList(description='\n                            A weighted list of object states to randomly choose\n                            between as the default for this state.\n                            ', tunable=TunableTuple(state=TunableStateValueReference(pack_safe=True), weight=Tunable(tunable_type=float, default=1.0))), default='reference'), client_states=TunableMapping(description='\n                        A list of client states. Although ObjectStateValues\n                        have their own State Change Operations (Audio effect\n                        state, Broadcaster, etc), those operations will be\n                        overriden by operations specified here.\n                        ', key_type=TunableStateValueReference(description='\n                            A state value\n                            ', pack_safe=True), value_type=StateChangeOperation.TunableFactory()), reset_to_default=Tunable(description='\n                        If checked, when the object is reset, the state will be\n                        reset to the default value. Otherwise, it will keep the\n                        current value.\n                        ', tunable_type=bool, default=False), reset_on_load_if_time_passes=Tunable(description='\n                        If checked then the object is saved with the default\n                        state rather than the current state.  If we want it\n                        to return to this state we need an interaction that\n                        is saved to put it back into it.\n                        ', tunable_type=bool, default=False), tested_states_on_add=OptionalTunable(description="\n                        The first test that passes will have its state applied.\n                        If no tests pass, the fallback state will be applied.\n                        This can be used to conditionally apply a state to an\n                        object.  For example, the Tree Rabbit Hale needs to \n                        default to the open state when it's on the Slyvan Glade\n                        venue.\n                        This runs when the object is added to the world.\n                        ", tunable=TestedStateValueReference.TunableFactory()), tested_states_on_location_changed=OptionalTunable(description="\n                        The first test that passes will have its state applied.\n                        If no tests pass, the fallback state will be applied.\n                        This can be used to conditionally apply a state to an\n                        object.  For example, the boat needs to be set to it's\n                        on water state if it is placed on water.\n                        This runs when the location of the object changes as\n                        long as the object isn't currently routing.\n                        ", tunable=TestedStateValueReference.TunableFactory()))), state_triggers=TunableList(StateTrigger.TunableFactory()), unique_state_changes=OptionalTunable(description='\n                Special cases that will cause state changes to occur.\n                ', tunable=TunableTuple(enter_carry_state=TunableStateValueReference(description='\n                        If specified, the object will enter this state when\n                        entering carry.\n                        ', allow_none=True), exit_carry_state=TunableStateValueReference(description='\n                        If specified, the object will enter this state when\n                        exiting carry.\n                        ', allow_none=True), outside_placement_state=TunableStateValueReference(description='\n                        If specified, the object will enter this state when\n                        being placed outside.\n                        ', allow_none=True), inside_placement_state=TunableStateValueReference(description='\n                        If specified, the object will enter this state when\n                        being placed inside.\n                        ', allow_none=True), on_natural_ground_placement_state=TunableStateValueReference(description='\n                        If specified, the object will enter this state when\n                        being placed on natural ground.\n                        ', allow_none=True), off_natural_ground_placement_state=TunableStateValueReference(description='\n                        If specified, the object will enter this state when\n                        being placed off of natural ground.\n                        ', allow_none=True), slot_placement=TunableList(description='\n                        A list of state changes which will be applied, if their\n                        tests pass, when this object is slotted to another\n                        object. In these tests, Actor is this object and\n                        Target/Object is the parent object.\n                        ', tunable=TunableTuple(tests=TunableTestSet(), state=TunableStateValueReference())), slot_removal=TunableList(description='\n                        A list of state changes which will be applied, if their\n                        tests pass, when this object is removed from a slot on\n                        another object. In these tests, Actor is this object and\n                        Target/Object is the parent object.\n                        ', tunable=TunableTuple(tests=TunableTestSet(), state=TunableStateValueReference())), surface_type_placement_states=TunableMapping(description='\n                        Mapping of surface type to the state that should be\n                        enabled when an object is placed on that type of\n                        surface.\n                        State will not be removed if object is off that\n                        surface, to do this the other options on the surface\n                        types should be tuned.\n                        i.e. Pet Ball should IDLE when placed on POOL routing\n                        surface, but should be on state OFF when placed on\n                        WORLD or OBJECT surfaces.\n                        ', key_type=TunableEnumEntry(SurfaceType, description='\n                            The surface type that will trigger the state \n                            change.\n                            ', default=SurfaceType.SURFACETYPE_WORLD), value_type=TunableStateValueReference(description='\n                            State to trigger when the object is placed on the \n                            specified surface type.\n                            ')))), delinquency_state_changes=OptionalTunable(TunableMapping(description='\n                A tunable mapping linking a utility to a list of state changes\n                to apply to the owning object of this component when that\n                utility goes delinquent and is shut off.\n                ', key_type=TunableEnumEntry(description='\n                    A utility that will force state changes when it is shut\n                    off.\n                    ', tunable_type=household_utilities.utility_types.Utilities, default=None), value_type=TunableList(description='\n                    A tunable list of states to apply to the owning object of\n                    this component when the mapped utility is shut off.\n                    ', tunable=TunableStateValueReference()))), timed_state_triggers=OptionalTunable(description='\n                If enabled, when states in this key mapping get triggered, it\n                will trigger states changes at each of the tuned intervals.\n                ', tunable=TunableMapping(description='\n                    Map of state when the timed state triggers will be active\n                    and the states to trigger, specific trigger times, and\n                    the options of whether to trigger on load.\n                    ', key_type=TunableStateValueReference(pack_safe=True), value_type=TunableTuple(trigger_on_load=Tunable(description='\n                            If set to True, when the state in the key mapping\n                            is set on an object on load the changes are triggered.\n                            ', tunable_type=bool, default=False), ops=TunableList(description='\n                            List of multiple states and times when they can be \n                            triggered.\n                            ', tunable=TunableTuple(description='\n                                Pair of trigger time and states to trigger when \n                                the time has passed.\n                                ', trigger_time=TunableSimMinute(description='\n                                    The time when the state to trigger will be\n                                    enabled.\n                                    ', default=10, minimum=0), states_to_trigger=TunableList(description='\n                                    List of states to trigger.\n                                    ', tunable=TunableStateValueReference(pack_safe=True)), loot_list=TunableList(description='\n                                    A list of loot operations to apply when state\n                                    change is triggered.\n                                    ', tunable=TunableReference(manager=services.get_instance_manager(sims4.resources.Types.ACTION), class_restrictions=('LootActions',), pack_safe=True))))))), overlapping_slot_states=OptionalTunable(description='\n            A mapping of slots that this object can overlap with when parented to\n            an object to the states that need to be applied when another object\n            is in one of those slots. When another object is parented to one of \n            the selected slots then this object will apply specific states. When\n            an object is removed from an overlapping slot then this object will \n            apply a different set of states.\n            ', tunable=TunableMapping(description="\n                A set of slots mapped to a set of states for when an object is\n                parented to an overlapping slot and what states to apply when \n                there is or isn't an object in that slot.\n                ", key_type=SlotType.TunableReference(), key_name='slot_type', value_type=TunableTuple(description='\n                    The state value to apply when another object is parented\n                    or removed from the parent object in the corresponding\n                    slot type.\n                    ', state_to_apply_on_parent=TunableStateValueReference(description='\n                        If an object is parented to a slot that overlaps with this\n                        object when it is parented to an object, then this is a\n                        reference to the states to apply to this object.\n                        '), state_to_apply_on_unparent=TunableStateValueReference(description='\n                        If no object is parented to a slot that overlaps with \n                        this object when it is parented to an object, then this is\n                        a reference to the states to apply to this object.\n                        '), state_to_apply_on_unparent_by_sim=TunableStateValueReference(description='\n                        If an object was parented to an overlapping slot and \n                        that child is unparented and the new parent is a sim\n                        then this is that state to apply.\n                        '), state_to_apply_on_deletion=TunableStateValueReference(description='\n                        If an object was parented to an overlapping slot and \n                        that child is being deleted.\n                        '), state_value_reference=TunableStateTypeReference(description='\n                        This is the state value that we will set to the states \n                        setup for when object are parented to overlapping slots.\n                        ')), value_name='overlap data')), description=description, verify_tunable_callback=self._verify_tunable_callback, **kwargs)

def state_change(targets, new_value_beginning=None, new_value_ending=None, xevt_id=None, animation_context=None, criticality=CleanupType.OnCancel, sequence=(), force_update=False):
    queue = []
    if not targets:
        return sequence
    set_at_beginning = new_value_beginning is not None and new_value_beginning.state is not None
    set_at_ending = new_value_ending is not None and new_value_ending.state is not None
    if set_at_beginning:

        def set_beginning_target_refs_states(*_, **__):
            for resolved_target in target_refs:
                resolved_target.set_state(new_value_beginning.state, new_value_beginning, force_update=force_update)

        queue.append(set_beginning_target_refs_states)
    did_set = False
    target_refs = weakref.WeakSet(targets)
    if set_at_ending:

        def set_ending_target_refs_states(*_, **__):
            nonlocal did_set
            if not did_set:
                for resolved_target in target_refs:
                    resolved_target.set_state(new_value_ending.state, new_value_ending, force_update=force_update)
                did_set = True

    if set_at_ending and xevt_id is not None:
        queue.append(lambda _: animation_context.register_event_handler(set_ending_target_refs_states, handler_id=xevt_id))
    queue.append(sequence)
    if set_at_ending:
        queue.append(set_ending_target_refs_states)
    else:
        criticality = CleanupType.NotCritical
    queue = build_element(queue, critical=criticality)
    return queue

class TunableStateChange(TunableFactory):

    @staticmethod
    def _state_change_at_beginning(new_value, **kwargs):
        return state_change(new_value_beginning=new_value, **kwargs)

    TunableAtBeginning = TunableFactory.create_auto_factory(_state_change_at_beginning, 'TunableAtBeginning', description='Change the state value at the beginning of the sequence.')

    @staticmethod
    def _state_change_at_end(new_value, **kwargs):
        return state_change(new_value_ending=new_value, **kwargs)

    TunableAtEnd = TunableFactory.create_auto_factory(_state_change_at_end, 'TunableAtEnd', description='Change the state value at the end of the sequence.', criticality=TunableEnumEntry(CleanupType, CleanupType.OnCancel, description='The criticality of making the state change.'))
    TunableOnXevt = TunableFactory.create_auto_factory(_state_change_at_end, 'TunableOnXevt', description='\n        Set the new state value in sync with an animation event with a\n        particular id. In the case no matching event occurs in the animation,\n        the value will still be set at the end of the sequence.\n        ', criticality=TunableEnumEntry(CleanupType, CleanupType.OnCancel, description='The criticality of making the state change.'), xevt_id=Tunable(int, 100, description="An xevt on which to change the state's value."))

    @staticmethod
    def _single_value(interaction, new_value):
        return new_value

    TunableSingleValue = TunableFactory.create_auto_factory(_single_value, 'TunableSingleValue', new_value=TunableStateValueReference())

    class ValueFromTestList(HasTunableSingletonFactory):

        @classproperty
        def FACTORY_TUNABLES(cls):
            from event_testing.tests import TunableTestVariant
            return {'new_values': TunableList(TunableTuple(test=TunableTestVariant(test_locked_args={'tooltip': None}), value=TunableStateValueReference())), 'fallback_value': OptionalTunable(TunableStateValueReference())}

        def __init__(self, new_values, fallback_value):
            self.new_values = new_values
            self.fallback_value = fallback_value

        def __call__(self, interaction):
            resolver = interaction.get_resolver()
            for new_value in self.new_values:
                if resolver(new_value.test):
                    return new_value.value
            return self.fallback_value

    class ValueFromTestSetList(ValueFromTestList):

        @classproperty
        def FACTORY_TUNABLES(cls):
            from event_testing.tests import TunableTestSet
            return {'new_values': TunableList(TunableTuple(tests=TunableTestSet(), value=TunableStateValueReference()))}

        def __call__(self, interaction):
            resolver = interaction.get_resolver()
            for new_value in self.new_values:
                if new_value.tests.run_tests(resolver):
                    return new_value.value
            return self.fallback_value

    @staticmethod
    def _factory(interaction, state_change_target, timing, new_value, force_update, **kwargs):
        actual_state_change_targets = interaction.get_participants(state_change_target)
        actual_new_value = new_value(interaction)
        return timing(new_value=actual_new_value, targets=actual_state_change_targets, animation_context=interaction.animation_context, force_update=force_update, **kwargs)

    FACTORY_TYPE = _factory

    def __init__(self, description='Change the value of a state on a participant of an interaction.', **kwargs):
        super().__init__(state_change_target=TunableEnumEntry(ParticipantType, ParticipantType.Object, description='Who or what to change the state on.'), timing=TunableVariant(description="When to change the state's value.", immediately=TunableStateChange.TunableAtBeginning(), at_end=TunableStateChange.TunableAtEnd(), on_xevt=TunableStateChange.TunableOnXevt(), default='at_end'), new_value=TunableVariant(description='A new value to set.', single_value=TunableStateChange.TunableSingleValue(), value_from_test_list=TunableStateChange.ValueFromTestList.TunableFactory(), value_from_test_set_list=TunableStateChange.ValueFromTestSetList.TunableFactory(), default='single_value'), force_update=Tunable(description="If checked, force update the state's value.", tunable_type=bool, default=False), description=description, **kwargs)

def transience_change(target, new_value_beginning=None, new_value_ending=None, xevt_id=None, animation_context=None, interaction=None, criticality=CleanupType.OnCancel, sequence=()):
    queue = []
    set_at_beginning = new_value_beginning is not None
    set_at_ending = new_value_ending is not None
    if set_at_ending:
        did_set = False
        target_ref = target.ref()

        def set_ending(*_, **__):
            nonlocal did_set
            if not did_set:
                resolved_target = target_ref()
                if resolved_target is not None:
                    resolved_target.transient = new_value_ending
                did_set = True

        if xevt_id is not None:
            queue.append(lambda _: animation_context.register_event_handler(set_ending, handler_id=xevt_id))

    def set_transience(target, value):
        if target is None:
            logger.error('Trying to set None target as transient in interaction. {}', interaction)
            return
        target.transient = value

    if set_at_beginning:
        queue.append(lambda _: set_transience(target, new_value_beginning))
    queue.append(sequence)
    if set_at_ending:
        queue.append(set_ending)
    else:
        criticality = CleanupType.NotCritical
    queue = build_element(queue, critical=criticality)
    return queue

class TunableTransienceChange(TunableFactory):

    @staticmethod
    def _factory(interaction, who, **kwargs):
        target = interaction.get_participant(who)
        if target is None:
            logger.warn('Trying to change the transience of a non existent object, is this expected?')
            return
        return transience_change(target=target, animation_context=interaction.animation_context, interaction=interaction, **kwargs)

    FACTORY_TYPE = _factory

    def __init__(self, description="Change the transience on the interaction's target.", **kwargs):
        super().__init__(who=TunableEnumEntry(ParticipantType, ParticipantType.Object, description='Who or what to apply this test to'), new_value_beginning=TunableVariant(locked_args={'no_change': None, 'make_transient': True, 'make_permanent': False}, default='no_change', description='A value to set transience to at the beginning (may be None)'), new_value_ending=TunableVariant(locked_args={'no_change': None, 'make_transient': True, 'make_permanent': False}, default='no_change', description='A value to set transience to at the beginning (may be None)'), xevt_id=OptionalTunable(Tunable(int, 100, description="An xevt on which to change the state's value to new_value_ending")), criticality=TunableEnumEntry(CleanupType, CleanupType.NotCritical, description='The criticality of making these state changes.'), description=description, **kwargs)

def filter_on_state_changed_callback(callback, filter_state):

    def callback_filter(target, state, old_value, new_value):
        if state != filter_state:
            return
        return callback(target, state, old_value, new_value)

    return callback_filter

def with_on_state_changed(target, filter_state, callback, *sequence):
    if filter_state is not None:
        callback = filter_on_state_changed_callback(callback, filter_state)

    def add_fn(_):
        target.add_state_changed_callback(callback)

    def remove_fn(_):
        target.remove_state_changed_callback(callback)

    return build_critical_section_with_finally(add_fn, sequence, remove_fn)

class TimedStateChange:

    def __init__(self, state, owner, active_state, trigger_times):
        self._state = state
        self._owner = owner
        self._active_state = active_state
        self._trigger_times = trigger_times
        self._trigger_index = 0
        interval_time = clock.interval_in_real_seconds(self._trigger_times[self._trigger_index].trigger_time)
        self._active_alarm_handle = alarms.add_alarm(self, interval_time, self._timed_trigger_callback)

    def _archive_timed_state_trigger(self, obj, state_value, at_state):
        if gsi_handlers.state_handlers.timed_state_trigger_archiver.enabled:
            trigger_time = self._trigger_times[self._trigger_index].trigger_time
            gsi_handlers.state_handlers.archive_timed_state_trigger(obj, state_value, at_state, trigger_time)

    def _timed_trigger_callback(self, _):
        trigger_time = self._trigger_times[self._trigger_index]
        states_to_trigger = trigger_time.states_to_trigger
        if states_to_trigger:
            for state in states_to_trigger:
                if state is None:
                    pass
                else:
                    self._state.set_state(state.state, state)
            resolver = SingleObjectResolver(self._owner)
            for loot_action in trigger_time.loot_list:
                loot_action.apply_to_resolver(resolver)
        if not self._state.is_state_timed_trigger_active(self._active_state):
            return
        self._trigger_index += 1
        if self._trigger_index >= len(self._trigger_times):
            self._state.disable_timed_state_trigger(self._active_state)
            return
        interval_time = clock.interval_in_real_seconds(self._trigger_times[self._trigger_index].trigger_time - self._trigger_times[self._trigger_index - 1].trigger_time)
        self._active_alarm_handle = alarms.add_alarm(self, interval_time, self._timed_trigger_callback)

    def stop_active_alarm(self):
        self._active_alarm_handle.cancel()
