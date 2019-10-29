from contextlib import contextmanagerimport collectionsimport functoolsimport itertoolsimport weakreffrom animation.animation_utils import flush_all_animationsfrom animation.posture_manifest import Hand, PostureManifest, AnimationParticipant, SlotManifest, MATCH_ANY, _NOT_SPECIFIC_ACTOR, FrozenPostureManifestfrom carry.carry_utils import create_carry_constraint, get_carried_objects_genfrom carry.pick_up_sim_liability import WaitToBePickedUpLiability, PickUpSimLiabilityfrom element_utils import build_critical_section_with_finally, build_critical_section, soft_sleep_foreverfrom element_utils import build_element, do_all, must_runfrom interactions import ParticipantType, PipelineProgress, TargetTypefrom interactions.aop import AffordanceObjectPairfrom interactions.base.super_interaction import SuperInteractionfrom interactions.constraints import Constraint, ANYWHERE, create_constraint_set, Circlefrom interactions.context import InteractionContext, QueueInsertStrategy, InteractionSourcefrom interactions.interaction_finisher import FinishingTypefrom interactions.priority import Priorityfrom interactions.utils.animation_reference import TunableAnimationReferencefrom interactions.utils.interaction_liabilities import STAND_SLOT_LIABILITY, CANCEL_AOP_LIABILITY, PRIVACY_LIABILITY, PrivacyLiabilityfrom interactions.utils.route_fail import handle_transition_failurefrom interactions.utils.routing_constants import TransitionFailureReasonsfrom objects.components.types import CARRYABLE_COMPONENTfrom objects.object_enums import ResetReasonfrom objects.pools import pool_utilsfrom objects.pools.ocean import Oceanfrom objects.terrain import TerrainPointfrom postures import DerailReason, MOVING_DERAILSfrom postures.base_postures import create_puppet_posturesfrom postures.context import PostureContextfrom postures.generic_posture_node import SimPostureNodefrom postures.posture import POSTURE_FAMILY_MAPfrom postures.posture_graph import TransitionSequenceStage, EMPTY_PATH_SPEC, PathType, SIM_SWIM_POSTURE_TYPE, SIM_DEFAULT_POSTURE_TYPEfrom postures.posture_specs import PostureSpecVariable, BODY_INDEX, BODY_TARGET_INDEX, BODY_POSTURE_TYPE_INDEX, PostureAspectBody, PostureAspectSurfacefrom postures.posture_state import PostureStatefrom postures.posture_state_spec import PostureStateSpecfrom postures.posture_tuning import PostureTuningfrom postures.stand import StandSuperInteractionfrom postures.transition import PostureStateTransitionfrom routing import SurfaceTypefrom server.pick_info import PickType, PickInfofrom services.reset_and_delete_service import ResetRecordfrom sims.outfits.outfit_enums import OutfitCategory, OutfitChangeReasonfrom sims4 import callback_utilsfrom sims4.callback_utils import CallableListfrom sims4.collections import frozendictfrom sims4.math import transform_almost_equalfrom sims4.profiler_utils import create_custom_named_profiler_functionfrom sims4.sim_irq_service import yield_to_irqfrom sims4.tuning.tunable import TunableSimMinute, TunableRealSecondfrom singletons import DEFAULTfrom teleport.teleport_helper import TeleportHelperfrom teleport.teleport_type_liability import TeleportStyleInjectionLiabilityfrom terrain import get_water_depthfrom vehicles.vehicle_constants import VehicleTransitionStatefrom world.ocean_tuning import OceanTuningimport build_buyimport cachesimport clockimport date_and_timeimport element_utilsimport elementsimport gsi_handlersimport interactions.constraintsimport interactions.utilsimport macrosimport postures.posture_graphimport postures.posture_scoringimport routingimport servicesimport sims4.collectionsimport sims4.loglogger = sims4.log.Logger('TransitionSequence')with sims4.reload.protected(globals()):
    global_plan_lock = None
    inject_interaction_name_in_callstack = False
def path_plan_allowed():
    if global_plan_lock is None:
        return True
    sim_with_lock = global_plan_lock()
    return sim_with_lock is None

def final_destinations_gen():
    for transition_controller in services.current_zone().all_transition_controllers:
        if transition_controller.is_transition_active():
            for final_dest in transition_controller.final_destinations_gen():
                yield final_dest
postures.posture_scoring.set_final_destinations_gen(final_destinations_gen)
class PosturePreferencesData:

    def __init__(self, apply_penalties, prefer_surface, require_current_constraint, posture_cost_overrides):
        self.apply_penalties = apply_penalties
        self.prefer_surface = prefer_surface
        self.require_current_constraint = require_current_constraint
        self.posture_cost_overrides = posture_cost_overrides.copy()

class TransitionSequenceData:

    def __init__(self):
        self.intended_location = None
        self.constraint = (None, None)
        self.templates = (None, None, None)
        self.valid_dest_nodes = set()
        self.segmented_paths = None
        self.connectivity = (None, None, None, None)
        self.path_spec = None
        self.final_destination = None
        self.final_included_sis = None
        self.progress = TransitionSequenceStage.EMPTY
        self.progress_max = TransitionSequenceStage.COMPLETE

