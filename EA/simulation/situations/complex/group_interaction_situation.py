from event_testing.test_events import TestEventfrom interactions.aop import AffordanceObjectPairfrom interactions.base.super_interaction import SuperInteractionfrom interactions.context import InteractionContext, InteractionSourcefrom interactions.interaction_finisher import FinishingTypefrom interactions.priority import Priorityfrom objects.terrain import TerrainPointfrom sims4.tuning.tunable import TunableTuple, TunableSimMinutefrom sims4.utils import classpropertyfrom situations.situation_complex import CommonSituationState, SituationStateData, SituationComplexCommon, CommonInteractionCompletedSituationStatefrom situations.situation_job import SituationJobimport servicesimport sims4.logimport situations.situation_typeslogger = sims4.log.Logger('Group Interaction', default_owner='nabaker')
class _InteractionState(CommonInteractionCompletedSituationState):

    def on_activate(self, reader=None):
        super().on_activate(reader)
        leader_sim = self.owner.initiating_sim_info.get_sim_instance()
        if leader_sim is None:
            self.owner._self_destruct()
        members = list(self.owner.all_sims_in_situation_gen())
        constraint_affordance = self.owner.constraint_affordance
        follower_sim_ids = set()
        for sim in members:
            if sim is leader_sim:
                if not sim.si_state.is_running_affordance(self.owner.constraint_leader_affordance):
                    self.owner.remove_sim_from_situation(sim)
                    if not sim.si_state.is_running_affordance(constraint_affordance):
                        self.owner.remove_sim_from_situation(sim)
                    else:
                        follower_sim_ids.add(sim.id)
            elif not sim.si_state.is_running_affordance(constraint_affordance):
                self.owner.remove_sim_from_situation(sim)
            else:
                follower_sim_ids.add(sim.id)
        interaction_context = InteractionContext(leader_sim, InteractionSource.SCRIPT_WITH_USER_INTENT, Priority.High)
        aop = AffordanceObjectPair(self.owner.affordance, self.owner._target_object, self.owner.affordance, None, picked_item_ids=follower_sim_ids)
        aop.test_and_execute(interaction_context)

    def _on_interaction_of_interest_complete(self, **kwargs):
        self.owner._self_destruct()

class _PreSituationState(CommonSituationState):
    PRE_GROUP_INTERACTION_TIMEOUT = 'pre_group_interaction_timeout'

    def on_activate(self, reader=None):
        super().on_activate(reader)
        self._test_event_register(TestEvent.InteractionStart, self.owner.constraint_affordance)
        self._test_event_register(TestEvent.InteractionStart, self.owner.constraint_leader_affordance)
        self._create_or_load_alarm(self.PRE_GROUP_INTERACTION_TIMEOUT, self.owner.pre_situation_state.time_out, lambda _: self.timer_expired(), should_persist=True)

    def handle_event(self, sim_info, event, resolver):
        if event == TestEvent.InteractionStart:
            affordance = resolver._interaction.affordance
            if affordance is self.owner.constraint_affordance or affordance is self.owner.constraint_leader_affordance:
                self.owner.on_sim_finish_routing(sim_info)

    def timer_expired(self):
        next_state = self.owner.get_next_interaction_state()
        self._change_state(next_state())

    def _get_remaining_time_for_gsi(self):
        return self._get_remaining_alarm_time(self.PRE_GROUP_INTERACTION_TIMEOUT)
