from protocolbuffers import Consts_pb2, UI_pb2, UI_pb2 as ui_protocolsfrom protocolbuffers.DistributorOps_pb2 import Operationfrom audio.primitive import TunablePlayAudiofrom build_buy import HouseholdInventoryFlagsfrom distributor.ops import GenericProtocolBufferOpfrom distributor.rollback import ProtocolBufferRollbackfrom distributor.shared_messages import create_icon_info_msgfrom distributor.system import Distributorfrom event_testing import test_eventsfrom households.household_tracker import HouseholdTrackerfrom objects.components import Component, types, componentmethod_with_fallbackfrom objects.hovertip import TooltipFieldsCompletefrom objects.object_enums import ItemLocationfrom objects.system import create_objectfrom services import get_instance_managerfrom sims4.localization import TunableLocalizedStringfrom sims4.tuning.dynamic_enum import DynamicEnumLockedfrom sims4.tuning.tunable import TunableTuple, TunableReference, TunableEnumEntry, Tunable, TunableList, TunableMapping, TunableRange, HasTunableSingletonFactory, AutoFactoryInit, OptionalTunable, HasTunableFactory, TunableSetfrom sims4.tuning.tunable_base import ExportModes, EnumBinaryExportTypefrom ui.ui_dialog_notification import UiDialogNotificationimport build_buyimport enumimport servicesimport sims4import telemetry_helperimport ui.screen_slamTELEMETRY_GROUP_COLLECTIONS = 'COLE'TELEMETRY_HOOK_COLLECTION_COMPLETE = 'COCO'TELEMETRY_COLLECTION_ID = 'coid'collection_telemetry_writer = sims4.telemetry.TelemetryWriter(TELEMETRY_GROUP_COLLECTIONS)logger = sims4.log.Logger('Collections')
class ObjectCollectionRarity(enum.Int):
    COMMON = 1
    UNCOMMON = 2
    RARE = 3

class CollectionIdentifier(DynamicEnumLocked):
    Unindentified = 0
    Gardening = 1
    Frogs = 2
    MySims = 3
    Metals = 4
    Crystals = 5
    NatureElements = 6
    Postcards = 7
    Fossils = 8
    Microscope = 9
    Telescope = 10
    Aliens = 11
    SpaceRocks = 12
    Fish = 13

class TunableCollectionTuple(TunableTuple):

    def __init__(self, **kwargs):
        super().__init__(collection_id=TunableEnumEntry(description='\n                            Unique Id for this collectible, cannot be re-used.\n                            ', tunable_type=CollectionIdentifier, default=CollectionIdentifier.Unindentified, export_modes=ExportModes.All), collection_name=TunableLocalizedString(description='\n                            Localization String for the name of the \n                            collection.  This will be read on the collection\n                            UI to separate each item group.\n                            ', export_modes=ExportModes.All), collection_tooltip=TunableLocalizedString(description='\n                            Localization String for the tooltip of the \n                            collection.  This will be shown when you hover over\n                            the header for each item group.\n                            ', export_modes=ExportModes.All), completed_award=TunableReference(description='\n                            Object award when the collection is completed.  \n                            This is an object that will be awarded to the Sim\n                            when all the items inside a collection have been \n                            discovered.\n                            ', manager=services.definition_manager(), allow_none=True, export_modes=ExportModes.All, pack_safe=True), completed_award_money=TunableRange(description='\n                            Money award when the collection is completed.  \n                            ', tunable_type=int, default=100, minimum=0, export_modes=ExportModes.All), hide_on_console=Tunable(description="\n                            Indicates if this collection should be hidden in the \n                            collections UI on console. Use for live event collections, \n                            which may not have occurred on console so we don't \n                            want to display collections the user can't get.\n                            ", tunable_type=bool, default=False, export_modes=ExportModes.All), completed_award_notification=UiDialogNotification.TunableFactory(description='\n                            Notification that will be shown when the collection\n                            is completed and the completed_award is given.\n                            '), object_list=TunableList(description='\n                            List of object that belong to a collectible group.\n                            ', tunable=CollectibleTuple.TunableFactory(), export_modes=ExportModes.All), bonus_object_list=TunableList(description='\n                            List of bonus objects that belong to a collectible group.\n                            Not required to complete the collection.\n                            ', tunable=CollectibleTuple.TunableFactory(), export_modes=ExportModes.All), screen_slam=OptionalTunable(description='\n                             Screen slam to show when the collection is\n                             completed and the completed_award is given.\n                             Localization Tokens: Collection Name = {0.String}\n                             ', tunable=ui.screen_slam.TunableScreenSlamSnippet()), first_collected_notification=OptionalTunable(description='\n                            If enabled a notification will be displayed when\n                            the first item of this collection has been found.\n                            ', tunable=UiDialogNotification.TunableFactory(description='\n                                Notification that will be shown the first item of\n                                this collection has been found.\n                                '), disabled_name='No_notification', enabled_name='Display_notification'))

