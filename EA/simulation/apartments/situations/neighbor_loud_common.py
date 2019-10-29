import randomfrom event_testing.resolver import SingleSimResolverfrom filters.tunable import TunableSimFilterfrom interactions.utils.loot import LootActionsfrom objects.components.state import TunableStateValueReferencefrom sims4.tuning.instances import lock_instance_tunablesfrom sims4.tuning.tunable import Tunable, TunableList, TunableTuple, TunableSimMinute, TunableVariantfrom sims4.utils import classpropertyfrom situations.bouncer.bouncer_types import BouncerExclusivityCategory, RequestSpawningOption, BouncerRequestPriorityfrom situations.situation import Situationfrom situations.situation_complex import SituationComplexCommon, CommonInteractionCompletedSituationState, SituationStateData, CommonInteractionStartedSituationStatefrom situations.situation_guest_list import SituationGuestList, SituationGuestInfoimport clockimport filtersimport servicesimport sims4.loglogger = sims4.log.Logger('LoudNeighborSituation', default_owner='rmccord')NEIGHBOR_TOKEN = 'neighbor_id'DOOR_TOKEN = 'door_id'
class _LoudNeighborState(CommonInteractionCompletedSituationState):
    LOOT_ACTION_DELAY = 'loot_action_delay'
    FACTORY_TUNABLES = {'loot_actions_on_situation_start': TunableTuple(description='\n            A list of loot actions and a delay before they are applied to all\n            instanced sims on the active lot.\n            ', loot_actions=TunableList(description='\n                Loot Actions that will be applied to instanced Sims on lot when\n                this situation starts.\n                ', tunable=LootActions.TunableReference(description='\n                    A loot action applied to instanced Sims on the active lot when\n                    the situation starts.\n                    ')), delay=TunableSimMinute(description="\n                The delay in sim minutes before we give the loot to Sims on\n                lot. This delay starts from when the loud state is set on the\n                neighbor's door.\n                ", default=0, minimum=0))}

    def __init__(self, *args, loot_actions_on_situation_start=None, **kwargs):
        super().__init__(*args, **kwargs)
        self._loot_actions_on_situation_start = loot_actions_on_situation_start

    def on_activate(self, reader=None):
        super().on_activate(reader)
        self._add_neighbor_to_auto_fill_blacklist()
        self._set_loud_door_state()
        self._create_or_load_alarm(_LoudNeighborState.LOOT_ACTION_DELAY, self._loot_actions_on_situation_start.delay, lambda _: self._apply_loud_loot_actions(), should_persist=True, reader=reader)

    def _add_neighbor_to_auto_fill_blacklist(self):
        timeout = self._get_remaining_alarm_time(self._time_out_string)
        next_state_timeout = self.owner.complain_state()._time_out
        if next_state_timeout is not None:
            timeout += clock.interval_in_sim_minutes(next_state_timeout)
        services.get_zone_situation_manager().add_sim_to_auto_fill_blacklist(self.owner._neighbor_sim_id, blacklist_all_jobs_time=timeout.in_hours())

    def _set_loud_door_state(self):
        if self.owner._neighbor_door_id is None:
            self.owner._self_destruct()
        apartment_door = services.object_manager().get(self.owner._neighbor_door_id)
        if apartment_door is None:
            self.owner._self_destruct()
            return
        apartment_door.set_state(self.owner.loud_door_state_on.state, self.owner.loud_door_state_on)

    def _apply_loud_loot_actions(self):
        sim_info_manager = services.sim_info_manager()
        for sim in sim_info_manager.instanced_sims_gen():
            resolver = SingleSimResolver(sim.sim_info)
            if sim.is_on_active_lot():
                for loot_action in self._loot_actions_on_situation_start.loot_actions:
                    loot_action.apply_to_resolver(resolver)

    def _on_interaction_of_interest_complete(self, **kwargs):
        self.owner._change_state(self.owner.complain_state())

    def timer_expired(self):
        services.get_zone_situation_manager().remove_sim_from_auto_fill_blacklist(self.owner._neighbor_sim_id)
        self.owner._self_destruct()

