import randomfrom buffs.tunable import TunableBuffReferencefrom event_testing.resolver import DoubleSimResolverfrom interactions.context import InteractionContext, QueueInsertStrategyfrom interactions.priority import Priorityfrom sims4.localization import TunableLocalizedStringfrom sims4.tuning.tunable import TunableSimMinute, TunableReference, TunableRange, Tunablefrom sims4.tuning.tunable_base import GroupNamesfrom situations.base_situation import _RequestUserDatafrom situations.bouncer.bouncer_request import SelectableSimRequestFactory, BouncerRequestfrom situations.bouncer.bouncer_types import RequestSpawningOption, BouncerRequestPriorityfrom situations.npc_hosted.welcome_wagon import _MakeFruitcakeSituationStatefrom situations.situation import Situationfrom situations.situation_complex import CommonInteractionCompletedSituationState, SituationComplexCommon, SituationStateData, CommonSituationStatefrom situations.situation_guest_list import SituationGuestList, SituationGuestInfofrom situations.situation_types import SituationCommonBlacklistCategoryfrom ui.ui_dialog_notification import UiDialogNotificationimport servicesimport sims4.tuning.instancesimport situations.bouncerSTRANGE_WELCOME_WAGON = 'strange_welcome_wagon'WAIT_TO_BE_LET_IN_TIMEOUT = 'wait_to_be_let_in_timeout'FRUITCAKE_TOKEN = 'fruitcake_id'
class MakeFruitcakeAndPossessionSituationState(_MakeFruitcakeSituationState):

    def _on_set_sim_role_state(self, sim, job_type, role_state_type, role_affordance_target):
        super()._on_set_sim_role_state(sim, job_type, role_state_type, role_affordance_target)
        source = self.owner._possession_source
        sim.add_buff_from_op(source.buff_type, buff_reason=source.buff_reason)

class HasFrontDoorStrangeSituationStartingState(MakeFruitcakeAndPossessionSituationState):
    pass

class HasNoFrontDoorStrangeSituationStartingState(MakeFruitcakeAndPossessionSituationState):
    pass

