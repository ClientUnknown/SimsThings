import itertoolsimport randomfrom filters.tunable import FilterTermTagfrom sims4.tuning.instances import lock_instance_tunablesfrom sims4.tuning.tunable import Tunable, TunableReference, TunableMapping, TunableEnumEntry, TunableSimMinutefrom sims4.utils import classpropertyfrom situations.ambient.busker_situation import BuskerSituationMixin, BuskSituationStatefrom situations.ambient.sales_table_vendor_situation import SalesTableVendorSituationMixinfrom situations.base_situation import _RequestUserDatafrom situations.bouncer.bouncer_request import SelectableSimRequestFactoryfrom situations.bouncer.bouncer_types import BouncerExclusivityCategory, RequestSpawningOption, BouncerRequestPriorityfrom situations.situation import Situationfrom situations.situation_complex import CommonSituationState, SituationComplexCommon, SituationStateData, SituationState, TunableSituationJobAndRoleStatefrom situations.situation_guest_list import SituationGuestList, SituationGuestInfofrom situations.situation_job import SituationJobfrom situations.situation_types import SituationCreationUIOptionimport filters.tunableimport servicesimport sims4.resourcesimport situations
class CooldownFestivalSituationState(CommonSituationState):
    FACTORY_TUNABLES = {'should_try_and_find_new_situation': Tunable(description='\n            If True then we will try and put these Sims into new situations\n            when they enter this state.\n            ', tunable_type=bool, default=False)}

    def __init__(self, *args, should_try_and_find_new_situation=False, **kwargs):
        super().__init__(*args, **kwargs)
        self._should_try_and_find_new_situation = should_try_and_find_new_situation

    def on_activate(self, reader=None):
        super().on_activate(reader=reader)
        if self._should_try_and_find_new_situation:
            for sim in self.owner.all_sims_in_situation_gen():
                self.owner.manager.bouncer.set_sim_looking_for_new_situation(sim)

class BaseGenericFestivalSituation(SituationComplexCommon):
    INSTANCE_TUNABLES = {'cooldown_state': CooldownFestivalSituationState.TunableFactory(description='\n            The state that the Situation will go into when the festival open\n            street director notifies it that the festival is going into\n            cooldown.\n            ', locked_args={'allow_join_situation': False, 'time_out': None}, tuning_group=SituationComplexCommon.SITUATION_STATE_GROUP), 'duration_randomizer': TunableSimMinute(description="\n            A random time between 0 and this tuned time will be added to the\n            situation's duration.\n            ", default=0, minimum=0)}
    REMOVE_INSTANCE_TUNABLES = Situation.NON_USER_FACING_REMOVE_INSTANCE_TUNABLES

    @classmethod
    def default_job(cls):
        pass

    def put_on_cooldown(self):
        self._change_state(self.cooldown_state())

    @classproperty
    def situation_serialization_option(cls):
        return situations.situation_types.SituationSerializationOption.OPEN_STREETS

    @classproperty
    def always_elevated_importance(cls):
        return True

    def _get_duration(self):
        if self._seed.duration_override is not None:
            return self._seed.duration_override
        return self.duration + random.randint(0, self.duration_randomizer)

class StartingFestivalSituationState(CommonSituationState):
    pass

class GenericOneStateFestivalAttendeeSituation(BaseGenericFestivalSituation):
    INSTANCE_TUNABLES = {'initial_state': StartingFestivalSituationState.TunableFactory(description='\n            The first state that the Sims will be put into when this Situation\n            Starts.\n            ', locked_args={'allow_join_situation': True, 'time_out': None}, tuning_group=SituationComplexCommon.SITUATION_STATE_GROUP)}

    @classmethod
    def _states(cls):
        return (SituationStateData(1, StartingFestivalSituationState, factory=cls.initial_state), SituationStateData(2, CooldownFestivalSituationState, factory=cls.cooldown_state))

    @classmethod
    def _get_tuned_job_and_default_role_state_tuples(cls):
        return list(cls.initial_state._tuned_values.job_and_role_changes.items())

    def start_situation(self):
        super().start_situation()
        self._change_state(self.initial_state())
lock_instance_tunables(GenericOneStateFestivalAttendeeSituation, exclusivity=BouncerExclusivityCategory.FESTIVAL_GOER, creation_ui_option=SituationCreationUIOption.NOT_AVAILABLE, _implies_greeted_status=False)
class StartingTransitioningFestivalSituationState(CommonSituationState):

    def timer_expired(self):
        self._change_state(self.owner.secondary_state())

