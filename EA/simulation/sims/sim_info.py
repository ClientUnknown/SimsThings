from _sims4_collections import frozendictfrom collections import OrderedDictimport itertoolsimport mathimport randomimport timefrom away_actions.away_action_tracker import AwayActionTrackerfrom away_actions.away_actions import AwayActionfrom away_actions.away_actions_interactions import ApplyDefaultAwayActionInteractionfrom bucks.sim_info_bucks_tracker import SimInfoBucksTrackerfrom careers.career_tracker import CareerTrackerfrom clock import interval_in_sim_daysfrom date_and_time import DateAndTime, TimeSpanfrom distributor.rollback import ProtocolBufferRollbackfrom distributor.system import Distributorfrom event_testing import test_eventsfrom event_testing.resolver import SingleSimResolver, DoubleSimResolverfrom event_testing.tests import TunableTestSetfrom fame.fame_tuning import FameTunablesfrom fame.lifestyle_brand_tracker import LifestyleBrandTrackerfrom familiars.familiar_tracker import FamiliarTrackerfrom indexed_manager import ObjectLoadDatafrom interactions.aop import AffordanceObjectPairfrom interactions.utils.adventure import AdventureTrackerfrom interactions.utils.death import DeathTrackerfrom interactions.utils.tunable import SetGoodbyeNotificationElementfrom notebook.notebook_tracker import NotebookTrackerSimInfofrom objects import ALL_HIDDEN_REASONS, ALL_HIDDEN_REASONS_EXCEPT_UNINITIALIZED, HiddenReasonFlagfrom objects.components import ComponentContainer, forward_to_components, forward_to_components_genfrom objects.components.consumable_component import ConsumableComponentfrom objects.components.inventory_enums import InventoryTypefrom objects.components.inventory_item import InventoryItemComponentfrom objects.components.statistic_component import HasStatisticComponentfrom objects.object_enums import ItemLocationfrom protocolbuffers import SimObjectAttributes_pb2 as protocols, FileSerialization_pb2 as serialization, GameplaySaveData_pb2 as gameplay_serializationfrom protocolbuffers import SimsCustomOptions_pb2 as custom_optionsfrom protocolbuffers.DistributorOps_pb2 import SetWhimBucksfrom protocolbuffers.ResourceKey_pb2 import ResourceKeyListfrom relationships.global_relationship_tuning import RelationshipGlobalTuningfrom relationships.relationship_tracker import RelationshipTrackerfrom relics.relic_tracker import RelicTrackerfrom reputation.reputation_tuning import ReputationTunablesfrom services.persistence_service import PersistenceTuningfrom services.relgraph_service import RelgraphServicefrom sickness.sickness_tracker import SicknessTrackerfrom sims.aging.aging_mixin import AgingMixinfrom sims.baby.baby_utils import run_baby_spawn_behaviorfrom sims.favorites.favorites_tracker import FavoritesTrackerfrom sims.genealogy_relgraph_enums import SimRelBitFlagsfrom sims.genealogy_tracker import GenealogyTracker, FamilyRelationshipIndex, genealogy_cachingfrom sims.ghost import Ghostfrom sims.global_gender_preference_tuning import GlobalGenderPreferenceTuningfrom sims.occult.sim_info_with_occult_tracker import SimInfoWithOccultTrackerfrom sims.outfits.outfit_enums import OutfitCategory, SpecialOutfitIndexfrom sims.outfits.outfit_tuning import OutfitTuningfrom sims.pregnancy.pregnancy_client_mixin import PregnancyClientMixinfrom sims.pregnancy.pregnancy_tracker import PregnancyTrackerfrom sims.royalty_tracker import RoyaltyTrackerfrom sims.sim_info_favorites_mixin import SimInfoFavoriteMixinfrom sims.sim_info_gameplay_options import SimInfoGameplayOptionsfrom sims.sim_info_lod import SimInfoLODLevelfrom sims.sim_info_name_data import SimInfoNameDatafrom sims.sim_info_tests import SimInfoTest, TraitTestfrom sims.sim_info_types import SimInfoSpawnerTags, SimSerializationOption, Gender, Species, SpeciesExtendedfrom sims.sim_spawner_enums import SimInfoCreationSourcefrom sims.suntan.suntan_ops import SetTanLevelfrom sims.suntan.suntan_tracker import SuntanTrackerfrom sims.template_affordance_provider.template_affordance_tracker import TemplateAffordanceTrackerfrom sims.unlock_tracker import UnlockTrackerfrom sims4.common import is_available_pack, UnavailablePackErrorfrom sims4.profiler_utils import create_custom_named_profiler_functionfrom sims4.protocol_buffer_utils import persist_fields_for_custom_optionfrom sims4.resources import Typesfrom sims4.tuning.tunable import TunableResourceKey, Tunable, TunableList, TunableReference, TunableTuple, TunableMapping, TunableEnumEntry, TunableVariant, OptionalTunablefrom sims4.utils import constpropertyfrom singletons import DEFAULTfrom statistics.commodity import Commodityfrom statistics.life_skill_statistic import LifeSkillStatisticfrom statistics.statistic_enums import CommodityTrackerSimulationLevel, StatisticLockActionfrom story_progression.story_progression_enums import CullingReasonsfrom story_progression.story_progression_tracker import StoryProgressionTrackerfrom traits.trait_tracker import TraitTrackerfrom world.spawn_point import SpawnPointOption, SpawnPointfrom world.spawn_point_enums import SpawnPointRequestReasonimport aspirations.aspirationsimport build_buyimport cachesimport clubsimport date_and_timeimport distributor.fieldsimport distributor.opsimport enumimport event_testingimport game_servicesimport gsi_handlersimport indexed_managerimport objects.componentsimport objects.systemimport placementimport routingimport servicesimport sims.sim_info_types as typesimport sims.sim_info_types as typesimport sims4.logimport sims4.resourcesimport statistics.skillimport tagimport telemetry_helperimport whimslogger = sims4.log.Logger('SimInfo', default_owner='manus')TELEMETRY_CHANGE_ASPI = 'ASPI'writer = sims4.telemetry.TelemetryWriter(TELEMETRY_CHANGE_ASPI)TELEMETRY_SIMULATION_ERROR = 'SERR'simulation_error_writer = sims4.telemetry.TelemetryWriter(TELEMETRY_SIMULATION_ERROR)TELEMETRY_WHIM_BUCKS_CHANGE = 'SPCH'TELEMETRY_WHIM_BUCKS_ADD = 'SPAD'TELEMETRY_WHIM_BUCKS_REMOVE = 'SPRM'TELEMETRY_FIELD_WHIM_BUCKS_SOURCE = 'spsc'TELEMETRY_FIELD_WHIM_BUCKS_CHANGE = 'spch'TELEMETRY_FIELD_WHIM_BUCKS_TOTAL = 'sptl'whim_bucks_writer = sims4.telemetry.TelemetryWriter(TELEMETRY_WHIM_BUCKS_CHANGE)with sims4.reload.protected(globals()):
    SAVE_ACTIVE_HOUSEHOLD_COMMAND = False
    INJECT_LOD_NAME_IN_CALLSTACK = False
class TunableSimTestVariant(TunableVariant):

    def __init__(self, description='A single tunable test.', **kwargs):
        super().__init__(sim_info=SimInfoTest.TunableFactory(locked_args={'tooltip': None}), trait=TraitTest.TunableFactory(locked_args={'tooltip': None}), default='sim_info', description=description, **kwargs)

class TunableSimTestList(event_testing.tests.TestListLoadingMixin):
    DEFAULT_LIST = event_testing.tests.TestList()

    def __init__(self, description=None):
        if description is None:
            description = 'A list of tests.  All tests must succeed to pass the TestSet.'
        super().__init__(description=description, tunable=TunableSimTestVariant())

