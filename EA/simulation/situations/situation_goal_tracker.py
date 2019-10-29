from _collections import dequefrom protocolbuffers import Situations_pb2from distributor.rollback import ProtocolBufferRollbackfrom distributor.system import Distributorfrom event_testing.test_events import TestEventfrom situations.base_situation_goal_tracker import BaseSituationGoalTrackerfrom situations.situation_goal import UiSituationGoalStatusfrom situations.situation_serialization import GoalTrackerTypeimport distributorimport servicesimport sims4.logimport sims4.randomimport situationslogger = sims4.log.Logger('SituationGoals')
class _GoalSetChain:
    UNUSED_DISPLAY_POSITION = -1

    def __init__(self, starting_goal_set_type, chosen_goal_set_type=None, chain_id=None, display_position=None):
        self._starting_goal_set_type = starting_goal_set_type
        if chosen_goal_set_type is None:
            self._next_goal_sets = [starting_goal_set_type]
            self._chosen_goal_set_type = None
        else:
            self._next_goal_sets = None
            self._chosen_goal_set_type = chosen_goal_set_type
        if chain_id is None:
            self._chain_id = self._starting_goal_set_type.guid64
        else:
            self._chain_id = chain_id
        self.display_position = display_position if display_position is not None else self.UNUSED_DISPLAY_POSITION

    def advance_goal_chain(self):
        if self._chosen_goal_set_type.chained_goal_sets is None or len(self._chosen_goal_set_type.chained_goal_sets) == 0:
            self._next_goal_sets = None
        else:
            self._next_goal_sets = list(self._chosen_goal_set_type.chained_goal_sets)
        self._chosen_goal_set_type = None

    @property
    def starting_goal_set_type(self):
        return self._starting_goal_set_type

    @property
    def chain_id(self):
        return self._chain_id

    @property
    def chosen_goal_set_type(self):
        return self._chosen_goal_set_type

    @chosen_goal_set_type.setter
    def chosen_goal_set_type(self, goal_set):
        self._chosen_goal_set_type = goal_set
        self._next_goal_sets = None

    @property
    def next_goal_sets(self):
        return self._next_goal_sets

