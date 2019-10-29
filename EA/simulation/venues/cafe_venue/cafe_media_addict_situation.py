import randomfrom objects.system import create_objectfrom sims4.tuning.instances import lock_instance_tunablesfrom sims4.tuning.tunable import TunableList, TunableReferencefrom situations.bouncer.bouncer_types import BouncerExclusivityCategoryfrom situations.situation import Situationfrom situations.situation_complex import CommonSituationState, SituationComplexCommon, SituationStateData, TunableSituationJobAndRoleStatefrom situations.situation_types import SituationCreationUIOptionfrom venues.cafe_venue.cafe_situations_common import _OrderCoffeeState, _PreOrderCoffeeStateimport servicesMEDIA_OBJECT_TOKEN = 'media_object_id'
class _MediaAddictState(CommonSituationState):

    def _get_role_state_overrides(self, sim, job_type, role_state_type, role_affordance_target):
        if self.owner._media_object_id is not None:
            target = services.current_zone().inventory_manager.get(self.owner._media_object_id)
        else:
            object_to_create = random.choice(self.owner.media_objects_to_create)
            target = self.owner._create_object_for_situation(sim, object_to_create)
            self.owner._media_object_id = target.id
        return (role_state_type, target)

class CafeMediaAddictSituation(SituationComplexCommon):
    INSTANCE_TUNABLES = {'pre_order_coffee_state': _PreOrderCoffeeState.TunableFactory(description='\n            The situation state used for when a Sim is arriving as a Cafe\n            Media Addict Sim.\n            ', tuning_group=SituationComplexCommon.SITUATION_STATE_GROUP, display_name='01_pre_order_coffee_situation_state'), 'order_coffee_state': _OrderCoffeeState.TunableFactory(description='\n            The situation state used for when a Sim is ordering coffee as a Media\n            Addict.\n            ', tuning_group=SituationComplexCommon.SITUATION_STATE_GROUP, display_name='02_order_coffee_situation_state'), 'media_addict_state': _MediaAddictState.TunableFactory(description='\n            The main state of the situation. This is where Sims will do \n            behavior after ordering coffee.\n            ', tuning_group=SituationComplexCommon.SITUATION_STATE_GROUP, display_name='03_media_addict_state'), 'cafe_media_addict_job': TunableSituationJobAndRoleState(description="\n            The default job and role state for a Sim in this situation. This\n            shouldn't actually matter because the Situation will put the Sim in\n            the Order Coffee State when they are added.\n            "), 'media_objects_to_create': TunableList(description='\n            A list of objects to randomly pick from for this type of Reader.\n            When the reader enters the state to read after they get their\n            coffee, we randomly create one of these objects and pass it to the\n            role affordances as the target.\n            ', tunable=TunableReference(description='\n                An object to create.', manager=services.definition_manager()))}
    REMOVE_INSTANCE_TUNABLES = Situation.NON_USER_FACING_REMOVE_INSTANCE_TUNABLES

    def __init__(self, *arg, **kwargs):
        super().__init__(*arg, **kwargs)
        reader = self._seed.custom_init_params_reader
        self._media_object_id = self._load_object(reader, MEDIA_OBJECT_TOKEN, claim=True)
        self._media_addict = None

    @classmethod
    def _states(cls):
        return (SituationStateData(1, _PreOrderCoffeeState, factory=cls.pre_order_coffee_state), SituationStateData(2, _OrderCoffeeState, factory=cls.order_coffee_state), SituationStateData(3, _MediaAddictState, factory=cls.media_addict_state))

    @classmethod
    def _get_tuned_job_and_default_role_state_tuples(cls):
        return [(cls.cafe_media_addict_job.job, cls.cafe_media_addict_job.role_state)]

    def get_order_coffee_state(self):
        return self.order_coffee_state()

    def get_post_coffee_state(self):
        return self.media_addict_state()

    def _on_set_sim_job(self, sim, job_type):
        super()._on_set_sim_job(sim, job_type)
        self._media_addict = sim

    @classmethod
    def default_job(cls):
        return cls.cafe_media_addict_job

    def start_situation(self):
        super().start_situation()
        self._change_state(self.order_coffee_state())

    def sim_of_interest(self, sim_info):
        if self._media_addict is not None and self._media_addict.sim_info is sim_info:
            return True
        return False

    def _save_custom_situation(self, writer):
        super()._save_custom_situation(writer)
        if self._media_object_id is not None:
            writer.write_uint64(MEDIA_OBJECT_TOKEN, self._media_object_id)
lock_instance_tunables(CafeMediaAddictSituation, exclusivity=BouncerExclusivityCategory.NORMAL, creation_ui_option=SituationCreationUIOption.NOT_AVAILABLE, _implies_greeted_status=False)