from protocolbuffers import SimObjectAttributes_pb2 as protocolsfrom sickness.sickness_tuning import SicknessTuningfrom sims.sim_info_lod import SimInfoLODLevelfrom sims.sim_info_tracker import SimInfoTrackerimport servicesimport sims4.resources
class SicknessTracker(SimInfoTracker):

    def __init__(self, sim_info):
        self._sim_info = sim_info
        self._current_sickness = None
        self._previous_sicknesses = []
        self._discovered_symptoms = []
        self._exams_performed = set()
        self._treatments_performed = set()
        self._treatments_ruled_out = set()
        self._last_progress = 0
        self._discovered_sickness = False

    @property
    def current_sickness(self):
        return self._current_sickness

    @property
    def previous_sicknesses(self):
        return frozenset(self._previous_sicknesses)

    @property
    def last_progress(self):
        return self._last_progress

    @property
    def discovered_symptoms(self):
        return tuple(self._discovered_symptoms)

    @property
    def exams_performed(self):
        return frozenset(self._exams_performed)

    @property
    def treatments_performed(self):
        return frozenset(self._treatments_performed)

    @property
    def ruled_out_treatments(self):
        return frozenset(self._treatments_ruled_out)

    @property
    def has_discovered_sickness(self):
        return self._discovered_sickness

    def discover_sickness(self):
        self._discovered_sickness = True

    def add_sickness(self, sickness):
        self._current_sickness = sickness

    def remove_sickness(self):
        if self.current_sickness is not None:
            if self.current_sickness.track_in_history:
                self._previous_sicknesses.insert(0, self.current_sickness)
                max_sicknesses = SicknessTuning.PREVIOUS_SICKNESSES_TO_TRACK
                if len(self._previous_sicknesses) > max_sicknesses:
                    del self._previous_sicknesses[max_sicknesses:]
            self.clear_diagnosis_data()
            self._current_sickness = None

    def record_last_progress(self, progress):
        self._last_progress = progress

    def discover_symptom(self, symptom):
        if symptom not in self._discovered_symptoms:
            self._discovered_symptoms.append(symptom)

    def track_examination(self, affordance):
        self._exams_performed.add(affordance)

    def track_treatment(self, affordance):
        self._treatments_performed.add(affordance)

    def rule_out_treatment(self, affordance):
        self._treatments_ruled_out.add(affordance)

    def clear_diagnosis_data(self):
        self._discovered_symptoms.clear()
        self._exams_performed.clear()
        self._treatments_performed.clear()
        self._treatments_ruled_out.clear()
        self._last_progress = 0
        self._discovered_sickness = False

    def sickness_tracker_save_data(self):
        data = protocols.PersistableSicknessTracker()
        self._save_sickness_data(data.current_sickness)
        data.previous_sicknesses.extend([sickness.guid64 for sickness in self.previous_sicknesses])
        return data

    def _save_sickness_data(self, sickness_data):
        if self._current_sickness is None:
            return
        sickness_data.sickness = self._current_sickness.guid64
        sickness_data.symptoms_discovered.extend(symptom.guid64 for symptom in self._discovered_symptoms)
        sickness_data.exams_performed.extend(exam.guid64 for exam in self._exams_performed)
        sickness_data.treatments_performed.extend(treatment.guid64 for treatment in self._treatments_performed)
        sickness_data.treatments_ruled_out.extend(treatment.guid64 for treatment in self._treatments_ruled_out)
        sickness_data.is_discovered = self._discovered_sickness

    def should_persist_data(self):
        return self._current_sickness or self.previous_sicknesses

    def load_sickness_tracker_data(self, data):
        self.clear_diagnosis_data()
        self._previous_sicknesses.clear()
        sickness_manager = services.get_instance_manager(sims4.resources.Types.SICKNESS)
        interaction_manager = services.get_instance_manager(sims4.resources.Types.INTERACTION)
        previous_sicknesses = [sickness_manager.get(sickness_guid) for sickness_guid in data.previous_sicknesses]
        self._previous_sicknesses.extend(sickness for sickness in previous_sicknesses if sickness is not None)
        if data.HasField('current_sickness'):
            current_sickness_data = data.current_sickness
            self._current_sickness = sickness_manager.get(current_sickness_data.sickness)
            if self._current_sickness is None:
                return
            self._discovered_sickness = current_sickness_data.is_discovered
            symptoms_discovered = [sickness_manager.get(symptom_guid) for symptom_guid in current_sickness_data.symptoms_discovered]
            self._discovered_symptoms.extend(symptom for symptom in symptoms_discovered if symptom is not None)
            exams_performed = [interaction_manager.get(interaction_guid) for interaction_guid in current_sickness_data.exams_performed]
            self._exams_performed.update(exam for exam in exams_performed if exam is not None)
            treatments_performed = [interaction_manager.get(interaction_guid) for interaction_guid in current_sickness_data.treatments_performed]
            self._treatments_performed.update(treatment for treatment in treatments_performed if treatment is not None)
            treatments_ruled_out = [interaction_manager.get(interaction_guid) for interaction_guid in current_sickness_data.treatments_ruled_out]
            self._treatments_ruled_out.update(treatment for treatment in treatments_ruled_out if treatment is not None)

    def on_lod_update(self, old_lod, new_lod):
        if new_lod == SimInfoLODLevel.MINIMUM:
            self.clean_up()

    def clean_up(self):
        self._sim_info = None
        self._current_sickness = None
        self.clear_diagnosis_data()
        self._previous_sicknesses.clear()
