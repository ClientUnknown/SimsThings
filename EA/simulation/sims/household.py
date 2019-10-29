from collections import OrderedDictfrom event_testing.resolver import DoubleSimResolverfrom interactions.utils.loot import LootActionsfrom protocolbuffers import FileSerialization_pb2 as serialization, ResourceKey_pb2, S4Common_pb2, FileSerialization_pb2, GameplaySaveData_pb2from protocolbuffers.Consts_pb2 import TELEMETRY_HOUSEHOLD_TRANSFER_GAINfrom protocolbuffers.Consts_pb2 import TELEMETRY_HOUSEHOLD_TRANSFER_GAINfrom protocolbuffers.DistributorOps_pb2 import Operationfrom bucks.household_bucks_tracker import HouseholdBucksTrackerfrom careers.career_enums import ReceiveDailyHomeworkHelpfrom date_and_time import create_time_span, DateAndTime, DATE_AND_TIME_ZEROfrom delivery.delivery_tracker import DeliveryTrackerfrom distributor.ops import GenericProtocolBufferOpfrom distributor.rollback import ProtocolBufferRollbackfrom distributor.system import Distributorfrom event_testing import test_eventsfrom holidays.holiday_tracker import HolidayTrackerfrom household_milestones.household_milestone_tracker import HouseholdMilestoneTrackerfrom laundry.household_laundry_tracker import HouseholdLaundryTrackerfrom objects import HiddenReasonFlag, ALL_HIDDEN_REASONSfrom objects.collection_manager import CollectionTrackerfrom pets.missing_pets_tracker import MissingPetsTrackerfrom relationships.relationship_bit import RelationshipBitfrom sims import bills, sim_infofrom sims.aging.aging_tuning import AgingTuningfrom sims.baby.baby_utils import remove_stale_babies, run_baby_spawn_behaviorfrom sims.household_telemetry import send_sim_added_telemetryfrom sims.outfits.outfit_enums import OutfitCategoryfrom sims.sim_info_lod import SimInfoLODLevelfrom sims.sim_info_types import Agefrom sims.sim_info_utils import sim_info_auto_finderfrom sims.sim_spawner_enums import SimInfoCreationSourcefrom sims4.common import UnavailablePackErrorfrom sims4.tuning.tunable import TunableTuplefrom situations.service_npcs.service_npc_record import ServiceNpcRecordfrom telemetry_helper import HouseholdTelemetryTrackerfrom traits.sim_info_fixup_action import SimInfoFixupActionTimingfrom world import regionimport alarmsimport autonomy.settingsimport build_buyimport distributor.opsimport distributor.systemimport servicesimport sims.fundsimport sims.sim_infoimport sims.sim_spawnerimport sims4.logimport sims4.tuning.tunableimport singletonslogger = sims4.log.Logger('HouseholdManager', default_owner='manus')
class Household:
    SIM_SPAWN_RADIUS = sims4.tuning.tunable.Tunable(description='\n        Radius of the circle around which other family members will be spawned.\n        ', tunable_type=int, default=2)
    MAXIMUM_SIZE = sims4.tuning.tunable.Tunable(description='\n        Maximum number of Sims you can have in a household at a time.\n        ', tunable_type=int, default=8)
    ANCESTRY_PURGE_DEPTH = sims4.tuning.tunable.TunableRange(description='\n        The maximum number of links that living Sims can have with an ancestor\n        before the ancestor is purged.\n        ', tunable_type=int, default=3, minimum=1)
    NPC_HOUSEHOLD_DEFAULT_FUNDS = sims4.tuning.tunable.TunableRange(description='\n        The default amount of funds an NPC household will have. This will\n        determine how much money an NPC sims brings with them when you invite\n        to household.\n        ', tunable_type=int, default=20000, minimum=0)
    SPECIAL_FIXES = TunableTuple(description='\n        Special Case tuning to fix up bad save data\n        ', pet_relbits=TunableTuple(description='\n            Not all sims in a household with a pet have the correct pet\n            ownership relbits. If this is the case, we will fix this for the \n            active household on load.\n            ', loot_for_pets=LootActions.TunablePackSafeReference()))
    HOUSEHOLD_TRACKERS = OrderedDict((('bucks_tracker', HouseholdBucksTracker), ('laundry_tracker', HouseholdLaundryTracker), ('missing_pet_tracker', MissingPetsTracker), ('delivery_tracker', DeliveryTracker), ('_collection_tracker', CollectionTracker)))

    def __init__(self, account, starting_funds=singletons.DEFAULT):
        self.account = account
        self.id = 0
        self.manager = None
        self._name = ''
        self._description = ''
        self._home_zone_id = 0
        self.last_modified_time = 0
        self._watchers = {}
        self._autonomy_settings = autonomy.settings.AutonomySettings()
        self._sim_infos = []
        if starting_funds is singletons.DEFAULT:
            starting_funds = self.NPC_HOUSEHOLD_DEFAULT_FUNDS
        self._funds = sims.funds.FamilyFunds(self.id, starting_funds)
        self.bills_manager = bills.Bills(self)
        self._has_cheated = False
        for (tracker_attr, tracker_type) in Household.HOUSEHOLD_TRACKERS.items():
            setattr(self, tracker_attr, tracker_type(self))
        self._household_milestone_tracker = None
        self._holiday_tracker = None
        self._service_npc_record = None
        self._telemetry_tracker = HouseholdTelemetryTracker(self)
        self._last_active_sim_id = 0
        self._reward_inventory = serialization.RewardPartList()
        self._cached_billable_household_value = 0
        self._highest_earned_situation_medals = {}
        self._situation_scoring_enabled = True
        self._hidden = False
        self.creator_id = 0
        self.creator_name = ''
        self.creator_uuid = None
        self.primitives = ()
        self._adopting_sim_ids = set()
        self._always_welcome_sim_ids = set()
        self._build_buy_unlocks = set()
        self._aging_update_alarm = None
        self.needs_welcome_wagon = False
        self._home_world_id = 0
        self._last_played_home_zone_id = 0
        self._home_zone_move_in_time = DATE_AND_TIME_ZERO
        self.premade_household_id = 0
        self.premade_household_template_id = 0
        self._is_player_household = False
        self._is_played_household = False
        self.pending_urnstone_ids = []
        self._max_sim_lod = None
        self.visible_to_client = False
        self._receive_homework_help_map = {Age.TEEN: ReceiveDailyHomeworkHelp.UNCHECKED, Age.CHILD: ReceiveDailyHomeworkHelp.UNCHECKED}

    def __repr__(self):
        sim_strings = []
        for sim_info in self._sim_infos:
            sim_strings.append(str(sim_info))
        return 'Household {} ({}): {}'.format(self.name if self.name else '<Unnamed Household>', self.id, '; '.join(sim_strings))

    def __len__(self):
        return len(self._sim_infos)

    def __iter__(self):
        return iter(self._sim_infos)

    @distributor.fields.Field(op=distributor.ops.SetHouseholdName)
    def name(self):
        return self._name

    @name.setter
    def name(self, value):
        self._name = value

    @distributor.fields.Field(op=distributor.ops.SetHouseholdDescription)
    def description(self):
        return self._description

    @description.setter
    def description(self, value):
        self._description = value

    @distributor.fields.Field(op=distributor.ops.SetHouseholdHidden)
    def hidden(self):
        return self._hidden

    resend_hidden = hidden.get_resend()

    @distributor.fields.Field(op=distributor.ops.SetHouseholdSims)
    def sim_infos(self):
        return tuple(self._sim_infos)

    resend_sim_infos = sim_infos.get_resend()

    @property
    def is_active_household(self):
        return self.id == services.active_household_id()

    @distributor.fields.Field(op=distributor.ops.SetPlayerProtectedStatus)
    def is_player_household(self):
        return self._is_player_household

    resend_is_player_household = is_player_household.get_resend()

    @distributor.fields.Field(op=distributor.ops.SetPlayedStatus)
    def is_played_household(self):
        return self._is_played_household

    resend_is_played_household = is_played_household.get_resend()

    @sim_info_auto_finder
    def get_pending_urnstone_sim_infos(self):
        return self.pending_urnstone_ids

    def on_sim_lod_update(self, sim_info_updated, old_lod, new_lod):
        if self._max_sim_lod is None:
            return
        if new_lod >= self._max_sim_lod:
            return
        max_lod = max((sim_info.lod for sim_info in self if sim_info is not sim_info_updated), default=new_lod)
        if new_lod > max_lod:
            max_lod = new_lod
        if max_lod >= self._max_sim_lod:
            return
        self._max_sim_lod = max_lod
        self.cleanup_trackers(new_lod=new_lod)

    def _initialize_max_household_lod(self):
        self._max_sim_lod = max((sim_info.lod for sim_info in self), default=SimInfoLODLevel.MINIMUM)

    def cleanup_trackers(self, new_lod=None):
        for (tracker_attr, tracker_type) in Household.HOUSEHOLD_TRACKERS.items():
            tracker = getattr(self, tracker_attr, None)
            if not new_lod is None:
                if not tracker_type.is_valid_for_lod(new_lod):
                    tracker.household_lod_cleanup()
            tracker.household_lod_cleanup()

    def set_to_hidden(self, family_funds=singletons.DEFAULT):
        services.business_service().clear_owned_business(self.id)
        if self.home_zone_id:
            self.clear_household_lot_ownership()
        self._hidden = True
        self._is_player_household = False
        self._is_played_household = False
        self._funds = sims.funds.FamilyFunds(self.id, self.NPC_HOUSEHOLD_DEFAULT_FUNDS if family_funds is singletons.DEFAULT else family_funds)
        self.bucks_tracker.clear_bucks_tracker()
        self._collection_tracker.clear_collection_tracker()
        self._service_npc_record = None
        self._reward_inventory = serialization.RewardPartList()
        self.resend_hidden()
        self.resend_is_player_household()
        self.resend_is_played_household()

    def handle_adultless_household(self, skip_hidden=False, skip_premade=False):
        if skip_hidden and self._hidden:
            return
        if skip_premade and self.premade_household_id > 0:
            return
        if not any(sim_info.can_live_alone for sim_info in self):
            for sim_info in tuple(self):
                sim_to_destroy = sim_info.get_sim_instance(allow_hidden_flags=ALL_HIDDEN_REASONS)
                if sim_to_destroy is not None:
                    sim_to_destroy.destroy(source=sim_to_destroy, cause='Last adult sim dying, destroying dependent Sims.')
                self.remove_sim_info(sim_info, destroy_if_empty_household=True)
                sim_info.transfer_to_hidden_household()
                sim_info.request_lod(SimInfoLODLevel.MINIMUM)
            self.set_to_hidden()

    @property
    def home_zone_move_in_time(self):
        return self._home_zone_move_in_time

    @distributor.fields.Field(op=distributor.ops.SetHouseholdHomeZoneId)
    def home_zone_id(self):
        return self._home_zone_id

    resend_home_zone_id = home_zone_id.get_resend()

    def get_home_world_id(self):
        return self._home_world_id

    def set_home_world_id(self, world_id):
        if self.home_zone_id != 0:
            logger.error('Trying to set home world for {} to {} when household lives on zone {}', self, world_id, self.home_zone_id)
            return
        self._home_world_id = world_id

    def get_home_region(self):
        if self._home_zone_id != 0:
            return region.get_region_instance_from_zone_id(self._home_zone_id)
        elif self._home_world_id != 0:
            return region.get_region_instance_from_world_id(self._home_world_id)
        return 0

    @property
    def valid_for_distribution(self):
        if self.id:
            return True
        return False

    @property
    def funds(self):
        return self._funds

    @property
    def rebate_manager(self):
        return self._rebate_manager

    @property
    def situation_scoring_enabled(self):
        return self._situation_scoring_enabled

    def set_situation_scoring(self, scoring_enabled):
        self._situation_scoring_enabled = scoring_enabled

    @property
    def telemetry_tracker(self):
        return self._telemetry_tracker

    @property
    def collection_tracker(self):
        return self._collection_tracker

    def get_household_collections(self):
        return self.collection_tracker.collection_data

    @property
    def household_milestone_tracker(self):
        return self._household_milestone_tracker

    @property
    def holiday_tracker(self):
        return self._holiday_tracker

    def add_adopting_sim(self, sim_id):
        self._adopting_sim_ids.add(sim_id)

    def remove_adopting_sim(self, sim_id):
        if sim_id in self._adopting_sim_ids:
            self._adopting_sim_ids.remove(sim_id)

    def add_always_welcome_sim(self, sim_id):
        self._always_welcome_sim_ids.add(sim_id)

    @property
    def always_welcomed_sims(self):
        return self._always_welcome_sim_ids

    @property
    def free_slot_count(self):

        def slot_count(sim_info):
            if sim_info.pregnancy_tracker is not None:
                pregnancy_tracker = sim_info.pregnancy_tracker
                if pregnancy_tracker.is_pregnant:
                    return 1 + pregnancy_tracker.offspring_count
            return 1

        used_slot_count = sum(slot_count(sim_info) for sim_info in self) + len(self._adopting_sim_ids)
        return self.MAXIMUM_SIZE - used_slot_count

    @property
    def household_size(self):
        return len(self._sim_infos)

    @property
    def zone_id(self):
        if self._sim_infos:
            return self._sim_infos[0].zone_id
        return 0

    def has_home_zone_been_active(self):
        return self._last_played_home_zone_id == self.home_zone_id

    def is_first_time_playing(self):
        return self.is_active_household and self._last_played_home_zone_id == 0

    def _get_updated_last_played_home_zone_id(self):
        if self.is_active_household:
            return self._home_zone_id
        if self._home_zone_id == self._last_played_home_zone_id:
            return self._home_zone_id
        elif services.owning_household_id_of_active_lot() == self.id:
            return self._home_zone_id
        return 0

    def get_highest_medal_for_situation(self, situation_id):
        highest_medal = self._highest_earned_situation_medals.get(situation_id)
        if highest_medal is None:
            return -1
        return highest_medal

    def set_highest_medal_for_situation(self, situation_id, medal_earned):
        if situation_id is not None:
            highest_medal = self._highest_earned_situation_medals.get(situation_id)
            if highest_medal is None or highest_medal < medal_earned:
                self._highest_earned_situation_medals[situation_id] = medal_earned

    def get_sims_at_home_not_instanced_not_busy(self):
        at_home_sim_ids = set()
        for sim_info in self.sim_info_gen():
            if sim_info.zone_id == self.home_zone_id and not (sim_info.is_instanced(allow_hidden_flags=HiddenReasonFlag.NOT_INITIALIZED) or sim_info.career_tracker.currently_during_work_hours):
                at_home_sim_ids.add(sim_info.id)
        return at_home_sim_ids

    def get_sims_at_home(self):
        at_home_sim_ids = set()
        current_zone_is_home_zone = services.current_zone_id() == self.home_zone_id
        for sim_info in self.sim_info_gen():
            if current_zone_is_home_zone:
                if sim_info.is_instanced(allow_hidden_flags=HiddenReasonFlag.NOT_INITIALIZED):
                    at_home_sim_ids.add(sim_info.id)
            at_home_sim_ids.add(sim_info.id)
        return at_home_sim_ids

    def household_net_worth(self, billable=False):
        household_inventory_value = build_buy.get_household_inventory_value(self.id)
        if household_inventory_value is None:
            household_inventory_value = 0
        sim_inventories_value = 0
        for sim_info in self.sim_info_gen():
            sim_inventories_value += sim_info.inventory_value()
        final_household_value = self._cached_billable_household_value + household_inventory_value + sim_inventories_value
        home_zone = services.get_zone(self.home_zone_id)
        if home_zone is None and billable:
            return final_household_value
        if not billable:
            household_funds = self._funds.money
            if home_zone is None:
                return final_household_value + household_funds
        billable_value = 0
        billable_value += home_zone.lot.furnished_lot_value
        plex_service = services.get_plex_service()
        is_plex = plex_service.is_zone_a_plex(self.home_zone_id)
        for obj in services.object_manager().values():
            if obj.is_sim:
                pass
            elif obj.get_household_owner_id() == self.id:
                pass
            elif not home_zone.lot.is_position_on_lot(obj.position):
                pass
            elif is_plex and plex_service.get_plex_zone_at_position(obj.position, obj.level) != self.home_zone_id:
                pass
            else:
                billable_value -= obj.current_value
                obj_inventory = obj.inventory_component
                if obj_inventory is not None:
                    billable_value -= obj_inventory.inventory_value
        if billable_value < 0:
            logger.error('The billable household value for household {} is a negative number ({}). Defaulting to 0.', self, billable_value, owner='tastle')
            billable_value = 0
        self._cached_billable_household_value = billable_value
        final_household_value = self._cached_billable_household_value + household_inventory_value + sim_inventories_value
        if billable:
            return final_household_value
        return final_household_value + household_funds

    @property
    def client(self):
        return services.client_manager().get_client_by_household_id(self.id)

    def on_all_households_and_sim_infos_loaded(self):
        self.bills_manager.on_all_households_and_sim_infos_loaded()
        self.bucks_tracker.on_all_households_and_sim_infos_loaded()
        self.missing_pet_tracker.on_all_households_and_sim_infos_loaded()
        self._load_fixup_always_welcomed_sims()
        self._initialize_max_household_lod()
        if self.SPECIAL_FIXES.pet_relbits.loot_for_pets is not None:
            for pet in self.get_pets_gen():
                for other_family_member in (family_member for family_member in self if pet is not family_member):
                    self.SPECIAL_FIXES.pet_relbits.loot_for_pets.apply_to_resolver(DoubleSimResolver(other_family_member, pet))

    def _load_fixup_always_welcomed_sims(self):
        mgr = services.sim_info_manager()
        self._always_welcome_sim_ids = set([i for i in self._always_welcome_sim_ids if mgr.is_sim_id_valid(i)])

    def on_active_sim_set(self):
        self.bills_manager.on_active_sim_set()

    def on_client_disconnect(self):
        self.telemetry_tracker.on_client_disconnect()
        if self._aging_update_alarm is not None:
            alarms.cancel_alarm(self._aging_update_alarm)

    def on_zone_load(self):
        if self.bucks_tracker is not None:
            self.bucks_tracker.on_zone_load()
        if self.is_active_household:
            self._collection_tracker.send_all_collection_data(self.id)
        self.delivery_tracker.on_zone_load()
        self.missing_pet_tracker.fix_up_data()

    def on_zone_unload(self):
        self._last_played_home_zone_id = self._get_updated_last_played_home_zone_id()

    def instanced_sims_gen(self, allow_hidden_flags=0):
        for sim_info in self._sim_infos:
            if sim_info.is_instanced(allow_hidden_flags=allow_hidden_flags):
                yield sim_info.get_sim_instance(allow_hidden_flags=allow_hidden_flags)

    def instanced_pets_gen(self):
        for sim in self.instanced_sims_gen():
            if sim.is_pet:
                yield sim

    def sim_info_gen(self):
        for sim_info in self._sim_infos:
            yield sim_info

    def baby_info_gen(self):
        for sim_info in self._sim_infos:
            if sim_info.is_baby:
                yield sim_info

    def teen_or_older_info_gen(self):
        for sim_info in self._sim_infos:
            if sim_info.is_teen_or_older:
                yield sim_info

    def get_humans_gen(self):
        for sim_info in self._sim_infos:
            if sim_info.is_human:
                yield sim_info

    def get_pets_gen(self):
        for sim_info in self._sim_infos:
            if sim_info.is_pet:
                yield sim_info

    def can_live_alone_info_gen(self):
        for sim_info in self._sim_infos:
            if sim_info.can_live_alone:
                yield sim_info

    def get_travel_group(self):
        for sim_info in self:
            if sim_info.travel_group_id:
                return services.travel_group_manager().get(sim_info.travel_group_id)

    def any_member_belong_to_travel_group_id(self, travel_group_id):
        return any(sim_info.travel_group_id == travel_group_id for sim_info in self)

    def any_member_in_travel_group(self):
        return any(sim_info.is_in_travel_group() for sim_info in self)

    def add_cas_part_to_reward_inventory(self, cas_part):
        reward_part_data = serialization.RewardPartData()
        reward_part_data.part_id = cas_part
        reward_part_data.is_new_reward = True
        self._reward_inventory.reward_parts.append(reward_part_data)

    def part_in_reward_inventory(self, cas_part):
        for reward_part_data in self._reward_inventory.reward_parts:
            if reward_part_data.part_id == cas_part:
                return True
        return False

    def get_create_op(self, *args, **kwargs):
        return distributor.ops.HouseholdCreate(self, *args, **kwargs)

    def get_delete_op(self):
        return distributor.ops.HouseholdDelete()

    def get_create_after_objs(self):
        return ()

    def on_add(self):
        if self.account:
            self.account.add_household(self)
        self._funds.set_household_id(self.id)
        distributor_inst = distributor.system.Distributor.instance()
        distributor_inst.add_object(self)

    def on_remove(self):
        if self.account:
            self.account.remove_household(self)
        current_zone = services.current_zone()
        if current_zone is not None and not current_zone.is_zone_shutting_down:
            services.business_service().clear_owned_business(self.id)
        distributor_inst = distributor.system.Distributor.instance()
        distributor_inst.remove_object(self)
        if self._holiday_tracker is not None:
            self._holiday_tracker.shutdown()
            self._holiday_tracker = None

    def can_add_sim_info(self, sim_info):
        if sim_info in self:
            return False
        pregnancy_tracker = sim_info.pregnancy_tracker
        if pregnancy_tracker is not None and pregnancy_tracker.is_pregnant:
            requested_slot_count = 1 + pregnancy_tracker.offspring_count
        else:
            requested_slot_count = 1
        return requested_slot_count <= self.free_slot_count

    def add_sim_info(self, sim_info, process_events=True):
        self._sim_infos.append(sim_info)
        if self.home_zone_id:
            for trait in tuple(t for t in sim_info.trait_tracker if t.is_npc_only):
                sim_info.remove_trait(trait)
            for buff in tuple(b for b in sim_info.Buffs if b.is_npc_only):
                sim_info.remove_buff_entry(buff)
        if services.active_household_id() == self.id:
            if not sim_info.request_lod(SimInfoLODLevel.ACTIVE):
                logger.error("Failed to set active sim's LOD: {}", self, owner='tingyul')
        elif sim_info.lod == SimInfoLODLevel.ACTIVE and not sim_info.request_lod(SimInfoLODLevel.FULL):
            logger.error("Failed to set non-active sim's LOD: {}", self, owner='tingyul')
        if process_events:
            if self._is_played_household:
                send_sim_added_telemetry(sim_info)
            self._on_sim_added(sim_info)
            self.resend_sim_infos()

    def _on_sim_added(self, sim_info):
        self.notify_dirty()
        if services.current_zone().is_zone_running:
            services.get_event_manager().process_events_for_household(test_events.TestEvent.HouseholdChanged, self)
            if self._holiday_tracker is not None:
                self._holiday_tracker.on_sim_added(sim_info)
        for unlock in sim_info.build_buy_unlocks:
            self.add_build_buy_unlock(unlock)
        sim_info.refresh_age_settings()

    def remove_sim_info(self, sim_info, destroy_if_empty_household=False, process_events=True):
        self._sim_infos.remove(sim_info)
        sim_info.assign_to_household(None, assign_is_npc=False)
        familiar_tracker = sim_info.familiar_tracker
        if familiar_tracker is not None:
            familiar_tracker.on_household_member_removed()
        for other_sim_info in self._sim_infos:
            familiar_tracker = other_sim_info.familiar_tracker
            if familiar_tracker is not None:
                familiar_tracker.on_household_member_removed()
        if process_events:
            self.notify_dirty()
            if services.current_zone().is_zone_running:
                services.get_event_manager().process_events_for_household(test_events.TestEvent.HouseholdChanged, self)
            self.resend_sim_infos()
        if destroy_if_empty_household:
            self.destroy_household_if_empty()

    def destroy_household_if_empty(self):
        if not self._sim_infos:
            services.get_persistence_service().del_household_proto_buff(self.id)
            services.household_manager().remove(self)
            return True
        return False

    def sim_in_household(self, sim_id):
        for sim_info in self._sim_infos:
            if sim_info.sim_id == sim_id:
                return True
        return False

    def all_sims_skip_load(self):
        return all(sim_info.sim_creation_path != serialization.SimData.SIMCREATION_NONE for sim_info in self._sim_infos)

    def add_sim_to_household(self, sim):
        self.add_sim_info_to_household(sim.sim_info)

    def add_sim_info_to_household(self, sim_info):
        sim_info.assign_to_household(self)
        self.add_sim_info(sim_info)
        sim_info.set_default_relationships(reciprocal=True, update_romance=False)

    @property
    def build_buy_unlocks(self):
        return self._build_buy_unlocks

    def add_build_buy_unlock(self, unlock):
        self._build_buy_unlocks.add(unlock)

    def get_sim_info_by_id(self, sim_id):
        for sim_info in self._sim_infos:
            if sim_info.sim_id == sim_id:
                return sim_info

    def add_watcher(self, handle, f):
        self._watchers[handle] = f
        return handle

    def remove_watcher(self, handle):
        return self._watchers.pop(handle)

    def notify_dirty(self):
        for watcher in self._watchers.values():
            watcher()

    def set_default_relationships(self):
        for sim_info in self:
            sim_info.set_default_relationships(reciprocal=True)

    def refresh_sim_data(self, sim_id, spawn=False, selectable=False):
        try:
            sim_proto = services.get_persistence_service().get_sim_proto_buff(sim_id)
            sim_info = services.sim_info_manager().get(sim_id)
            if sim_info is not None:
                if sim_info.revision < sim_proto.revision:
                    current_outfit = sim_info.get_current_outfit()
                    sim_info.load_sim_info(sim_proto)
                    sim_info.resend_outfits()
                    if sim_info.has_outfit(current_outfit):
                        sim_info._current_outfit = current_outfit
                    else:
                        sim_info._current_outfit = (OutfitCategory.EVERYDAY, 0)
            else:
                sim_info = sims.sim_info.SimInfo(sim_id=sim_id, account=self.account)
                sim_info.load_sim_info(sim_proto)
            if not self.sim_in_household(sim_id):
                sim_info.assign_to_household(self, assign_is_npc=False)
                self.add_sim_info(sim_info)
                sim_info.set_default_relationships(reciprocal=True, update_romance=False)
            if sim_info.pregnancy_tracker is not None:
                sim_info.pregnancy_tracker.refresh_pregnancy_data(on_create=lambda s: self.refresh_sim_data(s.id, spawn=spawn, selectable=selectable))
            if spawn:
                if sim_info.is_baby:
                    run_baby_spawn_behavior(sim_info)
                else:
                    sims.sim_spawner.SimSpawner.spawn_sim(sim_info, None)
            if selectable:
                client = services.client_manager().get_client_by_household_id(self.id)
                client.add_selectable_sim_info(sim_info)
                if not spawn:
                    sim_info.inject_into_inactive_zone(self.home_zone_id)
            sim_info.apply_fixup_actions(SimInfoFixupActionTiming.ON_ADDED_TO_ACTIVE_HOUSEHOLD)
        except Exception:
            logger.exception('Sim {} failed to load', sim_id)

    def load_data(self, household_msg, fixup_helper):
        self.id = household_msg.household_id
        self.premade_household_id = household_msg.premade_household_id
        self.premade_household_template_id = household_msg.premade_household_template_id
        self._name = household_msg.name
        self._description = household_msg.description
        self._hidden = household_msg.hidden
        self._last_active_sim_id = household_msg.last_played_sim_id
        if services.active_household_id() == self.id:
            self._is_player_household = True
            self._is_played_household = True
        else:
            self._is_player_household = household_msg.is_player
            self._is_played_household = not household_msg.is_unplayed
        update_player_status_from_creation_source = not self._hidden and not household_msg.HasField('is_player')
        if self._is_played_household:
            self._is_player_household = True
        if self._hidden:
            self._is_player_household = False
        move_in_time = DateAndTime(household_msg.gameplay_data.home_zone_move_in_ticks)
        self.set_household_lot_ownership(zone_id=household_msg.home_zone, move_in_time=move_in_time, from_load=True)
        if household_msg.gameplay_data.home_world_id != 0:
            self._home_world_id = household_msg.gameplay_data.home_world_id
        self._last_played_home_zone_id = household_msg.gameplay_data.last_played_home_zone_id
        self.last_modified_time = household_msg.last_modified_time
        self._funds = sims.funds.FamilyFunds(self.id, household_msg.money)
        self._rebate_manager = sims.rebate_manager.RebateManager(self)
        self.creator_id = household_msg.creator_id
        self.creator_name = household_msg.creator_name
        self.creator_uuid = household_msg.creator_uuid
        resend_sim_infos = False
        if household_msg.home_zone == 0 and household_msg.sims.ids:
            default_lod = SimInfoLODLevel.FULL if self.is_played_household else SimInfoLODLevel.BASE
            for sim_id in household_msg.sims.ids:
                try:
                    sim_proto = services.get_persistence_service().get_sim_proto_buff(sim_id)
                    if sim_proto is None:
                        continue
                    sim_info = services.sim_info_manager().get(sim_id)
                    existing_household_id = None
                    if sim_info is None:
                        sim_info = sims.sim_info.SimInfo(sim_id=sim_id, account=self.account)
                    else:
                        existing_household_id = sim_info.household_id
                    try:
                        sim_info.load_sim_info(sim_proto, default_lod=default_lod)
                    except UnavailablePackError as e:
                        logger.warn('Sim {} failed to load: {}', sim_id, e)
                        continue
                    if not self.sim_in_household(sim_id):
                        if existing_household_id is not None and existing_household_id != self.id:
                            other_household = services.household_manager().get(existing_household_id)
                            if other_household is None or self._sim_should_be_in_other_household(other_household, sim_info):
                                if fixup_helper is not None:
                                    fixup_helper.add_shared_sim_household(self)
                                else:
                                    logger.error('Removing {} from household {} with no fixup helper. Household may leak.', sim_info, self)
                                sim_info.assign_to_household(other_household)
                                if self.home_zone_id != 0:
                                    resend_sim_infos = True
                                continue
                            other_household.remove_sim_info(sim_info, process_events=False)
                            if other_household.home_zone_id != 0:
                                other_household.resend_sim_infos()
                            if fixup_helper is not None:
                                fixup_helper.add_shared_sim_household(other_household)
                            else:
                                logger.error('Removing {} from household {} with no fixup helper. Household may leak.', sim_info, other_household)
                            logger.warn('{} in wrong household {} will  be moved back into household {} where they belong.', sim_info, other_household, self)
                        self.add_sim_info(sim_info, process_events=False)
                        if sim_info.household_id != self.id:
                            if fixup_helper is not None:
                                fixup_helper.add_shared_sim_household(self)
                            logger.warn('{} household id {} will  be trumped with the household {} they now belong.', sim_info, sim_info.household_id, self)
                            sim_info.assign_to_household(self)
                except:
                    logger.exception('Sim {} failed to load', sim_id)
        if any(sim_info.creation_source.is_creation_source(SimInfoCreationSource.CAS_INITIAL | SimInfoCreationSource.CAS_REENTRY | SimInfoCreationSource.GALLERY) for sim_info in self):
            self._is_player_household = True
        self.bills_manager.load_data(household_msg)
        self._cached_billable_household_value = household_msg.gameplay_data.billable_household_value
        self.collection_tracker.load_data(household_msg)
        self.bucks_tracker.load_data(household_msg.gameplay_data)
        self.missing_pet_tracker.load_data(household_msg.gameplay_data)
        self.laundry_tracker.load_data(household_msg.gameplay_data)
        self.delivery_tracker.load_data(household_msg.gameplay_data)
        for record_msg in household_msg.gameplay_data.service_npc_records:
            record = self.get_service_npc_record(record_msg.service_type, add_if_no_record=True)
            record.load_npc_record(record_msg)
        for situation_medal in household_msg.gameplay_data.highest_earned_situation_medals:
            self._highest_earned_situation_medals[situation_medal.situation_id] = situation_medal.medal
        self._reward_inventory = serialization.RewardPartList()
        self._reward_inventory.CopyFrom(household_msg.reward_inventory)
        if update_player_status_from_creation_source and hasattr(household_msg.gameplay_data, 'build_buy_unlock_list'):
            for key_proto in household_msg.gameplay_data.build_buy_unlock_list.resource_keys:
                key = sims4.resources.Key(key_proto.type, key_proto.instance, key_proto.group)
                self._build_buy_unlocks.add(key)
        if hasattr(household_msg.gameplay_data, 'situation_scoring_enabled'):
            self._situation_scoring_enabled = household_msg.gameplay_data.situation_scoring_enabled
        self._always_welcome_sim_ids = set(household_msg.gameplay_data.always_welcomed_sim_ids)
        self.needs_welcome_wagon = household_msg.needs_welcome_wagon
        self.pending_urnstone_ids.clear()
        self.pending_urnstone_ids.extend(household_msg.pending_urnstones.ids)
        if self.is_active_household:
            self._household_milestone_tracker = HouseholdMilestoneTracker()
            self._household_milestone_tracker.load(blob=household_msg.gameplay_data.household_milestone_tracker)
            self._holiday_tracker = HolidayTracker(self)
            self._holiday_tracker.load_holiday_tracker(household_msg.gameplay_data.holiday_tracker)
        return resend_sim_infos

    def _sim_should_be_in_other_household(self, other_household, sim_info):
        active_household_id = services.active_household_id()
        if active_household_id == self.id:
            return False
        if active_household_id == other_household.id:
            return True
        elif self.home_zone_id == 0 != other_household.home_zone_id == 0:
            if self.home_zone_id != 0:
                return False
            return True
        elif self.is_played_household != other_household.is_played_household:
            if self.is_played_household:
                return False
            return True
        elif self.is_player_household != other_household.is_player_household:
            if self.is_player_household:
                return False
            return True
        return True
        if self.is_played_household != other_household.is_played_household:
            if self.is_played_household:
                return False
            return True
        elif self.is_player_household != other_household.is_player_household:
            if self.is_player_household:
                return False
            return True
        return True
        if self.id == sim_info.household_id:
            return True
        elif other_household.id == sim_info.household_id:
            return False
        return True

    def populate_household_data(self, household_msg):
        inventory = serialization.ObjectList()
        inventory.CopyFrom(household_msg.inventory)
        household_milestone_msg = GameplaySaveData_pb2.HouseholdMilestoneDataTracker()
        if self._household_milestone_tracker is None:
            household_milestone_msg.CopyFrom(household_msg.gameplay_data.household_milestone_tracker)
        holiday_tracker_msg = GameplaySaveData_pb2.HolidayTracker()
        if self._holiday_tracker is None:
            holiday_tracker_msg.CopyFrom(household_msg.gameplay_data.holiday_tracker)
        household_msg.Clear()
        household_msg.account_id = self.account.id
        household_msg.household_id = self.id
        household_msg.name = self.name
        household_msg.description = self.description
        household_msg.home_zone = self.home_zone_id
        household_msg.last_modified_time = self.last_modified_time
        household_msg.money = self.funds.money
        household_msg.hidden = self.hidden
        household_msg.creator_id = self.creator_id
        household_msg.creator_name = self.creator_name
        if self.creator_uuid is not None:
            household_msg.creator_uuid = self.creator_uuid
        household_msg.inventory = inventory
        household_msg.reward_inventory = self._reward_inventory
        household_msg.gameplay_data.home_world_id = self._home_world_id
        household_msg.gameplay_data.last_played_home_zone_id = self._get_updated_last_played_home_zone_id()
        household_msg.gameplay_data.build_buy_unlock_list = ResourceKey_pb2.ResourceKeyList()
        for unlock in self.build_buy_unlocks:
            key_proto = sims4.resources.get_protobuff_for_key(unlock)
            household_msg.gameplay_data.build_buy_unlock_list.resource_keys.append(key_proto)
        household_msg.gameplay_data.situation_scoring_enabled = self._situation_scoring_enabled
        household_msg.gameplay_data.always_welcomed_sim_ids.extend(self.always_welcomed_sims)
        if self.sim_in_household(self._last_active_sim_id):
            household_msg.last_played_sim_id = self._last_active_sim_id
        household_msg.is_unplayed = not self._is_played_household
        household_msg.is_player = self._is_player_household
        household_msg.gameplay_data.billable_household_value = self.household_net_worth(billable=True)
        household_msg.gameplay_data.ClearField('highest_earned_situation_medals')
        for (situation_id, medal) in self._highest_earned_situation_medals.items():
            with ProtocolBufferRollback(household_msg.gameplay_data.highest_earned_situation_medals) as situation_medal:
                situation_medal.situation_id = situation_id
                situation_medal.medal = medal
        self.bills_manager.save_data(household_msg)
        self.collection_tracker.save_data(household_msg)
        self.bucks_tracker.save_data(household_msg.gameplay_data)
        self.missing_pet_tracker.save_data(household_msg.gameplay_data)
        self.laundry_tracker.save_data(household_msg.gameplay_data)
        self.delivery_tracker.save_data(household_msg.gameplay_data)
        if self._service_npc_record is not None:
            for service_record in self._service_npc_record.values():
                with ProtocolBufferRollback(household_msg.gameplay_data.service_npc_records) as record_msg:
                    service_record.save_npc_record(record_msg)
        household_msg.gameplay_data.home_zone_move_in_ticks = self._home_zone_move_in_time.absolute_ticks()
        id_list = S4Common_pb2.IdList()
        for sim_info in self:
            id_list.ids.append(sim_info.id)
        household_msg.sims = id_list
        household_msg.pending_urnstones.ids.extend(self.pending_urnstone_ids)
        household_msg.needs_welcome_wagon = self.needs_welcome_wagon
        if self.premade_household_id > 0:
            household_msg.premade_household_id = self.premade_household_id
        if self.premade_household_template_id > 0:
            household_msg.premade_household_template_id = self.premade_household_template_id
        if self._household_milestone_tracker is not None:
            self._household_milestone_tracker.save(blob=household_milestone_msg)
        household_msg.gameplay_data.household_milestone_tracker = household_milestone_msg
        if self._holiday_tracker is not None:
            self._holiday_tracker.save_holiday_tracker(holiday_tracker_msg)
        household_msg.gameplay_data.holiday_tracker = holiday_tracker_msg

    def save_data(self):
        household_msg = services.get_persistence_service().get_household_proto_buff(self.id)
        if household_msg is None:
            household_msg = services.get_persistence_service().add_household_proto_buff(self.id)
        self.populate_household_data(household_msg)
        return True

    def get_service_npc_record(self, service_guid64, add_if_no_record=True):
        if self._service_npc_record is None:
            if add_if_no_record:
                self._service_npc_record = {}
            else:
                return
        record = self._service_npc_record.get(service_guid64)
        if add_if_no_record:
            record = ServiceNpcRecord(service_guid64, self)
            self._service_npc_record[service_guid64] = record
        return record

    def get_all_hired_service_npcs(self):
        all_hired = []
        if self._service_npc_record is None:
            return all_hired
        for (service_guid64, record) in self._service_npc_record.items():
            if record.hired:
                all_hired.append(service_guid64)
        return all_hired

    def get_preferred_service_npcs(self):
        sim_ids = set()
        if self._service_npc_record is None:
            return sim_ids
        for record in self._service_npc_record.values():
            if record.preferred_sim_ids:
                sim_ids.update(record.preferred_sim_ids)
        return sim_ids

    def get_all_prefered_sim_id_service_id(self):
        if self._service_npc_record is None:
            return
        preferred_services = []
        for record in self._service_npc_record.values():
            for sim_id in record.preferred_sim_ids:
                preferred_services.append((sim_id, record.service_id))
        return preferred_services

    def get_all_fired_service_npc_ids(self):
        sim_ids = set()
        if self._service_npc_record is None:
            return sim_ids
        for record in self._service_npc_record.values():
            if record.fired_sim_ids:
                sim_ids.update(record.fired_sim_ids)
        return sim_ids

    def load_fixup_service_npcs(self):
        if self._service_npc_record is not None:
            for record in self._service_npc_record.values():
                record.load_fixup()

    def on_active_sim_changed(self, new_sim):
        self._last_active_sim_id = new_sim.id

    def considers_current_zone_its_residence(self):
        current_zone_id = services.current_zone_id()
        if self.home_zone_id == current_zone_id:
            return True
        for sim_info in self:
            travel_group = sim_info.travel_group
            if travel_group is not None and travel_group.zone_id == current_zone_id:
                return True
        return False

    def available_to_populate_zone(self):
        if self.home_zone_id:
            return False
        if self.hidden:
            return False
        if not any(s.is_human for s in self):
            return False
        for sim_info in self:
            travel_group = sim_info.travel_group
            if travel_group is not None:
                return False
        return True

    def merge(self, merge_with_id, should_spawn=True, selectable=True):
        persistence_service = services.get_persistence_service()
        otherhouse = persistence_service.get_household_proto_buff(merge_with_id)
        if selectable:
            self._funds.add(otherhouse.money, TELEMETRY_HOUSEHOLD_TRANSFER_GAIN, None)
            self._reward_inventory.reward_parts.extend(otherhouse.reward_inventory.reward_parts)
        travel_group = self.get_travel_group()
        if travel_group is not None:
            current_zone = services.current_zone()
            if travel_group.zone_id == current_zone.id:
                should_spawn = False
            else:
                zone_proto = persistence_service.get_neighborhood_proto_buf_from_zone_id(travel_group.zone_id)
                should_spawn = zone_proto.neighborhood_id != current_zone.neighborhood_id
        for sim_id in otherhouse.sims.ids:
            self.refresh_sim_data(sim_id, spawn=should_spawn, selectable=selectable)
        persistence_service.del_household_proto_buff(merge_with_id)

    @property
    def autonomy_settings(self):
        return self._autonomy_settings

    def initialize_sim_infos(self):
        remove_stale_babies(self)
        for sim_info in self._sim_infos:
            self._on_sim_added(sim_info)

    def _send_household_aging_update(self, _):
        for sim_info in self._sim_infos:
            sim_info.send_age_progress_bar_update()

    def refresh_aging_updates(self, sim_info):
        sim_info.send_age_progress_bar_update()
        if self._aging_update_alarm is None:
            self._age_update_handle = alarms.add_alarm(self, create_time_span(days=AgingTuning.AGE_PROGRESS_UPDATE_TIME), self._send_household_aging_update, True)

    def clear_household_lot_ownership(self):
        self.set_household_lot_ownership(zone_id=0)

    def set_household_lot_ownership(self, *, zone_id, move_in_time=None, from_load=False):
        if self.home_zone_id:
            services.get_zone_manager().clear_lot_ownership(self.home_zone_id)
        if zone_id:
            zone_data_proto = services.get_persistence_service().get_zone_proto_buff(zone_id)
            zone_data_proto.nucleus_id = self.account.id
            zone_data_proto.household_id = self.id
            if self.is_active_household and services.current_zone().lot_owner_household_changed_between_save_and_load():
                services.get_door_service().unlock_all_doors()
            lot_decoration_service = services.lot_decoration_service()
            neighborhood_proto = services.get_persistence_service().get_neighborhood_proto_buff(zone_data_proto.neighborhood_id)
            for lot_owner_info in neighborhood_proto.lots:
                if lot_owner_info.zone_instance_id == zone_id:
                    lot_owner_info.ClearField('lot_owner')
                    if from_load or lot_decoration_service is not None:
                        lot_decoration_service.handle_lot_owner_changed(zone_id, self)
                    with ProtocolBufferRollback(lot_owner_info.lot_owner) as household_account_pair_msg:
                        household_account_pair_msg.household_id = self.id
                        household_account_pair_msg.nucleus_id = self.account.id
                        household_account_pair_msg.persona_name = self.account.persona_name
                    break
            self._home_world_id = zone_data_proto.world_id
        self._home_zone_id = zone_id
        if not from_load:
            self.resend_home_zone_id()
        self._home_zone_move_in_time = move_in_time or services.time_service().sim_now

    def move_object_to_sim_or_household_inventory(self, obj, sort_by_distance=False):
        instanced_sims = [sim for sim in self.instanced_sims_gen() if sim.sim_info.can_live_alone]
        if sort_by_distance:
            instanced_sims.sort(key=lambda sim: (obj.position - sim.position).magnitude_squared())
        inventory = obj.get_inventory()
        if inventory is not None:
            inventory.try_remove_object_by_id(obj.id, count=obj.stack_count())
        for sim in instanced_sims:
            if sim.inventory_component.player_try_add_object(obj):
                break
        build_buy.move_object_to_household_inventory(obj)

    def move_into_zone(self, zone_id):
        if self.home_zone_id == zone_id:
            return
        for sim_info in self:
            if not sim_info.is_instanced(allow_hidden_flags=ALL_HIDDEN_REASONS):
                sim_info.inject_into_inactive_zone(zone_id)
            sim_info.set_default_data()
        self.set_household_lot_ownership(zone_id=zone_id)

    def distribute_household_data(self):
        household_msg = FileSerialization_pb2.HouseholdData()
        self.populate_household_data(household_msg)
        Distributor.instance().add_op_with_no_owner(GenericProtocolBufferOp(Operation.HOUSEHOLD_UPDATE, household_msg))

    def get_homework_help(self, age):
        return self._receive_homework_help_map.get(age)

    def set_homework_help(self, age, homework_help_status):
        self._receive_homework_help_map[age] = homework_help_status