class CollectibleTuple(HasTunableSingletonFactory, AutoFactoryInit):
    FACTORY_TUNABLES = {'collectable_item': TunableReference(description='\n            Object reference to each collectible object\n            ', manager=services.definition_manager(), pack_safe=True), 'rarity': TunableReference(description='\n            The rarity state of the object. Should contain a state from the\n            mapping tuned above (common/uncommon/rare).\n            ', manager=services.get_instance_manager(sims4.resources.Types.OBJECT_STATE), needs_tuning=True), 'discovered': Tunable(description='\n            Discovery value of a collectible.  This way we can tune a \n            collectible item to be available from the beginning without\n            having the player to find it\n            ', tunable_type=bool, default=False)}

class ObjectCollectionData:
    COLLECTIONS_DEFINITION = TunableList(description='\n        List of collection groups.  Will need one defined per collection id\n        ', tunable=TunableCollectionTuple())
    COLLECTION_RARITY_MAPPING = TunableMapping(description='\n        Mapping of collectible rarity to localized string for that rarity.\n        Used for displaying rarity names on the UI.\n        ', key_type=TunableReference(description='\n            Mapping of rarity state to text\n            ', manager=services.get_instance_manager(sims4.resources.Types.OBJECT_STATE), needs_tuning=True), value_type=TunableTuple(description='\n            Tying each state to a text string and a value which can be called\n            by UI.\n            ', text_value=TunableLocalizedString(description='\n                Localization String For the name of the collection.  \n                This will be read on the collection UI to show item rarities.\n                '), rarity_value=TunableEnumEntry(description='\n                Rarity enum called for UI to determine sorting in the\n                collection UI\n                ', tunable_type=ObjectCollectionRarity, needs_tuning=True, default=ObjectCollectionRarity.COMMON, binary_type=EnumBinaryExportType.EnumUint32), export_class_name='CollectionRarity'), tuple_name='CollectionRarityMapping', export_modes=ExportModes.ClientBinary)
    COLLECTION_COLLECTED_STING = TunablePlayAudio(description='\n            The audio sting that gets played when a collectible is found.\n            ')
    COLLECTION_COMPLETED_STING = TunablePlayAudio(description='\n            The audio sting that gets played when a collection is completed.\n            ')
    COLLECTED_INVALID_STATES = TunableList(description='\n            List of states the collection system will check for in an object.\n            If the object has any of these states the collectible will not\n            be counted.\n            Example: Unidentified states on herbalism.\n            ', tunable=TunableReference(description='\n                The state value the object will have to invalidate its \n                collected event.\n                ', manager=services.get_instance_manager(sims4.resources.Types.OBJECT_STATE), pack_safe=True))
    COLLECTED_RARITY_STATE = TunableReference(description='\n            The rarity state the collection system will use for an object.\n            The object will need this state to call the rarity state/text.\n            ', manager=services.get_instance_manager(sims4.resources.Types.OBJECT_STATE))
    _COLLECTION_DATA = {}
    _BONUS_COLLECTION_DATA = {}

    @classmethod
    def initialize_collection_data(cls):
        if not cls._COLLECTION_DATA:
            for collection_data in cls.COLLECTIONS_DEFINITION:
                for collectible_object in collection_data.object_list:
                    collectible_object._collection_id = collection_data.collection_id
                    cls._COLLECTION_DATA[collectible_object.collectable_item.id] = collectible_object
                for collectible_object in collection_data.bonus_object_list:
                    collectible_object._collection_id = collection_data.collection_id
                    cls._BONUS_COLLECTION_DATA[collectible_object.collectable_item.id] = collectible_object

    @classmethod
    def get_collection_info_by_definition(cls, obj_def_id):
        if not cls._COLLECTION_DATA:
            ObjectCollectionData.initialize_collection_data()
        collectible = cls._COLLECTION_DATA.get(obj_def_id)
        if collectible:
            return (collectible._collection_id, collectible, True)
        else:
            collectible = cls._BONUS_COLLECTION_DATA.get(obj_def_id)
            if collectible:
                return (collectible._collection_id, collectible, False)
        return (None, None, None)

    @classmethod
    def is_base_object_of_collection(cls, obj_def_id, collection_id):
        if not cls._COLLECTION_DATA:
            ObjectCollectionData.initialize_collection_data()
        return obj_def_id in cls._COLLECTION_DATA

    @classmethod
    def get_collection_data(cls, collection_id):
        for collection_data in cls.COLLECTIONS_DEFINITION:
            if collection_data.collection_id == collection_id:
                return collection_data

