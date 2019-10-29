from protocolbuffers import SimObjectAttributes_pb2from relics.relic_tuning import RelicTuningfrom sims.sim_info_lod import SimInfoLODLevelfrom sims.sim_info_tracker import SimInfoTrackerfrom sims4.utils import classpropertyimport servicesimport sims4.loglogger = sims4.log.Logger('RelicTracker', default_owner='trevor')
class RelicTracker(SimInfoTracker):

    def __init__(self, sim_info):
        self._sim_info = sim_info
        self._known_relic_combos = None

    def add_relic_combo(self, combo_id):
        if self._known_relic_combos is None:
            self._known_relic_combos = set()
        self._known_relic_combos.add(combo_id)

    def _knows_relic_combo(self, combo_id):
        if self._known_relic_combos is not None:
            return combo_id in self._known_relic_combos
        return False

    def get_description_for_objects(self, object_a, object_b):
        (combo_id, combo_data) = RelicTuning.get_relic_combo_id_data_tuple_for_objects(object_a, object_b)
        return self._resolve_combo_id_to_description_text(combo_id, combo_data)

    def get_tooltip_for_object(self, obj):
        (combo_id, combo_data) = RelicTuning.get_relic_combo_id_data_tuple_for_hovertip(obj)
        if combo_data is None:
            return
        return self._resolve_combo_id_to_description_text(combo_id, combo_data)

    def _resolve_combo_id_to_description_text(self, combo_id, combo_data):
        if combo_data is None:
            logger.error("Trying to get a description for two relic objects, {} and {}, but that combo doesn't exist in the tuning.", object_a, object_b)
            return RelicTuning.DEFAULT_UNDISCOVERED_TEXT
        if self._knows_relic_combo(combo_id):
            return combo_data.discovered_picker_description_text
        unknown_value = combo_data.undiscovered_picker_description_text
        if unknown_value is not None:
            unknown_data = RelicTuning.get_relic_combo_data_for_combo_id(unknown_value)
            if unknown_data is not None and self._knows_relic_combo(unknown_value):
                return unknown_data.discovered_picker_description_text
        return RelicTuning.DEFAULT_UNDISCOVERED_TEXT

    def save(self):
        data = SimObjectAttributes_pb2.PersistableRelicTracker()
        if self._known_relic_combos:
            data.known_relics.extend(self._known_relic_combos)
        return data

    def load(self, data):
        if data.known_relics:
            self._known_relic_combos = set()
            self._known_relic_combos.update(data.known_relics)

    @classproperty
    def _tracker_lod_threshold(cls):
        return SimInfoLODLevel.FULL

    def on_lod_update(self, old_lod, new_lod):
        if new_lod < self._tracker_lod_threshold:
            self._known_relic_combos = None
        elif old_lod < self._tracker_lod_threshold:
            sim_msg = services.get_persistence_service().get_sim_proto_buff(self._sim_info.id)
            if sim_msg is not None:
                self.load(sim_msg.attributes.relic_tracker)
