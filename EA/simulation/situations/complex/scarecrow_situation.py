from _functools import partialfrom _sims4_collections import frozendictfrom event_testing.resolver import SingleObjectResolverfrom event_testing.test_events import TestEventfrom interactions import ParticipantTypefrom interactions.utils.loot import LootActionsfrom role.role_state import RoleStatefrom sims4.tuning.tunable_base import GroupNamesfrom situations.bouncer.bouncer_types import BouncerExclusivityCategoryfrom situations.complex.object_bound_situation_mixin import ObjectBoundSituationMixinfrom situations.situation import Situationfrom situations.situation_complex import SituationStateData, TunableInteractionOfInterest, SituationComplexCommon, CommonSituationStatefrom situations.situation_job import SituationJobfrom situations.situation_types import SituationCreationUIOptionimport servicesimport sims4.tuning.instanceslogger = sims4.log.Logger('ScarecrowSituation', default_owner='jdimailig')
class _SingleJobComplexSituationState(CommonSituationState):
    FACTORY_TUNABLES = {'role_state': RoleState.TunableReference(description='\n            The role the Sim has while in this state.\n            \n            This is the initial state.\n            '), 'locked_args': {'job_and_role_changes': frozendict()}}

    def __init__(self, *args, situation_job, role_state, job_and_role_changes, **kwargs):
        super().__init__(*args, job_and_role_changes={situation_job: role_state}, **kwargs)

class _DoStuffState(_SingleJobComplexSituationState):

    def get_time_remaining(self):
        if self._time_out_string in self._alarms:
            return self._alarms[self._time_out_string].alarm_handle.get_remaining_time()

    def timer_expired(self):
        self.owner.go_to_leave_state()

class _LeaveState(_SingleJobComplexSituationState):
    FACTORY_TUNABLES = {'_leave_interaction': TunableInteractionOfInterest(description='\n             The interaction that, once completed, can end the situation.\n             Typically the interaction that the Sim uses to route back\n             to the starting object.\n             \n             As a fallback, setting a timeout will also end the situation.\n             If for some reason this interaction fails to run or complete.\n             ')}

    def __init__(self, *args, _leave_interaction, **kwargs):
        super().__init__(*args, **kwargs)
        self._leave_interaction = _leave_interaction

    def on_activate(self, reader=None):
        super().on_activate(reader)
        for custom_key in self._leave_interaction.custom_keys_gen():
            self._test_event_register(TestEvent.InteractionComplete, custom_key)

    def handle_event(self, sim_info, event, resolver):
        if event == TestEvent.InteractionComplete and self.owner.is_sim_info_in_situation(sim_info) and resolver(self._leave_interaction):
            self.owner._self_destruct()

    def timer_expired(self):
        for sim in self.owner.all_sims_in_situation_gen():
            services.get_zone_situation_manager().make_sim_leave_now_must_run(sim)
        self.owner._self_destruct()

class ScarecrowSituation(ObjectBoundSituationMixin, SituationComplexCommon):
    INSTANCE_TUNABLES = {'_situation_job': SituationJob.TunableReference(description='\n            The situation job for the Sim.\n            \n            This job should define a spawn affordance that will trigger\n            a continuation targeting the object the Sim spawns at.\n            ', tuning_group=GroupNames.SITUATION), '_do_stuff_state': _DoStuffState.TunableFactory(description='\n            The state for the Sim doing stuff.\n            \n            This is the initial state after the Sim spawns onto the lot.\n\n            Any on-activate affordances run in this role will target\n            the object the Sim spawned near.\n            ', display_name='1. Do Stuff', tuning_group=GroupNames.STATE), '_leave_state': _LeaveState.TunableFactory(description='\n            The state for the Sim leaving.\n            \n            Any on-activate affordances run in this role will target\n            the object the Sim spawned near.\n            ', display_name='2. Leave', tuning_group=GroupNames.STATE), '_spawn_object_targeting_affordance': TunableInteractionOfInterest(description="\n            Affordance that runs targeting the object that the object that the\n            Sim had spawned at. This allows the situation to 'remember' that\n            object and when that object is destroyed, the situation will\n            be destroyed as well. \n            ", tuning_group=GroupNames.SITUATION), '_spawn_object_reset_loots': LootActions.TunableReference(description='\n            Loots used to reset the object from which the scarecrow spawned from,\n            to handle cases for when the scarecrow Sim is not on lot during load.\n            ', tuning_group=GroupNames.SITUATION)}
    REMOVE_INSTANCE_TUNABLES = Situation.NON_USER_FACING_REMOVE_INSTANCE_TUNABLES

    @classmethod
    def _states(cls):
        return (SituationStateData(1, _DoStuffState, partial(cls._do_stuff_state, situation_job=cls._situation_job)), SituationStateData(2, _LeaveState, partial(cls._leave_state, situation_job=cls._situation_job)))

    @classmethod
    def _get_tuned_job_and_default_role_state_tuples(cls):
        return [(cls._situation_job, None)]

    @classmethod
    def default_job(cls):
        return cls._situation_job

    @classmethod
    def get_sims_expected_to_be_in_situation(cls):
        return 1

    def _get_role_state_overrides(self, sim, job_type, role_state_type, role_affordance_target):
        return (role_state_type, services.object_manager().get(self.bound_object_id))

    def start_situation(self):
        super().start_situation()
        for custom_key in self._spawn_object_targeting_affordance.custom_keys_gen():
            self._register_test_event(TestEvent.InteractionStart, custom_key)
        self._change_state(self._do_stuff_state(situation_job=self._situation_job))

    def load_situation(self):
        scarecrow_guest_info = next(iter(self._guest_list.get_persisted_sim_guest_infos()))
        if scarecrow_guest_info is None:
            self._reset_scarecrow_object()
            return False
        scarecrow_sim_info = services.sim_info_manager().get(scarecrow_guest_info.sim_id)
        if scarecrow_sim_info is None or scarecrow_sim_info.zone_id != services.current_zone_id():
            self._reset_scarecrow_object()
            return False
        return super().load_situation()

    def _reset_scarecrow_object(self):
        scarecrow_object = services.object_manager().get(self._bound_object_id)
        resolver = SingleObjectResolver(scarecrow_object)
        self._spawn_object_reset_loots.apply_to_resolver(resolver)

    def handle_event(self, sim_info, event, resolver):
        if event == TestEvent.InteractionStart:
            if self.is_sim_info_in_situation(sim_info) and resolver(self._spawn_object_targeting_affordance):
                target = resolver.get_participant(ParticipantType.Object)
                if target is None:
                    logger.error('{}: {} target is None, cannot find the object for this situation to bind to!', self, resolver)
                    self._self_destruct()
                    return
                self.bind_object(target)
        else:
            super().handle_event(sim_info, event, resolver)

    def go_to_leave_state(self):
        self._change_state(self._leave_state(situation_job=self._situation_job))

    def _gsi_additional_data_gen(self):
        if isinstance(self._cur_state, _DoStuffState):
            yield ('Time till Leave State', str(self._cur_state.get_time_remaining()))
sims4.tuning.instances.lock_instance_tunables(ScarecrowSituation, exclusivity=BouncerExclusivityCategory.NORMAL, creation_ui_option=SituationCreationUIOption.NOT_AVAILABLE)