class CollectionTrackerData:

    def __init__(self, collection_id, new, base, quality=0, icon_info=None):
        self.collection_id = collection_id
        self.new = new
        self.base = base
        self.quality = quality
        self.icon_info = icon_info

class CollectionTracker(HouseholdTracker):

    def __init__(self, household):
        self._collections = {}
        self._owner = household

    @property
    def owner(self):
        return self._owner

    @property
    def collection_data(self):
        return self._collections

    def clear_collection_tracker(self):
        self._collections = {}

    def household_lod_cleanup(self):
        self.clear_collection_tracker()

    def mark_as_viewed(self, collection_id):
        for (key, collection_tracker_data) in self._collections.items():
            if not collection_id == 0:
                if collection_tracker_data.collection_id == collection_id:
                    collection_tracker_data.new = False
                    msg_type = UI_pb2.CollectibleItemUpdate.TYPE_DISCOVERY
                    self.send_collection_msg(msg_type, collection_tracker_data, self._owner.id, key)
            collection_tracker_data.new = False
            msg_type = UI_pb2.CollectibleItemUpdate.TYPE_DISCOVERY
            self.send_collection_msg(msg_type, collection_tracker_data, self._owner.id, key)

    def get_num_collected_items_per_collection_id(self, collection_id):
        base_count = 0
        bonus_count = 0
        for collection_tracker_data in self._collections.values():
            if collection_tracker_data.collection_id == collection_id:
                if collection_tracker_data.base:
                    base_count += 1
                else:
                    bonus_count += 1
        return (base_count, bonus_count)

    def get_num_of_collected_items_by_definition_ids(self, definition_ids):
        return sum(1 for definition_id in self._collections.keys() if definition_id in definition_ids)

    def check_collection_complete_by_id(self, collection_id):
        collection_data = ObjectCollectionData.get_collection_data(collection_id)
        if collection_data is None:
            return False
        else:
            collection_count = len(collection_data.object_list)
            (collected_count, _) = self.get_num_collected_items_per_collection_id(collection_id)
            if collection_count and collected_count:
                return collection_count == collected_count
        return False

    def check_add_collection_item(self, household, obj_id, obj_def_id, sim_info=None):
        (collection_id, _collectible_data, base) = ObjectCollectionData.get_collection_info_by_definition(obj_def_id)
        if collection_id is None:
            return False
        obj = services.current_zone().find_object(obj_id)
        if obj_def_id not in self._collections:
            collection_tracker_data = CollectionTrackerData(collection_id, True, base)
            if obj is not None:
                collection_tracker_data.icon_info = create_icon_info_msg(obj.get_icon_info_data())
                quality = obj.get_collectible_quality()
                if quality is not None:
                    collection_tracker_data.quality = quality
                    obj.update_tooltip_field(TooltipFieldsComplete.quality, quality)
            self._collections[obj_def_id] = collection_tracker_data
            self.check_collection_complete(collection_id, is_base_collection=base)
            services.get_event_manager().process_events_for_household(test_events.TestEvent.CollectionChanged, household)
            msg_type = UI_pb2.CollectibleItemUpdate.TYPE_ADD
            self.send_collection_msg(msg_type, collection_tracker_data, household.id, obj_def_id, obj_id=obj_id)
        elif obj is not None:
            collection_tracker_data = self._collections[obj_def_id]
            new_quality = obj.get_collectible_quality()
            if new_quality is not None:
                obj.update_tooltip_field(TooltipFieldsComplete.quality, new_quality)
                if new_quality > collection_tracker_data.quality:
                    collection_tracker_data.icon_info = create_icon_info_msg(obj.get_icon_info_data())
                    collection_tracker_data.quality = new_quality
                    msg_type = UI_pb2.CollectibleItemUpdate.TYPE_DISCOVERY
                    self.send_collection_msg(msg_type, collection_tracker_data, household.id, obj_def_id, obj_id=obj_id)
        services.get_event_manager().process_event(test_events.TestEvent.CollectedItem, sim_info=sim_info, collection_id=collection_id, collected_item_id=obj_def_id)
        return True

    def check_collection_complete(self, collection_id, is_base_collection=True):
        collection_data = ObjectCollectionData.get_collection_data(collection_id)
        collection_count = len(collection_data.object_list)
        (collected_count, bonus_collected_count) = self.get_num_collected_items_per_collection_id(collection_id)
        if not (collection_count and collected_count):
            return
        client = services.client_manager().get_client_by_household(self._owner)
        if client is not None and client.active_sim is not None:
            message_owner_info = client.active_sim.sim_info
        else:
            message_owner_info = None
        if collection_data.first_collected_notification is not None and message_owner_info is not None and collected_count + bonus_collected_count == 1:
            dialog = collection_data.first_collected_notification(message_owner_info, None)
            dialog.show_dialog()
        if is_base_collection and collection_count == collected_count:
            if client is not None:
                with telemetry_helper.begin_hook(collection_telemetry_writer, TELEMETRY_HOOK_COLLECTION_COMPLETE, household=client.household) as hook:
                    hook.write_int(TELEMETRY_COLLECTION_ID, collection_id)
                _sting = ObjectCollectionData.COLLECTION_COMPLETED_STING(client.active_sim)
                _sting.start()
            if message_owner_info is not None:
                dialog = collection_data.completed_award_notification(message_owner_info, None)
                dialog.show_dialog()
                if collection_data.screen_slam is not None:
                    collection_data.screen_slam.send_screen_slam_message(message_owner_info, collection_data.collection_name)
            lot = services.active_lot()
            if lot is not None and collection_data.completed_award is not None:
                award_object = None
                if lot.lot_id == services.active_household_lot_id():
                    award_object = lot.create_object_in_hidden_inventory(collection_data.completed_award)
                else:
                    award_object = create_object(collection_data.completed_award, loc_type=ItemLocation.HOUSEHOLD_INVENTORY)
                    build_buy.move_object_to_household_inventory(award_object, failure_flags=HouseholdInventoryFlags.FORCE_OWNERSHIP)
                if award_object is not None:
                    key = sims4.resources.Key(sims4.resources.Types.OBJCATALOG, award_object.definition.id)
                    self.owner.add_build_buy_unlock(key)
            household = services.household_manager().get(self._owner.id)
            if household is not None:
                household.funds.add(collection_data.completed_award_money, Consts_pb2.TELEMETRY_MONEY_ASPIRATION_REWARD, None)
        elif client is not None:
            _sting = ObjectCollectionData.COLLECTION_COLLECTED_STING(client.active_sim)
            _sting.start()

    def send_collection_msg(self, msg_type, collection_tracker_data, household_id, obj_def_id, obj_id=None):
        msg = UI_pb2.CollectibleItemUpdate()
        msg.type = msg_type
        msg.collection_id = collection_tracker_data.collection_id
        msg.household_id = household_id
        if obj_id is not None:
            msg.object_id = obj_id
        msg.object_def_id = obj_def_id
        msg.quality = collection_tracker_data.quality
        if collection_tracker_data.icon_info is not None:
            msg.icon_info = collection_tracker_data.icon_info
        distributor = Distributor.instance()
        distributor.add_op_with_no_owner(GenericProtocolBufferOp(Operation.SIM_COLLECTIBLE_ITEM_UPDATE, msg))

    def send_all_collection_data(self, household_id):
        for (collectible_def_id, collection_tracker_data) in self._collections.items():
            if collection_tracker_data.new:
                msg_type = UI_pb2.CollectibleItemUpdate.TYPE_ADD
            else:
                msg_type = UI_pb2.CollectibleItemUpdate.TYPE_DISCOVERY
            self.send_collection_msg(msg_type, collection_tracker_data, household_id, collectible_def_id)

    def save_data(self, household_msg):
        for (key, value) in self._collections.items():
            with ProtocolBufferRollback(household_msg.gameplay_data.collection_data) as collection_data:
                collection_data.collectible_def_id = key
                collection_data.collection_id = value.collection_id
                collection_data.new = value.new
                collection_data.quality = value.quality
                if value.icon_info is not None:
                    collection_data.icon_info = value.icon_info

    def load_data(self, household_msg):
        self._collections.clear()
        if self.owner.all_sims_skip_load():
            return
        current_zone_id = services.current_zone_id()
        for collection in household_msg.gameplay_data.collection_data:
            base = ObjectCollectionData.is_base_object_of_collection(collection.collectible_def_id, collection.collection_id)
            fallback_definition_id = build_buy.get_vetted_object_defn_guid(current_zone_id, 0, collection.collectible_def_id)
            if fallback_definition_id != collection.collectible_def_id:
                pass
            else:
                if collection.HasField('icon_info'):
                    icon_info = ui_protocols.IconInfo()
                    icon_info.CopyFrom(collection.icon_info)
                else:
                    icon_info = None
                collection_tracker_data = CollectionTrackerData(collection.collection_id, collection.new, base, quality=collection.quality, icon_info=icon_info)
                self._collections[collection.collectible_def_id] = collection_tracker_data