class SecondaryFestivalSituationState(CommonSituationState):
    pass

class GenericTwoStateFestivalAttendeeSituation(BaseGenericFestivalSituation):
    INSTANCE_TUNABLES = {'initial_state': StartingTransitioningFestivalSituationState.TunableFactory(description='\n            The first state that the Sims will be put into when this Situation\n            Starts.\n            ', locked_args={'allow_join_situation': True}, tuning_group=SituationComplexCommon.SITUATION_STATE_GROUP), 'secondary_state': SecondaryFestivalSituationState.TunableFactory(description='\n            The second state that this situation will be put into once the\n            first state ends.\n            ', locked_args={'allow_join_situation': False, 'time_out': None}, tuning_group=SituationComplexCommon.SITUATION_STATE_GROUP)}

    @classmethod
    def _states(cls):
        return (SituationStateData(1, StartingTransitioningFestivalSituationState, factory=cls.initial_state), SituationStateData(2, SecondaryFestivalSituationState, factory=cls.secondary_state), SituationStateData(3, CooldownFestivalSituationState, factory=cls.cooldown_state))

    @classmethod
    def _get_tuned_job_and_default_role_state_tuples(cls):
        return list(cls.initial_state._tuned_values.job_and_role_changes.items())

    def start_situation(self):
        super().start_situation()
        self._change_state(self.initial_state())
lock_instance_tunables(GenericTwoStateFestivalAttendeeSituation, exclusivity=BouncerExclusivityCategory.FESTIVAL_GOER, creation_ui_option=SituationCreationUIOption.NOT_AVAILABLE, _implies_greeted_status=False)
class EmployeeFestivalSituationState(BaseGenericFestivalSituation):
    INSTANCE_TUNABLES = {'initial_state': StartingFestivalSituationState.TunableFactory(description='\n            The first state that the Sims will be put into when this Situation\n            Starts.\n            ', locked_args={'allow_join_situation': True, 'time_out': None}, tuning_group=SituationComplexCommon.SITUATION_STATE_GROUP)}

    @classmethod
    def _states(cls):
        return (SituationStateData(1, StartingFestivalSituationState, factory=cls.initial_state), SituationStateData(2, CooldownFestivalSituationState, factory=cls.cooldown_state))

    @classmethod
    def _get_tuned_job_and_default_role_state_tuples(cls):
        return list(cls.initial_state._tuned_values.job_and_role_changes.items())

    def start_situation(self):
        super().start_situation()
        self._change_state(self.initial_state())
lock_instance_tunables(EmployeeFestivalSituationState, exclusivity=BouncerExclusivityCategory.FESTIVAL_GOER, creation_ui_option=SituationCreationUIOption.NOT_AVAILABLE, _implies_greeted_status=False)
class _SelectableSimsBackgroundSituationState(SituationState):
    pass

class SelectableSimFestivalSituation(BaseGenericFestivalSituation):
    INSTANCE_TUNABLES = {'job_and_role': TunableSituationJobAndRoleState(description='\n            The job and role that the selectable Sims will be given.\n            ')}
    REMOVE_INSTANCE_TUNABLES = Situation.NON_USER_FACING_REMOVE_INSTANCE_TUNABLES

    @classmethod
    def _states(cls):
        return (SituationStateData(1, _SelectableSimsBackgroundSituationState), SituationStateData(2, CooldownFestivalSituationState, factory=cls.cooldown_state))

    @classmethod
    def _get_tuned_job_and_default_role_state_tuples(cls):
        return [(cls.job_and_role.job, cls.job_and_role.role_state)]

    @classmethod
    def default_job(cls):
        pass

    def start_situation(self):
        super().start_situation()
        self._change_state(_SelectableSimsBackgroundSituationState())

    def _issue_requests(self):
        request = SelectableSimRequestFactory(self, callback_data=_RequestUserData(role_state_type=self.job_and_role.role_state), job_type=self.job_and_role.job, exclusivity=self.exclusivity)
        self.manager.bouncer.submit_request(request)
lock_instance_tunables(SelectableSimFestivalSituation, creation_ui_option=SituationCreationUIOption.NOT_AVAILABLE, _implies_greeted_status=False)
class MultiSimStartingFestivalSituationState(CommonSituationState):
    pass

