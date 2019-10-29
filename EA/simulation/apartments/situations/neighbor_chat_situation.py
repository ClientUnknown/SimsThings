from interactions.base.interaction import Interactionfrom interactions.context import InteractionContext, QueueInsertStrategyfrom interactions.priority import Priorityfrom sims4.tuning.instances import lock_instance_tunablesfrom sims4.utils import classpropertyfrom situations.bouncer.bouncer_types import BouncerExclusivityCategoryfrom situations.situation import Situationfrom situations.situation_complex import SituationComplexCommon, CommonSituationState, TunableSituationJobAndRoleState, SituationStateData, SituationStatefrom situations.situation_types import SituationCreationUIOption
class _WaitForNeighborToSpawnState(SituationState):
    pass

class _AnswerDoorState(CommonSituationState):
    FACTORY_TUNABLES = {'interaction_to_push': Interaction.TunableReference(description='\n            The interaction that will be pushed on the neighbor targeting the\n            knocker Sim.\n            ')}

    def __init__(self, *args, interaction_to_push=None, **kwargs):
        super().__init__(*args, **kwargs)
        self._interaction_to_push = interaction_to_push

    def on_activate(self, reader=None):
        super().on_activate(reader)
        if self.owner._neighbor_sim is not None:
            context = InteractionContext(self.owner._neighbor_sim, InteractionContext.SOURCE_SCRIPT, Priority.High, insert_strategy=QueueInsertStrategy.NEXT)
            self.owner._neighbor_sim.push_super_affordance(self._interaction_to_push, self.owner._knocker_sim, context)

class NeighborChatSituation(SituationComplexCommon):
    INSTANCE_TUNABLES = {'answer_door_state': _AnswerDoorState.TunableFactory(description='\n            The situation state for the neighbor to answer the door.\n            ', tuning_group=SituationComplexCommon.SITUATION_STATE_GROUP, display_name='01_answer_door_situation_state'), 'neighbor_job_and_role_state': TunableSituationJobAndRoleState(description='\n            The job and role state of the neighbor.\n            '), 'knocker_job_and_role_state': TunableSituationJobAndRoleState(description='\n            The job and role state of the Sim that knocked.\n            ')}
    REMOVE_INSTANCE_TUNABLES = Situation.NON_USER_FACING_REMOVE_INSTANCE_TUNABLES

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._neighbor_sim = None
        self._knocker_sim = None

    @classproperty
    def allow_user_facing_goals(cls):
        return False

    @classmethod
    def _states(cls):
        return (SituationStateData(1, _WaitForNeighborToSpawnState), SituationStateData(2, _AnswerDoorState, factory=cls.answer_door_state))

    @classmethod
    def default_job(cls):
        return cls.neighbor_job_and_role_state.job

    def _on_set_sim_job(self, sim, job_type):
        super()._on_set_sim_job(sim, job_type)
        if job_type is self.neighbor_job_and_role_state.job:
            self._neighbor_sim = sim
        elif job_type is self.knocker_job_and_role_state.job:
            self._knocker_sim = sim
        if self._neighbor_sim is not None and self._knocker_sim is not None:
            self._change_state(self.answer_door_state())

    @classmethod
    def _get_tuned_job_and_default_role_state_tuples(cls):
        return [(cls.neighbor_job_and_role_state.job, cls.neighbor_job_and_role_state.role_state), (cls.knocker_job_and_role_state.job, cls.knocker_job_and_role_state.role_state)]

    def start_situation(self):
        super().start_situation()
        self._change_state(_WaitForNeighborToSpawnState())

    def _on_remove_sim_from_situation(self, sim):
        super()._on_remove_sim_from_situation(sim)
        self._self_destruct()
lock_instance_tunables(NeighborChatSituation, exclusivity=BouncerExclusivityCategory.NORMAL, creation_ui_option=SituationCreationUIOption.NOT_AVAILABLE, _implies_greeted_status=False)