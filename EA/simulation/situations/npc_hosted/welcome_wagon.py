import randomfrom crafting.crafting_interactions import DebugCreateCraftableInteractionfrom date_and_time import create_time_spanfrom interactions.context import InteractionContext, QueueInsertStrategyfrom interactions.priority import Priorityfrom sims4.tuning.tunable import TunableSimMinute, TunableReference, TunableRange, TunableListfrom sims4.tuning.tunable_base import GroupNamesfrom situations.base_situation import _RequestUserDatafrom situations.bouncer.bouncer_request import SelectableSimRequestFactoryfrom situations.bouncer.bouncer_types import RequestSpawningOption, BouncerRequestPriorityfrom situations.situation import Situationfrom situations.situation_complex import CommonInteractionCompletedSituationState, CommonSituationState, SituationComplexCommon, SituationStateDatafrom situations.situation_guest_list import SituationGuestList, SituationGuestInfoimport servicesimport sims4.tuning.instancesimport situations.bouncerlogger = sims4.log.Logger('Welcome Wagon')WAIT_TO_BE_LET_IN_TIMEOUT = 'wait_to_be_let_in_timeout'FRUITCAKE_TOKEN = 'fruitcake_id'
class _MakeFruitcakeSituationState(CommonInteractionCompletedSituationState):

    def _get_role_state_overrides(self, sim, job_type, role_state_type, role_affordance_target):
        if job_type is not self.owner._fruitcake_bearer_situation_job:
            return super()._get_role_state_overrides(sim, job_type, role_state_type, role_affordance_target)
        if self.owner._fruitcake_id is not None:
            target = services.current_zone().inventory_manager.get(self.owner._fruitcake_id)
        else:
            bearer_recipe = random.choice(self.owner._bearer_recipes)
            if bearer_recipe is None:
                logger.error('No recipes tuned for the fruitcake-bearer. Recipe                creation failed for {} situation', self, owner='shipark')
                return (role_state_type, None)
            target = DebugCreateCraftableInteraction.create_craftable(bearer_recipe, sim, owning_household_id_override=services.active_household_id(), place_in_crafter_inventory=True)
            if target is None:
                raise ValueError('No craftable created for {} on {}'.format(self.owner._fruitcake_recipe, self))
            self.owner._fruitcake_id = target.id
        return (role_state_type, target)

    def _on_interaction_of_interest_complete(self, **kwargs):
        self.owner.create_welcome_wagon()

class _HasFrontDoorSituationStartingState(_MakeFruitcakeSituationState):
    pass

class _HasNoFrontDoorSituationStartingState(_MakeFruitcakeSituationState):
    pass

