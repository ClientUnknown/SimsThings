import collectionsfrom distributor.shared_messages import IconInfoDatafrom interactions.utils.tunable_icon import TunableIconfrom objects.collection_manager import ObjectCollectionDatafrom objects.hovertip import HovertipStyle, TooltipFieldsfrom sims4.localization import TunableLocalizedString, LocalizationHelperTuning, TunableLocalizedStringFactoryfrom sims4.tuning.instances import HashedTunedInstanceMetaclassfrom sims4.tuning.tunable import HasTunableReference, TunableEnumEntry, OptionalTunable, TunableList, TunableTuple, TunableReference, Tunable, TunableMappingfrom sims4.tuning.tunable_base import SourceQueriesfrom ui.notebook_tuning import NotebookCategories, NotebookSubCategoriesimport servicesimport sims4logger = sims4.log.Logger('Notebook', default_owner='camilogarcia')
class NotebookEntry(HasTunableReference, metaclass=HashedTunedInstanceMetaclass, manager=services.get_instance_manager(sims4.resources.Types.NOTEBOOK_ENTRY)):
    INSTANCE_TUNABLES = {'category_id': TunableEnumEntry(description='\n            Category type which will define the format the UI will use\n            to display the information.\n            ', tunable_type=NotebookCategories, default=NotebookCategories.INVALID), 'subcategory_id': TunableEnumEntry(description='\n            Subcategory type which will define the format the UI will use\n            to display the information.\n            ', tunable_type=NotebookSubCategories, default=NotebookSubCategories.INVALID), 'entry_text': TunableLocalizedString(description='\n            Text to be displayed on the notebook entry.        \n            '), 'entry_icon': OptionalTunable(TunableIcon(description='\n            Optional icon to be displayed with the entry text.\n            ')), 'entry_tooltip': OptionalTunable(TunableTuple(description='\n            Text to be displayed when the player hovers this entry.\n            ', tooltip_style=TunableEnumEntry(description='\n                Types of possible tooltips that can be displayed for an entry. \n                ', tunable_type=HovertipStyle, default=HovertipStyle.HOVER_TIP_DEFAULT), tooltip_fields=TunableMapping(description='\n                Mapping of tooltip fields to its localized values. Since \n                this fields are created from a system originally created \n                for recipes, all of them may be tuned, but these are the \n                most common fields to show on a tooltip:\n                - recipe_name = This is the actual title of the tooltip.  \n                This is the main text\n                - recipe_description = This description refers to the main \n                text that will show below the title\n                - header = Smaller text that will show just above the title\n                - subtext = Smaller text that will show just bellow the \n                title\n                ', key_type=TunableEnumEntry(description='\n                    Fields to be populated in the tooltip.  These fields\n                    will be populated with the text and tokens tuned.\n                    ', tunable_type=TooltipFields, default=TooltipFields.recipe_name), value_type=TunableLocalizedString()))), 'entry_sublist': OptionalTunable(TunableList(description='\n            List of objects linked to a notebook entry.\n            i.e. Ingredient objects attached to a serum or to a recipe.\n            ', tunable=TunableTuple(description='\n                Pair of object definitions and amount of objects needed\n                to \n                ', object_definition=TunableReference(services.definition_manager(), description='Reference to ingredient object.'), num_objects_required=Tunable(description='\n                    Number of objects required on this field.  This will be\n                    displayed next to the current value of objects found in the \n                    inventory.\n                    Example: Serums will displayed \n                             <current_objects_held / num_objects_required>\n                    ', tunable_type=int, default=0)))), 'entry_sublist_is_sortable': OptionalTunable(description='\n            If enabled, entry sublist will be presented sorted alphabetically.\n            ', tunable=TunableTuple(include_new_entry=Tunable(description='\n                    If checked, the new entry in entry sublist will be sorted.\n                    ', tunable_type=bool, default=False)))}

    def __init__(self, entry_object_definition_id=None, sub_entries=None, new_entry=True):
        self.new_entry = new_entry
        self.entry_object_definition_id = entry_object_definition_id
        if sub_entries is not None:
            self.sub_entries = list(sub_entries)
        else:
            self.sub_entries = list()

    def has_identical_entries(self, entries):
        for entry in entries:
            if self.__class__ == entry.__class__:
                return True
        return False

    def is_definition_based(self):
        return False

    @property
    def entry_icon_info_data(self):
        if self.entry_icon is not None:
            return IconInfoData(icon_resource=self.entry_icon)
