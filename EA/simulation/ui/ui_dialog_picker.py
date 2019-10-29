from protocolbuffers import Dialog_pb2, Consts_pb2, UI_pb2from distributor.shared_messages import build_icon_info_msg, IconInfoData, create_icon_info_msgfrom distributor.system import Distributorfrom interactions import ParticipantTypeSinglefrom interactions.utils.tunable_icon import TunableIconFactoryfrom objects.slots import SlotTypefrom sims.outfits.outfit_enums import OutfitCategory, REGULAR_OUTFIT_CATEGORIESfrom sims4.localization import LocalizationHelperTuning, TunableLocalizedString, TunableLocalizedStringFactoryVariant, NULL_LOCALIZED_STRING_FACTORY, TunableLocalizedStringFactoryfrom sims4.math import MAX_INT16from sims4.tuning.tunable import TunableEnumEntry, TunableList, OptionalTunable, Tunable, TunableResourceKey, TunableVariant, TunableTuple, HasTunableSingletonFactory, AutoFactoryInit, TunableRange, TunableReference, TunableEnumSet, TunableEnumFlags, TunableSetfrom sims4.utils import classpropertyfrom singletons import DEFAULT, EMPTY_SETfrom snippets import define_snippetfrom statistics.skill import Skillfrom ui.ui_dialog import UiDialogOkCancelfrom ui.ui_dialog_multi_picker import UiMultiPickerimport build_buyimport distributorimport enumimport servicesimport sims4.logimport taglogger = sims4.log.Logger('Dialog')
class ObjectPickerType(enum.Int, export=False):
    RECIPE = 1
    INTERACTION = 2
    SIM = 3
    OBJECT = 4
    PIE_MENU = 5
    CAREER = 6
    OUTFIT = 7
    PURCHASE = 8
    LOT = 9
    SIM_CLUB = 10
    ITEM = 11
    OBJECT_LARGE = 12
    DROPDOWN = 13
    OBJECT_SQUARE = 14
    ODD_JOBS = 15
    CUSTOM = 99

class ObjectPickerTuningFlags(enum.IntFlags):
    NONE = 0
    RECIPE = 1
    INTERACTION = 2
    SIM = 4
    OBJECT = 8
    PIE_MENU = 16
    CAREER = 32
    OUTFIT = 64
    PURCHASE = 128
    LOT = 256
    MAP_VIEW = 512
    APARTMENT = 1024
    ITEM = 2048
    DROPDOWN = 4096
    ALL = RECIPE | INTERACTION | SIM | OBJECT | PIE_MENU | CAREER | OUTFIT | PURCHASE | LOT | MAP_VIEW | APARTMENT | ITEM | DROPDOWN

class RowMapType(enum.Int):
    NAME = 0
    ICON = 1
    SKILL_LEVEL = 2
    PRICE = 3
    INGREDIENTS = 4
ROW_MAP_NAMES = ['name', 'icon', 'skill_level', 'price', 'ingredients']
class PickerColumn(HasTunableSingletonFactory, AutoFactoryInit):

    class ColumnType(enum.Int):
        TEXT = 1
        ICON = 2
        ICON_AND_TEXT = 3
        INGREDIENT_LIST = 4

    FACTORY_TUNABLES = {'column_type': TunableEnumEntry(description='\n            The type of column.\n            ', tunable_type=ColumnType, default=ColumnType.ICON_AND_TEXT), 'label': OptionalTunable(description='\n            If enabled, the text to show on the column. \n            ', tunable=TunableLocalizedString()), 'icon': OptionalTunable(description='\n            If enabled, the icon to show on the column.\n            ', tunable=TunableResourceKey(resource_types=sims4.resources.CompoundTypes.IMAGE, default=None)), 'tooltip': OptionalTunable(description='\n            If enabled, the tooltip text for the column.\n            ', tunable=TunableLocalizedString()), 'width': Tunable(description='\n            The width of the column.\n            ', tunable_type=float, default=100), 'sortable': Tunable(description='\n            Whether or not we can sort the column.\n            ', tunable_type=bool, default=True), 'column_data_name': TunableEnumEntry(description='\n            The name of the data field inside the row to show in this column,\n            name/skill/price etc.\n            ', tunable_type=RowMapType, default=RowMapType.NAME), 'column_icon_name': TunableEnumEntry(description='\n            The name of the icon field inside the row to show in this column,\n            most likely should just be icon.\n            ', tunable_type=RowMapType, default=RowMapType.ICON)}

    def populate_protocol_buffer(self, column_data):
        column_data.type = self.column_type
        if self.column_data_name is not None:
            column_data.column_data_name = ROW_MAP_NAMES[self.column_data_name]
        if self.column_icon_name is not None:
            column_data.column_icon_name = ROW_MAP_NAMES[self.column_icon_name]
        if self.label is not None:
            column_data.label = self.label
        if self.icon is not None:
            column_data.icon.type = self.icon.type
            column_data.icon.group = self.icon.group
            column_data.icon.instance = self.icon.instance
        if self.tooltip is not None:
            column_data.tooltip = self.tooltip
        column_data.width = self.width
        column_data.sortable = self.sortable

    def __format__(self, fmt):
        dump_str = 'type: {}, label:{}, icon:{}, tooltip:{}, width:{}, sortable:{}'.format(self.column_type, self.label, self.icon, self.tooltip, self.width, self.sortable)
        return dump_str

