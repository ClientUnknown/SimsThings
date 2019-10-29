from protocolbuffers import Consts_pb2, Business_pb2from business.business_enums import BusinessTypefrom business.business_manager import BusinessManagerfrom retail.retail_summary_dialog import RetailSummaryDialogfrom retail.retail_tuning import RetailTuningfrom retail.retail_utils import RetailUtilsfrom sims.outfits.outfit_enums import OutfitCategoryfrom sims4.tuning.tunable import TunableEnumEntry, TunableListfrom statistics.commodity import Commodityfrom ui.ui_dialog_notification import TunableUiDialogNotificationSnippetfrom vfx import PlayEffectimport servicesimport sims4.logimport taglogger = sims4.log.Logger('Retail', default_owner='trevor')
class RetailManager(BusinessManager):
    NPC_STORE_FOR_SALE_TAG = TunableEnumEntry(description='\n        Objects with this tag will be set For Sale when an NPC store is\n        visited.\n        ', tunable_type=tag.Tag, default=tag.Tag.INVALID, pack_safe=True)
    NPC_STORE_MANNEQUIN_TAG = TunableEnumEntry(description='\n        Objects with this tag will have their mannequin component outfits\n        restocked any time a premade NPC store is visited.\n        ', tunable_type=tag.Tag, default=tag.Tag.INVALID, pack_safe=True)
    FOR_SALE_VFX = PlayEffect.TunableFactory(description='\n        An effect that can be toggled on/off for all objects marked for sale.\n        ')
    ITEMS_SENT_TO_HH_INVENTORY_NOTIFICATION = TunableUiDialogNotificationSnippet(description="\n            The notification that shows up when items are sent to the household's\n            inventory because the item that these things are slotted to are\n            sold.\n            ")
    NPC_STORE_ITEM_COMMODITIES_TO_MAX_ON_OPEN = TunableList(description='\n        A list of commodities that should get maxed out on retail objects\n        when an NPC store opens.\n        ', tunable=Commodity.TunableReference(description='\n            The commodity to max out.\n            ', pack_safe=True))

    def __init__(self):
        super().__init__(BusinessType.RETAIL)
        self._objs_with_for_sale_vfx = {}
        self._for_sale_vfx_toggle_value = False

    def on_client_disconnect(self):
        self.remove_for_sale_vfx_from_all_objects()

    def set_advertising_type(self, advertising_type):
        commodity = RetailTuning.ADVERTISING_COMMODITY_MAP.get(advertising_type, None)
        if commodity is not None:
            tracker = services.active_lot().commodity_tracker
            tracker.remove_statistic(commodity)
            tracker.add_statistic(commodity)

    def get_advertising_type_for_gsi(self):
        if services.current_zone_id() == self._zone_id:
            tracker = services.active_lot().commodity_tracker
            commodities = RetailTuning.ADVERTISING_COMMODITY_MAP.values()
            return str([(c, tracker.get_value(c)) for c in commodities if tracker.has_statistic(c)])
        else:
            return ''

    def get_curb_appeal(self):
        total_curb_appeal = sum(obj.retail_component.get_current_curb_appeal() for obj in RetailUtils.get_all_retail_objects())
        return total_curb_appeal + self._get_lot_advertising_commodity_sum()

    def _get_lot_advertising_commodity_sum(self):
        return sum(self._get_lot_advertising_commodity_values())

    def _get_lot_advertising_commodity_values(self):
        tracker = services.active_lot().commodity_tracker
        commodities = RetailTuning.ADVERTISING_COMMODITY_MAP.values()
        return [tracker.get_value(c) for c in commodities if tracker.has_statistic(c)]

    def _fixup_placard_if_necessary(self, obj):
        obj_retail_component = obj.retail_component
        if obj_retail_component is not None and obj_retail_component.is_sold:
            obj_retail_component._change_to_placard(play_vfx=False)

    def should_automatically_close(self):
        return self.is_owner_household_active and (self._zone_id is not None and self._zone_id != services.current_zone_id())

    def _should_make_customer(self, sim_info):
        return False

    def on_protocols_loaded(self):
        self._employee_manager.reload_employee_uniforms()

    def refresh_for_sale_vfx_for_object(self, obj):
        if obj.retail_component is None:
            logger.error('Attempting to toggle for sale vfx on an object {} with no retail component.', obj, owner='tastle')
            return
        show_vfx = self._for_sale_vfx_toggle_value if obj.retail_component.is_for_sale else False
        self._update_for_sale_vfx_for_object(obj, show_vfx)

    def _update_for_sale_vfx_for_object(self, obj, toggle_value):
        if obj not in self._objs_with_for_sale_vfx and toggle_value:
            self._objs_with_for_sale_vfx[obj] = self.FOR_SALE_VFX(obj)
            self._objs_with_for_sale_vfx[obj].start()
        elif obj in self._objs_with_for_sale_vfx and not toggle_value:
            obj_vfx = self._objs_with_for_sale_vfx.pop(obj)
            obj_vfx.stop()

    def remove_for_sale_vfx_from_all_objects(self):
        self._for_sale_vfx_toggle_value = False
        for obj_vfx in self._objs_with_for_sale_vfx.values():
            obj_vfx.stop()
        self._objs_with_for_sale_vfx.clear()

    def toggle_for_sale_vfx(self):
        self._for_sale_vfx_toggle_value = not self._for_sale_vfx_toggle_value
        for item in RetailUtils.all_retail_objects_gen(allow_sold=False, include_inventories=False):
            self._update_for_sale_vfx_for_object(item, self._for_sale_vfx_toggle_value)

    def update_retail_objects_commodities(self):
        for retail_obj in RetailUtils.all_retail_objects_gen(allow_sold=False):
            retail_obj.update_component_commodity_flags()

    def _open_business(self):
        super()._open_business()
        if self._owner_household_id is not None:
            self.update_retail_objects_commodities()

    def _close_business(self, play_sound=True):
        if not self._is_open:
            return
        super()._close_business(play_sound)
        if self._owner_household_id is not None:
            self.update_retail_objects_commodities()

    def get_median_item_value(self):
        values = [obj.retail_component.get_retail_value() for obj in RetailUtils.all_retail_objects_gen()]
        if not values:
            return 0
        values.sort()
        count = len(values)
        midpoint = count//2
        if count % 2:
            return values[midpoint]
        return (values[midpoint] + values[midpoint - 1])/2

    def should_show_no_way_to_make_money_notification(self):
        return not self.has_any_object_for_sale()

    def has_any_object_for_sale(self):
        for retail_obj in RetailUtils.all_retail_objects_gen(allow_not_for_sale=True):
            if retail_obj.retail_component.is_for_sale:
                return True
            if retail_obj.is_in_inventory():
                return True
        return False

    def on_zone_load(self):
        super().on_zone_load()
        for obj in RetailUtils.get_all_retail_objects():
            self._fixup_placard_if_necessary(obj)
        if services.current_zone_id() != self._zone_id:
            return
        tracker = services.active_lot().commodity_tracker
        advertising_commodities = RetailTuning.ADVERTISING_COMMODITY_MAP.values()
        for advertising_commodity in advertising_commodities:
            commodity = tracker.get_statistic(advertising_commodity)
            if commodity is not None:
                commodity.decay_enabled = True

    def _open_pure_npc_store(self, is_premade):
        has_retail_obj = False
        for retail_obj in RetailUtils.all_retail_objects_gen(allow_not_for_sale=True):
            self._adjust_commodities_if_necessary(retail_obj)
            obj_retail_component = retail_obj.retail_component
            if obj_retail_component.is_for_sale or retail_obj.is_in_inventory():
                has_retail_obj = True
            else:
                if is_premade:
                    set_for_sale = retail_obj.has_tag(self.NPC_STORE_FOR_SALE_TAG)
                else:
                    set_for_sale = obj_retail_component.is_sold
                if set_for_sale:
                    obj_retail_component.set_for_sale()
                    has_retail_obj = True
                if retail_obj.has_tag(self.NPC_STORE_MANNEQUIN_TAG):
                    self._set_up_mannequin_during_open(retail_obj)
                    has_retail_obj = True
        self.set_open(has_retail_obj)

    @classmethod
    def _set_up_mannequin_during_open(cls, mannequin):
        (current_outfit_type, _) = mannequin.get_current_outfit()
        if current_outfit_type == OutfitCategory.BATHING:
            mannequin.set_current_outfit(mannequin.get_previous_outfit())

    def _open_household_owned_npc_store(self):
        should_open = False
        for retail_obj in RetailUtils.all_retail_objects_gen(allow_not_for_sale=True):
            self._adjust_commodities_if_necessary(retail_obj)
            if should_open or not retail_obj.retail_component.is_not_for_sale:
                should_open = True
        self.set_open(should_open)

    @classmethod
    def _adjust_commodities_if_necessary(cls, obj):
        for obj_commodity in cls.NPC_STORE_ITEM_COMMODITIES_TO_MAX_ON_OPEN:
            tracker = obj.get_tracker(obj_commodity)
            if tracker is not None and tracker.has_statistic(obj_commodity):
                tracker.set_max(obj_commodity)

    def show_summary_dialog(self, is_from_close=False):
        RetailSummaryDialog.show_dialog(self, is_from_close=is_from_close)

    def construct_business_message(self, msg):
        super().construct_business_message(msg)
        msg.retail_data = Business_pb2.RetailBusinessDataUpdate()

    def get_lot_name(self):
        zone_data = services.get_persistence_service().get_zone_proto_buff(self._zone_id)
        if zone_data is None:
            return ''
        return zone_data.name
