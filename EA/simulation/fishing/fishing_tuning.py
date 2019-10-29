from fishing.fishing_data import TunableFishingBaitReferencefrom notebook.notebook_entry import SubEntryDatafrom sims4.tuning.tunable import TunableMappingfrom tag import TunableTagfrom ui.notebook_tuning import NotebookCustomTypeTuningimport servicesimport sims4.loglogger = sims4.log.Logger('Fishing')
class FishingTuning:
    BAIT_TAG_DATA_MAP = TunableMapping(description='\n        Mapping between fishing bait tag and fishing bait data.\n        ', key_type=TunableTag(description='\n            The bait tag to which we want to map a bait data.\n            ', filter_prefixes=('func_bait',)), key_name='Bait Tag', value_type=TunableFishingBaitReference(description='\n            The bait data.\n            ', pack_safe=True), value_name='Bait Data')

    @staticmethod
    def get_fishing_bait_data(obj_def):
        bait_data = None
        for (tag, data) in FishingTuning.BAIT_TAG_DATA_MAP.items():
            if not bait_data is None:
                if bait_data.bait_priority < data.bait_priority:
                    bait_data = data
            bait_data = data
        return bait_data

    @staticmethod
    def get_fishing_bait_data_set(obj_def_ids):
        if obj_def_ids is None:
            return frozenset()
        definition_manager = services.definition_manager()
        bait_data_guids = set()
        for def_id in obj_def_ids:
            bait_def = definition_manager.get(def_id)
            if bait_def is None:
                pass
            else:
                bait_data = FishingTuning.get_fishing_bait_data(bait_def)
                if bait_data is None:
                    logger.error('Object {} failed trying to get fishing bait data category. Make sure the object has bait category tag.', bait_def)
                else:
                    bait_data_guids.add(bait_data.guid64)
        return bait_data_guids

    @staticmethod
    def get_fishing_bait_description(obj):
        bait_data = FishingTuning.get_fishing_bait_data(obj.definition)
        if bait_data is not None:
            return bait_data.bait_description()

    @staticmethod
    def add_bait_notebook_entry(sim, created_fish, bait):
        if sim.sim_info.notebook_tracker is None:
            return
        sub_entries = None
        if bait:
            bait_data = FishingTuning.get_fishing_bait_data(bait.definition)
            if bait_data is not None:
                sub_entries = (SubEntryData(bait_data.guid64, True),)
        sim.sim_info.notebook_tracker.unlock_entry(NotebookCustomTypeTuning.BAIT_NOTEBOOK_ENTRY(created_fish.definition.id, sub_entries=sub_entries))
