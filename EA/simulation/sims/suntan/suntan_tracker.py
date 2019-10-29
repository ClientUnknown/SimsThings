import randomfrom protocolbuffers import SimObjectAttributes_pb2from cas.cas import get_caspart_bodytypefrom distributor.rollback import ProtocolBufferRollbackfrom sims.sim_info_tracker import SimInfoTrackerfrom sims.suntan.suntan_tuning import TanLevelfrom sims4.tuning.tunable import TunablePackSafeReference, TunableMapping, TunableReference, TunableList, TunableCasPart, TunableEnumEntryimport servicesimport sims4.resources
class SuntanTracker(SimInfoTracker):
    TAN_PRANK_BUFF = TunablePackSafeReference(description='\n        A Sim that has this buff will generate new tan lines based on their\n        current outfit when changing tan level.\n        ', manager=services.get_instance_manager(sims4.resources.Types.BUFF))
    TAN_PRANK_CAS_PARTS = TunableList(description='\n        A list of CAS parts from which a random entry is selected if a Sim has\n        been pranked to generate tan lines.\n        ', tunable=TunableCasPart(description='\n            CAS part to use to generate tan lines for a Sim that has been\n            pranked.\n            ', pack_safe=True))
    UPDATE_TAN_LINES_BUFF = TunablePackSafeReference(description='\n        A Sim that has this buff will generate new tan lines based on their\n        current outfit when changing tan level.\n        ', manager=services.get_instance_manager(sims4.resources.Types.BUFF))
    TAN_LEVEL_TO_STATE_MAP = TunableMapping(description='\n        Map of tan level to object state that corresponds to that tan level.\n        Used on save/load to set the state of the Sim object to persist the\n        tan state correctly.\n        ', key_type=TunableEnumEntry(description='\n            Tan level that needs to be persisted.\n            ', tunable_type=TanLevel, default=TanLevel.NO_TAN, pack_safe=True), value_type=TunableReference(description='\n            The object state value that represents the persisted tan level\n            that needs to be set on load.\n            ', manager=services.get_instance_manager(sims4.resources.Types.OBJECT_STATE), class_restrictions=('ObjectStateValue',), pack_safe=True))
    TAN_LEVEL_OBJECT_STATE = TunablePackSafeReference(description='\n        The object state that represents a Sims tan level.\n        ', manager=services.get_instance_manager(sims4.resources.Types.OBJECT_STATE), class_restrictions=('ObjectState',))

    def __init__(self, sim_info):
        self._sim_info = sim_info
        self._tan_level = TanLevel.NO_TAN
        self._outfit_part_data_list = None
        self._force_update = False
        self._suntan_force_updated = False

    @property
    def tan_level(self):
        return self._tan_level

    @property
    def outfit_part_data_list(self):
        return self._outfit_part_data_list

    @property
    def force_update(self):
        return self._force_update

    def set_tan_level(self, tan_level=None, force_update=False):
        if not self._sim_info.is_simulating:
            return
        tan_level_changed = False
        if tan_level is not None:
            tan_level_changed = self._tan_level is not tan_level
            self._tan_level = tan_level
        if self._tan_level == TanLevel.NO_TAN:
            self._outfit_part_data_list = None
        if self._sim_info.has_buff(self.UPDATE_TAN_LINES_BUFF):
            if self.TAN_PRANK_BUFF is not None and self._sim_info.has_buff(self.TAN_PRANK_BUFF) and self.TAN_PRANK_CAS_PARTS:
                part_id = random.choice(self.TAN_PRANK_CAS_PARTS)
                body_type = get_caspart_bodytype(part_id)
                self._outfit_part_data_list = ((part_id, body_type),)
            else:
                current_outfit = self._sim_info.get_current_outfit()
                current_outfit_data = self._sim_info.get_outfit(*current_outfit)
                self._outfit_part_data_list = tuple(zip(current_outfit_data.part_ids, current_outfit_data.body_types))
        self._force_update = False
        if self.UPDATE_TAN_LINES_BUFF is not None and tan_level_changed:
            self._suntan_force_updated = False
        elif force_update:
            if self._suntan_force_updated:
                return
            self._suntan_force_updated = True
            self._force_update = True
        self._sim_info.resend_suntan_data()

    def on_start_up(self, sim_inst):
        if self.TAN_LEVEL_OBJECT_STATE is None:
            return
        state_to_set = self.TAN_LEVEL_TO_STATE_MAP.get(self._tan_level, None)
        if state_to_set is not None:
            sim_inst.set_state(self.TAN_LEVEL_OBJECT_STATE, state_to_set)

    def save(self):
        data = SimObjectAttributes_pb2.PersistableSuntanTracker()
        data.tan_level = self._tan_level
        if self._outfit_part_data_list is not None:
            for (part_id, body_type) in self._outfit_part_data_list:
                with ProtocolBufferRollback(data.outfit_part_data_list) as entry:
                    entry.id = part_id
                    entry.body_type = body_type
        return data

    def load(self, data):
        self._tan_level = data.tan_level
        if data.outfit_part_data_list:
            if self._outfit_part_data_list is None:
                self._outfit_part_data_list = []
            else:
                self._outfit_part_data_list.clear()
            for part_data in data.outfit_part_data_list:
                self._outfit_part_data_list.append((part_data.id, part_data.body_type))
