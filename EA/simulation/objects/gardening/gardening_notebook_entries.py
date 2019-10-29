import itertoolsfrom distributor.shared_messages import IconInfoDatafrom notebook.notebook_entry import NotebookEntry, EntryData, SubListDatafrom objects.collection_manager import ObjectCollectionData, CollectionIdentifierfrom objects.gardening.gardening_tuning import GardeningTuningfrom sims4.localization import LocalizationHelperTuning, TunableLocalizedStringFactoryimport services
class NotebookEntryGardeningPlant(NotebookEntry):
    REMOVE_INSTANCE_TUNABLES = ('entry_text', 'entry_icon', 'entry_tooltip', 'entry_sublist', 'entry_sublist_is_sortable')
    INSTANCE_TUNABLES = {'entry_text_rarity': TunableLocalizedStringFactory(description='\n            The text to display for rarity.\n            e.g.:\n            Rarity:\n{0.String}\n            '), 'entry_text_value': TunableLocalizedStringFactory(description="\n            The text to display for the fruit's Simoleon value.\n            e.g.:\n            Average Harvestable Value:\n{0.Money}\n            "), 'entry_text_splicing': TunableLocalizedStringFactory(description='\n            The text to display for a single splicing entry.\n            e.g.:\n            Splice with {P0.ObjectName} to get {P1.ObjectName}.\n            ')}

    def is_definition_based(self):
        return self.entry_object_definition_id is not None

    def get_definition_notebook_data(self, ingredient_cache=()):
        definition_manager = services.definition_manager()
        fruit_definition = definition_manager.get(self.entry_object_definition_id)
        if fruit_definition is None:
            return
        gardening_tuned_values = fruit_definition.cls._components.gardening._tuned_values
        plant_definition = gardening_tuned_values.plant
        sub_list_data = []
        sub_list_data.append(SubListData(None, 0, 0, True, False, self.entry_text_value(fruit_definition.price/5), None, None))
        season_service = services.season_service()
        if season_service is not None:
            season_text = GardeningTuning.get_seasonality_text_from_plant(plant_definition)
            if season_text is None:
                season_text = GardeningTuning.PLANT_SEASONALITY_TEXT(GardeningTuning.SEASONALITY_ALL_SEASONS_TEXT)
            sub_list_data.append(SubListData(None, 0, 0, True, False, season_text, None, None))
        sub_list_data.append(SubListData(None, 0, 0, True, False, LocalizationHelperTuning.get_object_description(plant_definition), None, None))
        for (splice_fruit, splice_fruit_result) in gardening_tuned_values.splicing_recipies.items():
            sub_list_data.append(SubListData(None, 0, 0, True, False, self.entry_text_splicing(splice_fruit, splice_fruit_result), None, None))
        gardening_collection_data = ObjectCollectionData.get_collection_data(CollectionIdentifier.Gardening)
        for obj_data in itertools.chain(gardening_collection_data.object_list, gardening_collection_data.bonus_object_list):
            if obj_data.collectable_item is fruit_definition:
                rarity_text = ObjectCollectionData.COLLECTION_RARITY_MAPPING[obj_data.rarity].text_value
                sub_list_data.append(SubListData(None, 0, 0, True, False, self.entry_text_rarity(rarity_text), None, None))
                break
        entry_data = EntryData(LocalizationHelperTuning.get_object_name(fruit_definition), IconInfoData(obj_def_id=fruit_definition.id), None, sub_list_data, None)
        return entry_data

    def has_identical_entries(self, entries):
        if any(entry.entry_object_definition_id == self.entry_object_definition_id for entry in entries):
            return True
        return False
