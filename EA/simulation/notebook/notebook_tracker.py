import collectionsfrom protocolbuffers import UI_pb2from protocolbuffers import SimObjectAttributes_pb2 as protocolsfrom protocolbuffers.DistributorOps_pb2 import Operationfrom crafting.crafting_interactions import StartCraftingMixinfrom distributor.ops import GenericProtocolBufferOpfrom distributor.rollback import ProtocolBufferRollbackfrom distributor.shared_messages import IconInfoData, create_icon_info_msgfrom distributor.system import Distributorfrom event_testing.resolver import SingleSimResolverfrom fishing.fishing_tuning import FishingTuningfrom notebook.notebook_entry import SubEntryDatafrom objects import ALL_HIDDEN_REASONSfrom sims.sim_info_lod import SimInfoLODLevelfrom sims.sim_info_tracker import SimInfoTrackerfrom sims4.localization import LocalizationHelperTuningfrom sims4.utils import classpropertyfrom ui.notebook_tuning import NotebookTuning, NotebookCustomTypeTuning, NotebookSubCategoriesfrom ui.ui_dialog import CommandArgTypeimport servicesimport sims4.resourceslogger = sims4.log.Logger('Notebook')
class NotebookTrackerSimInfo(SimInfoTracker):

    def __init__(self, sim_info):
        self._owner = sim_info
        self._notebook_entries = collections.defaultdict(list)
        self._notebook_entry_catsubcat_cache = collections.defaultdict(set)

    def clear_notebook_tracker(self):
        self._notebook_entries.clear()
        self._notebook_entry_catsubcat_cache.clear()

    def unlock_entry(self, notebook_entry, from_load=False, notifications=None, resolver=None):
        if resolver is None:
            resolver = SingleSimResolver(self._owner)
        response_command_tuple = (CommandArgType.ARG_TYPE_INT, self._owner.id)
        notebook_entries = self._notebook_entries.get(notebook_entry.subcategory_id)
        if notebook_entries and notebook_entry.has_identical_entries(notebook_entries):
            if notifications and notifications.unlocked_failed_notification:
                dialog = notifications.unlocked_failed_notification(self._owner, resolver)
                dialog.show_dialog(response_command_tuple=response_command_tuple)
            return
        self._notebook_entries[notebook_entry.subcategory_id].append(notebook_entry)
        category_id = NotebookTuning.get_category_id(notebook_entry.subcategory_id)
        self._notebook_entry_catsubcat_cache[category_id].add(notebook_entry.subcategory_id)
        if notifications and notifications.unlocked_success_notification:
            dialog = notifications.unlocked_success_notification(self._owner, resolver)
            dialog.show_dialog(response_command_tuple=response_command_tuple)
        if not from_load:
            notebook_entry.new_entry = True

    def remove_entries_by_subcategory(self, subcategory_id):
        category_id = NotebookTuning.get_category_id(subcategory_id)
        self._notebook_entries.pop(subcategory_id, None)
        category_cache = self._notebook_entry_catsubcat_cache.get(category_id)
        if category_cache and subcategory_id in category_cache:
            category_cache.remove(subcategory_id)
            if not category_cache:
                self._notebook_entry_catsubcat_cache.pop(category_id, None)

    def remove_entry_by_reference(self, subcategory_id, entry):
        notebook_entries = self._notebook_entries.get(subcategory_id)
        if not notebook_entries:
            return
        entries_to_remove = set(entry_inst for entry_inst in notebook_entries if isinstance(entry_inst, entry))
        for to_remove in entries_to_remove:
            notebook_entries.remove(to_remove)
        if not notebook_entries:
            self.remove_entries_by_subcategory(subcategory_id)

    def mark_entry_as_seen(self, subcategory_id, entry_id):
        entry = None
        for notebook_entry in self._notebook_entries[subcategory_id]:
            if entry_id == notebook_entry.entry_object_definition_id:
                entry = notebook_entry
                break
        logger.error('Failed to find notebook entry with SubcategoryId: {} and EntryDefinitionId: {} on Sim: {}.', NotebookSubCategories(subcategory_id), entry_id, self._owner)
        return
        for (i, sub_entry) in enumerate(entry.sub_entries):
            if sub_entry.new_sub_entry:
                entry.sub_entries[i] = SubEntryData(sub_entry.sub_entry_id, False)

    def generate_notebook_information(self, initial_selected_category=None):
        msg = UI_pb2.NotebookView()
        if self._notebook_entries:
            ingredient_cache = StartCraftingMixin.get_default_candidate_ingredients(self._owner.get_sim_instance())
        for (index, category_id) in enumerate(self._notebook_entry_catsubcat_cache.keys()):
            if category_id == initial_selected_category:
                msg.selected_category_index = index
            with ProtocolBufferRollback(msg.categories) as notebook_category_message:
                category_tuning = NotebookTuning.NOTEBOOK_CATEGORY_MAPPING[category_id]
                notebook_category_message.category_name = category_tuning.category_name
                if category_tuning.category_description is not None:
                    notebook_category_message.category_description = category_tuning.category_description
                notebook_category_message.category_icon = create_icon_info_msg(IconInfoData(icon_resource=category_tuning.category_icon))
                valid_subcategories = self._notebook_entry_catsubcat_cache[category_id]
                for subcategory_id in valid_subcategories:
                    with ProtocolBufferRollback(notebook_category_message.subcategories) as notebook_subcategory_message:
                        subcategory_tuning = category_tuning.subcategories[subcategory_id]
                        notebook_subcategory_message.subcategory_id = subcategory_id
                        notebook_subcategory_message.subcategory_name = subcategory_tuning.subcategory_name
                        notebook_subcategory_message.subcategory_icon = create_icon_info_msg(IconInfoData(icon_resource=subcategory_tuning.subcategory_icon))
                        notebook_subcategory_message.subcategory_tooltip = subcategory_tuning.subcategory_tooltip
                        notebook_subcategory_message.entry_type = subcategory_tuning.format_type
                        if subcategory_tuning.show_max_entries is not None:
                            notebook_subcategory_message.max_num_entries = subcategory_tuning.show_max_entries
                        if subcategory_tuning.is_sortable is None:
                            notebook_subcategory_message.is_sortable = False
                            notebook_subcategory_message.is_new_entry_sortable = False
                        else:
                            notebook_subcategory_message.is_sortable = True
                            notebook_subcategory_message.is_new_entry_sortable = subcategory_tuning.is_sortable.include_new_entry
                        subcategory_entries = self._notebook_entries[subcategory_id]
                        for entry in reversed(subcategory_entries):
                            if entry is None:
                                pass
                            else:
                                if entry.is_definition_based():
                                    definition_data = entry.get_definition_notebook_data(ingredient_cache=ingredient_cache)
                                    if definition_data is not None:
                                        self._fill_notebook_entry_data(notebook_subcategory_message, subcategory_tuning, definition_data, entry.entry_object_definition_id, True, entry.new_entry)
                                else:
                                    self._fill_notebook_entry_data(notebook_subcategory_message, subcategory_tuning, entry, entry.entry_object_definition_id, False, entry.new_entry)
                                entry.new_entry = False
        op = GenericProtocolBufferOp(Operation.NOTEBOOK_VIEW, msg)
        Distributor.instance().add_op(self._owner, op)

    def _fill_notebook_entry_data(self, notebook_subcategory_message, subcategory_tuning, entry, entry_def_id, definition_based, new_entry):
        active_sim = self._owner.get_sim_instance(allow_hidden_flags=ALL_HIDDEN_REASONS)
        with ProtocolBufferRollback(notebook_subcategory_message.entries) as notebook_entry_message:
            notebook_entry_message.entry_message = entry.entry_text
            if entry_def_id is not None:
                notebook_entry_message.entry_id = entry_def_id
            if entry.entry_icon_info_data is not None:
                notebook_entry_message.entry_icon = create_icon_info_msg(entry.entry_icon_info_data)
            if entry.entry_tooltip is not None:
                notebook_entry_message.entry_metadata_hovertip.hover_tip = entry.entry_tooltip.tooltip_style
                for (tooltip_key, tooltip_text) in entry.entry_tooltip.tooltip_fields.items():
                    setattr(notebook_entry_message.entry_metadata_hovertip, tooltip_key.name, tooltip_text)
            notebook_entry_message.new_entry = new_entry
            if entry.entry_sublist:
                entry_list_description = subcategory_tuning.entry_list_texts.has_list_text
                if entry_list_description is not None:
                    notebook_entry_message.entry_list_description = entry_list_description
                if entry.entry_sublist_is_sortable is None:
                    notebook_entry_message.is_sortable = False
                    notebook_entry_message.is_new_item_sortable = False
                else:
                    notebook_entry_message.is_sortable = True
                    notebook_entry_message.is_new_item_sortable = entry.entry_sublist_is_sortable.include_new_entry
                for sublist_data in entry.entry_sublist:
                    with ProtocolBufferRollback(notebook_entry_message.entry_list) as notebook_entry_list_message:
                        if sublist_data.is_ingredient:
                            item_message = sublist_data.object_display_name
                        else:
                            item_message = LocalizationHelperTuning.get_object_name(sublist_data.object_definition)
                        notebook_entry_list_message.item_message = item_message
                        if active_sim is not None and sublist_data.num_objects_required > 0:
                            if sublist_data.is_ingredient:
                                notebook_entry_list_message.item_count = sublist_data.item_count
                            else:
                                notebook_entry_list_message.item_count = active_sim.inventory_component.get_count(sublist_data.object_definition)
                        else:
                            notebook_entry_list_message.item_count = 0
                        notebook_entry_list_message.item_total = sublist_data.num_objects_required
                        notebook_entry_list_message.new_item = sublist_data.new_item
                        if sublist_data.item_icon_info_data is not None:
                            notebook_entry_list_message.item_icon = create_icon_info_msg(sublist_data.item_icon_info_data)
                        if sublist_data.item_tooltip is not None:
                            notebook_entry_list_message.item_tooltip = sublist_data.item_tooltip
            else:
                entry_list_description = subcategory_tuning.entry_list_texts.no_list_text
                if entry_list_description is not None:
                    notebook_entry_message.entry_list_description = entry_list_description

    def save_notebook(self):
        notebook_tracker_data = protocols.PersistableNotebookTracker()
        for category_list in self._notebook_entries.values():
            for entry in category_list:
                with ProtocolBufferRollback(notebook_tracker_data.notebook_entries) as entry_data:
                    entry_data.tuning_reference_id = entry.guid64
                    entry_data.new_entry = entry.new_entry
                    if entry.is_definition_based():
                        if entry.entry_object_definition_id is not None:
                            entry_data.object_recipe_id = entry.entry_object_definition_id
                        for sub_entry in entry.sub_entries:
                            with ProtocolBufferRollback(entry_data.object_sub_entries) as sub_entry_data:
                                sub_entry_data.sub_entry_id = sub_entry.sub_entry_id
                                sub_entry_data.new_sub_entry = sub_entry.new_sub_entry
        return notebook_tracker_data

    def load_notebook(self, notebook_proto_msg):
        manager = services.get_instance_manager(sims4.resources.Types.NOTEBOOK_ENTRY)
        for notebook_data in notebook_proto_msg.notebook_entries:
            tuning_reference_id = notebook_data.tuning_reference_id
            tuning_instance = manager.get(tuning_reference_id)
            if tuning_instance is None:
                pass
            else:
                object_entry_ids = list(notebook_data.object_entry_ids)
                object_definition_id = notebook_data.object_recipe_id
                sub_entries = []
                if object_entry_ids:
                    if tuning_instance is NotebookCustomTypeTuning.BAIT_NOTEBOOK_ENTRY:
                        object_entry_ids = FishingTuning.get_fishing_bait_data_set(object_entry_ids)
                    for sub_entry_id in object_entry_ids:
                        sub_entries.append(SubEntryData(sub_entry_id, False))
                else:
                    for sub_entry in notebook_data.object_sub_entries:
                        sub_entries.append(SubEntryData(sub_entry.sub_entry_id, sub_entry.new_sub_entry))
                self._owner.notebook_tracker.unlock_entry(tuning_instance(object_definition_id, sub_entries, notebook_data.new_entry), from_load=True)

    @property
    def unlocked_category_ids(self):
        return self._notebook_entry_catsubcat_cache.keys()

    @classproperty
    def _tracker_lod_threshold(cls):
        return SimInfoLODLevel.FULL

    def on_lod_update(self, old_lod, new_lod):
        if new_lod < self._tracker_lod_threshold:
            self.clear_notebook_tracker()
        elif old_lod < self._tracker_lod_threshold:
            sim_msg = services.get_persistence_service().get_sim_proto_buff(self._owner.id)
            if sim_msg is not None:
                self.load_notebook(sim_msg.attributes.notebook_tracker)