class BasePickerRow:

    def __init__(self, option_id=None, is_enable=True, name=None, icon=None, row_description=None, row_tooltip=None, tag=None, icon_info=None, pie_menu_influence_by_active_mood=False, is_selected=False, tag_list=None):
        self.option_id = option_id
        self.tag = tag
        self.is_enable = is_enable
        self.name = name
        self.icon = icon
        self.row_description = row_description
        self.row_tooltip = row_tooltip
        self.icon_info = icon_info
        self._pie_menu_influence_by_active_mood = pie_menu_influence_by_active_mood
        self.is_selected = is_selected
        self.tag_list = tag_list

    def populate_protocol_buffer(self, base_row_data, name_override=DEFAULT):
        base_row_data.option_id = self.option_id
        base_row_data.is_enable = bool(self.is_enable)
        base_row_data.is_selected = bool(self.is_selected)
        if name_override is DEFAULT:
            name_override = self.name
        if name_override is not None:
            base_row_data.name = name_override
        if self.icon is not None:
            base_row_data.icon.type = self.icon.type
            base_row_data.icon.group = self.icon.group
            base_row_data.icon.instance = self.icon.instance
            if self.icon_info is None:
                build_icon_info_msg(IconInfoData(icon_resource=self.icon), None, base_row_data.icon_info)
        if self.icon_info is not None:
            build_icon_info_msg(self.icon_info, None, base_row_data.icon_info)
        if self.row_description is not None:
            base_row_data.description = self.row_description
        if self.row_tooltip:
            base_row_data.tooltip = self.row_tooltip()
        if self.tag_list is not None:
            base_row_data.tag_list.extend(self.tag_list)

    @property
    def available_as_pie_menu(self):
        return True

    @property
    def pie_menu_category(self):
        pass

    @property
    def pie_menu_influence_by_active_mood(self):
        return self._pie_menu_influence_by_active_mood

    def __repr__(self):
        return str(self.tag)

    def __format__(self, fmt):
        show_name = ''
        if self.tag is not None:
            show_name = '[{}]\t\t\t'.format(self.tag.__class__.__name__)
        dump_str = ' {}, enable:{}, '.format(show_name, self.is_enable)
        return dump_str

class RecipePickerRow(BasePickerRow):

    def __init__(self, price=0, skill_level=0, linked_recipe=None, display_name=DEFAULT, ingredients=None, price_with_ingredients=0, mtx_id=None, discounted_price=0, is_discounted=False, **kwargs):
        super().__init__(**kwargs)
        self.price = price
        self.skill_level = skill_level
        self.linked_recipe = linked_recipe
        self.linked_option_ids = []
        self.display_name = display_name
        self.visible_as_subrow = self.tag.visible_as_subrow
        self._pie_menu_category = self.tag.base_recipe_category
        self.ingredients = ingredients
        self.price_with_ingredients = price_with_ingredients
        self.mtx_id = mtx_id
        self.discounted_price = discounted_price
        self.is_discounted = is_discounted

    def populate_protocol_buffer(self, recipe_row_data):
        super().populate_protocol_buffer(recipe_row_data.base_data)
        if self.display_name is not DEFAULT:
            recipe_row_data.serving_display_name = self.display_name
        if self.price != 0:
            price = abs(self.price)
            recipe_row_data.price = int(price)
        recipe_row_data.skill_level = int(self.skill_level)
        for linked_id in self.linked_option_ids:
            recipe_row_data.linked_option_ids.append(linked_id)
        recipe_row_data.visible_as_subrow = self.visible_as_subrow
        recipe_row_data.price_with_ingredients = self.price_with_ingredients
        if self.ingredients:
            for ingredient in self.ingredients:
                ingredient_data = recipe_row_data.ingredients.add()
                ingredient_data.ingredient_name = ingredient.ingredient_name
                ingredient_data.in_inventory = ingredient.is_in_inventory
        if self.mtx_id is not None:
            recipe_row_data.mtx_id = self.mtx_id
        recipe_row_data.discounted_price = int(self.discounted_price)
        recipe_row_data.is_discounted = self.is_discounted

    @property
    def available_as_pie_menu(self):
        return self.visible_as_subrow

    @property
    def pie_menu_category(self):
        return self._pie_menu_category

    def __format__(self, fmt):
        super_dump_str = super().__format__(fmt)
        dump_str = 'RecipePickerRow({}, skill:{}, price:{}, linked rows[{}])'.format(super_dump_str, self.skill_level, self.price, len(self.linked_option_ids))
        return dump_str

class SimPickerRow(BasePickerRow):

    def __init__(self, sim_id=None, select_default=False, **kwargs):
        super().__init__(**kwargs)
        self.sim_id = sim_id
        self.select_default = select_default

    def populate_protocol_buffer(self, sim_row_data):
        super().populate_protocol_buffer(sim_row_data.base_data)
        if self.sim_id is not None:
            sim_row_data.sim_id = self.sim_id
            sim_row_data.select_default = self.select_default

    def __format__(self, fmt):
        dump_str = 'SimPickerRow(Sim id:{})'.format(self.sim_id)
        return dump_str

class ObjectPickerRow(BasePickerRow):

    def __init__(self, object_id=None, def_id=None, count=1, rarity_text=None, use_catalog_product_thumbnails=True, **kwargs):
        super().__init__(**kwargs)
        self.object_id = object_id
        self.def_id = def_id
        self.count = count
        self.rarity_text = rarity_text
        self.use_catalog_product_thumbnails = use_catalog_product_thumbnails

    def populate_protocol_buffer(self, object_row_data):
        super().populate_protocol_buffer(object_row_data.base_data)
        if self.object_id is not None:
            object_row_data.object_id = self.object_id
        if self.def_id is not None:
            object_row_data.def_id = self.def_id
        object_row_data.count = self.count
        if self.rarity_text is not None:
            object_row_data.rarity_text = self.rarity_text
        if not self.use_catalog_product_thumbnails:
            object_row_data.use_catalog_product_thumbnails = False

    def __format__(self, fmt):
        super_dump_str = super().__format__(fmt)
        dump_str = 'ObjectPickerRow({}, object_id:{}, def_id:{})'.format(super_dump_str, self.object_id, self.def_id)
        return dump_str