EntryData = collections.namedtuple('EntryData', ('entry_text', 'entry_icon_info_data', 'entry_tooltip', 'entry_sublist', 'entry_sublist_is_sortable'))EntryTooltip = collections.namedtuple('EntryTooltip', ('tooltip_style', 'tooltip_fields'))SubEntryData = collections.namedtuple('SubEntryData', ('sub_entry_id', 'new_sub_entry'))SubListData = collections.namedtuple('SubListData', ('object_definition', 'item_count', 'num_objects_required', 'is_ingredient', 'new_item', 'object_display_name', 'item_icon_info_data', 'item_tooltip'))
class NotebookEntryBait(NotebookEntry):
    REMOVE_INSTANCE_TUNABLES = ('entry_text', 'entry_icon', 'entry_tooltip', 'entry_sublist')
    INSTANCE_TUNABLES = {'entry_text_rarity': TunableLocalizedStringFactory(description='\n            The text to display for rarity.\n            e.g.:\n            Rarity:\n{0.String}\n            '), 'entry_text_size_mapping': TunableMapping(description='\n            Mapping between fish size and the text to display for size.\n            ', key_type=Tunable(description='\n                The size of the fish.\n                ', tunable_type=str, default=None, source_query=SourceQueries.SwingEnumNamePattern.format('fishType')), value_type=TunableLocalizedString(description='\n                The size text.\n                '))}

    def _add_sub_entry(self, new_sub_entry):
        for sub_entry in self.sub_entries:
            if sub_entry.sub_entry_id == new_sub_entry.sub_entry_id:
                break
        self.sub_entries.append(new_sub_entry)

    def _get_entry_rarity_text(self, entry_def):
        (_, collectible_data, _) = ObjectCollectionData.get_collection_info_by_definition(entry_def.id)
        if collectible_data is None:
            logger.error('Failed to find rarity text for Fishing Bait Entry {}.', entry_def)
            return
        rarity_text = ObjectCollectionData.COLLECTION_RARITY_MAPPING[collectible_data.rarity].text_value
        return self.entry_text_rarity(rarity_text)

    def _get_entry_size_text(self, entry_def):
        return self.entry_text_size_mapping[entry_def.cls.fish_type]

    def _get_entry_tooltip(self, entry_def):
        return EntryTooltip(HovertipStyle.HOVER_TIP_DEFAULT, {TooltipFields.subtext: self._get_entry_size_text(entry_def), TooltipFields.rarity_text: self._get_entry_rarity_text(entry_def), TooltipFields.recipe_description: LocalizationHelperTuning.get_object_description(entry_def), TooltipFields.recipe_name: LocalizationHelperTuning.get_object_name(entry_def)})

    def is_definition_based(self):
        return self.entry_object_definition_id is not None

    def get_definition_notebook_data(self, ingredient_cache=[]):
        definition_manager = services.definition_manager()
        snippet_manager = services.snippet_manager()
        fish_definition = definition_manager.get(self.entry_object_definition_id)
        sublist = []
        for (sub_entry_id, new_sub_entry) in reversed(self.sub_entries):
            bait_data = snippet_manager.get(sub_entry_id)
            if fish_definition is None or bait_data is None:
                return
            sublist.append(SubListData(None, 0, 0, True, new_sub_entry, bait_data.bait_name(), IconInfoData(obj_def_id=bait_data.bait_icon_definition.id), bait_data.bait_description()))
        return EntryData(LocalizationHelperTuning.get_object_name(fish_definition), IconInfoData(obj_def_id=fish_definition.id), self._get_entry_tooltip(fish_definition), sublist, self.entry_sublist_is_sortable)

    def has_identical_entries(self, entries):
        for entry in entries:
            if entry.entry_object_definition_id != self.entry_object_definition_id:
                pass
            else:
                for sub_entry in self.sub_entries:
                    entry._add_sub_entry(sub_entry)
                return True
        return False

class NotebookEntryRecipe(NotebookEntry):
    REMOVE_INSTANCE_TUNABLES = ('entry_text', 'entry_icon', 'entry_tooltip', 'entry_sublist')

    @property
    def recipe_object_definition_id(self):
        if self.sub_entries:
            return next(iter(self.sub_entries)).sub_entry_id
        return 0

    def is_definition_based(self):
        return True

    def _get_entry_tooltip(self, entry_def):
        return EntryTooltip(HovertipStyle.HOVER_TIP_DEFAULT, {TooltipFields.recipe_description: LocalizationHelperTuning.get_object_description(entry_def), TooltipFields.recipe_name: LocalizationHelperTuning.get_object_name(entry_def)})

    def get_definition_notebook_data(self, ingredient_cache=[]):
        ingredients_used = {}
        manager = services.get_instance_manager(sims4.resources.Types.RECIPE)
        recipe_definition = manager.get(self.recipe_object_definition_id)
        if recipe_definition is None:
            return
        final_product = recipe_definition.final_product_definition
        self.entry_object_definition_id = final_product.id
        ingredient_display = []
        if recipe_definition.use_ingredients is not None:
            for tuned_ingredient_factory in recipe_definition.sorted_ingredient_requirements:
                ingredients_found_count = 0
                ingredients_needed_count = 0
                ingredient_requirement = tuned_ingredient_factory()
                ingredient_requirement.attempt_satisfy_ingredients(ingredient_cache, ingredients_used)
                ingredients_found_count += ingredient_requirement.count_satisfied
                ingredients_needed_count += ingredient_requirement.count_required
                ingredient_display.append(SubListData(None, ingredients_found_count, ingredients_needed_count, True, False, ingredient_requirement.get_diplay_name(), None, None))
        return EntryData(LocalizationHelperTuning.get_object_name(final_product), IconInfoData(obj_def_id=final_product.id), self._get_entry_tooltip(final_product), ingredient_display, self.entry_sublist_is_sortable)

    def has_identical_entries(self, entries):
        if all(entry.entry_object_definition_id != self.entry_object_definition_id for entry in entries):
            return False
        return super().has_identical_entries(entries)