class PreWelcomeWagon(SituationComplexCommon):
    INSTANCE_TUNABLES = {'has_front_door_situation_starting_state': _HasFrontDoorSituationStartingState.TunableFactory(description='\n                The first state of this situation in the case that the lot\n                has a front door.  If it does not then the Has No Front Door\n                Situation Starting State will be started instead.\n                ', tuning_group=GroupNames.STATE), 'has_no_front_door_situation_starting_state': _HasNoFrontDoorSituationStartingState.TunableFactory(description='\n                The first state of this situation in the case that the lot has\n                no front door.  Sims should be routing to the arrival spawn\n                point.\n                ', tuning_group=GroupNames.STATE), '_door_knocker_situation_job': TunableReference(description='\n                The job for the situation door knocker.  This sim will end up\n                being the host for the situation.\n                ', manager=services.situation_job_manager()), '_fruitcake_bearer_situation_job': TunableReference(description='\n                The job for the bearing of the vile nastiness known as...\n                \n                \n                ...fruitcake...\n                ', manager=services.situation_job_manager()), '_other_neighbors_job': TunableReference(description='\n                The job for all of the other neighbors in the situation.\n                ', manager=services.situation_job_manager()), '_number_of_neighbors': TunableRange(description="\n                The number of other neighbors to bring to the situation.  If\n                there aren't enough neighbors then none will be generated to\n                bring.\n                ", tunable_type=int, default=0, minimum=0), '_bearer_recipes': TunableList(description='\n            A list of recipes from which a random selection will\n            be made and used by the fruitcake bearer to generate and carry\n            a craftable into the Pre Welcome Wagon situation.\n            ', tunable=TunableReference(description='\n                Recipe that will be brought in during the Pre Welcome Wagon \n                situation by the fruitcake-bearer.\n                ', manager=services.get_instance_manager(sims4.resources.Types.RECIPE)), minlength=1), '_welcome_wagon_situation': TunableReference(description='\n                The actual welcome wagon situation that we want to start once\n                we have actually gotten the Sims to where we want them to be.\n                ', manager=services.get_instance_manager(sims4.resources.Types.SITUATION))}
    REMOVE_INSTANCE_TUNABLES = Situation.NON_USER_FACING_REMOVE_INSTANCE_TUNABLES

    @classmethod
    def _states(cls):
        return (SituationStateData(1, _HasFrontDoorSituationStartingState, factory=cls.has_front_door_situation_starting_state), SituationStateData(2, _HasNoFrontDoorSituationStartingState, factory=cls.has_no_front_door_situation_starting_state))

    @classmethod
    def default_job(cls):
        pass

    @classmethod
    def _get_tuned_job_and_default_role_state_tuples(cls):
        return list(cls.has_front_door_situation_starting_state._tuned_values.job_and_role_changes.items())

    @classmethod
    def get_predefined_guest_list(cls):
        active_sim_info = services.active_sim_info()
        door_knocker_results = services.sim_filter_service().submit_filter(cls._door_knocker_situation_job.filter, callback=None, requesting_sim_info=active_sim_info, allow_yielding=False, gsi_source_fn=cls.get_sim_filter_gsi_name)
        if not door_knocker_results:
            return
        door_knocker = random.choice(door_knocker_results)
        guest_list = SituationGuestList(invite_only=True, host_sim_id=door_knocker.sim_info.sim_id, filter_requesting_sim_id=active_sim_info.sim_id)
        guest_list.add_guest_info(SituationGuestInfo(door_knocker.sim_info.sim_id, cls._door_knocker_situation_job, RequestSpawningOption.DONT_CARE, BouncerRequestPriority.EVENT_VIP, expectation_preference=True))
        blacklist = set()
        blacklist.add(door_knocker.sim_info.sim_id)
        fruitcake_bearer_results = services.sim_filter_service().submit_filter(cls._fruitcake_bearer_situation_job.filter, callback=None, requesting_sim_info=active_sim_info, allow_yielding=False, blacklist_sim_ids=blacklist, gsi_source_fn=cls.get_sim_filter_gsi_name)
        if not fruitcake_bearer_results:
            return guest_list
        fruitcake_bearer = random.choice(fruitcake_bearer_results)
        guest_list.add_guest_info(SituationGuestInfo(fruitcake_bearer.sim_info.sim_id, cls._fruitcake_bearer_situation_job, RequestSpawningOption.DONT_CARE, BouncerRequestPriority.EVENT_VIP, expectation_preference=True))
        blacklist.add(fruitcake_bearer.sim_info.sim_id)
        other_neighbors_results = services.sim_filter_service().submit_filter(cls._other_neighbors_job.filter, callback=None, requesting_sim_info=active_sim_info, allow_yielding=False, blacklist_sim_ids=blacklist, gsi_source_fn=cls.get_sim_filter_gsi_name)
        if not other_neighbors_results:
            return guest_list
        if len(other_neighbors_results) > cls._number_of_neighbors:
            neighbors = random.sample(other_neighbors_results, cls._number_of_neighbors)
        else:
            neighbors = other_neighbors_results
        for neighbor in neighbors:
            guest_list.add_guest_info(SituationGuestInfo(neighbor.sim_info.sim_id, cls._other_neighbors_job, RequestSpawningOption.DONT_CARE, BouncerRequestPriority.EVENT_VIP, expectation_preference=True))
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
sims4.tuning.instances.lock_instance_tunables(PreWelcomeWagon, exclusivity=situations.bouncer.bouncer_types.BouncerExclusivityCategory.NORMAL, creation_ui_option=situations.situation_types.SituationCreationUIOption.NOT_AVAILABLE)
class _WaitToBeLetInState(CommonInteractionCompletedSituationState):
    FACTORY_TUNABLES = {'timeout': TunableSimMinute(description='\n                The amount of time to wait in this situation state before it\n                times out and we send the sims home.\n                ', default=10, minimum=1)}

    def __init__(self, timeout, **kwargs):
        super().__init__(**kwargs)
        self._timeout = timeout

    def on_activate(self, reader=None):
        super().on_activate(reader)
        self._create_or_load_alarm(WAIT_TO_BE_LET_IN_TIMEOUT, self._timeout, lambda _: self.timer_expired(), should_persist=True, reader=reader)

    def timer_expired(self):
        self.owner._self_destruct()

    def _on_interaction_of_interest_complete(self, **kwargs):
        self._change_state(self.owner.party_situation_state())

