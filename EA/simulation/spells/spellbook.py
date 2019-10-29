import itertoolsfrom protocolbuffers.DistributorOps_pb2 import Operationfrom protocolbuffers.UI_pb2 import BookView, BookPageMessage, BookCategoryMessage, BookTabMessageimport sims4.logfrom collections import defaultdictfrom distributor.ops import GenericProtocolBufferOpfrom distributor.rollback import ProtocolBufferRollbackfrom distributor.shared_messages import IconInfoData, create_icon_info_msgfrom distributor.system import Distributorfrom sims4.localization import LocalizationHelperTuningfrom ui.book_tuning import BookDisplayStyle, BookPageType, BookCategoryDisplayType, BookEntryStatusFlagfrom ui.spellbook_tuning import SpellbookTuninglogger = sims4.log.Logger('SpellBook', default_owner='jdimailig')MAX_VISIBLE_PAGES = 2
class _SpellbookCategoryHelper:

    def __init__(self, book_helper, tuning_data):
        self._book_helper = book_helper
        self._tuning_data = tuning_data
        self._first_page_index = book_helper.current_page_index
        entries = tuning_data.content.entries
        self._unpaginated_entries = list(reversed(entries))
        self._unlocked_entries = set()
        self._new_entries = set()
        unlock_tracker = book_helper.sim_info.unlock_tracker
        if unlock_tracker is not None:
            for entry in entries:
                if unlock_tracker.is_unlocked(entry):
                    self._unlocked_entries.add(entry)
                if unlock_tracker.is_marked_as_new(entry):
                    self._new_entries.add(entry)
        self._populate_entry_message = self._populate_recipe_entry_message if tuning_data.content.category_type == BookCategoryDisplayType.WITCH_POTION else self._populate_spell_entry_message

    @property
    def category_display_type(self):
        return self._tuning_data.content.category_type

    def construct_page_data(self):
        self._generate_category_list_data()
        self._generate_category_tab_data()
        self._generate_category_pages()

    def _generate_category_list_data(self):
        content_list_tuning = self._tuning_data.content_list
        unlocked = len(self._unlocked_entries)
        total = len(self._tuning_data.content.entries)
        progress = 100 if unlocked == total else int(unlocked/total*100)
        list_data = BookCategoryMessage()
        list_data.first_page_index = self._first_page_index
        list_data.name = self._tuning_data.category_name
        list_data.icon.type = content_list_tuning.icon.type
        list_data.icon.group = content_list_tuning.icon.group
        list_data.icon.instance = content_list_tuning.icon.instance
        if content_list_tuning.tooltip is not None:
            list_data.tooltip_text = content_list_tuning.tooltip
        list_data.progress = progress
        list_data.progress_title = SpellbookTuning.PROGRESS_LABEL
        list_data.progress_text = SpellbookTuning.PROGRESS_TEXT_FORMAT(unlocked, total)
        for entry in self._new_entries:
            list_data.new_entries.append(entry.guid64)
        self._book_helper.set_content_list_message(self.category_display_type, list_data)

    def _generate_category_tab_data(self):
        tab_tuning = self._tuning_data.tab
        tab_data = BookTabMessage()
        tab_data.first_page_index = self._first_page_index
        tooltip = None
        if tab_tuning.tooltip is not None:
            tooltip = tab_tuning.tooltip
        else:
            tooltip = self._tuning_data.category_name
        tab_data.icon_info = create_icon_info_msg(IconInfoData(icon_resource=tab_tuning.icon), None, None, tooltip)
        self._book_helper.set_content_tab_message(self.category_display_type, tab_data)

    def _is_unlocked(self, entry):
        return entry in self._unlocked_entries

    def _is_new(self, entry):
        return entry in self._new_entries

    def _generate_category_pages(self):
        self._generate_category_front_page()
        while self._unpaginated_entries:
            self._generate_additional_entry_page()
        if self._book_helper.current_page_index % MAX_VISIBLE_PAGES:
            self._generate_blank_page()

    def _add_entries_to_category_page(self, page, entry_limit):
        entries_added = 0
        while self._unpaginated_entries and entries_added < entry_limit:
            entry_to_add = self._unpaginated_entries.pop()
            with ProtocolBufferRollback(page.entries) as entry_message:
                entry_message.id = entry_to_add.guid64
                entry_message.category_type = self.category_display_type
                if entry_to_add in self._unlocked_entries:
                    entry_message.status_flags |= BookEntryStatusFlag.ENTRY_UNLOCKED
                if entry_to_add in self._new_entries:
                    entry_message.status_flags |= BookEntryStatusFlag.ENTRY_NEW
                self._populate_entry_message(entry_message, entry_to_add)
                entries_added += 1

    def _generate_category_front_page(self):
        front_page_tuning = self._tuning_data.front_page
        page = BookPageMessage()
        page.type = BookPageType.CATEGORY_FRONT
        page.title = self._tuning_data.category_name
        if front_page_tuning.category_description is not None:
            page.description = front_page_tuning.category_description
        page.icon.type = front_page_tuning.icon.type
        page.icon.group = front_page_tuning.icon.group
        page.icon.instance = front_page_tuning.icon.instance
        self._add_entries_to_category_page(page, SpellbookTuning.CATEGORY_FRONT_PAGE_ENTRY_COUNT)
        self._book_helper.add_category_page(self.category_display_type, page)

    def _generate_additional_entry_page(self):
        page = BookPageMessage()
        page.type = BookPageType.CATEGORY
        page_tuning = self._tuning_data.page
        if page_tuning.icon:
            page.icon.type = page_tuning.icon.type
            page.icon.group = page_tuning.icon.group
            page.icon.instance = page_tuning.icon.instance
        self._add_entries_to_category_page(page, SpellbookTuning.CATEGORY_ENTRY_COUNT)
        self._book_helper.add_category_page(self.category_display_type, page)

    def _generate_blank_page(self):
        page = BookPageMessage()
        page.type = BookPageType.BLANK
        page_tuning = self._tuning_data.page
        if page_tuning.icon:
            page.icon.type = page_tuning.icon.type
            page.icon.group = page_tuning.icon.group
            page.icon.instance = page_tuning.icon.instance
        self._book_helper.add_category_page(self.category_display_type, page)

    def _populate_spell_entry_message(self, entry_message, spell):
        entry_message.name = spell.display_name
        if spell.locked_description and not self._is_unlocked(spell):
            entry_message.description = spell.locked_description
        else:
            entry_message.description = spell.display_description
        entry_message.icon.type = spell.display_icon.type
        entry_message.icon.group = spell.display_icon.group
        entry_message.icon.instance = spell.display_icon.instance
        ingredients = spell.ingredients.ingredients
        if ingredients:
            entry_message.subtext_title = SpellbookTuning.INGREDIENTS_LABEL
            entry_message.subtext = LocalizationHelperTuning.get_comma_separated_list(*tuple(SpellbookTuning.INGREDIENT_FORMAT(LocalizationHelperTuning.get_object_name(ingredient.ingredient), ingredient.quantity) for ingredient in ingredients))

    def _populate_recipe_entry_message(self, entry_message, recipe):
        recipe_display_mapping = SpellbookTuning.POTION_DISPLAY_DATA
        recipe_display_data = recipe_display_mapping.get(recipe)
        entry_message.name = recipe.name()
        if recipe_display_data is None:
            logger.error('{} not found in potion display data, update SpellbookTuning.POTION_DISPLAY_DATA', recipe)
            return
        if recipe_display_data.locked_description and not self._is_unlocked(recipe):
            entry_message.description = recipe_display_data.locked_description
        elif recipe_display_data.potion_description is not None:
            entry_message.description = recipe_display_data.potion_description
        else:
            entry_message.description = recipe.recipe_description()
        entry_message.icon.type = recipe_display_data.icon.type
        entry_message.icon.group = recipe_display_data.icon.group
        entry_message.icon.instance = recipe_display_data.icon.instance
        if recipe.use_ingredients is not None:
            entry_message.subtext_title = SpellbookTuning.INGREDIENTS_LABEL
            entry_message.subtext = LocalizationHelperTuning.get_comma_separated_list(*tuple(SpellbookTuning.INGREDIENT_FORMAT(ingredient.get_diplay_name(), ingredient.count_required) for ingredient in (req_factory() for req_factory in recipe.sorted_ingredient_requirements)))

