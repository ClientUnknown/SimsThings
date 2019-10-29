from collections import defaultdictimport itertoolsimport randomfrom protocolbuffers import SimObjectAttributes_pb2from careers.career_tuning import Careerfrom filters.tunable import DynamicSimFilterfrom sims4.collections import frozendictfrom sims4.tuning.tunable import TunableList, TunableReference, TunableRange, TunableMappingfrom sims4.tuning.tunable_base import GroupNamesfrom traits.traits import Traitimport servicesimport sims4.logimport telemetry_helperTELEMETRY_GROUP_DETECTIVE_CAREER = 'DETE'TELEMETRY_HOOK_DETECTIVE_CASE_START = 'DCAS'TELEMETRY_HOOK_DETECTIVE_CASE_END = 'DCAE'TELEMETRY_DETECTIVE_CRIMINAL_ID = 'crii'TELEMETRY_DETECTIVE_CRIME_DURATION = 'cdur'detective_telemetry_writer = sims4.telemetry.TelemetryWriter(TELEMETRY_GROUP_DETECTIVE_CAREER)logger = sims4.log.Logger('Detective', default_owner='bhill')
class DetectiveCareer(Career):
    INSTANCE_TUNABLES = {'crime_scene_events': TunableList(description='\n            The career events for each of the different types of crime scene.\n            ', tunable=TunableReference(manager=services.get_instance_manager(sims4.resources.Types.CAREER_EVENT)), tuning_group=GroupNames.CAREER), 'text_clues': TunableList(description="\n            A list of groups of mutually exclusive clues that the player can\n            discover in the course of solving a crime. Only one clue will be\n            chosen from each group. (e.g. if all hair-color clues are in one\n            group, only one hair-color clue will be chosen so there aren't\n            conflicting clues)\n            ", tunable=TunableList(description='\n                A group of mutually incompatible clues. Only one clue will be\n                chosen from this group.\n                ', tunable=TunableReference(description='\n                    The clue information and filter term.\n                    ', manager=services.get_instance_manager(sims4.resources.Types.DETECTIVE_CLUE))), tuning_group=GroupNames.CAREER), 'clue_incompatibility': TunableMapping(description='\n            Clues that are incompatible with each other.\n            ', key_name='clue', key_type=TunableReference(description='\n                The clue that is incompatible with other clues.\n                ', manager=services.get_instance_manager(sims4.resources.Types.DETECTIVE_CLUE)), value_name='incompatible_clues', value_type=TunableList(description='\n                The clues that are incompatible with the clue used as the\n                key here.\n                ', tunable=TunableReference(manager=services.get_instance_manager(sims4.resources.Types.DETECTIVE_CLUE))), tuning_group=GroupNames.CAREER), 'number_of_clues': TunableRange(description='\n            The number of clues per crime that the player will be given.\n            ', tunable_type=int, default=5, minimum=1, tuning_group=GroupNames.CAREER), 'number_of_decoys_per_undiscovered_clue': TunableRange(description='\n            The number of Sims to spawn as decoys for each clue that the\n            detective has not yet discovered.\n            ', tunable_type=int, default=2, minimum=1, tuning_group=GroupNames.CAREER), 'criminal_filter': DynamicSimFilter.TunableReference(description='\n            The filter to use when spawning a criminal. The filter terms are a\n            randomly generated set of clues.\n            ', tuning_group=GroupNames.CAREER), 'criminal_trait': Trait.TunableReference(description='\n            A trait that is awarded to the criminal. The trait is added when the\n            criminal is selected, and is removed when a new criminal is selected\n            or the career is quit by the Sim.\n            ', tuning_group=GroupNames.CAREER), 'decoy_filter': DynamicSimFilter.TunableReference(description='\n            The filter to use when spawning decoys. The filter terms are a\n            subset of the discovered clues.\n            ', tuning_group=GroupNames.CAREER)}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._used_clues = []
        self._unused_clues = []
        self._case_start_time_in_minutes = 0
        self.crime_scene_event_id = None
        self.active_criminal_sim_id = 0

    @classmethod
    def _tuning_loaded_callback(cls):
        super()._tuning_loaded_callback()
        incompatibility = defaultdict(list)
        for (clue, incompatible_clues) in cls.clue_incompatibility.items():
            for incompatible_clue in incompatible_clues:
                incompatibility[clue].append(incompatible_clue)
                incompatibility[incompatible_clue].append(clue)
        cls.clue_incompatibility = frozendict(incompatibility)

    @classmethod
    def _verify_tuning_callback(cls):
        super()._verify_tuning_callback()
        if len(cls.text_clues) < cls.number_of_clues:
            logger.error('Only {} sets of detective clues have been tuned, but at least {} are required.', len(cls.text_clues), cls.number_of_clues)

    def get_custom_gsi_data(self):
        custom_data = {}
        for (clue_index, clue) in enumerate(self._unused_clues):
            custom_data['Clue #{}'.format(clue_index)] = str(clue)
        for (clue_index, clue) in enumerate(self._used_clues):
            custom_data['Used Clue #{}'.format(clue_index)] = str(clue)
        if self.active_criminal_sim_id:
            criminal_sim_info = services.sim_info_manager().get(self.active_criminal_sim_id)
            if criminal_sim_info is not None:
                custom_data['Criminal'] = str(criminal_sim_info)
        return custom_data

    def quit_career(self, *args, **kwargs):
        self._clear_crime_data()
        return super().quit_career(*args, **kwargs)

    def _clear_crime_data(self):
        if self.active_criminal_sim_id:
            self.send_detective_telemetry(TELEMETRY_HOOK_DETECTIVE_CASE_END)
            criminal_sim_info = services.sim_info_manager().get(self.active_criminal_sim_id)
            if criminal_sim_info is not None:
                criminal_sim_info.remove_trait(self.criminal_trait)
        self._used_clues = []
        self._unused_clues = []

    def create_new_crime_data(self):
        self._clear_crime_data()
        incompatible_clues = set()
        clue_groups = list(self.text_clues)
        random.shuffle(clue_groups)
        for clue_group in clue_groups:
            clue_group = list(set(clue_group) - incompatible_clues)
            if not clue_group:
                pass
            else:
                clue = random.choice(clue_group)
                self._unused_clues.append(clue)
                incompatible_clues.update(self.clue_incompatibility.get(clue, ()))
        self._case_start_time_in_minutes = int(services.time_service().sim_now.absolute_minutes())
        self.crime_scene_event_id = None
        self.active_criminal_sim_id = self._create_criminal(tuple(clue.filter_term for clue in self._unused_clues))
        self.send_detective_telemetry(TELEMETRY_HOOK_DETECTIVE_CASE_START)

    def pop_unused_clue(self):
        if self._unused_clues:
            clue = random.choice(self._unused_clues)
            self._unused_clues.remove(clue)
            self._used_clues.append(clue)
            return clue

    def get_crime_scene_career_event(self):
        if not self.crime_scene_event_id:
            self.crime_scene_event_id = random.choice(self.crime_scene_events).guid64
        career_event_manager = services.get_instance_manager(sims4.resources.Types.CAREER_EVENT)
        return career_event_manager.get(self.crime_scene_event_id)

    def get_decoy_sim_ids_for_apb(self, persisted_sim_ids=None):
        decoys = []
        decoy_count = len(self._unused_clues)*self.number_of_decoys_per_undiscovered_clue
        if decoy_count == 0:
            return decoys
        blacklist_sim_ids = {self.sim_info.id}
        if self.active_criminal_sim_id:
            blacklist_sim_ids.add(self.active_criminal_sim_id)
        used_clue_filter_terms = tuple(clue.get_decoy_filter_term() for clue in self._used_clues)
        decoy_filter = self.decoy_filter(filter_terms=used_clue_filter_terms)
        sim_filter_service = services.sim_filter_service()
        filter_result = sim_filter_service.submit_matching_filter(number_of_sims_to_find=decoy_count, sim_filter=decoy_filter, sim_constraints=persisted_sim_ids, requesting_sim_info=self._sim_info, blacklist_sim_ids=blacklist_sim_ids, continue_if_constraints_fail=True, allow_yielding=False, gsi_source_fn=self.get_sim_filter_gsi_name)
        decoys.extend(f.sim_info.id for f in filter_result)
        return decoys

    def get_sim_filter_gsi_name(self):
        return str(self)

    def get_discovered_clues(self):
        return self._used_clues

    def _create_criminal(self, filter_terms):
        criminal_filter = self.criminal_filter(filter_terms=filter_terms)
        criminals = services.sim_filter_service().submit_matching_filter(sim_filter=criminal_filter, requesting_sim_info=self._sim_info, blacklist_sim_ids=set((self.active_criminal_sim_id,)), allow_yielding=False, gsi_source_fn=self.get_sim_filter_gsi_name)
        if criminals:
            criminal_sim_info = criminals[0].sim_info
            criminal_sim_info.add_trait(self.criminal_trait)
            return criminal_sim_info.sim_id
        logger.error('No criminal was spawned.', trigger_breakpoint=True)
        return 0

    def create_criminal_fixup(self):
        self.active_criminal_sim_id = self._create_criminal(tuple(clue.filter_term for clue in itertools.chain(self._used_clues, self._unused_clues)))
        return self.active_criminal_sim_id

    def get_persistable_sim_career_proto(self):
        proto = super().get_persistable_sim_career_proto()
        proto.detective_data = SimObjectAttributes_pb2.DetectiveCareerData()
        proto.detective_data.active_criminal_sim_id = self.active_criminal_sim_id if self.active_criminal_sim_id is not None else 0
        proto.detective_data.unused_clue_ids.extend(clue.guid64 for clue in self._unused_clues)
        proto.detective_data.used_clue_ids.extend(clue.guid64 for clue in self._used_clues)
        proto.detective_data.crime_scene_event_id = self.crime_scene_event_id if self.crime_scene_event_id is not None else 0
        proto.detective_data.case_start_time_in_minutes = self._case_start_time_in_minutes
        return proto

    def load_from_persistable_sim_career_proto(self, proto, skip_load=False):
        super().load_from_persistable_sim_career_proto(proto, skip_load=skip_load)
        self._unused_clues = []
        self._used_clues = []
        clue_manager = services.get_instance_manager(sims4.resources.Types.DETECTIVE_CLUE)
        for clue_id in proto.detective_data.unused_clue_ids:
            clue = clue_manager.get(clue_id)
            if clue is None:
                logger.info('Trying to load unavailable DETECTIVE_CLUE resource: {}', clue_id)
            else:
                self._unused_clues.append(clue)
        for clue_id in proto.detective_data.used_clue_ids:
            clue = clue_manager.get(clue_id)
            if clue is None:
                logger.info('Trying to load unavailable DETECTIVE_CLUE resource: {}', clue_id)
            else:
                self._used_clues.append(clue)
        self.active_criminal_sim_id = proto.detective_data.active_criminal_sim_id
        self.crime_scene_event_id = proto.detective_data.crime_scene_event_id
        self._case_start_time_in_minutes = proto.detective_data.case_start_time_in_minutes

    def send_detective_telemetry(self, hook_tag):
        with telemetry_helper.begin_hook(detective_telemetry_writer, hook_tag, sim_info=self.sim_info) as hook:
            hook.write_int(TELEMETRY_DETECTIVE_CRIMINAL_ID, self.active_criminal_sim_id)
            if hook_tag == TELEMETRY_HOOK_DETECTIVE_CASE_END and self._case_start_time_in_minutes != 0:
                now = int(services.time_service().sim_now.absolute_minutes())
                duration = now - self._case_start_time_in_minutes
                hook.write_int(TELEMETRY_DETECTIVE_CRIME_DURATION, duration)
