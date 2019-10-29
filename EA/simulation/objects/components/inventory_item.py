from protocolbuffers import SimObjectAttributes_pb2 as protocolsfrom distributor.shared_messages import IconInfoData, build_icon_info_msgfrom event_testing.test_events import TestEventfrom interactions.utils.tunable_icon import TunableIconAllPacksfrom objects.components import Component, types, componentmethod_with_fallbackfrom objects.components.inventory_enums import InventoryType, StackScheme, InventoryItemClaimStatusfrom objects.components.inventory_type_tuning import InventoryTypeTuningfrom objects.components.state import TunableStateTypeReferencefrom objects.components.state_change import StateChangefrom objects.components.types import INVENTORY_COMPONENTfrom objects.hovertip import TooltipFieldsfrom objects.mixins import SuperAffordanceProviderMixin, TargetSuperAffordanceProviderMixinfrom relics.relic_tuning import RelicTuningfrom sims4.localization import TunableLocalizedStringfrom sims4.tuning.tunable import TunableEnumEntry, TunableList, TunableReference, Tunable, AutoFactoryInit, HasTunableFactory, TunableTuple, OptionalTunable, TunableVariant, TunableSet, TunableSimMinute, TunableMappingimport cachesimport servicesimport sims4.loglogger = sims4.log.Logger('InventoryItem', default_owner='tingyul')
class InventoryItemComponent(Component, HasTunableFactory, AutoFactoryInit, SuperAffordanceProviderMixin, TargetSuperAffordanceProviderMixin, component_name=types.INVENTORY_ITEM_COMPONENT, persistence_key=protocols.PersistenceMaster.PersistableData.InventoryItemComponent):
    DEFAULT_ADD_TO_WORLD_AFFORDANCES = TunableList(description="\n        A list of default affordances to add objects in a Sim's inventory to\n        the world.\n        ", tunable=TunableReference(manager=services.get_instance_manager(sims4.resources.Types.INTERACTION)))
    DEFAULT_ADD_TO_SIM_INVENTORY_AFFORDANCES = TunableList(description="\n        A list of default affordances to add objects to a Sim's inventory.\n        ", tunable=TunableReference(manager=services.get_instance_manager(sims4.resources.Types.INTERACTION)))
    DEFAULT_NO_CARRY_ADD_TO_WORLD_AFFORDANCES = TunableList(description="\n        A list of default affordances to add objects in a Sim's inventory that\n        skip the carry pose to the world.\n        ", tunable=TunableReference(manager=services.get_instance_manager(sims4.resources.Types.INTERACTION)))
    DEFAULT_NO_CARRY_ADD_TO_SIM_INVENTORY_AFFORDANCES = TunableList(description="\n        A list of default affordances to add objects that skip the carry pose\n        to a Sim's inventory.\n        ", tunable=TunableReference(manager=services.get_instance_manager(sims4.resources.Types.INTERACTION)))
    PUT_AWAY_AFFORDANCE = TunableReference(description='\n        An affordance for putting an object away in an inventory.\n        ', manager=services.get_instance_manager(sims4.resources.Types.INTERACTION))
    STACK_SORT_ORDER_STATES = TunableList(description='\n        A list of states that dictate the order of an inventory stack. States\n        lower down in this list will cause the object to be further down in\n        the stack.\n        ', tunable=TunableTuple(description='\n            States to consider.\n            ', state=TunableReference(description='\n                State to sort on.\n                ', manager=services.get_instance_manager(sims4.resources.Types.OBJECT_STATE), class_restrictions='ObjectState'), is_value_order_inverted=Tunable(description='\n                Normally, higher state value is better. For example, an\n                IngredientQuality value of 0 is the worst and 10 is the best.\n\n                However, there are some state values where lower is better,\n                e.g. burnt state is tied to the burnt commodity where 0 is\n                unburnt and 100 is completely burnt. This option should be set\n                for these states.\n                ', tunable_type=bool, default=False)))
    STACK_SCHEME_OPTIONS = TunableMapping(description='\n        This mapping allows special functionality for dynamic stack schemes.  This allows things like:\n        - Ability to specify a stack icon.\n        - Ability to specify the tooltip text that is shown in the stack hovertip.\n        ', key_type=TunableEnumEntry(tunable_type=StackScheme, default=StackScheme.NONE, invalid_enums=(StackScheme.NONE, StackScheme.DEFINITION, StackScheme.VARIANT_GROUP)), value_type=TunableTuple(description='\n            Various settings for the inventory stack scheme.\n            ', icon=TunableIconAllPacks(description='\n                Use this icon for this stack scheme.\n                '), tooltip=TunableTuple(description='\n                If set, these strings are used for the tooltip of the stack.\n                ', title=TunableLocalizedString(description='Tooltip title'), tooltip_description=TunableLocalizedString(description='Tooltip description'))))

    @staticmethod
    def _verify_tunable_callback(cls, tunable_name, source, valid_inventory_types, skip_carry_pose, inventory_only, **kwargs):
        if skip_carry_pose:
            for inv_type in valid_inventory_types:
                inv_data = InventoryTypeTuning.INVENTORY_TYPE_DATA.get(inv_type)
                if inv_data is not None and not inv_data.skip_carry_pose_allowed:
                    logger.error('You cannot tune your item to skip carry\n                    pose unless it is only valid for the sim, mailbox, and/or\n                    hidden inventories.  Any other inventory type will not\n                    properly support this option. -Mike Duke')

    FACTORY_TUNABLES = {'description': '\n            An object with this component can be placed in inventories.\n            ', 'valid_inventory_types': TunableList(description='\n            A list of Inventory Types this object can go into.\n            ', tunable=TunableEnumEntry(description='\n                Any inventory type tuned here is one in which the owner of this\n                component can be placed into.\n                ', tunable_type=InventoryType, default=InventoryType.UNDEFINED, invalid_enums=(InventoryType.UNDEFINED,))), 'skip_carry_pose': Tunable(description='\n            If Checked, this object will not use the normal pick up or put down\n            SI which goes through the carry pose.  It will instead use a swipe\n            pick up which does a radial route and swipe.  Put down will run a\n            FGL and do a swipe then fade in the object in the world. You can\n            only use this for an object that is only valid for the sim, hidden\n            and/or mailbox inventory.  It will not work with other inventory\n            types.', tunable_type=bool, default=False), 'inventory_only': Tunable(description='\n            Denote the owner of this component as an "Inventory Only" object.\n            These objects are not meant to be placed in world, and will not\n            generate any of the default interactions normally generated for\n            inventory objects.\n            ', tunable_type=bool, default=False), 'visible': Tunable(description="\n            Whether the object is visible in the Sim's Inventory or not.\n            Objects that are invisible won't show up but can still be tested\n            for.\n            ", tunable_type=bool, default=True), 'put_away_affordance': OptionalTunable(description='\n            Whether to use the default put away interaction or an overriding\n            one. The default affordance is tuned at\n            objects.components.inventory_item -> InventoryItemComponent -> Put\n            Away Affordance.\n            ', tunable=TunableReference(manager=services.get_instance_manager(sims4.resources.Types.INTERACTION)), disabled_name='DEFAULT', enabled_name='OVERRIDE'), 'no_carry_add_to_sim_inventory_affordances': OptionalTunable(description='\n            Any affordances tuned here will be used in place of the "Default No\n            Carry Add To Sim Inventory Affordances" tunable. The default\n            affordances are tuned at objects.components.inventory_item ->\n            InventoryItemComponent -> Default No Carry Add To Sim Inventory\n            Affordances\n            ', tunable=TunableList(description="\n                A list of override affordances to add objects that skip the carry pose\n                to a Sim's inventory.\n                ", tunable=TunableReference(manager=services.get_instance_manager(sims4.resources.Types.INTERACTION))), disabled_name='DEFAULT', enabled_name='OVERRIDE'), 'no_carry_add_to_world_affordances': OptionalTunable(description='\n            Any affordances tuned here will be used in place of the "Default No\n            Carry Add To World Affordances" tunable. The default affordances\n            are tuned at objects.components.inventory_item -> \n            InventoryItemComponent -> Default No Carry Add To World Affordances\n            ', tunable=TunableSet(description="\n                A set of override affordances to add objects in a Sim's \n                inventory that skip the carry pose to the world.\n                ", tunable=TunableReference(manager=services.get_instance_manager(sims4.resources.Types.INTERACTION))), disabled_name='DEFAULT', enabled_name='OVERRIDE'), 'stack_scheme': TunableEnumEntry(description="\n            How object should stack in an inventory. If you're confused on\n            what definitions and variants are, consult a build/buy designer or\n            producer.\n            \n            NONE: Object will not stack.\n            \n            VARIANT_GROUP: This object will stack with objects with in the same\n            variant group. For example, orange guitars will stack with red\n            guitars.\n\n            DEFINITION: This object will stack with objects with the same\n            definition. For example, orange guitars will stack with other\n            orange guitars but not with red guitars.\n            \n            Dynamic entries stack together.\n            ", tunable_type=StackScheme, default=StackScheme.VARIANT_GROUP), 'stack_scheme_object_state': OptionalTunable(description='\n            The object state we are using in combination with stack scheme. If enabled,\n            the specific state will be considered when inventory system categorize items\n            into different stacks.\n            \n            ex. If we set "hexed state" here for potions, then potions with different\n            "hexed" states (hexed, non-hexed) will be stored into different stacks in\n            inventory.\n            ', tunable=TunableStateTypeReference()), 'can_place_in_world': Tunable(description='\n            If checked, this object will generate affordances allowing it to be\n            placed in the world. If unchecked, it will not.\n            ', tunable_type=bool, default=True), 'remove_from_npc_inventory': Tunable(description="\n            If checked, this object will never be added to a NPC Sim's\n            inventory. \n            \n            This field is never used for an active family sims. Player played\n            sims use this flag to shelve the objects in their inventories\n            (performance optimization). Instead of creating the object in the\n            Sim's inventory, shelved objects are stored in the save file and\n            loaded only when the Sim's family becomes player controlled.\n            ", tunable_type=bool, default=False), 'forward_client_state_change_to_inventory_owner': OptionalTunable(description='\n            Whether the object is forwarding the client state changes to the \n            inventory owner or not.\n            \n            example. Earbuds object has Audio State change but it will play\n            the audio on the Sim owner instead.\n            ', tunable=TunableList(description='\n                List of client states that are going to be forwarded to \n                inventory owner.\n                ', tunable=TunableVariant(description='\n                    Any client states change tuned here is going to be \n                    forwarded to inventory owner.\n                    ', locked_args={'audio_state': StateChange.AUDIO_STATE, 'audio_effect_state': StateChange.AUDIO_EFFECT_STATE, 'vfx_state': StateChange.VFX}))), 'forward_affordances_to_inventory_owner': Tunable(description='\n            If checked, all interactions for this object will be available\n            when clicking on inventory owner object, while having this object \n            in their inventory.\n            \n            example. Earbuds "Listen To" is available on the Sim while\n            having earbuds in Sim\'s inventory.\n            ', tunable_type=bool, default=False), 'on_inventory_change_tooltip_updates': TunableSet(description='\n            A set of tooltip fields that should be updated when this object\n            changes inventory. Not all tooltip fields are supported. Talk to\n            a GPE to add support for more fields.\n            ', tunable=TunableEnumEntry(description='\n                The Tooltip Field to update on this object.\n                ', tunable_type=TooltipFields, default=TooltipFields.relic_description)), 'persist_in_hidden_storage': Tunable(description="\n            If checked, any objects that are part of a Sim's inventory's\n            hidden storage will be persisted as hidden, and will be created\n            in the hidden storage on load. Otherwise, objects that were in\n            the hidden storage on save will be moved to the visible storage\n            on load.\n            \n            eg. Crystals that are mounted in the crystal helmet should persist\n            their hidden state so that they are created in the hidden storage\n            on load.\n            ", tunable_type=bool, default=False), 'register_with_lost_and_found': OptionalTunable(description="\n            If enabled, objects placed on a lot from a Sim inventory will\n            register for lost and found cleanup.  When the zone spins up, items\n            'left behind' or 'lost' by a Sim after the Sim's household leaves\n            a lot will be returned to them or their household.  Only use for\n            items where this is likely to matter to the player.\n            ", tunable=TunableTuple(description='\n                Data for use with lost and found service.\n                ', time_before_lost=TunableSimMinute(description='\n                    The amount of time an object has to be on a lot until\n                    it is considered lost for lost and found purposes.\n                    ', default=0))), 'always_destroy_on_inventory_transfer': Tunable(description='\n            If checked then this object will always be destroyed on inventory\n            transfer.\n            ', tunable_type=bool, default=False), 'verify_tunable_callback': _verify_tunable_callback}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._current_inventory_type = None
        self._last_inventory_owner_ref = None
        self._stack_count = 1
        self._stack_id = None
        self._sort_order = None
        self._stat_modifier_handles = []
        self._claim_status = InventoryItemClaimStatus.UNCLAIMED
        self.save_for_stack_compaction = False
        self._is_hidden = False

    def on_state_changed(self, state, old_value, new_value, from_init):
        self._update_stack_id_with_state(state)
        inventory = self.get_inventory()
        if inventory is not None:
            for owner in inventory.owning_objects_gen():
                owner.inventory_component.object_state_update_callback(old_value, new_value)
        for state_info in InventoryItemComponent.STACK_SORT_ORDER_STATES:
            if state_info.state is state:
                self._sort_order = None
                if inventory is not None:
                    inventory.push_inventory_item_update_msg(self.owner)
                return

    def post_component_reset(self):
        inventory = self.get_inventory()
        if inventory is not None:
            inventory.push_inventory_item_update_msg(self.owner)

    @property
    def current_inventory_type(self):
        return self._current_inventory_type

    @property
    def last_inventory_owner(self):
        if self._last_inventory_owner_ref is not None:
            return self._last_inventory_owner_ref()

    @last_inventory_owner.setter
    def last_inventory_owner(self, value):
        if value is None:
            self._last_inventory_owner_ref = None
        else:
            self._last_inventory_owner_ref = value.ref()

    @property
    def is_hidden(self):
        return self._is_hidden

    @is_hidden.setter
    def is_hidden(self, value):
        self._is_hidden = value

    @caches.cached
    def get_root_owner(self):
        return tuple(self._root_owner_gen())

    def _root_owner_gen(self):
        test_object = self.last_inventory_owner
        if test_object is not None:
            if test_object.is_in_inventory():
                yield from test_object.inventoryitem_component.root_owner_gen()
            yield test_object
        elif not InventoryTypeTuning.is_shared_between_objects(self._current_inventory_type):
            logger.error('{} is in a non-shared inventory type {} but has no owner object.', self.owner, self._current_inventory_type)
        else:
            inventories = services.current_zone().lot.get_object_inventories(self._current_inventory_type)
            for inventory in inventories:
                for owning_object in inventory.owning_objects_gen():
                    if owning_object.is_in_inventory():
                        yield from owning_object.inventoryitem_component.root_owner_gen()
                    else:
                        yield owning_object

    @componentmethod_with_fallback(lambda : False)
    def is_in_inventory(self):
        return self._current_inventory_type is not None

    @componentmethod_with_fallback(lambda : 1)
    def stack_count(self):
        return self._stack_count

    @componentmethod_with_fallback(lambda count: None)
    def set_stack_count(self, count):
        self._stack_count = count

    @componentmethod_with_fallback(lambda num: None)
    def update_stack_count(self, num):
        self._stack_count += num

    @componentmethod_with_fallback(lambda sim=None: False)
    def is_in_sim_inventory(self, sim=None):
        if sim is not None:
            inventory = self.get_inventory()
            if inventory is not None:
                return inventory.owner is sim
            return False
        return self._current_inventory_type == InventoryType.SIM

    def on_added_to_inventory(self):
        inventory = self.get_inventory()
        if inventory is not None:
            self._process_inventory_changed_event(inventory.owner)
            self._update_tooltip_fields(inventory.owner)
            owner_inventory_component = inventory.owner.inventory_component
            if owner_inventory_component is not None:
                if self.forward_affordances_to_inventory_owner:
                    owner_inventory_component.add_forwarded_object(self.owner)
                if inventory.owner.is_sim:
                    if self.target_super_affordances or self.super_affordances:
                        owner_inventory_component.add_affordance_provider_object(self.owner)
                    if self.register_with_lost_and_found:
                        services.get_object_lost_and_found_service().remove_object(self.owner.id)

    def on_removed_from_inventory(self):
        owner = self.last_inventory_owner
        if owner is not None:
            self._process_inventory_changed_event(owner)
            self._update_tooltip_fields()
            inventory = owner.inventory_component
            if inventory is not None:
                if inventory.inventory_type not in (InventoryType.MAILBOX, InventoryType.HIDDEN):
                    self.owner.new_in_inventory = False
                if self.forward_affordances_to_inventory_owner:
                    inventory.remove_forwarded_object(self.owner)
                if owner.is_sim:
                    if self.target_super_affordances or self.super_affordances:
                        inventory.remove_affordance_provider_object(self.owner)
                    if self.register_with_lost_and_found:
                        services.get_object_lost_and_found_service().add_game_object(owner.zone_id, self.owner.id, owner.id, owner.household_id, self.register_with_lost_and_found.time_before_lost)

    def _update_tooltip_fields(self, inventory_owner=None):
        for tooltip_field in self.on_inventory_change_tooltip_updates:
            if tooltip_field == TooltipFields.relic_description:
                if inventory_owner is not None and inventory_owner.is_sim and inventory_owner.sim_info.relic_tracker is not None:
                    tooltip_text = inventory_owner.sim_info.relic_tracker.get_tooltip_for_object(self.owner)
                else:
                    tooltip_text = RelicTuning.IN_WORLD_HOVERTIP_TEXT
                self.owner.update_tooltip_field(TooltipFields.relic_description, tooltip_text, should_update=True)

    def _process_inventory_changed_event(self, owner):
        services.get_event_manager().process_event(TestEvent.OnInventoryChanged, sim_info=owner.sim_info if owner.is_sim else None)

    @componentmethod_with_fallback(lambda : None)
    def get_inventory(self):
        if self.is_in_inventory():
            if self.last_inventory_owner is not None:
                return self.last_inventory_owner.inventory_component
            if not InventoryTypeTuning.is_shared_between_objects(self._current_inventory_type):
                logger.error('{} is in a non-shared inventory type {} but has no owner object.', self.owner, self._current_inventory_type)
            inventories = services.current_zone().lot.get_object_inventories(self._current_inventory_type)
            for inventory in inventories:
                if self.owner in inventory:
                    return inventory
            for inventory in inventories:
                return inventory

    @componentmethod_with_fallback(lambda inventory_type: False)
    def can_go_in_inventory_type(self, inventory_type):
        if inventory_type == InventoryType.HIDDEN:
            if InventoryType.MAILBOX not in self.valid_inventory_types:
                logger.warn('Object can go in the hidden inventory, but not the mailbox: {}', self)
            return True
        return inventory_type in self.valid_inventory_types

    def get_stack_id(self):
        if self._stack_id is None:
            self._stack_id = services.inventory_manager().get_stack_id(self.owner, self.stack_scheme)
        return self._stack_id

    @componentmethod_with_fallback(lambda new_stack_id: None)
    def set_stack_id(self, new_stack_id):
        self._stack_id = new_stack_id

    def _update_stack_id_with_state(self, state):
        if state is self.stack_scheme_object_state:
            custom_key = self.owner.get_state(state)
            new_stack_id = services.inventory_manager().get_stack_id(self.owner, self.stack_scheme, custom_key)
            if new_stack_id == self._stack_id:
                return
            inventory = self.get_inventory()
            if inventory is not None:
                inventory.update_object_stack_by_id(self.owner.id, new_stack_id)
            else:
                self._stack_id = new_stack_id

    @componentmethod_with_fallback(lambda *args, **kwargs: 0)
    def get_stack_sort_order(self, inspect_only=False):
        if inspect_only or self._sort_order is None:
            self._recalculate_sort_order()
        if self._sort_order is not None:
            return self._sort_order
        return 0

    @property
    def has_stack_option(self):
        return self.stack_scheme in self.STACK_SCHEME_OPTIONS

    def populate_stack_icon_info_data(self, icon_info_msg):
        stack_options = self.STACK_SCHEME_OPTIONS.get(self.stack_scheme)
        if stack_options is None:
            logger.error('{} does not have stack options, but they were requested for {}.', self.stack_scheme, self.owner, owner='jdimailig')
            return
        tooltip_name = stack_options.tooltip.title
        tooltip_description = stack_options.tooltip.tooltip_description
        icon_info = IconInfoData(icon_resource=stack_options.icon)
        build_icon_info_msg(icon_info, tooltip_name, icon_info_msg, desc=tooltip_description)

    def _recalculate_sort_order(self):
        sort_order = 0
        multiplier = 1
        for state_info in InventoryItemComponent.STACK_SORT_ORDER_STATES:
            state = state_info.state
            if state is None:
                pass
            else:
                invert_order = state_info.is_value_order_inverted
                num_values = len(state.values)
                if self.owner.has_state(state):
                    state_value = self.owner.get_state(state)
                    value = state.values.index(state_value)
                    if not invert_order:
                        value = num_values - value - 1
                    sort_order += multiplier*value
                multiplier *= num_values
        self._sort_order = sort_order

    def component_interactable_gen(self):
        if not self.inventory_only:
            yield self

    def component_super_affordances_gen(self, **kwargs):
        if self.owner.get_users():
            return
        if not self.inventory_only:
            lot = None
            obj_inventory_found = False
            for valid_type in self.valid_inventory_types:
                if valid_type == InventoryType.SIM:
                    if self.skip_carry_pose:
                        if self.no_carry_add_to_sim_inventory_affordances is None:
                            yield from self.DEFAULT_NO_CARRY_ADD_TO_SIM_INVENTORY_AFFORDANCES
                        else:
                            yield from self.no_carry_add_to_sim_inventory_affordances
                        if self.can_place_in_world:
                            if self.no_carry_add_to_world_affordances is None:
                                yield from self.DEFAULT_NO_CARRY_ADD_TO_WORLD_AFFORDANCES
                            else:
                                yield from self.no_carry_add_to_world_affordances
                    else:
                        yield from self.DEFAULT_ADD_TO_SIM_INVENTORY_AFFORDANCES
                        if self.can_place_in_world:
                            yield from self.DEFAULT_ADD_TO_WORLD_AFFORDANCES
                elif not obj_inventory_found:
                    if self.skip_carry_pose:
                        pass
                    else:
                        lot = services.current_zone().lot
                        if lot or InventoryTypeTuning.is_put_away_allowed_on_inventory_type(valid_type):
                            for inventory in lot.get_object_inventories(valid_type):
                                if not inventory.has_owning_object:
                                    pass
                                else:
                                    obj_inventory_found = True
                                    if self.put_away_affordance is None:
                                        yield self.PUT_AWAY_AFFORDANCE
                                    else:
                                        yield self.put_away_affordance
                                    break

    def place_in_world_affordances_gen(self):
        if self.inventory_only or not self.can_place_in_world:
            return
        if self.skip_carry_pose:
            if self.no_carry_add_to_world_affordances is None:
                yield from self.DEFAULT_NO_CARRY_ADD_TO_WORLD_AFFORDANCES
            else:
                yield from self.no_carry_add_to_world_affordances
        else:
            yield from self.DEFAULT_ADD_TO_WORLD_AFFORDANCES

    def place_in_inventory_affordances_gen(self):
        if self.skip_carry_pose:
            if self.no_carry_add_to_sim_inventory_affordances is None:
                yield from self.DEFAULT_NO_CARRY_ADD_TO_SIM_INVENTORY_AFFORDANCES
            else:
                yield from self.no_carry_add_to_sim_inventory_affordances
        else:
            yield from self.DEFAULT_ADD_TO_SIM_INVENTORY_AFFORDANCES

    def valid_object_inventory_gen(self):
        lot = services.current_zone().lot
        for valid_type in self.valid_inventory_types:
            if valid_type != InventoryType.SIM and InventoryTypeTuning.is_put_away_allowed_on_inventory_type(valid_type):
                for inventory in lot.get_object_inventories(valid_type):
                    for obj in inventory.owning_objects_gen():
                        yield obj

    def set_inventory_type(self, inventory_type, owner):
        if self._current_inventory_type != None:
            self._remove_inventory_effects(self._current_inventory_type)
            self._current_inventory_type = None
        if inventory_type is not None:
            if not InventoryTypeTuning.is_shared_between_objects(inventory_type):
                logger.assert_raise(owner is not None, 'Adding {} to non-shared inventory type {} without owner object', self.owner, inventory_type)
            self._current_inventory_type = inventory_type
            self.last_inventory_owner = owner
            self._apply_inventory_effects(inventory_type)

    @property
    def inventory_owner(self):
        if self.is_in_inventory():
            return self.last_inventory_owner

    def clear_previous_inventory(self):
        self.last_inventory_owner = None

    def get_clone_for_stack_split(self):
        inventory_type = self._current_inventory_type
        self._current_inventory_type = None
        try:
            return self.owner.clone()
        finally:
            self._current_inventory_type = inventory_type

    @componentmethod_with_fallback(lambda : None)
    def get_inventory_plex_id(self):
        inventory_type = self.current_inventory_type
        if inventory_type is None or not InventoryTypeTuning.is_shared_between_objects(inventory_type):
            return
        plex_service = services.get_plex_service()
        if not plex_service.is_active_zone_a_plex:
            return
        return plex_service.get_active_zone_plex_id()

    def save(self, persistence_master_message):
        persistable_data = protocols.PersistenceMaster.PersistableData()
        persistable_data.type = protocols.PersistenceMaster.PersistableData.InventoryItemComponent
        inventory_item_save = persistable_data.Extensions[protocols.PersistableInventoryItemComponent.persistable_data]
        inventory_item_save.inventory_type = self._current_inventory_type if self._current_inventory_type is not None else 0
        inventory_item_save.owner_id = self.last_inventory_owner.id if self.last_inventory_owner is not None else 0
        if self._claim_status == InventoryItemClaimStatus.CLAIMED:
            inventory_item_save.requires_claiming = True
        if self.save_for_stack_compaction:
            inventory_item_save.stack_count = 0
        else:
            inventory_item_save.stack_count = self._stack_count
        if self.persist_in_hidden_storage:
            inventory_item_save.is_hidden = self._is_hidden
        persistence_master_message.data.extend([persistable_data])

    def load(self, message):
        data = message.Extensions[protocols.PersistableInventoryItemComponent.persistable_data]
        self._stack_count = data.stack_count
        if data.requires_claiming:
            self._claim_status = InventoryItemClaimStatus.CLAIMED
        zone = services.current_zone()
        inventory_owner = zone.find_object(data.owner_id)
        if data.inventory_type == 0 or data.inventory_type not in InventoryType:
            self.last_inventory_owner = inventory_owner
            return
        inventory_type = InventoryType(data.inventory_type)
        inventory_component = inventory_owner.inventory_component if inventory_owner is not None else None
        if inventory_component is None:
            if InventoryTypeTuning.is_shared_between_objects(inventory_type):
                inventory_component = zone.lot.get_object_inventories(inventory_type)[0]
            else:
                logger.error('Failed to insert {} into {} on load -- no inventory owner', self.owner, inventory_type)
                return
        self._is_hidden = data.is_hidden
        if not inventory_component.can_add(self.owner, hidden=self.is_hidden):
            logger.error("Failed to insert {} back into {} on load -- can't add", self.owner, inventory_component)
            return
        inventory_component.add_from_load(self.owner, hidden=self.is_hidden)

    def _apply_inventory_effects(self, inventory_type):
        inventory_component = self.owner.get_component(INVENTORY_COMPONENT)
        if inventory_component is not None:
            for inventory_item in inventory_component:
                inventory_item.inventoryitem_component._apply_inventory_effects(inventory_type)
            self.owner.update_object_tooltip()
        effects = InventoryTypeTuning.get_gameplay_effects_tuning(inventory_type)
        if effects:
            for (stat_type, decay_modifier) in effects.decay_modifiers.items():
                tracker = self.owner.get_tracker(stat_type)
                if tracker is not None:
                    stat = tracker.get_statistic(stat_type)
                    if stat is not None:
                        stat.add_decay_rate_modifier(decay_modifier)
            if effects.autonomy_modifiers:
                for autonomy_mod in effects.autonomy_modifiers:
                    modifier_handle = self.owner.add_statistic_modifier(autonomy_mod)
                    if modifier_handle is None:
                        logger.error("Applying autonomy modifiers to {} which doesn't have a statistic component.", self.owner, owner='rmccord')
                    else:
                        self._stat_modifier_handles.append(modifier_handle)

    def _remove_inventory_effects(self, inventory_type):
        inventory_component = self.owner.get_component(INVENTORY_COMPONENT)
        if inventory_component is not None:
            for inventory_item in inventory_component:
                inventory_item.inventoryitem_component._remove_inventory_effects(inventory_type)
            self.owner.update_object_tooltip()
        effects = InventoryTypeTuning.get_gameplay_effects_tuning(inventory_type)
        if effects:
            for (stat_type, decay_modifier) in effects.decay_modifiers.items():
                tracker = self.owner.get_tracker(stat_type)
                if tracker is not None:
                    stat = tracker.get_statistic(stat_type)
                    if stat is not None:
                        stat.remove_decay_rate_modifier(decay_modifier)
        for handle in self._stat_modifier_handles:
            self.owner.remove_statistic_modifier(handle)
        self._stat_modifier_handles.clear()

    @classmethod
    def should_item_be_removed_from_inventory(cls, def_id):
        object_tuning = services.definition_manager().get_object_tuning(def_id)
        if object_tuning is None:
            logger.error('Unexpected error: Loading object into inventory that is not script backed. Definition: {}', def_id, owner='manus')
            return True
        inv_item_comp = object_tuning.tuned_components.inventory_item
        if inv_item_comp is None:
            logger.error('Unexpected error: Loading object into inventory without inventory item component. Object: {}', object_tuning, owner='manus')
            return True
        return inv_item_comp.remove_from_npc_inventory

    def set_item_as_claimed(self):
        self._claim_status = InventoryItemClaimStatus.CLAIMED