class StrangePreWelcomeWagon(SituationComplexCommon):
    INSTANCE_TUNABLES = {'has_front_door_situation_starting_state': HasFrontDoorStrangeSituationStartingState.TunableFactory(description='\n            The first state of this situation in the case that the lot\n            has a front door.  If it does not then the Has No Front Door\n            Situation Starting State will be started instead.\n            ', tuning_group=GroupNames.STATE), 'has_no_front_door_situation_starting_state': HasNoFrontDoorStrangeSituationStartingState.TunableFactory(description='\n            The first state of this situation in the case that the lot has\n            no front door.  Sims should be routing to the arrival spawn\n            point.\n            ', tuning_group=GroupNames.STATE), '_door_knocker_situation_job': TunableReference(description='\n            The job for the situation door knocker.  This sim will end up\n            being the host for the situation.\n            ', manager=services.situation_job_manager()), '_fruitcake_bearer_situation_job': TunableReference(description='\n            The job for the bearing of the vile nastiness known as...\n            \n            \n            ...fruitcake...\n            ', manager=services.situation_job_manager()), '_other_infected_job': TunableReference(description='\n            The job for all of the other infected in the situation.\n            ', manager=services.situation_job_manager()), '_extra_infected': TunableRange(description='\n            The number of additional infected Sims to bring.\n            ', tunable_type=int, default=1, minimum=1), '_fruitcake_recipe': TunableReference(description='\n            A recipe for the revolting food product commonly known as...\n            \n            \n            ...fruitcake...\n            ', manager=services.get_instance_manager(sims4.resources.Types.RECIPE)), '_welcome_wagon_situation': TunableReference(description='\n            The actual welcome wagon situation that we want to start once\n            we have actually gotten the Sims to where we want them to be.\n            ', manager=services.get_instance_manager(sims4.resources.Types.SITUATION)), '_possession_source': TunableBuffReference(description="\n            Possession buff that keeps the Sims possessed even after the\n            situation's end.\n            ")}
    REMOVE_INSTANCE_TUNABLES = Situation.NON_USER_FACING_REMOVE_INSTANCE_TUNABLES

    @classmethod
    def _states(cls):
        return (SituationStateData(1, HasFrontDoorStrangeSituationStartingState, factory=cls.has_front_door_situation_starting_state), SituationStateData(2, HasNoFrontDoorStrangeSituationStartingState, factory=cls.has_no_front_door_situation_starting_state))

    @classmethod
    def default_job(cls):
        pass

    @classmethod
    def _get_tuned_job_and_default_role_state_tuples(cls):
        return list(cls.has_front_door_situation_starting_state._tuned_values.job_and_role_changes.items())

    @classmethod
    def get_predefined_guest_list(cls):
        active_sim_info = services.active_sim_info()
        door_knocker_results = services.sim_filter_service().submit_matching_filter(sim_filter=cls._door_knocker_situation_job.filter, callback=None, requesting_sim_info=active_sim_info, allow_yielding=False, gsi_source_fn=cls.get_sim_filter_gsi_name)
        door_knocker = door_knocker_results[0]
        guest_list = SituationGuestList(invite_only=True, host_sim_id=door_knocker.sim_info.sim_id, filter_requesting_sim_id=active_sim_info.sim_id)
        guest_list.add_guest_info(SituationGuestInfo(door_knocker.sim_info.sim_id, cls._door_knocker_situation_job, RequestSpawningOption.DONT_CARE, BouncerRequestPriority.EVENT_VIP, expectation_preference=True))
        blacklist = set()
        blacklist.add(door_knocker.sim_info.sim_id)
        fruitcake_bearer_results = services.sim_filter_service().submit_matching_filter(sim_filter=cls._fruitcake_bearer_situation_job.filter, callback=None, requesting_sim_info=active_sim_info, allow_yielding=False, blacklist_sim_ids=blacklist, gsi_source_fn=cls.get_sim_filter_gsi_name)
        fruitcake_bearer = fruitcake_bearer_results[0]
        guest_list.add_guest_info(SituationGuestInfo(fruitcake_bearer.sim_info.sim_id, cls._fruitcake_bearer_situation_job, RequestSpawningOption.DONT_CARE, BouncerRequestPriority.EVENT_VIP, expectation_preference=True))
        blacklist.add(fruitcake_bearer.sim_info.sim_id)
        guaranteed_infected_results = services.sim_filter_service().submit_matching_filter(sim_filter=cls._other_infected_job.filter, callback=None, requesting_sim_info=active_sim_info, allow_yielding=False, blacklist_sim_ids=blacklist, gsi_source_fn=cls.get_sim_filter_gsi_name)
        guaranteed_infected = guaranteed_infected_results[0]
        guest_list.add_guest_info(SituationGuestInfo(guaranteed_infected.sim_info.sim_id, cls._other_infected_job, RequestSpawningOption.DONT_CARE, BouncerRequestPriority.EVENT_VIP, expectation_preference=True))
        other_infected = services.sim_filter_service().submit_filter(sim_filter=cls._other_infected_job.filter, callback=None, requesting_sim_info=active_sim_info, allow_yielding=False, blacklist_sim_ids=blacklist, gsi_source_fn=cls.get_sim_filter_gsi_name)
        if not other_infected:
            return guest_list
        if len(other_infected) > cls._extra_infected - 1:
            infected_to_come = random.sample(other_infected, cls._extra_infected - 1)
        else:
            infected_to_come = other_infected
        for infected in infected_to_come:
            guest_list.add_guest_info(SituationGuestInfo(infected.sim_info.sim_id, cls._other_infected_job, RequestSpawningOption.DONT_CARE, BouncerRequestPriority.EVENT_VIP, expectation_preference=True))
        return guest_list

    def __init__(self, *arg, **kwargs):
        super().__init__(*arg, **kwargs)
        reader = self._seed.custom_init_params_reader
        if reader is None:
            self._fruitcake_id = None
        else:
            self._fruitcake_id = reader.read_uint64(FRUITCAKE_TOKEN, None)

    def _save_custom_situation(self, writer):
        super()._save_custom_situation(writer)
        if self._fruitcake_id is not None:
            writer.write_uint64(FRUITCAKE_TOKEN, self._fruitcake_id)

    @property
    def _bearer_recipes(self):
        return (self._fruitcake_recipe,)

    def start_situation(self):
        super().start_situation()
        if services.get_door_service().has_front_door():
            self._change_state(self.has_front_door_situation_starting_state())
        else:
            self._change_state(self.has_no_front_door_situation_starting_state())

    def create_welcome_wagon(self):
        situation_manager = services.get_zone_situation_manager()
        if not situation_manager.is_user_facing_situation_running():
            situation_manager.create_situation(self._welcome_wagon_situation, guest_list=self._guest_list.clone(), user_facing=True, scoring_enabled=False)
        active_household = services.active_household()
        active_household.needs_welcome_wagon = False
        self._self_destruct()
