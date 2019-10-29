from protocolbuffers import InteractionOps_pb2 as interaction_protocol, SimObjectAttributes_pb2from autonomy.autonomy_modifier import TunableAutonomyModifierfrom objects.components import Component, types, ComponentPriorityfrom objects.components.state import TunableStateValueReference, StateComponent, ObjectStateValuefrom objects.slots import SlotTypefrom retail.retail_utils import RetailUtilsfrom sims4.common import Packfrom sims4.tuning.tunable import HasTunableFactory, AutoFactoryInit, OptionalTunable, TunableTuple, Tunable, TunableReference, TunableList, TunablePackSafeReference, TunableSet, TunableMapping, HasTunableSingletonFactoryfrom sims4.utils import classpropertyfrom snippets import define_snippetfrom vfx import PlayEffectimport build_buyimport servicesimport sims4.resourceslogger = sims4.log.Logger('Retail', default_owner='trevor')
class RetailCurbAppeal(HasTunableSingletonFactory, AutoFactoryInit):
    FACTORY_TUNABLES = {'base_curb_appeal': Tunable(description='\n            The amount of curb appeal this object should add just for being on\n            the retail lot. Curb appeal affects the number of customers the\n            store draws in. Sim counts can be tuned in the Retail Customer\n            tuning.\n            ', tunable_type=float, default=1), 'state_based_curb_appeal': TunableMapping(description='\n            A mapping of states and the amount of curb appeal to add/subtract\n            when the object is in that state. When an object changes out of\n            these states, the curb appeal will be reverted back.\n            ', key_type=ObjectStateValue.TunableReference(description='\n                The object state the retail object should be in for the \n                ', pack_safe=True), key_name='Retail_Object_State', value_type=Tunable(description='\n                The curb appeal to apply to the retail lot when the object\n                is in the specified state.\n                ', tunable_type=float, default=1), value_name='Curb_Appeal_Adjustmnet')}

