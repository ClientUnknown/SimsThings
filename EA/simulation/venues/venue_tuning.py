from _collections import defaultdictimport randomfrom buffs.tunable import TunableBuffReferencefrom clubs.club_enums import ClubHangoutSettingfrom event_testing.resolver import SingleSimResolverfrom objects.doors.door_enums import VenueFrontdoorRequirementfrom scheduler import SituationWeeklySchedule, WeeklySchedulefrom sims.sim_info_types import Speciesfrom sims4.localization import TunableLocalizedString, TunableLocalizedStringFactory, TunableLocalizedStringVariantfrom sims4.tuning.geometric import TunableCurvefrom sims4.tuning.instances import HashedTunedInstanceMetaclassfrom sims4.tuning.tunable import Tunable, TunableList, TunableTuple, TunableResourceKey, TunableReference, AutoFactoryInit, HasTunableSingletonFactory, TunableVariant, OptionalTunable, TunableEnumEntry, TunableEnumFlags, TunableRange, TunableMappingfrom sims4.tuning.tunable_base import ExportModes, GroupNamesfrom sims4.utils import classpropertyfrom situations.situation import Situationfrom situations.situation_guest_list import SituationGuestList, SituationInvitationPurpose, SituationGuestInfofrom situations.situation_types import GreetedStatusfrom venues.npc_summoning import ResidentialLotArrivalBehavior, CreateAndAddToSituation, AddToBackgroundSituation, NotfifyZoneDirectorfrom venues.venue_object_test import TunableVenueObjectWithPairimport date_and_timeimport enumimport servicesimport sims4.logimport sims4.resourcesimport sims4.tuningimport tagimport venues.venue_constantsimport zone_directorlogger = sims4.log.Logger('Venues')
class ResidentialZoneFixupForNPC(HasTunableSingletonFactory, AutoFactoryInit):
    FACTORY_TUNABLES = {'description': '\n            Specify what to do with a non resident NPC on a residential lot\n            when the zone has to be fixed up on load. \n            This fix up will occur if sim time or the\n            active household has changed since the zone was last saved.\n            ', 'player_lot_greeted': CreateAndAddToSituation.TunableFactory(), 'npc_lot_greeted': CreateAndAddToSituation.TunableFactory(), 'npc_lot_ungreeted': CreateAndAddToSituation.TunableFactory()}

    def __call__(self, npc_infos, purpose=None):
        situation_manager = services.get_zone_situation_manager()
        is_active_household_residence = False
        active_household = services.active_household()
        if active_household is not None:
            is_active_household_residence = active_household.considers_current_zone_its_residence()
        for sim_info in npc_infos:
            npc = sim_info.get_sim_instance()
            if npc is None:
                pass
            else:
                greeted_status = situation_manager.get_npc_greeted_status_during_zone_fixup(sim_info)
                if is_active_household_residence:
                    if greeted_status == GreetedStatus.GREETED:
                        logger.debug('Player lot greeted {} during zone fixup', sim_info, owner='sscholl')
                        self.player_lot_greeted((sim_info,))
                        if greeted_status == GreetedStatus.WAITING_TO_BE_GREETED:
                            logger.debug('NPC lot waiting to be greeted {} during zone fixup', sim_info, owner='sscholl')
                            self.npc_lot_ungreeted((sim_info,))
                        elif greeted_status == GreetedStatus.GREETED:
                            logger.debug('NPC lot greeted {} during zone fixup', sim_info, owner='sscholl')
                            self.npc_lot_greeted((sim_info,))
                        else:
                            logger.debug('No option for {} during zone fixup', sim_info, owner='sscholl')
                elif greeted_status == GreetedStatus.WAITING_TO_BE_GREETED:
                    logger.debug('NPC lot waiting to be greeted {} during zone fixup', sim_info, owner='sscholl')
                    self.npc_lot_ungreeted((sim_info,))
                elif greeted_status == GreetedStatus.GREETED:
                    logger.debug('NPC lot greeted {} during zone fixup', sim_info, owner='sscholl')
                    self.npc_lot_greeted((sim_info,))
                else:
                    logger.debug('No option for {} during zone fixup', sim_info, owner='sscholl')