class OddJobPickerRow(BasePickerRow):

    def __init__(self, customer_id=None, customer_description=None, tip_title=None, tip_text=None, tip_icon=None, **kwargs):
        super().__init__(**kwargs)
        self.customer_id = customer_id
        self.customer_description = customer_description
        self.tip_title = tip_title
        self.tip_text = tip_text
        self.tip_icon = tip_icon

    def populate_protocol_buffer(self, odd_job_picker_row):
        super().populate_protocol_buffer(odd_job_picker_row.base_data)
        odd_job_picker_row.customer_id = self.customer_id
        odd_job_picker_row.customer_description = self.customer_description
        odd_job_picker_row.tip_title = self.tip_title
        build_icon_info_msg(IconInfoData(icon_resource=self.tip_icon), None, odd_job_picker_row.tip_icon, desc=self.tip_text)

    def __format__(self, fmt):
        super_dump_str = super().__format__(fmt)
        dump_str = 'OddJobPickerRow({})'.format(super_dump_str)
        return dump_str

class OutfitPickerRow(BasePickerRow):

    def __init__(self, outfit_sim_id, outfit_category, outfit_index, **kwargs):
        super().__init__(**kwargs)
        self._outfit_sim_id = outfit_sim_id
        self._outfit_category = outfit_category
        self._outfit_index = outfit_index

    def populate_protocol_buffer(self, outfit_row_data):
        super().populate_protocol_buffer(outfit_row_data.base_data)
        outfit_row_data.outfit_sim_id = self._outfit_sim_id
        outfit_row_data.outfit_category = self._outfit_category
        outfit_row_data.outfit_index = self._outfit_index

    def __format__(self, fmt):
        super_dump_str = super().__format__(fmt)
        dump_str = 'OutfitPickerRow({})'.format(super_dump_str)
        return dump_str

class PurchasePickerRow(BasePickerRow):

    def __init__(self, def_id=0, num_owned=0, tags=(), num_available=None, custom_price=None, objects=EMPTY_SET, show_discount=False, **kwargs):
        super().__init__(**kwargs)
        self.def_id = def_id
        self.num_owned = num_owned
        self.tags = tags
        self.num_available = num_available
        self.custom_price = custom_price
        self.objects = objects
        self.show_discount = show_discount

    def populate_protocol_buffer(self, purchase_row_data):
        super().populate_protocol_buffer(purchase_row_data.base_data)
        purchase_row_data.def_id = self.def_id
        purchase_row_data.num_owned = self.num_owned
        purchase_row_data.tag_list.extend(self.tags)
        if self.num_available is not None:
            purchase_row_data.num_available = self.num_available
        if self.custom_price is not None:
            purchase_row_data.custom_price = self.custom_price
        purchase_row_data.is_discounted = self.show_discount
        obj = next(iter(self.objects), None)
        if obj is not None:
            purchase_row_data.object_id = obj.id
            icon_info = obj.get_icon_info_data()
            build_icon_info_msg(icon_info, None, purchase_row_data.base_data.icon_info)
        elif self.def_id is not None:
            definition_tuning = services.definition_manager().get_object_tuning(self.def_id)
            icon_override = definition_tuning.icon_override
            if icon_override is not None:
                icon_info = IconInfoData(icon_resource=icon_override)
                build_icon_info_msg(icon_info, None, purchase_row_data.base_data.icon_info)

    def __format__(self, fmt):
        super_dump_str = super().__format__(fmt)
        dump_str = 'PurchasePickerRow({}, def_id: {}, num_owned: {})'.format(super_dump_str, self.def_id, self.num_owned)
        return dump_str

class LotPickerRow(BasePickerRow):

    def __init__(self, zone_data, **kwargs):
        super().__init__(**kwargs)
        self.zone_id = zone_data.zone_id
        self.name = zone_data.name
        self.world_id = zone_data.world_id
        self.lot_template_id = zone_data.lot_template_id
        self.lot_description_id = zone_data.lot_description_id
        venue_manager = services.get_instance_manager(sims4.resources.Types.VENUE)
        venue_type_id = build_buy.get_current_venue(zone_data.zone_id)
        if venue_type_id is not None:
            venue_type = venue_manager.get(venue_type_id)
            if venue_type is not None:
                self.venue_type_name = venue_type.display_name
        householdProto = services.get_persistence_service().get_household_proto_buff(zone_data.household_id)
        self.household_name = householdProto.name if householdProto is not None else None

    def populate_protocol_buffer(self, lot_row_data):
        super().populate_protocol_buffer(lot_row_data.base_data, name_override=LocalizationHelperTuning.get_raw_text(self.name))
        logger.assert_raise(self.zone_id is not None, 'No zone_id passed to lot picker row', owner='nbaker')
        lot_row_data.lot_info_item.zone_id = self.zone_id
        if self.name is not None:
            lot_row_data.lot_info_item.name = self.name
        if self.world_id is not None:
            lot_row_data.lot_info_item.world_id = self.world_id
        if self.lot_template_id is not None:
            lot_row_data.lot_info_item.lot_template_id = self.lot_template_id
        if self.lot_description_id is not None:
            lot_row_data.lot_info_item.lot_description_id = self.lot_description_id
        if self.venue_type_name is not None:
            lot_row_data.lot_info_item.venue_type_name = self.venue_type_name
        if self.household_name is not None:
            lot_row_data.lot_info_item.household_name = self.household_name

    def __format__(self, fmt):
        dump_str = 'LotPickerRow(Zone id:{})'.format(self.zone_id)
        return dump_str