class MultiSimFestivalSituation(BaseGenericFestivalSituation):
    INSTANCE_TUNABLES = {'group_filter': TunableReference(description='\n            The aggregate filter that we use to find the sims for this\n            situation.\n            ', manager=services.get_instance_manager(sims4.resources.Types.SIM_FILTER), class_restrictions=filters.tunable.TunableAggregateFilter), 'situation_job_mapping': TunableMapping(description='\n            A mapping of filter term tag to situation job.\n            \n            The filter term tag is returned as part of the sim filters used to \n            create the guest list for this particular background situation.\n            \n            The situation job is the job that the Sim will be assigned to in\n            the background situation.\n            ', key_name='filter_tag', key_type=TunableEnumEntry(description='\n                The filter term tag returned with the filter results.\n                ', tunable_type=FilterTermTag, default=FilterTermTag.NO_TAG), value_name='job', value_type=TunableReference(description='\n                The job the Sim will receive when added to the this situation.\n                ', manager=services.get_instance_manager(sims4.resources.Types.SITUATION_JOB))), 'initial_state': MultiSimStartingFestivalSituationState.TunableFactory(description='\n            The first state that the Sims will be put into when this Situation\n            Starts.\n            ', locked_args={'allow_join_situation': True, 'time_out': None}, tuning_group=SituationComplexCommon.SITUATION_STATE_GROUP), 'blacklist_job': SituationJob.TunableReference(description='\n            The default job used for blacklisting Sims from coming back as\n            festival goers.\n            ')}

    @classmethod
    def _states(cls):
        return (SituationStateData(1, MultiSimStartingFestivalSituationState, factory=cls.initial_state), SituationStateData(2, CooldownFestivalSituationState, factory=cls.cooldown_state))

    @classmethod
    def _get_tuned_job_and_default_role_state_tuples(cls):
        return list(cls.initial_state._tuned_values.job_and_role_changes.items())

    @classmethod
    def get_predefined_guest_list(cls):
        guest_list = SituationGuestList(invite_only=True)
        situation_manager = services.get_zone_situation_manager()
        worker_filter = cls.group_filter if cls.group_filter is not None else cls.default_job().filter
        instanced_sim_ids = [sim.sim_info.id for sim in services.sim_info_manager().instanced_sims_gen()]
        household_sim_ids = [sim_info.id for sim_info in services.active_household().sim_info_gen()]
        auto_fill_blacklist = situation_manager.get_auto_fill_blacklist(sim_job=cls.blacklist_job)
        situation_sims = set()
        for situation in situation_manager.get_situations_by_tags(cls.tags):
            situation_sims.update(situation.invited_sim_ids)
        blacklist_sim_ids = set(itertools.chain(situation_sims, instanced_sim_ids, household_sim_ids, auto_fill_blacklist))
        filter_results = services.sim_filter_service().submit_matching_filter(sim_filter=worker_filter, allow_yielding=False, blacklist_sim_ids=blacklist_sim_ids, gsi_source_fn=cls.get_sim_filter_gsi_name)
        if not filter_results:
            return
        for result in filter_results:
            job = cls.situation_job_mapping.get(result.tag, cls.default_job())
            guest_list.add_guest_info(SituationGuestInfo(result.sim_info.sim_id, job, RequestSpawningOption.DONT_CARE, BouncerRequestPriority.BACKGROUND_HIGH))
        return guest_list

    def start_situation(self):
        super().start_situation()
        self._change_state(self.initial_state())
lock_instance_tunables(MultiSimFestivalSituation, creation_ui_option=SituationCreationUIOption.NOT_AVAILABLE, _implies_greeted_status=False)
class FestivalPerformanceSpaceBuskerSituation(BuskerSituationMixin, BaseGenericFestivalSituation):
    REMOVE_INSTANCE_TUNABLES = Situation.NON_USER_FACING_REMOVE_INSTANCE_TUNABLES

    @classmethod
    def _states(cls):
        return (SituationStateData(1, BuskSituationState, factory=cls.busk_state), SituationStateData(2, CooldownFestivalSituationState, factory=cls.cooldown_state))
lock_instance_tunables(FestivalPerformanceSpaceBuskerSituation, creation_ui_option=SituationCreationUIOption.NOT_AVAILABLE, _implies_greeted_status=False)
class FestivalSalesTableVendorSituation(SalesTableVendorSituationMixin, BaseGenericFestivalSituation):
    REMOVE_INSTANCE_TUNABLES = ('cooldown_state',)

    def put_on_cooldown(self):
        self._change_state(self.teardown_state())
lock_instance_tunables(FestivalSalesTableVendorSituation, creation_ui_option=SituationCreationUIOption.NOT_AVAILABLE, duration=0, _implies_greeted_status=False)