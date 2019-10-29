import randomfrom date_and_time import DateAndTimefrom distributor.rollback import ProtocolBufferRollbackfrom event_testing.resolver import SingleSimResolverfrom households.household_tracker import HouseholdTrackerfrom laundry.laundry_tuning import LaundryTuningimport servicesimport sims4logger = sims4.log.Logger('Laundry', default_owner='mkartika')
class HouseholdLaundryTracker(HouseholdTracker):

    def __init__(self, household):
        self._owner = household
        self._last_unload_laundry_time = None
        self._finished_laundry_conditions = {}

    @property
    def owner(self):
        return self._owner

    @property
    def last_unload_laundry_time(self):
        return self._last_unload_laundry_time

    @property
    def finished_laundry_conditions(self):
        return self._finished_laundry_conditions

    def _update_finished_laundry_conditions(self):
        timeout = LaundryTuning.PUT_AWAY_FINISHED_LAUNDRY.laundry_condition_timeout
        now = services.time_service().sim_now
        self._finished_laundry_conditions = {key: value for (key, value) in self._finished_laundry_conditions.items() if timeout >= (now - value[0]).in_minutes()}

    def _apply_laundry_rewards(self, sim):
        self._update_finished_laundry_conditions()
        if self._finished_laundry_conditions:
            chosen_condition = random.choice(list(self._finished_laundry_conditions.values()))
            loot_reward = LaundryTuning.PUT_AWAY_FINISHED_LAUNDRY.conditions_and_rewards_map[chosen_condition[1]]
            resolver = SingleSimResolver(sim.sim_info)
            loot_reward.apply_to_resolver(resolver)

    def apply_laundry_effect(self, sim):
        if self._last_unload_laundry_time is None:
            return
        elapsed_time = (services.time_service().sim_now - self._last_unload_laundry_time).in_minutes()
        if elapsed_time >= LaundryTuning.NOT_DOING_LAUNDRY_PUNISHMENT.timeout:
            resolver = SingleSimResolver(sim.sim_info)
            LaundryTuning.NOT_DOING_LAUNDRY_PUNISHMENT.loot_to_apply.apply_to_resolver(resolver)
            self._finished_laundry_conditions.clear()
        else:
            self._apply_laundry_rewards(sim)

    def update_last_unload_laundry_time(self):
        self._last_unload_laundry_time = services.time_service().sim_now

    def update_finished_laundry_condition(self, resolver):
        target = resolver.interaction.target
        if target is None:
            logger.error('Failed to update finished laundry condition from interaction {} because the target is None.', resolver.interaction)
        sim_now = services.time_service().sim_now
        condition_states = LaundryTuning.PUT_AWAY_FINISHED_LAUNDRY.laundry_condition_states.condition_states
        excluded_states = LaundryTuning.PUT_AWAY_FINISHED_LAUNDRY.laundry_condition_states.excluded_states
        for state_type in condition_states:
            val = target.get_state(state_type)
            if val in excluded_states:
                self._finished_laundry_conditions.pop(val.state, None)
            else:
                self._finished_laundry_conditions[val.state] = (sim_now, val)

    def reset(self):
        self._last_unload_laundry_time = None
        self._finished_laundry_conditions.clear()

    def household_lod_cleanup(self):
        self.reset()

    def save_data(self, household_msg):
        if self._last_unload_laundry_time is None:
            if household_msg.laundry_data.laundry_conditions:
                logger.error("Household {} has Laundry Conditions {} while Last Unload Laundry is None. Bad tracker data, Laundry Conditions won't be saved.", self.owner, self._finished_laundry_conditions)
            return
        household_msg.laundry_data.last_unload_time = self._last_unload_laundry_time.absolute_ticks()
        for (timestamp, state_value) in self._finished_laundry_conditions.values():
            with ProtocolBufferRollback(household_msg.laundry_data.laundry_conditions) as msg:
                msg.timestamp = timestamp.absolute_ticks()
                msg.state_value_name_hash = state_value.guid64

    def load_data(self, household_proto):
        if household_proto.laundry_data.last_unload_time == 0:
            if household_proto.laundry_data.laundry_conditions:
                logger.error("Household {} has Laundry Conditions {} while Last Unload Laundry is None. Laundry Conditions won't be loaded.", self.owner, household_proto.laundry_data.laundry_conditions)
            return
        self._last_unload_laundry_time = DateAndTime(household_proto.laundry_data.last_unload_time)
        object_state_manager = services.get_instance_manager(sims4.resources.Types.OBJECT_STATE)
        for laundry_condition in household_proto.laundry_data.laundry_conditions:
            timestamp = DateAndTime(laundry_condition.timestamp)
            state_value = object_state_manager.get(laundry_condition.state_value_name_hash)
            if state_value is None:
                logger.warn('Failed to load an invalid laundry object state value {} on household {}.', laundry_condition.state_value_name_hash, self.owner)
            else:
                self._finished_laundry_conditions[state_value.state] = (timestamp, state_value)