class UiDialogObjectPicker(UiDialogOkCancel):

    class DialogDescriptionDisplay(enum.Int):
        DEFAULT = 0
        NO_DESCRIPTION = 1
        FULL_DESCRIPTION = 2
        SINGLE_LINE_DESCRIPTION = 3

    MAX_SELECTABLE_UNLIMITED = 'unlimited'
    MAX_SELECTABLE_STATIC = 'static'
    MAX_SELECTABLE_SLOT_COUNT = 'slot_count'
    MAX_SELECTABLE_ALL_BUT_ONE = 'all_but_one'
    MAX_SELECTABLE_HOUSEHOLD_SIZE = 'household_size'
    MAX_SELECTABLE_UNUSED_PARTS = 'unused_parts'

    class _MaxSelectableUnusedParts(HasTunableSingletonFactory, AutoFactoryInit):
        FACTORY_TUNABLES = {'participant': TunableEnumEntry(description='\n                The participant we want to examine the parts of.\n                ', tunable_type=ParticipantTypeSingle, default=ParticipantTypeSingle.Object), 'parts_of_interest': TunableSet(description='\n                The set of part definitions we are interested in.\n                The value returned will be the set of these parts on the object that are unused.\n                ', tunable=TunableReference(manager=services.get_instance_manager(sims4.resources.Types.OBJECT_PART), pack_safe=True), minlength=1), 'maximum_use_count': OptionalTunable(description='\n                If set, num selectable can not exceed this amount after considering number of in-use parts.\n                ', tunable=TunableRange(tunable_type=int, default=1, minimum=1))}

        @classproperty
        def max_type(cls):
            return UiDialogObjectPicker.MAX_SELECTABLE_UNUSED_PARTS

        def get_max_selectable(self, _picker, resolver):
            participant = resolver.get_participant(self.participant)
            part_owner = participant.part_owner if participant.is_part else participant
            parts = part_owner.parts
            if parts is None:
                logger.error('{}: {} has no Parts! Verify that the tuning is correct.', self, participant)
                return 0
            available = 0
            in_use = 0
            for part in parts:
                if part.part_definition not in self.parts_of_interest:
                    pass
                elif part.in_use:
                    in_use += 1
                else:
                    available += 1
            if self.maximum_use_count is None:
                return available
            return max(self.maximum_use_count - in_use, 0)

    FACTORY_TUNABLES = {'text': OptionalTunable(description='\n            If enabled, this dialog will include text.\n            ', tunable=TunableLocalizedStringFactoryVariant(description="\n                The dialog's text.\n                "), disabled_value=NULL_LOCALIZED_STRING_FACTORY), 'max_selectable': TunableVariant(description='\n            Method of determining maximum selectable items.\n            ', static_count=TunableTuple(description='\n                static maximum selectable\n                ', number_selectable=TunableRange(description='\n                    Maximum items selectable\n                    ', tunable_type=int, default=1, minimum=1), exclude_previously_selected=Tunable(description='\n                    If True, number selectable is increased by number of\n                    pre-existing selections.\n                    ', tunable_type=bool, default=True), locked_args={'max_type': MAX_SELECTABLE_STATIC}), unlimited=TunableTuple(description='\n                Unlimited Selectable\n                ', locked_args={'max_type': MAX_SELECTABLE_UNLIMITED}), slot_based_count=TunableTuple(description='\n                maximum selectable based on empty/full slots on target\n                ', slot_type=SlotType.TunableReference(description=' \n                    A particular slot type to be tested.\n                    '), require_empty=Tunable(description='\n                    based on empty slots\n                    ', tunable_type=bool, default=True), delta=Tunable(description='\n                    offset from number of empty slots\n                    ', tunable_type=int, default=0), check_target_parent=Tunable(description="\n                    If True, will check against target object's parent of the slot.\n                    ", tunable_type=bool, default=False), check_part_owner=Tunable(description='\n                    If True, if the slot check target object is a part, we\n                    would need to check the part owner.\n                    ', tunable_type=bool, default=False), locked_args={'max_type': MAX_SELECTABLE_SLOT_COUNT}), all_but_one=TunableTuple(description='\n                The maximum number of selectable items is the number of\n                available items minus one.\n                ', locked_args={'max_type': MAX_SELECTABLE_ALL_BUT_ONE}), household_size=TunableTuple(description="\n                The maximum number of selectable items is the number of free\n                slots available in the Sim's household.\n                ", static_maximum=OptionalTunable(description='\n                    If enabled, the number of maximum selectable items is capped\n                    to this. The effective maximum could be lower if there are\n                    fewer than this many available household slots.\n                    ', tunable=TunableRange(tunable_type=int, minimum=1, default=8), disabled_value=MAX_INT16), locked_args={'max_type': MAX_SELECTABLE_HOUSEHOLD_SIZE}), unused_parts=_MaxSelectableUnusedParts.TunableFactory(), default='static_count'), 'min_selectable': TunableRange(description='\n           The minimum number of items that must be selected to treat the\n           dialog as accepted and push continuations. If 0, then multi-select\n           sim pickers will push continuations even if no items are selected.\n           ', tunable_type=int, default=1, minimum=0), 'is_sortable': Tunable(description='\n           Should list of items be presented sorted\n           ', tunable_type=bool, default=False), 'use_dropdown_filter': Tunable(description='\n           Should categories be presented in a dropdown\n           ', tunable_type=bool, default=False), 'row_description_display': TunableEnumEntry(description="\n            How to display the description.\n            \n            DEFAULT - Show the description in the default way. In some dialogs\n            (like object pickers) this will ellipsize the description if it's\n            too long.\n            \n            NO_DESCRIPTION - Don't show any description.\n            \n            FULL_DESCRIPTION - Show the full description, regardless of length.\n            In object pickers, this will cause the description field to grow\n            with the length of the description.\n            \n            SINGLE_LINE_DESCRIPTION - Only show the first line of the description\n            in the picker cell views, up to the first line break. \n            Shows the full description in a tooltip.\n            ", tunable_type=DialogDescriptionDisplay, default=DialogDescriptionDisplay.DEFAULT), 'hide_row_description': Tunable(description='\n            If set to True, we will not show the row description for this picker dialog.\n            ', tunable_type=bool, default=False)}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.picker_rows = []
        self.picked_results = []
        self.target_sim = None
        self.target = None
        self.ingredient_check = None
        self.max_selectable_num = 1

    @property
    def multi_select(self):
        return self.min_selectable < 1 or (self.max_selectable_num > 1 or self.max_selectable_num == 0)

    def add_row(self, row):
        if row is None:
            return
        if not self._validate_row(row):
            return
        if row.option_id is None:
            row.option_id = len(self.picker_rows)
        self._customize_add_row(row)
        self.picker_rows.append(row)

    def _validate_row(self, row):
        raise NotImplementedError

    def _customize_add_row(self, row):
        pass

    def set_target_sim(self, target_sim):
        self.target_sim = target_sim

    def set_target(self, target):
        self.target = target

    def pick_results(self, picked_results=[], ingredient_check=None):
        option_ids = [picker_row.option_id for picker_row in self.picker_rows]
        for result in picked_results:
            if result not in option_ids:
                logger.error('Player choose {0} out of provided {1} for dialog {2}', picked_results, option_ids, self)
                return False
        self.picked_results = picked_results
        self.ingredient_check = ingredient_check
        return True

    def get_result_rows(self):
        return [row for row in self.picker_rows if row.option_id in self.picked_results]

    def get_result_tags(self):
        return [row.tag for row in self.get_result_rows()]

    def get_single_result_tag(self):
        tags = self.get_result_tags()
        if not tags:
            return
        if len(tags) != 1:
            raise ValueError('Multiple selections not supported')
        return tags[0]

    def build_msg(self, **kwargs):
        msg = super().build_msg(**kwargs)
        msg.dialog_type = Dialog_pb2.UiDialogMessage.OBJECT_PICKER
        msg.picker_data = self.build_object_picker()
        return msg

    def _build_customize_picker(self, picker_data):
        raise NotImplementedError

    def build_object_picker(self):
        picker_data = Dialog_pb2.UiDialogPicker()
        picker_data.title = self._build_localized_string_msg(self.title)
        if self.picker_type is not None:
            picker_data.type = self.picker_type
        picker_data.min_selectable = self.min_selectable
        if isinstance(self.max_selectable, int):
            picker_data.max_selectable = self.max_selectable
        elif self.max_selectable.max_type == self.MAX_SELECTABLE_STATIC:
            max_selectable = self.max_selectable.number_selectable
            if self.max_selectable.exclude_previously_selected:
                max_selectable += sum(row.is_selected for row in self.picker_rows)
            elif max_selectable == 1 and any(row.is_selected for row in self.picker_rows):
                logger.error('attempting to use single selection dialog when there is already a selection: {}', self, owner='nbaker')
            picker_data.max_selectable = max_selectable
        elif self.max_selectable.max_type == self.MAX_SELECTABLE_SLOT_COUNT:
            if self.target is not None:
                slot_target_object = self.target if not self.max_selectable.check_target_parent else self.target.parent
                if slot_target_object is not None:
                    if self.max_selectable.check_part_owner:
                        slot_target_object = slot_target_object.part_owner
                    get_slots = slot_target_object.get_runtime_slots_gen(slot_types={self.max_selectable.slot_type}, bone_name_hash=None)
                    if slot_target_object.is_part and self.max_selectable.require_empty:
                        picker_data.max_selectable = sum(1 for slot in get_slots if slot.empty)
                    else:
                        picker_data.max_selectable = sum(1 for slot in get_slots if not slot.empty)
                    picker_data.max_selectable += self.max_selectable.delta
            else:
                logger.error('attempting to use slot based picker without a target object for dialog: {}', self, owner='nbaker')
        elif self.max_selectable.max_type == self.MAX_SELECTABLE_ALL_BUT_ONE:
            picker_data.max_selectable = max(0, len(self.picker_rows) - 1)
        elif self.max_selectable.max_type == self.MAX_SELECTABLE_HOUSEHOLD_SIZE:
            household = self.owner.household
            picker_data.max_selectable = min(self.max_selectable.static_maximum, household.free_slot_count)
        elif self.max_selectable.max_type == self.MAX_SELECTABLE_UNUSED_PARTS:
            picker_data.max_selectable = self.max_selectable.get_max_selectable(self, self._resolver)
        elif self.max_selectable.max_type == self.MAX_SELECTABLE_UNLIMITED:
            picker_data.max_selectable = 0
        picker_data.owner_sim_id = self.owner.sim_id
        if self.target_sim is not None:
            picker_data.target_sim_id = self.target_sim.sim_id
        self.max_selectable_num = picker_data.max_selectable
        picker_data.is_sortable = self.is_sortable
        picker_data.use_dropdown_filter = self.use_dropdown_filter
        picker_data.description_display = self.row_description_display
        self._build_customize_picker(picker_data)
        return picker_data