class CollectableComponent(Component, HasTunableFactory, AutoFactoryInit, component_name=types.COLLECTABLE_COMPONENT):

    @staticmethod
    def _verify_tunable_callback(*args, valid_quality_states=None, **kwargs):
        if valid_quality_states is None:
            return
        states = tuple(valid_quality_states)
        if states is None or len(states) == 0:
            return
        first_state = states[0]
        for quality_state in states:
            if quality_state.state != first_state.state:
                logger.error('CollectableComponent valid_quality_states contains state values from different states.', owner='stjulien')
                return

    FACTORY_TUNABLES = {'override_slot_placement': OptionalTunable(description='\n            Whether or not this object specify the slot name where it should be \n            placed.\n            This will override the placement through slot type sets and will\n            use the hash tuned here to find where it should be placed.\n            ', tunable=Tunable(description='\n                Slot name where object should be placed.\n                ', tunable_type=str, default=''), disabled_name='No_slot_override', enabled_name='Use_custom_slot_name'), 'game_component_animation_definition': OptionalTunable(description='\n            If enabled the definition tuned will be used by the game component\n            for some types of collectibles to display a different model when\n            used by some game types.\n            e.g. Card collectibles when being used on the Card battle machine\n            will display another model on the battle screen. \n            ', tunable=TunableReference(description='\n                Definition the game component will used when collectible is \n                being used by some games (e.g. Card Battles).\n                ', manager=services.definition_manager())), 'valid_quality_states': TunableSet(description='\n            Should contain a list of valid quality states for the collectible.\n            If valid states are in this list it will be managed by the collection tracker\n            All state_values must be from the same state. If empty, quality will not be used\n            e.g. Ancient artifacts can be found broken (low quality) or intact (high quality)\n            ', tunable=TunableReference(description='\n                State value for quality of the collectible.\n                ', manager=get_instance_manager(sims4.resources.Types.OBJECT_STATE), class_restrictions='ObjectStateValue')), 'verify_tunable_callback': _verify_tunable_callback}

    def pre_add(self, *_, **__):
        (_, collectible_data, _) = ObjectCollectionData.get_collection_info_by_definition(self.owner.definition.id)
        if collectible_data is not None:
            if self.owner.has_state(ObjectCollectionData.COLLECTED_RARITY_STATE):
                self.owner.set_state(ObjectCollectionData.COLLECTED_RARITY_STATE, collectible_data.rarity, from_init=True)
            else:
                logger.error('Missing tuned rarity state on game object {}', self.owner, owner='cdimiceli')

    def on_finalize_load(self):
        quality = self.get_collectible_quality()
        if quality is not None:
            self.owner.update_tooltip_field(TooltipFieldsComplete.quality, quality)

    def on_added_to_inventory(self):
        self.add_to_collection_tracker()

    def on_state_changed(self, state, old_value, new_value, from_init):
        if old_value in ObjectCollectionData.COLLECTED_INVALID_STATES and new_value not in ObjectCollectionData.COLLECTED_INVALID_STATES:
            self.add_to_collection_tracker()

    @componentmethod_with_fallback(lambda : None)
    def add_to_collection_tracker(self):
        household = services.active_household()
        if household is not None:
            if self.owner.household_owner_id != household.id:
                return
            owner = self.owner
            if any(owner.state_value_active(invalid_state) for invalid_state in ObjectCollectionData.COLLECTED_INVALID_STATES):
                return
            inventory = self.owner.get_inventory()
            if inventory is not None and inventory.owner.is_sim:
                sim_info = inventory.owner.sim_info
            else:
                sim_info = None
            household.collection_tracker.check_add_collection_item(household, self.owner.id, self.owner.definition.id, sim_info=sim_info)

    @componentmethod_with_fallback(lambda : None)
    def get_collectible_slot(self):
        slot = self.override_slot_placement
        return slot

    @componentmethod_with_fallback(lambda : None)
    def get_game_animation_definition(self):
        return self.game_component_animation_definition

    @componentmethod_with_fallback(lambda : None)
    def get_collectible_quality(self):
        if self.valid_quality_states is None:
            return
        states = tuple(self.valid_quality_states)
        if states is None or len(states) == 0:
            return
        else:
            quality_state = states[0]
            if quality_state is not None and self.owner.has_state(quality_state.state):
                return self.owner.get_state(quality_state.state).value
