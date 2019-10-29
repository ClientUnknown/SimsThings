import randomfrom sims4.tuning.instances import lock_instance_tunablesfrom sims4.tuning.tunable import TunableList, TunableReferencefrom situations.bouncer.bouncer_types import BouncerExclusivityCategoryfrom situations.situation import Situationfrom situations.situation_complex import SituationComplexCommon, TunableSituationJobAndRoleState, CommonSituationState, SituationStateDatafrom situations.situation_types import SituationCreationUIOptionimport servicesINSTRUMENT_TOKEN = 'instrument_id'
class BuskSituationState(CommonSituationState):
    pass

class BuskerSituationMixin:
    INSTANCE_TUNABLES = {'busk_state': BuskSituationState.TunableFactory(description='\n            Situation State for the Sim to busk at the performance space.\n            '), 'busker_job_and_role_state': TunableSituationJobAndRoleState(description='\n            Job and Role State for the busker.\n            '), 'instrument_objects_to_create': TunableList(description='\n            A list of objects to randomly pick from for this type of busker.\n            When the busker joins the situation, we randomly create one of\n            these and use it for the duration of the situation.\n            ', tunable=TunableReference(description='\n                An object to create.', manager=services.definition_manager()))}

    def __init__(self, *arg, **kwargs):
        super().__init__(*arg, **kwargs)
        reader = self._seed.custom_init_params_reader
        self._instrument_id = self._load_object(reader, INSTRUMENT_TOKEN, claim=True)

    @classmethod
    def default_job(cls):
        pass

    @classmethod
    def _states(cls):
        return (SituationStateData(1, BuskSituationState, factory=cls.busk_state),)

    @classmethod
    def _get_tuned_job_and_default_role_state_tuples(cls):
        return [(cls.busker_job_and_role_state.job, cls.busker_job_and_role_state.role_state)]

    def _on_set_sim_job(self, sim, job_type):
        super()._on_set_sim_job(sim, job_type)
        if self._instrument_id is None:
            object_to_create = random.choice(self.instrument_objects_to_create)
            target = self._create_object_for_situation(sim, object_to_create)
            if target is not None:
                self._instrument_id = target.id

    def _on_remove_sim_from_situation(self, sim):
        super()._on_remove_sim_from_situation(sim)
        if self._instrument_id is None:
            return
        obj = services.object_manager().get(self._instrument_id)
        if obj is None:
            return
        obj.make_transient()

    def start_situation(self):
        super().start_situation()
        self._change_state(self.busk_state())

    def _save_custom_situation(self, writer):
        super()._save_custom_situation(writer)
        if self._instrument_id is not None:
            writer.write_uint64(INSTRUMENT_TOKEN, self._instrument_id)

class PerformanceSpaceBuskerSituation(BuskerSituationMixin, SituationComplexCommon):
    REMOVE_INSTANCE_TUNABLES = Situation.NON_USER_FACING_REMOVE_INSTANCE_TUNABLES
lock_instance_tunables(PerformanceSpaceBuskerSituation, exclusivity=BouncerExclusivityCategory.WALKBY, creation_ui_option=SituationCreationUIOption.NOT_AVAILABLE, _implies_greeted_status=False)