class UiRecipePicker(UiDialogObjectPicker):

    @staticmethod
    def _verify_tunable_callback(instance_class, tunable_name, source, column_sort_priorities=None, picker_columns=None, **kwargs):
        if column_sort_priorities is not None:
            length = len(picker_columns)
            if any(v >= length for v in column_sort_priorities):
                logger.error('UiRecipePicker dialog in {} has invalid column sort priority. Valid values are 0-{}', instance_class, length - 1, owner='cjiang')

    FACTORY_TUNABLES = {'skill': OptionalTunable(Skill.TunableReference(description='\n            The skill associated with the picker dialog.\n            ')), 'picker_columns': TunableList(description='\n            List of the column info\n            ', tunable=PickerColumn.TunableFactory()), 'column_sort_priorities': OptionalTunable(description='\n            If enabled, specifies column sorting.\n            ', tunable=TunableList(description='\n                The priority index for the column (column numbers are 0-based\n                index. So, if you wish to use the first column the id is 0).\n                ', tunable=int)), 'display_ingredient_check': Tunable(description='\n            If set to True, we will display the use ingredients checkbox on the\n            picker UI.\n            ', tunable_type=bool, default=True), 'verify_tunable_callback': _verify_tunable_callback}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.picker_type = ObjectPickerType.RECIPE

    def _customize_add_row(self, row):
        for picker_row in self.picker_rows:
            self._build_row_links(row, picker_row)
            self._build_row_links(picker_row, row)

    def _validate_row(self, row):
        return isinstance(row, RecipePickerRow)

    @staticmethod
    def _build_row_links(row1, row2):
        if row1.linked_recipe is not None and row1.linked_recipe is row2.tag:
            row2.linked_option_ids.append(row1.option_id)

    def _build_customize_picker(self, picker_data):
        for column in self.picker_columns:
            column_data = picker_data.recipe_picker_data.column_list.add()
            column.populate_protocol_buffer(column_data)
        if self.skill is not None:
            picker_data.recipe_picker_data.skill_id = self.skill.guid64
        if self.column_sort_priorities is not None:
            picker_data.recipe_picker_data.column_sort_list.extend(self.column_sort_priorities)
        for row in self.picker_rows:
            row_data = picker_data.recipe_picker_data.row_data.add()
            row.populate_protocol_buffer(row_data)
        picker_data.recipe_picker_data.display_ingredient_check = self.display_ingredient_check