GROUP_INTERACTION_TUNING_GROUP = 'Group_Interaction'
class GroupInteractionSituation(SituationComplexCommon):
    INSTANCE_TUNABLES = {'pre_situation_state': TunableTuple(description='\n            Information related to the pre interaction situation state.\n            ', situation_state=_PreSituationState.TunableFactory(description='\n                The pre-interaction situation state. Get everyone to their positions\n                and idle.\n                '), time_out=TunableSimMinute(description='\n                How long this will last.\n                ', default=15, minimum=1), tuning_group=GROUP_INTERACTION_TUNING_GROUP), 'constraint_affordance': SuperInteraction.TunableReference(description='\n            The interaction that puts the followers into the constraint.\n            '), 'constraint_leader_affordance': SuperInteraction.TunableReference(description='\n            The interaction that puts the leader into the constraint.\n            '), 'leader_job': SituationJob.TunableReference(description='\n            The situation job for leader.\n            ', tuning_group=GROUP_INTERACTION_TUNING_GROUP), 'member_job': SituationJob.TunableReference(description='\n            The situation job for member.\n            ', tuning_group=GROUP_INTERACTION_TUNING_GROUP), 'interaction_state': _InteractionState.TunableFactory(description='\n            The state that sim is doing the interaction.\n            ', tuning_group=GROUP_INTERACTION_TUNING_GROUP), 'affordance': SuperInteraction.TunableReference(description='\n            The affordance for leader sim to run when all sims have gathered.\n            ', tuning_group=GROUP_INTERACTION_TUNING_GROUP)}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._target_object = None
        self._routing_sims = []

    @classproperty
    def situation_serialization_option(cls):
        return situations.situation_types.SituationSerializationOption.DONT

    def start_situation(self):
        super().start_situation()
        self._create_situation_geometry()
        self._change_state(self.pre_situation_state.situation_state())

    @classmethod
    def _states(cls):
        return (SituationStateData(1, _PreSituationState, factory=cls.pre_situation_state.situation_state), SituationStateData(2, _InteractionState, factory=cls.interaction_state))

    @classmethod
    def default_job(cls):
        pass

    @classmethod
    def _get_tuned_job_and_default_role_state_tuples(cls):
        return list(cls.pre_situation_state.situation_state._tuned_values.job_and_role_changes.items())

    @property
    def should_route_sims_on_add(self):
        return False

    def _on_set_sim_job(self, sim, job_type):
        super()._on_set_sim_job(sim, job_type)
        self._route_sim(sim)

    def _get_ignored_object_ids(self):
        ignored_sim_ids = [sim.id for sim in self.all_sims_in_situation_gen()]
        return ignored_sim_ids

    def get_next_interaction_state(self):
        return self.interaction_state

    def _create_situation_geometry(self):
        seed = self._seed
        default_target_id = seed.extra_kwargs.get('default_target_id', None)
        if default_target_id is not None:
            self._target_object = services.object_manager().get(default_target_id)
        if self._target_object is None:
            default_location = seed.extra_kwargs.get('default_location', None)
            if default_location is not None:
                self._target_object = TerrainPoint(default_location)
            else:
                logger.error('Failed to determine target for {}', self)
                self._self_destruct()
                return
        else:
            leader_sim = self.initiating_sim_info.get_sim_instance()
            if leader_sim is None:
                logger.error('No leader sim for {}', self)
                self._self_destruct()
                return

    def _route_sim(self, sim):
        interaction_context = InteractionContext(sim, InteractionSource.SCRIPT_WITH_USER_INTENT, Priority.High)
        leader_sim = self.initiating_sim_info.get_sim_instance()
        if leader_sim is sim:
            affordance = self.constraint_leader_affordance
        else:
            affordance = self.constraint_affordance
        aop = AffordanceObjectPair(affordance, self._target_object, affordance, None)
        aop.test_and_execute(interaction_context)
        self._routing_sims.append(sim.id)

    def on_sim_finish_routing(self, sim_info):
        if sim_info.id in self._routing_sims:
            self._routing_sims.remove(sim_info.id)
            if not self._routing_sims:
                next_state = self.get_next_interaction_state()
                self._change_state(next_state())
        else:
            logger.error('Sim {} finishes routing but not in routing sim list of situation {}', sim_info, self)

    def _cancel_constraint_affordance_for_sim(self, sim):
        for si in sim.get_all_running_and_queued_interactions():
            if si.affordance is self.constraint_affordance:
                si.cancel(FinishingType.SITUATIONS, cancel_reason_msg='Group Interaction Situation done.')
            if si.affordance is self.constraint_leader_affordance:
                si.cancel(FinishingType.SITUATIONS, cancel_reason_msg='Group Interaction Situation done.')

    def _on_remove_sim_from_situation(self, sim):
        self._cancel_constraint_affordance_for_sim(sim)
        super()._on_remove_sim_from_situation(sim)

    def _destroy(self):
        for sim in self.all_sims_in_situation_gen():
            self._cancel_constraint_affordance_for_sim(sim)
        self._target_object = None
        super()._destroy()
