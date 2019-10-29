import randomfrom objects.system import create_objectfrom sims4.tuning.instances import lock_instance_tunablesfrom sims4.tuning.tunable import TunableList, TunableReferencefrom situations.bouncer.bouncer_types import BouncerExclusivityCategoryfrom situations.situation import Situationfrom situations.situation_complex import CommonSituationState, SituationComplexCommon, SituationStateData, TunableSituationJobAndRoleStatefrom situations.situation_types import SituationCreationUIOptionfrom venues.cafe_venue.cafe_situations_common import _OrderCoffeeState, _PreOrderCoffeeStateimport servicesBOOK_TOKEN = 'book_id'
class _ReaderState(CommonSituationState):

    def _get_role_state_overrides(self, sim, job_type, role_state_type, role_affordance_target):
        if self.owner._book_id is not None:
            target = services.current_zone().inventory_manager.get(self.owner._book_id)
        else:
            book_to_create = random.choice(self.owner.reader_objects_to_create)
            target = self.owner._create_object_for_situation(sim, book_to_create)
            self.owner._book_id = target.id
        return (role_state_type, target)

class CafeReaderSituation(SituationComplexCommon):
    INSTANCE_TUNABLES = {'pre_order_coffee_state': _PreOrderCoffeeState.TunableFactory(description='\n            The situation state used for when a Sim is arriving as a Cafe\n            Reader Sim.\n            ', tuning_group=SituationComplexCommon.SITUATION_STATE_GROUP, display_name='01_pre_order_coffee_situation_state'), 'order_coffee_state': _OrderCoffeeState.TunableFactory(description='\n            The situation state used for when a Sim is ordering coffee as a Cafe\n            Reader Sim.\n            ', tuning_group=SituationComplexCommon.SITUATION_STATE_GROUP, display_name='02_order_coffee_situation_state'), 'reader_state': _ReaderState.TunableFactory(description='\n            The main state of the situation. This is where Sims will do \n            behavior after ordering coffee\n            ', tuning_group=SituationComplexCommon.SITUATION_STATE_GROUP, display_name='03_reader_state'), 'cafe_reader_job': TunableSituationJobAndRoleState(description="\n            The default job for a Sim in this situation. This shouldn't\n            actually matter because the Situation will put the Sim in the Order\n            Coffee State when they are added.\n            "), 'reader_objects_to_create': TunableList(description='\n            A list of objects to randomly pick from for this type of Reader.\n            When the reader enters the state to read after they get their\n            coffee, we randomly create one of these objects and pass it to the\n            role affordances as the target.\n            ', tunable=TunableReference(description='\n                An object to create.', manager=services.definition_manager()))}
    REMOVE_INSTANCE_TUNABLES = Situation.NON_USER_FACING_REMOVE_INSTANCE_TUNABLES

    def __init__(self, *arg, **kwargs):
        super().__init__(*arg, **kwargs)
        reader = self._seed.custom_init_params_reader
        self._book_id = self._load_object(reader, BOOK_TOKEN, claim=True)
        self._reader_sim = None

    @classmethod
    def _states(cls):
        return (SituationStateData(1, _PreOrderCoffeeState, factory=cls.pre_order_coffee_state), SituationStateData(2, _OrderCoffeeState, factory=cls.order_coffee_state), SituationStateData(3, _ReaderState, factory=cls.reader_state))

    @classmethod
    def _get_tuned_job_and_default_role_state_tuples(cls):
        return [(cls.cafe_reader_job.job, cls.cafe_reader_job.role_state)]

    def _on_set_sim_job(self, sim, job_type):
        super()._on_set_sim_job(sim, job_type)
        self._reader_sim = sim

    def get_order_coffee_state(self):
        return self.order_coffee_state()

    def get_post_coffee_state(self):
        return self.reader_state()

    @classmethod
    def default_job(cls):
        return cls.cafe_reader_job

    def start_situation(self):
        super().start_situation()
        self._change_state(self.pre_order_coffee_state())

    def sim_of_interest(self, sim_info):
        if self._reader_sim is not None and self._reader_sim.sim_info is sim_info:
            return True
        return False

    def _save_custom_situation(self, writer):
        super()._save_custom_situation(writer)
        if self._book_id is not None:
            writer.write_uint64(BOOK_TOKEN, self._book_id)
lock_instance_tunables(CafeReaderSituation, exclusivity=BouncerExclusivityCategory.NORMAL, creation_ui_option=SituationCreationUIOption.NOT_AVAILABLE, _implies_greeted_status=False)