class TransitionSequenceController:
    PRIVACY_ENGAGE = 0
    PRIVACY_SHOO = 1
    PRIVACY_BLOCK = 2
    MINIMUM_AREA_FOR_NO_STAND_RESERVATION = 2
    SIM_MINUTES_TO_WAIT_FOR_VIOLATORS = TunableSimMinute(description='\n        How many Sim minutes a Sim will wait for violating Sims to route away\n        before giving up on the interaction he was trying to run.  Used\n        currently for privacy and for slot reservations.\n        ', default=15, minimum=0)
    SLEEP_TIME_FOR_IDLE_WAITING = TunableRealSecond(1, description='\n        Time in real seconds idle behavior will sleep for before trying to find\n        next work again.\n        ')
    SHOO_ANIMATION = TunableAnimationReference(description='\n        The animation to play when Sims need to shoo privacy violators.\n        ')
    CALL_OVER_ANIMATION = TunableAnimationReference(description='\n        The animation to play when Sims require another Sim to continue their\n        transition, e.g. a toddler requiring to be picked up.\n        ')

    def __init__(self, interaction, ignore_all_other_sis=False):
        self._interaction = interaction
        self._target_interaction = None
        self._expected_sim_count = 0
        self._success = False
        self._canceled = False
        self._running_transition_interactions = set()
        self._transition_canceled = False
        self._current_transitions = {}
        self._derailed = {}
        self._has_tried_bring_group_along = False
        self._original_interaction_target = None
        self._original_interaction_target_changed = False
        self._shortest_path_success = collections.defaultdict(lambda : True)
        self._failure_target_and_reason = {}
        self._blocked_sis = []
        self._sim_jobs = []
        self._sim_idles = set()
        self._worker_all_element = None
        self._exited_due_to_exception = False
        self._sim_data = {}
        self._tried_destinations = collections.defaultdict(set)
        self._failure_path_spec = None
        self._running = False
        self._privacy_initiation_time = None
        self._processed_on_route_change = False
        self.outdoor_streetwear_change = {}
        self.deferred_si_cancels = {}
        self._relevant_objects = set()
        self._location_changed_targets = set()
        self.ignore_all_other_sis = ignore_all_other_sis
        self._pushed_mobile_posture_exit = False
        self.interaction.carry_sim_node = SimPostureNode(interaction.sim)
        self._has_deferred_putdown = False
        self._vehicle_transition_state = VehicleTransitionState.NO_STATE
        self._deployed_vehicle = None

    @property
    def has_deferred_putdown(self):
        return self._has_deferred_putdown

    @has_deferred_putdown.setter
    def has_deferred_putdown(self, value):
        self._has_deferred_putdown = value

    def __str__(self):
        if self.interaction.sim is not None:
            return 'TransitionSequence for {} {} on {}'.format(self.interaction.affordance.__name__, self.interaction.id, self.interaction.sim.full_name)
        return 'TransitionSequence for {} {} on Sim who is None'.format(self.interaction.affordance.__name__, self.interaction.id)

    @property
    def running(self):
        return self._running

    def with_current_transition(self, sim, posture_transition, sequence=()):

        def set_current_transition(_):
            if sim in self._current_transitions and self._current_transitions[sim] is not None:
                raise RuntimeError('{} attempting to do two posture transitions at the same time. \n   1: Dest State: {}, Source: {}\n   2: Dest State: {}, Source: {}'.format(sim, self._current_transitions[sim]._dest_state, self._current_transitions[sim]._source_interaction, posture_transition._dest_state, posture_transition._source_interaction))
            self._current_transitions[sim] = posture_transition

        def clear_current_transition(_):
            if self._current_transitions[sim] == posture_transition:
                self._current_transitions[sim] = None
            self._deployed_vehicle = None

        return build_critical_section_with_finally(set_current_transition, sequence, clear_current_transition)

    @property
    def succeeded(self):
        return self._success

    @property
    def canceled(self):
        return self._canceled

    @property
    def interaction(self):
        return self._interaction

    @property
    def sim(self):
        return self.interaction.sim

    @property
    def deployed_vehicle(self):
        if self._deployed_vehicle is not None:
            return self._deployed_vehicle()

    @staticmethod
    @caches.cached
    def _get_intended_location_from_spec(sim, path_spec):
        final_transition_spec = path_spec._path[-1]
        final_posture_spec = final_transition_spec.posture_spec
        posture_type = final_posture_spec[BODY_INDEX][BODY_POSTURE_TYPE_INDEX]
        if posture_type.has_mobile_entry_transition():
            final_posture_target = final_posture_spec[BODY_INDEX][BODY_TARGET_INDEX]
            posture = posture_type(sim, final_posture_target, postures.PostureTrack.BODY, is_throwaway=True)
            slot_constraint = posture.slot_constraint_simple
            if slot_constraint is not None:
                for sub_slot_constraint in slot_constraint:
                    final_transform = sub_slot_constraint.containment_transform
                    routing_surface = sub_slot_constraint.routing_surface
                    location = routing.Location(final_transform.translation, final_transform.orientation, routing_surface)
                    return location
        for transition_spec in reversed(path_spec._path):
            if transition_spec.path is not None:
                return transition_spec.path.final_location

    def intended_location(self, sim):
        if self.running and not (self.canceled or self.interaction.is_finishing or self.is_derailed(sim)):
            path_spec = self._get_path_spec(sim)
            if path_spec is not None and path_spec._path is not None:
                intended_location = self._get_intended_location_from_spec(sim, path_spec)
                if intended_location is not None:
                    return intended_location
        return sim.location

    def _clear_target_interaction(self):
        if self._target_interaction is not None:
            self._target_interaction.transition = None
            self._target_interaction.on_removed_from_queue()
            self._target_interaction = None

    def on_reset(self):
        self.end_transition()
        self.shutdown()

    def on_reset_early_detachment(self, obj, reset_reason):
        if reset_reason != ResetReason.BEING_DESTROYED and self.sim is not None:
            self.derail(DerailReason.NAVMESH_UPDATED, self.sim)

    def on_reset_add_interdependent_reset_records(self, obj, reset_reason, reset_records):
        if not self.interaction.should_reset_based_on_pipeline_progress:
            return
        if reset_reason == ResetReason.BEING_DESTROYED:
            for sim in self._sim_data:
                reset_records.append(ResetRecord(sim, ResetReason.RESET_EXPECTED, self, 'Relevant object for Transition.'))

    def derail(self, reason:DerailReason, sim, test_result=None):
        if self._success:
            return
        if self.interaction is sim.posture.source_interaction:
            return
        if gsi_handlers.posture_graph_handlers.archiver.enabled:
            gsi_handlers.posture_graph_handlers.archive_derailed_transition(sim, self.interaction, reason, test_result)
        self._derailed[sim] = reason
        if sim in self._current_transitions and self._current_transitions[sim] is not None:
            self._current_transitions[sim].trigger_soft_stop()

    def release_stand_slot_reservations(self, sims):
        for sim in sims:
            interaction = self.get_interaction_for_sim(sim)
            if interaction is not None:
                interaction.release_liabilities(liabilities_to_release=(STAND_SLOT_LIABILITY,))

    def sim_is_traversing_invalid_portal(self, sim):
        if sim not in self._sim_data:
            return False
        path_spec = self._sim_data[sim].path_spec
        if path_spec is None or not path_spec.path:
            return False
        specs_to_check = [path_spec.transition_specs[path_spec.path_progress]]
        if path_spec.path_progress > 0:
            specs_to_check.append(path_spec.transition_specs[path_spec.path_progress - 1])
        for spec in specs_to_check:
            if spec.portal_id is not None and spec.portal_obj is None:
                return True
        return False

    def get_interaction_for_sim(self, sim):
        participant_type = self.interaction.get_participant_type(sim)
        if participant_type == ParticipantType.Actor:
            return self.interaction
        elif participant_type in (ParticipantType.TargetSim, ParticipantType.CarriedObject):
            return self.interaction.get_target_si()[0]
        else:
            return
        return

    @contextmanager
    def deferred_derailment(self):
        derail = self.derail
        derailed = dict(self._derailed)

        def deferred_derail(reason, sim, test_result=None):
            derailed[sim] = reason

        self.derail = deferred_derail
        try:
            yield None
        finally:
            self.derail = derail
            self._derailed = derailed

    @macros.macro
    def _get_path_spec(self, sim):
        if sim in self._sim_data:
            return self._sim_data[sim].path_spec

    def is_multi_sim_path_spec(self, sim):
        path_spec = self._get_path_spec(sim)
        if path_spec is not None:
            dest_spec = path_spec.path[-1]
            if dest_spec is not None and dest_spec.body is not None:
                return dest_spec.body.posture_type.multi_sim
        return False

    def get_transition_specs(self, sim):
        path_spec = self._get_path_spec(sim)
        if path_spec is not None:
            return path_spec.transition_specs
        return path_spec

    def get_transitions_gen(self):
        for (sim, sim_data) in self._sim_data.items():
            if sim_data.progress >= TransitionSequenceStage.ROUTES:
                yield (sim, sim_data.path_spec.remaining_path)

    def get_transitioning_sims(self):
        if self._sim_data is None:
            return ()
        sims = set(self._sim_data.keys())
        sims.update(self.interaction.required_sims(for_threading=True))
        return sims

    def get_remaining_transitions(self, sim):
        path_spec = self._get_path_spec(sim)
        if path_spec is None:
            return []
        return path_spec.remaining_path

    def get_previous_spec(self, sim):
        path_spec = self._get_path_spec(sim)
        if path_spec is None:
            return []
        return path_spec.previous_posture_spec

    def advance_path(self, sim, prime_path=False):
        path_spec = self._get_path_spec(sim)
        if path_spec is postures.posture_graph.EMPTY_PATH_SPEC:
            return
        if path_spec is not None and prime_path and path_spec.path_progress == 0:
            path_spec.advance_path()

    def get_transition_spec(self, sim):
        path_spec = self._get_path_spec(sim)
        if path_spec is not None:
            return path_spec.get_transition_spec()

    def get_next_transition_spec(self, sim):
        path_spec = self._get_path_spec(sim)
        if path_spec is None:
            return
        transition_spec = path_spec.get_transition_spec()
        if transition_spec is None:
            return
        return path_spec.get_next_transition_spec(transition_spec)

    def get_transition_should_reserve(self, sim):
        path_spec = self._get_path_spec(sim)
        if path_spec is not None:
            return path_spec.get_transition_should_reserve()
        return False

    def get_destination_constraint(self, sim):
        path_spec = self._get_path_spec(sim)
        if path_spec is not None:
            return path_spec.final_constraint

    def get_var_map(self, sim):
        path_spec = self._get_path_spec(sim)
        if path_spec is None:
            return
        return path_spec.var_map

    def is_derailed(self, sim):
        if sim in self._derailed:
            return self._derailed[sim] != DerailReason.NOT_DERAILED
        return False

    @property
    def any_derailed(self):
        return any(v != DerailReason.NOT_DERAILED for v in self._derailed.values())

    def is_transition_active(self):
        if self._success or not self.canceled:
            return True
        return False

    def get_failure_reason_and_target(self, sim):
        (failure_reason, failure_object_id) = (None, None)
        path_spec = self._get_path_spec(sim)
        if path_spec is not None:
            (failure_reason, failure_object_id) = path_spec.get_failure_reason_and_object_id()
            if failure_reason is not None:
                if failure_reason == routing.FAIL_PATH_TYPE_OBJECT_BLOCKING:
                    failure_reason = TransitionFailureReasons.BLOCKING_OBJECT
                elif failure_reason == routing.FAIL_PATH_TYPE_BUILD_BLOCKING or failure_reason == routing.FAIL_PATH_TYPE_UNKNOWN or failure_reason == routing.FAIL_PATH_TYPE_UNKNOWN_BLOCKING:
                    failure_reason = TransitionFailureReasons.BUILD_BUY
        if sim in self._failure_target_and_reason:
            (failure_reason, failure_object_id) = self._failure_target_and_reason[sim]
        return (failure_reason, failure_object_id)

    def set_failure_target(self, sim, reason, target_id=None):
        if sim in self._failure_target_and_reason:
            return
        self._failure_target_and_reason[sim] = (reason, target_id)

    def add_stand_slot_reservation(self, sim, interaction, position, routing_surface):
        sim.routing_component.add_stand_slot_reservation(interaction, position, routing_surface, self.get_transitioning_sims())

    def _do(self, timeline, sim, *args):
        element = build_element(args)
        if element is None:
            return
        result = yield from element_utils.run_child(timeline, element)
        return result

    def _do_must(self, timeline, sim, *args):
        element = build_element(args)
        if element is None:
            return
        element = must_run(element)
        result = yield from element_utils.run_child(timeline, element)
        return result

    def on_owned_interaction_canceled(self, interaction):
        if interaction.is_social and self.interaction.is_social and interaction.social_group is self.interaction.social_group:
            return
        self.derail(DerailReason.PREEMPTED, interaction.sim)

    def cancel(self, finishing_type=None, cancel_reason_msg=None, test_result=None, si_to_cancel=None):
        if finishing_type is not None:
            if finishing_type == FinishingType.NATURAL:
                return True
            if finishing_type == FinishingType.USER_CANCEL:
                self.interaction.route_fail_on_transition_fail = False
        self._transition_canceled = True
        main_group = self.sim.get_main_group()
        if main_group is not None:
            main_group.remove_non_adjustable_sim(self.sim)
        defer_cancel = False
        for transition in self._current_transitions.values():
            if transition is None:
                pass
            elif transition.is_routing:
                transition.trigger_soft_stop()
            else:
                defer_cancel = True
        if self.interaction.running:
            defer_cancel = True
        if not (self.interaction.is_cancel_aop and defer_cancel):
            self.cancel_sequence(finishing_type=finishing_type, test_result=test_result)
        elif si_to_cancel not in self.deferred_si_cancels:
            self.deferred_si_cancels[si_to_cancel] = (finishing_type, cancel_reason_msg)
        return self.canceled

    def cancel_sequence(self, finishing_type=None, test_result=None):
        if not self.canceled:
            if gsi_handlers.posture_graph_handlers.archiver.enabled:
                gsi_handlers.posture_graph_handlers.archive_canceled_transition(self.interaction.sim, self.interaction, finishing_type, test_result)
            self._canceled = True
            transition_finishing_type = finishing_type or FinishingType.TRANSITION_FAILURE
            for interaction in list(self._running_transition_interactions):
                if interaction.sim.posture.source_interaction is interaction:
                    pass
                else:
                    interaction.cancel(transition_finishing_type, cancel_reason_msg='Transition Sequence Failed. Cancel all running transition interactions.')
            if not self.interaction.is_finishing:
                self.interaction.cancel(transition_finishing_type, cancel_reason_msg='Transition Sequence Failed. Cancel transition interaction.')
            for (si, cancel_info) in self.deferred_si_cancels.items():
                (finishing_type, cancel_reason_msg) = cancel_info
                si.cancel(finishing_type, cancel_reason_msg=cancel_reason_msg)
            self.deferred_si_cancels.clear()

    def final_destinations_gen(self):
        for sim_data in self._sim_data.values():
            if sim_data.final_destination is not None:
                yield sim_data.final_destination

    def get_final_constraint(self, sim):
        sim_data = self._sim_data.get(sim)
        if sim_data is None:
            return ANYWHERE
        else:
            if sim_data.path_spec is not None and sim_data.path_spec.final_constraint is not None:
                final_constraint = sim_data.path_spec.final_constraint
            else:
                final_constraint = sim_data.constraint[0]
            if final_constraint is None:
                return ANYWHERE
        return final_constraint

    @staticmethod
    def _is_set_valid(source_dest_sets):
        valid = False
        for source_dest_set in source_dest_sets.values():
            if source_dest_set[0] and source_dest_set[1]:
                valid = True
                break
        return valid

    def _is_putdown_interaction(self, target=None, interaction=None):
        interaction = interaction or self.interaction
        if not interaction.is_putdown:
            return False
        elif target is not None:
            carry_target = interaction.carry_target or interaction.target
            if carry_target is not target:
                return False
        return True

    def get_sims_with_invalid_paths(self):
        permanent_failure = True
        invalid_sims = set()
        for (sim, sim_data) in self._sim_data.items():
            if not any(sim_data.connectivity):
                invalid_sims.add(sim)
                if not sim_data.constraint:
                    pass
                elif self._tried_destinations[sim]:
                    pass
                else:
                    must_include_sis = list(sim.si_state.all_guaranteed_si_gen(self.interaction.priority, self.interaction.group_id))
                    if must_include_sis:
                        permanent_failure = False
                        (best_complete_path, source_destination_sets, source_middle_sets, middle_destination_sets) = sim_data.connectivity
                        if best_complete_path:
                            pass
                        elif source_destination_sets and self._is_set_valid(source_destination_sets):
                            pass
                        elif source_middle_sets and middle_destination_sets and self._is_set_valid(source_middle_sets):
                            pass
                        else:
                            invalid_sims.add(sim)
            else:
                (best_complete_path, source_destination_sets, source_middle_sets, middle_destination_sets) = sim_data.connectivity
                if best_complete_path:
                    pass
                elif source_destination_sets and self._is_set_valid(source_destination_sets):
                    pass
                elif source_middle_sets and middle_destination_sets and self._is_set_valid(source_middle_sets):
                    pass
                else:
                    invalid_sims.add(sim)
        if invalid_sims and permanent_failure:
            return set()
        if invalid_sims:
            self.cancel_incompatible_sis_given_final_posture_states()
        return invalid_sims

    def estimate_distance_for_current_progress(self):
        yield_to_irq()
        sim = self.interaction.sim
        sim_data = self._sim_data[sim]
        included_sis = sim_data.constraint[1] or set()
        if self.interaction.teleporting:
            return (0, True, included_sis)
        if sim_data.progress < TransitionSequenceStage.CONNECTIVITY:
            return (None, False, set())
        if sim_data.progress == TransitionSequenceStage.CONNECTIVITY:
            if len(self.interaction.object_reservation_tests):
                for valid_destination in sim_data.valid_dest_nodes:
                    if valid_destination.body_target.may_reserve(sim):
                        break
                return (None, False, set())
            (distance, posture_change) = self._estimate_distance_for_connectivity(sim)
            return (distance, posture_change, included_sis)
        if sim_data.progress > TransitionSequenceStage.CONNECTIVITY:
            path_spec = sim_data.path_spec
            if path_spec is EMPTY_PATH_SPEC or path_spec.is_failure_path:
                return (None, False, set())
            if path_spec.completed_path:
                return (0, False, included_sis)
            return (path_spec.total_cost, True, included_sis)
        return (None, False, set())

    def _estimate_distance_for_connectivity(self, sim):
        connectivity = self._sim_data[sim].connectivity
        (best_complete_path, source_destination_sets, source_middle_sets, _) = connectivity
        if best_complete_path:
            return (0, False)
        if source_destination_sets or not source_middle_sets:
            return (None, False)
        min_distance = sims4.math.MAX_FLOAT
        if source_destination_sets and source_middle_sets:
            routing_sets = source_destination_sets if any(source_handles and destination_handles for (source_handles, destination_handles, _, _, _, _) in source_destination_sets.values()) else source_middle_sets
        else:
            routing_sets = source_destination_sets or source_middle_sets
        for (source_handles, destination_handles, _, _, _, _) in routing_sets.values():
            left_handles = set(source_handles.keys())
            right_handles = set(destination_handles.keys())
            if left_handles:
                if not right_handles:
                    pass
                else:
                    yield_to_irq()
                    if DEFAULT in right_handles:
                        min_distance = 0.0
                    else:
                        distances = routing.estimate_path_batch(left_handles, right_handles, routing_context=sim.routing_context)
                        if not distances:
                            pass
                        else:
                            for (left_handle, right_handle, distance) in distances:
                                if distance is not None and distance < min_distance:
                                    min_distance = distance + left_handle.path.cost + right_handle.path.cost
        if min_distance == sims4.math.MAX_FLOAT:
            return (None, False)
        return (min_distance, True)

    def get_included_sis(self):
        included_sis = set()
        for sim_data in self._sim_data.values():
            included_sis_sim = sim_data.constraint[1]
            if included_sis_sim:
                for included_si_sim in included_sis_sim:
                    if included_si_sim is self.interaction:
                        pass
                    else:
                        included_sis.add(included_si_sim)
        return included_sis

    def add_blocked_si(self, blocked_si):
        self._blocked_sis.append(blocked_si)

    def _wait_for_violators(self, timeline, blocked_sims):
        cancel_functions = CallableList()

        def wait_for_violators(timeline):
            then = services.time_service().sim_now
            while True:
                for blocked_si in self._blocked_sis[:]:
                    handler = blocked_si.get_interaction_reservation_handler(sim=self.sim)
                    if handler is None:
                        pass
                    elif handler.may_reserve():
                        self._blocked_sis.remove(blocked_si)
                if self._blocked_sis and self._blocked_sis or not any(blocked_sim.routing_component.get_stand_slot_reservation_violators() for blocked_sim in blocked_sims):
                    cancel_functions()
                    return
                now = services.time_service().sim_now
                timeout = self.SIM_MINUTES_TO_WAIT_FOR_VIOLATORS
                if self.canceled or now - then > clock.interval_in_sim_minutes(timeout):
                    for blocked_sim in blocked_sims:
                        self.derail(DerailReason.TRANSITION_FAILED, blocked_sim)
                    del self._blocked_sis[:]
                    cancel_functions()
                    return
                yield timeline.run_child(elements.SleepElement(date_and_time.create_time_span(minutes=1)))

        idle_work = [elements.GeneratorElement(wait_for_violators)]
        for blocked_sim in blocked_sims:
            (idle, cancel_fn) = blocked_sim.get_idle_element()
            cancel_functions.append(cancel_fn)
            idle_work.append(idle)
        yield from self._do(timeline, self.sim, elements.AllElement(idle_work))

    def reset_derailed_transitions(self):
        sims_to_reset = []
        moved_social_group = False
        for (sim, derailed_reason) in self._derailed.items():
            if not derailed_reason is None:
                if derailed_reason == DerailReason.NOT_DERAILED:
                    pass
                else:
                    if self._derailed[sim] != DerailReason.TRANSITION_FAILED:
                        for tried_destinations_sim in self._tried_destinations:
                            self._tried_destinations[tried_destinations_sim].clear()
                    else:
                        final_destination = self._sim_data[sim].final_destination
                        if final_destination is not None:
                            tried_dests = {dest for dest in self._sim_data[sim].valid_dest_nodes if dest.body_target is final_destination.body_target}
                            self._tried_destinations[sim] |= tried_dests
                    if derailed_reason != DerailReason.PRIVACY_ENGAGED:
                        sims_to_reset.append(sim)
                        if self._original_interaction_target_changed:
                            self.interaction.set_target(self._original_interaction_target)
                            self._original_interaction_target = None
                            self._original_interaction_target_changed = False
                    if self.interaction.social_group is not None:
                        self.interaction.social_group.refresh_social_geometry()
                        moved_social_group = True
                    self._derailed[sim] = DerailReason.NOT_DERAILED
                    if moved_social_group or derailed_reason in MOVING_DERAILS and self.interaction.is_social and derailed_reason == DerailReason.NAVMESH_UPDATED_BY_BUILD:
                        (location, _) = sim.get_location_on_nearest_surface_below()
                        if not sim.validate_location(location):
                            sim.schedule_reset_asap(reset_reason=ResetReason.RESET_EXPECTED, source=self, cause='Sim is in invalid location during transition.')
        for sim in sims_to_reset:
            self.set_sim_progress(sim, TransitionSequenceStage.EMPTY)
        if sims_to_reset:
            self.interaction.refresh_constraints()
            self.release_stand_slot_reservations(sims_to_reset)
        self._has_tried_bring_group_along = False

    def _validate_transitions(self):
        for sim_data in self._sim_data.values():
            if not sim_data.path_spec is None:
                if sim_data.path_spec is postures.posture_graph.EMPTY_PATH_SPEC:
                    self.cancel()
            self.cancel()

    def end_transition(self):
        if self._sim_data is not None:
            for sim_data in self._sim_data.values():
                included_sis = sim_data.constraint[1]
                if included_sis is None:
                    pass
                else:
                    for included_si in included_sis:
                        included_si.transition = None
                        included_si.owning_transition_sequences.discard(self)
        self._clear_target_interaction()
        if self._sim_data is not None:
            for (sim, sim_data) in self._sim_data.items():
                if sim_data.path_spec is not None:
                    sim_data.path_spec.cleanup_path_spec(sim)

    def shutdown(self):
        self._clear_relevant_objects()
        self._clear_target_location_changed_callbacks()
        if self._sim_data is not None:
            for sim in self._sim_data:
                self._clear_owned_transition(sim)
                social_group = sim.get_main_group()
                if social_group is not None and not sims4.math.transform_almost_equal(sim.intended_transform, sim.transform, epsilon=sims4.geometry.ANIMATION_SLOT_EPSILON):
                    social_group.refresh_social_geometry(sim=sim)
        if self._success or self.canceled:
            self.reset_all_progress()
            self.cancel_incompatible_sis_given_final_posture_states()
        services.current_zone().all_transition_controllers.discard(self)

    def cancel_incompatible_sis_given_final_posture_states(self):
        interaction = self.interaction
        if interaction is None or not interaction.cancel_incompatible_with_posture_on_transition_shutdown:
            return
        cancel_reason_msg = "Incompatible with Sim's final transform."
        for sim in self.get_transitioning_sims():
            sim.evaluate_si_state_and_cancel_incompatible(FinishingType.INTERACTION_INCOMPATIBILITY, cancel_reason_msg)

    def _clear_cancel_by_posture_change(self):
        for sim_data in self._sim_data.values():
            if sim_data.final_included_sis:
                for si in sim_data.final_included_sis:
                    si.disable_cancel_by_posture_change = False

    def _clear_owned_transition(self, sim):
        sim_data = self._sim_data.get(sim)
        if sim_data.final_included_sis:
            for included_si in sim_data.final_included_sis:
                included_si.owning_transition_sequences.discard(self)
        included_sis = sim_data.constraint[1]
        if included_sis:
            for included_si in included_sis:
                included_si.owning_transition_sequences.discard(self)

    def _get_carry_transference_work(self):
        carry_transference_work_begin = collections.defaultdict(list)
        for sim in self._sim_data:
            for si in sim.si_state:
                if si._carry_transfer_animation is None:
                    pass
                else:
                    end_carry_transfer = si.get_carry_transfer_end_element()
                    carry_transference_work_begin[si.sim].append(build_critical_section(end_carry_transfer, flush_all_animations))
        carry_transference_sis = set()
        for sim_data in self._sim_data.values():
            additional_templates = sim_data.templates[1]
            if additional_templates:
                carry_transference_sis.update(additional_templates.keys())
            carry_si = sim_data.templates[2]
            if carry_si is not None:
                carry_transference_sis.add(carry_si)
        carry_transference_sis.discard(self.interaction)
        carry_transference_work_end = collections.defaultdict(list)
        for si in carry_transference_sis:
            if si._carry_transfer_animation is None:
                pass
            else:
                begin_carry_transfer = si.get_carry_transfer_begin_element()
                carry_transference_work_end[si.sim].append(build_critical_section(begin_carry_transfer, flush_all_animations))
        return (carry_transference_work_begin, carry_transference_work_end)

    def _get_animation_work(self, animation):
        return (animation(self._interaction, sequence=()), flush_all_animations)

    def get_final_included_sis_for_sim(self, sim):
        if sim not in self._sim_data:
            return
        return self._sim_data[sim].final_included_sis

    def get_tried_dest_nodes_for_sim(self, sim):
        return self._tried_destinations[sim]

    def get_sims_in_sim_data(self):
        return self._sim_data

    def compute_transition_connectivity(self):
        gen = self.run_transitions(None, progress_max=TransitionSequenceStage.CONNECTIVITY)
        try:
            next(gen)
            logger.error('run_transitions yielded when computing connectivity.')
        except StopIteration as exc:
            return exc.value

    def run_transitions(self, timeline, progress_max=TransitionSequenceStage.COMPLETE):
        logger.debug('{}: Running.', self)
        callback_utils.invoke_callbacks(callback_utils.CallbackEvent.TRANSITION_SEQUENCE_ENTER)
        try:
            self._running = True
            self._progress_max = progress_max
            self.reset_derailed_transitions()
            self._add_interaction_target_location_changed_callback()
            for required_sim in self.get_transitioning_sims():
                sim_data = self._sim_data.get(required_sim)
                if sim_data is None or sim_data.progress < progress_max:
                    break
            return True
            sim = self.interaction.get_participant(ParticipantType.Actor)
            services.current_zone().all_transition_controllers.add(self)
            if progress_max < TransitionSequenceStage.COMPLETE or not self.interaction.disable_transitions:
                yield from self._build_transitions(timeline)
            if self.any_derailed:
                return False
            if progress_max < TransitionSequenceStage.COMPLETE:
                services.current_zone().all_transition_controllers.discard(self)
                return True
            if self.interaction.disable_transitions:
                result = yield from self.run_super_interaction(timeline, self.interaction)
                return result
            self._validate_transitions()
            (target_si, test_result) = self.interaction.get_target_si()
            if not test_result:
                self.cancel(FinishingType.FAILED_TESTS, test_result=test_result)
            if self.canceled:
                (failure_reason, failure_target) = self.get_failure_reason_and_target(sim)
                if failure_reason is not None or failure_target is not None:
                    yield from self._do(timeline, sim, handle_transition_failure(sim, self.interaction.target, self.interaction, failure_reason=failure_reason, failure_object_id=failure_target))
                return False
            if target_si.set_as_added_to_queue():
                target_si.transition = self
                self._target_interaction = target_si
            for sim_data in self._sim_data.values():
                if sim_data.final_included_sis:
                    for si in sim_data.final_included_sis:
                        si.disable_cancel_by_posture_change = True
            (carry_transference_work_begin, carry_transference_work_end) = self._get_carry_transference_work()
            if target_si is not None and carry_transference_work_begin:
                yield from self._do_must(timeline, self.sim, do_all(thread_element_map=carry_transference_work_begin))
            self._worker_all_element = elements.AllElement([build_element(self._create_next_elements)])
            result = yield from self._do(timeline, None, self._worker_all_element)
            if carry_transference_work_end:
                yield from self._do_must(timeline, self.sim, do_all(thread_element_map=carry_transference_work_end))
            if progress_max == TransitionSequenceStage.COMPLETE:
                blocked_sims = set()
                for (blocked_sim, reason) in self._derailed.items():
                    if reason == DerailReason.WAIT_FOR_BLOCKING_SIMS:
                        blocked_sims.add(blocked_sim)
                if blocked_sims:
                    yield from self._wait_for_violators(timeline, blocked_sims)
            if not self._success:
                if self._transition_canceled:
                    self.cancel()
                if self.canceled or self.is_derailed(self._interaction.sim):
                    result = False
            if result:
                for (_, transition) in self.get_transitions_gen():
                    if transition:
                        result = False
                        break
            if not self._shortest_path_success[sim]:
                derail_reason = self._derailed.get(sim)
                if derail_reason != DerailReason.WAIT_TO_BE_PUT_DOWN:
                    self.cancel()
                return False
            if result:
                self._success = True
                if not self.interaction.is_finishing:
                    should_replace_posture_source = SuperInteraction.should_replace_posture_source_interaction(self.interaction)
                    would_replace_nonfinishing = should_replace_posture_source and not self.sim.posture.source_interaction.is_finishing
                    if would_replace_nonfinishing and not self.interaction.is_cancel_aop:
                        self.sim.posture.source_interaction.merge(self.interaction)
                        self.interaction.cancel(FinishingType.TRANSITION_FAILURE, 'Transition Sequence. Replace posture source non-finishing.')
                    elif len(sim_data.path_spec.transition_specs) == 1 and not sim_data.path_spec.transition_specs[0].do_reservation(self.sim):
                        self.sim.posture.source_interaction.merge(self.interaction)
                        self.interaction.cancel(FinishingType.TRANSITION_FAILURE, 'Transition Sequence. Reservation failed.')
                    else:
                        self.interaction.apply_posture_state(self.interaction.sim.posture_state)
                        result = yield from self.run_super_interaction(timeline, self.interaction)
        except:
            logger.debug('{} RAISED EXCEPTION.', self)
            self._exited_due_to_exception = True
            for sim in self._sim_jobs:
                logger.warn('Terminating transition for Sim {}', sim)
            for sim in self._sim_idles:
                logger.warn('Terminating transition idle for Sim {}', sim)
            self._sim_jobs.clear()
            self._sim_idles.clear()
            raise
        finally:
            if self._transition_canceled:
                self.cancel()
            logger.debug('{} DONE.', self)
            self._clear_cancel_by_posture_change()
            if progress_max == TransitionSequenceStage.COMPLETE:
                sims_to_update_intended_location = set()
                for sim in self.get_transitioning_sims():
                    if not sims4.math.transform_almost_equal(sim.intended_transform, sim.transform, epsilon=sims4.geometry.ANIMATION_SLOT_EPSILON):
                        sims_to_update_intended_location.add(sim)
                        for (_, _, carry_object) in get_carried_objects_gen(sim):
                            if carry_object.is_sim:
                                sims_to_update_intended_location.add(carry_object)
                self.shutdown()
                for sim in sims_to_update_intended_location:
                    sim.routing_component.on_intended_location_changed(sim.intended_location)
                if not self.any_derailed:
                    self.cancel_incompatible_sis_given_final_posture_states()
                callback_utils.invoke_callbacks(callback_utils.CallbackEvent.TRANSITION_SEQUENCE_EXIT)
                if self._interaction.must_run:
                    for sim in self.get_transitioning_sims():
                        if self.is_derailed(sim):
                            break
                    logger.warn('Failed to plan a must run interaction {}', self.interaction, owner='tastle')
                    for sim in self.get_transitioning_sims():
                        self.sim.reset(ResetReason.RESET_EXPECTED, self, 'Failed to plan must run.')
            self._worker_all_element = None
            self._running = False
        if self._sim_jobs:
            raise AssertionError('Transition Sequence: Attempted to exit when there were still existing jobs. [tastle]')
        return self._success

    @staticmethod
    def choose_hand_and_filter_specs(sim, posture_specs_and_vars, carry_target, used_hand_and_target=None):
        new_specs_and_vars = []
        already_matched = set()
        used_hand = None
        used_hand_target = None
        left_carry_target = sim.posture_state.left.target
        right_carry_target = sim.posture_state.right.target
        chosen_hand = None
        if left_carry_target == carry_target and carry_target is not None:
            chosen_hand = Hand.LEFT
        elif right_carry_target == carry_target and carry_target is not None:
            chosen_hand = Hand.RIGHT
        elif left_carry_target is None and right_carry_target is not None:
            chosen_hand = Hand.LEFT
        elif right_carry_target is None and left_carry_target is not None:
            chosen_hand = Hand.RIGHT
        elif used_hand_and_target is not None:
            (used_hand, used_hand_target) = used_hand_and_target
            if carry_target is used_hand_target:
                chosen_hand = used_hand
            else:
                chosen_hand = Hand.LEFT if used_hand != Hand.LEFT else Hand.RIGHT
        elif carry_target is not None:
            allowed_hands = carry_target.get_allowed_hands(sim)
            if len(allowed_hands) == 1:
                chosen_hand = allowed_hands[0]
        if chosen_hand is None:
            allowed_hands = set()
            for (_, posture_spec_vars, _) in posture_specs_and_vars:
                required_hand = posture_spec_vars.get(PostureSpecVariable.HAND)
                if required_hand is not None:
                    allowed_hands.add(required_hand)
            if used_hand is not None:
                allowed_hands.discard(used_hand)
            preferred_hand = sim.get_preferred_hand()
            if allowed_hands and preferred_hand in allowed_hands:
                chosen_hand = preferred_hand
            else:
                chosen_hand = allowed_hands.pop()
            if chosen_hand is None:
                logger.error('Failed to find a valid hand for {}', carry_target)
        elif carry_target is not None:
            allowed_hands = carry_target.get_allowed_hands(sim)
            try:
                if chosen_hand not in allowed_hands:
                    chosen_hand = allowed_hands[0]
            except:
                logger.exception('Sim {} failed to find a hand to carry object {}', sim, carry_target)
        if chosen_hand == used_hand and carry_target is not used_hand_target:
            return (new_specs_and_vars, chosen_hand)
        hand_map = {PostureSpecVariable.HAND: chosen_hand}
        for (index_a, (posture_spec_template_a, posture_spec_vars_a, constraint_a)) in enumerate(posture_specs_and_vars):
            if index_a in already_matched:
                pass
            else:
                found_match = False
                if PostureSpecVariable.HAND in posture_spec_vars_a:
                    for (index_b, (posture_spec_template_b, posture_spec_vars_b, constraint_b)) in enumerate(posture_specs_and_vars[index_a + 1:]):
                        real_index_b = index_b + index_a + 1
                        if posture_spec_template_a != posture_spec_template_b:
                            pass
                        elif carry_target is not None:
                            is_sim = getattr(carry_target, 'is_sim', False)
                            if is_sim:
                                hand_a = posture_spec_vars_a.get(PostureSpecVariable.HAND)
                                hand_b = posture_spec_vars_b.get(PostureSpecVariable.HAND)
                                if hand_a == hand_b and constraint_a.geometry != constraint_b.geometry:
                                    pass
                                else:
                                    vars_match = True
                                    for (key_a, var_a) in posture_spec_vars_a.items():
                                        if key_a == PostureSpecVariable.HAND:
                                            pass
                                        else:
                                            if not key_a not in posture_spec_vars_b:
                                                if posture_spec_vars_b[key_a] != var_a:
                                                    vars_match = False
                                                    break
                                            vars_match = False
                                            break
                                    if not vars_match:
                                        pass
                                    else:
                                        found_match = True
                                        already_matched.add(real_index_b)
                                        cur_posture_vars = frozendict(posture_spec_vars_a, hand_map)
                                        hand_constraint = create_carry_constraint(carry_target, hand=chosen_hand)
                                        constraint_new = constraint_a.intersect(hand_constraint)
                                        if not constraint_new.valid:
                                            constraint_new = constraint_b.intersect(hand_constraint)
                                        if constraint_new.valid:
                                            new_specs_and_vars.append((posture_spec_template_a, cur_posture_vars, constraint_new))
                            else:
                                vars_match = True
                                for (key_a, var_a) in posture_spec_vars_a.items():
                                    if key_a == PostureSpecVariable.HAND:
                                        pass
                                    else:
                                        if not key_a not in posture_spec_vars_b:
                                            if posture_spec_vars_b[key_a] != var_a:
                                                vars_match = False
                                                break
                                        vars_match = False
                                        break
                                if not vars_match:
                                    pass
                                else:
                                    found_match = True
                                    already_matched.add(real_index_b)
                                    cur_posture_vars = frozendict(posture_spec_vars_a, hand_map)
                                    hand_constraint = create_carry_constraint(carry_target, hand=chosen_hand)
                                    constraint_new = constraint_a.intersect(hand_constraint)
                                    if not constraint_new.valid:
                                        constraint_new = constraint_b.intersect(hand_constraint)
                                    if constraint_new.valid:
                                        new_specs_and_vars.append((posture_spec_template_a, cur_posture_vars, constraint_new))
                        else:
                            vars_match = True
                            for (key_a, var_a) in posture_spec_vars_a.items():
                                if key_a == PostureSpecVariable.HAND:
                                    pass
                                else:
                                    if not key_a not in posture_spec_vars_b:
                                        if posture_spec_vars_b[key_a] != var_a:
                                            vars_match = False
                                            break
                                    vars_match = False
                                    break
                            if not vars_match:
                                pass
                            else:
                                found_match = True
                                already_matched.add(real_index_b)
                                cur_posture_vars = frozendict(posture_spec_vars_a, hand_map)
                                hand_constraint = create_carry_constraint(carry_target, hand=chosen_hand)
                                constraint_new = constraint_a.intersect(hand_constraint)
                                if not constraint_new.valid:
                                    constraint_new = constraint_b.intersect(hand_constraint)
                                if constraint_new.valid:
                                    new_specs_and_vars.append((posture_spec_template_a, cur_posture_vars, constraint_new))
                if not (index_a + 1 < len(posture_specs_and_vars) and found_match):
                    cur_posture_vars = frozendict(posture_spec_vars_a, hand_map)
                    new_specs_and_vars.append((posture_spec_template_a, cur_posture_vars, constraint_a))
        return (new_specs_and_vars, chosen_hand)

    @staticmethod
    def resolve_constraint_for_hands(sim, interaction, interaction_constraint, context=None):
        if not interaction_constraint.valid:
            return interaction_constraint
        if context is not None:
            carry_target = context.carry_target
        else:
            carry_target = interaction.carry_target
        hand_is_immutable = dict(zip((Hand.LEFT, Hand.RIGHT), (o is not None and o is not carry_target for o in sim.posture_state.carry_targets)))
        if not any(hand_is_immutable.values()):
            return interaction_constraint
        new_constraints = []
        for constraint in interaction_constraint:
            if constraint._posture_state_spec is None or not constraint._posture_state_spec.posture_manifest:
                new_constraints.append(constraint)
            else:
                valid_manifest_entries = PostureManifest()
                for entry in constraint._posture_state_spec.posture_manifest:
                    (hand, entry_carry_target) = entry.carry_hand_and_target
                    if hand_is_immutable.get(hand, False):
                        if entry_carry_target != AnimationParticipant.CREATE_TARGET:
                            valid_manifest_entries.add(entry)
                    valid_manifest_entries.add(entry)
                if not valid_manifest_entries:
                    pass
                else:
                    valid_manifest_constraint = Constraint(posture_state_spec=PostureStateSpec(valid_manifest_entries, SlotManifest().intern(), None))
                    test_constraint = constraint.intersect(valid_manifest_constraint)
                    if not test_constraint.valid:
                        pass
                    else:
                        new_constraints.append(test_constraint)
        new_constraint = create_constraint_set(new_constraints)
        return new_constraint

    @staticmethod
    def _get_specs_for_constraints(sim, interaction, interaction_constraint, pick=None, carry_target=None, used_hand_and_target=None):
        target = interaction.target
        create_target = interaction.create_target
        if any(sim.posture_state.carry_targets):

            def remove_references_to_unrelated_carried_objects(obj, default):
                if obj != None and obj != carry_target and obj in sim.posture_state.carry_targets:
                    return MATCH_ANY
                return default

        else:
            remove_references_to_unrelated_carried_objects = None
        posture_specs_and_vars = interaction_constraint.get_posture_specs(remove_references_to_unrelated_carried_objects, interaction=interaction)
        (posture_specs_and_vars, used_hand) = TransitionSequenceController.choose_hand_and_filter_specs(sim, posture_specs_and_vars, carry_target, used_hand_and_target=used_hand_and_target)
        templates = collections.defaultdict(list)
        for (posture_spec_template, posture_spec_vars, constraint) in posture_specs_and_vars:
            if any(isinstance(v, PostureSpecVariable) for v in posture_spec_vars.values()):
                logger.error('posture_spec_vars contains a variable as a value: {}', posture_spec_vars)
            else:
                posture_spec_vars_updates = {}
                if PostureSpecVariable.INTERACTION_TARGET not in posture_spec_vars:
                    if interaction.target_type == TargetType.FILTERED_TARGET:
                        posture_spec_vars_updates[PostureSpecVariable.INTERACTION_TARGET] = PostureSpecVariable.BODY_TARGET_FILTERED
                    else:
                        posture_spec_vars_updates[PostureSpecVariable.INTERACTION_TARGET] = target
                if PostureSpecVariable.CARRY_TARGET not in posture_spec_vars:
                    posture_spec_vars_updates[PostureSpecVariable.CARRY_TARGET] = carry_target
                if posture_spec_vars.get(PostureSpecVariable.SLOT_TEST_DEFINITION) == AnimationParticipant.CREATE_TARGET:
                    posture_spec_vars_updates[PostureSpecVariable.SLOT_TEST_DEFINITION] = create_target
                if posture_spec_vars_updates:
                    posture_spec_vars += posture_spec_vars_updates
                if interaction is not None and (interaction.posture_preferences is not None and (interaction.posture_preferences.prefer_clicked_part and pick is not None)) and pick.target is not None:
                    best_parts = pick.target.get_closest_parts_to_position(pick.location, posture_spec=posture_spec_template)
                    interaction.add_preferred_objects(best_parts)
                templates[constraint].append((posture_spec_template, posture_spec_vars))
        return (templates, used_hand)

    @staticmethod
    def get_templates_including_carry_transference(sim, interaction, interaction_constraint, included_sis, participant_type):
        potential_carry_sis = set()
        for si in included_sis:
            if not si.has_active_cancel_replacement:
                potential_carry_sis.add(si)
        carried_object_transfers = []
        for carry_posture in sim.posture_state.carry_aspects:
            if carry_posture.target is None:
                pass
            else:
                if carry_posture.owning_interactions:
                    carry_interactions = carry_posture.owning_interactions
                else:
                    carry_interactions = [carry_posture.source_interaction]
                for carry_interaction in carry_interactions:
                    if carry_interaction is not None and carry_posture is not None:
                        valid_targets = {carry_interaction.target}
                        if carry_interaction.staging:
                            valid_targets.add(carry_interaction.carry_target)
                        if carry_posture.target in valid_targets and carry_interaction in potential_carry_sis:
                            carried_object_transfers.append(carry_interaction)
                            for owning_interaction in carry_posture.owning_interactions:
                                potential_carry_sis.discard(owning_interaction)
                            potential_carry_sis.discard(carry_posture.source_interaction)
        for si in potential_carry_sis:
            if not si.is_finishing:
                if si.has_active_cancel_replacement:
                    pass
                else:
                    for constraint in si.constraint_intersection(posture_state=None):
                        if constraint.posture_state_spec is not None and constraint.posture_state_spec.slot_manifest:
                            potential_carry_target = si.carry_target
                            if potential_carry_target is not None and potential_carry_target is si.target:
                                carried_object_transfers.append(si)
                                break
        carry_target = interaction.carry_target
        if carry_target is None or carry_target.definition != interaction.create_target.definition:
            carry_target = interaction.create_target
        if interaction.should_carry_create_target() and interaction.create_target is not None and interaction.disable_transitions:
            carry_target = None
        if carry_target is not None:
            carry_target_si = interaction
            carry_target_constraint = interaction_constraint
        else:
            carry_target_si = None
            carry_target_constraint = None
        TSC = TransitionSequenceController
        constraint_resolver = interaction.get_constraint_resolver(None, participant_type=participant_type)
        additional_constraint_list = {}
        if carried_object_transfers:
            for carry_si in reversed(carried_object_transfers):
                cancel_aop_liability = carry_si.get_liability(CANCEL_AOP_LIABILITY)
                if cancel_aop_liability is not None and cancel_aop_liability.interaction_to_cancel is interaction:
                    pass
                else:
                    carry_constraint = carry_si.constraint_intersection(posture_state=None)
                    carry_constraint_resolved = TSC.resolve_constraint_for_hands(sim, carry_si, carry_constraint)
                    carry_constraint_resolved = carry_constraint_resolved.apply_posture_state(None, constraint_resolver)
                    additional_constraint_list[carry_si] = carry_constraint_resolved
                    carry_target_additional = carry_si.carry_target
                    if not carry_target is None:
                        if sim.posture_state.get_carry_track(carry_target_additional) is None and (sim.posture_state.get_carry_track(carry_target) is not None and carry_target is not interaction.carry_target) and carry_target is not interaction.target:
                            carry_target = carry_target_additional
                            carry_target_si = carry_si
                            carry_target_constraint = carry_constraint_resolved
                    carry_target = carry_target_additional
                    carry_target_si = carry_si
                    carry_target_constraint = carry_constraint_resolved
        if carry_target_si is not None and carry_target_si is not interaction:
            template_constraint = interaction_constraint.intersect(carry_target_constraint)
            del additional_constraint_list[carry_target_si]
        else:
            template_constraint = interaction_constraint
        (templates, used_hand) = TSC._get_specs_for_constraints(sim, interaction, template_constraint, pick=interaction.context.pick, carry_target=carry_target)
        additional_template_list = {}
        for (carry_si, carry_constraint_resolved) in additional_constraint_list.items():
            (carry_constraint_templates, _) = TSC._get_specs_for_constraints(sim, carry_si, carry_constraint_resolved, pick=interaction.context.pick, carry_target=carry_si.carry_target, used_hand_and_target=(used_hand, carry_target))
            additional_template_list[carry_si] = carry_constraint_templates
        return (templates, additional_template_list, carry_target_si)

    def _get_constraint_for_interaction(self, sim, interaction, participant_type, ignore_inertial, ignore_combinables):
        interaction_raw_constraint = interaction.constraint_intersection(sim=sim, participant_type=participant_type, posture_state=None)
        if gsi_handlers.posture_graph_handlers.archiver.enabled:
            gsi_handlers.posture_graph_handlers.add_possible_constraints(sim, interaction_raw_constraint, 'Interaction')
        interaction_constraint = interaction.transition_constraint_intersection(sim, participant_type, interaction_raw_constraint)
        if gsi_handlers.posture_graph_handlers.archiver.enabled:
            gsi_handlers.posture_graph_handlers.add_possible_constraints(sim, interaction_constraint, 'Interaction Transition')
        if not interaction_constraint.valid:
            return (interaction_constraint, ())
        interaction_constraint_resolved = self.resolve_constraint_for_hands(sim, self.interaction, interaction_constraint)
        if not interaction_constraint_resolved.valid:
            included_sis = [carry_si for carry_si in sim.si_state if sim.posture_state.is_carry_source_or_owning_interaction(carry_si)]
            return (interaction_constraint_resolved, included_sis)
        if self.ignore_all_other_sis:
            return (interaction_constraint, ())
        additional_included_sis = set()
        if not ignore_combinables:
            final_valid_combinables = interaction.get_combinable_interactions_with_safe_carryables()
            if interaction.sim is sim:
                test_intersection = interaction_constraint_resolved
                interaction_constraint_no_holster = interaction.constraint_intersection(sim=sim, participant_type=participant_type, posture_state=None, allow_holster=False)
                interaction_constraint_no_holster = interaction.transition_constraint_intersection(sim, participant_type, interaction_constraint_no_holster)
                for combinable in final_valid_combinables:
                    if combinable is interaction:
                        pass
                    else:
                        combinable_constraint = combinable.constraint_intersection(sim=sim, posture_state=None)
                        if not combinable_constraint.valid:
                            break
                        test_intersection = test_intersection.intersect(combinable_constraint)
                        if not test_intersection.valid:
                            break
                        interaction_constraint_resolved = test_intersection
                        if combinable.targeted_carryable is not None:
                            test_intersection_no_holster = interaction_constraint_no_holster.intersect(combinable_constraint)
                            if test_intersection_no_holster.valid:
                                additional_included_sis.add(combinable)
                                additional_included_sis.add(combinable)
                        else:
                            additional_included_sis.add(combinable)
        if gsi_handlers.posture_graph_handlers.archiver.enabled:
            gsi_handlers.posture_graph_handlers.add_possible_constraints(sim, interaction_constraint_resolved, 'Interaction Resolved')
        force_inertial_sis = self.interaction.posture_preferences.require_current_constraint or self.interaction.is_adjustment_interaction()
        if force_inertial_sis:
            ignore_inertial = False
        (si_constraint, included_sis) = sim.si_state.get_best_constraint_and_sources(interaction_constraint_resolved, self.interaction, force_inertial_sis, ignore_inertial=ignore_inertial, participant_type=participant_type)
        if additional_included_sis:
            included_sis.update(additional_included_sis)
        if si_constraint.valid or interaction.is_cancel_aop:
            return (interaction_constraint_resolved, [])
        if gsi_handlers.posture_graph_handlers.archiver.enabled:
            gsi_handlers.posture_graph_handlers.add_possible_constraints(sim, si_constraint, 'SI Constraint')
        if not si_constraint.valid:
            if self._progress_max == TransitionSequenceStage.COMPLETE:
                self.derail(DerailReason.CONSTRAINTS_CHANGED, sim)
            return (si_constraint, included_sis)
        si_constraint_geometry_only = si_constraint.generate_geometry_only_constraint()
        if gsi_handlers.posture_graph_handlers.archiver.enabled:
            gsi_handlers.posture_graph_handlers.add_possible_constraints(sim, si_constraint_geometry_only, 'Geometry Only')
        combined_constraint = interaction_constraint_resolved.intersect(si_constraint_geometry_only)
        if gsi_handlers.posture_graph_handlers.archiver.enabled:
            gsi_handlers.posture_graph_handlers.add_possible_constraints(sim, combined_constraint, 'Int Resolved + Geometry')
        si_constraint_body_posture_only = si_constraint.generate_body_posture_only_constraint()
        final_constraint = combined_constraint.intersect(si_constraint_body_posture_only)
        body_aspect = sim.posture_state.body
        if not final_constraint.supports_mobile_posture(body_aspect.posture_type):
            posture_graph_service = services.current_zone().posture_graph_service
            posture_object = posture_graph_service.get_compatible_mobile_posture_target(sim)
            if posture_object is not None:
                self._pushed_mobile_posture_exit = True
                edge_constraint = posture_object.get_edge_constraint(sim=sim)
                final_constraint = final_constraint.generate_constraint_with_new_geometry(edge_constraint.geometry, routing_surface=edge_constraint.routing_surface)
        if body_aspect.mobile and body_aspect.posture_type is not SIM_DEFAULT_POSTURE_TYPE and (any(sub_constraint.geometry is not None for sub_constraint in final_constraint) or (interaction.is_cancel_aop or self.involves_specific_surface_or_body_target(final_constraint)) or gsi_handlers.posture_graph_handlers.archiver.enabled):
            gsi_handlers.posture_graph_handlers.add_possible_constraints(sim, final_constraint, 'Pre Revised Constraint')
        return (final_constraint, included_sis)

    def has_geometry_outside_pool(self, constraint, sim):
        ray_projection_distance = 0.5
        pool = pool_utils.get_pool_by_block_id(sim.block_id)
        pool_center = pool.center_point
        zone = services.current_zone()
        for sub_constraint in constraint:
            sub_routing_surfaces = sub_constraint.get_all_valid_routing_surfaces()
            if not sub_routing_surfaces:
                pass
            else:
                for sub_surface in sub_routing_surfaces:
                    if sub_surface is None or not sub_surface.type == routing.SurfaceType.SURFACETYPE_POOL:
                        if sub_constraint.geometry is None:
                            pass
                        else:
                            for polygon in sub_constraint.geometry.polygon:
                                for polygon_corner in polygon:
                                    if build_buy.is_location_pool(zone.id, polygon_corner, sub_surface.secondary_id):
                                        pass
                                    else:
                                        polygon_corner_2d = sims4.math.Vector2(polygon_corner.x, polygon_corner.z)
                                        v = pool_center - polygon_corner_2d
                                        u = sims4.math.vector_normalize(v)
                                        new_point = polygon_corner_2d + ray_projection_distance*u
                                        new_position = sims4.math.Vector3(new_point.x, 0, new_point.y)
                                        if not build_buy.is_location_pool(zone.id, new_position, sub_surface.secondary_id):
                                            new_routing_location = routing.Location(new_position, sims4.math.Quaternion.ZERO(), sub_surface)
                                            if routing.test_connectivity_pt_pt(sim.routing_location, new_routing_location, sim.routing_context):
                                                return True
        return False

    def involves_specific_surface_or_body_target(self, constraint):
        for sub_constraint in constraint:
            posture_state_spec = sub_constraint.posture_state_spec
            if not posture_state_spec.body_target is None:
                if isinstance(posture_state_spec.body_target, PostureSpecVariable):
                    return False
            return False
        return True

    def get_graph_test_functions(self, sim, target_sim, target_path_spec):
        sim_data = self._sim_data[sim]
        target_transitions = None
        if target_path_spec is not None:
            target_transitions = target_path_spec.path
        if target_transitions:
            body_index = BODY_INDEX
            body_posture_type_index = BODY_POSTURE_TYPE_INDEX
            body_target_index = BODY_TARGET_INDEX
            previous_transition = None
            for target_transition in reversed(target_transitions):
                target_posture_target = target_transition[body_index][body_target_index]
                if target_transition[body_index][body_posture_type_index].multi_sim:
                    break
                if target_transition[body_index][body_posture_type_index].mobile:
                    target_posture_target = previous_transition[body_index][body_target_index]
                    break
                previous_transition = target_transition
            target_posture_target = target_transitions[-1][body_index][body_target_index]
        else:
            target_posture_target = None

        def valid_destination_test(destination_spec, var_map):

            def is_valid_destination():
                dest_body = destination_spec[BODY_INDEX]
                dest_body_target = dest_body[BODY_TARGET_INDEX]
                dest_body_posture_type = dest_body[BODY_POSTURE_TYPE_INDEX]
                if sim in self._tried_destinations:
                    for tried_destination_spec in self._tried_destinations[sim]:
                        if dest_body_target == tried_destination_spec[BODY_INDEX][BODY_TARGET_INDEX]:
                            return False
                if dest_body_target is not None and sim in self._tried_destinations and destination_spec in self._tried_destinations[sim]:
                    return False
                if destination_spec in sim_data.valid_dest_nodes:
                    return True
                if target_sim is None and dest_body_posture_type.multi_sim and sim.posture.posture_type is not dest_body_posture_type:
                    return False
                for additional_destination_validity_test in self.interaction.additional_destination_validity_tests:
                    if not additional_destination_validity_test(dest_body_target):
                        return False
                if dest_body_target is None:
                    return True
                if not dest_body_posture_type.is_valid_destination_target(sim, dest_body_target, adjacent_sim=target_sim, adjacent_target=target_posture_target):
                    return False
                elif dest_body_target.is_part and not dest_body_target.supports_posture_spec(destination_spec, self.interaction, sim=sim):
                    return False
                return True

            result = is_valid_destination()
            if result:
                sim_data.valid_dest_nodes.add(destination_spec)
            return result

        body_index = BODY_INDEX
        body_posture_type_index = BODY_POSTURE_TYPE_INDEX
        valid_edge_test = None
        if target_transitions is not None:
            for (transition_index, target_transition) in enumerate(target_transitions):
                target_transition_posture_type = target_transition[body_index][body_posture_type_index]
                if target_transition_posture_type.multi_sim and target_transition_posture_type.require_parallel_entry_transition:
                    previous_target_transition = target_transitions[transition_index - 1]
                    previous_target_transition_posture_type = previous_target_transition[body_index][body_posture_type_index]

                    def valid_edge_test(node_a, node_b):
                        posture_type_a = node_a[body_index][body_posture_type_index]
                        posture_type_b = node_b[body_index][body_posture_type_index]
                        if posture_type_b is target_transition_posture_type:
                            return posture_type_a is previous_target_transition_posture_type or posture_type_a is PostureTuning.SIM_CARRIED_POSTURE
                        elif posture_type_a.multi_sim or posture_type_b.multi_sim:
                            return target_path_spec.edge_exists(posture_type_a, posture_type_b)
                        return True

                    break
            if len(target_transitions) > 1:

                def valid_edge_test(node_a, node_b):
                    if self._interaction.carry_target is sim:
                        node_b_body_target = node_b.body.target
                        if node_b_body_target is not None and node_b_body_target.is_sim and node_b_body_target is not self._interaction.sim:
                            return False
                        else:
                            posture_type_a = node_a[body_index][body_posture_type_index]
                            posture_type_b = node_b[body_index][body_posture_type_index]
                            b_requires_parallel_entry = posture_type_b.multi_sim and posture_type_b.require_parallel_entry_transition
                            if b_requires_parallel_entry:
                                return target_path_spec.edge_exists(posture_type_a, posture_type_b)
                    else:
                        posture_type_a = node_a[body_index][body_posture_type_index]
                        posture_type_b = node_b[body_index][body_posture_type_index]
                        b_requires_parallel_entry = posture_type_b.multi_sim and posture_type_b.require_parallel_entry_transition
                        if b_requires_parallel_entry:
                            return target_path_spec.edge_exists(posture_type_a, posture_type_b)
                    return True

        elif target_sim is None:

            def valid_edge_test(node_a, node_b):
                if node_b[body_index][body_posture_type_index].multi_sim:
                    if node_a[body_index][body_posture_type_index].multi_sim:
                        return True
                    else:
                        return False
                return True

        preferred_carrying_sim = self._interaction.context.preferred_carrying_sim
        if preferred_carrying_sim in (self._interaction.sim, self._interaction.target, self._interaction.carry_target):
            preferred_carrying_sim = None
        if preferred_carrying_sim is not None:
            _valid_edge_test = valid_edge_test

            def valid_edge_test(node_a, node_b):
                if _valid_edge_test is not None:
                    result = _valid_edge_test(node_a, node_b)
                    if not result:
                        return result
                    elif node_b.body.target is not None and node_b.body.target.is_sim and node_b.body.target is not preferred_carrying_sim:
                        return False
                elif node_b.body.target is not None and node_b.body.target.is_sim and node_b.body.target is not preferred_carrying_sim:
                    return False
                return True

        if self._is_putdown_interaction(target=sim):
            put_down_body_target = target_transitions[-1][BODY_INDEX][BODY_TARGET_INDEX]
            _valid_edge_test2 = valid_edge_test

            def valid_edge_test(node_a, node_b):
                if _valid_edge_test2 is not None:
                    result = _valid_edge_test2(node_a, node_b)
                    if not result:
                        return result
                    else:
                        node_a_target = node_a.body.target
                        if node_a_target is not None and node_a_target.is_sim:
                            node_b_target = node_b.body.target
                            if node_b_target is not node_a_target and node_b_target is not put_down_body_target:
                                return False
                else:
                    node_a_target = node_a.body.target
                    if node_a_target is not None and node_a_target.is_sim:
                        node_b_target = node_b.body.target
                        if node_b_target is not node_a_target and node_b_target is not put_down_body_target:
                            return False
                return True

        return (valid_destination_test, valid_edge_test)

    def _combine_preferences(self, sim, interaction, included_sis):
        preferences = interaction.combined_posture_preferences
        posture_preferences = PosturePreferencesData(preferences.apply_penalties, preferences.prefer_surface, preferences.require_current_constraint, preferences.posture_cost_overrides)
        combined_preferences = sims4.collections.AttributeDict(vars(posture_preferences))
        for si in included_sis:
            if si.has_active_cancel_replacement:
                pass
            else:
                si_preferences = si.combined_posture_preferences
                combined_preferences.apply_penalties = si_preferences.apply_penalties or combined_preferences.apply_penalties
                combined_preferences.prefer_surface = si_preferences.prefer_surface or combined_preferences.prefer_surface
                combined_preferences.require_current_constraint = si_preferences.require_current_constraint or combined_preferences.require_current_constraint
                for (entry, value) in si_preferences.posture_cost_overrides.items():
                    if combined_preferences.posture_cost_overrides.get(entry):
                        combined_preferences.posture_cost_overrides[entry] += value
                    else:
                        combined_preferences.posture_cost_overrides[entry] = value
        for (posture, score) in sim.Buffs.get_additional_posture_costs().items():
            if combined_preferences.posture_cost_overrides.get(posture):
                combined_preferences.posture_cost_overrides[posture] += score
            else:
                combined_preferences.posture_cost_overrides[posture] = score
        return sims4.collections.FrozenAttributeDict(combined_preferences)

    @property
    def relevant_objects(self):
        return self._relevant_objects

    def add_relevant_object(self, obj):
        if obj is None or isinstance(obj, PostureSpecVariable) or obj.is_sim:
            return
        relevant_object = obj.part_owner if obj.is_part else obj
        if relevant_object not in self._relevant_objects:
            relevant_object.register_transition_controller(self)
            self._relevant_objects.add(relevant_object)

    def _add_interaction_target_location_changed_callback(self):
        target = self.interaction.target
        if target is None:
            return
        if target.is_sim:
            return
        routing_component = target.routing_component
        if routing_component is None:
            return
        self.add_on_target_location_changed_callback(target)

    def add_on_target_location_changed_callback(self, target):
        target = target.part_owner if target.is_part else target
        if target not in self._location_changed_targets:
            target.register_on_location_changed(self._target_location_changed)
            self._location_changed_targets.add(target)

    def _target_location_changed(self, obj, *args, **kwargs):
        carry_target = self.interaction.carry_target
        if carry_target is not None:
            carry_target = carry_target.part_owner if carry_target.is_part else carry_target
        interaction_target = self.interaction.target
        if interaction_target is not None:
            interaction_target = interaction_target.part_owner if interaction_target.is_part else interaction_target
        if carry_target is obj or interaction_target is obj:
            if self.interaction.sim is None:
                logger.error('Trying to derail a transition for interaction {} with a None Sim', self.interaction, owner='camilogarcia')
            else:
                self.derail(DerailReason.CONSTRAINTS_CHANGED, self.interaction.sim)
        else:
            obj.unregister_on_location_changed(self._target_location_changed)
            self._location_changed_targets.remove(obj)

    def _clear_target_location_changed_callbacks(self):
        for target in self._location_changed_targets:
            target.unregister_on_location_changed(self._target_location_changed)
        self._location_changed_targets.clear()

    def _clear_relevant_objects(self):
        for obj in self._relevant_objects:
            if obj is not None and not obj.is_sim:
                obj.unregister_transition_controller(self)
        self._relevant_objects.clear()

    def remove_relevant_object(self, obj):
        if obj is None or obj.is_sim:
            return
        relevant_obj = obj.part_owner if obj.is_part else obj
        if relevant_obj not in self._relevant_objects:
            return
        relevant_obj.unregister_transition_controller(self)
        self._relevant_objects.remove(relevant_obj)

    def will_derail_if_given_object_is_reset(self, obj):
        if self.succeeded or obj in self._relevant_objects:
            return True
        return False

    def get_transitions_for_sim(self, *args, **kwargs):
        if not inject_interaction_name_in_callstack:
            result = yield from self._get_transitions_for_sim(*args, **kwargs)
            return result
        name = self.interaction.__class__.__name__.replace('-', '_')
        name_f = create_custom_named_profiler_function(name, use_generator=True)
        result = yield from name_f(lambda : self._get_transitions_for_sim(*args, **kwargs))
        return result

    def _get_transitions_for_sim(self, timeline, sim, target_sim=None, target_path_spec=None, ignore_inertial=False, ignore_combinables=False):
        global global_plan_lock
        if sim is None:
            return postures.posture_graph.EMPTY_PATH_SPEC
        participant_type = self.interaction.get_participant_type(sim)
        interaction = self.interaction
        is_putdown = self._is_putdown_interaction(target=sim)
        sim_data = self._sim_data[sim]
        sim_data.progress_max = self._progress_max
        (final_constraint, included_sis) = sim_data.constraint
        if final_constraint is None:
            if is_putdown:
                (constraint_interaction, _) = interaction.get_target_si()
                constraint_interaction_participant_type = ParticipantType.Actor
            else:
                constraint_interaction = interaction
                constraint_interaction_participant_type = participant_type
            (final_constraint, included_sis) = self._get_constraint_for_interaction(sim, constraint_interaction, constraint_interaction_participant_type, ignore_inertial, ignore_combinables)
            if self.is_derailed(sim):
                return postures.posture_graph.EMPTY_PATH_SPEC
            final_constraint = self._revise_final_constraint(sim, final_constraint, interaction)
            if not final_constraint.valid:
                included_sis = list(sim.si_state.all_guaranteed_si_gen(priority=self.interaction.priority, group_id=self.interaction.group_id))
            sim_data.constraint = (final_constraint, included_sis)
            for si in included_sis:
                si.owning_transition_sequences.add(self)
            if gsi_handlers.interaction_archive_handlers.is_archive_enabled(self._interaction) and sim is interaction.sim:
                gsi_handlers.interaction_archive_handlers.add_constraint(interaction, sim, final_constraint)
        if final_constraint is ANYWHERE:
            if gsi_handlers.posture_graph_handlers.archiver.enabled:
                gsi_handlers.posture_graph_handlers.archive_current_spec_valid(sim, self.interaction)
            if self.interaction.outfit_change is not None and self.interaction.outfit_change.on_route_change is not None:
                path_nodes = [sim.posture_state.spec, sim.posture_state.spec]
            else:
                path_nodes = [sim.posture_state.spec]
            path = postures.posture_graph.PathSpec(path_nodes, 0, {}, sim.posture_state.spec, final_constraint, final_constraint)
            if sim_data.progress_max >= TransitionSequenceStage.CONNECTIVITY:
                sim_data.connectivity = postures.posture_graph.Connectivity(path, None, None, None)
                sim_data.progress = TransitionSequenceStage.CONNECTIVITY
            if sim_data.progress_max >= TransitionSequenceStage.ROUTES:
                sim_data.progress = TransitionSequenceStage.ROUTES
                sim_data.path_spec = path
            return path
        if not final_constraint.valid:
            self.set_failure_target(sim, TransitionFailureReasons.NO_VALID_INTERSECTION, None)
            self._shortest_path_success[sim] = False
            path = postures.posture_graph.EMPTY_PATH_SPEC
            if sim_data.progress_max >= TransitionSequenceStage.ROUTES:
                sim_data.progress = TransitionSequenceStage.ROUTES
                sim_data.path_spec = path
            return path
        if sim_data.progress >= TransitionSequenceStage.TEMPLATES:
            (templates, additional_template_list, carry_target_si) = sim_data.templates
        else:
            (templates, additional_template_list, carry_target_si) = self.get_templates_including_carry_transference(sim, interaction, final_constraint, included_sis, participant_type)
            if gsi_handlers.posture_graph_handlers.archiver.enabled:
                gsi_handlers.posture_graph_handlers.add_possible_constraints(sim, final_constraint, 'Final Constraint')
            sim_data.templates = (templates, additional_template_list, carry_target_si)
            sim_data.progress = TransitionSequenceStage.TEMPLATES
        (valid_destination_test, valid_edge_test) = self.get_graph_test_functions(sim, target_sim, target_path_spec)
        posture_graph = services.current_zone().posture_graph_service
        if sim_data.progress >= TransitionSequenceStage.PATHS:
            segmented_paths = sim_data.segmented_paths
        else:
            preferences = self._combine_preferences(sim, interaction, included_sis)
            segmented_paths = posture_graph.get_segmented_paths(sim, templates, additional_template_list, interaction, participant_type, valid_destination_test, valid_edge_test, preferences, final_constraint, included_sis)
            sim_data.progress = TransitionSequenceStage.PATHS
            sim_data.segmented_paths = segmented_paths
            sim_data.intended_location = sim.get_intended_location_excluding_transition(self)
        if not segmented_paths:
            self._shortest_path_success[sim] = False
            return postures.posture_graph.EMPTY_PATH_SPEC
        all_destinations = set().union(*(sp.destinations for sp in segmented_paths))
        if sim_data.progress_max < TransitionSequenceStage.CONNECTIVITY:
            return postures.posture_graph.EMPTY_PATH_SPEC
        if sim_data.progress >= TransitionSequenceStage.CONNECTIVITY:
            connectivity = sim_data.connectivity
        else:
            postures.posture_graph.set_transition_destinations(self.sim, {}, {})
            resolve_animation_participant = self.interaction.get_constraint_resolver(None)
            connectivity = posture_graph.generate_connectivity_handles(sim, segmented_paths, interaction, participant_type, resolve_animation_participant)
            sim_data.connectivity = connectivity
            sim_data.progress = TransitionSequenceStage.CONNECTIVITY
        if interaction.teleporting:
            path = posture_graph.handle_teleporting_path(segmented_paths)
            if sim_data.progress_max >= TransitionSequenceStage.ROUTES:
                sim_data.path_spec = path
                sim_data.progress = TransitionSequenceStage.ROUTES
            (_, source_dest_sets, _, _) = connectivity
            for (_, destination_handles, _, _, _, _) in source_dest_sets.values():
                for dest_data in destination_handles.values():
                    (_, _, _, _, dest_goals, _, _) = dest_data
                    if interaction.dest_goals is not None:
                        interaction.dest_goals.extend(dest_goals)
            return path
        if interaction.disable_transitions:
            return
        if self._progress_max < TransitionSequenceStage.ROUTES:
            return
        success = False
        path_spec = postures.posture_graph.EMPTY_PATH_SPEC
        while global_plan_lock:
            yield from element_utils.run_child(timeline, elements.BusyWaitElement(soft_sleep_forever(), path_plan_allowed))
        global_plan_lock = sim.ref()
        try:
            (success, path_spec) = yield from posture_graph.find_best_path_pair(self.interaction, sim, connectivity, timeline)
            if gsi_handlers.posture_graph_handlers.archiver.enabled:
                gsi_handlers.posture_graph_handlers.log_possible_segmented_paths(sim, segmented_paths)
            if success or path_spec.failed_path_type != PathType.MIDDLE_LEFT and (path_spec.failed_path_type != PathType.MIDDLE_RIGHT and all_destinations - self._tried_destinations[sim]) and path_spec.destination_spec is not None:
                if self._failure_path_spec is None:
                    self._failure_path_spec = path_spec
                sim_data.final_destination = path_spec.destination_spec
                self.derail(DerailReason.TRANSITION_FAILED, sim)
                return postures.posture_graph.EMPTY_PATH_SPEC
            path_spec.finalize(sim)
            additional_sis = posture_graph.handle_additional_pickups_and_putdowns(path_spec, additional_template_list, sim)
            defer_carry = any(node.body.posture_type.mobile for node in path_spec.path)
            if not defer_carry:
                should_derail = not self._interaction.cancel_incompatible_carry_interactions(can_defer_putdown=False, derail_actors=True)
                if should_derail:
                    self.derail(DerailReason.WAIT_FOR_CARRY_TARGET, sim)
            current_path = path_spec.remaining_original_transition_specs()
            if current_path:
                sim_data.path_spec = path_spec
                destination_node = current_path[-1]
                sim_data.final_destination = destination_node.posture_spec
                all_included_sis = set(included_sis)
                if carry_target_si is not None and carry_target_si is not self.interaction:
                    all_included_sis.add(carry_target_si)
                all_included_sis.update(additional_sis)
                sim_data.final_included_sis = all_included_sis
                for si in all_included_sis:
                    si.owning_transition_sequences.add(self)
                if sim is self.interaction.sim and destination_node.var_map:
                    self._original_interaction_target = self.interaction.target
                    self._original_interaction_target_changed = True
                    self.interaction.apply_var_map(sim, destination_node.var_map)
                if destination_node.mobile:
                    self.interaction.locked_params += destination_node.locked_params
                if not (destination_node.locked_params and transform_almost_equal(sim.intended_location.transform, sim.location.transform, epsilon=sims4.geometry.ANIMATION_SLOT_EPSILON)):
                    sim.routing_component.on_intended_location_changed(sim.intended_location)
                    for (_, _, carry_object) in get_carried_objects_gen(sim):
                        if carry_object.is_sim:
                            carry_object.routing_component.on_intended_location_changed(sim.intended_location)
                if final_constraint.create_jig_fn is not None:
                    final_constraint.create_jig_fn(sim, intended_location=sim.intended_location)
            else:
                path_spec = postures.posture_graph.EMPTY_PATH_SPEC
                sim_data.path_spec = path_spec
            sim_data.progress = TransitionSequenceStage.ROUTES
            self._shortest_path_success[sim] = success
            return path_spec
        finally:
            global_plan_lock = None

    @staticmethod
    def _revise_final_constraint(sim, final_constraint, interaction):
        if not final_constraint.valid:
            return final_constraint
        new_constraints = []
        for constraint in final_constraint:
            posture_state_spec = constraint._posture_state_spec
            if posture_state_spec is None:
                new_constraints.append(constraint)
            else:
                new_posture_manifest = set()
                for posture_manifest_entry in posture_state_spec.posture_manifest:
                    specific_posture = posture_manifest_entry.posture_type_specific
                    if specific_posture is not None:
                        new_posture_manifest.add(posture_manifest_entry)
                    else:
                        family = posture_manifest_entry.family
                        posture_family = POSTURE_FAMILY_MAP.get(family)
                        if not posture_family:
                            if family == '*' or family == '':
                                return final_constraint
                            logger.error("No postures in the '{}' family. Interaction {}.", family, interaction, owner='manus')
                        for specific in posture_family:
                            if not specific.is_canonical_family_posture:
                                if sim.posture.posture_type is specific:
                                    new_entry = posture_manifest_entry.clone(family=None, specific=specific._posture_name)
                                    new_posture_manifest.add(new_entry)
                            new_entry = posture_manifest_entry.clone(family=None, specific=specific._posture_name)
                            new_posture_manifest.add(new_entry)
                if not new_posture_manifest:
                    logger.error('While evaluating interaction {}, could not find any substitutions for {}', interaction, final_constraint, owner='manus')
                    return final_constraint
                else:
                    body_target_in_spec = posture_state_spec.body_target
                    if posture_state_spec.is_vehicle_only_spec():
                        parented_vehicle = sim.parented_vehicle
                        if parented_vehicle is not None:
                            body_target_in_spec = parented_vehicle
                    new_posture_state_spec = PostureStateSpec(FrozenPostureManifest(new_posture_manifest), posture_state_spec.slot_manifest, body_target_in_spec)
                    new_constraint = constraint.generate_constraint_with_posture_spec(new_posture_state_spec)
                    new_constraints.append(new_constraint)
                    new_final_constraint = create_constraint_set(new_constraints)
                    if not ((body_target_in_spec is None or body_target_in_spec == PostureSpecVariable.ANYTHING) and new_final_constraint.valid):
                        logger.error('While evaluating interaction {}, _revise_final_constraint created an invalid constraint {}.', interaction, new_final_constraint, owner='manus')
                        return final_constraint
        new_final_constraint = create_constraint_set(new_constraints)
        if not new_final_constraint.valid:
            logger.error('While evaluating interaction {}, _revise_final_constraint created an invalid constraint {}.', interaction, new_final_constraint, owner='manus')
            return final_constraint
        return new_final_constraint

    def set_sim_progress(self, sim, progress:TransitionSequenceStage):
        if sim not in self._sim_data:
            return
        sim_data = self._sim_data[sim]
        if progress > sim_data.progress:
            raise RuntimeError('Attempt to set progress for a Sim forwards: {} > {}'.format(progress, sim_data.progress))
        if progress < TransitionSequenceStage.ACTOR_TARGET_SYNC:
            sim_data.progress = TransitionSequenceStage.ROUTES
        if progress < TransitionSequenceStage.ROUTES:
            self._shortest_path_success[sim] = True
            if sim_data.path_spec is not None:
                sim_data.path_spec.cleanup_path_spec(sim)
                sim_data.path_spec = None
            del self._blocked_sis[:]
        if progress < TransitionSequenceStage.PATHS:
            sim_data.valid_dest_nodes = set()
            sim_data.final_destination = None
            sim_data.segmented_paths = None
        if progress < TransitionSequenceStage.CONNECTIVITY:
            sim_data.connectivity = (None, None, None, None)
        if progress < TransitionSequenceStage.TEMPLATES:
            self._clear_owned_transition(sim)
            if sim_data.final_included_sis is not None:
                for si in sim_data.final_included_sis:
                    si.disable_cancel_by_posture_change = False
                sim_data.final_included_sis = None
            sim_data.intended_location = None
            sim_data.constraint = (None, None)
            sim_data.templates = (None, None, None)
        sim_data.progress = progress

    def reset_sim_progress(self, sim):
        sim_data = self._sim_data.get(sim)
        if sim_data is not None:
            self.set_sim_progress(sim, TransitionSequenceStage.EMPTY)
            sim.queue.clear_head_cache()

    def reset_all_progress(self):
        if self._sim_data is not None:
            for sim in self._sim_data:
                self.reset_sim_progress(sim)

    def _build_and_log_transitions_for_sim(self, timeline, sim, required=True, **kwargs):
        path_spec = yield from self._build_transitions_for_sim(timeline, sim, required=required, **kwargs)
        if gsi_handlers.posture_graph_handlers.archiver.enabled:
            try:
                gsi_handlers.posture_graph_handlers.archive_path(sim, path_spec, self._shortest_path_success[sim], self._progress_max)
            except:
                logger.exception('GSI Transition Archive Failed.')
        return path_spec

    def _build_transitions_for_sim(self, timeline, sim, required=True, **kwargs):
        sim_data = self._sim_data.get(sim)
        if sim_data is None:
            sim_data = TransitionSequenceData()
            self._sim_data[sim] = sim_data
        else:
            needs_reset = False
            if sim_data.path_spec is not EMPTY_PATH_SPEC:
                current_state = sim.posture_state.get_posture_spec(sim_data.path_spec.var_map)
                current_path = sim_data.path_spec.path
                if not current_path[0].same_spec_ignoring_surface_if_mobile(current_state):
                    needs_reset = True
            intended_location_built = sim_data.intended_location
            if intended_location_built is not None:
                intended_location_current = sim.get_intended_location_excluding_transition(self)
                if sims4.math.transform_almost_equal_2d(intended_location_built.transform, intended_location_current.transform, epsilon=sims4.geometry.ANIMATION_SLOT_EPSILON) and intended_location_built.routing_surface != intended_location_current.routing_surface:
                    needs_reset = True
            if not (sim_data.path_spec is not None and needs_reset or needs_reset):
                (_, included_sis) = sim_data.constraint
                if included_sis:
                    needs_reset = any(si.is_finishing for si in included_sis)
            if sim_data.progress >= TransitionSequenceStage.PATHS:
                segmented_paths = sim_data.segmented_paths
                needs_reset = segmented_paths and not all(segmented_path.check_validity(sim) for segmented_path in segmented_paths)
            if needs_reset or needs_reset:
                self.reset_sim_progress(sim)
        if sim_data.path_spec is not None:
            if sim_data.progress < TransitionSequenceStage.ROUTES:
                raise RuntimeError('Sim has path specs but progress < ROUTES')
            return sim_data.path_spec
        if gsi_handlers.posture_graph_handlers.archiver.enabled:
            gsi_handlers.posture_graph_handlers.set_current_posture_interaction(sim, self.interaction)
        path_spec = yield from self.get_transitions_for_sim(timeline, sim, **kwargs)
        if self.is_derailed(sim):
            return path_spec
        if path_spec is EMPTY_PATH_SPEC:
            if self.interaction.combinable_interactions:
                self.set_sim_progress(sim, TransitionSequenceStage.EMPTY)
                path_spec = yield from self.get_transitions_for_sim(timeline, sim, ignore_combinables=True, **kwargs)
                if self.is_derailed(sim):
                    return path_spec
            if path_spec is EMPTY_PATH_SPEC:
                must_include_sis = list(sim.si_state.all_guaranteed_si_gen(self.interaction.priority, self.interaction.group_id))
                if not must_include_sis:
                    self.set_sim_progress(sim, TransitionSequenceStage.EMPTY)
                    path_spec = yield from self.get_transitions_for_sim(timeline, sim, ignore_inertial=True, ignore_combinables=True, **kwargs)
                    if self.is_derailed(sim):
                        return path_spec
        if self._progress_max < TransitionSequenceStage.COMPLETE or self.interaction.disable_transitions:
            return path_spec
        if self._failure_path_spec is not None and path_spec is EMPTY_PATH_SPEC:
            self._sim_data[sim].path_spec = self._failure_path_spec
            self._failure_path_spec.generate_transition_interactions(sim, self.interaction, transition_success=self._shortest_path_success[sim])
            return self._failure_path_spec
        current_path = path_spec.remaining_path
        if not current_path:
            current_state = None
            if sim is not None and required and self.sim is sim:
                logger.info('{} could not find transitions for {}.', self, sim)
                self.cancel(test_result='No path found for sim.')
        else:
            current_state = sim.posture_state.get_posture_spec(path_spec.var_map)
            path_spec.flag_slot_reservations()
            if self._is_putdown_interaction(target=sim):
                (transition_interaction, _) = self.interaction.get_target_si()
            else:
                transition_interaction = self.interaction
            result = path_spec.generate_transition_interactions(sim, transition_interaction, transition_success=self._shortest_path_success[sim])
            if not result:
                logger.info('{} failed to generate transitions for {}.', self, sim)
                self.cancel(test_result='Failed to generate transition interactions for sequence.')
        if not current_path[0][BODY_INDEX][BODY_POSTURE_TYPE_INDEX].unconstrained:
            path_spec.completed_path = True
        return path_spec

    @staticmethod
    def do_paths_share_body_target(path_spec_a, path_spec_b, exception_fn=None):
        if path_spec_b is not None:
            for node_a in path_spec_a.path:
                if node_a.body_target is not None:
                    for node_b in path_spec_b.path:
                        if node_a.body_target is node_b.body_target:
                            if exception_fn is not None and exception_fn(node_a, node_b):
                                pass
                            else:
                                return True
        return False

    def _build_transitions(self, timeline):
        if gsi_handlers.posture_graph_handlers.archiver.enabled:
            gsi_handlers.posture_graph_handlers.increment_build_pass(self.sim, self.interaction)
            gsi_handlers.posture_graph_handlers.add_tried_destinations(self.sim, self.interaction, self._tried_destinations)
        actor = self.interaction.get_participant(ParticipantType.Actor)
        if self.interaction.carry_target is not None and self.interaction.carry_target.is_sim:
            target = self.interaction.carry_target
        else:
            target = self.interaction.get_participant(ParticipantType.TargetSim)
        services.current_zone().posture_graph_service.update_generic_sim_carry_node(actor)
        if self.interaction.is_target_sim_location_and_posture_valid():
            if target in self._sim_data:
                self.set_sim_progress(target, TransitionSequenceStage.EMPTY)
                del self._sim_data[target]
            target = None
        actor_path_spec = yield from self._build_and_log_transitions_for_sim(timeline, actor, target_sim=target)
        if not ((target not in self.interaction.required_sims(for_threading=True) or self.interaction.is_social) and self._shortest_path_success[actor]):
            return
        if self._has_tried_bring_group_along or self._progress_max == TransitionSequenceStage.COMPLETE:
            main_group = self.sim.get_main_group()
            if main_group is not None and (main_group.has_social_geometry(self.sim) and self.interaction.context.source == InteractionSource.PIE_MENU) and not self.interaction.is_social:
                main_group.add_non_adjustable_sim(self.sim)
            self._has_tried_bring_group_along = True
            if self.interaction.should_rally:
                self._interaction.maybe_bring_group_along()
            elif self.interaction.relocate_main_group and main_group is not None:
                main_group.try_relocate_around_focus(self.sim)
        if target is not None and actor_path_spec is not None:
            with create_puppet_postures(target):
                target_path_spec = yield from self._build_and_log_transitions_for_sim(timeline, target, target_sim=actor, target_path_spec=actor_path_spec)
                if not self._shortest_path_success[target]:
                    if self._shortest_path_success[actor]:
                        self.derail(DerailReason.TRANSITION_FAILED, actor)
                        self.derail(DerailReason.TRANSITION_FAILED, target)
                    return
                if not self._is_putdown_interaction():
                    carry_target = self._interaction.carry_target
                    if carry_target is not None and carry_target.is_sim:

                        def exception_fn(actor_node, target_node):
                            if actor_node.body.posture_type is postures.posture_graph.SIM_DEFAULT_POSTURE_TYPE:
                                return True
                            return False

                    elif actor.posture.target is not None and actor.posture.target is target.posture.target:

                        def exception_fn(actor_node, target_node):
                            if actor_node == actor_path_spec.path[0]:
                                return True
                            return False

                    else:
                        exception_fn = None
                    if TransitionSequenceController.do_paths_share_body_target(actor_path_spec, target_path_spec, exception_fn=exception_fn):
                        self.derail(DerailReason.TRANSITION_FAILED, actor)
                        self.derail(DerailReason.TRANSITION_FAILED, target)
                        return
        else:
            target_path_spec = None
        for sim in self.get_transitioning_sims():
            if sim is not actor and sim is not target and sim in self.interaction.get_participants(ParticipantType.AllSims):
                yield from self._build_and_log_transitions_for_sim(timeline, sim, required=False)
        if self._progress_max < TransitionSequenceStage.ROUTES or self.interaction.disable_transitions or self.any_derailed:
            return
        actor_data = self._sim_data[actor]
        if target is not None:
            target_data = self._sim_data[target]
        if target_path_spec.path:
            body_index = BODY_INDEX
            body_posture_type_index = BODY_POSTURE_TYPE_INDEX
            for transition in actor_path_spec.path:
                if not transition[body_index][body_posture_type_index].multi_sim:
                    if self.interaction.require_shared_body_target:
                        if actor_path_spec.cost <= target_path_spec.cost:
                            self.set_sim_progress(target, TransitionSequenceStage.TEMPLATES)
                            with create_puppet_postures(target):
                                target_path_spec = yield from self._build_and_log_transitions_for_sim(timeline, target, target_sim=actor, target_path_spec=actor_path_spec)
                                if self.is_derailed(target):
                                    return
                        else:
                            self.set_sim_progress(actor, TransitionSequenceStage.TEMPLATES)
                            actor_path_spec = yield from self._build_and_log_transitions_for_sim(timeline, actor, target_sim=target, target_path_spec=target_path_spec)
                            if self.is_derailed(actor):
                                return
                        break
                if actor_path_spec.cost <= target_path_spec.cost:
                    self.set_sim_progress(target, TransitionSequenceStage.TEMPLATES)
                    with create_puppet_postures(target):
                        target_path_spec = yield from self._build_and_log_transitions_for_sim(timeline, target, target_sim=actor, target_path_spec=actor_path_spec)
                        if self.is_derailed(target):
                            return
                else:
                    self.set_sim_progress(actor, TransitionSequenceStage.TEMPLATES)
                    actor_path_spec = yield from self._build_and_log_transitions_for_sim(timeline, actor, target_sim=target, target_path_spec=target_path_spec)
                    if self.is_derailed(actor):
                        return
                break
        actor_data.progress = TransitionSequenceStage.ACTOR_TARGET_SYNC
        if actor_data.progress < TransitionSequenceStage.ACTOR_TARGET_SYNC and (actor_path_spec.path and target_path_spec) and target is not None:
            target_data.progress = TransitionSequenceStage.ACTOR_TARGET_SYNC
        if not self.interaction.disable_transitions:
            for sim in self.get_transitioning_sims():
                if sim in self._sim_data:
                    path_spec = self._get_path_spec(sim)
                    if path_spec is not None:
                        path_spec.unlock_portals(sim)
                        if len(path_spec.path) > 1 and path_spec.path[-1][BODY_INDEX][BODY_POSTURE_TYPE_INDEX].mobile and not path_spec.path[-2][BODY_INDEX][BODY_POSTURE_TYPE_INDEX].mobile:
                            pass
                        else:
                            final_constraint = path_spec.final_constraint
                            if final_constraint is not None and not path_spec.is_failure_path:
                                interaction = self.get_interaction_for_sim(sim)
                                if interaction is None:
                                    interaction = self.interaction
                                (single_point, routing_surface) = final_constraint.single_point()
                                constraint_areas = {constraint.area() for constraint in final_constraint}
                                constraint_areas.discard(None)
                                if single_point is not None or constraint_areas and min(constraint_areas) < self.MINIMUM_AREA_FOR_NO_STAND_RESERVATION:
                                    final_location = path_spec.final_routing_location
                                    if final_location is not None:
                                        single_point = final_location.transform.translation
                                        routing_surface = final_location.routing_surface
                                    if single_point is not None:
                                        self.add_stand_slot_reservation(sim, interaction, single_point, routing_surface)
                                    else:
                                        sim.routing_component.remove_stand_slot_reservation(interaction)
                                else:
                                    sim.routing_component.remove_stand_slot_reservation(interaction)
        for sim in self._sim_data:
            self.advance_path(sim, prime_path=True)

    def _assign_source_interaction_to_posture_state(self, sim, si, posture_state):
        source_interaction = None
        potential_source_sis = [source_si for source_si in (sim.si_state if si is None else itertools.chain((si,), sim.si_state)) if source_si.provided_posture_type is not None]
        for aspect in posture_state.aspects:
            for potential_source_si in potential_source_sis:
                if aspect.posture_type is potential_source_si.provided_posture_type:
                    if aspect.source_interaction is None:
                        aspect.source_interaction = potential_source_si
                    if not aspect.source_interaction is None:
                        if potential_source_si is si:
                            source_interaction = potential_source_si
                            break
                    source_interaction = potential_source_si
                    break
        return source_interaction

    def _get_transition_path_clothing_change(self, path_nodes, sim_info):

        def get_node_water_height(path_node):
            return get_water_depth(path_node.position[0], path_node.position[2], path_node.routing_surface_id.secondary_id)

        if services.terrain_service.ocean_object() is None:
            return
        (swimwear_water_depth, swimwear_outfit_change_reason) = OceanTuning.get_actor_swimwear_change_info(sim_info)
        if swimwear_water_depth is None:
            return
        if swimwear_outfit_change_reason is None:
            return
        else:
            should_change_into_swimwear = False
            prev_node_in_water = get_node_water_height(path_nodes[0]) > swimwear_water_depth
            for node in path_nodes[1:]:
                current_node_in_water = get_node_water_height(node) > swimwear_water_depth
                if not prev_node_in_water:
                    should_change_into_swimwear = True
                    break
                prev_node_in_water = current_node_in_water
            if should_change_into_swimwear:
                outfit = sim_info.get_outfit_for_clothing_change(self.interaction, swimwear_outfit_change_reason)
                return build_critical_section(sim_info.get_change_outfit_element_and_archive_change_reason(outfit, do_spin=True, interaction=self.interaction, change_reason=self._get_transition_path_clothing_change.__name__), flush_all_animations)

    def create_transition(self, create_posture_state_func, si, current_transition, var_map, participant_type, sim, *additional_sims):
        posture_state = create_posture_state_func(var_map)
        if posture_state is None:
            self.cancel()
            return lambda _: False
        source_interaction = self._assign_source_interaction_to_posture_state(sim, si, posture_state)
        if not posture_state.constraint_intersection.valid:
            logger.error('create_transition ended up with a constraint that is invalid: {} for interaction: {}', posture_state, self.interaction)
            return lambda _: False
        last_nonmobile_posture_with_entry_change = None
        remaining_transitions = self.get_remaining_transitions(sim)
        if not any(remaining_transition.body_posture.supports_outfit_change for remaining_transition in remaining_transitions):
            for remaining_transition in reversed(remaining_transitions):
                if remaining_transition.body_posture.outfit_change and remaining_transition.body_posture.posture_type is not posture_state.body.posture_type and remaining_transition.body_posture.multi_sim == posture_state.body.multi_sim:
                    last_nonmobile_posture_with_entry_change = remaining_transition.body_posture
                    break
        if sim.posture_state.body.supports_outfit_change and last_nonmobile_posture_with_entry_change:
            entry_change = last_nonmobile_posture_with_entry_change.post_route_clothing_change(self.interaction, do_spin=True, sim_info=sim.sim_info)
        elif posture_state.body.outfit_change:
            entry_change = posture_state.body.post_route_clothing_change(self.interaction, do_spin=True, sim_info=sim.sim_info)
        else:
            entry_change = None
        if posture_state.body.outfit_change:
            if entry_change is not None and posture_state.body.has_exit_change(self.interaction, sim_info=sim.sim_info):
                sim.sim_info.set_previous_outfit(None)
            posture_state.body.prepare_exit_clothing_change(self.interaction, sim_info=sim.sim_info)
        on_route_change = None
        if self.sim.posture_state.body.supports_outfit_change or posture_state.body.supports_outfit_change:
            on_route_change = self.interaction.pre_route_clothing_change(do_spin=not sim.should_route_instantly())
            self._processed_on_route_change = True
        exit_change = sim.posture_state.body.exit_clothing_change(self.interaction, sim_info=sim.sim_info, do_spin=True)
        if self._processed_on_route_change or entry_change is None and entry_change is not None:
            clothing_change = entry_change
        elif on_route_change is not None:
            clothing_change = on_route_change
        elif exit_change is not None:
            clothing_change = exit_change
        else:
            clothing_change = None
        outdoor_streetwear_change = self.outdoor_streetwear_change.get(sim.id, None)
        if sim.posture_state.body.supports_outfit_change or posture_state.body.supports_outfit_change:
            clothing_change = build_critical_section(sim.sim_info.get_change_outfit_element_and_archive_change_reason(outdoor_streetwear_change, do_spin=True, interaction=self.interaction, change_reason=OutfitChangeReason.WeatherBased), flush_all_animations)
            del self.outdoor_streetwear_change[sim.id]
        context = PostureContext(self.interaction.context.source, self.interaction.priority, self.interaction.context.pick)
        owning_interaction = None
        if source_interaction is not None:
            final_valid_combinables = self.interaction.get_combinable_interactions_with_safe_carryables()
            posture_target = source_interaction.target
            if posture_target is not None and posture_target.has_component(CARRYABLE_COMPONENT):
                interactions_set = {self.interaction}
                interactions_set.update(posture_state.sim.si_state)
                if final_valid_combinables is not None:
                    interactions_set.update(final_valid_combinables)
                for si in interactions_set:
                    if si.carry_target is posture_target:
                        owning_interaction = si
                        break
            elif final_valid_combinables:
                if posture_target.is_part:
                    posture_target_part_owner = posture_target.part_owner
                else:
                    posture_target_part_owner = posture_target
                for combinable in final_valid_combinables:
                    if combinable != self.interaction and combinable.target is posture_target_part_owner:
                        owning_interaction = combinable
                        break
        if clothing_change is None and outdoor_streetwear_change is not None and source_interaction is None or source_interaction.visible or owning_interaction is None:
            owning_interaction = self.interaction
        transition_spec = self.get_transition_spec(sim)
        portal_obj = transition_spec.portal_obj
        if portal_obj is not None:
            portal_id = transition_spec.portal_id
            portal_entry_clothing_change = portal_obj.get_entry_clothing_change(owning_interaction, portal_id, sim_info=sim.sim_info)
            portal_exit_clothing_change = portal_obj.get_exit_clothing_change(owning_interaction, portal_id, sim_info=sim.sim_info)
        else:
            portal_entry_clothing_change = None
            portal_exit_clothing_change = None
        if transition_spec.path is not None:
            final_node = transition_spec.path[-1]
            final_transform = sims4.math.Transform(sims4.math.Vector3(*final_node.position), sims4.math.Quaternion(*final_node.orientation))
            final_transform_constraint = interactions.constraints.Transform(final_transform, routing_surface=final_node.routing_surface_id)
            posture_state.add_constraint(final_node, final_transform_constraint)
            path_nodes = list(transition_spec.path.nodes)
            path_clothing_change = self._get_transition_path_clothing_change(path_nodes, sim.sim_info)
            if path_clothing_change is not None:
                clothing_change = path_clothing_change
        else:
            final_node = None
        sim.si_state.pre_resolve_posture_change(posture_state)
        if final_node is not None:
            posture_state.remove_constraint(final_node)
        if transition_spec.path is not None:
            posture_state.remove_constraint(final_node)
        transition = PostureStateTransition(posture_state, source_interaction, context, var_map, transition_spec, self.interaction, owning_interaction, self.get_transition_should_reserve(sim), transition_spec.final_constraint)
        if clothing_change is not None:
            if sim.posture_state.body.supports_outfit_change:
                if posture_state.body.saved_exit_clothing_change is not None:
                    sequence = build_critical_section_with_finally(clothing_change, transition, lambda _: posture_state.body.ensure_exit_clothing_change_application())
                else:
                    sequence = (clothing_change, transition)
            elif posture_state.body.supports_outfit_change:
                if sim.posture_state.body.saved_exit_clothing_change is not None:
                    body_posture = sim.posture_state.body
                    sequence = build_critical_section_with_finally(transition, clothing_change, lambda _: body_posture.ensure_exit_clothing_change_application())
                else:
                    sequence = (transition, clothing_change)
            elif exit_change is not None:
                posture_state.body.transfer_exit_clothing_change(sim.posture_state.body)
                sequence = (transition,)
            else:
                sequence = (transition,)
        elif portal_entry_clothing_change is not None:
            sequence = (portal_entry_clothing_change, transition)
        elif portal_exit_clothing_change is not None:
            sequence = (transition, portal_exit_clothing_change)
        else:
            sequence = (transition,)
        sequence = sim.without_social_focus(sequence)
        process_si_states = tuple(sim.si_state.process_gen for sim in itertools.chain((sim,), additional_sims))
        process_si_states_again = tuple(sim.si_state.process_gen for sim in itertools.chain((sim,), additional_sims))
        sequence = build_critical_section(process_si_states, sequence, process_si_states_again)
        sequence = self.with_current_transition(sim, transition, sequence)
        transition_spec.created_posture_state = posture_state
        return sequence

    def run_super_interaction(self, timeline, si, pre_run_behavior=None, linked_sim=None):
        if not self._is_putdown_interaction():
            (target_si, test_result) = si.get_target_si()
            if not test_result:
                self.cancel(FinishingType.FAILED_TESTS, test_result=test_result)
                return False
        else:
            target_si = None
        sim = si.sim
        should_wait_for_others = sim is self.sim and si is self.interaction
        start_time = services.time_service().sim_now
        maximum_wait_time = si.maximum_time_to_wait_for_other_sims
        while should_wait_for_others and not self._transition_canceled:
            should_wait_for_others = False
            if self.any_derailed:
                return False
            if sim is self.sim:
                for other_sim in self._sim_data:
                    if sim.posture.multi_sim and sim.posture.linked_posture == other_sim.posture:
                        pass
                    elif not other_sim is sim:
                        if other_sim is linked_sim:
                            pass
                        elif self._is_putdown_interaction(target=other_sim, interaction=si):
                            pass
                        else:
                            remaining_transitions_other = self.get_remaining_transitions(other_sim)
                            if remaining_transitions_other:
                                should_wait_for_others = True
                                break
            if should_wait_for_others:
                now = services.time_service().sim_now
                if now - start_time > clock.interval_in_sim_minutes(maximum_wait_time):
                    self.cancel()
                    break
                else:
                    yield from self._do(timeline, sim, (sim.posture.get_idle_behavior(), flush_all_animations, elements.SoftSleepElement(clock.interval_in_real_seconds(self.SLEEP_TIME_FOR_IDLE_WAITING))))
        if self.canceled:
            return False
        if not si.is_putdown:
            si = target_si
            target_si = si
        if si.staging or target_si is not None and target_si.staging and si.sim in self._sim_data:
            included_sis_actor = self._sim_data[si.sim].final_included_sis
        else:
            included_sis_actor = None
        result = yield from si.run_direct_gen(timeline, source_interaction=self.interaction, pre_run_behavior=pre_run_behavior, included_sis=included_sis_actor)
        if target_si is not None:
            if target_si.sim in self._sim_data:
                included_sis_target = self._sim_data[target_si.sim].final_included_sis
            else:
                included_sis_target = None
            result = yield from target_si.run_direct_gen(timeline, source_interaction=self.interaction, included_sis=included_sis_target)
        if result and si is self.interaction or target_si is self.interaction:
            self._success = True
            if self.interaction.is_social and self.interaction.additional_social_to_run_on_both is not None:
                result = yield from self.interaction.run_additional_social_affordance_gen(timeline)
                if not result:
                    logger.warn('Failed to run additional social affordances for {}', self.interaction, owner='maxr')
                    return False
        if self._is_putdown_interaction(interaction=si):
            self.reset_all_progress()
        return result

    def _create_transition_interaction(self, timeline, sim, destination_spec, create_posture_state_func, target, participant_type, target_si=None, linked_sim=None):
        if self.is_derailed(sim):
            return True
        result = True
        transition_spec = self.get_transition_spec(sim)
        current_spec = None
        if transition_spec is None or not transition_spec.test_transition_interactions(sim, self.interaction):
            return False
        executed_path = False
        for (si, var_map) in transition_spec.transition_interactions(sim):
            current_spec = sim.posture_state.get_posture_spec(var_map)
            yield_to_irq()
            has_pre_route_change = si is not None and (si.outfit_change is not None and si.outfit_change.on_route_change is not None)
            if executed_path:
                run_transition_gen = None
            elif current_spec == destination_spec and transition_spec.path is None and not (has_pre_route_change or transition_spec.portal_obj):
                run_transition_gen = None
            else:

                def run_transition_gen(timeline):
                    nonlocal executed_path
                    self.interaction.add_default_outfit_priority()
                    if target is not None:
                        sequence = self.create_transition(create_posture_state_func, si, destination_spec, var_map, participant_type, sim, target)
                    else:
                        sequence = self.create_transition(create_posture_state_func, si, destination_spec, var_map, participant_type, sim)
                    if not si.route_fail_on_transition_fail:
                        sequence = sim.without_route_failure(sequence)
                    executed_path = True
                    result_transition = yield from element_utils.run_child(timeline, sequence)
                    if si is not None and result_transition or not (self.is_derailed(sim) and self._derailed[sim] == DerailReason.TRANSITION_FAILED and (self.canceled or self._shortest_path_success[sim])):
                        self.cancel(test_result=result_transition)
                    return result_transition

            if si is None:
                if run_transition_gen is not None:
                    result = yield from run_transition_gen(timeline)
                else:
                    result = True
            try:
                self._running_transition_interactions.add(si)
                if self.interaction == si and self._transition_canceled:
                    result = False
                else:
                    result = yield from self.run_super_interaction(timeline, si, pre_run_behavior=run_transition_gen, linked_sim=linked_sim)
                    if target_si is not None:
                        self._running_transition_interactions.add(target_si)
                        result = yield from self.run_super_interaction(timeline, target_si)
                        target_si = None
            finally:
                self._running_transition_interactions.discard(si)
                if target_si is not None:
                    self._running_transition_interactions.discard(target_si)
            if not result:
                break
        path_spec = self._get_path_spec(sim)
        if result or path_spec is not None and path_spec.is_failure_path:
            self.advance_path(sim)
            if target is not None:
                self.advance_path(target)
            if linked_sim is not None and target is not linked_sim:
                self.advance_path(linked_sim)
            return result
        elif self.is_derailed(sim):
            return True
        return result

    def _create_posture_state(self, posture_state, spec, var_map):
        posture_state = PostureState(posture_state.sim, posture_state, spec, var_map)
        return posture_state

    def _create_transition_single(self, sim, transition, participant_type=ParticipantType.Actor):

        def do_transition_single(timeline):

            def create_posture_state_func(var_map):
                return self._create_posture_state(sim.posture_state, transition, var_map)

            result = yield from self._create_transition_interaction(timeline, sim, transition, create_posture_state_func, None, participant_type)
            return result

        return do_transition_single

    def _create_transition_multi_entry(self, sim, sim_node, target, target_node):

        def do_transition_multi_entry(timeline):
            target_transition_spec = self._get_path_spec(target).get_transition_spec()
            target_si = target_transition_spec.get_multi_target_interaction(target)
            if target_si is None:
                logger.error('Target {} does not have target si to run for mulit sim tranistion. {}', target, self.interaction)
                return False
            target_si.context.group_id = self.interaction.group_id
            if not target_si.aop.test(target_si.context):
                logger.debug('Target interaction failed for multi-entry: {}', target_si)
                return False

            def create_multi_sim_posture_state(var_map):
                master_posture_state = self._create_posture_state(sim.posture_state, sim_node, var_map)
                puppet_posture_state = self._create_posture_state(target.posture_state, target_node, var_map)
                if master_posture_state is not None and puppet_posture_state is not None:
                    master_posture_state.linked_posture_state = puppet_posture_state
                    puppet_posture_state.body.source_interaction = target_si
                    puppet_posture_state.body.transfer_exit_clothing_change(target.posture_state.body)
                return master_posture_state

            result = yield from self._create_transition_interaction(timeline, sim, sim_node, create_multi_sim_posture_state, target, ParticipantType.Actor, target_si=target_si)
            return result

        return do_transition_multi_entry

    def _create_transition_multi_carry_exit(self, sim, sim_node, target, target_node):

        def do_transition_multi_carry_exit(timeline):

            def create_posture_state_func(var_map):
                return self._create_posture_state(sim.posture_state, sim_node, var_map)

            target_transition_spec = self.get_transition_spec(target)
            (target_si, target_var_map) = target_transition_spec.transition_interactions(target)[0]
            target_posture_state = self._create_posture_state(target.posture_state, target_node, target_var_map)
            source_interaction = self._assign_source_interaction_to_posture_state(sim, target_si, target_posture_state)
            context = PostureContext(self.interaction.context.source, self.interaction.priority, self.interaction.context.pick)
            transition = PostureStateTransition(target_posture_state, source_interaction, context, target_var_map, target_transition_spec, self.interaction, None, False, target_transition_spec.final_constraint)
            for posture in sim.posture_state.aspects:
                if posture.target is target:
                    posture.set_carried_linked_posture_exit_transition(transition, target_posture_state.body)
                    break
            self._target_interaction = None
            result = yield from self._create_transition_interaction(timeline, sim, sim_node, create_posture_state_func, None, ParticipantType.Actor)
            if not result:
                return result
            transition_element = must_run(target_posture_state.body.begin(None, target_posture_state, context, target.routing_surface))
            result = yield from self.run_super_interaction(timeline, target_si, pre_run_behavior=transition_element)
            yield from element_utils.run_child(timeline, (target_posture_state.body.get_idle_behavior(), flush_all_animations))
            target_si.transition = None
            return result

        return do_transition_multi_carry_exit

    def _create_transition_multi_carry_entry(self, sim, sim_node, target):

        def do_transition_multi_carry_entry(timeline):

            def create_posture_state_func(var_map):
                return self._create_posture_state(sim.posture_state, sim_node, var_map)

            result = yield from self._create_transition_interaction(timeline, sim, sim_node, create_posture_state_func, target, ParticipantType.Actor)
            return result

        return do_transition_multi_carry_entry

    def _create_transition_multi_exit(self, sim, sim_current_state, sim_edge):

        def do_transition_multi_exit(timeline):
            linked_sim = sim.posture.linked_sim
            linked_path_spec = self._get_path_spec(linked_sim)
            linked_destination_target = linked_sim.posture.target
            if linked_path_spec is not None:
                linked_transition_spec = linked_path_spec.get_transition_spec()
                linked_si = linked_transition_spec.get_multi_target_interaction(linked_sim)
                linked_destination_spec = linked_transition_spec.posture_spec
                logger.assert_raise(linked_si is not None, 'linked_si is None for path {}, Sim {} running {}, linked Sim {} running {},', linked_path_spec, sim, sim.posture, linked_sim, linked_sim.posture, owner='jdimailig')
            else:
                source_posture_type = sim_current_state.body_posture
                linked_source_target = None if sim_current_state.body_target is None else linked_sim.posture.target
                valid_exit_posture_types = tuple(sorted(source_posture_type.get_exit_postures_gen(linked_sim, linked_destination_target), key=lambda p: p is sim_edge.body_posture, reverse=True))
                posture_graph_service = services.current_zone().posture_graph_service
                for linked_sim_destination_posture_type in valid_exit_posture_types:
                    linked_source_spec = linked_sim.posture_state.spec.clone(body=PostureAspectBody((source_posture_type, linked_source_target)))
                    if source_posture_type.mobile or linked_sim_destination_posture_type.mobile:
                        body_target = None
                    else:
                        body_target = linked_destination_target
                    linked_destination_spec = linked_sim.posture_state.spec.clone(body=PostureAspectBody((linked_sim_destination_posture_type, body_target)))
                    if body_target is None:
                        linked_destination_spec = linked_destination_spec.clone(surface=PostureAspectSurface((None, None, None)))
                    edge_info = posture_graph_service.get_edge(linked_source_spec, linked_destination_spec)
                    if body_target.is_part:
                        for overlapping_part in body_target.get_overlapping_parts():
                            linked_destination_spec = linked_sim.posture_state.spec.clone(body=PostureAspectBody((linked_sim_destination_posture_type, overlapping_part)))
                            edge_info = posture_graph_service.get_edge(linked_source_spec, linked_destination_spec)
                            if edge_info is not None:
                                body_target = overlapping_part
                                break
                    if edge_info is None and body_target is not None and edge_info is None:
                        pass
                    else:
                        for op in edge_info.operations:
                            aop = op.associated_aop(linked_sim, self.get_var_map(linked_sim))
                            if aop is not None:
                                break
                        break
                self.cancel()
                return False
                linked_context = InteractionContext(linked_sim, self.interaction.source, self.interaction.priority, insert_strategy=QueueInsertStrategy.NEXT, must_run_next=True, group_id=self.interaction.group_id)
                linked_aop = AffordanceObjectPair(aop.affordance, body_target, aop.affordance, None)
                if not linked_aop.test(linked_context):
                    self.cancel()
                    return False
                execute_result = linked_aop.interaction_factory(linked_context)
                linked_si = execute_result.interaction
                logger.assert_raise(execute_result.result, 'linked_si is None for Sim {} running {}, linked Sim {} running {}, with result {}', sim, sim.posture, linked_sim, linked_sim.posture, execute_result, owner='jdimailig')
            posture_transition_context = PostureContext(self.interaction.context.source, self.interaction._priority, None)
            linked_posture_state = PostureState(linked_sim, linked_sim.posture_state, linked_destination_spec, {})
            linked_target_posture = linked_posture_state.body
            linked_target_posture.source_interaction = linked_si
            linked_target_posture.transfer_exit_clothing_change(linked_sim.posture_state.body)
            if linked_target_posture._primitive is None:
                transition = must_run(linked_target_posture.begin(None, linked_posture_state, posture_transition_context, linked_sim.routing_surface))
            else:
                transition = None
            with self.deferred_derailment():
                result = yield from self.run_super_interaction(timeline, linked_si, pre_run_behavior=transition)
                if not result:
                    self.cancel()
                    return False

                def multi_posture_exit(var_map):
                    master_posture = self._create_posture_state(sim.posture_state, sim_edge, var_map)
                    if linked_target_posture is not None:
                        master_posture.linked_posture_state = linked_posture_state
                    return master_posture

                result = yield from self._create_transition_interaction(timeline, sim, sim_edge, multi_posture_exit, None, ParticipantType.Actor, linked_sim=linked_sim)
                return result

        return do_transition_multi_exit

    def _run_interaction_privacy_tests(self, privacy_interaction, sim):
        resolver = privacy_interaction.get_resolver(target=sim)
        return privacy_interaction.privacy.tests.run_tests(resolver)

    def _determine_privacy_interaction(self, sim):
        if self.interaction.privacy is not None:
            return self.interaction
        sim_data = self._sim_data.get(sim)
        for transition_spec in reversed(sim_data.path_spec.transition_specs):
            transition_interactions = transition_spec.transition_interactions(sim)
            if not transition_interactions:
                pass
            else:
                for (interaction, _) in reversed(transition_interactions):
                    if interaction is not None and interaction.privacy is not None and interaction.pipeline_progress < PipelineProgress.EXITED:
                        return interaction

    def _get_privacy_status(self, sim):
        privacy_interaction = self._determine_privacy_interaction(sim)
        if not privacy_interaction:
            return (None, None)
        participant_type = privacy_interaction.get_participant_type(sim)
        if participant_type == ParticipantType.Actor and privacy_interaction.privacy:
            if privacy_interaction.privacy_test_cache is None:
                privacy_interaction.privacy_test_cache = self._run_interaction_privacy_tests(privacy_interaction, sim)
            if not privacy_interaction.privacy_test_cache:
                return (None, None)
            if not privacy_interaction.get_liability(PRIVACY_LIABILITY):
                remaining_transitions = self.get_remaining_transitions(sim)
                engage_privacy = False
                if sim.posture_state.body.mobile and not remaining_transitions[0].body_posture.mobile:
                    engage_privacy = True
                elif len(remaining_transitions) == 1:
                    engage_privacy = True
                if engage_privacy:
                    return (self.PRIVACY_ENGAGE, privacy_interaction)
            elif not privacy_interaction.get_liability(PRIVACY_LIABILITY).privacy.has_shooed:
                return (self.PRIVACY_SHOO, privacy_interaction)
            elif privacy_interaction.get_liability(PRIVACY_LIABILITY).privacy.find_violating_sims():
                return (self.PRIVACY_BLOCK, privacy_interaction)
        return (None, None)

    def _get_putdown_transition_info(self, sim, actor_transitions, current_state, next_state):
        wait_to_be_picked_up_liability = self._interaction.get_liability(WaitToBePickedUpLiability.LIABILITY_TOKEN)
        if wait_to_be_picked_up_liability is not None:
            self.derail(DerailReason.WAIT_TO_BE_PUT_DOWN, sim)
            return (None, None, None, None, None)
        if self._is_putdown_interaction(target=sim):
            return
        if not actor_transitions:
            return
        current_body_posture_target = current_state.body.target
        next_body_posture_target = next_state.body.target
        if current_body_posture_target is None or current_body_posture_target.is_sim or next_body_posture_target is not None and next_body_posture_target.is_sim:
            if len(actor_transitions) == 1:
                return
            carrying_sim = next_state.body.target
            preferred_carrying_sim = self._interaction.context.preferred_carrying_sim
            if preferred_carrying_sim is not carrying_sim:
                animation_work = self._get_animation_work(self.CALL_OVER_ANIMATION)
            else:
                animation_work = None
        elif not (current_body_posture_target is not None and current_body_posture_target.is_sim and (next_body_posture_target is None or next_body_posture_target.is_sim)):
            carrying_sim = current_body_posture_target
            animation_work = None
        else:
            return
        (put_down_position, put_down_routing_surface) = sim.get_initial_put_down_position()
        social_group = self._interaction.social_group
        if carrying_sim in social_group:
            put_down_position = social_group.position
            put_down_routing_surface = social_group.routing_surface
        context = InteractionContext(carrying_sim, InteractionSource.POSTURE_GRAPH, Priority.High, carry_target=sim, insert_strategy=QueueInsertStrategy.FIRST, must_run_next=True)
        interaction_parameters = {'put_down_position': put_down_position, 'put_down_routing_surface': put_down_routing_surface}
        post_carry_aspect = actor_transitions[0].body if social_group is not None and sim in social_group and len(actor_transitions) < 2 else actor_transitions[1].body
        if post_carry_aspect.posture_type.multi_sim:
            return
        if post_carry_aspect.target is not None:
            for aop in sim.get_provided_aops_gen(post_carry_aspect.target, context, **interaction_parameters):
                affordance = aop.affordance
                if not affordance.is_putdown:
                    pass
                elif affordance.get_provided_posture() is not post_carry_aspect.posture_type:
                    pass
                elif not aop.test(context):
                    pass
                else:
                    break
            self.derail(DerailReason.TRANSITION_FAILED, sim)
            return (None, None, None, None, None)
        else:
            aop = AffordanceObjectPair(SuperInteraction.CARRY_POSTURE_REPLACEMENT_AFFORDANCE, sim, SuperInteraction.CARRY_POSTURE_REPLACEMENT_AFFORDANCE, None, **interaction_parameters)

        def _on_finish(pickup_interaction):
            if not pickup_interaction.is_finishing_naturally:
                if self._interaction.is_cancel_aop:
                    self.derail(DerailReason.WAIT_TO_BE_PUT_DOWN, sim)
                else:
                    self._interaction.cancel(pickup_interaction.finishing_type, cancel_reason_msg='Unable to complete pick up')
                    self.derail(DerailReason.TRANSITION_FAILED, sim)

        result = aop.test_and_execute(context)
        if not result:
            self.derail(DerailReason.TRANSITION_FAILED, sim)
        pick_up_interaction = result.interaction
        for si in sim.si_state.all_guaranteed_si_gen(pick_up_interaction.priority, pick_up_interaction.group_id):
            si.cancel(FinishingType.INTERACTION_INCOMPATIBILITY, cancel_reason_msg='Canceling in order to be picked up.')
        self._interaction.set_saved_participant(0, carrying_sim)
        pick_up_liability = PickUpSimLiability(self._interaction, _on_finish)
        pick_up_interaction.add_liability(PickUpSimLiability.LIABILITY_TOKEN, pick_up_liability)
        self.derail(DerailReason.WAIT_TO_BE_PUT_DOWN, sim)
        return (None, None, None, None, animation_work)

    def _handle_teleport_style_interaction_transition_info(self, sim, actor_transitions, current_state, next_state):
        teleport_style_aop = None
        if TeleportHelper.can_teleport_style_be_injected_before_interaction(sim, self.interaction):
            remaining_transition_specs = self._get_path_spec(sim).remaining_original_transition_specs()
            final_routing_location = None
            for spec in remaining_transition_specs:
                if spec.portal_obj is not None:
                    portal_inst = spec.portal_obj.get_portal_by_id(spec.portal_id)
                    if portal_inst is not None:
                        portal_template = portal_inst.portal_template
                        if not portal_template.allow_teleport_style_interaction_to_skip_portal:
                            break
                if spec.path is not None:
                    if spec.path.final_location.routing_surface.type != SurfaceType.SURFACETYPE_WORLD:
                        pass
                    else:
                        final_routing_location = spec.path.final_location
            if final_routing_location is not None:
                pick_type = PickType.PICK_TERRAIN
                location = final_routing_location.transform.translation
                routing_surface = final_routing_location.routing_surface
                lot_id = None
                level = sim.level
                alt = False
                control = False
                shift = False
                ignore_neighborhood_id = False
                override_target = TerrainPoint(final_routing_location)
                if self.interaction.context.pick is not None:
                    parent_pick = self.interaction.context.pick
                    lot_id = parent_pick.lot_id
                    level = parent_pick.level
                    ignore_neighborhood_id = parent_pick.ignore_neighborhood_id
                    alt = parent_pick.modifiers.alt
                    control = parent_pick.modifiers.control
                    shift = parent_pick.modifiers.shift
                elif self.interaction.target is not None:
                    parent_target = self.interaction.target
                    level = parent_target.level
                override_pick = PickInfo(pick_type=pick_type, target=override_target, location=location, routing_surface=routing_surface, lot_id=lot_id, level=level, alt=alt, control=control, shift=shift, ignore_neighborhood_id=ignore_neighborhood_id)
                (teleport_style_aop, interaction_context, _) = sim.get_teleport_style_interaction_aop(self.interaction, override_pick=override_pick, override_target=override_target)
        self.interaction.add_liability(TeleportStyleInjectionLiability.LIABILITY_TOKEN, TeleportStyleInjectionLiability())
        if teleport_style_aop is not None:
            execute_result = teleport_style_aop.execute(interaction_context)
            if execute_result:
                return True
        return False

    def _handle_vehicle_transition_info(self, sim, actor_transitions, current_state, next_state):
        vehicle = current_state.body[BODY_TARGET_INDEX]
        vehicle_component = vehicle.vehicle_component if vehicle is not None else None
        current_posture_on_vehicle = vehicle_component is not None
        next_posture_on_vehicle = next_state.is_on_vehicle()
        if current_posture_on_vehicle and (next_posture_on_vehicle or self._vehicle_transition_state != VehicleTransitionState.DISMOUNTING):
            remaining_transition_specs = self._get_path_spec(sim).remaining_original_transition_specs()
            for spec in remaining_transition_specs:
                if spec.path is not None:
                    final_position = spec.path.final_location.transform.translation
                    if (final_position - vehicle.position).magnitude_squared() < vehicle_component.minimum_route_distance*vehicle_component.minimum_route_distance:
                        break
                    execute_result = vehicle_component.push_dismount_affordance(sim, final_position, depend_on_si=self.interaction)
                    if execute_result:
                        self.derail(DerailReason.MUST_EXIT_MOBILE_POSTURE_OBJECT, sim)
                    break
            if not self.interaction.is_cancel_aop:
                self._vehicle_transition_state = VehicleTransitionState.DISMOUNTING
            return
        if current_posture_on_vehicle or self._vehicle_transition_state == VehicleTransitionState.DISMOUNTING:
            self._vehicle_transition_state = VehicleTransitionState.NO_STATE
            path_spec = self._get_path_spec(sim)
            previous_posture_spec = path_spec.previous_posture_spec
            if current_state == previous_posture_spec:
                path_progress = path_spec.path_progress
                previous_posture_spec = path_spec.path[path_progress - 2] if path_progress >= 2 else None
            if previous_posture_spec is not None:
                vehicle = previous_posture_spec.body_target
                vehicle_component = vehicle.vehicle_component if vehicle is not None else None
                if vehicle_component is not None and (self._should_skip_vehicle_retrieval(path_spec.remaining_original_transition_specs()) or vehicle_component.retrieve_tuning is not None and (sim.routing_surface == vehicle.routing_surface and (sim.household_id == vehicle.household_owner_id and vehicle.inventoryitem_component is not None)) and self.sim.inventory_component.can_add(vehicle)):
                    execute_result = vehicle_component.push_retrieve_vehicle_affordance(sim, depend_on_si=self.interaction)
                    if execute_result:
                        self.derail(DerailReason.MUST_EXIT_MOBILE_POSTURE_OBJECT, sim)
                        return
        is_vehicle_posture_change = current_posture_on_vehicle or next_posture_on_vehicle
        if is_vehicle_posture_change or self._vehicle_transition_state == VehicleTransitionState.DEPLOYING or not self._vehicle_transition_state == VehicleTransitionState.MOUNTING:
            path_spec = self._get_path_spec(sim)
            remaining_transition_specs = path_spec.remaining_original_transition_specs()
            if not remaining_transition_specs:
                return
            else:
                next_spec = remaining_transition_specs[0]
                mounted = False
                final_spec = remaining_transition_specs[-1] if remaining_transition_specs else None
                final_body_target = final_spec.posture_spec[BODY_INDEX][BODY_TARGET_INDEX]
                if final_body_target is not None or any(next_spec.portal_obj is not None for next_spec in remaining_transition_specs):
                    for vehicle in sim.inventory_component.vehicle_objects_gen():
                        target_vehicle_component = vehicle.vehicle_component
                        if target_vehicle_component.deploy_tuning is not None and sim.routing_surface.type in target_vehicle_component.allowed_surfaces and next_spec.path.length() > target_vehicle_component.minimum_route_distance:
                            execute_result = target_vehicle_component.push_deploy_vehicle_affordance(sim, depend_on_si=self.interaction)
                            if execute_result:
                                self._vehicle_transition_state = VehicleTransitionState.DEPLOYING
                                self._deployed_vehicle = weakref.ref(vehicle)
                                self.derail(DerailReason.CONSTRAINTS_CHANGED, sim)
                                mounted = True
                                break
                if not (next_spec.path is not None and mounted):
                    previous_spec = path_spec.previous_transition_spec
                    if previous_spec is not None and previous_spec.portal_obj is not None and next_spec.path is not None:
                        self._mount_vehicle_post_portal_transition(sim, previous_spec, next_spec)
        elif is_vehicle_posture_change or self._vehicle_transition_state == VehicleTransitionState.DEPLOYING and self.deployed_vehicle is not None:
            current_vehicle = self.deployed_vehicle
            execute_result = current_vehicle.vehicle_component.push_drive_affordance(sim, depend_on_si=self.interaction)
            if execute_result:
                self._vehicle_transition_state = VehicleTransitionState.NO_STATE
                self._deployed_vehicle = None
                self.derail(DerailReason.CONSTRAINTS_CHANGED, sim)
                return

    def _handle_formation_transition_info(self, sim):
        master = sim.routing_master if not sim.get_routing_slave_data() else sim
        if master is None:
            return
        slave_datas = master.get_routing_slave_data()
        if not slave_datas:
            return
        transitioning_sims = self.get_transitioning_sims()
        if master in transitioning_sims and all(slave_data.slave in transitioning_sims for slave_data in slave_datas):
            return
        if master is sim:
            derail = False
            transition_spec = self.get_transition_spec(sim)
            if transition_spec.path is None:
                return
            incompatible_sis = set()
            for slave_data in slave_datas:
                if not slave_data.should_slave_for_path(transition_spec.path):
                    pass
                else:
                    slave = slave_data.slave
                    if not slave.is_sim:
                        pass
                    else:
                        for interaction in slave.get_all_running_and_queued_interactions():
                            if interaction.is_super:
                                if interaction not in incompatible_sis:
                                    incompatible_sis.add(interaction)
                                    if not interaction.interruptible:
                                        interaction.cancel(FinishingType.ROUTING_FORMATION, 'Routing Formation master started to route.', immediate=True)
                                        derail = True
                            elif not interaction.interruptible:
                                interaction.cancel(FinishingType.ROUTING_FORMATION, 'Routing Formation master started to route.', immediate=True)
                                derail = True
                        for si in incompatible_sis:
                            if si.is_finishing or si.user_cancelable:
                                si.cancel(FinishingType.ROUTING_FORMATION, 'Routing Formation master started to route.', immediate=True)
                            derail = True
                        for interaction in slave.queue:
                            if interaction.provided_posture_type is not None and interaction.provided_posture_type.mobile:
                                pass
                            elif interaction.transition is not None and interaction not in incompatible_sis:
                                interaction.transition.derail(DerailReason.MASTER_SIM_ROUTING, slave)
                                if interaction.transition.running:
                                    derail = True
                        if slave.posture.mobile:
                            if slave.transition_controller is not None and sim not in slave.transition_controller.get_transitioning_sims():
                                derail = True
                        derail = True
            if derail:
                self.derail(DerailReason.WAIT_FOR_FORMATION_SLAVE, sim)
            return
        slave_data = master.get_formation_data_for_slave(sim)
        if master.is_sim:
            if master.routing_component.current_path is not None and master.routing_component.current_path.length() > slave_data.route_length_minimum:
                self.derail(DerailReason.MASTER_SIM_ROUTING, sim)
                return
            if master.transition_controller is not None:
                transition_spec = master.transition_controller.get_transition_spec(master)
                if transition_spec is not None and (transition_spec.path is not None and transition_spec.path.length() > slave_data.route_length_minimum) and self.interaction.provided_posture_type is None:
                    self.derail(DerailReason.MASTER_SIM_ROUTING, sim)

    def _handle_deferred_putdown(self, sim, current_state, next_state):
        carry_targets = sim.posture_state.carry_targets
        if current_state.carry_target is None and any(carry_targets):
            derail_actors = next_state.body_posture.mobile and next_state.body_posture is not StandSuperInteraction.STAND_POSTURE_TYPE
            should_derail = not self._interaction.cancel_incompatible_carry_interactions(can_defer_putdown=False, derail_actors=derail_actors)
            if should_derail:
                self.derail(DerailReason.WAIT_FOR_BLOCKING_SIMS, sim)
                if self.interaction.is_social:
                    other_sim = self.interaction.target_sim if sim is self.interaction.sim else self.interaction.sim
                    self.interaction.transition.derail(DerailReason.WAIT_FOR_BLOCKING_SIMS, other_sim)
        if current_state._body_target_type != next_state._body_target_type:
            posture_graph = services.current_zone().posture_graph_service
            posture_graph.handle_additional_pickups_and_putdowns(self._get_path_spec(sim), self._sim_data.get(sim).templates[1], sim, can_defer_putdown=False)
            self.has_deferred_putdown = False

    def _get_next_transition_info(self, sim):
        if self._get_path_spec(sim) is None:
            return (None, None, None, None, None)
        actor_transitions = self.get_remaining_transitions(sim)
        if not actor_transitions:
            return (None, None, None, None, None)
        participant_type = self.interaction.get_participant_type(sim)
        var_map = self.get_var_map(sim)
        current_state = sim.posture_state.get_posture_spec(var_map)
        next_state = actor_transitions[0]
        work = None
        was_teleport_style_interaction_executed = self._handle_teleport_style_interaction_transition_info(sim, actor_transitions, current_state, next_state)
        if was_teleport_style_interaction_executed:
            self.derail(DerailReason.CONSTRAINTS_CHANGED, sim)
            return (None, None, None, None, None)
        self._handle_vehicle_transition_info(sim, actor_transitions, current_state, next_state)
        self._handle_formation_transition_info(sim)
        self._handle_deferred_putdown(sim, current_state, next_state)
        (privacy_status, privacy_interaction) = self._get_privacy_status(sim)
        if privacy_status == self.PRIVACY_ENGAGE:
            target = next_state[BODY_POSTURE_TYPE_INDEX][BODY_TARGET_INDEX]
            privacy_interaction.add_liability(PRIVACY_LIABILITY, PrivacyLiability(privacy_interaction, target))
            sim.queue.on_required_sims_changed(privacy_interaction)
            if privacy_interaction.get_liability(PRIVACY_LIABILITY).privacy.find_violating_sims(consider_exempt=False):
                if not privacy_interaction.privacy.animate_shoo:
                    return (None, None, None, None, None)
                work = self._get_animation_work(self.SHOO_ANIMATION)
        else:
            if privacy_status == self.PRIVACY_SHOO:
                privacy_interaction.priority = Priority.Critical
                services.get_master_controller().reset_timestamp_for_sim(self.sim)
                self.derail(DerailReason.PRIVACY_ENGAGED, sim)
                privacy_interaction.get_liability(PRIVACY_LIABILITY).privacy.has_shooed = True
                self._privacy_initiation_time = services.time_service().sim_now
                return (None, None, None, None, None)
            if privacy_status == self.PRIVACY_BLOCK:
                return (None, None, None, None, None)
        transition_info = self._get_putdown_transition_info(sim, actor_transitions, current_state, next_state)
        if transition_info is not None:
            return transition_info
        current_body_posture_target = current_state.body.target
        next_body_posture_target = next_state.body.target
        next_carry_target = next_state.carry_target
        next_carry_target = var_map.get(next_carry_target, next_carry_target)
        if next_carry_target.is_sim:
            if sim.routing_surface != next_carry_target.routing_surface:
                constraint = next_carry_target.get_carry_transition_constraint(sim, sim.position, sim.routing_surface)
                constraint = constraint._copy(_multi_surface=False)
                affordance = interactions.utils.satisfy_constraint_interaction.SatisfyConstraintSuperInteraction
                aop = AffordanceObjectPair(affordance, None, affordance, None, constraint_to_satisfy=constraint, route_fail_on_transition_fail=False, name_override='TransitionSequence[CarryTargetMove]', allow_posture_changes=True, depended_on_si=self.interaction)
                context = InteractionContext(next_carry_target, InteractionContext.SOURCE_SCRIPT, Priority.High, insert_strategy=QueueInsertStrategy.FIRST, must_run_next=True, group_id=self.interaction.group_id)
                execute_result = aop.test_and_execute(context)
                if execute_result:
                    self.derail(DerailReason.WAIT_FOR_CARRY_TARGET, sim)
                else:
                    self.derail(DerailReason.TRANSITION_FAILED, sim)
                return (None, None, None, None, None)
            if next_carry_target.parent is not None:
                self.derail(DerailReason.WAIT_FOR_CARRY_TARGET, sim)
                return (None, None, None, None, None)
            carry_target_transitions = self.get_remaining_transitions(next_carry_target)
            if carry_target_transitions:
                carry_target_next_body_target = carry_target_transitions[0].body.target
                if carry_target_next_body_target is not sim:
                    return (None, None, None, None, None)
        if current_state.carry_target is None and next_carry_target is not None and next_body_posture_target is not None and next_body_posture_target.is_sim and next_body_posture_target is not current_body_posture_target:
            return (None, None, None, None, None)
        if current_body_posture_target.is_sim:
            if next_body_posture_target is not current_body_posture_target:
                return (None, None, None, None, None)
            if next_body_posture_target is not None and next_body_posture_target.is_sim:
                next_body_posture_target_carry_target = next_body_posture_target.posture_state.get_posture_spec(self.get_var_map(next_body_posture_target)).carry_target
                if next_body_posture_target_carry_target != PostureSpecVariable.CARRY_TARGET and next_body_posture_target_carry_target is not sim:
                    logger.error('{} is transitioning to the same state: {} -> {} with next_body_posture_target: {} and next_body_posture_target_carry_target: {}', sim, current_state, next_state, next_body_posture_target, next_body_posture_target_carry_target)
                    return (None, None, None, None, None)
        return (participant_type, current_state, next_state, actor_transitions, work)

    def is_multi_sim_entry(self, current_state, next_state):
        if current_state is None or next_state is None:
            return False
        return not current_state[BODY_INDEX][BODY_POSTURE_TYPE_INDEX].multi_sim and next_state[BODY_INDEX][BODY_POSTURE_TYPE_INDEX].multi_sim

    def is_multi_sim_exit(self, current_state, next_state):
        if current_state is None or next_state is None:
            return False
        return current_state[BODY_INDEX][BODY_POSTURE_TYPE_INDEX].multi_sim and not next_state[BODY_INDEX][BODY_POSTURE_TYPE_INDEX].multi_sim

    def is_multi_to_multi(self, current_state, next_state):
        if current_state is None or next_state is None:
            return False
        return current_state[BODY_INDEX][BODY_POSTURE_TYPE_INDEX].multi_sim and next_state[BODY_INDEX][BODY_POSTURE_TYPE_INDEX].multi_sim

    def _create_next_elements(self, timeline):
        no_work_sims = []
        executed_work = False
        any_participant_has_work = False
        for sim in self.get_transitioning_sims():
            participant_has_work = False
            if sim in self._sim_jobs:
                executed_work = True
                if sim not in self._sim_idles:
                    participant_has_work = True
            elif self._get_path_spec(sim) is not None:
                transitions_sim = self.get_remaining_transitions(sim)
                if transitions_sim:
                    if sim.posture.multi_sim:
                        if self.is_multi_to_multi(self.get_previous_spec(sim), transitions_sim[0]) and self.interaction.get_participant_type(sim) != ParticipantType.Actor:
                            pass
                        elif sim.posture.linked_sim in self._sim_jobs and self.is_multi_sim_exit(self.get_previous_spec(sim), transitions_sim[0]):
                            pass
                        else:
                            (privacy_status, _) = self._get_privacy_status(sim)
                            if privacy_status != self.PRIVACY_BLOCK:
                                participant_has_work = True
                            else:
                                now = services.time_service().sim_now
                                timeout = self.SIM_MINUTES_TO_WAIT_FOR_VIOLATORS
                                delta = now - self._privacy_initiation_time
                                if delta > clock.interval_in_sim_minutes(timeout):
                                    self.cancel(FinishingType.TRANSITION_FAILURE)
                                else:
                                    self._execute_work_as_element(timeline, sim, elements.SoftSleepElement(clock.interval_in_sim_minutes(1)))
                            any_participant_has_work = any_participant_has_work or participant_has_work
                            if not participant_has_work:
                                no_work_sims.append(sim)
                            if participant_has_work:
                                if sim in self._sim_jobs:
                                    pass
                                else:
                                    executed_work = True
                                    self._sim_idles.discard(sim)
                                    self._execute_work_as_element(timeline, sim, functools.partial(self._execute_next_transition, sim))
                    else:
                        (privacy_status, _) = self._get_privacy_status(sim)
                        if privacy_status != self.PRIVACY_BLOCK:
                            participant_has_work = True
                        else:
                            now = services.time_service().sim_now
                            timeout = self.SIM_MINUTES_TO_WAIT_FOR_VIOLATORS
                            delta = now - self._privacy_initiation_time
                            if delta > clock.interval_in_sim_minutes(timeout):
                                self.cancel(FinishingType.TRANSITION_FAILURE)
                            else:
                                self._execute_work_as_element(timeline, sim, elements.SoftSleepElement(clock.interval_in_sim_minutes(1)))
                        any_participant_has_work = any_participant_has_work or participant_has_work
                        if not participant_has_work:
                            no_work_sims.append(sim)
                        if participant_has_work:
                            if sim in self._sim_jobs:
                                pass
                            else:
                                executed_work = True
                                self._sim_idles.discard(sim)
                                self._execute_work_as_element(timeline, sim, functools.partial(self._execute_next_transition, sim))
            any_participant_has_work = any_participant_has_work or participant_has_work
            if not participant_has_work:
                no_work_sims.append(sim)
            if participant_has_work:
                if sim in self._sim_jobs:
                    pass
                else:
                    executed_work = True
                    self._sim_idles.discard(sim)
                    self._execute_work_as_element(timeline, sim, functools.partial(self._execute_next_transition, sim))
        if any_participant_has_work:
            for sim in no_work_sims:
                if sim not in self._sim_idles:
                    self._execute_work_as_element(timeline, sim, functools.partial(self._execute_next_transition, sim, no_work=True))
        if any_participant_has_work and not executed_work:
            raise RuntimeError('Deadlock in the transition sequence.\n Interaction: {},\n Participants: {},\n Full path_specs: {} \n[tastle]'.format(self.interaction, self.get_transitioning_sims(), [sim_data.path_spec for sim_data in self._sim_data.values()]))

    def _execute_work_as_element(self, timeline, sim, work):
        self._sim_jobs.append(sim)
        child = build_element([build_critical_section_with_finally(work, lambda _: self._sim_jobs.remove(sim)), self._create_next_elements])
        self._worker_all_element.add_work(timeline, child)

    def _execute_next_transition(self, sim, timeline, no_work=False):
        if any(self._derailed.values()):
            return False
        if self._transition_canceled:
            self.cancel()
            return False
        else:
            selected_work = None
            if not no_work:
                (participant_type, sim_current_state, sim_next_state, actor_transitions, work) = self._get_next_transition_info(sim)
                if work is not None:
                    single_sim_transition = build_element(work)
                    selected_work = single_sim_transition
                else:
                    multi_sim_exit_sim = self.is_multi_sim_exit(sim_current_state, sim_next_state)
                    if multi_sim_exit_sim:
                        target = sim.posture.linked_sim
                        sim_multi_exit = self._create_transition_multi_exit(sim, sim_current_state, sim_next_state)
                        sim_multi_exit = build_element(sim_multi_exit)
                        selected_work = sim_multi_exit
                    if multi_sim_exit_sim or self._interaction.is_putdown and actor_transitions is not None:
                        next_transition_spec = self.get_next_transition_spec(sim)
                        if next_transition_spec is None or not next_transition_spec.is_carry:
                            target = self.interaction.carry_target or self.interaction.target
                            if target is not None and target.is_sim and target.parent is sim:
                                target_transitions = self.get_remaining_transitions(target)
                                if target_transitions:
                                    next_state_target = target_transitions[0]
                                    if sim_next_state is None or next_state_target.body.target is sim_next_state.body.target:
                                        selected_work = build_element(self._create_transition_multi_carry_exit(sim, sim_next_state or sim_current_state, target, next_state_target))
                                        multi_sim_exit_sim = True
                                elif target.posture_state.body.target is sim:
                                    self.derail(DerailReason.WAIT_TO_BE_PUT_DOWN, sim)
                    multi_sim_entry_sim = self.is_multi_sim_entry(sim_current_state, sim_next_state) or self.is_multi_to_multi(sim_current_state, sim_next_state)
                    if participant_type is ParticipantType.Actor:
                        target = self.interaction.get_participant(ParticipantType.TargetSim)
                        if target is not None:
                            var_map_target = self.get_var_map(target)
                            if var_map_target is not None:
                                current_state_target = sim.posture_state.get_posture_spec(var_map_target)
                                next_transitions_target = self.get_remaining_transitions(target)
                                next_state_target = next_transitions_target[0] if next_transitions_target else None
                                multi_sim_entry_target = self.is_multi_sim_entry(current_state_target, next_state_target) or self.is_multi_to_multi(current_state_target, next_state_target)
                                multi_sim_entry = multi_sim_entry_sim and multi_sim_entry_target
                                if multi_sim_entry:
                                    multi_sim_entry = self._create_transition_multi_entry(sim, sim_next_state, target, next_state_target)
                                    multi_sim_entry = build_element(multi_sim_entry)
                                    if selected_work is not None:
                                        raise RuntimeError('Multiple work units planned in _execute_next_transition')
                                    selected_work = multi_sim_entry
                    if not multi_sim_exit_sim:
                        single_sim_transition = None
                        next_carry_target = sim_next_state.carry_target
                        if next_carry_target is not None:
                            var_map = self.get_var_map(sim)
                            if var_map is not None:
                                next_carry_target = var_map.get(next_carry_target, next_carry_target)
                                if next_carry_target.is_sim:
                                    single_sim_transition = self._create_transition_multi_carry_entry(sim, sim_next_state, next_carry_target)
                        if sim_current_state.carry_target is None and single_sim_transition is None:
                            single_sim_transition = self._create_transition_single(sim, sim_next_state, participant_type)
                        single_sim_transition = build_element(single_sim_transition)
                        if selected_work is not None:
                            raise RuntimeError('Multiple work units planned in _execute_next_transition')
                        selected_work = single_sim_transition
            if selected_work is None and sim not in self._sim_idles:

                def _do_idle_behavior(timeline):
                    if sim.posture.multi_sim and sim.posture.source_interaction is not None and sim.posture.source_interaction.is_finishing:
                        result = yield from element_utils.run_child(timeline, elements.SoftSleepElement(clock.interval_in_real_seconds(self.SLEEP_TIME_FOR_IDLE_WAITING)))
                    else:
                        result = yield from element_utils.run_child(timeline, (sim.posture.get_idle_behavior(), flush_all_animations, elements.SoftSleepElement(clock.interval_in_real_seconds(self.SLEEP_TIME_FOR_IDLE_WAITING))))
                    return result

                selected_work = _do_idle_behavior
                self._sim_idles.add(sim)
            if selected_work is not None:
                result = yield from self._do(timeline, sim, selected_work)
                if not result:
                    if self._shortest_path_success[sim]:
                        self.derail(DerailReason.TRANSITION_FAILED, sim, test_result=result)
                    else:
                        self.cancel(test_result=result)
                    return False
        return True

    def _should_skip_vehicle_retrieval(self, remaining_transition_specs):
        for spec in remaining_transition_specs:
            if spec.portal_obj is None:
                pass
            else:
                portal_inst = spec.portal_obj.get_portal_by_id(spec.portal_id)
                if portal_inst is None:
                    pass
                else:
                    portal_template = portal_inst.portal_template
                    if portal_template.use_vehicle_after_traversal:
                        return True
                    break
        return False

    def _mount_vehicle_post_portal_transition(self, sim, previous_spec, next_spec):
        portal_object = previous_spec.portal_obj
        portal_id = previous_spec.portal_id
        vehicles = portal_object.portal_component.get_vehicles_nearby_portal_id(portal_id)
        vehicles.sort(key=lambda vehicle: vehicle.household_owner_id == sim.household_id, reverse=True)
        for vehicle in vehicles:
            if vehicle.household_owner_id is not None and vehicle.household_owner_id != 0 and vehicle.household_owner_id != sim.household_id:
                pass
            else:
                vehicle_component = vehicle.vehicle_component
                if next_spec.path.length() > vehicle_component.minimum_route_distance:
                    execute_result = vehicle.vehicle_component.push_drive_affordance(sim, depend_on_si=self.interaction)
                    if execute_result:
                        self._vehicle_transition_state = VehicleTransitionState.MOUNTING
                        self.derail(DerailReason.CONSTRAINTS_CHANGED, sim)
                        return True
        return False