class _PartySituationState(CommonSituationState):
    FACTORY_TUNABLES = {'interaction_to_push': TunableReference(description='\n                The interaction that will be pushed on all non-selectable sims\n                when this situation state begins if there is a front door.\n                ', manager=services.get_instance_manager(sims4.resources.Types.INTERACTION), display_name='Interaction To Push If Front Door Exists.')}

    def __init__(self, interaction_to_push, **kwargs):
        super().__init__(**kwargs)
        self._interaction_to_push = interaction_to_push

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

class WelcomeWagon(SituationComplexCommon):
    INSTANCE_TUNABLES = {'wait_to_be_let_in_state': _WaitToBeLetInState.TunableFactory(description='\n                Second state of the situation.  In this state the sims should\n                be waiting to be let into the house.\n                ', tuning_group=GroupNames.STATE), 'party_situation_state': _PartySituationState.TunableFactory(description='\n                The third situation state.  In this state everyone parties!\n                ', tuning_group=GroupNames.STATE), '_door_knocker_situation_job': TunableReference(description='\n                The job for the situation door knocker.  This sim will end up\n                being the host for the situation.\n                ', manager=services.situation_job_manager()), '_fruitcake_bearer_situation_job': TunableReference(description='\n                The job for the bearing of the vile nastiness known as...\n                \n                \n                ...fruitcake...\n                ', manager=services.situation_job_manager()), '_other_neighbors_job': TunableReference(description='\n                The job for all of the other neighbors in the situation.\n                ', manager=services.situation_job_manager()), '_player_sim_job': TunableReference(description='\n                The job for all of the player sims.\n                ', manager=services.situation_job_manager())}

    @classmethod
    def _states(cls):
        return (SituationStateData(3, _WaitToBeLetInState, factory=cls.wait_to_be_let_in_state), SituationStateData(4, _PartySituationState, factory=cls.party_situation_state))

    @classmethod
    def default_job(cls):
        pass

    @classmethod
    def _get_tuned_job_and_default_role_state_tuples(cls):
        return list(cls.wait_to_be_let_in_state._tuned_values.job_and_role_changes.items())

    def start_situation(self):
        super().start_situation()
        self._change_state(self.wait_to_be_let_in_state())

    def _issue_requests(self):
        super()._issue_requests()
        request = SelectableSimRequestFactory(self, callback_data=_RequestUserData(), job_type=self._player_sim_job, exclusivity=self.exclusivity)
        self.manager.bouncer.submit_request(request)
sims4.tuning.instances.lock_instance_tunables(WelcomeWagon, exclusivity=situations.bouncer.bouncer_types.BouncerExclusivityCategory.NORMAL, creation_ui_option=situations.situation_types.SituationCreationUIOption.NOT_AVAILABLE)