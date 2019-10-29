from animation.posture_manifest import AnimationParticipantfrom event_testing.resolver import DoubleObjectResolverfrom objects.components import componentmethod, typesfrom objects.components.get_put_component_mixin import GetPutComponentMixinfrom objects.components.inventory import InventoryComponentfrom objects.components.inventory_enums import InventoryTypefrom objects.components.inventory_item_trigger import ItemStateTriggerfrom objects.components.inventory_owner_tuning import InventoryTuningfrom objects.object_enums import ItemLocation, ResetReasonfrom objects.system import create_objectfrom postures.posture_specs import PostureSpecVariablefrom sims4.tuning.tunable import TunableList, TunableReference, TunableEnumEntry, Tunable, OptionalTunable, TunableTuplefrom statistics.statistic import Statisticimport servicesimport sims4.resourceslogger = sims4.log.Logger('Inventory', default_owner='tingyul')
class ObjectInventoryComponent(GetPutComponentMixin, InventoryComponent, component_name=types.INVENTORY_COMPONENT):
    DEFAULT_OBJECT_INVENTORY_AFFORDANCES = TunableList(TunableReference(description='\n            Affordances for all object inventories.\n            ', manager=services.get_instance_manager(sims4.resources.Types.INTERACTION)))
    FACTORY_TUNABLES = {'description': '\n            Generate an object inventory for this object\n            ', 'inventory_type': TunableEnumEntry(description='\n            Inventory Type must be set for the object type you add this for.\n            ', tunable_type=InventoryType, default=InventoryType.UNDEFINED, invalid_enums=(InventoryType.UNDEFINED, InventoryType.SIM)), 'visible': Tunable(description='\n            If this inventory is visible to player.', tunable_type=bool, default=True), 'starting_objects': TunableList(description='\n            Objects in this list automatically populate the inventory when its\n            owner is created. Currently, to keep the game object count down, an\n            object will not be added if the object inventory already has\n            another object of the same type.', tunable=TunableReference(manager=services.definition_manager(), description='Objects to populate inventory with.', pack_safe=True)), 'purchasable_objects': OptionalTunable(description='\n            If this list is enabled, an interaction to buy the purchasable\n            objects through a dialog picker will show on the inventory object.\n            \n            Example usage: a list of books for the bookshelf inventory.\n            ', tunable=TunableTuple(show_description=Tunable(description='\n                    Toggles whether the object description should show in the \n                    purchase picker.\n                    ', tunable_type=bool, default=False), objects=TunableList(description='\n                    A list of object definitions that can be purchased.\n                    ', tunable=TunableReference(manager=services.definition_manager(), description='')))), 'score_contained_objects_for_autonomy': Tunable(description='\n            Whether or not to score for autonomy any objects contained in this object.', tunable_type=bool, default=True), 'item_state_triggers': TunableList(description="\n            The state triggers to modify inventory owner's state value based on\n            inventory items states.\n            ", tunable=ItemStateTrigger.TunableFactory()), 'allow_putdown_in_inventory': Tunable(description="\n            This inventory allows Sims to put objects away into it, such as books\n            or other carryables. Ex: mailbox has an inventory but we don't want\n            Sims putting away items in the inventory.", tunable_type=bool, default=True), 'test_set': OptionalTunable(description='\n            If enabled, the ability to pick up items from and put items in this\n            object is gated by this test.\n            ', tunable=TunableReference(manager=services.get_instance_manager(sims4.resources.Types.SNIPPET), class_restrictions=('TestSetInstance',))), 'count_statistic': OptionalTunable(description='\n            A statistic whose value will be the number of objects in this\n            inventory. It will automatically be added to the object owning this\n            type of component.\n            ', tunable=Statistic.TunableReference()), 'return_owned_objects': Tunable(description="\n            If enabled, inventory objects will return to their household\n            owner's inventory when this object is destroyed off lot. This is\n            because build buy can undo actions on lot and cause object id\n            collisions.\n            \n            We first consider the closest instanced Sims, and finally move to\n            the household inventory if we can't move to a Sim's inventory.\n            ", tunable_type=bool, default=False), '_use_top_item_tooltip': Tunable(description="\n            If checked, this inventory would use the top item's tooltip as its\n            own tooltip. \n            ", tunable_type=bool, default=False)}

    def __init__(self, owner, inventory_type, visible, starting_objects, purchasable_objects, score_contained_objects_for_autonomy, item_state_triggers, allow_putdown_in_inventory, test_set, count_statistic, return_owned_objects, _use_top_item_tooltip, **kwargs):
        super().__init__(owner, **kwargs)
        self._inventory_type = inventory_type
        self.visible = visible
        self.starting_objects = starting_objects
        self.purchasable_objects = purchasable_objects
        self.score_contained_objects_for_autonomy = score_contained_objects_for_autonomy
        self.item_state_triggers = item_state_triggers
        self.allow_putdown_in_inventory = allow_putdown_in_inventory
        self.test_set = test_set
        self.count_statistic = count_statistic
        self.return_owned_objects = return_owned_objects
        self._use_top_item_tooltip = _use_top_item_tooltip

    @property
    def inventory_type(self):
        return self._inventory_type

    @property
    def default_item_location(self):
        return ItemLocation.OBJECT_INVENTORY

    @componentmethod
    def get_inventory_access_constraint(self, sim, is_put, carry_target, use_owner_as_target_for_resolver=False):
        if use_owner_as_target_for_resolver:

            def constraint_resolver(animation_participant, default=None):
                if animation_participant in (AnimationParticipant.SURFACE, PostureSpecVariable.SURFACE_TARGET, AnimationParticipant.TARGET, PostureSpecVariable.INTERACTION_TARGET):
                    return self.owner
                return default

        else:
            constraint_resolver = None
        return self._get_access_constraint(sim, is_put, carry_target, resolver=constraint_resolver)

    @componentmethod
    def get_inventory_access_animation(self, *args, **kwargs):
        return self._get_access_animation(*args, **kwargs)

    @property
    def should_score_contained_objects_for_autonomy(self):
        return self.score_contained_objects_for_autonomy

    @property
    def use_top_item_tooltip(self):
        return self._use_top_item_tooltip

    def _get_inventory_count_statistic(self):
        return self.count_statistic

    def on_add(self):
        for trigger in self.item_state_triggers:
            self.add_state_trigger(trigger(self))
        super().on_add()

    def on_reset_component_get_interdependent_reset_records(self, reset_reason, reset_records):
        if not self.owner.is_on_active_lot():
            household_manager = services.household_manager()
            objects_to_transfer = list(iter(self))
            for obj in objects_to_transfer:
                household_id = obj.get_household_owner_id()
                if household_id is not None:
                    household = household_manager.get(household_id)
                    if household is not None:
                        household.move_object_to_sim_or_household_inventory(obj)
        super().on_reset_component_get_interdependent_reset_records(reset_reason, reset_records)

    def on_post_bb_fixup(self):
        self._add_starting_objects()

    def _add_starting_objects(self):
        for definition in self.starting_objects:
            if self.has_item_with_definition(definition):
                pass
            else:
                new_object = create_object(definition, loc_type=ItemLocation.OBJECT_INVENTORY)
                if new_object is None:
                    logger.error('Failed to create object {}', definition)
                else:
                    new_object.set_household_owner_id(self.owner.get_household_owner_id())
                    if not self.player_try_add_object(new_object):
                        logger.error('Failed to add object {} to inventory {}', new_object, self)
                        new_object.destroy(source=self.owner, cause='Failed to add starting object to inventory.')

    def component_interactable_gen(self):
        yield self

    def component_super_affordances_gen(self, **kwargs):
        if self.visible:
            for affordance in self.DEFAULT_OBJECT_INVENTORY_AFFORDANCES:
                yield affordance

    def _can_access(self, sim):
        if self.test_set is not None:
            resolver = DoubleObjectResolver(sim, self.owner)
            result = self.test_set(resolver)
            if not result:
                return False
        return True

    @componentmethod
    def can_access_for_pickup(self, sim):
        if not self._can_access(sim):
            return False
        elif any(self.owner.state_value_active(value) for value in InventoryTuning.INVALID_ACCESS_STATES):
            return False
        return True

    @componentmethod
    def can_access_for_putdown(self, sim):
        if not self.allow_putdown_in_inventory:
            return False
        elif not self._can_access(sim):
            return False
        return True
