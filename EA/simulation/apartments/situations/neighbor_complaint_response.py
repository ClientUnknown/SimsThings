from interactions.base.interaction import Interactionfrom interactions.context import InteractionContext, QueueInsertStrategyfrom interactions.priority import Priorityfrom sims4.tuning.instances import lock_instance_tunablesfrom sims4.utils import classpropertyfrom situations.bouncer.bouncer_types import BouncerExclusivityCategoryfrom situations.situation_complex import SituationComplexCommon, CommonSituationState, TunableSituationJobAndRoleState, SituationStateData, SituationState
class _WaitForNeighborToSpawnState(SituationState):
    pass

class _AnswerDoorState(CommonSituationState):
    FACTORY_TUNABLES = {'interaction_to_push': Interaction.TunableReference(description='\n            The interaction that will be pushed on all non-selectable sims\n            when this situation state begins if there is a front door.\n            ')}

    def __init__(self, *args, interaction_to_push=None, **kwargs):
        super().__init__(*args, **kwargs)
        self._interaction_to_push = interaction_to_push

    def on_activate(self, reader=None):
        super().on_activate(reader)
        if self.owner._neighbor_sim is not None:
            context = InteractionContext(self.owner._neighbor_sim, InteractionContext.SOURCE_SCRIPT, Priority.High, insert_strategy=QueueInsertStrategy.NEXT)
            self.owner._neighbor_sim.push_super_affordance(self._interaction_to_push, self.owner._neighbor_sim, context)

class NeighborResponseSituation(SituationComplexCommon):
    INSTANCE_TUNABLES = {'answer_door_state': _AnswerDoorState.TunableFactory(description='\n            The situation state for the loud neighbor to answer the door.\n            ', tuning_group=SituationComplexCommon.SITUATION_STATE_GROUP, display_name='01_answer_door_situation_state'), 'loud_neighbor_job_and_role_state': TunableSituationJobAndRoleState(description='\n            The job and role state of the loud neighbor.\n            ')}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._neighbor_sim = None

    @classproperty
    def allow_user_facing_goals(cls):
        return False

    @classmethod
    def _states(cls):
        return (SituationStateData(1, _WaitForNeighborToSpawnState), SituationStateData(2, _AnswerDoorState, factory=cls.answer_door_state))

    @classmethod
    def default_job(cls):
        pass

    def _on_set_sim_job(self, sim, job_type):
        super()._on_set_sim_job(sim, job_type)
        self._neighbor_sim = sim
        self._change_state(self.answer_door_state())

    @classmethod
    def _get_tuned_job_and_default_role_state_tuples(cls):
        return [(cls.loud_neighbor_job_and_role_state.job, cls.loud_neighbor_job_and_role_state.role_state)]

    def start_situation(self):
        super().start_situation()
        self._change_state(_WaitForNeighborToSpawnState())
lock_instance_tunables(NeighborResponseSituation, exclusivity=BouncerExclusivityCategory.NORMAL, _implies_greeted_status=False)