class _ComplainState(CommonInteractionStartedSituationState):
    FACTORY_TUNABLES = {'neighbor_situation': Situation.TunableReference(description='\n            The Situation for the loud neighbor to come out and see what the\n            player wants when they bang on the door.\n            ', class_restrictions=('NeighborResponseSituation',)), 'turn_off_loud_door_state': Tunable(description='\n            If enabled, we will set the door to the loud door off state when\n            entering this situation state.\n            ', tunable_type=bool, default=False)}

    def __init__(self, *args, neighbor_situation=None, turn_off_loud_door_state=None, **kwargs):
        super().__init__(*args, **kwargs)
        self._neighbor_situation = neighbor_situation
        self._turn_off_loud_door_state = turn_off_loud_door_state
        self.neighbor_response_situation_id = None

    def on_activate(self, reader=None):
        super().on_activate(reader)

    def _create_neighbor_response_situation(self):
        situation_manager = services.get_zone_situation_manager()
        guest_list = SituationGuestList(invite_only=True)
        guest_list.add_guest_info(SituationGuestInfo(self.owner._neighbor_sim_id, self._neighbor_situation.loud_neighbor_job_and_role_state.job, RequestSpawningOption.MUST_SPAWN, BouncerRequestPriority.EVENT_VIP))
        self.neighbor_response_situation_id = situation_manager.create_situation(self._neighbor_situation, guest_list=guest_list, user_facing=False)

    def _set_loud_door_state_off(self):
        if self._turn_off_loud_door_state and self.owner._neighbor_door_id is not None:
            apartment_door = services.object_manager().get(self.owner._neighbor_door_id)
            if apartment_door is not None:
                apartment_door.set_state(self.owner.loud_door_state_off.state, self.owner.loud_door_state_off)

    def _on_interaction_of_interest_started(self):
        self._create_neighbor_response_situation()
        services.get_zone_situation_manager().remove_sim_from_auto_fill_blacklist(self.owner._neighbor_sim_id)
        self._set_loud_door_state_off()