class ResidentialTravelDisplayName(HasTunableSingletonFactory, AutoFactoryInit):
    FACTORY_TUNABLES = {'description': '\n        Specify the contextual string for when a user clicks to travel to an\n        adjacent lot in the street.\n        ', 'ring_doorbell_name': TunableLocalizedStringFactory(description='\n            The interaction name for when the actor doesn\'t know any Sims that live on the\n            destination lot.\n            \n            Tokens: 0:ActorSim\n            Example: "Ring Doorbell"\n            '), 'visit_sim_name': TunableLocalizedStringFactory(description='\n            The interaction name for when the actor knows exactly one Sim that lives on the\n            destination lot.\n            \n            Tokens: 0:ActorSim, 1:Sim known\n            Example: "Visit {1.SimName}"\n            '), 'visit_household_name': TunableLocalizedStringFactory(description='\n            The interaction name for when the actor knows more than one Sim\n            that lives on the destination lot, or the Sim they know is not at\n            home.\n            \n            Tokens: 0:ActorSim, 1:Household Name\n            Example: "Visit The {1.String} Household"\n            '), 'visit_the_household_plural_name': TunableLocalizedStringFactory(description='\n            The interaction name for when the actor knows more than one Sim\n            that lives on the destination lot, or the Sim they know is not at\n            home, and everyone who lives there has the same household name as\n            their last name.\n            \n            Tokens: 0:ActorSim, 1:Household Name\n            Example: "Visit The {1.String|enHouseholdNamePlural}"\n            '), 'no_one_home_encapsulation': TunableLocalizedStringFactory(description='\n            The string that gets appended on the end of our interaction string\n            if none of the household Sims at the destination lot are home.\n            \n            Tokens: 0:Interaction Name\n            Example: "{0.String} (No One At Home)"\n            '), 'go_here_name': TunableLocalizedStringFactory(description='\n            The interaction name for when no household lives on the destination\n            lot.\n            \n            Tokens: 0:ActorSim\n            Example: "Go Here"\n            '), 'go_home_name': TunableLocalizedStringFactory(description='\n            The interaction name for when the actor\'s home lot is the\n            destination lot.\n            \n            Tokens: 0:ActorSim\n            Example: "Go Home"\n            ')}

    def __call__(self, target, context):
        sim = context.sim
        lot_id = context.pick.lot_id
        if lot_id is None:
            return
        persistence_service = services.get_persistence_service()
        to_zone_id = persistence_service.resolve_lot_id_into_zone_id(lot_id)
        if to_zone_id is None:
            return
        if sim.sim_info.vacation_or_home_zone_id == to_zone_id:
            return self.go_home_name(sim)
        household_id = None
        lot_owner_info = persistence_service.get_lot_proto_buff(lot_id)
        if lot_owner_info is not None:
            for household in lot_owner_info.lot_owner:
                household_id = household.household_id
                break
        if household_id:
            household = services.household_manager().get(household_id)
        else:
            household = None
        if household is None:
            return self.go_here_name(sim)
        sim_infos_known = False
        sim_infos_known_at_home = []
        sim_infos_at_home = False
        same_last_name = True
        for sim_info in household.sim_info_gen():
            if sim_info.relationship_tracker.get_all_bits(sim.id):
                sim_infos_known = True
                if sim_info.zone_id == to_zone_id:
                    sim_infos_known_at_home.append(sim_info)
            elif sim_info.zone_id == to_zone_id:
                sim_infos_at_home = True
            if not sim_info.last_name == household.name:
                same_last_name = False
        if not sim_infos_known:
            travel_name = self.ring_doorbell_name(sim)
        elif len(sim_infos_known_at_home) == 1:
            return self.visit_sim_name(sim, sim_infos_known_at_home[0])
        else:
            if same_last_name:
                travel_name = self.visit_the_household_plural_name(sim, household.name)
            else:
                travel_name = self.visit_household_name(sim, household.name)
            if not sim_infos_at_home:
                return self.no_one_home_encapsulation(travel_name)
            else:
                return travel_name
        if not sim_infos_at_home:
            return self.no_one_home_encapsulation(travel_name)
        else:
            return travel_name