class SimInfo(SimInfoWithOccultTracker, SimInfoCreationSource.SimInfoCreationSourceMixin, AgingMixin, PregnancyClientMixin, SimInfoFavoriteMixin, ComponentContainer, HasStatisticComponent):

    class BodyBlendTypes(enum.Int, export=False):
        BODYBLENDTYPE_HEAVY = 0
        BODYBLENDTYPE_FIT = 1
        BODYBLENDTYPE_LEAN = 2
        BODYBLENDTYPE_BONY = 3
        BODYBLENDTYPE_PREGNANT = 4
        BODYBLENDTYPE_HIPS_WIDE = 5
        BODYBLENDTYPE_HIPS_NARROW = 6
        BODYBLENDTYPE_WAIST_WIDE = 7
        BODYBLENDTYPE_WAIST_NARROW = 8

    DEFAULT_THUMBNAIL = TunableResourceKey(None, resource_types=sims4.resources.CompoundTypes.IMAGE, description='Icon to be displayed for the Buff.')
    DEFAULT_GAMEPLAY_OPTIONS = SimInfoGameplayOptions.ALLOW_FAME | SimInfoGameplayOptions.ALLOW_REPUTATION
    SIM_DEFINITIONS = TunableMapping(description='\n        A Map from Species to base definition object.\n        ', key_type=TunableEnumEntry(description='\n            Species this definition is for.\n            ', tunable_type=SpeciesExtended, default=SpeciesExtended.HUMAN, invalid_enums=(SpeciesExtended.INVALID,)), value_type=TunableReference(description='\n            The definition used to instantiate Sims.\n            ', manager=services.definition_manager(), class_restrictions='Sim', pack_safe=True))

    @staticmethod
    def get_sim_definition(species):
        if species in SimInfo.SIM_DEFINITIONS:
            return SimInfo.SIM_DEFINITIONS[species]
        else:
            logger.error("Requesting the definition for a species({}) type that doesn't have one in SIM_DEFINITIONS", species)
            return SimInfo.SIM_DEFINITIONS[Species.HUMAN]

    PHYSIQUE_CHANGE_AFFORDANCES = TunableTuple(description="\n        Affordances to run when a Sim's physique changes.\n        ", FAT_CHANGE_POSITIVE_AFFORDANCE=TunableReference(description="\n            Affordance to run when a Sim's fat changes to positive effect.\n            ", manager=services.get_instance_manager(sims4.resources.Types.INTERACTION)), FAT_CHANGE_MAX_POSITIVE_AFFORDANCE=TunableReference(description="\n            Affordance to run when a Sim's fat changes to maximum positive effect.\n            ", manager=services.get_instance_manager(sims4.resources.Types.INTERACTION)), FAT_CHANGE_NEGATIVE_AFFORDANCE=TunableReference(description="\n            Affordance to run when a Sim's fat changes to negative effect.\n            ", manager=services.get_instance_manager(sims4.resources.Types.INTERACTION)), FAT_CHANGE_MAX_NEGATIVE_AFFORDANCE=TunableReference(description="\n            Affordance to run when a Sim's fat changes to maximum negative effect.\n            ", manager=services.get_instance_manager(sims4.resources.Types.INTERACTION)), FAT_CHANGE_NEUTRAL_AFFORDANCE=TunableReference(description="\n            Affordance to run when a Sim's fat changes to neutral effect.\n            ", manager=services.get_instance_manager(sims4.resources.Types.INTERACTION)), FIT_CHANGE_POSITIVE_AFFORDANCE=TunableReference(description="\n            Affordance to run when a Sim's fitness changes to positive effect.\n            ", manager=services.get_instance_manager(sims4.resources.Types.INTERACTION)), FIT_CHANGE_NEGATIVE_AFFORDANCE=TunableReference(description="\n            Affordance to run when a Sim's fitness changes to negative effect.\n            ", manager=services.get_instance_manager(sims4.resources.Types.INTERACTION)), FIT_CHANGE_NEUTRAL_AFFORDANCE=TunableReference(description="\n            Affordance to run when a Sim's fitness changes to neutral effect.\n            ", manager=services.get_instance_manager(sims4.resources.Types.INTERACTION)))
    MAXIMUM_SAFE_FITNESS_VALUE = Tunable(description="\n        This is the value over which a Sim's fitness will always decay.  When a\n        Sim's fitness is set initially inside of CAS, it will not decay below\n        that value unless it is higher than this tunable. Sims with an initial\n        fitness value higher than this tunable will see their fitness commodity\n        decay towards this point.\n        \n        EXAMPLE: MAXIMUM_SAFE_FITNESS_VALUE is set to 90, and a Sim is created\n        in CAS with a fitness value of 100.  Their fitness commodity will decay\n        towards 90.  Another Sim is created with a fitness value of 80.  Their\n        fitness commodity will decay towards 80.\n        ", tunable_type=int, default=90)
    INITIAL_STATIC_COMMODITIES = TunableList(description='\n        A list of static commodities that are added to ever sim info on its\n        creation.\n        ', tunable=TunableReference(description='\n            A static commodity that is added to each sim info on its creation.\n            ', manager=services.get_instance_manager(sims4.resources.Types.STATIC_COMMODITY)))
    INITIAL_STATISTICS = TunableList(description='\n        A list of statistics that will be added to each sim info on its\n        creation.\n        ', tunable=TunableTuple(statistic=TunableReference(description='\n                A statistic that will be added to each sim info upon creation.\n                ', manager=services.get_instance_manager(sims4.resources.Types.STATISTIC), pack_safe=True), tests=OptionalTunable(description='\n                If enabled, the statistic will only be added to each sim info\n                if the tests pass.\n                ', tunable=TunableSimTestList())))
    AWAY_ACTIONS = TunableMapping(description='\n        A mapping between affordances and lists of away actions.  The\n        affordances are used to generate AoPs with each of the away actions.\n        ', key_type=TunableReference(description='\n            The interaction that will be used to create AoPs from the away list\n            of away actions that it is mapped to.\n            ', manager=services.get_instance_manager(sims4.resources.Types.INTERACTION)), value_type=TunableList(description='\n            A list of away actions that are available for the player to select\n            from and apply to the sim.\n            ', tunable=AwayAction.TunableReference(pack_safe=True)))
    DEFAULT_AWAY_ACTION = TunableMapping(description='\n        Map of commodities to away action.  When the default away action is\n        asked for we look at the ad data of each commodity and select the away\n        action linked to the commodity that is advertising the highest.\n        ', key_type=Commodity.TunableReference(description='\n            The commodity that we will look at the advertising value for.\n            ', pack_safe=True), value_type=AwayAction.TunableReference(description='\n            The away action that will applied if the key is the highest\n            advertising commodity of the ones listed.\n            ', pack_safe=True))
    APPLY_DEFAULT_AWAY_ACTION_INTERACTION = ApplyDefaultAwayActionInteraction.TunableReference(description='\n        Interaction that will be used to apply the default away action onto the\n        sim info.\n        ')
    SIM_SKEWER_AFFORDANCES = TunableList(description="\n        A list of affordances that will test and be available when the player\n        clicks on a Sim's interaction button in the Sim skewer.\n        ", tunable=TunableReference(description="\n            An affordance shown when the player clicks on a sim's\n            interaction button in the Sim skewer.\n            ", manager=services.affordance_manager()))
    MAX_WHIM_BUCKS = 999999999
    SIM_INFO_TRACKERS = OrderedDict((('_relationship_tracker', RelationshipTracker), ('_trait_tracker', TraitTracker), ('_pregnancy_tracker', PregnancyTracker), ('_death_tracker', DeathTracker), ('_adventure_tracker', AdventureTracker), ('_royalty_tracker', RoyaltyTracker), ('_career_tracker', CareerTracker), ('_genealogy_tracker', GenealogyTracker), ('_story_progression_tracker', StoryProgressionTracker), ('_unlock_tracker', UnlockTracker), ('_away_action_tracker', AwayActionTracker), ('_notebook_tracker', NotebookTrackerSimInfo), ('_whim_tracker', whims.whims_tracker.WhimsTracker), ('_aspiration_tracker', aspirations.aspirations.AspirationTracker), ('_template_affordance_tracker', TemplateAffordanceTracker), ('_relic_tracker', RelicTracker), ('_lifestyle_brand_tracker', LifestyleBrandTracker), ('_suntan_tracker', SuntanTracker), ('_sickness_tracker', SicknessTracker), ('_familiar_tracker', FamiliarTracker), ('_favorites_tracker', FavoritesTracker)))

    def __init__(self, *args, zone_id:int=0, zone_name='', world_id:int=0, account=None, **kwargs):
        super().__init__(*args, **kwargs)
        self._revision = 0
        self._lod = SimInfoLODLevel.BASE
        self.add_component(objects.components.buff_component.BuffComponent(self))
        self.commodity_tracker.simulation_level = CommodityTrackerSimulationLevel.LOW_LEVEL_SIMULATION
        for tracker_attr in SimInfo.SIM_INFO_TRACKERS:
            setattr(self, tracker_attr, None)
        self._prespawn_zone_id = zone_id
        self._zone_id = zone_id
        self.zone_name = zone_name
        self._world_id = world_id
        self._account = account
        self._sim_ref = None
        self._serialization_option = SimSerializationOption.UNDECLARED
        self._household_id = None
        self._autonomy_scoring_preferences = {}
        self._autonomy_use_preferences = {}
        self._primary_aspiration = None
        self._current_skill_guid = 0
        self._fat = 0
        self._fit = 0
        self._generation = 0
        self._travel_group_id = 0
        self.thumbnail = self.DEFAULT_THUMBNAIL
        self._current_whims = []
        self._whim_bucks = 0
        self._sim_creation_path = None
        self._time_sim_was_saved = None
        self._additional_bonus_days = 0
        self.startup_sim_location = None
        self._si_state = None
        self._has_loaded_si_state = False
        self._cached_inventory_value = 0
        self.spawn_point_id = None
        self.spawner_tags = []
        self.spawn_point_option = SpawnPointOption.SPAWN_ANY_POINT_WITH_CONSTRAINT_TAGS
        self.game_time_bring_home = None
        self._initial_fitness_value = None
        self._build_buy_unlocks = set()
        self._singed = False
        self._grubby = False
        self._plumbbob_override = None
        self._goodbye_notification = None
        self._transform_on_load = None
        self._level_on_load = 0
        self._surface_id_on_load = 1
        self._sim_headline = None
        self.premade_sim_template_id = 0
        self._inventory_data = None
        self._bucks_tracker = None
        self._linked_sims = None
        self._fix_relationships = False
        self.do_first_sim_info_load_fixups = False
        self._blacklisted_statistics_cache = None
        self._gameplay_options = self.DEFAULT_GAMEPLAY_OPTIONS
        self._squad_members = set()

    def __repr__(self):
        return "<sim '{0}' {1:#x}>".format(self.full_name, self.sim_id)

    def __str__(self):
        return self.full_name

    def get_delete_op(self):
        pass

    @constproperty
    def is_sim():
        return True

    @property
    def sim_info(self):
        return self

    @distributor.fields.Field(op=distributor.ops.SetIsNpc)
    def is_npc(self):
        return services.active_household_id() != self.household_id

    resend_is_npc = is_npc.get_resend()

    @property
    def is_player_sim(self):
        household = self.household
        if household is not None:
            return household.is_player_household
        return False

    @property
    def is_played_sim(self):
        household = self.household
        if household is not None:
            return household.is_played_household
        return False

    @property
    def is_selectable(self):
        client = services.client_manager().get_client_by_household_id(self._household_id)
        if client is None:
            return False
        return self in client.selectable_sims

    @property
    def is_selected(self):
        sim = self.get_sim_instance(allow_hidden_flags=ALL_HIDDEN_REASONS)
        if sim is not None:
            return sim.is_selected
        return False

    @property
    def is_premade_sim(self):
        return self.creation_source.is_creation_source(SimInfoCreationSource.PRE_MADE)

    @property
    def lod(self):
        return self._lod

    def request_lod(self, new_lod):
        if self._lod == new_lod:
            return True
        if not self.can_change_lod(self._lod):
            return False
        if not self.can_set_to_lod(new_lod):
            return False
        old_lod = self._lod
        self._lod = new_lod
        if self.household is not None:
            self.household.on_sim_lod_update(self, old_lod, new_lod)
        for (tracker_attr, tracker_type) in SimInfo.SIM_INFO_TRACKERS.items():
            is_valid = tracker_type.is_valid_for_lod(new_lod)
            tracker = getattr(self, tracker_attr, None)
            if tracker is None and is_valid:
                tracker = tracker_type(self)
                setattr(self, tracker_attr, tracker)
            if tracker is not None:
                tracker.on_lod_update(old_lod, new_lod)
                if not is_valid:
                    setattr(self, tracker_attr, None)
        if self.has_component(objects.components.types.STATISTIC_COMPONENT):
            self.statistic_component.on_lod_update(old_lod, new_lod)
        if self.Buffs is not None:
            self.Buffs.on_lod_update(old_lod, new_lod)
        if new_lod == SimInfoLODLevel.MINIMUM:
            self._build_buy_unlocks.clear()
            if services.hidden_sim_service().is_hidden(self.id):
                services.hidden_sim_service().unhide_sim(self.id)
            clubs.on_sim_killed_or_culled(self)
            self.refresh_age_settings()
            self.clear_outfits_to_minimum()
            self._primary_aspiration = None
            if self.has_component(objects.components.types.STATISTIC_COMPONENT):
                self.statistic_component.on_remove()
                self.remove_component(objects.components.types.STATISTIC_COMPONENT)
            self.Buffs.clean_up()
            self.remove_component(objects.components.types.BUFF_COMPONENT)
            self._zone_id = 0
        return True

    def can_set_to_lod(self, lod):
        if lod == SimInfoLODLevel.MINIMUM and self.get_culling_immunity_reasons():
            return False
        return True

    def can_change_lod(self, lod):
        if lod == SimInfoLODLevel.MINIMUM:
            return False
        return True

    @property
    def can_instantiate_sim(self):
        if self.lod == SimInfoLODLevel.MINIMUM:
            return False
        return True

    def get_name_data(self):
        return SimInfoNameData(self.gender, self.first_name, self.last_name, self.full_name_key)

    @forward_to_components_gen
    def get_additional_create_ops_gen(self):
        pass

    def get_resolver(self):
        return SingleSimResolver(self)

    def on_loading_screen_animation_finished(self):
        if self._career_tracker is not None:
            self._career_tracker.on_loading_screen_animation_finished()

    def on_situation_request(self, situation):
        if self._career_tracker is None:
            logger.error('on_situation_request: sim_info {} has no career_tracker.', self, owner='nabaker')
            return
        self._career_tracker.on_situation_request(situation)

    def update_fitness_state(self):
        sim = self._sim_ref()
        if not sim.needs_fitness_update:
            return
        sim.needs_fitness_update = False
        self._set_fit_fat()

    @property
    def household(self):
        return services.household_manager().get(self._household_id)

    @property
    def family_funds(self):
        return self.household.funds

    @property
    def travel_group(self):
        return services.travel_group_manager().get(self._travel_group_id)

    def on_add(self):
        if self.has_component(objects.components.types.STATISTIC_COMPONENT):
            self.commodity_tracker.add_watcher(self._publish_commodity_update)
            self.statistic_tracker.add_watcher(self._publish_statistic_update)

    @forward_to_components
    def on_remove(self):
        if self.lod > SimInfoLODLevel.MINIMUM:
            with services.relationship_service().suppress_client_updates_context_manager():
                self.Buffs.clean_up()
            if self._whim_tracker is not None:
                self._whim_tracker.clean_up()
            self._current_whims.clear()
            self._away_action_tracker.clean_up()
            self._career_tracker.clean_up()
            if self._aspiration_tracker is not None:
                self._aspiration_tracker.clean_up()
            if self._favorites_tracker is not None:
                self._favorites_tracker.clean_up()
        if self.household is not None:
            if self.household.client is not None:
                self.household.client.set_next_sim_or_none(only_if_this_active_sim_info=self)
                self.household.client.selectable_sims.remove_selectable_sim_info(self)
            self.household.remove_sim_info(self)

    @property
    def is_enabled_in_skewer(self):
        if self.is_baby:
            return False
        if self.is_pet and not services.get_selectable_sims().can_select_pets:
            return False
        if self.household is None:
            return False
        if self.lod == SimInfoLODLevel.MINIMUM:
            return False
        daycare_service = services.daycare_service()
        if daycare_service is None:
            return False
        if self in daycare_service.get_sim_infos_for_nanny(self.household):
            return False
        if services.hidden_sim_service().is_hidden(self.id):
            return False
        else:
            tutorial_service = services.get_tutorial_service()
            if tutorial_service is not None and tutorial_service.is_sim_unselectable(self):
                return False
        return True

    def try_add_object_to_inventory_without_component(self, obj):
        if not obj.can_go_in_inventory_type(InventoryType.SIM):
            return (False, obj)
        obj.item_location = ItemLocation.SIM_INVENTORY
        obj.save_object(self.inventory_data.objects, ItemLocation.SIM_INVENTORY, self.id)
        obj.destroy(cause="Added to uninstantiated sim's inventory")
        return (True, None)

    def inventory_value(self):
        sim = self.get_sim_instance(allow_hidden_flags=ALL_HIDDEN_REASONS)
        if sim is not None:
            self._cached_inventory_value = sim.inventory_component.inventory_value
        return self._cached_inventory_value

    def _generate_default_away_action_aop(self, context, **kwargs):
        return AffordanceObjectPair(SimInfo.APPLY_DEFAULT_AWAY_ACTION_INTERACTION, None, SimInfo.APPLY_DEFAULT_AWAY_ACTION_INTERACTION, None, away_action_sim_info=self, **kwargs)

    def _generate_away_action_affordances(self, context, **kwargs):
        for (affordance, away_action_list) in SimInfo.AWAY_ACTIONS.items():
            for away_action in away_action_list:
                yield AffordanceObjectPair(affordance, None, affordance, None, away_action=away_action, away_action_sim_info=self, **kwargs)

    def sim_skewer_affordance_gen(self, context, **kwargs):
        career = self._career_tracker.get_currently_at_work_career()
        if career is not None and not career.is_at_active_event:
            yield from career.sim_skewer_rabbit_hole_affordances_gen(context, **kwargs)
            return
        rabbit_hole_service = services.get_rabbit_hole_service()
        if rabbit_hole_service.is_in_rabbit_hole(self.id):
            yield from rabbit_hole_service.sim_skewer_rabbit_hole_affordances_gen(self, context, **kwargs)
            return
        sim = self.get_sim_instance()
        for affordance in self.SIM_SKEWER_AFFORDANCES:
            if affordance.simless or sim is None:
                pass
            else:
                for aop in affordance.potential_interactions(sim, context, sim_info=self, **kwargs):
                    yield aop
        if not self.household.missing_pet_tracker.is_pet_missing(self):
            yield self._generate_default_away_action_aop(context, **kwargs)
            yield from self._generate_away_action_affordances(context, **kwargs)

    def bucks_trackers_gen(self):
        if self.household is not None:
            yield self.household.bucks_tracker
        club_service = services.get_club_service()
        for club in club_service.get_clubs_for_sim_info(self):
            yield club.bucks_tracker
        yield self.get_bucks_tracker(add_if_none=False)

    @property
    def sim_creation_path(self):
        return self._sim_creation_path

    def send_age_progress_bar_update(self):
        self.resend_age_progress_data()
        days_until_ready_to_age = interval_in_sim_days(max(0, self._days_until_ready_to_age()))
        current_time = services.time_service().sim_now
        ready_to_age_time = current_time + days_until_ready_to_age
        self.update_time_alive()
        op = distributor.ops.SetSimAgeProgressTooltipData(int(current_time.absolute_days()), int(ready_to_age_time.absolute_days()), int(self._time_alive.in_days()))
        Distributor.instance().add_op(self, op)

    @distributor.fields.Field(op=distributor.ops.SetPrimaryAspiration)
    def primary_aspiration(self):
        return self._primary_aspiration

    resend_primary_aspiration = primary_aspiration.get_resend()

    @primary_aspiration.setter
    def primary_aspiration(self, value):
        self._primary_aspiration = value
        if self.aspiration_tracker is not None:
            self.aspiration_tracker.initialize_aspiration()
        services.get_event_manager().process_event(test_events.TestEvent.AspirationChanged, sim_info=self, new_aspiration=value)
        with telemetry_helper.begin_hook(writer, TELEMETRY_CHANGE_ASPI, sim=self.get_sim_instance(allow_hidden_flags=ALL_HIDDEN_REASONS)) as hook:
            hook.write_guid('aspi', value.guid64 if value is not None else 0)

    def start_aspiration_tracker_on_instantiation(self, force_ui_update=False):
        if self._aspiration_tracker is None:
            logger.error("Trying to start aspiration tracker when it hasn't been loaded for Sim {}", self, owner='tingyul')
            return
        if force_ui_update:
            self._aspiration_tracker.force_send_data_update()
        self._aspiration_tracker.initialize_aspiration(from_load=True)
        self._aspiration_tracker.set_update_alarm()
        self._career_tracker.activate_career_aspirations()

    @distributor.fields.Field(op=distributor.ops.SetCurrentWhims)
    def current_whims(self):
        return self._current_whims

    resend_current_whims = current_whims.get_resend()

    @current_whims.setter
    def current_whims(self, value):
        self._current_whims = value

    def send_whim_bucks_update(self, reason):
        if self.is_selectable:
            op = distributor.ops.SetWhimBucks(self._whim_bucks, reason)
            Distributor.instance().add_op(self, op)

    def set_whim_bucks(self, value, reason):
        self._whim_bucks = min(value, self.MAX_WHIM_BUCKS)
        self.send_whim_bucks_update(reason)
        services.get_event_manager().process_event(test_events.TestEvent.WhimBucksChanged, sim_info=self)

    def add_whim_bucks(self, amount, reason, source=None):
        self.set_whim_bucks(self._whim_bucks + amount, reason)
        if source is not None:
            if amount < 0:
                with telemetry_helper.begin_hook(writer, TELEMETRY_WHIM_BUCKS_REMOVE, sim_info=self) as hook:
                    hook.write_int(TELEMETRY_FIELD_WHIM_BUCKS_SOURCE, source)
                    hook.write_int(TELEMETRY_FIELD_WHIM_BUCKS_CHANGE, abs(amount))
                    hook.write_int(TELEMETRY_FIELD_WHIM_BUCKS_TOTAL, self._whim_bucks)
            else:
                with telemetry_helper.begin_hook(writer, TELEMETRY_WHIM_BUCKS_ADD, sim_info=self) as hook:
                    hook.write_int(TELEMETRY_FIELD_WHIM_BUCKS_SOURCE, source)
                    hook.write_int(TELEMETRY_FIELD_WHIM_BUCKS_CHANGE, abs(amount))
                    hook.write_int(TELEMETRY_FIELD_WHIM_BUCKS_TOTAL, self._whim_bucks)

    def get_whim_bucks(self):
        return self._whim_bucks

    @property
    def goodbye_notification(self):
        return self._goodbye_notification

    def try_to_set_goodbye_notification(self, value):
        if self._goodbye_notification != SetGoodbyeNotificationElement.NEVER_USE_NOTIFICATION_NO_MATTER_WHAT:
            self._goodbye_notification = value

    def clear_goodbye_notification(self):
        self._goodbye_notification = None

    @property
    def clothing_preference_gender(self):
        if self.has_trait(GlobalGenderPreferenceTuning.MALE_CLOTHING_PREFERENCE_TRAIT):
            return Gender.MALE
        if self.has_trait(GlobalGenderPreferenceTuning.FEMALE_CLOTHING_PREFERENCE_TRAIT):
            return Gender.FEMALE
        return self.gender

    @distributor.fields.Field(op=distributor.ops.OverridePlumbbob)
    def plumbbob_override(self):
        return self._plumbbob_override

    @plumbbob_override.setter
    def plumbbob_override(self, value):
        self._plumbbob_override = value

    @distributor.fields.Field(op=distributor.ops.SetDeathType)
    def death_type(self):
        return self._death_tracker.death_type

    resend_death_type = death_type.get_resend()

    @property
    def is_ghost(self):
        return self._death_tracker.is_ghost

    @property
    def death_tracker(self):
        return self._death_tracker

    @property
    def pregnancy_tracker(self):
        return self._pregnancy_tracker

    @property
    def adventure_tracker(self):
        return self._adventure_tracker

    @property
    def royalty_tracker(self):
        return self._royalty_tracker

    @property
    def away_action_tracker(self):
        return self._away_action_tracker

    @property
    def template_affordance_tracker(self):
        return self._template_affordance_tracker

    @property
    def notebook_tracker(self):
        return self._notebook_tracker

    @property
    def sickness_tracker(self):
        return self._sickness_tracker

    @property
    def current_sickness(self):
        if self._sickness_tracker is None:
            return
        return self._sickness_tracker.current_sickness

    def has_sickness_tracking(self):
        return self.current_sickness is not None

    def is_sick(self):
        current_sickness = self.current_sickness
        return current_sickness is not None and current_sickness.considered_sick

    def has_sickness(self, sickness):
        return self.current_sickness is sickness

    def sickness_record_last_progress(self, progress):
        self._sickness_tracker.record_last_progress(progress)

    def discover_symptom(self, symptom):
        self._sickness_tracker.discover_symptom(symptom)

    def track_examination(self, affordance):
        self._sickness_tracker.track_examination(affordance)

    def track_treatment(self, affordance):
        self._sickness_tracker.track_treatment(affordance)

    def rule_out_treatment(self, affordance):
        self._sickness_tracker.rule_out_treatment(affordance)

    def was_symptom_discovered(self, symptom):
        return symptom in self._sickness_tracker.discovered_symptoms

    def was_exam_performed(self, affordance):
        return affordance in self._sickness_tracker.exams_performed

    def was_treatment_performed(self, affordance):
        return affordance in self._sickness_tracker.treatments_performed

    def was_treatment_ruled_out(self, affordance):
        return affordance in self._sickness_tracker.ruled_out_treatments

    @distributor.fields.Field(op=distributor.ops.SetAwayAction)
    def current_away_action(self):
        if self._away_action_tracker is None:
            return
        return self._away_action_tracker.current_away_action

    resend_current_away_action = current_away_action.get_resend()

    def add_statistic(self, stat_type, value):
        tracker = self.get_tracker(stat_type)
        tracker.set_value(stat_type, value, add=True)

    def remove_statistic(self, stat_type):
        tracker = self.get_tracker(stat_type)
        if tracker is not None:
            tracker.remove_statistic(stat_type)

    @property
    def si_state(self):
        return self._si_state

    @property
    def has_loaded_si_state(self):
        return self._has_loaded_si_state

    @property
    def is_pregnant(self):
        if self._pregnancy_tracker is None:
            return False
        return self._pregnancy_tracker.is_pregnant

    @property
    def current_skill_guid(self):
        return self._current_skill_guid

    @current_skill_guid.setter
    def current_skill_guid(self, value):
        if self._current_skill_guid != value:
            self._current_skill_guid = value

    @property
    def prespawn_zone_id(self):
        return self._prespawn_zone_id

    @property
    def zone_id(self):
        return self._zone_id

    def set_zone_on_spawn(self):
        logger.assert_raise(not self.is_instanced(allow_hidden_flags=ALL_HIDDEN_REASONS), 'Attempting to set instanced sim into current zone.', owner='jjacobson')
        current_zone = services.current_zone()
        current_zone_id = current_zone.id
        if self.is_npc and (self._serialization_option == SimSerializationOption.UNDECLARED or self._serialization_option == SimSerializationOption.LOT and self._zone_id != current_zone_id or self._serialization_option == SimSerializationOption.OPEN_STREETS and self.world_id != current_zone.open_street_id):
            self.set_current_outfit((OutfitCategory.EVERYDAY, 0))
        if self._zone_id != current_zone_id:
            self._prespawn_zone_id = self._zone_id
            self._zone_id = current_zone_id
            self.world_id = current_zone.open_street_id
            self._si_state = gameplay_serialization.SuperInteractionSaveState()

    def inject_into_inactive_zone(self, new_zone_id, start_away_actions=True, skip_instanced_check=False, skip_daycare=False):
        if services.current_zone_id() == new_zone_id:
            logger.error('Attempting to put sim:{} into the active zone:{}', self, services.current_zone())
            return
        if self._zone_id == new_zone_id:
            return
        if skip_instanced_check or self.is_instanced(allow_hidden_flags=ALL_HIDDEN_REASONS):
            logger.error('Trying to inject {} into zone when sim_info is still instanced.', self)
        self._zone_id = new_zone_id
        self.world_id = services.get_persistence_service().get_world_id_from_zone(new_zone_id)
        self.spawner_tags = []
        self.spawn_point_option = SpawnPointOption.SPAWN_ANY_POINT_WITH_CONSTRAINT_TAGS
        self.startup_sim_location = None
        self._si_state = gameplay_serialization.SuperInteractionSaveState()
        self._serialization_option = SimSerializationOption.UNDECLARED
        if self._away_action_tracker is not None and start_away_actions:
            self._away_action_tracker.refresh(on_travel_away=True)
        if not skip_daycare:
            services.daycare_service().refresh_household_daycare_nanny_status(self, try_enable_if_selectable_toddler=True)

    @property
    def world_id(self):
        return self._world_id

    @world_id.setter
    def world_id(self, value):
        if self._world_id != value:
            self._world_id = value

    @property
    def serialization_option(self):
        return self._serialization_option

    @property
    def fat(self):
        return self._fat

    @fat.setter
    def fat(self, value):
        self._fat = value

    @property
    def fit(self):
        return self._fit

    @fit.setter
    def fit(self, value):
        self._fit = value

    @distributor.fields.Field(op=distributor.ops.SetSinged, default=False)
    def singed(self):
        return self._singed

    @singed.setter
    def singed(self, value):
        self._singed = value

    @distributor.fields.Field(op=distributor.ops.SetGrubby, default=False)
    def grubby(self):
        return self._grubby

    @grubby.setter
    def grubby(self, value):
        self._grubby = value

    @property
    def on_fire(self):
        sim_instance = self.get_sim_instance()
        if not sim_instance:
            return False
        return services.get_fire_service().sim_is_on_fire(sim_instance)

    @property
    def thumbnail(self):
        return self._thumbnail

    @thumbnail.setter
    def thumbnail(self, value):
        if value is not None:
            self._thumbnail = value
        else:
            self._thumbnail = sims4.resources.Key(0, 0, 0)

    @property
    def autonomy_scoring_preferences(self):
        return self._autonomy_scoring_preferences

    @property
    def autonomy_use_preferences(self):
        return self._autonomy_use_preferences

    @distributor.fields.Field(op=distributor.ops.SetCareers)
    def career_tracker(self):
        return self._career_tracker

    @property
    def careers(self):
        if self._career_tracker is not None:
            return self._career_tracker.careers
        return frozendict()

    @property
    def has_custom_career(self):
        if self._career_tracker is not None:
            return self._career_tracker.has_custom_career
        return False

    @property
    def time_sim_was_saved(self):
        return self._time_sim_was_saved

    @time_sim_was_saved.setter
    def time_sim_was_saved(self, value):
        self._time_sim_was_saved = value

    def get_days_since_instantiation(self, *, uninstatiated_time):
        if self.time_sim_was_saved is None:
            return uninstatiated_time
        time_since_instantiation = services.time_service().sim_now - self.time_sim_was_saved
        time_since_instantiation = time_since_instantiation.in_days()
        return time_since_instantiation

    def apply_career_changes(self, missed_time_percent=0):
        for statistic in tuple(self.commodity_tracker):
            if isinstance(statistic, LifeSkillStatistic):
                if statistic.missing_career_decay_rate == 0.0:
                    pass
                else:
                    reduced_value = statistic.get_value() - missed_time_percent*statistic.missing_career_decay_rate
                    statistic.set_value(reduced_value)

    def get_school_data(self):
        sim_definition = self.get_sim_definition(self.extended_species)
        return sim_definition._cls._school

    @property
    def relationship_tracker(self):
        return self._relationship_tracker

    @distributor.fields.Field(op=distributor.ops.SetSimHeadline)
    def sim_headline(self):
        return self._sim_headline

    @sim_headline.setter
    def sim_headline(self, value):
        self._sim_headline = value

    @distributor.fields.Field(op=distributor.ops.SetLinkedSims)
    def linked_sims(self):
        if self._linked_sims is None:
            return tuple()
        return tuple(self._linked_sims)

    resend_linked_sims = linked_sims.get_resend()

    def add_linked_sim(self, linked_sim_id):
        if self.id == linked_sim_id:
            return
        if self._linked_sims is None:
            self._linked_sims = set()
        self._linked_sims.add(linked_sim_id)
        self.resend_linked_sims()

    def remove_linked_sim(self, linked_sim_id):
        if self._linked_sims is None:
            return
        if linked_sim_id in self._linked_sims:
            self._linked_sims.remove(linked_sim_id)
            self.resend_linked_sims()

    @distributor.fields.Field(op=distributor.ops.SetAccountId)
    def account_id(self):
        if self._account is not None:
            return self._account.id

    @property
    def account(self):
        return self._account

    @property
    def client(self):
        if self.account is not None:
            return self.account.get_client(self.zone_id)

    @property
    def Buffs(self):
        return self.get_component(objects.components.types.BUFF_COMPONENT)

    @property
    def aspiration_tracker(self):
        return self._aspiration_tracker

    @property
    def whim_tracker(self):
        return self._whim_tracker

    @property
    def unlock_tracker(self):
        return self._unlock_tracker

    @property
    def relic_tracker(self):
        return self._relic_tracker

    @property
    def lifestyle_brand_tracker(self):
        return self._lifestyle_brand_tracker

    @property
    def familiar_tracker(self):
        return self._familiar_tracker

    @property
    def favorites_tracker(self):
        return self._favorites_tracker

    @property
    def suntan_tracker(self):
        return self._suntan_tracker

    @distributor.fields.Field(op=SetTanLevel)
    def suntan_data(self):
        return self.suntan_tracker

    resend_suntan_data = suntan_data.get_resend()

    def force_resend_suntan_data(self):
        if self.suntan_tracker:
            self.suntan_tracker.set_tan_level(force_update=True)

    @property
    def revision(self):
        return self._revision

    @property
    def inventory_data(self):
        return self._inventory_data

    @inventory_data.setter
    def inventory_data(self, new_data):
        self._inventory_data = new_data

    @property
    def build_buy_unlocks(self):
        return self._build_buy_unlocks

    def add_build_buy_unlock(self, unlock):
        self._build_buy_unlocks.add(unlock)

    @property
    def is_simulating(self):
        sim_inst = self.get_sim_instance(allow_hidden_flags=ALL_HIDDEN_REASONS_EXCEPT_UNINITIALIZED)
        if sim_inst is not None:
            return sim_inst.is_simulating
        elif self.is_baby and self.is_selectable:
            return True
        return False

    def get_statistic(self, stat, add=True):
        tracker = self.get_tracker(stat)
        return tracker.get_statistic(stat, add=add)

    @caches.cached
    def all_skills(self):
        if self.commodity_tracker is None:
            return tuple()
        return tuple(stat for stat in self.commodity_tracker if isinstance(stat, statistics.skill.Skill))

    def get_sim_instance(self, *, allow_hidden_flags=0):
        if self._sim_ref:
            sim = self._sim_ref()
            if sim is not None and not sim.is_hidden(allow_hidden_flags=allow_hidden_flags):
                return sim

    def is_instanced(self, *, allow_hidden_flags=0):
        sim = self.get_sim_instance(allow_hidden_flags=allow_hidden_flags)
        return sim is not None

    def add_topic(self, *args, **kwargs):
        if self._sim_ref and self._sim_ref() is None:
            return
        return self._sim_ref().add_topic(*args, **kwargs)

    def remove_topic(self, *args, **kwargs):
        if self._sim_ref and self._sim_ref() is None:
            return
        return self._sim_ref().remove_topic(*args, **kwargs)

    def set_sub_action_lockout(self, *args, **kwargs):
        if self._sim_ref and self._sim_ref() is None:
            return
        return self._sim_ref().set_sub_action_lockout(*args, **kwargs)

    def add_statistic_component(self):
        logger.error('Sim Info {}: called add_statistic_component(). This is not supported.', self)

    def can_add_component(self, component_definition):
        if self.lod == SimInfoLODLevel.MINIMUM:
            return False
        return True

    def create_sim_instance(self, position, sim_spawner_tags=None, saved_spawner_tags=None, spawn_action=None, sim_location=None, additional_fgl_search_flags=None, from_load=False, use_fgl=True, spawn_point_override=None, pre_add_fn=None, spawn_at_lot=True):
        if self.household is None:
            logger.callstack('Creating a Sim instance with a None household. This will cause problems.\n   Sim: {}\n   Household id: {}\n   Creation Source: {}', self, self.household_id, self.creation_source, level=sims4.log.LEVEL_ERROR, owner='tingyul')
        if not self.can_instantiate_sim:
            logger.error('Failed attempt to instantiate a MINIMUM LOD sim_info: {}', self)
            return False
        sim_info = self

        def init(obj):
            trans = None
            orient = None
            start_routing_surface = None
            total_spawner_tags = []
            try:
                zone = services.current_zone()
                starting_position = position
                if sim_location is not None:
                    logger.info('Sim {} spawning with sim_location {}', sim_info, sim_location)
                    starting_position = sim_location.transform.translation
                    starting_orientation = sim_location.transform.orientation
                    start_routing_surface = sim_location.routing_surface
                    if start_routing_surface.primary_id != sim_info.zone_id:
                        if sim_info.world_id != zone.open_street_id:
                            logger.warn("Sim {} spawning in zone {} but the sim's startup sim location had zone saved as {}. Setting sim location routing surface to use new zone.", sim_info, sim_info.zone_id, start_routing_surface.primary_id)
                        start_routing_surface = routing.SurfaceIdentifier(sim_info.zone_id, start_routing_surface.secondary_id, routing.SurfaceType.SURFACETYPE_WORLD)
                else:
                    logger.info('Sim {} spawning with no sim_location'.format(sim_info))
                    starting_orientation = None
                    start_routing_surface = None
                if not use_fgl:
                    trans = starting_position
                    orient = starting_orientation
                elif starting_position is not None:
                    logger.info('Sim {} spawning with starting_position {}', sim_info, starting_position)
                    fgl_search_flags = placement.FGLSearchFlagsDefault | placement.FGLSearchFlag.USE_SIM_FOOTPRINT | placement.FGLSearchFlag.STAY_IN_CURRENT_BLOCK
                    if additional_fgl_search_flags is not None:
                        fgl_search_flags = fgl_search_flags | additional_fgl_search_flags
                    additional_avoid_sim_radius = routing.get_default_agent_radius() if from_load else routing.get_sim_extra_clearance_distance()
                    starting_location = placement.create_starting_location(position=starting_position, orientation=starting_orientation, routing_surface=start_routing_surface)
                    fgl_context = placement.create_fgl_context_for_sim(starting_location, self, search_flags=fgl_search_flags, additional_avoid_sim_radius=additional_avoid_sim_radius)
                    (trans, orient) = placement.find_good_location(fgl_context)
                    logger.info('Sim {} spawning FGL returned {}, {}', sim_info, trans, orient)
                if trans is None:
                    zone = services.current_zone()
                    default_tags = SimInfoSpawnerTags.SIM_SPAWNER_TAGS
                    lot_id = None
                    if not sim_spawner_tags:
                        total_spawner_tags = list(default_tags)
                        if spawn_at_lot:
                            lot_id = zone.lot.lot_id
                    else:
                        total_spawner_tags = sim_spawner_tags
                        if SpawnPoint.ARRIVAL_SPAWN_POINT_TAG in total_spawner_tags or SpawnPoint.VISITOR_ARRIVAL_SPAWN_POINT_TAG in total_spawner_tags:
                            lot_id = zone.lot.lot_id
                    logger.info('Sim {} looking for spawn point relative to lot_id {} tags {}', sim_info, lot_id, total_spawner_tags)
                    if spawn_point_override is None:
                        spawn_point = zone.get_spawn_point(lot_id=lot_id, sim_spawner_tags=total_spawner_tags, spawning_sim_info=self, spawn_point_request_reason=SpawnPointRequestReason.SPAWN)
                    else:
                        spawn_point = spawn_point_override
                    if spawn_point is not None:
                        (trans, orient) = spawn_point.next_spawn_spot()
                        start_routing_surface = spawn_point.routing_surface
                        sim_info.spawn_point_id = spawn_point.spawn_point_id
                        logger.info('Sim {} spawning from spawn point {} transform {}', sim_info, spawn_point.spawn_point_id, trans)
                    else:
                        (trans, orient) = self._find_place_on_lot_for_sim()
                        logger.info('Sim {} spawn point determined using FGL at {} {}', sim_info, trans, orient)
            except:
                logger.exception('Error in create_sim_instance/find_good_location:')
            if trans is None:
                logger.error('find_good_location Failed, Setting Sim Position to Default')
                translation = DEFAULT if position is None else position
            else:
                translation = trans
            orientation = DEFAULT if orient is None else orient
            routing_surface = DEFAULT if start_routing_surface is None else start_routing_surface
            obj.move_to(translation=translation, orientation=orientation, routing_surface=routing_surface)
            obj.sim_info = sim_info
            obj.opacity = 0
            if not (from_load and sim_info.spawner_tags):
                sim_info.spawner_tags = saved_spawner_tags or total_spawner_tags
            if pre_add_fn is not None:
                pre_add_fn(obj)

        run_baby_spawn_behavior(self)
        sim_inst = objects.system.create_object(self.get_sim_definition(self.extended_species), self.sim_id, init=init)
        if sim_info.is_ghost:
            sim_inst.routing_context.ghost_route = True
        sim_inst.on_start_up.append(lambda _: sim_inst.fade_in() if spawn_action is None else spawn_action)
        self._sim_ref = sim_inst.ref()
        services.daycare_service().on_sim_spawn(self)
        return True

    def _find_place_on_lot_for_sim(self):
        zone = services.current_zone()
        center_pos = sims4.math.Vector3.ZERO()
        if zone.lot is not None:
            center_pos = zone.lot.center
        position = sims4.math.Vector3(center_pos.x, services.terrain_service.terrain_object().get_height_at(center_pos.x, center_pos.z), center_pos.z)
        starting_location = placement.create_starting_location(position=position)
        fgl_context = placement.create_fgl_context_for_sim(starting_location, self, additional_avoid_sim_radius=routing.get_sim_extra_clearance_distance())
        return placement.find_good_location(fgl_context)

    def _get_fit_fat(self):
        physique = [x for x in self.physique.split(',')]
        max_fat = ConsumableComponent.FAT_COMMODITY.max_value_tuning
        max_fit = ConsumableComponent.FIT_COMMODITY.max_value_tuning
        min_fat = ConsumableComponent.FAT_COMMODITY.min_value_tuning
        min_fit = ConsumableComponent.FIT_COMMODITY.min_value_tuning
        heavy = float(physique[SimInfo.BodyBlendTypes.BODYBLENDTYPE_HEAVY])
        lean = float(physique[SimInfo.BodyBlendTypes.BODYBLENDTYPE_LEAN])
        fit = float(physique[SimInfo.BodyBlendTypes.BODYBLENDTYPE_FIT])
        bony = float(physique[SimInfo.BodyBlendTypes.BODYBLENDTYPE_BONY])
        self.fat = (1 + heavy - lean)*max_fat + min_fat
        self.fit = (1 + fit - bony)*max_fit + min_fit

    def _set_fit_fat(self):
        sim = self.get_sim_instance()
        if sim is not None:
            self.fat = sim.commodity_tracker.get_value(ConsumableComponent.FAT_COMMODITY)
            self.fit = sim.commodity_tracker.get_value(ConsumableComponent.FIT_COMMODITY)
        physique = [x for x in self.physique.split(',')]
        max_fat = ConsumableComponent.FAT_COMMODITY.max_value_tuning
        max_fit = ConsumableComponent.FIT_COMMODITY.max_value_tuning
        min_fat = ConsumableComponent.FAT_COMMODITY.min_value_tuning
        min_fit = ConsumableComponent.FIT_COMMODITY.min_value_tuning
        fat_range = max_fat - min_fat
        fit_range = max_fit - min_fit
        fat_base = max_fat - fat_range/2
        fit_base = max_fit - fit_range/2
        heavy = 0.0 if self.fat <= fat_base else (self.fat - fat_base)/(max_fat - fat_base)
        lean = 0.0 if self.fat >= fat_base else (fat_base - self.fat)/(fat_base - min_fat)
        fit = 0.0 if self.fit <= fit_base else (self.fit - fit_base)/(max_fit - fit_base)
        bony = 0.0 if self.fit >= fit_base else (fit_base - self.fit)/(fit_base - min_fit)
        physique_range = 1000
        physique[SimInfo.BodyBlendTypes.BODYBLENDTYPE_HEAVY] = str(math.trunc(heavy*physique_range)/physique_range)
        physique[SimInfo.BodyBlendTypes.BODYBLENDTYPE_LEAN] = str(math.trunc(lean*physique_range)/physique_range)
        physique[SimInfo.BodyBlendTypes.BODYBLENDTYPE_FIT] = str(math.trunc(fit*physique_range)/physique_range)
        physique[SimInfo.BodyBlendTypes.BODYBLENDTYPE_BONY] = str(math.trunc(bony*physique_range)/physique_range)
        physique = ','.join([x for x in physique])
        self.physique = physique

    def _create_additional_statistics(self):
        sim_resolver = self.get_resolver()
        for init_stat in self.INITIAL_STATISTICS:
            if not init_stat.tests is None:
                if init_stat.tests.run_tests(sim_resolver):
                    tracker = self.get_tracker(init_stat.statistic)
                    tracker.add_statistic(init_stat.statistic)
            tracker = self.get_tracker(init_stat.statistic)
            tracker.add_statistic(init_stat.statistic)

    def _setup_fitness_commodities(self):
        self.commodity_tracker.set_value(ConsumableComponent.FAT_COMMODITY, self.fat)
        self.commodity_tracker.set_value(ConsumableComponent.FIT_COMMODITY, self.fit)
        fitness_commodity = self.commodity_tracker.get_statistic(ConsumableComponent.FIT_COMMODITY)
        if self._initial_fitness_value is None:
            self._initial_fitness_value = self.fit
        if self._initial_fitness_value > self.MAXIMUM_SAFE_FITNESS_VALUE:
            fitness_commodity.convergence_value = self.MAXIMUM_SAFE_FITNESS_VALUE
        else:
            fitness_commodity.convergence_value = self._initial_fitness_value
        fatness_commodity = self.commodity_tracker.get_statistic(ConsumableComponent.FAT_COMMODITY)
        fatness_commodity.core = True
        fitness_commodity.core = True

    @property
    def household_id(self):
        return self._household_id

    def assign_to_household(self, household, assign_is_npc=True):
        self._household_id = household.id if household is not None else None
        if assign_is_npc:
            self.resend_is_npc()
        sim = self.get_sim_instance(allow_hidden_flags=ALL_HIDDEN_REASONS)
        if sim is not None:
            for inv_obj in sim.inventory_component:
                inv_obj_current_household_id = inv_obj.get_household_owner_id()
                if inv_obj_current_household_id is not None:
                    if inv_obj_current_household_id != self._household_id:
                        inv_obj.set_household_owner_id(self._household_id)
                    else:
                        logger.error('Sim: {} has inventory object: {} already set to household id: {} when assigning sim to household.', sim, inv_obj, self._household_id)

    @property
    def travel_group_id(self):
        return self._travel_group_id

    def is_in_travel_group(self):
        if self._travel_group_id == 0:
            return False
        elif self.travel_group is None:
            return False
        return True

    def assign_to_travel_group(self, travel_group):
        if not (self._travel_group_id != 0 and (travel_group.id != self._travel_group_id or game_services.service_manager.is_traveling)):
            logger.error('Attempting to add a Sim to a second travel group. Sim: {}, Travel Group: {}'.format(self, travel_group), owner='rmccord')
            return False
        self._travel_group_id = travel_group.id
        return True

    def remove_from_travel_group(self, travel_group):
        if self._travel_group_id != travel_group.id:
            logger.error('Attempting to remove a Sim from a travel group they are not a part of.', owner='rmccord')
            return False
        self._travel_group_id = 0
        return True

    @property
    def is_at_home(self):
        if self.household is not None and self.household.home_zone_id != 0 and self.household.home_zone_id == self.zone_id:
            return True
        return self.is_renting_zone(self.zone_id)

    @property
    def lives_here(self):
        current_zone_id = services.current_zone_id()
        if self.household is not None and self.household.home_zone_id != 0 and current_zone_id == self.household.home_zone_id:
            return True
        return self.is_renting_zone(current_zone_id)

    @property
    def vacation_or_home_zone_id(self):
        travel_group = self.travel_group
        if travel_group is not None:
            return travel_group.zone_id
        if self.household is None:
            return 0
        else:
            return self.household.home_zone_id

    @property
    def can_care_for_toddler_at_home(self):
        if not self.can_live_alone:
            return False
        if self.household is None or self.household.home_zone_id != self.zone_id:
            return False
        elif self._career_tracker.get_currently_at_work_career():
            return False
        return True

    @property
    def can_live_alone(self):
        return self.is_teen_or_older and self.is_human

    def can_go_to_work(self, zone_id=DEFAULT):
        if self.household is None:
            return False
        if zone_id is DEFAULT:
            zone_id = services.current_zone_id()
        return self.household.home_zone_id == zone_id

    def should_send_home_to_go_to_work(self):
        if self.travel_group_id != 0:
            return False
        return True

    def should_add_foreign_zone_buff(self, zone_id):
        if self.household.home_zone_id == zone_id:
            return False
        else:
            travel_group = self.travel_group
            if travel_group is not None and travel_group.zone_id == zone_id:
                return False
        return True

    def is_renting_zone(self, zone_id):
        travel_group = self.travel_group
        if travel_group is not None:
            return travel_group.zone_id == zone_id
        return False

    @property
    def story_progression_tracker(self):
        return self._story_progression_tracker

    @property
    def genealogy(self):
        return self._genealogy_tracker

    @property
    def generation(self):
        return self._generation

    @generation.setter
    def generation(self, value):
        self._generation = value

    def set_and_propagate_family_relation(self, relation, sim_info):
        self._genealogy_tracker.set_and_propagate_family_relation(relation, sim_info)

    def get_family_sim_ids(self, include_self=False):
        return self._genealogy_tracker.get_family_sim_ids(include_self=include_self)

    def get_relation(self, relation):
        return self._genealogy_tracker.get_relation(relation)

    def incest_prevention_test(self, sim_info_b):
        sim_a_fam_data = set(self.get_family_sim_ids(include_self=True))
        sim_b_fam_data = set(sim_info_b.get_family_sim_ids(include_self=True))
        rel_union = sim_a_fam_data & sim_b_fam_data
        if None in rel_union:
            rel_union.remove(None)
        if rel_union:
            return False
        return True

    def set_freeze_fame(self, should_freeze, force=False):
        if should_freeze:
            if self.get_gameplay_option(SimInfoGameplayOptions.FREEZE_FAME):
                return
        elif not self.get_gameplay_option(SimInfoGameplayOptions.FREEZE_FAME):
            return
        self.set_gameplay_option(SimInfoGameplayOptions.FREEZE_FAME, should_freeze)
        if force or should_freeze:
            self.lock_statistic(FameTunables.FAME_RANKED_STATISTIC, StatisticLockAction.DO_NOT_CHANGE_VALUE)
        else:
            stat = self.get_statistic(FameTunables.FAME_RANKED_STATISTIC)
            if stat is None:
                logger.error('Trying to unfreeze fame for {}, but was unable to get or create a fame statistic', self)
            if self.is_in_locked_commodities(stat):
                self.unlock_statistic(FameTunables.FAME_RANKED_STATISTIC)

    def force_allow_fame(self, allow_fame):
        self.allow_fame = allow_fame
        self.set_gameplay_option(SimInfoGameplayOptions.FORCE_CURRENT_ALLOW_FAME_SETTING, True)

    @distributor.fields.Field(op=distributor.ops.SetAllowFame)
    def allow_fame(self):
        return self.get_gameplay_option(SimInfoGameplayOptions.ALLOW_FAME)

    @allow_fame.setter
    def allow_fame(self, value):
        self.set_gameplay_option(SimInfoGameplayOptions.ALLOW_FAME, value)
        stat = self.get_statistic(FameTunables.FAME_RANKED_STATISTIC)
        if value:
            if self.is_in_locked_commodities(stat):
                self.unlock_statistic(FameTunables.FAME_RANKED_STATISTIC)
        else:
            self.set_freeze_fame(False)
            if not self.is_in_locked_commodities(stat):
                self.lock_statistic(FameTunables.FAME_RANKED_STATISTIC, StatisticLockAction.USE_MIN_VALUE_TUNING)

    @distributor.fields.Field(op=distributor.ops.SetAllowReputation)
    def allow_reputation(self):
        return self.get_gameplay_option(SimInfoGameplayOptions.ALLOW_REPUTATION)

    @allow_reputation.setter
    def allow_reputation(self, value):
        self.set_gameplay_option(SimInfoGameplayOptions.ALLOW_REPUTATION, value)
        if value:
            stat = self.get_statistic(ReputationTunables.REPUTATION_RANKED_STATISTIC)
            if self.is_in_locked_commodities(stat):
                self.unlock_statistic(ReputationTunables.REPUTATION_RANKED_STATISTIC)
        else:
            self.lock_statistic(ReputationTunables.REPUTATION_RANKED_STATISTIC, StatisticLockAction.DO_NOT_CHANGE_VALUE)

    def get_gameplay_option(self, gameplay_option):
        if self._gameplay_options & gameplay_option:
            return True
        return False

    def set_gameplay_option(self, gameplay_option, value):
        if value == True if self._gameplay_options & gameplay_option else False:
            return
        if value:
            self._gameplay_options |= gameplay_option
        else:
            self._gameplay_options &= ~gameplay_option

    def add_sim_info_id_to_squad(self, sim_info_id):
        self._squad_members.add(sim_info_id)

    def remove_sim_info_id_from_squad(self, sim_info_id):
        if sim_info_id in self._squad_members:
            self._squad_members.remove(sim_info_id)

    @property
    def squad_members(self):
        return self._squad_members

    def _get_persisted_lod(self):
        if self.lod == SimInfoLODLevel.ACTIVE:
            return SimInfoLODLevel.FULL
        return self.lod

    def save_sim(self, for_cloning=False, full_service=False):
        if self.lod > SimInfoLODLevel.MINIMUM and self._aspiration_tracker is not None:
            self._aspiration_tracker.update_timers()
        attributes_msg = self._save_sim_attributes()
        if attributes_msg is None:
            return
        outfit_msg = self.save_outfits()
        if outfit_msg is None:
            return
        if self.lod == SimInfoLODLevel.MINIMUM:
            return self._save_sim_base(attributes_msg=attributes_msg, outfit_msg=outfit_msg)
        inventory_msg = self.inventory_data
        interactions_msg = None
        location_data = None
        sim = self.get_sim_instance(allow_hidden_flags=ALL_HIDDEN_REASONS)
        if sim is not None:
            inventory_msg = sim.get_inventory_proto_for_save()
            if inventory_msg is None:
                return
            self.inventory_data = inventory_msg
            interactions_msg = sim.si_state.save_interactions()
            if interactions_msg is None:
                return
            if full_service:
                self._serialization_option = self._get_serialization_option()
            if self._zone_id == services.current_zone_id():
                location_data = gameplay_serialization.WorldLocation()
                (position, orientation, level, surface_id) = sim.get_location_for_save()
                location_data.x = position.x
                location_data.y = position.y
                location_data.z = position.z
                location_data.rot_x = orientation.x
                location_data.rot_y = orientation.y
                location_data.rot_z = orientation.z
                location_data.rot_w = orientation.w
                location_data.level = level
                location_data.surface_id = surface_id
        elif self._transform_on_load is not None:
            location_data = gameplay_serialization.WorldLocation()
            transform = self._transform_on_load
            location_data.x = transform.translation.x
            location_data.y = transform.translation.y
            location_data.z = transform.translation.z
            location_data.rot_x = transform.orientation.x
            location_data.rot_y = transform.orientation.y
            location_data.rot_z = transform.orientation.z
            location_data.rot_w = transform.orientation.w
            location_data.level = self._level_on_load
            location_data.surface_id = self._surface_id_on_load
        sim_msg = self._save_sim_base(attributes_msg=attributes_msg, outfit_msg=outfit_msg, inventory_msg=inventory_msg, interactions_msg=interactions_msg, location_data=location_data, for_cloning=for_cloning)
        return sim_msg

    def _save_sim_base(self, attributes_msg=None, outfit_msg=None, inventory_msg=None, interactions_msg=None, location_data=None, for_cloning=False):
        self._set_fit_fat()
        sim_msg = services.get_persistence_service().get_sim_proto_buff(self.sim_id)
        if sim_msg is None:
            sim_msg = services.get_persistence_service().add_sim_proto_buff(self.sim_id)
        if for_cloning:
            clone_sim_msg = serialization.SimData()
            clone_sim_msg.MergeFrom(sim_msg)
            return self._generate_sim_protocol_buffer(clone_sim_msg, attributes_msg=attributes_msg, outfit_msg=outfit_msg, inventory_msg=inventory_msg, interactions_msg=interactions_msg, location_data=location_data, for_cloning=for_cloning)
        return self._generate_sim_protocol_buffer(sim_msg, attributes_msg=attributes_msg, outfit_msg=outfit_msg, inventory_msg=inventory_msg, interactions_msg=interactions_msg, location_data=location_data, for_cloning=for_cloning)

    def _generate_sim_protocol_buffer(self, sim_msg, attributes_msg=None, outfit_msg=None, inventory_msg=None, interactions_msg=None, location_data=None, for_cloning=False):
        if self._whim_tracker is None:
            old_bucks_count = sim_msg.gameplay_data.whim_bucks
        sim_msg.Clear()
        sim_msg.sim_id = self.sim_id
        sim_msg.zone_id = self._zone_id
        sim_msg.world_id = self._world_id
        sim_msg.first_name = self._base.first_name
        sim_msg.last_name = self._base.last_name
        sim_msg.breed_name = self._base.breed_name
        sim_msg.first_name_key = self._base.first_name_key
        sim_msg.last_name_key = self._base.last_name_key
        sim_msg.full_name_key = self._base.full_name_key
        sim_msg.breed_name_key = self._base.breed_name_key
        sim_msg.gender = self.gender
        sim_msg.extended_species = self.extended_species
        sim_msg.age = self.age
        sim_msg.skin_tone = self._base.skin_tone
        sim_msg.pelt_layers.MergeFromString(self._base.pelt_layers)
        sim_msg.custom_texture = self._base.custom_texture
        sim_msg.voice_pitch = self._base.voice_pitch
        sim_msg.voice_actor = self._base.voice_actor
        sim_msg.voice_effect = self._base.voice_effect
        sim_msg.physique = self._base.physique
        sim_msg.facial_attr = self._base.facial_attributes or bytes(0)
        sim_msg.genetic_data.MergeFromString(self._base.genetic_data)
        sim_msg.fix_relationship = False
        sim_msg.generation = self._generation
        sim_msg.sim_lod = self._get_persisted_lod()
        sim_msg.outfits = outfit_msg
        sim_msg.flags = self._base.flags
        household_id = self._household_id if self._household_id is not None else 0
        sim_msg.household_id = household_id
        household = self.household
        sim_msg.household_name = household.name if household is not None else ''
        sim_msg.nucleus_id = self.account_id
        self._revision += 1
        sim_msg.revision = self._revision
        sim_msg.attributes = attributes_msg
        if self.spouse_sim_id is not None:
            sim_msg.significant_other = self.spouse_sim_id
        sim_msg.gameplay_data.serialization_option = self._serialization_option
        SimInfoCreationSource.save_creation_source(self.creation_source, sim_msg)
        sim_msg.created = services.time_service().sim_now.absolute_ticks()
        sim_msg.gameplay_data.old_household_id = household_id
        sim_msg.gameplay_data.premade_sim_template_id = self.premade_sim_template_id
        if self.lod == SimInfoLODLevel.MINIMUM:
            return sim_msg
        sim_msg.pregnancy_progress = self.pregnancy_progress
        sim_msg.age_progress = self._age_progress.get_value()
        sim_msg.age_progress_randomized = True
        sim_msg.inventory = inventory_msg
        sim_msg.primary_aspiration = self._primary_aspiration.guid64 if self._primary_aspiration is not None else 0
        (outfit_type, outfit_index) = self._current_outfit
        if outfit_index == SpecialOutfitIndex.DEFAULT:
            (outfit_type, outfit_index) = self.get_previous_outfit()
        if outfit_type == OutfitCategory.SPECIAL and outfit_type == OutfitCategory.BATHING:
            outfit_type = OutfitCategory.EVERYDAY
            outfit_index = 0
        outfit_category_tuning = OutfitTuning.OUTFIT_CATEGORY_TUNING.get(outfit_type)
        if outfit_category_tuning.save_outfit_category is None:
            sim_msg.current_outfit_type = outfit_type
        else:
            sim_msg.current_outfit_type = outfit_category_tuning.save_outfit_category
        sim_msg.current_outfit_index = outfit_index
        sim_msg.gameplay_data.inventory_value = self.inventory_value()
        if interactions_msg is not None:
            sim_msg.gameplay_data.interaction_state = interactions_msg
            if not for_cloning:
                self._si_state.Clear()
                self._si_state.MergeFrom(interactions_msg)
                self._has_loaded_si_state = True
        sim_msg.gameplay_data.additional_bonus_days = self._additional_bonus_days
        if self.spawn_point_id is not None:
            sim_msg.gameplay_data.spawn_point_id = self.spawn_point_id
        sim_msg.gameplay_data.spawn_point_option = self.spawn_point_option
        sim_msg.gameplay_data.spawner_tags.extend(self.spawner_tags)
        sim_msg.gameplay_data.build_buy_unlock_list = ResourceKeyList()
        for unlock in self.build_buy_unlocks:
            if isinstance(unlock, int):
                pass
            else:
                key_proto = sims4.resources.get_protobuff_for_key(unlock)
                sim_msg.gameplay_data.build_buy_unlock_list.resource_keys.append(key_proto)
        if self._whim_tracker is not None:
            sim_msg.gameplay_data.whim_bucks = self._whim_bucks
            self._whim_tracker.save_whims_info_to_proto(sim_msg.gameplay_data.whim_tracker)
        else:
            sim_msg.gameplay_data.whim_bucks = old_bucks_count
        self._away_action_tracker.save_away_action_info_to_proto(sim_msg.gameplay_data.away_action_tracker)
        now_time = services.time_service().sim_now
        sim_msg.gameplay_data.zone_time_stamp.time_sim_info_was_saved = now_time.absolute_ticks()
        if self.is_instanced(allow_hidden_flags=ALL_HIDDEN_REASONS):
            sim_msg.gameplay_data.zone_time_stamp.time_sim_was_saved = now_time.absolute_ticks()
        elif self._time_sim_was_saved is not None:
            sim_msg.gameplay_data.zone_time_stamp.time_sim_was_saved = self._time_sim_was_saved.absolute_ticks()
        if household.home_zone_id != self._zone_id:
            if self.is_instanced(allow_hidden_flags=ALL_HIDDEN_REASONS):
                time_expire = self._get_time_to_go_home()
                sim_msg.gameplay_data.zone_time_stamp.game_time_expire = time_expire.absolute_ticks()
            elif self.game_time_bring_home is not None:
                sim_msg.gameplay_data.zone_time_stamp.game_time_expire = self.game_time_bring_home
        if household is not None and location_data is not None:
            sim_msg.gameplay_data.location = location_data
        current_mood = self.get_mood()
        current_mood_intensity = self.get_mood_intensity()
        sim_msg.current_mood = current_mood.guid64
        try:
            sim_msg.current_mood_intensity = current_mood_intensity
        except ValueError:
            logger.error('Mood intensity is {} for {}. Setting to 0', current_mood_intensity, current_mood)
            sim_msg.current_mood_intensity = 0
        if self._initial_fitness_value is not None:
            sim_msg.initial_fitness_value = self._initial_fitness_value
        self.update_time_alive()
        sim_msg.gameplay_data.time_alive = self._time_alive.in_ticks()
        self.save_favorite(sim_msg.gameplay_data.favorite_data)
        if self._bucks_tracker is not None:
            self._bucks_tracker.save_data(sim_msg.gameplay_data)
        sim_msg.gameplay_data.gameplay_options = self._gameplay_options
        if self._squad_members:
            sim_msg.gameplay_data.squad_members.extend([sim_info_id for sim_info_id in self._squad_members])
        if SAVE_ACTIVE_HOUSEHOLD_COMMAND:
            sim_msg.sim_creation_path = serialization.SimData.SIMCREATION_PRE_MADE
            persist_fields_for_custom_option(sim_msg, custom_options.persist_for_new_game)
        if for_cloning:
            sim_msg.sim_creation_path = serialization.SimData.SIMCREATION_CLONED
            persist_fields_for_custom_option(sim_msg, custom_options.persist_for_cloned_sim)
        return sim_msg

    def _save_sim_attributes(self):
        sim_pb = services.get_persistence_service().get_sim_proto_buff(self.sim_id)
        old_attributes_save = sim_pb.attributes if sim_pb is not None else None
        attributes_save = protocols.PersistableSimInfoAttributes()
        attributes_save.occult_tracker = self._occult_tracker.save()
        death_save = self._death_tracker.save()
        if death_save is not None:
            attributes_save.death_tracker = self._death_tracker.save()
        attributes_save.genealogy_tracker = self._genealogy_tracker.save_genealogy()
        if self.lod == SimInfoLODLevel.MINIMUM:
            return attributes_save
        attributes_save.pregnancy_tracker = self._pregnancy_tracker.save()
        attributes_save.sim_careers = self._career_tracker.save()
        attributes_save.trait_tracker = self._trait_tracker.save()
        attributes_save.story_progression_tracker = self._story_progression_tracker.save()
        for (tag, obj_id) in self._autonomy_scoring_preferences.items():
            with ProtocolBufferRollback(attributes_save.object_preferences.preferences) as entry:
                entry.tag = tag
                entry.object_id = obj_id
        for (tag, obj_id) in self._autonomy_use_preferences.items():
            with ProtocolBufferRollback(attributes_save.object_ownership.owned_object) as entry:
                entry.tag = tag
                entry.object_id = obj_id
        stored_object_info_component = self.get_component(objects.components.types.STORED_OBJECT_INFO_COMPONENT)
        if stored_object_info_component is not None:
            attributes_save.stored_object_info_component = stored_object_info_component.get_save_data()
        (commodites, skill_statistics, ranked_statistics) = self.commodity_tracker.save()
        attributes_save.commodity_tracker.commodities.extend(commodites)
        regular_statistics = self.statistic_tracker.save()
        attributes_save.statistics_tracker.statistics.extend(regular_statistics)
        attributes_save.skill_tracker.skills.extend(skill_statistics)
        attributes_save.ranked_statistic_tracker.ranked_statistics.extend(ranked_statistics)
        attributes_save.suntan_tracker = self._suntan_tracker.save()
        if self._familiar_tracker is not None:
            attributes_save.familiar_tracker = self._familiar_tracker.save()
        elif old_attributes_save is not None:
            attributes_save.familiar_tracker.MergeFrom(old_attributes_save.familiar_tracker)
        if self._favorites_tracker is not None:
            attributes_save.favorites_tracker = self._favorites_tracker.save()
        elif old_attributes_save is not None:
            attributes_save.favorites_tracker.MergeFrom(old_attributes_save.favorites_tracker)
        if self._aspiration_tracker is not None:
            self._aspiration_tracker.save(attributes_save.event_data_tracker)
        elif old_attributes_save is not None:
            attributes_save.event_data_tracker.MergeFrom(old_attributes_save.event_data_tracker)
        if self._unlock_tracker is not None:
            attributes_save.unlock_tracker = self._unlock_tracker.save_unlock()
        elif old_attributes_save is not None:
            attributes_save.unlock_tracker.MergeFrom(old_attributes_save.unlock_tracker)
        if self._notebook_tracker is not None:
            attributes_save.notebook_tracker = self._notebook_tracker.save_notebook()
        elif old_attributes_save is not None:
            attributes_save.notebook_tracker.MergeFrom(old_attributes_save.notebook_tracker)
        if self._adventure_tracker is not None:
            attributes_save.adventure_tracker = self._adventure_tracker.save()
        elif old_attributes_save is not None:
            attributes_save.adventure_tracker.MergeFrom(old_attributes_save.adventure_tracker)
        if self._royalty_tracker is not None:
            attributes_save.royalty_tracker = self._royalty_tracker.save()
        elif old_attributes_save is not None:
            attributes_save.royalty_tracker.MergeFrom(old_attributes_save.royalty_tracker)
        if self._relic_tracker is not None:
            attributes_save.relic_tracker = self._relic_tracker.save()
        elif old_attributes_save is not None:
            attributes_save.relic_tracker.MergeFrom(old_attributes_save.relic_tracker)
        if self._sickness_tracker is not None:
            if self._sickness_tracker.should_persist_data():
                attributes_save.sickness_tracker = self._sickness_tracker.sickness_tracker_save_data()
        elif old_attributes_save is not None:
            attributes_save.sickness_tracker.MergeFrom(old_attributes_save.sickness_tracker)
        if self._lifestyle_brand_tracker is not None:
            attributes_save.lifestyle_brand_tracker = self._lifestyle_brand_tracker.save()
        elif old_attributes_save is not None:
            attributes_save.lifestyle_brand_tracker.MergeFrom(old_attributes_save.lifestyle_brand_tracker)
        attributes_save.appearance_tracker = self.appearance_tracker.save_appearance_tracker()
        return attributes_save

    def _get_serialization_option(self):
        sim = self.get_sim_instance(allow_hidden_flags=HiddenReasonFlag.RABBIT_HOLE)
        if sim is None:
            return self._serialization_option
        owning_household = services.current_zone().get_active_lot_owner_household()
        situation_manager = services.get_zone_situation_manager()
        current_zone_id = services.current_zone_id()
        if sim.is_selectable or owning_household is not None and self in owning_household or self.is_renting_zone(current_zone_id):
            if sim.is_on_active_lot() or sim.has_hidden_flags(HiddenReasonFlag.RABBIT_HOLE):
                return SimSerializationOption.LOT
            return SimSerializationOption.OPEN_STREETS
        return situation_manager.get_sim_serialization_option(sim)

    def _save_for_travel(self):
        sim = self.get_sim_instance(allow_hidden_flags=ALL_HIDDEN_REASONS_EXCEPT_UNINITIALIZED)
        if sim is None:
            return
        interactions_msg = sim.si_state.save_interactions()
        if interactions_msg is None:
            return
        inventory_msg = sim.get_inventory_proto_for_save()
        if inventory_msg is None:
            return
        sim_msg = services.get_persistence_service().get_sim_proto_buff(self.sim_id)
        if sim_msg is None:
            self.save_sim()
        self._si_state.Clear()
        self._si_state.MergeFrom(interactions_msg)
        self._has_loaded_si_state = True
        self.inventory_data = inventory_msg
        self._serialization_option = self._get_serialization_option()
        (position, orientation, level, surface_id) = sim.get_location_for_save()
        world_coord = sims4.math.Transform(position, orientation)
        self._transform_on_load = world_coord
        self._level_on_load = level
        self._surface_id_on_load = surface_id
        sim_msg.gameplay_data.interaction_state = interactions_msg
        sim_msg.inventory = inventory_msg
        location_data = gameplay_serialization.WorldLocation()
        location_data.x = position.x
        location_data.y = position.y
        location_data.z = position.z
        location_data.rot_x = orientation.x
        location_data.rot_y = orientation.y
        location_data.rot_z = orientation.z
        location_data.rot_w = orientation.w
        location_data.level = level
        location_data.surface_id = surface_id
        sim_msg.gameplay_data.location = location_data
        if self.household.home_zone_id != self._zone_id:
            self.game_time_bring_home = self._get_time_to_go_home()

    def load_for_travel_to_current_zone(self):
        sim_proto = services.get_persistence_service().get_sim_proto_buff(self.sim_id)
        if sim_proto is None:
            logger.error("Missing persistence for {}. Can't update due to travel", self)
            return
        self._zone_id = sim_proto.zone_id
        self.zone_name = sim_proto.zone_name
        self._world_id = sim_proto.world_id

    def load_sim_info(self, sim_proto, is_clone=False, default_lod=SimInfoLODLevel.BASE):
        self._base.species = sim_proto.extended_species
        self._species = SpeciesExtended.get_species(self.extended_species)
        required_pack = SpeciesExtended.get_required_pack(self.extended_species)
        if required_pack is not None and not is_available_pack(required_pack):
            raise UnavailablePackError('Cannot load Sims with species {}'.format(self.extended_species))
        if indexed_manager.capture_load_times:
            time_stamp = time.time()
            species_def = self.get_sim_definition(self.species)
            if species_def not in indexed_manager.object_load_times:
                indexed_manager.object_load_times[species_def] = ObjectLoadData()
        self._sim_creation_path = sim_proto.sim_creation_path
        self._lod = SimInfoLODLevel(sim_proto.sim_lod) if sim_proto.HasField('sim_lod') else default_lod
        self._initialize_sim_info_trackers(self._lod)
        skip_load = self._sim_creation_path != serialization.SimData.SIMCREATION_NONE
        if sim_proto.gender == types.Gender.MALE or sim_proto.gender == types.Gender.FEMALE:
            self._base.gender = sim_proto.gender
        self._base.age = types.Age(sim_proto.age)
        if not INJECT_LOD_NAME_IN_CALLSTACK:
            self._load_sim_info(sim_proto, skip_load, is_clone=is_clone)
            if indexed_manager.capture_load_times:
                time_elapsed = time.time() - time_stamp
                indexed_manager.object_load_times[species_def].time_spent_loading += time_elapsed
                indexed_manager.object_load_times[species_def].loads += 1
            return
        name_f = create_custom_named_profiler_function('Load LOD {} SimInfo'.format(self._lod.name))
        name_f(lambda : self._load_sim_info(sim_proto, skip_load, is_clone=is_clone))
        if indexed_manager.capture_load_times:
            time_elapsed = time.time() - time_stamp
            indexed_manager.object_load_times[species_def].time_spent_loading += time_elapsed
            indexed_manager.object_load_times[species_def].loads += 1

    def _load_sim_info(self, sim_proto, skip_load, is_clone=False):
        self._base.first_name = sim_proto.first_name
        self._base.last_name = sim_proto.last_name
        self._base.breed_name = sim_proto.breed_name
        self._base.first_name_key = sim_proto.first_name_key
        self._base.last_name_key = sim_proto.last_name_key
        self._base.full_name_key = sim_proto.full_name_key
        self._base.breed_name_key = sim_proto.breed_name_key
        self._zone_id = sim_proto.zone_id
        self.zone_name = sim_proto.zone_name
        self._world_id = sim_proto.world_id
        self._household_id = sim_proto.household_id
        self._serialization_option = sim_proto.gameplay_data.serialization_option
        self._base.skin_tone = sim_proto.skin_tone
        self._base.pelt_layers = sim_proto.pelt_layers.SerializeToString()
        self._base.custom_texture = sim_proto.custom_texture
        self._base.voice_pitch = sim_proto.voice_pitch
        self._base.voice_actor = sim_proto.voice_actor
        self._base.voice_effect = sim_proto.voice_effect
        self._base.physique = sim_proto.physique
        self._base.facial_attributes = sim_proto.facial_attr
        self._generation = sim_proto.generation
        self._fix_relationships = sim_proto.fix_relationship
        self.do_first_sim_info_load_fixups = self._sim_creation_path != serialization.SimData.SIMCREATION_NONE
        self._get_fit_fat()
        sim_attribute_data = sim_proto.attributes
        if sim_attribute_data is not None:
            self.set_trait_ids_on_base(trait_ids_override=list(set(itertools.chain(sim_attribute_data.trait_tracker.trait_ids, self.trait_ids))))
        self.load_outfits(sim_proto.outfits)
        self.creation_source = SimInfoCreationSource.load_creation_source(sim_proto)
        self._nucleus_id = sim_proto.nucleus_id
        self._base.genetic_data = sim_proto.genetic_data.SerializeToString()
        self._base.flags = sim_proto.flags
        self.premade_sim_template_id = sim_proto.gameplay_data.premade_sim_template_id
        self._revision = sim_proto.revision
        if sim_attribute_data is not None:
            self._relationship_tracker.load(sim_attribute_data.relationship_tracker.relationships)
            self._genealogy_tracker.load_genealogy(sim_attribute_data.genealogy_tracker)
            self._death_tracker.load(sim_attribute_data.death_tracker)
            self._occult_tracker.load(sim_attribute_data.occult_tracker)
            if sim_proto.significant_other != 0:
                self.update_spouse_sim_id(sim_proto.significant_other)
        Ghost.make_ghost_if_needed(self)
        if self.lod == SimInfoLODLevel.MINIMUM:
            services.sim_info_manager().add_sim_info_if_not_in_manager(self)
            return
        age_progress = sim_proto.age_progress
        if not sim_proto.age_progress_randomized:
            age_progress = self.get_randomized_progress(age_progress)
        self._age_progress.set_value(age_progress)
        self._build_buy_unlocks = set()
        old_unlocks = set(list(sim_proto.gameplay_data.build_buy_unlocks))
        for unlock in old_unlocks:
            if isinstance(unlock, int):
                key = sims4.resources.Key(Types.OBJCATALOG, unlock, 0)
                self._build_buy_unlocks.add(key)
        if hasattr(sim_proto.gameplay_data, 'build_buy_unlock_list'):
            for key_proto in sim_proto.gameplay_data.build_buy_unlock_list.resource_keys:
                key = sims4.resources.Key(key_proto.type, key_proto.instance, key_proto.group)
                self._build_buy_unlocks.add(key)
        self._primary_aspiration = services.get_instance_manager(sims4.resources.Types.ASPIRATION_TRACK).get(sim_proto.primary_aspiration)
        if not self.is_toddler_or_younger:
            available_aspirations = []
            aspiration_track_manager = services.get_instance_manager(sims4.resources.Types.ASPIRATION_TRACK)
            for aspiration_track in aspiration_track_manager.types.values():
                if aspiration_track.is_child_aspiration_track:
                    if self.is_child:
                        available_aspirations.append(aspiration_track)
                elif not self.is_child:
                    available_aspirations.append(aspiration_track)
            self._primary_aspiration = random.choice(available_aspirations)
        self._cached_inventory_value = sim_proto.gameplay_data.inventory_value
        if self._primary_aspiration is None or self._primary_aspiration.is_available() or not (self.is_human and skip_load):
            self._away_action_tracker.load_away_action_info_from_proto(sim_proto.gameplay_data.away_action_tracker)
        self.spawn_point_id = sim_proto.gameplay_data.spawn_point_id if sim_proto.gameplay_data.HasField('spawn_point_id') else None
        self.spawn_point_option = SpawnPointOption(sim_proto.gameplay_data.spawn_point_option) if sim_proto.gameplay_data.HasField('spawn_point_option') else SpawnPointOption.SPAWN_ANY_POINT_WITH_CONSTRAINT_TAGS
        self.spawner_tags = []
        if sim_proto.HasField('initial_fitness_value'):
            self._initial_fitness_value = sim_proto.initial_fitness_value
        if sim_proto.gameplay_data.HasField('time_alive'):
            time_alive = TimeSpan(sim_proto.gameplay_data.time_alive)
        else:
            time_alive = None
        self.load_time_alive(time_alive)
        for spawner_tag in sim_proto.gameplay_data.spawner_tags:
            self.spawner_tags.append(tag.Tag(spawner_tag))
        try:
            self.Buffs.load_in_progress = True
            self.commodity_tracker.load_in_progress = True
            self.on_base_characteristic_changed()
            with services.relationship_service().suppress_client_updates_context_manager():
                self._trait_tracker.load(sim_attribute_data.trait_tracker, skip_load)
        finally:
            self.Buffs.load_in_progress = False
            self.commodity_tracker.load_in_progress = False
        self._create_additional_statistics()
        if self._whim_tracker is not None:
            self.set_whim_bucks(sim_proto.gameplay_data.whim_bucks, SetWhimBucks.LOAD)
            self._whim_tracker.cache_whim_goal_proto(sim_proto.gameplay_data.whim_tracker, skip_load=skip_load)
        if sim_proto.HasField('current_outfit_type'):
            outfit_type = sim_proto.current_outfit_type
            outfit_index = sim_proto.current_outfit_index
            self._set_current_outfit_without_distribution((outfit_type, outfit_index))
        self._load_inventory(sim_proto, skip_load)
        self._additional_bonus_days = sim_proto.gameplay_data.additional_bonus_days
        self.load_favorite(sim_proto.gameplay_data.favorite_data)
        if sim_proto.gameplay_data.zone_time_stamp.HasField('time_sim_was_saved'):
            self._time_sim_was_saved = DateAndTime(sim_proto.gameplay_data.zone_time_stamp.time_sim_was_saved)
        if skip_load or sim_proto.gameplay_data.zone_time_stamp.game_time_expire != 0:
            self.game_time_bring_home = sim_proto.gameplay_data.zone_time_stamp.game_time_expire
        if sim_attribute_data:
            try:
                self.Buffs.load_in_progress = True
                self._blacklisted_statistics_cache = self.get_blacklisted_statistics()
                self.commodity_tracker.load(sim_attribute_data.commodity_tracker.commodities, skip_load=skip_load, update_affordance_cache=False)
                if self.lod > SimInfoLODLevel.BASE:
                    for commodity in tuple(self.commodity_tracker):
                        if commodity.has_auto_satisfy_value():
                            commodity.set_to_auto_satisfy_value()
                self.statistic_tracker.load(sim_attribute_data.statistics_tracker.statistics, skip_load=skip_load)
                self.commodity_tracker.load(sim_attribute_data.skill_tracker.skills, update_affordance_cache=False)
                self.commodity_tracker.load(sim_attribute_data.ranked_statistic_tracker.ranked_statistics, update_affordance_cache=True)
                self._suntan_tracker.load(sim_attribute_data.suntan_tracker)
                skills_to_check_for_unlocks = [commodity for commodity in self.commodity_tracker.get_all_commodities() if commodity.unlocks_skills_on_max() and len(commodity.skill_unlocks_on_max) > 0]
                if skills_to_check_for_unlocks:
                    self._check_skills_for_unlock(skills_to_check_for_unlocks, sim_attribute_data.skill_tracker.skills)
                self._pregnancy_tracker.load(sim_attribute_data.pregnancy_tracker)
                self._story_progression_tracker.load(sim_attribute_data.story_progression_tracker)
                self.appearance_tracker.load_appearance_tracker(sim_attribute_data.appearance_tracker)
                if sim_attribute_data.HasField('sickness_tracker'):
                    self.sickness_tracker.load_sickness_tracker_data(sim_attribute_data.sickness_tracker)
                    if self.has_sickness_tracking():
                        self.current_sickness.on_sim_info_loaded(self)
                if sim_attribute_data.HasField('stored_object_info_component'):
                    component_def = objects.components.types.STORED_OBJECT_INFO_COMPONENT
                    if self.add_dynamic_component(component_def):
                        stored_object_info_component = self.get_component(component_def)
                        stored_object_info_component.load_stored_object_info(sim_attribute_data.stored_object_info_component)
                for entry in sim_attribute_data.object_preferences.preferences:
                    self._autonomy_scoring_preferences[entry.tag] = entry.object_id
                for entry in sim_attribute_data.object_ownership.owned_object:
                    self._autonomy_use_preferences[entry.tag] = entry.object_id
                self._career_tracker.load(sim_attribute_data.sim_careers, skip_load=skip_load)
                if self._adventure_tracker is not None:
                    self._adventure_tracker.load(sim_attribute_data.adventure_tracker)
                if self._notebook_tracker is not None:
                    self._notebook_tracker.load_notebook(sim_attribute_data.notebook_tracker)
                if self._royalty_tracker is not None and not skip_load:
                    self._royalty_tracker.load(sim_attribute_data.royalty_tracker)
                if not (self._unlock_tracker is not None and (is_clone or skip_load)):
                    self._unlock_tracker.load_unlock(sim_attribute_data.unlock_tracker)
                if self._relic_tracker is not None and not skip_load:
                    self._relic_tracker.load(sim_attribute_data.relic_tracker)
                if self._lifestyle_brand_tracker is not None and not skip_load:
                    self._lifestyle_brand_tracker.load(sim_attribute_data.lifestyle_brand_tracker)
                if self._favorites_tracker is not None and not skip_load:
                    self._favorites_tracker.load(sim_attribute_data.favorites_tracker)
            except:
                logger.exception('Failed to load attributes for sim {}.', self._base.first_name)
            finally:
                self._blacklisted_statistics_cache = None
                self.Buffs.load_in_progress = False
        self._setup_fitness_commodities()
        if self._serialization_option != SimSerializationOption.UNDECLARED:
            world_coord = sims4.math.Transform()
            location = sim_proto.gameplay_data.location
            world_coord.translation = sims4.math.Vector3(location.x, location.y, location.z)
            world_coord.orientation = sims4.math.Quaternion(location.rot_x, location.rot_y, location.rot_z, location.rot_w)
            self._transform_on_load = world_coord
            self._level_on_load = location.level
            self._surface_id_on_load = location.surface_id
        self._si_state = gameplay_serialization.SuperInteractionSaveState()
        if skip_load or sim_proto.gameplay_data.HasField('location') and sim_proto.gameplay_data.HasField('interaction_state'):
            self._has_loaded_si_state = True
            self._si_state.MergeFrom(sim_proto.gameplay_data.interaction_state)
        services.sim_info_manager().add_sim_info_if_not_in_manager(self)
        if len(sim_proto.gameplay_data.bucks_data) > 0:
            bucks_tracker = self.get_bucks_tracker(add_if_none=True)
            bucks_tracker.load_data(sim_proto.gameplay_data)
        if sim_proto.gameplay_data.HasField('gameplay_options'):
            self._gameplay_options = sim_proto.gameplay_data.gameplay_options
            if self.get_gameplay_option(SimInfoGameplayOptions.FORCE_CURRENT_ALLOW_FAME_SETTING) and not self.get_gameplay_option(SimInfoGameplayOptions.ALLOW_FAME):
                self.allow_fame = False
            elif self.get_gameplay_option(SimInfoGameplayOptions.FREEZE_FAME):
                self.set_freeze_fame(True, force=True)
        sim_info_manager = services.sim_info_manager()
        for squad_member_id in sim_proto.gameplay_data.squad_members:
            self.add_sim_info_id_to_squad(squad_member_id)
        self._post_load()

    def _get_time_to_go_home(self):
        random_minutes = PersistenceTuning.MINUTES_STAY_ON_LOT_BEFORE_GO_HOME.random_int()
        random_minutes_time_span = date_and_time.create_time_span(minutes=random_minutes)
        return services.time_service().sim_now + random_minutes_time_span

    def get_blacklisted_statistics(self):
        if self._blacklisted_statistics_cache is not None:
            return self._blacklisted_statistics_cache
        blacklisted_statistics = set()
        for trait in self.trait_tracker:
            blacklisted_statistics.update(trait.initial_commodities_blacklist)
        return tuple(blacklisted_statistics)

    def _initialize_sim_info_trackers(self, lod):
        for (tracker_attr, tracker_type) in SimInfo.SIM_INFO_TRACKERS.items():
            if tracker_type.is_valid_for_lod(lod):
                setattr(self, tracker_attr, tracker_type(self))

    def report_telemetry(self, report_source_string):
        with telemetry_helper.begin_hook(simulation_error_writer, TELEMETRY_SIMULATION_ERROR, sim_info=self, valid_for_npc=True) as hook:
            hook.write_int('smid', self.sim_id)
            hook.write_string('snam', self.full_name)
            hook.write_string('hoid', str(self._household_id))
            hook.write_int('crid', self._sim_creation_path)
            self.creation_source.write_creation_source(hook)
            hook.write_string('csrc', report_source_string)

    def load_from_resource(self, resource_key):
        super().load_from_resource(resource_key)
        self._get_fit_fat()
        self._setup_fitness_commodities()
        aspiration_manager = services.get_instance_manager(sims4.resources.Types.ASPIRATION_TRACK)
        aspiration = aspiration_manager.get(self._base.aspiration_id)
        if aspiration.is_available():
            self.primary_aspiration = aspiration
        for trait in tuple(self.trait_tracker):
            if aspiration is None and trait.is_aspiration_trait:
                pass
            else:
                self.remove_trait(trait)
        trait_manager = services.get_instance_manager(sims4.resources.Types.TRAIT)
        for trait_id in self._base.base_trait_ids:
            trait = trait_manager.get(trait_id)
            if trait is not None:
                self.add_trait(trait)
        self._update_age_trait(self.age)
        self.on_base_characteristic_changed()

    def push_to_relgraph(self):
        if RelgraphService.RELGRAPH_ENABLED:
            self._base.push_to_relgraph()

    def _load_inventory(self, sim_proto, skip_load):
        inventory_data = serialization.ObjectList()
        if not skip_load:
            inventory_data.MergeFrom(sim_proto.inventory)
        if sim_proto.gameplay_data.HasField('old_household_id'):
            old_household_id = sim_proto.gameplay_data.old_household_id
            if old_household_id != self._household_id:
                for inv_obj in inventory_data.objects:
                    if inv_obj.owner_id == old_household_id:
                        inv_obj.owner_id = self._household_id
        self._inventory_data = inventory_data

    def apply_fixup_actions(self, fixup_source):
        for trait in tuple(self.trait_tracker):
            if trait.should_apply_fixup_actions(fixup_source):
                trait.apply_fixup_actions(self)
                self.remove_trait(trait)

    def fixup_inventory(self):
        if self.inventory_data is None:
            return
        pruned_inventory = serialization.ObjectList()
        zone_id = services.current_zone_id()
        inventory_manager = services.inventory_manager()
        count = 0
        for inv_obj in self.inventory_data.objects:
            if not self.is_player_sim:
                def_id = build_buy.get_vetted_object_defn_guid(zone_id, inv_obj.object_id, inv_obj.guid or inv_obj.type)
                if def_id is None:
                    count += 1
                elif InventoryItemComponent.should_item_be_removed_from_inventory(def_id):
                    count += 1
                else:
                    attribute_data = protocols.PersistenceMaster()
                    attribute_data.ParseFromString(inv_obj.attributes)
                    if inventory_manager.has_inventory_item_failed_claiming(inv_obj.object_id, attribute_data.data):
                        count += 1
                    else:
                        pruned_inventory.objects.append(inv_obj)
            else:
                attribute_data = protocols.PersistenceMaster()
                attribute_data.ParseFromString(inv_obj.attributes)
                if inventory_manager.has_inventory_item_failed_claiming(inv_obj.object_id, attribute_data.data):
                    count += 1
                else:
                    pruned_inventory.objects.append(inv_obj)
        if count > 0:
            logger.info('Inventory Purge: NPC {} lost {} objects from inventory.', str(self), count)
        self.inventory_data = pruned_inventory

    def _check_skills_for_unlock(self, skills, commodity_loading_data):
        open_set = set(skills)
        closed_set = set()
        while open_set:
            current_skill = open_set.pop()
            closed_set.add(current_skill)
            if not current_skill.reached_max_level:
                pass
            else:
                for skill_to_unlock in current_skill.skill_unlocks_on_max:
                    if skill_to_unlock not in closed_set:
                        self.commodity_tracker.add_statistic(skill_to_unlock, force_add=True)
                        skill_data_object = [sdo for sdo in commodity_loading_data if sdo.name_hash == skill_to_unlock.guid64]
                        self.commodity_tracker.load(skill_data_object)
                        open_set.add(skill_to_unlock)

    def _post_load(self):
        self.refresh_age_settings()
        self.publish_all_commodities()
        services.sim_info_manager().try_set_sim_fame_option_to_global_option(self)

    def on_all_sim_infos_loaded(self):
        if self.lod == SimInfoLODLevel.MINIMUM:
            return
        self.career_tracker.remove_invalid_careers()
        if self.familiar_tracker is not None:
            self.familiar_tracker.on_all_sim_infos_loaded()

    def refresh_age_settings(self):
        aging_service = services.get_aging_service()
        self._auto_aging_enabled = aging_service.is_aging_enabled_for_sim_info(self)
        self._age_speed_setting = aging_service.aging_speed
        self.update_age_callbacks()

    def on_zone_unload(self):
        if self.lod == SimInfoLODLevel.MINIMUM:
            return
        if game_services.service_manager.is_traveling:
            self._save_for_travel()
        self._career_tracker.on_zone_unload()
        if self._aspiration_tracker is not None:
            self._aspiration_tracker.on_zone_unload()
        self.trait_tracker.on_zone_unload()
        if self.Buffs is not None:
            self.Buffs.on_zone_unload()
        if game_services.service_manager.is_traveling:
            self.commodity_tracker.remove_statistics_on_travel()
            self.statistic_tracker.remove_statistics_on_travel()
            self.static_commodity_tracker.remove_statistics_on_travel()
            if self.away_action_tracker is not None:
                self.away_action_tracker.stop_current_away_action()

    def on_zone_load(self):
        if self.lod == SimInfoLODLevel.MINIMUM:
            return
        self.startup_sim_location = self._get_startup_location()
        if self.Buffs is not None:
            self.Buffs.on_zone_load()
        if self._aspiration_tracker is not None:
            self._aspiration_tracker.on_zone_load()
        self._career_tracker.on_zone_load()
        if self._bucks_tracker is not None:
            self._bucks_tracker.on_zone_load()
        if self._sickness_tracker is not None and self.has_sickness_tracking():
            self.current_sickness.on_zone_load(self)
        for static_commodity_type in self.INITIAL_STATIC_COMMODITIES:
            self.static_commodity_tracker.add_statistic(static_commodity_type)
        if self.commodity_tracker is not None:
            self.commodity_tracker.on_zone_load()
        self.trait_tracker.on_zone_load()

    def _get_startup_location(self):
        current_zone = services.current_zone()
        if self._transform_on_load is not None and self._level_on_load is not None and (current_zone.id == self._zone_id or current_zone.open_street_id == self._world_id):
            routing_surface = routing.SurfaceIdentifier(current_zone.id, self._level_on_load, routing.SurfaceType(self._surface_id_on_load))
            return sims4.math.Location(self._transform_on_load, routing_surface)

    def on_all_households_and_sim_infos_loaded(self):
        if self.lod == SimInfoLODLevel.MINIMUM:
            return
        if self._bucks_tracker is not None:
            self._bucks_tracker.on_all_households_and_sim_infos_loaded()
        self._pregnancy_tracker.refresh_pregnancy_data()
        if not self.premade_sim_template_id:
            self.update_school_data()

    def update_school_data(self):
        school_data = self.get_school_data()
        if school_data is not None:
            school_data.update_school_data(self)

    def set_relgraph_family_edges(self):
        with genealogy_caching():
            for sim_id in self._genealogy_tracker.get_parent_sim_ids_gen():
                RelgraphService.relgraph_set_edge(self.sim_id, sim_id, SimRelBitFlags.SIMRELBITS_PARENT)
            for sim_id in self._genealogy_tracker.get_children_sim_ids_gen():
                RelgraphService.relgraph_set_edge(self.sim_id, sim_id, SimRelBitFlags.SIMRELBITS_CHILD)
            if self.spouse_sim_id is not None:
                RelgraphService.relgraph_set_edge(self.sim_id, self.spouse_sim_id, SimRelBitFlags.SIMRELBITS_SPOUSE)

    def on_sim_added_to_skewer(self):
        self.Buffs.on_sim_added_to_skewer()
        for stat_inst in self.commodity_tracker:
            if stat_inst.is_skill:
                stat_value = stat_inst.get_value()
                stat_inst.refresh_threshold_callback()
                self._publish_commodity_update(type(stat_inst), stat_value, stat_value)
        if FameTunables.END_FEUD_LOOT is not None:
            feud_target = self.get_feud_target()
            if feud_target is not None and feud_target.household is self.household:
                resolver = DoubleSimResolver(self, feud_target)
                FameTunables.END_FEUD_LOOT.apply_to_resolver(resolver)

    def publish_all_commodities(self):
        for stat_inst in self.commodity_tracker:
            if self.is_npc and not getattr(stat_inst, 'update_client_for_npcs', False):
                pass
            else:
                stat_value = stat_inst.get_value()
                self._publish_commodity_update(type(stat_inst), stat_value, stat_value)

    def _publish_commodity_update(self, stat_type, old_value, new_value):
        stat_type.send_commodity_update_message(self, old_value, new_value)

    def _publish_statistic_update(self, stat_type, old_value, new_value):
        if not self.is_npc:
            services.get_event_manager().process_event(test_events.TestEvent.StatValueUpdate, sim_info=self, statistic=stat_type, custom_keys=(stat_type,))

    def update_spouse_sim_id(self, spouse_sim_id):
        mgr = services.sim_info_manager()
        if spouse_sim_id is not None and self._relationship_tracker.spouse_sim_id is not None and self._relationship_tracker.spouse_sim_id != spouse_sim_id:
            logger.error('Naughty! {} already has a spouse but being assigned another one. Original: {} (id: {}). New: {} (id: {}).', self, mgr.get(self._relationship_tracker.spouse_sim_id), self._relationship_tracker.spouse_sim_id, mgr.get(spouse_sim_id), spouse_sim_id)
            return
        ex_spouse_id = self._relationship_tracker.spouse_sim_id
        self._relationship_tracker.spouse_sim_id = spouse_sim_id
        if spouse_sim_id is None:
            RelgraphService.relgraph_set_marriage(self.sim_id, ex_spouse_id, False)
        else:
            RelgraphService.relgraph_set_marriage(self.sim_id, spouse_sim_id, True)
        services.get_event_manager().process_event(test_events.TestEvent.SpouseEvent, sim_info=self)

    def get_significant_other_sim_info(self):
        spouse_sim_info = self.get_spouse_sim_info()
        if spouse_sim_info is not None:
            return spouse_sim_info
        for rel in self._relationship_tracker:
            for bit in RelationshipGlobalTuning.SIGNIFICANT_OTHER_RELATIONSHIP_BITS:
                if rel.has_bit(self.sim_id, bit):
                    return rel.get_other_sim_info(self.sim_id)

    def get_fiance_sim_info(self):
        bit = RelationshipGlobalTuning.ENGAGEMENT_RELATIONSHIP_BIT
        for rel in self._relationship_tracker:
            if rel.has_bit(self.sim_id, bit):
                return rel.get_other_sim_info(self.sim_id)

    @property
    def spouse_sim_id(self):
        return self._relationship_tracker.spouse_sim_id

    def get_spouse_sim_info(self):
        signficant_other_id = self.spouse_sim_id
        if signficant_other_id:
            sim_info_manager = services.sim_info_manager()
            if sim_info_manager is not None:
                significant_other = sim_info_manager.get(signficant_other_id)
                if significant_other is not None:
                    return significant_other

    def get_feud_target(self):
        if RelationshipGlobalTuning.FEUD_TARGET is None:
            return
        for rel in self._relationship_tracker:
            if rel.has_bit(self.sim_id, RelationshipGlobalTuning.FEUD_TARGET):
                return rel.get_other_sim_info(self.sim_id)

    def get_gender_preference(self, gender):
        return self.get_statistic(GlobalGenderPreferenceTuning.GENDER_PREFERENCE[gender])

    def get_gender_preferences_gen(self):
        for (gender, gender_preference_statistic) in GlobalGenderPreferenceTuning.GENDER_PREFERENCE.items():
            yield (gender, self.get_statistic(gender_preference_statistic))

    def has_gender_prefernce_been_set(self):
        return any(stat.get_value() > 0 for (_, stat) in self.get_gender_preferences_gen())

    def set_default_data(self):
        if self._sim_creation_path == serialization.SimData.SIMCREATION_NONE:
            if self._fix_relationships:
                self.set_default_relationships(reciprocal=True, from_load=True)
                self._fix_relationships = False
            return
        self.set_default_relationships(reciprocal=True, from_load=True)
        if self._sim_creation_path != serialization.SimData.SIMCREATION_PRE_MADE:
            self.premade_sim_template_id = 0
        self.creation_source = SimInfoCreationSource.get_creation_source_from_creation_path(self._sim_creation_path)
        if self.creation_source.is_creation_source(SimInfoCreationSource.GALLERY):
            for commodity in list(self.commodity_tracker):
                if commodity.is_skill:
                    pass
                elif not commodity.core:
                    pass
                elif isinstance(commodity, ConsumableComponent.FAT_COMMODITY):
                    pass
                elif isinstance(commodity, ConsumableComponent.FIT_COMMODITY):
                    pass
                elif not commodity.set_to_auto_satisfy_value():
                    commodity.set_value(commodity.get_initial_value())
        self._sim_creation_path = serialization.SimData.SIMCREATION_NONE

    def set_default_relationships(self, reciprocal=False, update_romance=True, from_load=False, default_track_overrides=None):
        if self.household is None:
            return
        sim_id = self.id
        relationship_tracker = self.relationship_tracker

        def add_known_traits(sim_info, family_member):
            trait_tracker = family_member.trait_tracker
            for house_member_trait in trait_tracker.personality_traits:
                sim_info.relationship_tracker.add_known_trait(house_member_trait, family_member.id, notify_client=False)

        for house_member in itertools.chain(self.household.sim_info_gen(), self._genealogy_tracker.get_parent_sim_infos_gen()):
            if house_member is self:
                pass
            else:
                house_member_id = house_member.id
                if self.is_pet == house_member.is_pet:
                    test_track = RelationshipGlobalTuning.REL_INSPECTOR_TRACK
                else:
                    test_track = RelationshipGlobalTuning.DEFAULT_PET_TO_SIM_TRACK
                track = relationship_tracker.get_relationship_track(house_member_id, track=test_track, add=False)
                if track is not None:
                    if reciprocal:
                        pass
                    else:
                        return
                family_member = house_member.add_family_link(self, from_load=from_load)
                relationship_tracker.set_default_tracks(house_member, update_romance=update_romance, family_member=family_member, default_track_overrides=default_track_overrides)
                add_known_traits(self, house_member)
                relationship_tracker.add_knows_career(house_member.id, notify_client=False)
                relationship_tracker.send_relationship_info(house_member_id)
                if reciprocal:
                    self.add_family_link(house_member, from_load=from_load)
                    house_member.relationship_tracker.set_default_tracks(self, update_romance=update_romance, family_member=family_member, bits_only=True)
                    add_known_traits(house_member, self)
                    house_member.relationship_tracker.add_knows_career(sim_id, notify_client=False)
                    house_member.relationship_tracker.send_relationship_info(sim_id)

    def add_family_link(self, target_sim_info, from_load=False):
        bit = self.genealogy.get_family_relationship_bit(target_sim_info.id)
        if bit is None:
            return False
        if target_sim_info.relationship_tracker.has_bit(self.id, bit):
            return True
        target_sim_info.relationship_tracker.add_relationship_bit(self.id, bit, from_load=from_load)
        return True

    def add_parent_relations(self, parent_a, parent_b):
        parent_a_relation = FamilyRelationshipIndex.MOTHER if parent_a.is_female else FamilyRelationshipIndex.FATHER
        self.set_and_propagate_family_relation(parent_a_relation, parent_a)
        if parent_b is not None and parent_a is not parent_b:
            parent_b_relation = FamilyRelationshipIndex.MOTHER if parent_a_relation == FamilyRelationshipIndex.FATHER else FamilyRelationshipIndex.FATHER
            self.set_and_propagate_family_relation(parent_b_relation, parent_b)

    def debug_apply_away_action(self, away_action):
        self._away_action_tracker.create_and_apply_away_action(away_action)

    def debug_apply_default_away_action(self):
        self._away_action_tracker.reset_to_default_away_action()

    def get_default_away_action(self, on_travel_away=False):
        is_instance = self.is_instanced(allow_hidden_flags=ALL_HIDDEN_REASONS) and not on_travel_away
        highest_advertising_value = None
        highest_advertising_away_action = None
        if services.hidden_sim_service().default_away_action(self.id) is not None:
            return services.hidden_sim_service().default_away_action(self.id)
        if is_instance or services.daycare_service().is_sim_info_at_daycare(self):
            return services.daycare_service().default_away_action(self)
        for (commodity, away_action) in SimInfo.DEFAULT_AWAY_ACTION.items():
            if is_instance and not away_action.available_when_instanced:
                pass
            else:
                commodity_instance = self.get_statistic(commodity, add=False)
                if commodity_instance is None:
                    pass
                elif not away_action.test(sim_info=self, target=None):
                    pass
                else:
                    advertising_value = commodity_instance.autonomous_desire
                    if not highest_advertising_value is None:
                        if highest_advertising_value < advertising_value:
                            highest_advertising_value = advertising_value
                            highest_advertising_away_action = away_action
                    highest_advertising_value = advertising_value
                    highest_advertising_away_action = away_action
        return highest_advertising_away_action

    def debug_get_current_situations_string(self):
        current_situations = ''
        sit_man = services.get_zone_situation_manager()
        if sit_man is not None:
            sim = self.get_sim_instance()
            if sim is not None:
                current_situations = ','.join(str(sit) for sit in sit_man.get_situations_sim_is_in(sim))
        return current_situations

    def send_travel_switch_to_zone_op(self, zone_id=DEFAULT):
        if zone_id is DEFAULT:
            zone_id = self.zone_id
            world_id = self.world_id
        else:
            world_id = services.get_persistence_service().get_world_id_from_zone(zone_id)
        if zone_id == 0:
            return
        op = distributor.ops.TravelSwitchToZone((self.id, self.household_id, zone_id, world_id))
        distributor.ops.record(self, op)

    def flush_to_client_on_teardown(self):
        buff_component = self.Buffs
        if buff_component is not None:
            buff_component.on_sim_removed(immediate=True)

    def get_culling_immunity_reasons(self):
        reasons = []
        if self.is_player_sim:
            reasons.append(CullingReasons.PLAYER)
        immune_to_culling = any(trait.culling_behavior.is_immune_to_culling() for trait in self.trait_tracker)
        if immune_to_culling:
            reasons.append(CullingReasons.TRAIT_IMMUNE)
        if self.is_instanced(allow_hidden_flags=ALL_HIDDEN_REASONS):
            reasons.append(CullingReasons.INSTANCED)
        if self.is_in_travel_group():
            reasons.append(CullingReasons.IN_TRAVEL_GROUP)
        return reasons

    def remove_permanently(self, household=None):
        if household is None:
            household = self.household
        if gsi_handlers.sim_info_lifetime_handlers.archiver.enabled:
            gsi_handlers.sim_info_lifetime_handlers.archive_sim_info_event(self, 'remove sim info')
        household.remove_sim_info(self, destroy_if_empty_household=True)
        services.sim_info_manager().remove_permanently(self)
        services.get_persistence_service().del_sim_proto_buff(self.id)

    def log_sim_info(self, logger_func, additional_msg=None):
        sim_info_strings = []
        if additional_msg is not None:
            sim_info_strings.append(additional_msg)
        sim_info_strings.append('Sim info for {}'.format(self))
        sim = self.get_sim_instance(allow_hidden_flags=ALL_HIDDEN_REASONS)
        if sim is not None:
            sim_info_strings.append('Simulation state: {}'.format(sim._simulation_state))
            sim_info_strings.append('Interaction queue:')
            for interaction in sim.queue:
                sim_info_strings.append('    {}'.format(interaction))
        else:
            sim_info_strings.append('Simulation state: UNINSTANTIATED')
        sim_info_strings.append('Traits:')
        for trait in self.trait_tracker:
            sim_info_strings.append('    {}'.format(trait))
        sim_info_strings.append('Buffs:')
        for buff in self.Buffs:
            sim_info_strings.append('    {}'.format(buff))
        sim_info_strings.append('Death Type = {}'.format(self.death_type))
        logger_func('\n'.join(sim_info_strings))

    def is_valid_statistic_to_remove(self, statistic):
        if statistic in self.get_initial_commodities():
            return False
        if statistic is ConsumableComponent.FAT_COMMODITY:
            return False
        if statistic is ConsumableComponent.FIT_COMMODITY:
            return False
        for init_stat in self.INITIAL_STATISTICS:
            if not init_stat.tests is None:
                if init_stat.tests.run_tests(self.get_resolver()):
                    return False
            return False
        return True

    def discourage_route_to_join_social_group(self):
        if any(buff.discourage_route_to_join_social_group for buff in self.Buffs):
            return True
        return False

    def get_bucks_tracker(self, add_if_none=False):
        if add_if_none:
            self._bucks_tracker = SimInfoBucksTracker(self)
        return self._bucks_tracker

    def transfer_to_hidden_household(self):
        household = services.household_manager().create_household(self.account)
        household.set_to_hidden()
        household.add_sim_info(self)
        self.assign_to_household(household)
        return household

def save_active_household_command_start():
    global SAVE_ACTIVE_HOUSEHOLD_COMMAND
    SAVE_ACTIVE_HOUSEHOLD_COMMAND = True

def save_active_household_command_stop():
    global SAVE_ACTIVE_HOUSEHOLD_COMMAND
    SAVE_ACTIVE_HOUSEHOLD_COMMAND = False

class AccountConnection(enum.Int, export=False):
    SAME_LOT = 1
    DIFFERENT_LOT = 2
    OFFLINE = 3
