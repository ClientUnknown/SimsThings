from role.role_state import RoleStatefrom sims4.tuning.instances import lock_instance_tunablesfrom sims4.tuning.tunable import TunableInterval, TunableSimMinute, TunableTuplefrom situations.bouncer.bouncer_types import BouncerExclusivityCategoryfrom situations.situation import Situationfrom situations.situation_complex import SituationComplexCommon, CommonSituationState, SituationStateDatafrom situations.situation_job import SituationJobfrom situations.situation_types import SituationCreationUIOptionimport servicesCUSTOMER_SITUATIONS_TOKEN = 'customer_situation_ids'SITUATION_ALARM = 'situation_alarm'
class ManageCustomersState(CommonSituationState):
    FACTORY_TUNABLES = {'time_between_customer_checks': TunableSimMinute(description='\n            Time in Sim minutes between situation checks to see if we need to add\n            more Sims to be customers.\n            ', default=10)}

    def __init__(self, *args, time_between_customer_checks=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.time_between_customer_checks = time_between_customer_checks

    def on_activate(self, reader=None):
        super().on_activate(reader)
        self.number_of_situations = self.owner.number_of_expected_customers.random_int()
        self._create_or_load_alarm(SITUATION_ALARM, self.time_between_customer_checks, lambda _: self._check_customers(), repeating=True, should_persist=False, reader=reader)

    def _check_customers(self):
        customer_situations = self.owner.get_customer_situations()
        if len(customer_situations) < self.number_of_situations:
            num_to_create = self.number_of_situations - len(customer_situations)
            for _ in range(num_to_create):
                self.owner.create_customer_situation()

class YardSaleSituation(SituationComplexCommon):
    INSTANCE_TUNABLES = {'user_job': TunableTuple(description='\n            The job and role which the Sim is placed into.\n            ', situation_job=SituationJob.TunableReference(description='\n                A reference to a SituationJob that can be performed at this Situation.\n                '), role_state=RoleState.TunableReference(description='\n                A role state the sim assigned to the job will perform.\n                ')), 'manage_customers_state': ManageCustomersState.TunableFactory(tuning_group=SituationComplexCommon.SITUATION_STATE_GROUP), 'customer_situation': Situation.TunableReference(description='\n            Customer Situation to spawn that will pull customers to purchase\n            items from the craft sales table.\n            ', class_restrictions=('YardSaleCustomerSituation',)), 'number_of_expected_customers': TunableInterval(description='\n            The number of customers we expect to have at any given time the\n            yard sale is running. The yard sale will attempt to manage this\n            many customer situations at any given time.\n            ', tunable_type=int, default_lower=0, default_upper=10, minimum=0, maximum=10)}

    def __init__(self, *arg, **kwargs):
        super().__init__(*arg, **kwargs)
        self.scoring_enabled = False
        reader = self._seed.custom_init_params_reader
        if reader is None:
            self.customer_situations = []
        else:
            self.customer_situations = list(reader.read_uint32s(CUSTOMER_SITUATIONS_TOKEN, list()))

    @classmethod
    def default_job(cls):
        pass

    @classmethod
    def _get_tuned_job_and_default_role_state_tuples(cls):
        return [(cls.user_job.situation_job, cls.user_job.role_state)]

    @classmethod
    def _states(cls):
        return (SituationStateData(1, ManageCustomersState, factory=cls.manage_customers_state),)

    def start_situation(self):
        super().start_situation()
        self._change_state(self.manage_customers_state())

    def _self_destruct(self):
        situation_manager = services.get_zone_situation_manager()
        for situation_id in self.customer_situations:
            situation = situation_manager.get(situation_id)
            if situation is not None:
                situation._self_destruct()
        self.customer_situations.clear()
        super()._self_destruct()

    def get_customer_situations(self):
        customers = []
        situation_manager = services.get_zone_situation_manager()
        for situation_id in self.customer_situations:
            situation = situation_manager.get(situation_id)
            if situation is not None:
                customers.append(situation)
        self.customer_situations = [situation.id for situation in customers]
        return self.customer_situations

    def create_customer_situation(self):
        situation_manager = services.get_zone_situation_manager()
        situation_id = situation_manager.create_situation(self.customer_situation, guest_list=None, user_facing=False)
        self.customer_situations.append(situation_id)
lock_instance_tunables(YardSaleSituation, exclusivity=BouncerExclusivityCategory.VENUE_BACKGROUND, creation_ui_option=SituationCreationUIOption.NOT_AVAILABLE, _implies_greeted_status=False)