class VenueTypes(enum.Int):
    STANDARD = 0
    RESIDENTIAL = 1
    RENTAL = 2
    RESTAURANT = 3
    RETAIL = 4
    VET_CLINIC = 5

class VenueFlags(enum.IntFlags):
    NONE = 0
    WATER_LOT_RECOMMENDED = 1

class Venue(metaclass=HashedTunedInstanceMetaclass, manager=services.get_instance_manager(sims4.resources.Types.VENUE)):
    INSTANCE_TUNABLES = {'display_name': TunableLocalizedString(description='\n            Name that will be displayed for the venue\n            ', export_modes=ExportModes.All), 'display_name_incomplete': TunableLocalizedString(description='\n            Name that will be displayed for the incomplete venue\n            ', allow_none=True, export_modes=ExportModes.All), 'venue_description': TunableLocalizedString(description='\n            Description of Venue that will be displayed\n            ', export_modes=ExportModes.All), 'venue_icon': TunableResourceKey(description='\n            Venue Icon for UI\n            ', resource_types=sims4.resources.CompoundTypes.IMAGE, export_modes=ExportModes.All), 'venue_thumbnail': TunableResourceKey(description='\n            Image of Venue that will be displayed', resource_types=sims4.resources.CompoundTypes.IMAGE, allow_none=True, export_modes=ExportModes.All), 'venue_buffs': TunableList(description='\n            A list of buffs that are added on Sims while they are instanced in\n            this venue.\n            ', tunable=TunableBuffReference(description='\n                A buff that exists on Sims while they are instanced in this\n                venue.\n                ', pack_safe=True)), 'venue_type': TunableEnumEntry(description="\n            The venue's functional type. Used to distinguish venues that function differently.\n            ", tunable_type=VenueTypes, default=VenueTypes.STANDARD, export_modes=ExportModes.All), 'venue_flags': TunableEnumFlags(description='\n            Venue flags used to mark a venue with specific properties.\n            ', enum_type=VenueFlags, allow_no_flags=True, default=VenueFlags.NONE, export_modes=ExportModes.All), 'visible_in_map_view': Tunable(description='\n            If checked, the venue icon will be visible in the map view.\n            ', tunable_type=bool, default=False, export_modes=ExportModes.All), 'allow_game_triggered_events': Tunable(description='\n            Whether this venue can have game triggered events. ex for careers\n            ', tunable_type=bool, default=False), 'background_event_schedule': SituationWeeklySchedule.TunableFactory(description='\n            The Background Events that run on this venue. They run underneath\n            any user facing Situations and there can only be one at a time. The\n            schedule times and durations are windows in which background events\n            can start.\n            '), 'special_event_schedule': SituationWeeklySchedule.TunableFactory(description='\n            The Special Events that run on this venue. These run on top of\n            Background Events. We run only one user facing event at a time, so\n            if the player started something then this may run in the\n            background, otherwise the player will be invited to join in on this\n            Venue Special Event.\n            '), 'required_objects': TunableList(description='\n            A list of objects that are required to be on a lot before\n            that lot can be labeled as this venue.\n            ', tunable=TunableVenueObjectWithPair(description="\n                Specify object tag(s) that must be on this venue. Allows you to\n                group objects, i.e. weight bench, treadmill, and basketball\n                goals are tagged as 'exercise objects.'\n                \n                This is not the same as automatic objects tuning. \n                Please read comments for both the fields.\n                "), export_modes=ExportModes.All), 'npc_summoning_behavior': TunableMapping(description='\n            Whenever an NPC is summoned to a lot by the player, determine\n            which action to take based on the summoning purpose. The purpose\n            is a dynamic enum: venues.venue_constants.NPCSummoningPurpose.\n            \n            The action will generally involve either adding a sim to an existing\n            situation or creating a situation then adding them to it.\n            \n            \\depot\\Sims4Projects\\Docs\\Design\\Open Streets\\Open Street Invite Matrix.xlsx\n            \n            residential: This is behavior pushed on the NPC if this venue was a residential lot.\n            create_situation: Place the NPC in the specified situation/job pair.\n            add_to_background_situation: Add the NPC the currently running background \n            situation in the venue.\n            notify_zone_director: notifies the current zones zone director that\n            a sim needs to be spawned and lets the zone director handle it.\n            ', key_type=sims4.tuning.tunable.TunableEnumEntry(description='\n                The different reasons that we have for summoning an NPC. Every\n                time an NPC is summoned they are given one of these reasons\n                as a key to how we want to handle that Sim.\n                ', tunable_type=venues.venue_constants.NPCSummoningPurpose, default=venues.venue_constants.NPCSummoningPurpose.DEFAULT), value_type=TunableMapping(description="\n                A mapping between species and the action we want to take.  If\n                a species doesn't have specific tuning then the Human species\n                tuning will be used instead.\n                ", key_type=TunableEnumEntry(description='\n                    The species that we want to use to perform this behavior.\n                    ', tunable_type=Species, default=Species.HUMAN, invalid_enums=(Species.INVALID,)), value_type=TunableVariant(description='\n                    The behavior that we want to accomplish based on the summoning\n                    type.\n                    ', locked_args={'disabled': None}, residential=ResidentialLotArrivalBehavior.TunableFactory(), create_situation=CreateAndAddToSituation.TunableFactory(), add_to_background_situation=AddToBackgroundSituation.TunableFactory(), notify_zone_director=NotfifyZoneDirector.TunableFactory(), default='disabled')), tuning_group=GroupNames.TRIGGERS), 'player_requires_visitation_rights': OptionalTunable(description='\n            If enabled, then lots of this venue type will require player Sims that\n            are not on their home lot to go through the process of being greeted\n            before they are given full rights to using the lot.\n            ', tunable=TunableTuple(ungreeted=Situation.TunableReference(description='\n                    The situation to create for ungreeted player sims on this lot.\n                    ', display_name='Player Ungreeted Situation'), greeted=Situation.TunableReference(description='\n                    The situation to create for greeted player sims on this lot.\n                    ', display_name='Player Greeted Situation'))), 'zone_fixup': TunableVariant(description='\n            Specify what to do with a non resident NPC\n            when the zone has to be fixed up on load. \n            This fix up will occur if sim time or the\n            active household has changed since the zone was last saved.\n            ', residential=ResidentialZoneFixupForNPC.TunableFactory(), create_situation=CreateAndAddToSituation.TunableFactory(), add_to_background_situation=AddToBackgroundSituation.TunableFactory(), default='residential', tuning_group=GroupNames.SPECIAL_CASES), 'travel_interaction_name': TunableVariant(description='\n            Specify what name a travel interaction gets when this Venue is an\n            adjacent lot.\n            ', visit_residential=ResidentialTravelDisplayName.TunableFactory(description='\n                The interaction name for when the destination lot is a\n                residence.\n                '), visit_venue=TunableLocalizedStringFactory(description='\n                The interaction name for when the destination lot is a\n                commercial venue.\n                Tokens: 0:ActorSim\n                Example: "Visit The Bar"\n                '), tuning_group=GroupNames.SPECIAL_CASES), 'travel_with_interaction_name': TunableVariant(description='\n            Specify what name a travel interaction gets when this Venue is an\n            adjacent lot.\n            ', visit_residential=ResidentialTravelDisplayName.TunableFactory(description='\n                The interaction name for when the destination lot is a\n                residence and the actor Sim is traveling with someone.\n                '), visit_venue=TunableLocalizedStringFactory(description='\n                The interaction name for when the destination lot is a\n                commercial venue and the actor is traveling with someone.\n                Tokens: 0:ActorSim\n                Example: "Visit The Bar With..."\n                '), tuning_group=GroupNames.SPECIAL_CASES), 'venue_requires_front_door': TunableEnumEntry(description='\n            Set to NEVER if this venue should never run the front door\n            generation code. Set to ALWAYS if this venue should always \n            run the front door generation code (like Residential lots).\n            Set to OWNED_OR_RENTED if it should only run if the lot is\n            owned by a household or rented by one. \n            If it runs, venue will have the ring doorbell interaction and \n            additional behavior like backup logic for broom teleports.\n            ', tunable_type=VenueFrontdoorRequirement, default=VenueFrontdoorRequirement.NEVER), 'automatic_objects': TunableList(description='\n            A list of objects that is required to exist on this venue (e.g. the\n            mailbox). If any of these objects are missing from this venue, they\n            will be auto-placed on zone load.', tunable=TunableTuple(description="\n                An item that is required to be present on this venue. The object's tag \n                will be used to determine if any similar objects are present. If no \n                similar objects are present, then the object's actual definition is used to \n                create an object of this type.\n                \n                This is not the same as required objects tuning. Please read comments \n                for both the fields.\n                \n                E.g. To require a mailbox to be present on a lot, tune a hypothetical basicMailbox \n                here. The code will not trigger as long as a basicMailbox, fancyMailbox, or \n                cheapMailbox are present on the lot. If none of them are, then a basicMailbox \n                will be automatically created.\n                ", default_value=TunableReference(description='\n                    The default object to use if no suitably tagged object is\n                    present on the lot.\n                    ', manager=services.definition_manager()), tag=TunableEnumEntry(description='\n                    The tag to search for\n                    ', tunable_type=tag.Tag, default=tag.Tag.INVALID))), 'hide_from_buildbuy_ui': Tunable(description='\n            If True, this venue type will not be available in the venue picker in\n            build/buy.\n            ', tunable_type=bool, default=False, export_modes=ExportModes.All), 'exclude_owned_objects_in_lot_value_calculation': Tunable(description='\n            Whether or not owned objects should be excluded when computing the lot\n            value for this venue type. \n            Example: Residential should include the value but Rentable should not.\n            ', tunable_type=bool, default=False, export_modes=ExportModes.All), 'gallery_upload_venue_type': TunableReference(description="\n            The venue type that this venue gets uploaded as to the gallery. In\n            each region's tuning, make sure the upload type is downloaded as\n            the appropriate venue type. \n            Example: Rentable venues should be uploaded as Residential.\n            ", manager=services.venue_manager(), allow_none=True, export_modes=ExportModes.All), 'allows_fire': Tunable(description='\n            If True a fire can happen on this venue, \n            otherwise fires will not spawn on this venue.\n            ', tunable_type=bool, default=False), 'allow_rolestate_routing_on_navmesh': Tunable(description='\n            Allow all RoleStates routing permission on lot navmeshes of this\n            venue type. This is particularly useful for outdoor venue types\n            (lots with no walls), where it is awkward to have to "invite a sim\n            in" before they may route on the lot, be called over, etc.\n            \n            This tunable overrides the "Allow Npc Routing On Active Lot"\n            tunable of individual RoleStates.\n            ', tunable_type=bool, default=False), 'category_tags': TunableList(description='\n            A list of tags to associate with this venue type.\n            ', tunable=TunableEnumEntry(description='\n                A category tag for this venue.\n                ', tunable_type=tag.Tag, default=tag.Tag.INVALID), export_modes=ExportModes.All), 'zone_director': zone_director.ZoneDirectorBase.TunableReference(description='\n            The ZoneDirector type to request for this Venue Type. This will be the\n            default type for this Venue Type. It may be overridden by a system such\n            as Active Careers (e.g. your house is a crime scene now).\n            '), 'new_venue_type_dialog_description': TunableLocalizedString(description="\n            When the venue type is 'new' to the player, the Venue Celebration\n            dialog is shown.  This is the localized string ID for the description\n            text.\n            ", allow_none=True, export_modes=ExportModes.All), 'new_venue_type_dialog_image': TunableResourceKey(description="\n            When the venue type is 'new' to the player, the Venue Celebration\n            dialog is shown.  This is the main image ID shown in the dialog.\n            ", resource_types=sims4.resources.CompoundTypes.IMAGE, allow_none=True, export_modes=ExportModes.All), 'new_venue_type_dialog_example_item': TunableResourceKey(description="\n            When the venue type is 'new' to the player, the Venue Celebration\n            dialog is shown.  This is the example lot ID to apply should the\n            user respond positively to the dialog.\n            ", resource_types=(sims4.resources.Types.TRAY_METADATA,), allow_none=True, export_modes=ExportModes.All), 'allow_super_speed_three': Tunable(description='\n            If set to True, game is allowed to get into super speed 3.\n            ', tunable_type=bool, default=True), 'allowed_for_clubs': Tunable(description='\n            If checked, this Venue can be associated with Clubs and will be\n            available for Club Gatherings.\n            ', tunable_type=bool, default=False, tuning_group=GroupNames.CLUBS, export_modes=ExportModes.All), 'club_gathering_text': OptionalTunable(description="\n            Specify text included in an NPC's invite to join a gathering at this\n            venue. This must be enabled if allowed_for_clubs is checked. If\n            allowed_for_clubs is unchecked, setting this field has no effect.\n            ", tunable=TunableLocalizedStringVariant(), tuning_group=GroupNames.CLUBS), 'club_gathering_auto_spawn_schedule': OptionalTunable(description='\n            If enabled, this schedule will specify the times when we will attempt to\n            spawn associated Club Gatherings on this venue.\n            ', tunable=WeeklySchedule.TunableFactory(description='\n                This schedule will specify the times when we will attempt to spawn\n                associated Club Gatherings on this venue.\n                ', schedule_entry_data={'tuning_name': 'club_gathering_data', 'tuning_type': TunableTuple(description='\n                        Specify gathering behavior at these days and time.\n                        ', maximum_club_gatherings=TunableRange(description='\n                            Define the maximum number of gatherings that can be auto-\n                            started.\n                            ', tunable_type=int, minimum=0, default=3), ideal_club_gatherings=TunableCurve(description='\n                            Define the ideal number of gatherings that should be\n                            auto-started.\n                            ', x_axis_name='clubs_using_this_as_preferred_venue', y_axis_name='ideal_number_of_club_gatherings'))}), tuning_group=GroupNames.CLUBS), 'whim_set': OptionalTunable(description='\n            If enabled then this venue type will offer a whim set to the Sim\n            when it is the active lot.\n            ', tunable=TunableReference(description='\n                A whim set that is active when this venue is the active lot.\n                ', manager=services.get_instance_manager(sims4.resources.Types.ASPIRATION), class_restrictions=('ObjectivelessWhimSet',))), 'drama_node_events': TunableList(description='\n            A list of drama nodes that provide special events to the venues\n            that they are a part of.\n            ', tunable=TunableReference(description='\n                A drama node that will contain a special even on a venue.\n                ', manager=services.get_instance_manager(sims4.resources.Types.DRAMA_NODE), class_restrictions=('VenueEventDramaNode',), pack_safe=True)), 'drama_node_events_to_schedule': TunableRange(description='\n            The number of drama node events that will be scheduled if events\n            are specified.\n            ', tunable_type=int, default=1, minimum=1)}

    @classmethod
    def _verify_tuning_callback(cls):
        if cls.special_event_schedule is not None:
            for entry in cls.special_event_schedule.schedule_entries:
                if entry.situation.venue_situation_player_job is None:
                    logger.error('Venue Situation Player Job {} tuned in Situation: {}', entry.situation.venue_situation_player_job, entry.situation)
        if cls.allowed_for_clubs and not cls.club_gathering_text:
            logger.error('Venue {} is marked as allowed_for_clubs but has no club_gathering_text specified.', cls, owner='epanero')

    def __init__(self, **kwargs):
        self._active_background_event_id = None
        self._active_special_event_id = None
        self._background_event_schedule = None
        self._special_event_schedule = None
        self._club_gathering_schedule = None

    def create_zone_director_instance(self):
        return self.zone_director()

    def set_active_event_ids(self, background_event_id=None, special_event_id=None):
        self._active_background_event_id = background_event_id
        self._active_special_event_id = special_event_id

    @property
    def active_background_event_id(self):
        return self._active_background_event_id

    @property
    def active_special_event_id(self):
        return self._active_special_event_id

    def _start_schedule(self, schedule, schedule_callback, *, schedule_immediate):
        if schedule is None:
            return
        schedule_instance = schedule(start_callback=schedule_callback, schedule_immediate=False)
        if schedule_immediate:
            (best_time_span, best_data_list) = schedule_instance.time_until_next_scheduled_event(services.time_service().sim_now, schedule_immediate=True)
            if best_time_span == date_and_time.TimeSpan.ZERO:
                for best_data in best_data_list:
                    schedule_callback(schedule_instance, best_data)
        return schedule_instance

    def schedule_background_events(self, schedule_immediate=True):
        self._background_event_schedule = self._start_schedule(self.background_event_schedule, self._start_background_event, schedule_immediate=schedule_immediate)

    def schedule_special_events(self, schedule_immediate=True):
        self._special_event_schedule = self.special_event_schedule(start_callback=self._try_start_special_event, schedule_immediate=schedule_immediate)

    def schedule_club_gatherings(self, schedule_immediate=False):
        self._club_gathering_schedule = self._start_schedule(self.club_gathering_auto_spawn_schedule, self._try_balance_club_gatherings, schedule_immediate=schedule_immediate)

    def _start_background_event(self, scheduler, alarm_data, extra_data=None):
        entry = alarm_data.entry
        situation = entry.situation
        situation_manager = services.get_zone_situation_manager()
        if self._active_background_event_id is not None and self._active_background_event_id in situation_manager:
            situation_manager.destroy_situation_by_id(self._active_background_event_id)
        situation_id = services.get_zone_situation_manager().create_situation(situation, user_facing=False, spawn_sims_during_zone_spin_up=True)
        self._active_background_event_id = situation_id

    def _try_start_special_event(self, scheduler, alarm_data, extra_data):
        entry = alarm_data.entry
        situation = entry.situation
        situation_manager = services.get_zone_situation_manager()
        if self._active_special_event_id is None:
            client_manager = services.client_manager()
            client = next(iter(client_manager.values()))
            invited_sim = client.active_sim
            active_sim_available = situation.is_situation_available(invited_sim)

            def _start_special_event(dialog):
                guest_list = None
                if dialog.accepted:
                    start_user_facing = True
                    guest_list = SituationGuestList()
                    guest_info = SituationGuestInfo.construct_from_purpose(invited_sim.id, situation.venue_situation_player_job, SituationInvitationPurpose.INVITED)
                    guest_list.add_guest_info(guest_info)
                else:
                    start_user_facing = False
                situation_id = situation_manager.create_situation(situation, guest_list=guest_list, user_facing=start_user_facing)
                self._active_special_event_id = situation_id

            if situation.venue_invitation_message is not None and (situation_manager.is_user_facing_situation_running() or active_sim_available):
                dialog = situation.venue_invitation_message(invited_sim, SingleSimResolver(invited_sim))
                dialog.show_dialog(on_response=_start_special_event, additional_tokens=(situation.display_name, situation.venue_situation_player_job.display_name))
            else:
                situation_id = situation_manager.create_situation(situation, user_facing=False)
                self._active_special_event_id = situation_id

    def _try_balance_club_gatherings(self, scheduler, alarm_data, extra_data=None):
        club_service = services.get_club_service()
        if club_service is None:
            return
        club_gathering_data = alarm_data.entry.club_gathering_data

        def is_club_valid_for_venue(club):
            if club.hangout_setting == ClubHangoutSetting.HANGOUT_VENUE:
                return club.hangout_venue is type(self)
            elif club.hangout_setting == ClubHangoutSetting.HANGOUT_LOT:
                return club.hangout_zone_id == services.current_zone_id()
            return False

        clubs = tuple(club for club in club_service.clubs if is_club_valid_for_venue(club))
        if not clubs:
            return
        ideal_club_gatherings = club_gathering_data.ideal_club_gatherings.get(len(clubs))
        ideal_club_gatherings = int(random.triangular(0, club_gathering_data.maximum_club_gatherings, ideal_club_gatherings))
        lot_household = services.active_lot().get_household()
        for club in clubs:
            if len(club_service.clubs_to_gatherings_map) >= ideal_club_gatherings:
                break
            if club in club_service.clubs_to_gatherings_map:
                pass
            elif not club.is_gathering_auto_spawning_available():
                pass
            elif lot_household is not None and not any(member.household is lot_household for member in club.members):
                pass
            elif not club.is_gathering_auto_start_available():
                pass
            else:
                club_service.start_gathering(club)

    def shut_down(self):
        if self._background_event_schedule is not None:
            self._background_event_schedule.destroy()
        if self._special_event_schedule is not None:
            self._special_event_schedule.destroy()
        situation_manager = services.get_zone_situation_manager()
        if self._active_background_event_id is not None:
            situation_manager.destroy_situation_by_id(self._active_background_event_id)
            self._active_background_event_id = None
        if self._active_special_event_id is not None:
            situation_manager.destroy_situation_by_id(self._active_special_event_id)
            self._active_special_event_id = None

    @classmethod
    def lot_has_required_venue_objects(cls, lot):
        failure_reasons = []
        for required_object_tuning in cls.required_objects:
            object_test = required_object_tuning.object
            object_list = object_test()
            num_objects = len(object_list)
            if num_objects < required_object_tuning.number:
                pass
        failure_message = None
        failure = len(failure_reasons) > 0
        if failure:
            failure_message = ''
            for message in failure_reasons:
                failure_message += message + '\n'
        return (not failure, failure_message)

    def summon_npcs(self, npc_infos, purpose, host_sim_info=None):
        summoned = False
        open_street_director = services.venue_service().get_zone_director().open_street_director
        if open_street_director is not None:
            summoned = open_street_director.summon_npcs(npc_infos, purpose, host_sim_info=host_sim_info)
        if summoned or self.npc_summoning_behavior is None:
            return
        summon_behaviors = self.npc_summoning_behavior.get(purpose)
        if summon_behaviors is None:
            summon_behaviors = self.npc_summoning_behavior.get(venues.venue_constants.NPCSummoningPurpose.DEFAULT)
            if summon_behaviors is None:
                return
        species_sim_info_map = defaultdict(list)
        for sim_info in npc_infos:
            species_sim_info_map[sim_info.species].append(sim_info)
        for (species, sim_infos) in species_sim_info_map.items():
            summon_behavior = summon_behaviors.get(species)
            if summon_behavior is None:
                summon_behavior = summon_behaviors.get(Species.HUMAN)
                if summon_behavior is None:
                    pass
                else:
                    summon_behavior(sim_infos, host_sim_info=host_sim_info)
            else:
                summon_behavior(sim_infos, host_sim_info=host_sim_info)

    @classproperty
    def is_residential(cls):
        return cls.venue_type == VenueTypes.RESIDENTIAL

    @classproperty
    def requires_front_door(cls):
        return cls.venue_requires_front_door != VenueFrontdoorRequirement.NEVER

    @classproperty
    def requires_visitation_rights(cls):
        return cls.player_requires_visitation_rights is not None

    @classproperty
    def player_ungreeted_situation_type(cls):
        if cls.player_requires_visitation_rights is None:
            return
        return cls.player_requires_visitation_rights.ungreeted

    @classproperty
    def player_greeted_situation_type(cls):
        if cls.player_requires_visitation_rights is None:
            return
        return cls.player_requires_visitation_rights.greeted