sims4.tuning.instances.lock_instance_tunables(StrangePreWelcomeWagon, exclusivity=situations.bouncer.bouncer_types.BouncerExclusivityCategory.NORMAL, creation_ui_option=situations.situation_types.SituationCreationUIOption.NOT_AVAILABLE)
class WaitToInfectSituationState(CommonInteractionCompletedSituationState):
    FACTORY_TUNABLES = {'timeout': TunableSimMinute(description='\n            The amount of time to wait in this situation state before it\n            times out and we send the sims home.\n            ', default=10, minimum=1)}

    def __init__(self, timeout, **kwargs):
        super().__init__(**kwargs)
        self._timeout = timeout

    def on_activate(self, reader=None):
        super().on_activate(reader)
        self._create_or_load_alarm(WAIT_TO_BE_LET_IN_TIMEOUT, self._timeout, lambda _: self.timer_expired(), should_persist=True, reader=reader)

    def timer_expired(self):
        self.owner._self_destruct()

    def _on_interaction_of_interest_complete(self, **kwargs):
        self._change_state(self.owner.infect_state())
INFECTION_SPREAD_TOKEN = 'infection_spread'
class InfectSituationState(CommonInteractionCompletedSituationState):
    FACTORY_TUNABLES = {'interaction_to_push': TunableReference(description='\n            The interaction that will be pushed on all non-selectable sims\n            when this situation state begins if there is a front door.\n            ', manager=services.get_instance_manager(sims4.resources.Types.INTERACTION), display_name='Interaction To Push If Front Door Exists.'), 'post_welcome_wagon_situation': TunableReference(description='\n            The post welcome wagon agent situation that will attempt to clean\n            up after the infected.\n            ', manager=services.get_instance_manager(sims4.resources.Types.SITUATION))}

    def __init__(self, interaction_to_push, post_welcome_wagon_situation, **kwargs):
        super().__init__(**kwargs)
        self._interaction_to_push = interaction_to_push
        self._post_welcome_wagon_situation = post_welcome_wagon_situation
        self._infection_spread = 0

    def on_activate(self, reader=None):
        super().on_activate(reader)
        if not services.get_door_service().has_front_door():
            return
        for sim in self.owner.all_sims_in_situation_gen():
            if sim.is_selectable:
                pass
            else:
                context = InteractionContext(sim, InteractionContext.SOURCE_SCRIPT, Priority.High, insert_strategy=QueueInsertStrategy.NEXT)
                sim.push_super_affordance(self._interaction_to_push, sim, context)
        if reader is not None:
            self._infection_spread = reader.read_uint64(INFECTION_SPREAD_TOKEN, 0)

    def save_state(self, writer):
        super().save_state(writer)
        writer.write_uint64(INFECTION_SPREAD_TOKEN, self._infection_spread)

    def _on_interaction_of_interest_complete(self, **kwargs):
        self._infection_spread += 1

    def on_deactivate(self):
        if self._infection_spread > 0:
            services.get_zone_situation_manager().create_situation(self._post_welcome_wagon_situation, user_facing=False, scoring_enabled=False)
        super().on_deactivate()

class StrangeWelcomeWagon(SituationComplexCommon):
    INSTANCE_TUNABLES = {'wait_to_infect_state': WaitToInfectSituationState.TunableFactory(description='\n            Second state of the situation.  In this state the sims should\n            be waiting to be let into the house.\n            ', tuning_group=GroupNames.STATE), 'infect_state': InfectSituationState.TunableFactory(description='\n            The third situation state.  In this state everyone parties!\n            ', tuning_group=GroupNames.STATE), '_player_sim_job': TunableReference(description='\n            The job for all of the player sims.\n            ', manager=services.situation_job_manager())}

    @classmethod
    def _states(cls):
        return (SituationStateData(1, WaitToInfectSituationState, factory=cls.wait_to_infect_state), SituationStateData(2, InfectSituationState, factory=cls.infect_state))

    @classmethod
    def default_job(cls):
        pass

    @classmethod
    def _get_tuned_job_and_default_role_state_tuples(cls):
        return list(cls.wait_to_infect_state._tuned_values.job_and_role_changes.items())

    def start_situation(self):
        super().start_situation()
        self._change_state(self.wait_to_infect_state())

    def _issue_requests(self):
        super()._issue_requests()
        request = SelectableSimRequestFactory(self, callback_data=_RequestUserData(), job_type=self._player_sim_job, exclusivity=self.exclusivity)
        self.manager.bouncer.submit_request(request)

    def _on_remove_sim_from_situation(self, sim):
        situation_manager = services.get_zone_situation_manager()
        situation_sim = self._situation_sims.get(sim)
        if situation_sim is not None and situation_sim.current_job_type is not self._player_sim_job:
            situation_manager.make_sim_leave_now_must_run(sim)
        super()._on_remove_sim_from_situation(sim)
sims4.tuning.instances.lock_instance_tunables(StrangeWelcomeWagon, exclusivity=situations.bouncer.bouncer_types.BouncerExclusivityCategory.NORMAL, creation_ui_option=situations.situation_types.SituationCreationUIOption.NOT_AVAILABLE)
class DelayState(CommonSituationState):

    def timer_expired(self):
        self.owner._change_state(self.owner.clean_up_state())