class SpellbookHelper:

    def __init__(self, sim_info):
        self._sim_info = sim_info
        self._current_page_index = 0
        self._category_to_pages = None
        self._content_list_entries = {}
        self._content_tab_entries = {}

    @property
    def sim_info(self):
        return self._sim_info

    @property
    def current_page_index(self):
        return self._current_page_index

    def set_content_list_message(self, category_type, category_message):
        self._content_list_entries[category_type] = category_message

    def set_content_tab_message(self, category_type, tab_message):
        self._content_tab_entries[category_type] = tab_message

    def add_category_page(self, category_type, page_message):
        page_message.category_type = category_type
        self._category_to_pages[category_type].append(page_message)
        self._current_page_index += 1

    def view_spellbook(self, context=None):
        self._current_page_index = 0
        self._category_to_pages = defaultdict(list)
        self._content_list_entries = {}
        self._content_tab_entries = {}
        book_view_message = BookView()
        book_view_message.style = BookDisplayStyle.WITCH
        if context is not None:
            book_view_message.context = context
        with ProtocolBufferRollback(book_view_message.pages) as front_page:
            front_page.type = BookPageType.FRONT
            front_page.title = SpellbookTuning.FRONT_PAGE_DATA.title(self._sim_info)
            front_page_icon = SpellbookTuning.FRONT_PAGE_DATA.icon
            if front_page_icon is not None:
                front_page.icon.type = front_page_icon.type
                front_page.icon.group = front_page_icon.group
                front_page.icon.instance = front_page_icon.instance
            if SpellbookTuning.FRONT_PAGE_DATA.page_description is not None:
                front_page.description = SpellbookTuning.FRONT_PAGE_DATA.page_description
        self._current_page_index = 2
        for category_data in SpellbookTuning.CATEGORY_DATAS:
            category_helper = _SpellbookCategoryHelper(self, category_data)
            category_helper.construct_page_data()
        with ProtocolBufferRollback(book_view_message.pages) as contents_page:
            contents_page.type = BookPageType.CATEGORY_LIST
            contents_page.title = SpellbookTuning.CATEGORY_LIST_DATA.title(self._sim_info)
            if SpellbookTuning.CATEGORY_LIST_DATA.page_description is not None:
                contents_page.description = SpellbookTuning.CATEGORY_LIST_DATA.page_description
            for category_entry_message in self._content_list_entries.values():
                contents_page.categories.append(category_entry_message)
        for page in itertools.chain(*self._category_to_pages.values()):
            book_view_message.pages.append(page)
        for category_tab_message in self._content_tab_entries.values():
            book_view_message.tabs.append(category_tab_message)
        op = GenericProtocolBufferOp(Operation.BOOK_VIEW, book_view_message)
        Distributor.instance().add_op(self._sim_info, op)
