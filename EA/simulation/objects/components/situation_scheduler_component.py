from protocolbuffers import SimObjectAttributes_pb2 as protocolsfrom objects.components import Component, componentmethodfrom objects.components.types import SITUATION_SCHEDULER_COMPONENTfrom situations.situation_guest_list import SituationGuestListimport servicesimport sims4.loglogger = sims4.log.Logger('SituationSchedulerComponent', default_owner='mkartika')
class SituationSchedulerComponent(Component, allow_dynamic=True, component_name=SITUATION_SCHEDULER_COMPONENT, persistence_key=protocols.PersistenceMaster.PersistableData.SituationSchedulerComponent):

    def __init__(self, *args, scheduler=None, **kwargs):
        super().__init__(*args, **kwargs)
        self._situation_scheduler = scheduler
        self._generated_situation_ids = set()

    @componentmethod
    def set_situation_scheduler(self, scheduler):
        self._destroy_situation_scheduler()
        self._situation_scheduler = scheduler

    @componentmethod
    def create_situation(self, situation_type):
        if not situation_type.situation_meets_starting_requirements():
            return
        situation_manager = services.get_zone_situation_manager()
        self._cleanup_generated_situations(situation_manager)
        running_situation = self._get_same_situation_running(situation_manager, situation_type)
        if running_situation is not None:
            situation_manager.destroy_situation_by_id(running_situation.id)
        guest_list = SituationGuestList(invite_only=True)
        situation_id = situation_manager.create_situation(situation_type, guest_list=guest_list, user_facing=False, scoring_enabled=False, spawn_sims_during_zone_spin_up=True, creation_source=str(self), default_target_id=self.owner.id)
        if situation_id is None:
            return
        self._generated_situation_ids.add(situation_id)

    def on_remove(self, *_, **__):
        self._destroy_situation_scheduler()
        self._destroy_generated_situations()

    def _cleanup_generated_situations(self, situation_manager):
        for situation_id in list(self._generated_situation_ids):
            running_situation = situation_manager.get(situation_id)
            if running_situation is None:
                self._generated_situation_ids.remove(situation_id)

    def _get_same_situation_running(self, situation_manager, situation_type):
        for situation_id in self._generated_situation_ids:
            running_situation = situation_manager.get(situation_id)
            if situation_type is type(running_situation):
                return running_situation

    def _destroy_situation_scheduler(self):
        if self._situation_scheduler is not None:
            self._situation_scheduler.destroy()
            self._situation_scheduler = None

    def _destroy_generated_situations(self):
        situation_manager = services.get_zone_situation_manager()
        for situation_id in self._generated_situation_ids:
            situation_manager.destroy_situation_by_id(situation_id)
        self._generated_situation_ids.clear()

    def save(self, persistence_master_message):
        persistable_data = protocols.PersistenceMaster.PersistableData()
        persistable_data.type = protocols.PersistenceMaster.PersistableData.SituationSchedulerComponent
        component_data = persistable_data.Extensions[protocols.PersistableSituationSchedulerComponent.persistable_data]
        if self._generated_situation_ids:
            component_data.situation_ids.extend(self._generated_situation_ids)
        persistence_master_message.data.extend([persistable_data])

    def load(self, persistable_data):
        component_data = persistable_data.Extensions[protocols.PersistableSituationSchedulerComponent.persistable_data]
        for situation_id in component_data.situation_ids:
            self._generated_situation_ids.add(situation_id)