class CleanUpState(CommonInteractionCompletedSituationState):

    def on_activate(self, reader=None):
        super().on_activate(reader)
        self.owner._create_agents()

    def _on_interaction_of_interest_complete(self, **kwargs):
        self.owner._change_state(self.owner.nothing_to_see_here_state())

    def timer_expired(self):
        self.owner._change_state(self.owner.nothing_to_see_here_state())

class NothingToSeeHereState(CommonInteractionCompletedSituationState):
    FACTORY_TUNABLES = {'timeout_notification': UiDialogNotification.TunableFactory(description='\n            The notification that will play if the situation times out.\n            ')}

    def __init__(self, *args, timeout_notification=None, **kwargs):
        super().__init__(*args, **kwargs)
        self._timeout_notification = timeout_notification

    def _end_situation(self):
        active_sim_info = services.active_sim_info()
        agent = next(iter(self.owner.all_sims_in_situation_gen()))
        notification = self._timeout_notification(active_sim_info, resolver=DoubleSimResolver(active_sim_info, agent))
        notification.show_dialog()
        situation_manger = services.get_zone_situation_manager()
        for sim in self.owner.all_sims_in_situation_gen():
            situation_manger.make_sim_leave_now_must_run(sim)
        self.owner._self_destruct()

    def _on_interaction_of_interest_complete(self, **kwargs):
        self._end_situation()

    def timer_expired(self):
        self._end_situation()

class StrangePostWelcomeWagon(SituationComplexCommon):
    INSTANCE_TUNABLES = {'delay_state': DelayState.TunableFactory(description='\n            A state in which the game delays creating the agents in order to\n            give the infected some time to leave.\n            ', tuning_group=GroupNames.STATE), 'clean_up_state': CleanUpState.TunableFactory(description='\n            A state in which the agents clean up what was done by the\n            infected Sims.\n            ', tuning_group=GroupNames.STATE), 'nothing_to_see_here_state': NothingToSeeHereState.TunableFactory(description='\n            A state in which the agents inform the player Sim that there\n            is nothing to see here before leaving.\n            ', tuning_group=GroupNames.STATE), 'save_lock_tooltip': TunableLocalizedString(description='\n            The tooltip/message to show when the player tries to save the game\n            while this situation is running. Save is locked when situation starts.\n            ', tuning_group=GroupNames.UI), 'secret_agent_job': TunableReference(description='\n            The job for all of the agents.\n            ', manager=services.get_instance_manager(sims4.resources.Types.SITUATION_JOB)), 'secret_agents_to_create': TunableRange(description='\n            The number of agents that will be created.\n            ', tunable_type=int, default=1, minimum=1)}
    REMOVE_INSTANCE_TUNABLES = Situation.NON_USER_FACING_REMOVE_INSTANCE_TUNABLES

    @classmethod
    def _states(cls):
        return (SituationStateData.from_auto_factory(0, cls.delay_state), SituationStateData(1, CleanUpState, factory=cls.clean_up_state), SituationStateData(2, NothingToSeeHereState, factory=cls.nothing_to_see_here_state))

    @classmethod
    def default_job(cls):
        pass

    @classmethod
    def _get_tuned_job_and_default_role_state_tuples(cls):
        return list(cls.clean_up_state._tuned_values.job_and_role_changes.items())

    def _destroy(self):
        super()._destroy()
        services.get_persistence_service().unlock_save(self)

    def start_situation(self):
        services.get_persistence_service().lock_save(self)
        super().start_situation()
        self._change_state(self.delay_state())

    def get_lock_save_reason(self):
        return self.save_lock_tooltip

    def _create_agents(self):
        for _ in range(self.secret_agents_to_create):
            request = BouncerRequest(self, callback_data=_RequestUserData(), job_type=self.secret_agent_job, request_priority=BouncerRequestPriority.GAME_BREAKER, user_facing=self.is_user_facing, exclusivity=self.exclusivity, common_blacklist_categories=SituationCommonBlacklistCategory.ACTIVE_HOUSEHOLD | SituationCommonBlacklistCategory.ACTIVE_LOT_HOUSEHOLD, spawning_option=RequestSpawningOption.MUST_SPAWN, accept_looking_for_more_work=self.secret_agent_job.accept_looking_for_more_work)
            self.manager.bouncer.submit_request(request)
sims4.tuning.instances.lock_instance_tunables(StrangePostWelcomeWagon, exclusivity=situations.bouncer.bouncer_types.BouncerExclusivityCategory.NORMAL, creation_ui_option=situations.situation_types.SituationCreationUIOption.NOT_AVAILABLE)