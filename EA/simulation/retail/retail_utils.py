from objects.components.inventory_enums import InventoryTypefrom objects.components.inventory_type_tuning import InventoryTypeTuningfrom sims4.tuning.tunable import TunableEnumWithFilter, TunableList, TunableEnumEntryimport objects.components.typesimport servicesimport tag
class RetailUtils:
    RETAIL_CUSTOMER_SITUATION_TAG = TunableEnumWithFilter(description='\n        The tag associated with customer situations.\n        ', tunable_type=tag.Tag, default=tag.Tag.INVALID, filter_prefixes=['situation'], pack_safe=True)
    RETAIL_EMPLOYEE_SITUATION_TAG = TunableEnumWithFilter(description='\n        The tag associated with employee situations.\n        ', tunable_type=tag.Tag, default=tag.Tag.INVALID, filter_prefixes=['situation'], pack_safe=True)
    RETAIL_INVENTORY_TYPES = TunableList(description='\n        A reference to the inventory types of retail inventories. If a retail\n        item gets put into any inventory type in this list, it will\n        automatically be marked for sale.\n        ', tunable=TunableEnumEntry(description='\n            The inventory type.\n            ', tunable_type=InventoryType, default=InventoryType.UNDEFINED, pack_safe=True))

    @classmethod
    def all_retail_objects_gen(cls, allow_for_sale=True, allow_sold=True, allow_not_for_sale=False, include_inventories=True):
        business_manager = services.business_service().get_business_manager_for_zone()
        if business_manager is None:
            return
        lot_owner_household_id = cls._get_lot_owner_household_id()
        accessed_shared_inventories = []
        for obj in services.object_manager().valid_objects():
            if not obj.is_on_active_lot():
                pass
            elif not cls._is_obj_owned_by_lot_owner(obj, lot_owner_household_id):
                pass
            else:
                if not obj.has_component(objects.components.types.RETAIL_COMPONENT) or (not allow_for_sale or obj.retail_component.is_for_sale or (not allow_sold or obj.retail_component.is_sold or not allow_not_for_sale)) or obj.retail_component.is_not_for_sale:
                    yield obj
                if allow_for_sale and include_inventories and obj.has_component(objects.components.types.INVENTORY_COMPONENT):
                    inventory_type = obj.inventory_component.inventory_type
                    if inventory_type in RetailUtils.RETAIL_INVENTORY_TYPES:
                        if InventoryTypeTuning.is_shared_between_objects(inventory_type):
                            if inventory_type in accessed_shared_inventories:
                                pass
                            else:
                                accessed_shared_inventories.append(inventory_type)
                        for inventory_obj in obj.inventory_component:
                            if inventory_obj.has_component(objects.components.types.RETAIL_COMPONENT):
                                yield inventory_obj

    @classmethod
    def get_all_retail_objects(cls):
        retail_manager = services.business_service().get_retail_manager_for_zone()
        if retail_manager is None:
            return set()
        lot_owner_household_id = cls._get_lot_owner_household_id()
        output_set = set()
        for obj in services.object_manager().valid_objects():
            if not obj.is_on_active_lot():
                pass
            elif not cls._is_obj_owned_by_lot_owner(obj, lot_owner_household_id):
                pass
            else:
                if obj.has_component(objects.components.types.RETAIL_COMPONENT):
                    output_set.add(obj)
                if obj.has_component(objects.components.types.INVENTORY_COMPONENT) and obj.inventory_component.inventory_type in RetailUtils.RETAIL_INVENTORY_TYPES:
                    output_set |= set(obj.inventory_component)
        return output_set

    @classmethod
    def get_retail_customer_situation_from_sim(cls, sim):
        situation_manager = services.get_zone_situation_manager()
        for situation in situation_manager.get_situations_sim_is_in_by_tag(sim, cls.RETAIL_CUSTOMER_SITUATION_TAG):
            return situation

    @classmethod
    def get_retail_employee_situation_from_sim(cls, sim):
        situation_manager = services.get_zone_situation_manager()
        for situation in situation_manager.get_situations_sim_is_in_by_tag(sim, cls.RETAIL_EMPLOYEE_SITUATION_TAG):
            return situation

    @classmethod
    def _get_lot_owner_household_id(cls):
        zone_data = services.get_persistence_service().get_zone_proto_buff(services.current_zone_id())
        if zone_data is not None:
            return zone_data.household_id
        return 0

    @classmethod
    def _is_obj_owned_by_lot_owner(cls, obj, lot_owner_household_id):
        obj_household_owner_id = obj.get_household_owner_id() or 0
        return lot_owner_household_id == obj_household_owner_id