class RetailComponent(Component, HasTunableFactory, AutoFactoryInit, component_name=types.RETAIL_COMPONENT, persistence_priority=ComponentPriority.PRIORITY_RETAIL, persistence_key=SimObjectAttributes_pb2.PersistenceMaster.PersistableData.RetailComponent):
    FACTORY_TUNABLES = {'sellable': OptionalTunable(description='\n            If enabled, this object can be sold on a retail lot.\n            ', disabled_name='Not_For_Sale', enabled_by_default=True, tunable=TunableTuple(description='\n                The data associated with selling this item.\n                ', placard_override=OptionalTunable(description='\n                    If enabled, we will only use this placard when this object\n                    is sold. If disabled, the game will attempt to smartly\n                    choose a placard.\n                    ', tunable=TunableTuple(description='\n                        The placard and vfx to use for this object.\n                        ', model=TunablePackSafeReference(description='\n                            The placard to use when this object is sold.\n                            ', manager=services.definition_manager()), vfx=PlayEffect.TunableFactory(description='\n                            The effect to play when the object is sold.\n                            '))), for_sale_extra_affordances=TunableList(description="\n                    When this object is marked For Sale, these are the extra\n                    interactions that will still be available. For instance, a\n                    debug interaction to sell the object could go here or you\n                    may want Sit to still be on chairs so customers can try\n                    them out. You may also want Clean on anything that can get\n                    dirty so employees can clean them.\n                    \n                    Note: These interactions are specific to this object. Do not\n                    add interactions that don't make sense for this object.\n                    ", tunable=TunableReference(description='\n                        The affordance to be left available on the object.\n                        ', manager=services.get_instance_manager(sims4.resources.Types.INTERACTION), pack_safe=True)), buy_affordance=TunablePackSafeReference(description='\n                    The affordance a Sim will run to buy retail objects. This\n                    affordance should handle destroying the object and adding\n                    the money to the retail funds.\n                    ', manager=services.get_instance_manager(sims4.resources.Types.INTERACTION)), restock_affordances=TunableList(description='\n                    The affordances a Sim will run to restock retail objects.\n                    ', tunable=TunableReference(manager=services.get_instance_manager(sims4.resources.Types.INTERACTION), pack_safe=True)), clear_placard_affordance=TunablePackSafeReference(description='\n                    The affordance a Sim will run to remove a placard from the lot.\n                    ', manager=services.get_instance_manager(sims4.resources.Types.INTERACTION), allow_none=True), browse_affordance=TunablePackSafeReference(description='\n                    The affordance a Sim will run to browse retail objects.\n                    ', manager=services.get_instance_manager(sims4.resources.Types.INTERACTION)), set_for_sale_affordance=TunablePackSafeReference(description='\n                    The affordance a Sim will run to set a retail object as For\n                    Sale.\n                    ', manager=services.get_instance_manager(sims4.resources.Types.INTERACTION), allow_none=True), set_not_for_sale_affordance=TunablePackSafeReference(description='\n                    The affordance a Sim will run to set a retail object as Not\n                    For Sale.\n                    ', manager=services.get_instance_manager(sims4.resources.Types.INTERACTION), allow_none=True), allowed_occupied_slots_for_sellable=TunableSet(description='\n                    By default, an object will become unsellable if anything is\n                    parented to it. This is to prevent awkward scenarios such\n                    as selling a counter with a sink is parented, leaving the\n                    sink floating in mid-air. However, some slots on objects\n                    are okay occupied, e.g. a table should still be sellable if\n                    chairs are parented. Adding those slots to this set (e.g.\n                    slot_SitChair on tables) will allow this object to remain\n                    sellable even if those slots are occupied.\n                    ', tunable=SlotType.TunableReference()))), 'advertises': OptionalTunable(description='\n            If enabled, this object will contribute to the curb appeal for the\n            retail lot on which it is placed. Curb appeal affects foot traffic\n            for the store as well as the type of clientele.\n            ', disabled_name='Does_Not_Advertise', enabled_by_default=True, tunable=RetailCurbAppeal.TunableFactory())}
    NOT_FOR_SALE_STATE = TunableStateValueReference(description='\n        The state value that represents and object, on a retail lot, that is\n        not for sale at all. Objects in this state should function like normal.\n        ', pack_safe=True)
    FOR_SALE_STATE = TunableStateValueReference(description='\n        The state value that represents an object that is valid for sale on a\n        retail lot. This is the state that will be tested in order to show sale\n        interactions.\n        ', pack_safe=True)
    SOLD_STATE = TunableStateValueReference(description="\n        The state value that represents an object that is no longer valid for\n        sale on a retail lot. This is the state that will be set on the object\n        when it's sold and in its Placard form.\n        ", pack_safe=True)
    DEFAULT_SALE_STATE = TunableStateValueReference(description='\n        This is the default for sale state for an object. When it is given a\n        retail component for this first time, this is what the For Sale state\n        will be set to.\n        ', pack_safe=True)
    SET_FOR_SALE_VFX = PlayEffect.TunableFactory(description='\n        An effect that will play on an object when it gets set for sale.\n        ')
    SET_NOT_FOR_SALE_VFX = PlayEffect.TunableFactory(description='\n        An effect that will play on an object when it gets set not for sale.\n        ')
    PLACARD_FLOOR = TunableTuple(description='\n        The placard to use, and vfx to show, for objects that were on the floor\n        when sold.\n        ', model=TunableReference(description='\n            The placard to use when the object is sold.\n            ', manager=services.definition_manager(), pack_safe=True), vfx=PlayEffect.TunableFactory(description='\n            The effect to play when the object is sold.\n            '))
    PLACARD_SURFACE = TunableTuple(description='\n        The placard to use, and vfx to show, for objects that were on a surface\n        when sold.\n        ', model=TunableReference(description='\n            The placard to use when the object is sold.\n            ', manager=services.definition_manager(), pack_safe=True), vfx=PlayEffect.TunableFactory(description='\n            The effect to play when the object is sold.\n            '))
    PLACARD_WALL = TunableTuple(description='\n        The placard to use, and vfx to show, for objects that were on the wall\n        when sold.\n        ', model=TunableReference(description='\n            The placard to use when the object is sold.\n            ', manager=services.definition_manager(), pack_safe=True), vfx=PlayEffect.TunableFactory(description='\n            The effect to play when the object is sold.\n            '))
    PLACARD_CEILING = TunableTuple(description='\n        The placard to use, and vfx to show, for objects that were on the\n        ceiling when sold.\n        ', model=TunableReference(description='\n            The placard to use when the object is sold.\n            ', manager=services.definition_manager(), pack_safe=True), vfx=PlayEffect.TunableFactory(description='\n            The effect to play when the object is sold.\n            '))
    UNINTERACTABLE_AUTONOMY_MODIFIER = TunableAutonomyModifier(description='\n        Autonomy modifier that disables interactions on this object. Applied\n        to this object and its children when marked as sellable or sold.\n        ', locked_args={'relationship_multipliers': None})

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._cached_value = None
        self._uninteractable_autonomy_modifier_handle = None

    @classproperty
    def required_packs(cls):
        return (Pack.EP01,)

    def on_add(self):
        if self.owner.state_component is None:
            self.owner.add_component(StateComponent(self.owner, states=(), state_triggers=(), unique_state_changes=None, delinquency_state_changes=None, timed_state_triggers=None))
        self.owner.set_state_dynamically(state=self.DEFAULT_SALE_STATE.state, new_value=self.DEFAULT_SALE_STATE, seed_value=self.SOLD_STATE)
        self.owner.update_component_commodity_flags()

    def save(self, persistence_master_message):
        persistable_data = SimObjectAttributes_pb2.PersistenceMaster.PersistableData()
        persistable_data.type = SimObjectAttributes_pb2.PersistenceMaster.PersistableData.RetailComponent
        retail_data = persistable_data.Extensions[SimObjectAttributes_pb2.PersistableRetailComponent.persistable_data]
        if self._cached_value is not None:
            retail_data.cached_value = self._cached_value
        persistence_master_message.data.extend([persistable_data])

    def load(self, persistence_master_message):
        retail_data = persistence_master_message.Extensions[SimObjectAttributes_pb2.PersistableRetailComponent.persistable_data]
        if retail_data.HasField('cached_value'):
            self._cached_value = retail_data.cached_value

    def get_current_curb_appeal(self):
        curb_appeal = 0
        if self.advertises:
            curb_appeal = self.advertises.base_curb_appeal
            curb_appeal += sum([curb_appeal for (state, curb_appeal) in self.advertises.state_based_curb_appeal.items() if self.owner.state_value_active(state)])
        return curb_appeal

    def on_state_changed(self, state, old_value, new_value, from_init):
        reapply_state = False
        if old_value is new_value:
            if state is not self.FOR_SALE_STATE.state:
                return
            reapply_state = True
        retail_manager = services.business_service().get_retail_manager_for_zone()
        if retail_manager is None:
            return
        if new_value is self.NOT_FOR_SALE_STATE or new_value is self.DEFAULT_SALE_STATE:
            show_vfx = not reapply_state and (old_value is self.FOR_SALE_STATE or old_value is self.DEFAULT_SALE_STATE)
            if self.FOR_SALE_STATE in self.owner.swapping_to_parent.slot_component.state_values:
                show_vfx = False
            self._set_not_for_sale_internal(show_vfx=show_vfx)
        elif new_value is self.FOR_SALE_STATE:
            show_vfx = not reapply_state and (old_value is self.NOT_FOR_SALE_STATE or old_value is self.DEFAULT_SALE_STATE)
            if self.NOT_FOR_SALE_STATE in self.owner.swapping_to_parent.slot_component.state_values:
                show_vfx = False
            self._set_for_sale_internal(show_vfx=show_vfx)
            if show_vfx and self.owner.swapping_to_parent is not None and old_value is self.SOLD_STATE:
                self.owner.remove_client_state_suppressor(state)
                self.owner.reset_states_to_default()
        elif new_value is self.SOLD_STATE:
            self.owner.add_client_state_suppressor(self.SOLD_STATE.state)
            self._set_sold_internal()
        self.owner.update_component_commodity_flags()

    def on_added_to_inventory(self):
        inventory = self.owner.get_inventory()
        if inventory is None:
            return
        if inventory.inventory_type in RetailUtils.RETAIL_INVENTORY_TYPES:
            if not self.is_sold:
                self.set_for_sale()
        else:
            if self.owner.get_state(self.DEFAULT_SALE_STATE.state) == self.DEFAULT_SALE_STATE:
                return
            if not self.is_sold:
                self.set_not_for_sale()

    def on_child_added(self, child, location):
        if self.is_for_sale and not self.is_allowed_slot(location.slot_hash):
            self.set_not_for_sale()
        child_retail = child.retail_component
        if child_retail is not None and self.is_for_sale_or_sold:
            child_retail.set_uninteractable()

    def on_child_removed(self, child, new_parent=None):
        child_retail = child.retail_component
        if child_retail is not None:
            child_retail.set_interactable(from_unparent=True)

    def on_finalize_load(self):
        self.owner.update_component_commodity_flags()
        retail_manager = services.business_service().get_retail_manager_for_zone()
        if retail_manager is None:
            if self.is_sold or self.is_for_sale:
                self.set_not_for_sale()
        elif self.is_sold:
            self.owner.add_client_state_suppressor(self.SOLD_STATE.state)

    @property
    def is_for_sale(self):
        return self.owner.state_value_active(self.FOR_SALE_STATE)

    @property
    def is_sold(self):
        return self.owner.state_value_active(self.SOLD_STATE)

    @property
    def is_not_for_sale(self):
        return self.owner.state_value_active(self.NOT_FOR_SALE_STATE) or self.owner.state_value_active(self.DEFAULT_SALE_STATE)

    @property
    def is_for_sale_or_sold(self):
        return not self.is_not_for_sale

    def get_retail_value(self):
        obj = self.owner
        crafting_component = obj.get_component(types.CRAFTING_COMPONENT)
        if crafting_component is None:
            return obj.catalog_value
        if self._cached_value is None:
            return obj.current_value
        state_component = obj.state_component
        if state_component is not None:
            return max(round(self._cached_value*state_component.state_based_value_mod), 0)
        else:
            return self._cached_value

    def get_sell_price(self):
        base_value = self.get_retail_value()
        retail_manager = services.business_service().get_retail_manager_for_zone()
        if retail_manager is None:
            logger.error("Trying to get the sell price of a retail item but no retail_manager was found for this lot. Defaulting to the object's value without a markup applied.")
            return base_value
        return retail_manager.get_value_with_markup(base_value)

    def get_buy_affordance(self):
        sellable_data = self.sellable
        if sellable_data is not None:
            return sellable_data.buy_affordance

    def is_allowed_slot(self, slot_hash):
        if not self.sellable:
            return False
        for runtime_slot in self.owner.get_runtime_slots_gen(bone_name_hash=slot_hash):
            if self.sellable.allowed_occupied_slots_for_sellable & runtime_slot.slot_types:
                return True
        return False

    def get_can_be_sold(self):
        if not self.sellable:
            return False
        elif any(not self.is_allowed_slot(child.slot_hash) for child in self.owner.children):
            return False
        return True

    def set_not_for_sale(self):
        self.owner.set_state(self.NOT_FOR_SALE_STATE.state, self.NOT_FOR_SALE_STATE)

    def set_for_sale(self):
        self.owner.set_state(self.FOR_SALE_STATE.state, self.FOR_SALE_STATE)

    def _set_sold_internal(self):
        retail_manager = services.business_service().get_retail_manager_for_zone()
        if retail_manager is None:
            logger.error('Trying to set an item as sold but the retail manager is None.')
            return
        item = self.owner
        self._handle_children_of_sold_object(item)
        self._change_to_placard()
        item.on_set_sold()

    def set_uninteractable(self, propagate_to_children=False):
        if self._uninteractable_autonomy_modifier_handle is not None:
            return
        self._uninteractable_autonomy_modifier_handle = self.owner.add_statistic_modifier(self.UNINTERACTABLE_AUTONOMY_MODIFIER)
        if propagate_to_children:
            for child in self.owner.children:
                retail_component = child.retail_component
                if retail_component is not None:
                    child.retail_component.set_uninteractable(propagate_to_children=False)

    def set_interactable(self, propagate_to_children=False, from_unparent=False):
        if self._uninteractable_autonomy_modifier_handle is None:
            return
        if not from_unparent:
            parent = self.owner.parent
            if parent is not None:
                parent_retail = parent.retail_component
                if parent_retail is not None and parent_retail.is_for_sale_or_sold:
                    return
        self.owner.remove_statistic_modifier(self._uninteractable_autonomy_modifier_handle)
        self._uninteractable_autonomy_modifier_handle = None
        if propagate_to_children:
            for child in self.owner.children:
                retail_component = child.retail_component
                if retail_component is not None and not retail_component.is_for_sale_or_sold:
                    child.retail_component.set_interactable(propagate_to_children=False)

    def _set_not_for_sale_internal(self, show_vfx=True):
        self.set_interactable(propagate_to_children=True)
        retail_manager = services.business_service().get_retail_manager_for_zone()
        if retail_manager is None:
            return
        retail_manager.refresh_for_sale_vfx_for_object(self.owner)
        if show_vfx:
            self.SET_NOT_FOR_SALE_VFX(self.owner).start_one_shot()

    def _set_for_sale_internal(self, show_vfx=True):
        self.set_uninteractable(propagate_to_children=True)
        item = self.owner
        if item.standin_model is not None:
            item.standin_model = None
            item.on_restock()
        if self._cached_value is not None:
            item.base_value = self._cached_value
            self._cached_value = None
        retail_manager = services.business_service().get_retail_manager_for_zone()
        if retail_manager is None:
            logger.error("Trying to set an item For Sale but it's not on a valid retail lot.")
            return False
        retail_manager.refresh_for_sale_vfx_for_object(self.owner)
        if show_vfx:
            self.SET_FOR_SALE_VFX(self.owner).start_one_shot()
        return True

    def _choose_placard_info(self):
        placard_override = self.sellable.placard_override
        if placard_override is not None:
            if placard_override.model is not None:
                return placard_override
            logger.error('Object [{}] has a placard override enabled on the retail component [{}] but the placard override has no model set. We will attempt to pick the correct placard.', self.owner, self)
        item = self.owner
        if item.parent is not None:
            return self.PLACARD_SURFACE
        if item.wall_or_fence_placement:
            return self.PLACARD_WALL
        if item.ceiling_placement:
            return self.PLACARD_CEILING
        else:
            return self.PLACARD_FLOOR

    def _change_to_placard(self, play_vfx=True):
        item = self.owner
        if self._cached_value is None:
            self._cached_value = item.base_value
        item.base_value = 0
        placard_info = self._choose_placard_info()
        item.standin_model = placard_info.model.definition.get_model(0)
        item.set_state(self.SOLD_STATE.state, self.SOLD_STATE)
        if play_vfx:
            effect = placard_info.vfx(item)
            effect.start_one_shot()
        retail_manager = services.business_service().get_retail_manager_for_zone()
        if retail_manager is None:
            logger.error("Trying to change a retail object to a placard but it's not on a valid retail lot.")
            return False
        retail_manager.refresh_for_sale_vfx_for_object(self.owner)

    def _handle_children_of_sold_object(self, obj):
        retail_manager = services.business_service().get_retail_manager_for_zone()
        active_household_is_owner = retail_manager.is_owner_household_active
        should_show_notification = False
        for child in tuple(obj.children):
            if child.has_component(types.RETAIL_COMPONENT):
                child.retail_component.set_not_for_sale()
            if active_household_is_owner:
                should_show_notification = True
                build_buy.move_object_to_household_inventory(child)
            else:
                child.schedule_destroy_asap()
        if should_show_notification:
            notification = retail_manager.ITEMS_SENT_TO_HH_INVENTORY_NOTIFICATION(obj)
            notification.show_dialog()

    def component_super_affordances_gen(self, **kwargs):
        retail_manager = services.business_service().get_retail_manager_for_zone()
        if retail_manager is None:
            return
        sellable_data = self.sellable
        if sellable_data is not None:
            if self.is_for_sale:
                yield from sellable_data.for_sale_extra_affordances
                if sellable_data.set_not_for_sale_affordance is not None:
                    yield sellable_data.set_not_for_sale_affordance
                    if retail_manager.is_open:
                        if sellable_data.buy_affordance is not None:
                            yield sellable_data.buy_affordance
                        if sellable_data.browse_affordance is not None:
                            yield sellable_data.browse_affordance
            elif self.is_not_for_sale:
                if sellable_data.set_for_sale_affordance is not None and self.get_can_be_sold():
                    yield sellable_data.set_for_sale_affordance
            elif self.is_sold:
                yield from sellable_data.restock_affordances
                if sellable_data.clear_placard_affordance is not None:
                    yield sellable_data.clear_placard_affordance

    def modify_interactable_flags(self, interactable_flag_field):
        if not self.is_sold:
            interactable_flag_field.flags |= interaction_protocol.Interactable.FORSALE
(TunableRetailComponentReference, TunableRetailComponentSnippet) = define_snippet('Retail_Component', RetailComponent.TunableFactory())