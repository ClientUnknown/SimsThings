import itertoolsfrom filters.tunable import TunableAggregateFilter, FilterTermTagfrom role.role_state import RoleStatefrom sims4.tuning.tunable import TunableTuple, TunableMapping, TunableEnumEntry, TunableReference, TunableList, TunableEnumWithFilterfrom sims4.utils import classpropertyfrom situations.bouncer.bouncer_types import RequestSpawningOption, BouncerExclusivityCategoryfrom situations.situation import Situationfrom situations.situation_complex import SituationState, CommonSituationState, SituationComplexCommon, SituationStateData, CommonInteractionCompletedSituationStatefrom situations.situation_guest_list import SituationGuestList, SituationGuestInfofrom situations.situation_job import SituationJobfrom situations.situation_types import SituationSerializationOption, SituationCreationUIOptionfrom tag import Tag, SPAWN_PREFIXfrom world.spawn_point import SpawnPointfrom world.spawn_point_enums import SpawnPointRequestReasonimport servicesimport sims4.tuning.instances
class GetSimsState(SituationState):

    def _on_set_sim_role_state(self, sim, *args, **kwargs):
        super()._on_set_sim_role_state(sim, *args, **kwargs)
        if self.owner.num_of_sims >= self.owner.num_invited_sims:
            self.owner.on_all_sims_spawned()

class WalkbyWalkState(CommonSituationState):

    def timer_expired(self):
        self._change_state(self.owner.leave_state())

class LeaveState(CommonInteractionCompletedSituationState):

    def _on_interaction_of_interest_complete(self, **kwargs):
        self._end_situation()

    def _additional_tests(self, sim_info, event, resolver):
        return self.owner.is_sim_info_in_situation(sim_info)

    def timer_expired(self):
        self._end_situation()

    def _end_situation(self):
        for sim in self.owner.all_sims_in_situation_gen():
            services.get_zone_situation_manager().make_sim_leave_now_must_run(sim)
        self.owner._self_destruct()