class LoudNeighborSituation(SituationComplexCommon):
    INSTANCE_TUNABLES = {'loud_neighbor_state': _LoudNeighborState.TunableFactory(description='\n            The situation state used for when a neighbor starts being loud.\n            This will listen for a Sim to bang on the door and complain about\n            the noise before transitioning to the complain state.\n            ', tuning_group=SituationComplexCommon.SITUATION_STATE_GROUP, display_name='01_loud_neighbor_situation_state'), 'complain_state': _ComplainState.TunableFactory(description="\n            The situation state used for when a player Sim has banged on the\n            neighbor's door and we are waiting for them to complain to the\n            neighbor.\n            ", tuning_group=SituationComplexCommon.SITUATION_STATE_GROUP, display_name='02_complain_situation_state'), 'loud_neighbor_filters': TunableList(description='\n            Sim filters that fit the description of loud neighbor(s). We run\n            through them until we find someone matching the filter.\n            ', tunable=TunableVariant(description='\n                The filter we want to use to find loud neighbors.\n                ', single_filter=TunableSimFilter.TunablePackSafeReference(description='\n                    A Sim Filter to find a loud neighbor.\n                    '), aggregate_filter=TunableSimFilter.TunablePackSafeReference(description='\n                    An aggregate Sim Filter to find a loud neighbor that has\n                    other Sims.\n                    ', class_restrictions=filters.tunable.TunableAggregateFilter), default='single_filter')), 'loud_door_state_on': TunableStateValueReference(description='\n            State to set on the apartment door of the loud neighbor when the\n            situation starts.\n            '), 'loud_door_state_off': TunableStateValueReference(description='\n            State to set on the apartment door of the loud neighbor when they\n            are no longer being loud.\n            ')}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        reader = self._seed.custom_init_params_reader
        if reader is not None:
            self._neighbor_sim_id = reader.read_uint64(NEIGHBOR_TOKEN, None)
            self._neighbor_door_id = reader.read_uint64(DOOR_TOKEN, None)
        else:
            self._neighbor_sim_id = None
            self._neighbor_door_id = None

    @classproperty
    def allow_user_facing_goals(cls):
        return False

    @classmethod
    def _get_tuned_job_and_default_role_state_tuples(cls):
        return []

    @classmethod
    def _states(cls):
        return (SituationStateData(1, _LoudNeighborState, factory=cls.loud_neighbor_state), SituationStateData(2, _ComplainState, factory=cls.complain_state))

    @classmethod
    def default_job(cls):
        pass

    @classmethod
    def situation_meets_starting_requirements(cls, **kwargs):
        neighbor_sim_id = cls._get_loud_neighbor()
        if neighbor_sim_id is None:
            return False
        return True

    def start_situation(self):
        super().start_situation()
        neighbor_sim_id = self._get_loud_neighbor()
        self._set_loud_neighbor_and_door(neighbor_sim_id)
        if self._neighbor_sim_id is not None:
            self._change_state(self.loud_neighbor_state())

    def _save_custom_situation(self, writer):
        super()._save_custom_situation(writer)
        if self._neighbor_sim_id is not None:
            writer.write_uint64(NEIGHBOR_TOKEN, self._neighbor_sim_id)
        if self._neighbor_door_id is not None:
            writer.write_uint64(DOOR_TOKEN, self._neighbor_door_id)

    def _destroy(self):
        if self._neighbor_door_id is not None:
            apartment_door = services.object_manager().get(self._neighbor_door_id)
            if apartment_door is not None:
                apartment_door.set_state(self.loud_door_state_off.state, self.loud_door_state_off)
        services.get_zone_situation_manager().remove_sim_from_auto_fill_blacklist(self._neighbor_sim_id)
        super()._destroy()

    @classmethod
    def _get_loud_neighbor(cls):
        neighbor_sim_id = None
        blacklist_sim_ids = {sim_info.sim_id for sim_info in services.active_household()}
        blacklist_sim_ids.update(set(sim_info.sim_id for sim_info in services.sim_info_manager().instanced_sims_gen()))
        loud_neighbor_filters = sorted(cls.loud_neighbor_filters, key=lambda *args: random.random())
        for neighbor_filter in loud_neighbor_filters:
            neighbors = services.sim_filter_service().submit_matching_filter(sim_filter=neighbor_filter, allow_yielding=False, blacklist_sim_ids=blacklist_sim_ids, gsi_source_fn=cls.get_sim_filter_gsi_name)
            neighbor_sim_infos_at_home = [result.sim_info for result in neighbors if result.sim_info.is_at_home]
            if len(neighbor_sim_infos_at_home) > 1 or len(neighbor_sim_infos_at_home):
                if neighbor_filter.is_aggregate_filter():
                    pass
                else:
                    neighbor_sim_id = neighbor_sim_infos_at_home[0].sim_id if neighbor_sim_infos_at_home else None
                    if neighbor_sim_id is not None:
                        break
        return neighbor_sim_id

    def _set_loud_neighbor_and_door(self, neighbor_sim_id):
        neighbor_sim_info = services.sim_info_manager().get(neighbor_sim_id)
        if neighbor_sim_info is None:
            self._self_destruct()
            return
        self._neighbor_sim_id = neighbor_sim_id
        door_service = services.get_door_service()
        plex_door_infos = door_service.get_plex_door_infos()
        object_manager = services.object_manager()
        for door_info in plex_door_infos:
            door = object_manager.get(door_info.door_id)
            if door is not None and door.household_owner_id == neighbor_sim_info.household_id:
                self._neighbor_door_id = door_info.door_id
                break
        logger.error('Could not find door object that belongs to {}', neighbor_sim_info.household.name)
        self._self_destruct()
lock_instance_tunables(LoudNeighborSituation, exclusivity=BouncerExclusivityCategory.NORMAL, _implies_greeted_status=False)