class SituationGoalTracker(BaseSituationGoalTracker):
    MAX_MINOR_GOALS = 3
    constrained_goals = set()

    def __init__(self, situation):
        super().__init__(situation)
        self._realized_main_goal = None
        self._main_goal_completed = False
        self._realized_minor_goals = {}
        self._goal_chains = None
        self._inherited_target_sim_info = None
        self._completed_goals = {}

    def destroy(self):
        super().destroy()
        self._destroy_realized_goals()
        self._completed_goals = None
        self._goal_chains = None
        self._inherited_target_sim_info = None

    def save_to_seed(self, situation_seed):
        target_sim_id = 0 if self._inherited_target_sim_info is None else self._inherited_target_sim_info.id
        tracker_seedling = situation_seed.setup_for_goal_tracker_save(GoalTrackerType.STANDARD_GOAL_TRACKER, self._has_offered_goals, target_sim_id)
        if self._goal_chains:
            for chain in self._goal_chains:
                chain_seedling = situations.situation_serialization.GoalChainSeedling(chain.starting_goal_set_type, chain.chosen_goal_set_type, chain.chain_id, chain.display_position)
                tracker_seedling.add_chain(chain_seedling)
        if self._realized_main_goal is not None:
            goal_seedling = self._realized_main_goal.create_seedling()
            if self._main_goal_completed:
                goal_seedling.set_completed()
            tracker_seedling.set_main_goal(goal_seedling)
        for (goal, chain) in self._realized_minor_goals.items():
            goal_seedling = goal.create_seedling()
            goal_seedling.chain_id = chain.chain_id
            tracker_seedling.add_minor_goal(goal_seedling)
        for (completed_goal, chosen_goal_set_type) in self.get_completed_goal_info():
            goal_seedling = completed_goal.create_seedling()
            tracker_seedling.add_completed_goal((goal_seedling, chosen_goal_set_type))

    def load_from_seedling(self, tracker_seedling):
        if self._has_offered_goals:
            raise AssertionError('Attempting to load goals for situation: {} but goals have already been offered.'.format(self))
        self._has_offered_goals = tracker_seedling.has_offered_goals
        if tracker_seedling.inherited_target_id != 0:
            self._inherited_target_sim_info = services.sim_info_manager().get(tracker_seedling.inherited_target_id)
        self._goal_chains = []
        for chain_seedling in tracker_seedling.chains:
            self._goal_chains.append(_GoalSetChain(chain_seedling.starting_goal_set_type, chain_seedling.chosen_goal_set_type, chain_seedling.chain_id, chain_seedling.display_position))
        if tracker_seedling.main_goal:
            goal_seedling = tracker_seedling.main_goal
            sim_info = services.sim_info_manager().get(goal_seedling.actor_id)
            self._realized_main_goal = goal_seedling.goal_type(sim_info=sim_info, situation=self._situation, goal_id=self._goal_id_generator(), count=goal_seedling.count, reader=goal_seedling.reader, locked=goal_seedling.locked, completed_time=goal_seedling.completed_time)
            if goal_seedling.completed:
                self._main_goal_completed = True
            else:
                self._realized_main_goal.setup()
                self._realized_main_goal.register_for_on_goal_completed_callback(self._on_goal_completed)
        for goal_seedling in tracker_seedling.minor_goals:
            sim_info = services.sim_info_manager().get(goal_seedling.actor_id)
            for chain in self._goal_chains:
                if chain.chain_id == goal_seedling.chain_id:
                    break
            logger.error('Unable to find chain with chain_id: {} during load of situation: {}', goal_seedling.chain_id, self)
            goal = goal_seedling.goal_type(sim_info=sim_info, situation=self._situation, goal_id=self._goal_id_generator(), count=goal_seedling.count, reader=goal_seedling.reader, locked=goal_seedling.locked, completed_time=goal_seedling.completed_time)
            goal.setup()
            self._realized_minor_goals[goal] = chain
            goal.register_for_on_goal_completed_callback(self._on_goal_completed)
        for (goal_seedling, chosen_goal_set_type) in tracker_seedling.completed_goals:
            sim_info = services.sim_info_manager().get(goal_seedling.actor_id)
            goal = goal_seedling.goal_type(sim_info=sim_info, situation=self._situation, goal_id=self._goal_id_generator(), count=goal_seedling.count, reader=goal_seedling.reader, locked=goal_seedling.locked, completed_time=goal_seedling.completed_time)
            self._completed_goals[goal_seedling.goal_type] = (goal, chosen_goal_set_type)
        self.send_goal_update_to_client()
        self._validate_goal_status()

    def _validate_goal_status(self):
        if self._realized_main_goal is not None:
            self._realized_main_goal.validate_completion()
        for goal in tuple(self._realized_minor_goals.keys()):
            goal.validate_completion()

    def _does_goal_or_goal_set_and_tags_match(self, current_tag_set, goal_or_goal_set):
        if goal_or_goal_set.role_tags:
            return bool(current_tag_set & goal_or_goal_set.role_tags)
        return True

    def _generate_current_tag_match_set(self):
        current_tag_set = set()
        for sim in self._situation.all_sims_in_situation_gen():
            if not sim.is_selectable:
                pass
            else:
                current_tag_set.update(self._situation.get_role_tags_for_sim(sim))
        return current_tag_set

    def _offer_goals(self):
        self._has_offered_goals = True
        new_goals_offered = False
        goal_actor = self._situation.get_situation_goal_actor()
        if self._situation.main_goal is not None:
            self._realized_main_goal = self._situation.main_goal(sim_info=goal_actor, situation=self._situation, goal_id=self._goal_id_generator())
            self._realized_main_goal.setup()
            self._realized_main_goal.on_goal_offered()
            self._realized_main_goal.register_for_on_goal_completed_callback(self._on_goal_completed)
            new_goals_offered = True
        if self._situation.minor_goal_chains is not None:
            self._goal_chains = []
            for goal_set_ref in self._situation.minor_goal_chains:
                self._goal_chains.append(_GoalSetChain(goal_set_ref))
        if self._realized_main_goal is None and self._goal_chains is None and len(self._realized_minor_goals) < self.MAX_MINOR_GOALS:
            available_goal_chains = []
            current_tag_set = self._generate_current_tag_match_set()
            for possible_chain in self._goal_chains:
                if possible_chain.next_goal_sets is None:
                    pass
                elif possible_chain in self._realized_minor_goals.values():
                    pass
                else:
                    available_goal_chains.append(possible_chain)
            num_new_goals = self.MAX_MINOR_GOALS - len(self._realized_minor_goals)
            chosen_tuned_goals = {}
            for chain in available_goal_chains:
                for goal_set_ref in chain.next_goal_sets:
                    if not self._does_goal_or_goal_set_and_tags_match(current_tag_set, goal_set_ref):
                        pass
                    else:
                        weighted_goal_refs = []
                        for weighted_goal_ref in goal_set_ref.goals:
                            if self._does_goal_or_goal_set_and_tags_match(current_tag_set, weighted_goal_ref.goal):
                                weighted_goal_refs.append((weighted_goal_ref.weight, weighted_goal_ref.goal))
                        while len(weighted_goal_refs) > 0:
                            tuned_goal = sims4.random.pop_weighted(weighted_goal_refs)
                            if SituationGoalTracker.constrained_goals and tuned_goal not in SituationGoalTracker.constrained_goals:
                                pass
                            elif tuned_goal in chosen_tuned_goals:
                                pass
                            else:
                                is_realized = False
                                for goal_instance in self._realized_minor_goals:
                                    if tuned_goal is type(goal_instance):
                                        is_realized = True
                                        break
                                if is_realized:
                                    pass
                                else:
                                    old_goal_instance = self._completed_goals.get(tuned_goal)
                                    if old_goal_instance is not None and old_goal_instance[0].is_on_cooldown():
                                        pass
                                    else:
                                        goal_actor_sim = goal_actor.get_sim_instance() if goal_actor is not None else None
                                        if tuned_goal.can_be_given_as_goal(goal_actor_sim, self._situation, inherited_target_sim_info=self._inherited_target_sim_info):
                                            chosen_tuned_goals[tuned_goal] = chain
                                            chain.chosen_goal_set_type = goal_set_ref
                                            break
                        if chain.chosen_goal_set_type is not None:
                            break
                if len(chosen_tuned_goals) >= num_new_goals:
                    break
            for tuned_goal in chosen_tuned_goals.keys():
                goal = tuned_goal(sim_info=goal_actor, situation=self._situation, goal_id=self._goal_id_generator(), inherited_target_sim_info=self._inherited_target_sim_info)
                goal.setup()
                self._realized_minor_goals[goal] = chosen_tuned_goals[tuned_goal]
                goal.on_goal_offered()
                goal.register_for_on_goal_completed_callback(self._on_goal_completed)
                new_goals_offered = True
        logger.debug('Offering Situation Goals in situation {}', self._situation)
        unused_display_priority = deque(range(self.MAX_MINOR_GOALS))
        chains_needing_positions = []
        for chain in self._goal_chains:
            if chain in self._realized_minor_goals.values():
                if chain.display_position != _GoalSetChain.UNUSED_DISPLAY_POSITION:
                    unused_display_priority.remove(chain.display_position)
                else:
                    chains_needing_positions.append(chain)
            else:
                chain.display_position = _GoalSetChain.UNUSED_DISPLAY_POSITION
        for chain in chains_needing_positions:
            chain.display_position = unused_display_priority.popleft()
        if new_goals_offered:
            self._validate_goal_status()
        return new_goals_offered

    def autocomplete_goals_on_load(self, previous_zone_id):
        if self._realized_minor_goals is not None:
            for (goal, _) in tuple(self._realized_minor_goals.items()):
                if goal.should_autocomplete_on_load(previous_zone_id):
                    goal.force_complete(score_override=0, start_cooldown=False)
        if self._realized_main_goal is not None and self._realized_main_goal.should_autocomplete_on_load(previous_zone_id):
            self._realized_main_goal.force_complete(score_override=0, start_cooldown=False)

    def get_goal_info(self):
        infos = []
        if self._realized_minor_goals is not None:
            for (goal, chain) in self._realized_minor_goals.items():
                infos.append((goal, chain.chosen_goal_set_type))
        if self._realized_main_goal is not None:
            infos.insert(0, (self._realized_main_goal, None))
        return infos

    def get_completed_goal_info(self):
        return self._completed_goals.values()

    def debug_force_complete_named_goal(self, goal_name, target_sim=None):
        if self._realized_minor_goals is not None:
            all_realized_goals = list(self._realized_minor_goals.keys())
        else:
            all_realized_goals = []
        if self._realized_main_goal is not None:
            all_realized_goals.insert(0, self._realized_main_goal)
        for goal in all_realized_goals:
            if goal.__class__.__name__.lower().find(goal_name.lower()) != -1:
                goal.force_complete(target_sim=target_sim)
                return True
        return False

    def _destroy_realized_goals(self):
        if self._realized_main_goal is not None:
            self._realized_main_goal.destroy()
            self._realized_main_goal = None
        if self._realized_minor_goals is not None:
            for goal in self._realized_minor_goals.keys():
                goal.destroy()
            self._realized_minor_goals = {}

    def _on_goal_completed(self, goal, goal_completed):
        if goal_completed:
            if goal is self._realized_main_goal:
                self._completed_goals[type(goal)] = (goal, None)
                self._main_goal_completed = True
                services.get_event_manager().process_event(TestEvent.MainSituationGoalComplete, sim_info=goal.sim_info, custom_keys=self._situation.custom_event_keys)
            else:
                chain = self._realized_minor_goals.pop(goal, None)
                if chain is not None:
                    self._completed_goals[type(goal)] = (goal, chain.chosen_goal_set_type)
                    chain.advance_goal_chain()
            goal.decommision()
            self._inherited_target_sim_info = goal.get_actual_target_sim_info()
            self._situation.on_goal_completed(goal)
            self.refresh_goals(completed_goal=goal)
        else:
            self.send_goal_update_to_client()

    def send_goal_update_to_client(self, completed_goal=None, goal_preferences=None):
        situation = self._situation
        if situation.is_user_facing and situation.should_display_score and situation.is_running:
            msg = Situations_pb2.SituationGoalsUpdate()
            msg.situation_id = situation.id
            main_goal = self._realized_main_goal
            if main_goal is not None and situation._main_goal_visibility:
                self._build_goal_message(msg.major_goal, main_goal)
            highlight_first_incomplete_minor_goal = situation.highlight_first_incomplete_minor_goal
            if self._realized_minor_goals is None:
                situation_goals = []
            else:
                situation_goals = sorted(self._realized_minor_goals.keys(), key=lambda goal: self._realized_minor_goals[goal].display_position)
            for goal in situation_goals:
                if not goal.visible_minor_goal:
                    pass
                else:
                    with ProtocolBufferRollback(msg.goals) as goal_msg:
                        self._build_goal_message(goal_msg, goal)
                        if situation.main_goal_audio_sting is not None:
                            goal_msg.audio_sting.type = situation.main_goal_audio_sting.type
                            goal_msg.audio_sting.group = situation.main_goal_audio_sting.group
                            goal_msg.audio_sting.instance = situation.main_goal_audio_sting.instance
                        if main_goal is not None and goal.id == main_goal.id and highlight_first_incomplete_minor_goal:
                            goal_msg.highlight_goal = True
                            highlight_first_incomplete_minor_goal = False
            msg.goal_status = UiSituationGoalStatus.COMPLETED
            if completed_goal is not None:
                msg.completed_goal_id = completed_goal.id
                goal_status_override = completed_goal.goal_status_override
                if goal_status_override is not None:
                    msg.goal_status = goal_status_override
            op = distributor.ops.SituationGoalUpdateOp(msg)
            Distributor.instance().add_op(situation, op)
