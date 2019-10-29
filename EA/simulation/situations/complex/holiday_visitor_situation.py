from interactions.base.interaction import Interactionfrom interactions.context import QueueInsertStrategyfrom sims4.tuning.tunable_base import GroupNamesfrom sims4.tuning.tunable import OptionalTunable, Tunablefrom situations.ambient.walkby_limiting_tags_mixin import WalkbyLimitingTagsMixinfrom situations.situation import Situationfrom situations.situation_complex import SituationComplexCommon, SituationStateData, CommonInteractionCompletedSituationState, CommonSituationStatefrom situations.situation_job import SituationJobfrom tag import TunableTagsimport interactionsimport servicesimport sims4.logimport sims4.tuning.instancesimport sims4.tuning.tunableimport situations.bouncerimport randomlogger = sims4.log.Logger('HolidayVisitorNPC', default_owner='jgiordano')INTERACTION_TARGET_TOKEN = 'interaction_target'
class _ArrivalState(CommonInteractionCompletedSituationState):

    def _on_interaction_of_interest_complete(self, **kwargs):
        if self.owner.selected_target is not None:
            self._change_state(self.owner.holiday_visitor_npc_job.push_interaction_state())
        else:
            self._change_state(self.owner.holiday_visitor_npc_job.hang_out_state())

    def timer_expired(self):
        self._on_interaction_of_interest_complete()

class _PushInteractionState(CommonInteractionCompletedSituationState):
    FACTORY_TUNABLES = {'interaction_to_push': Interaction.TunableReference(description='\n            Interaction to push on a random target that was specified by the target\n            filter method.\n            '), 'iterations': Tunable(description='\n            Number of times we want to push the interaction one after the other.\n            ', tunable_type=int, default=1)}

    def __init__(self, interaction_to_push, iterations, **kwargs):
        super().__init__(**kwargs)
        self._interaction_to_push = interaction_to_push
        self._iterations = iterations
        self._iteration_count = 0

    def on_activate(self, reader=None):
        super().on_activate(reader)
        self._push_interaction_or_next_state()

    def _on_interaction_of_interest_complete(self, **kwargs):
        self._iteration_count += 1
        self.owner.selected_target = self.owner.get_random_target()
        self._push_interaction_or_next_state()

    def _push_interaction_or_next_state(self):
        holiday_visitor_npc_sim = self.owner.holiday_visitor_npc()
        if self._iteration_count >= self._iterations or holiday_visitor_npc_sim is None or self.owner.selected_target is None:
            self._change_state(self.owner.holiday_visitor_npc_job.hang_out_state())
            return
        context = interactions.context.InteractionContext(holiday_visitor_npc_sim, interactions.context.InteractionContext.SOURCE_SCRIPT, interactions.priority.Priority.High, insert_strategy=QueueInsertStrategy.NEXT)
        enqueue_result = holiday_visitor_npc_sim.push_super_affordance(self._interaction_to_push, self.owner.selected_target, context)
        if not enqueue_result:
            logger.error('interaction failed to push with result {}', enqueue_result)
            self._change_state(self.owner.holiday_visitor_npc_job.hang_out_state())

    def timer_expired(self):
        self._on_interaction_of_interest_complete()

class _HangOutState(CommonInteractionCompletedSituationState):

    def _on_interaction_of_interest_complete(self, **kwargs):
        self._change_state(self.owner.holiday_visitor_npc_job.leave_state())

    def timer_expired(self):
        self._on_interaction_of_interest_complete()

class _LeaveState(CommonSituationState):
    pass

class HolidayVisitorNPCSituation(WalkbyLimitingTagsMixin, SituationComplexCommon):
    INSTANCE_TUNABLES = {'holiday_visitor_npc_job': sims4.tuning.tunable.TunableTuple(situation_job=SituationJob.TunableReference(description='\n                A reference to the SituationJob used for the Sim performing the\n                holiday visitor situation.\n                '), arrival_state=_ArrivalState.TunableFactory(description='\n                The state for pushing the NPC onto the lot.\n                '), hang_out_state=_HangOutState.TunableFactory(description='\n                State where they hang out using role autonomy (if we want\n                them to eat cookies). The interaction of interest should be them\n                leaving at the fireplace.\n                '), push_interaction_state=_PushInteractionState.TunableFactory(description='\n                The state for pushing the NPC to do an interaction on\n                one of the primary targets\n                '), leave_state=_LeaveState.TunableFactory(description='\n                The state for pushing the NPC to leave.\n                '), tuning_group=GroupNames.SITUATION), 'target_filter_tags': OptionalTunable(description='\n            Choose what kind of targets to grab. If\n            turned on, use tags. Otherwise, use \n            household sims.\n            ', tunable=TunableTags(description='\n                Define tags we want to filter by.\n                ', minlength=1), disabled_name='use_household_sims', enabled_name='use_tags')}
    REMOVE_INSTANCE_TUNABLES = Situation.NON_USER_FACING_REMOVE_INSTANCE_TUNABLES

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.selected_target = None
        reader = self._seed.custom_init_params_reader
        if reader is not None:
            selected_target_id = reader.read_uint64(INTERACTION_TARGET_TOKEN, 0)
            object_manager = services.object_manager()
            self.selected_target = object_manager.get(selected_target_id)

    @classmethod
    def _states(cls):
        return (SituationStateData(1, _ArrivalState, factory=cls.holiday_visitor_npc_job.arrival_state), SituationStateData(2, _PushInteractionState, factory=cls.holiday_visitor_npc_job.push_interaction_state), SituationStateData(3, _HangOutState, factory=cls.holiday_visitor_npc_job.hang_out_state), SituationStateData(4, _LeaveState, factory=cls.holiday_visitor_npc_job.leave_state))

    @classmethod
    def _get_tuned_job_and_default_role_state_tuples(cls):
        return [(cls.holiday_visitor_npc_job.situation_job, cls.holiday_visitor_npc_job.arrival_state)]

    @classmethod
    def default_job(cls):
        pass

    @classmethod
    def get_sims_expected_to_be_in_situation(cls):
        return 1

    def _save_custom_situation(self, writer):
        super()._save_custom_situation(writer)
        if self.selected_target is not None:
            writer.write_uint64(INTERACTION_TARGET_TOKEN, int(self.selected_target.id))

    def holiday_visitor_npc(self):
        sim = next(self.all_sims_in_job_gen(self.holiday_visitor_npc_job.situation_job), None)
        return sim

    def get_random_target(self):
        object_manager = services.object_manager()
        if self.target_filter_tags is not None:
            found_objects = object_manager.get_objects_matching_tags(self.target_filter_tags, match_any=True)
            if len(found_objects) > 0:
                random_object = random.choice(list(found_objects))
                return random_object
            return
        else:
            household_sims = services.active_household().instanced_sims_gen()
            random_sim = random.choice(list(household_sims))
            return random_sim

    def start_situation(self):
        super().start_situation()
        if self.selected_target is None:
            self.selected_target = self.get_random_target()
        self._change_state(self.holiday_visitor_npc_job.arrival_state())
sims4.tuning.instances.lock_instance_tunables(HolidayVisitorNPCSituation, exclusivity=situations.bouncer.bouncer_types.BouncerExclusivityCategory.WORKER, creation_ui_option=situations.situation_types.SituationCreationUIOption.NOT_AVAILABLE)