from sims4.service_manager import Servicefrom sims4.utils import classpropertyimport persistence_error_typesimport servicesimport sims4.loglogger = sims4.log.Logger('call_to_action', default_owner='nabaker')
class CallToActionService(Service):

    def __init__(self):
        self._permanently_disabled = set()
        self._active = dict()

    @classproperty
    def save_error_code(cls):
        return persistence_error_types.ErrorCodes.SERVICE_SAVE_FAILED_CALL_TO_ACTION_SERVICE

    def save(self, save_slot_data=None, **kwargs):
        cta_service_data = save_slot_data.gameplay_data.call_to_action_service
        cta_service_data.Clear()
        cta_service_data.permanently_disabled_ids.extend(self._permanently_disabled)

    def on_all_households_and_sim_infos_loaded(self, client):
        save_slot_data_msg = services.get_persistence_service().get_save_slot_proto_buff()
        cta_service_data = save_slot_data_msg.gameplay_data.call_to_action_service
        self._permanently_disabled = set(cta_service_data.permanently_disabled_ids)

    def on_zone_load(self):
        for call_to_action in self._active.values():
            call_to_action.turn_on(call_to_action.owner)

    def begin(self, factory, owner):
        guid = factory.guid64
        if guid not in self._permanently_disabled:
            call_to_action = factory()
            self._active[guid] = call_to_action
            call_to_action.turn_on(owner)

    def end(self, factory):
        call_to_action = self._active.pop(factory.guid64, None)
        if call_to_action is not None:
            call_to_action.turn_off()

    def abort(self, factory, permanent):
        guid = factory.guid64
        if guid in self._active:
            if permanent:
                self._permanently_disabled.add(guid)
            self.end(factory)

    def object_created(self, script_object):
        for call_to_action in self._active.values():
            call_to_action.turn_on_object_on_create(script_object)