class WalkbyDogWalker(SituationComplexCommon):
    INSTANCE_TUNABLES = {'group_filter': TunableAggregateFilter.TunableReference(description='\n            The aggregate filter that we use to find the sims for this\n            situation.\n            '), 'walk_state': WalkbyWalkState.TunableFactory(description='\n            A state for getting the Sims to \n            ', locked_args={'allow_join_situation': False}), 'leave_state': LeaveState.TunableFactory(description='\n            The state for the adoption officer to leave.\n            ', locked_args={'allow_join_situation': False}), 'dog_walker': TunableTuple(situation_job=SituationJob.TunableReference(description='\n                The Situation Job of the dog walker.\n                '), initial_role_state=RoleState.TunableReference(description='\n                The initial Role State of the dog walker.\n                ')), 'dog': TunableTuple(situation_job=SituationJob.TunableReference(description='\n                The Situation Job of the dog.\n                '), initial_role_state=RoleState.TunableReference(description='\n                The initial Role State of the dog.\n                ')), 'situation_job_mapping': TunableMapping(description='\n            A mapping of filter term tag to situation job.\n            \n            The filter term tag is returned as part of the sim filters used to \n            create the guest list for this particular situation.\n            \n            The situation job is the job that the Sim will be assigned to in\n            the background situation.\n            ', key_name='filter_tag', key_type=TunableEnumEntry(description='\n                The filter term tag returned with the filter results.\n                ', tunable_type=FilterTermTag, default=FilterTermTag.NO_TAG), value_name='job', value_type=TunableReference(description='\n                The job the Sim will receive when added to the this situation.\n                ', manager=services.get_instance_manager(sims4.resources.Types.SITUATION_JOB))), 'sim_spawner_tags': TunableList(description='\n            A list of tags that represent where to spawn Sims for this\n            Situation when they come onto the lot.  This tuning will be used\n            instead of the tuning on the jobs.\n            NOTE: Tags will be searched in order of tuning. Tag [0] has\n            priority over Tag [1] and so on.\n            ', tunable=TunableEnumWithFilter(tunable_type=Tag, default=Tag.INVALID, filter_prefixes=SPAWN_PREFIX))}
    REMOVE_INSTANCE_TUNABLES = Situation.NON_USER_FACING_REMOVE_INSTANCE_TUNABLES

    @classmethod
    def _states(cls):
        return (SituationStateData(1, GetSimsState), SituationStateData(2, WalkbyWalkState, factory=cls.walk_state), SituationStateData(3, LeaveState, factory=cls.leave_state))

    @classmethod
    def default_job(cls):
        pass

    @classmethod
    def _get_tuned_job_and_default_role_state_tuples(cls):
        return [(cls.dog_walker.situation_job, cls.dog_walker.initial_role_state), (cls.dog.situation_job, cls.dog.initial_role_state)]

    @classmethod
    def get_predefined_guest_list(cls):
        guest_list = SituationGuestList(invite_only=True)
        situation_manager = services.get_zone_situation_manager()
        instanced_sim_ids = [sim.sim_info.id for sim in services.sim_info_manager().instanced_sims_gen()]
        household_sim_ids = [sim_info.id for sim_info in services.active_household().sim_info_gen()]
        auto_fill_blacklist_walker = situation_manager.get_auto_fill_blacklist(sim_job=cls.dog_walker.situation_job)
        auto_fill_blacklist_dog = situation_manager.get_auto_fill_blacklist(sim_job=cls.dog.situation_job)
        situation_sims = set()
        for situation in situation_manager.get_situations_by_tags(cls.tags):
            situation_sims.update(situation.invited_sim_ids)
        blacklist_sim_ids = set(itertools.chain(situation_sims, instanced_sim_ids, household_sim_ids, auto_fill_blacklist_walker, auto_fill_blacklist_dog))
        filter_results = services.sim_filter_service().submit_matching_filter(sim_filter=cls.group_filter, allow_yielding=False, blacklist_sim_ids=blacklist_sim_ids, gsi_source_fn=cls.get_sim_filter_gsi_name)
        if not filter_results:
            return
        if len(filter_results) != cls.group_filter.get_filter_count():
            return
        for result in filter_results:
            job = cls.situation_job_mapping.get(result.tag, None)
            if job is None:
                pass
            else:
                guest_list.add_guest_info(SituationGuestInfo(result.sim_info.sim_id, job, RequestSpawningOption.DONT_CARE, job.sim_auto_invite_allow_priority))
        return guest_list

    def start_situation(self):
        super().start_situation()
        if self._guest_list.guest_info_count != self.group_filter.get_filter_count():
            self._self_destruct()
        else:
            self._change_state(GetSimsState())

    @classmethod
    def get_sims_expected_to_be_in_situation(cls):
        return cls.group_filter.get_filter_count()

    @classmethod
    def _can_start_walkby(cls, lot_id:int):
        return True

    @classproperty
    def situation_serialization_option(cls):
        return SituationSerializationOption.OPEN_STREETS

    @property
    def _should_cancel_leave_interaction_on_premature_removal(self):
        return True

    def on_all_sims_spawned(self):
        self._change_state(self.walk_state())

    def _issue_requests(self):
        zone = services.current_zone()
        if SpawnPoint.ARRIVAL_SPAWN_POINT_TAG in self.sim_spawner_tags or SpawnPoint.VISITOR_ARRIVAL_SPAWN_POINT_TAG in self.sim_spawner_tags:
            lot_id = zone.lot.lot_id
        else:
            lot_id = None
        spawn_point = zone.get_spawn_point(lot_id=lot_id, sim_spawner_tags=self.sim_spawner_tags, spawn_point_request_reason=SpawnPointRequestReason.SPAWN)
        super()._issue_requests(spawn_point_override=spawn_point)
sims4.tuning.instances.lock_instance_tunables(WalkbyDogWalker, exclusivity=BouncerExclusivityCategory.WALKBY, creation_ui_option=SituationCreationUIOption.NOT_AVAILABLE, duration=0)