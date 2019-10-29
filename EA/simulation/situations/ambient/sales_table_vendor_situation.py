from sims4.tuning.instances import lock_instance_tunablesfrom sims4.tuning.tunable import TunableList, TunableInterval, TunableEnumEntryfrom situations.bouncer.bouncer_types import BouncerExclusivityCategoryfrom situations.situation import Situationfrom situations.situation_complex import SituationComplexCommon, TunableSituationJobAndRoleState, CommonSituationState, SituationStateData, CommonInteractionCompletedSituationStatefrom situations.situation_types import SituationCreationUIOptionfrom tag import Tagimport servicesimport sims4.loglogger = sims4.log.Logger('SalesTableVendorSituation', default_owner='rmccord')SALE_ITEM_LIST_TOKEN = 'sale_item_list'SITUATION_ALARM = 'gather_objects_alarm'ALARM_TIME_IN_SIM_MINUTES = 10
class SalesTableSetupState(CommonInteractionCompletedSituationState):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def create_setup_alarm(self, reader=None):
        self._create_or_load_alarm(SITUATION_ALARM, ALARM_TIME_IN_SIM_MINUTES, lambda _: self._gather_objects_alarm_callback(), should_persist=False, reader=reader)

    def on_activate(self, reader=None):
        super().on_activate(reader)
        self.create_setup_alarm(reader=reader)

    def _on_interaction_of_interest_complete(self, **kwargs):
        self.owner._change_state(self.owner.tend_state())

    def _gather_objects_alarm_callback(self):
        self.owner.find_created_objects()
        self.create_setup_alarm()

class TendSalesTableState(CommonSituationState):

    def on_activate(self, reader=None):
        super().on_activate(reader)
        self.owner.find_created_objects()

    def timer_expired(self):
        super().timer_expired()
        self.owner._change_state(self.owner.teardown_state())

class SalesTableTeardownState(CommonInteractionCompletedSituationState):

    def _on_interaction_of_interest_complete(self, **kwargs):
        self.owner._self_destruct()

    def timer_expired(self):
        self.owner._self_destruct()

class SalesTableVendorSituationMixin:
    INSTANCE_TUNABLES = {'setup_state': SalesTableSetupState.TunableFactory(tuning_group=SituationComplexCommon.SITUATION_STATE_GROUP, display_name='01_setup_state'), 'tend_state': TendSalesTableState.TunableFactory(tuning_group=SituationComplexCommon.SITUATION_STATE_GROUP, display_name='02_tend_state'), 'teardown_state': SalesTableTeardownState.TunableFactory(tuning_group=SituationComplexCommon.SITUATION_STATE_GROUP, display_name='03_teardown_state'), 'vendor_job_and_role_state': TunableSituationJobAndRoleState(description='\n            Job and Role State for the vendor.\n            '), 'sale_object_tags': TunableList(description='\n            A list of tags that tell us the object comes from the vendor. We\n            use these tags to find objects and destroy them when the situation\n            ends or the sim is removed.\n            ', tunable=TunableEnumEntry(description='\n                A tag that denotes the object comes from the craft sales vendor\n                and can be destroyed if the situation ends or the sim leaves.\n                ', tunable_type=Tag, default=Tag.INVALID)), 'number_of_sale_objects': TunableInterval(description='\n            ', tunable_type=int, default_lower=7, default_upper=10, minimum=1, maximum=15)}

    def __init__(self, *arg, **kwargs):
        super().__init__(*arg, **kwargs)
        reader = self._seed.custom_init_params_reader
        if reader is None:
            self.sale_item_list = set()
        else:
            self.sale_item_list = set(reader.read_uint64s(SALE_ITEM_LIST_TOKEN, set()))
        self.situation_sim = None

    @classmethod
    def default_job(cls):
        pass

    @classmethod
    def _states(cls):
        return (SituationStateData(1, SalesTableSetupState, factory=cls.setup_state), SituationStateData(2, TendSalesTableState, factory=cls.tend_state), SituationStateData(3, SalesTableTeardownState, factory=cls.teardown_state))

    @classmethod
    def _get_tuned_job_and_default_role_state_tuples(cls):
        return [(cls.vendor_job_and_role_state.job, cls.vendor_job_and_role_state.role_state)]

    def destroy_created_objects(self):
        if not services.current_zone().is_zone_shutting_down:
            for obj_id in self.sale_item_list:
                obj = services.object_manager().get(obj_id)
                if obj is None:
                    obj = services.inventory_manager().get(obj_id)
                if obj is None:
                    pass
                else:
                    household_owner_id = obj.get_household_owner_id()
                    if self.situation_sim is not None and household_owner_id == self.situation_sim.household_id:
                        obj.destroy(source=self, cause='SalesTableVendorSituation has ended.')
        self.sale_item_list = None

    def find_created_objects(self):
        if self.situation_sim is None:
            return
        objects_with_tag = []
        object_manager = services.object_manager()
        for obj in object_manager.get_objects_with_tags_gen(self.sale_object_tags):
            objects_with_tag.append(obj)
        inventory_manager = services.inventory_manager()
        for obj in inventory_manager.get_objects_with_tags_gen(self.sale_object_tags):
            objects_with_tag.append(obj)
        owned_objects_with_tag = {obj.id for obj in objects_with_tag if obj.get_household_owner_id == self.situation_sim.household_id}
        self.sale_item_list.update(owned_objects_with_tag)

    def _on_set_sim_job(self, sim, job_type):
        super()._on_set_sim_job(sim, job_type)
        self.situation_sim = sim

    def _on_remove_sim_from_situation(self, sim):
        super()._on_remove_sim_from_situation(sim)
        self.destroy_created_objects()

    def start_situation(self):
        super().start_situation()
        self._change_state(self.setup_state())

    def _save_custom_situation(self, writer):
        super()._save_custom_situation(writer)
        if self.sale_item_list:
            writer.write_uint64s(SALE_ITEM_LIST_TOKEN, self.sale_item_list)

class SalesTableVendorSituation(SalesTableVendorSituationMixin, SituationComplexCommon):
    REMOVE_INSTANCE_TUNABLES = Situation.NON_USER_FACING_REMOVE_INSTANCE_TUNABLES
lock_instance_tunables(SalesTableVendorSituation, exclusivity=BouncerExclusivityCategory.WALKBY, creation_ui_option=SituationCreationUIOption.NOT_AVAILABLE, _implies_greeted_status=False)