from autonomy.autonomy_modifier import TunableAutonomyModifierfrom objects.components.inventory_enums import InventoryType, ObjectShareabilityfrom sims4.tuning.tunable import TunableMapping, TunableTuple, Tunable, TunableRange, OptionalTunable, TunableEnumEntry, TunableListfrom statistics.tunable import CommodityDecayModifierMappingimport servicesimport sims4.loglogger = sims4.log.Logger('InventoryTypeTuning')
class InventoryTypeTuning:
    INVENTORY_TYPE_DATA = TunableMapping(description='\n        A mapping of Inventory Type to any static information required by the\n        client to display inventory data as well information about allowances\n        for each InventoryType.\n        ', key_type=InventoryType, value_type=TunableTuple(description='\n            Any information required by the client to display inventory data.\n            ', skip_carry_pose_allowed=Tunable(description='\n                If checked, an object tuned to be put away in this inventory\n                type will be allowed to skip the carry pose.  If unchecked, it\n                will not be allowed to skip the carry pose.\n                ', tunable_type=bool, default=False), put_away_allowed=Tunable(description='\n                If checked, objects can be manually "put away" in this\n                inventory type. If unchecked, objects cannot be manually "put\n                away" in this inventory type.\n                ', tunable_type=bool, default=True), shared_between_objects=TunableEnumEntry(description='\n                If shareable, this inventory will be shared between all objects\n                that have it. For example, if you put an item in one fridge,\n                you would be able to remove it from a different fridge on the\n                lot.', tunable_type=ObjectShareability, default=ObjectShareability.SHARED), max_inventory_size=OptionalTunable(tunable=TunableRange(description='\n                    Max number of items inventory type can have\n                    ', tunable_type=int, default=sims4.math.MAX_INT32, minimum=1, maximum=sims4.math.MAX_INT32), disabled_name='unbounded', enabled_name='fixed_size')))
    GAMEPLAY_MODIFIERS = TunableMapping(description="\n        A mapping of Inventory Type to the gameplay effects they provide. If an\n        inventory does not affect contained objects, it is fine to leave that\n        inventory's type out of this mapping.\n        ", key_type=InventoryType, value_type=TunableTuple(description='\n            Gameplay modifiers.\n            ', decay_modifiers=CommodityDecayModifierMapping(description='\n                Multiply the decay rate of specific commodities by a tunable\n                integer in order to speed up or slow down decay while the\n                object is contained within this inventory. This modifier will\n                be multiplied with other modifiers on the object, if it has\n                any.\n                '), autonomy_modifiers=TunableList(description='\n                Objects in the inventory of this object will have these\n                autonomy modifiers applied to them.\n                ', tunable=TunableAutonomyModifier(description='\n                    Autonomy modifiers for objects that are placed in this\n                    inventory type.\n                    ', locked_args={'relationship_multipliers': None}))))

    @classmethod
    def _verify_tuning_callback(cls):
        for inventory_type in set(InventoryType) - set(cls.INVENTORY_TYPE_DATA.keys()):
            logger.error('Inventory type {} has no tuned inventory type data. This can be fixed in the tuning for objects.components.inventory_enum.tuning -> InventoryTypeTuning -> Inventory Type Data.', inventory_type.name, owner='bhill')

    @staticmethod
    def get_inventory_type_data_tuning(inventory_type):
        return InventoryTypeTuning.INVENTORY_TYPE_DATA.get(inventory_type)

    @staticmethod
    def get_gameplay_effects_tuning(inventory_type):
        return InventoryTypeTuning.GAMEPLAY_MODIFIERS.get(inventory_type)

    @staticmethod
    def is_shared_between_objects(inventory_type):
        tuning = InventoryTypeTuning.get_inventory_type_data_tuning(inventory_type)
        if tuning is None or tuning.shared_between_objects == ObjectShareability.SHARED:
            return True
        if tuning.shared_between_objects == ObjectShareability.NOT_SHARED:
            return False
        elif tuning.shared_between_objects == ObjectShareability.SHARED_IF_NOT_IN_APARTMENT:
            return not services.get_plex_service().is_zone_an_apartment(services.current_zone_id(), consider_penthouse_an_apartment=False)
        return True

    @staticmethod
    def is_put_away_allowed_on_inventory_type(inventory_type):
        tuning = InventoryTypeTuning.get_inventory_type_data_tuning(inventory_type)
        return tuning is None or tuning.put_away_allowed

    @staticmethod
    def get_max_inventory_size_for_inventory_type(inventory_type):
        tuning = InventoryTypeTuning.get_inventory_type_data_tuning(inventory_type)
        if tuning is None:
            return sims4.math.MAX_UINT32
        return tuning.max_inventory_size