class UiSimPicker(UiDialogObjectPicker):
    FACTORY_TUNABLES = {'column_count': TunableRange(description='\n            Define the number of columns to display in the picker dialog.\n            ', tunable_type=int, default=3, minimum=3, maximum=8), 'should_show_names': Tunable(description="\n            If true then we will show the sim's names in the picker.\n            ", tunable_type=bool, default=True)}

    def __init__(self, *args, sim_filter=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.picker_type = ObjectPickerType.SIM

    def _validate_row(self, row):
        return isinstance(row, SimPickerRow)

    def _build_customize_picker(self, picker_data):
        for row in self.picker_rows:
            row_data = picker_data.sim_picker_data.row_data.add()
            row.populate_protocol_buffer(row_data)
        picker_data.sim_picker_data.should_show_names = self.should_show_names
        picker_data.sim_picker_data.column_count = self.column_count

    def sort_selected_items_to_front(self):
        self.picker_rows.sort(key=lambda row: row.select_default, reverse=True)

class UiObjectPicker(UiDialogObjectPicker):

    class UiObjectPickerObjectPickerType(enum.Int):
        INTERACTION = ObjectPickerType.INTERACTION
        OBJECT = ObjectPickerType.OBJECT
        PIE_MENU = ObjectPickerType.PIE_MENU
        OBJECT_LARGE = ObjectPickerType.OBJECT_LARGE
        OBJECT_SQUARE = ObjectPickerType.OBJECT_SQUARE

    FACTORY_TUNABLES = {'picker_type': TunableEnumEntry(description='\n            Object picker type for the picker dialog.\n            ', tunable_type=UiObjectPickerObjectPickerType, default=UiObjectPickerObjectPickerType.OBJECT)}

    def _validate_row(self, row):
        return isinstance(row, ObjectPickerRow)

    def _build_customize_picker(self, picker_data):
        for row in self.picker_rows:
            row_data = picker_data.object_picker_data.row_data.add()
            row.populate_protocol_buffer(row_data)

class UiOddJobPicker(UiDialogObjectPicker):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.picker_type = ObjectPickerType.ODD_JOBS
        self.star_ranking = 0

    def _validate_row(self, row):
        return isinstance(row, OddJobPickerRow)

    def _build_customize_picker(self, picker_data):
        picker_data.odd_job_picker_data.star_ranking = self.star_ranking
        for row in self.picker_rows:
            row_data = picker_data.odd_job_picker_data.row_data.add()
            row.populate_protocol_buffer(row_data)

class UiCareerPicker(UiDialogObjectPicker):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.picker_type = ObjectPickerType.CAREER

    def _validate_row(self, row):
        return isinstance(row, CareerPickerRow)

    def _build_customize_picker(self, picker_data):
        for row in self.picker_rows:
            row_data = picker_data.career_picker_data.row_data.add()
            row.populate_protocol_buffer(row_data)

class UiOutfitPicker(UiDialogObjectPicker):

    class _OutftiPickerThumbnailType(enum.Int):
        SIM_INFO = 1
        MANNEQUIN = 2

    FACTORY_TUNABLES = {'thumbnail_type': TunableEnumEntry(description='\n            Define how thumbnails are to be rendered.\n            ', tunable_type=_OutftiPickerThumbnailType, default=_OutftiPickerThumbnailType.SIM_INFO), 'outfit_categories': TunableEnumSet(description='\n            The categories to display.\n            ', enum_type=OutfitCategory, default_enum_list=REGULAR_OUTFIT_CATEGORIES), 'show_filter': Tunable(description='\n            If enabled, the outfit picker has buttons to filter on the tuned\n            outfit categories.\n            ', tunable_type=bool, default=True)}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.picker_type = ObjectPickerType.OUTFIT
        self.outfit_category_filters = ()

    def _validate_row(self, row):
        return isinstance(row, OutfitPickerRow)

    def _build_customize_picker(self, picker_data):
        picker_data.outfit_picker_data.thumbnail_type = self.thumbnail_type
        picker_data.outfit_picker_data.outfit_category_filters.extend(self.outfit_category_filters)
        for row in self.picker_rows:
            row_data = picker_data.outfit_picker_data.row_data.add()
            row.populate_protocol_buffer(row_data)

class UiPurchasePicker(UiDialogObjectPicker):
    FACTORY_TUNABLES = {'categories': TunableList(description='\n            A list of categories that will be displayed in the picker.\n            ', tunable=TunableTuple(description='\n                Tuning for a single category in the picker.\n                ', tag=TunableEnumEntry(description='\n                    A single tag used for filtering items.  If an item\n                    in the picker has this tag then it will be displayed\n                    in this category.\n                    ', tunable_type=tag.Tag, default=tag.Tag.INVALID), icon=TunableResourceKey(description='\n                    Icon that represents this category.\n                    ', default=None, resource_types=sims4.resources.CompoundTypes.IMAGE), tooltip=TunableLocalizedString(description='\n                    A localized string for the tooltip of the category.\n                    ')))}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.picker_type = ObjectPickerType.PURCHASE
        self.object_id = 0
        self.inventory_object_id = 0
        self.show_description = 0
        self.mailman_purchase = False

    def _validate_row(self, row):
        return isinstance(row, PurchasePickerRow)

    def _build_customize_picker(self, picker_data):
        picker_data.shop_picker_data.object_id = self.object_id
        picker_data.shop_picker_data.inventory_object_id = self.inventory_object_id
        picker_data.shop_picker_data.show_description = self.show_description
        picker_data.shop_picker_data.mailman_purchase = self.mailman_purchase
        for category in self.categories:
            category_data = picker_data.shop_picker_data.categories.add()
            category_data.tag_type = category.tag
            build_icon_info_msg(IconInfoData(icon_resource=category.icon), None, category_data.icon_info)
            category_data.description = category.tooltip
        for row in self.picker_rows:
            row_data = picker_data.shop_picker_data.row_data.add()
            row.populate_protocol_buffer(row_data)

class UiLotPicker(UiDialogObjectPicker):

    def __init__(self, *args, lot_filter=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.picker_type = ObjectPickerType.LOT

    def _validate_row(self, row):
        return isinstance(row, LotPickerRow)

    def _build_customize_picker(self, picker_data):
        for row in self.picker_rows:
            row_data = picker_data.lot_picker_data.row_data.add()
            row.populate_protocol_buffer(row_data)

class UiItemPicker(UiDialogObjectPicker):

    def __init__(self, *args, lot_filter=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.picker_type = ObjectPickerType.ITEM

    def _validate_row(self, row):
        return isinstance(row, BasePickerRow)

    def _build_customize_picker(self, picker_data):
        for row in self.picker_rows:
            row_data = picker_data.row_picker_data.add()
            row.populate_protocol_buffer(row_data)

class UiMapViewPicker(UiDialogObjectPicker):

    class MapViewMode(enum.Int):
        TRAVEL = UI_pb2.ShowMapView.TRAVEL
        VACATION = UI_pb2.ShowMapView.VACATION
        PURCHASE = UI_pb2.ShowMapView.PURCHASE

    FACTORY_TUNABLES = {'map_view_mode': TunableVariant(description='\n            Which view mode to use for this map view picker.\n            ', travel=TunableTuple(description='\n                This picker is used for travel.\n                ', locked_args={'mode': MapViewMode.TRAVEL}), vacation=TunableTuple(description='\n                This picker is used to rent a lot for vacation.\n                ', locked_args={'mode': MapViewMode.VACATION}), purchase=TunableTuple(description='\n                This picker is used to purchase a lot. You must provide the\n                venue type that is valid to buy.\n                ', locked_args={'mode': MapViewMode.PURCHASE}, venue_to_purchase=TunableReference(description='\n                    This is the type of venue the player is actually wanting.\n                    If the player chooses a lot that is not of this venue type,\n                    it will be changed to this venue type upon purchase.\n                    ', manager=services.get_instance_manager(sims4.resources.Types.VENUE)), allowed_venues=TunableList(description='\n                    These are the venues that the map view will have available\n                    for purchase.\n                    ', tunable=TunableReference(manager=services.get_instance_manager(sims4.resources.Types.VENUE)))), default='travel')}

    def __init__(self, *args, traveling_sims=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.picker_type = ObjectPickerType.CUSTOM
        self.traveling_sims = traveling_sims

    def _validate_row(self, row):
        return isinstance(row, LotPickerRow)

    def distribute_dialog(self, _, dialog_msg, **kwargs):
        distributor_inst = Distributor.instance()
        op = distributor.shared_messages.create_message_op(dialog_msg, Consts_pb2.MSG_SHOW_MAP_VIEW)
        owner = self.owner
        if owner is not None:
            distributor_inst.add_op(owner, op)
        else:
            distributor_inst.add_op_with_no_owner(op)

    def build_msg(self, additional_tokens=(), icon_override=DEFAULT, event_id=None, **kwargs):
        msg = UI_pb2.ShowMapView()
        msg.actor_sim_id = self.owner.id
        if self.target_sim is not None:
            msg.target_sim_id = self.target_sim.id
        if self.traveling_sims is not None:
            msg.traveling_sim_ids.extend([sim.id for sim in self.traveling_sims])
        msg.lot_ids_for_travel.extend([row.zone_id for row in self.picker_rows])
        msg.dialog_id = self.dialog_id
        msg.mode = self.map_view_mode.mode
        if self.map_view_mode.mode == self.MapViewMode.PURCHASE:
            msg.purchase_venue_type = self.map_view_mode.venue_to_purchase.guid64
            msg.venue_types_allowed.extend([v.guid64 for v in self.map_view_mode.allowed_venues])
        return msg

class UiApartmentPicker(UiDialogObjectPicker):

    def __init__(self, *args, traveling_sims=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.picker_type = ObjectPickerType.CUSTOM
        self.traveling_sims = traveling_sims

    def _validate_row(self, row):
        return isinstance(row, LotPickerRow)

    def distribute_dialog(self, _, dialog_msg, **kwargs):
        distributor_inst = Distributor.instance()
        op = distributor.shared_messages.create_message_op(dialog_msg, Consts_pb2.MSG_SHOW_PLEX_VIEW)
        owner = self.owner
        if owner is not None:
            distributor_inst.add_op(owner, op)
        else:
            distributor_inst.add_op_with_no_owner(op)

    def build_msg(self, **kwargs):
        msg = UI_pb2.ShowPlexView()
        msg.actor_sim_id = self.owner.id
        if self.target_sim is not None:
            msg.target_sim_id = self.target_sim.id
        if self.traveling_sims is not None:
            msg.traveling_sim_ids.extend([sim.id for sim in self.traveling_sims])
        msg.lot_ids_for_travel.extend([row.zone_id for row in self.picker_rows])
        msg.dialog_id = self.dialog_id
        return msg

class UiDropdownPicker(UiDialogObjectPicker):

    class DropdownOptions(enum.IntFlags):
        NONE = 0
        HIDE_ICON_UNLESS_SELECTED = 1

    FACTORY_TUNABLES = {'default_item_text': TunableLocalizedStringFactory(description='\n            The text that appears in the drop down selection when no valid\n            selection is made.\n            '), 'default_item_icon': TunableIconFactory(), 'options': TunableEnumFlags(description='\n            The options to pass to the drop down picker.\n            ', enum_type=DropdownOptions, default=DropdownOptions.NONE)}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.picker_type = ObjectPickerType.DROPDOWN

    def _validate_row(self, row):
        return isinstance(row, ObjectPickerRow)

    def _build_customize_picker(self, picker_data):
        for (id, row) in enumerate(self.picker_rows):
            row_data = picker_data.dropdown_picker_data.items.add()
            row_data.text = row.name
            row_data.icon_info = create_icon_info_msg(row.icon_info)
            row_data.id = id
            if row.is_selected:
                picker_data.dropdown_picker_data.selected_item_id = id
        default_item = Dialog_pb2.UiDialogDropdownItem()
        default_item.text = self.default_item_text()
        icon_info = self.default_item_icon(None)
        default_item.icon_info = create_icon_info_msg(icon_info)
        picker_data.dropdown_picker_data.default_item = default_item
        picker_data.dropdown_picker_data.options = self.options

class TunablePickerDialogVariant(TunableVariant):

    def __init__(self, description='A tunable picker dialog variant.', available_picker_flags=ObjectPickerTuningFlags.ALL, dialog_locked_args={}, **kwargs):
        if available_picker_flags & ObjectPickerTuningFlags.SIM:
            kwargs['sim_picker'] = UiSimPicker.TunableFactory(locked_args=dialog_locked_args)
        if available_picker_flags & (ObjectPickerTuningFlags.OBJECT | ObjectPickerTuningFlags.INTERACTION | ObjectPickerTuningFlags.PIE_MENU):
            kwargs['object_picker'] = UiObjectPicker.TunableFactory(locked_args=dialog_locked_args)
        if available_picker_flags & ObjectPickerTuningFlags.CAREER:
            kwargs['career_picker'] = UiCareerPicker.TunableFactory(locked_args=dialog_locked_args)
        if available_picker_flags & ObjectPickerTuningFlags.OUTFIT:
            kwargs['outfit_picker'] = UiOutfitPicker.TunableFactory(locked_args=dialog_locked_args)
        if available_picker_flags & ObjectPickerTuningFlags.RECIPE:
            kwargs['recipe_picker'] = UiRecipePicker.TunableFactory(locked_args=dialog_locked_args)
        if available_picker_flags & ObjectPickerTuningFlags.PURCHASE:
            kwargs['purchase_picker'] = UiPurchasePicker.TunableFactory(locked_args=dialog_locked_args)
        if available_picker_flags & ObjectPickerTuningFlags.LOT:
            kwargs['lot_picker'] = UiLotPicker.TunableFactory(locked_args=dialog_locked_args)
        if available_picker_flags & ObjectPickerTuningFlags.MAP_VIEW:
            kwargs['map_view_picker'] = UiMapViewPicker.TunableFactory(locked_args=dialog_locked_args)
        if available_picker_flags & ObjectPickerTuningFlags.ITEM:
            kwargs['item_picker'] = UiItemPicker.TunableFactory(locked_args=dialog_locked_args)
        if available_picker_flags & ObjectPickerTuningFlags.DROPDOWN:
            kwargs['dropdown'] = UiDropdownPicker.TunableFactory(locked_args=dialog_locked_args)
        super().__init__(description=description, **kwargs)
(TunableUiOutfitPickerReference, TunableUiOutfitPickerSnippet) = define_snippet('OutfitPicker', UiOutfitPicker.TunableFactory())