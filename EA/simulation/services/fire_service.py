import itertoolsimport randomimport weakreffrom protocolbuffers import Consts_pb2from event_testing.resolver import SingleSimResolverfrom event_testing.results import TestResultfrom event_testing.test_events import TestEventfrom event_testing.tests import TunableTestSetfrom fire.fire_tuning import FireTuningfrom indexed_manager import CallbackTypesfrom interactions.context import InteractionContextfrom interactions.interaction_cancel_compatibility import InteractionCancelCompatibility, InteractionCancelReasonfrom interactions.liability import Liabilityfrom interactions.priority import Priorityfrom interactions.utils.success_chance import SuccessChancefrom objects import systemfrom objects.components.state import TunableStateValueReference, ObjectState, ObjectStateValuefrom objects.fire.fire import Firefrom objects.helpers.user_footprint_helper import UserFootprintHelperfrom plex.plex_enums import PlexBuildingTypefrom postures.transition_sequence import DerailReasonfrom sims import household_managerfrom sims4.callback_utils import CallableListfrom sims4.localization import TunableLocalizedStringFactoryfrom sims4.localization.localization_tunables import LocalizedStringHouseholdNameSelectorfrom sims4.service_manager import Servicefrom sims4.tuning.geometric import TunableVector2from sims4.tuning.tunable import TunableReference, Tunable, TunableRange, TunableInterval, TunableList, TunablePercent, TunableEnumEntryfrom singletons import DEFAULTfrom situations import situation_complexfrom situations.situation import Situationfrom situations.situation_guest_list import SituationGuestList, SituationGuestInfo, SituationInvitationPurposefrom ui.ui_dialog_notification import TunableUiDialogNotificationSnippet, UiDialogNotificationfrom vfx import PlayEffectimport alarmsimport build_buyimport clockimport date_and_timeimport placementimport servicesimport sims4.resourcesimport tagimport terrainlogger = sims4.log.Logger('Fire', default_owner='rfleig')with sims4.reload.protected(globals()):
    fire_enabled = True
class FireImmunityLiability(Liability):
    LIABILITY_TOKEN = 'FireImmunityLiability'

class FireService(Service):
    FIRE_OBJECT_DEF = TunableReference(manager=services.definition_manager())
    FIRE_OBJECT_FIRE_STATE = ObjectState.TunableReference(description='The ObjectState used to track a fire objects progress. Do not Tune.')
    FIRE_OBJECT_EXTINGUISHED_STATE_VALUE = ObjectStateValue.TunableReference(description='The ObjectStateValue a fire object has when the fire has been extinguished or just burnt out. Do Not Tune.')
    FIRE_SPREAD_INTIAL_TIME_IN_SIM_MINUTES = Tunable(description='\n        Initial time in sim minutes to wait when a fire first breaks out on a \n        lot before trying to spread the fire.\n        ', tunable_type=int, default=15)
    FIRE_SPREAD_REPEATING_TIME_IN_SIM_MINUTES = Tunable(description='\n        How long in Sim minutes to wait between each check for whether or\n        not fire should spread.\n        ', tunable_type=int, default=15)
    FIRE_SPREAD_CHANCE = TunableRange(description='\n        A value between 0 - 1 that is how likely fire is to spread once \n        the spread timer goes off.\n        ', minimum=0, maximum=1, tunable_type=float, default=0.9)
    FIRE_STARTED_NOTIFICATION = TunableUiDialogNotificationSnippet(description='\n        The notification that is displayed whenever a fire first breaks out on\n        a lot.\n        ')
    FIRE_REACTION_NOTIFICATION = TunableUiDialogNotificationSnippet(description='\n        The notification that is displayed whenever the first Sim reacts to \n        the fire so that the player can click on the sim and center in on the\n        sim to help find the fire.\n        ')
    FIRE_QUADTREE_RADIUS = Tunable(description="\n        Size of the fire's quadtree footprint used for spatial queries\n        ", tunable_type=float, default=1.0)
    FIRE_RETARDANT_EXTRA_OBJECT_RADIUS = Tunable(description='\n        Extra amount of space to preserve around a fire retardant object where\n        fire cannot spread.\n        ', tunable_type=float, default=0.2)
    MAX_NUM_ATTEMPTS_TO_PLACE_FIRE = Tunable(description='\n        When trying to spread fire, this is the number of times an attempt will\n        be made to find a place to put the new fire down without overlapping\n        before giving up.\n        ', tunable_type=int, default=10)
    FIRE_PLACEMENT_RANGE = TunableInterval(description='\n        A tunable to represent how far from an existing fire object that new\n        fire object can be placed. The value represents multiples of the radius\n        of the fire object.\n        \n        Example a value of 2 means that it is ok to place the new fire object\n        2 * the object radius away from the existing fire location. This is \n        the minimum because anything less will overlap with the existing fire \n        object on placement.\n        ', tunable_type=float, minimum=2, default_lower=2, default_upper=3)
    FLAMMABLE_COMMODITY = TunableReference(description='\n        The commodity used to determin if an object is flammable or not.\n        ', manager=services.get_instance_manager(sims4.resources.Types.STATISTIC))
    FLAMMABLE_COMMODITY_DECAY_PER_FIRE = TunableRange(description='\n        The amount of decay modifier to add to an objects FLAMMABLE_COMMODITY\n        per fire object that is overlapping with it. No negative numbers.\n        ', tunable_type=float, default=5, minimum=0)
    FIRE_SIM_ON_FIRE_AFFORDANCE = TunableReference(description='\n        The affordance that gets pushed onto a Sim when they catch on fire.\n        ', manager=services.get_instance_manager(sims4.resources.Types.INTERACTION))
    FIRE_SIM_ON_FIRE_CHANCE = SuccessChance.TunableFactory(description='\n        The chance that a sim will catch on fire, modified by tested multipliers.\n        ')
    FIRE_CAN_SPREAD_TO_SIM_TESTS = TunableTestSet(description='\n        A tunable set of tests which Sims are required to pass in order for\n        fire to be placed at their location. If the tests fail fire will fail\n        to spread to their location and they will not catch fire as a result.\n        ')
    FIRE_SITUATION = TunableReference(description='\n        A reference to the fire situation to use on Sims that are on a lot\n        with a fire.\n        ', manager=services.get_instance_manager(sims4.resources.Types.SITUATION))
    FIRE_BRIGADE_SITUATION = TunableReference(description='\n        A reference to a fire brigade situation that has a tunable chance of \n        getting spun up when a fire occurs. This summons a volunteer\n        fire brigade that will attempt to put out the fire.\n        ', manager=services.get_instance_manager(sims4.resources.Types.SITUATION))
    FIRE_JOB = TunableReference(description='\n        A reference to the fire job that Sims will have in the fire situation\n        while there is a fire on the lot.\n        ', manager=services.get_instance_manager(sims4.resources.Types.SITUATION_JOB))
    FIRE_PANIC_BUFFS = TunableList(TunableReference(manager=services.get_instance_manager(sims4.resources.Types.BUFF)), description='\n                                       A List of Buffs that indicate a Sim is\n                                       in a panic state because of fire. This\n                                       will be used to limit their behaviors\n                                       while they are aware of a fire on the\n                                       lot.\n                                       ')
    SAVE_LOCK_TOOLTIP = TunableLocalizedStringFactory(description='The tooltip/message to show when the player tries to save the game while a fire situation is happening')
    INTERACTION_UNAVAILABLE_DUE_TO_FIRE_TOOLTIP = TunableLocalizedStringFactory(description='The tooltip to show in the grayed out tooltip when the player tries to interact with things on a lot that has a fire.')
    SPRINKLER_HEAD_OBJECT_DEF = TunableReference(manager=services.definition_manager())
    SPRINKLER_HEAD_SUPPRESSION_RADIUS = Tunable(description='\n        The radius within which a sprinkler head will suppress fires.\n        ', tunable_type=float, default=3)
    SPRINKLER_BOX_OBJECT_TAG = TunableEnumEntry(tunable_type=tag.Tag, default=tag.Tag.INVALID)
    SPRINKLER_FLOOR_OBJECT_TAG = TunableEnumEntry(tunable_type=tag.Tag, default=tag.Tag.INVALID)
    SPRINKLER_FLOOR_SUPPRESSION_RADIUS = Tunable(description='\n        The radius within which a floor sprinkler will suppress fires.\n        ', tunable_type=float, default=1.5)
    FIRE_ALARM_OBJECT_DEF = TunableReference(manager=services.definition_manager())
    FIRE_ALARM_ACTIVE_STATE = TunableStateValueReference(description='\n        The state the fire alarm should be in while active\n        ')
    FIRE_ALARM_DEACTIVATED_STATE = TunableStateValueReference(description='\n        The state the fire alarm should be in while not active\n        ')
    FIRE_SPRINKLER_ACTIVE_STATE = TunableStateValueReference(description='\n        The state the fire sprinkler should be in while active\n        ')
    FIRE_SPRINKLER_DEACTIVATED_STATE = TunableStateValueReference(description='\n        The state the fire sprinkler should be in while not active\n        ')
    SPRINKLER_EFFECT = PlayEffect.TunableFactory()
    SPRINKLER_ACTIVATION_TIME = Tunable(description='\n        Time in sim minutes after a fire starts on a lot before activating the sprinkler system.\n        ', tunable_type=int, default=30)
    SPRINKLER_RUN_TIME = Tunable(description='\n        Time in sim minutes between sprinkler system checks. It will check for new fires,\n        and deactivate if there are no fires left burning.\n        ', tunable_type=int, default=15)
    SPRINKLER_PUDDLE_CHANCE = Tunable(description="\n        Chance for a puddle to appear somewhere in the sprinkler's area of effect.\n        ", tunable_type=int, default=30)
    FIRE_STRENGTH_COMMODITY = TunableReference(description='\n        The commodity that represents the strength of a fire.\n        ', manager=services.get_instance_manager(sims4.resources.Types.STATISTIC))
    FIRE_BEEN_EXTINGUISHED_COMMODITY = TunableReference(description='\n        A static commodity used to mark a fire object as having been\n        extinguished. \n        \n        If this commodity is present on the object when it burns\n        out then it will be removed from the fire_object_quadtree so that fire\n        can spark back up there.\n        ', manager=services.get_instance_manager(sims4.resources.Types.STATISTIC))
    FIRE_STRENGTH_COMMODITY_SUPRESSION_DECAY = TunableRange(description='\n        The amount of decay modifier to add to an objects FIRE_STRENGTH_COMMODITY\n        when it is being supresssed by a sprinkler. No negative numbers.\n        ', tunable_type=float, default=15, minimum=0)
    FIRE_ALARM_CYCLE_TIME = Tunable(description='\n        Time in sim minutes after a fire starts on a lot before fire alarms\n        will start activating due to fires within range. This is also the time\n        between checks to see if fires have been put out, for deactivation\n        purposes.\n        ', tunable_type=int, default=15)
    FIRE_ALARM_ACTIVATION_RADIUS = Tunable(description='\n        How far away from a given fire alarm a fire must be in order not to\n        set it off.\n        ', tunable_type=float, default=5.0)
    SCORCH_TERRAIN_CLEANUP_HOUR = Tunable(description='\n        Hour of the day to attempt to clean up any scorch marks that are on\n        terrain. Range: 0-23 Default: 3 = 3am\n        ', tunable_type=int, default=3)
    SCORCH_TERRAIN_CLEANUP_RADIUS = Tunable(description='\n        The radius in which a clean scorch mark call will remove scorch marks\n        ', tunable_type=float, default=2.5)
    FIRE_INSURANCE_CLAIM_PERCENTAGE = TunablePercent(description='\n        A value between 0 and 100 which is the percentage of the loss covered \n        by insurance when an object is burned/destroyed.\n        ', default=60)
    FIRE_INSURANCE_CLAIM_NOTIFICATION = UiDialogNotification.TunableFactory(description='\n        This is the dialog that will be displayed at the end of a fire that will\n        alert the user of the amount of money they have been refunded as part of\n        the fire insurance.\n        ', text=LocalizedStringHouseholdNameSelector.TunableFactory(description='\n            This string is provided two tokens.\n              * The first token is either a Sim, should the Sim be the only\n             member of the household, or a string containing the household name\n             should that not be the case. \n              * The second token is a number representing the amount of money\n              refunded by insurance.\n            '))
    START_PANIC_INTERACTION = situation_complex.TunableReference(description='\n            The interaction to look for when a Sim reacts to a fire to know to\n            start that Sim in the panic state.\n            ', manager=services.affordance_manager())
    FIRE_SPREAD_HEIGHT_THRESHOLD = Tunable(description='\n        The height differential threshold, between an existing fire and the\n        place it is attempting to spawn, above which the fire will not spread.\n        ', tunable_type=float, default=0.5)
    FIRE_EXTNIGUISH_NEARBY_RADIUS = Tunable(description='\n        The radius that nearby fires or sims on fires will also be extinguished\n        when a sim extinguishes a fire or a sim on fire.\n        ', tunable_type=float, default=1.1)
    ROUTING_FIRE_CHECK_RADIUS = Tunable(description='\n        The radius in which a routing sim has to be within in order to possibly\n        catch on fire\n        ', tunable_type=float, default=0.4)
    CAREGIVER_SITUATION = Situation.TunableReference(description='\n        The caregiver situation. Used to find the care dependent bit.\n        ')
    SPRINKLER_HEAD_CEILING_OFFSET = 0.1
    IMMEDIATE_SUPPRESSION_RATE = 100.0
    FLAMMABLE_COMMODITY_BURNT_VALUE = 0

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._fire_objects = weakref.WeakSet()
        self._situation_ids = {}
        self._fire_brigade_situation_sim_ids = []
        self._fire_brigade_situation_id = None
        self._fire_spread_alarm = None
        self._fire_quadtree = None
        self._flammable_objects_quadtree = None
        self._burning_objects = None
        self._scorch_cleanup_alarm = None
        self._sprinkler_system_objects = None
        self._sprinkler_floor_objects = None
        self._sprinkler_heads = None
        self._fire_objects_being_suppressed = weakref.WeakSet()
        self._unsuppressible_fires = weakref.WeakSet()
        self._sprinkler_alarm = None
        self._sprinkler_has_been_activated = False
        self._fire_alarm_objects = weakref.WeakSet()
        self._fire_alarm_alarm = None
        self._activated_fire_alarms = weakref.WeakSet()
        self._insurance_value = 0
        self._registered_for_panic_start = False
        self._alerted_sims = False
        self._toddlers_to_save = None
        self._scorch_delay_alarms = None

    @property
    def fire_is_active(self):
        if self._fire_objects:
            return True
        return False

    @property
    def fire_quadtree(self):
        return self._fire_quadtree

    @property
    def flammable_objects_quadtree(self):
        return self._flammable_objects_quadtree

    def has_toddler_to_save_for_sim(self, saver_sim_info):
        if saver_sim_info.can_live_alone:
            if saver_sim_info.lives_here:
                return True
            for toddler in self._toddlers_to_save:
                if toddler.household is None:
                    pass
                else:
                    if toddler.household is saver_sim_info.household:
                        return True
                    if toddler.relationship_tracker.has_bit(saver_sim_info.id, self.CAREGIVER_SITUATION.caregiver_data.care_dependent_bit):
                        return True
        return False

    def get_toddler_to_save_for_sim(self, saver_sim_info):
        if self._toddlers_to_save is None:
            return
        for toddler in self._toddlers_to_save:
            if toddler.relationship_tracker.has_bit(saver_sim_info.id, self.CAREGIVER_SITUATION.caregiver_data.care_dependent_bit):
                self._toddlers_to_save.remove(toddler)
                return toddler
        return self._toddlers_to_save.pop()

    def get_lock_save_reason(self):
        return self.SAVE_LOCK_TOOLTIP()

    def get_fire_position(self):
        if not self._fire_objects:
            return
        fire_objects_list = list(self._fire_objects)
        fire_object = random.choice(fire_objects_list)
        return fire_object.position

    def _fire_spread_alarm_callback(self, handle):
        if not self.fire_is_active:
            alarms.cancel_alarm(handle)
            self._fire_spread_alarm = None
            return
        chance = random.uniform(0, 1)
        if chance > self.FIRE_SPREAD_CHANCE:
            return
        self.spread_fire()

    def _add_fire_to_quadtree(self, fire_object):
        if self._fire_quadtree is None:
            self._fire_quadtree = sims4.geometry.QuadTree()
        location = sims4.math.Vector2(fire_object.position.x, fire_object.position.z)
        fire_bounds = sims4.geometry.QtCircle(location, self.FIRE_QUADTREE_RADIUS)
        self._fire_quadtree.insert(fire_object, fire_bounds)

    def _remove_fire_from_quadtree(self, fire_object):
        if self._fire_quadtree is None:
            return
        self._fire_quadtree.remove(fire_object)

    def query_quadtree_for_fire_object(self, position, radius=DEFAULT, surface_id=None):
        if self._fire_quadtree is None:
            return []
        if radius is DEFAULT:
            radius = self.FIRE_QUADTREE_RADIUS
        query = sims4.geometry.SpatialQuery(sims4.geometry.QtCircle(position, radius), [self._fire_quadtree])
        found_fires = query.run()
        if surface_id is not None:
            fires_to_remove = set()
            for fire in found_fires:
                if fire.routing_surface.secondary_id != surface_id.secondary_id:
                    fires_to_remove.add(fire)
            if fires_to_remove:
                found_fires = [fire for fire in found_fires if fire not in fires_to_remove]
        return found_fires

    def _query_quadtree_for_flammable_object(self, position, radius=DEFAULT, surface_id=None):
        if self._flammable_objects_quadtree is None:
            return []
        radius = self.FIRE_QUADTREE_RADIUS if radius is DEFAULT else radius
        query = sims4.geometry.SpatialQuery(sims4.geometry.QtCircle(position, radius), [self._flammable_objects_quadtree])
        found_objs = query.run()
        if surface_id is not None:
            obj_to_remove = set()
            for fire in found_objs:
                if fire.routing_surface != surface_id:
                    obj_to_remove.add(fire)
            if obj_to_remove:
                found_objs = [fire for fire in found_objs if fire not in obj_to_remove]
        return found_objs

    def _query_quadtree_for_sim(self, position, surface_id, filter_type, radius=DEFAULT, flags=sims4.geometry.ObjectQuadTreeQueryFlag.IGNORE_SURFACE_TYPE):
        sim_quadtree = services.sim_quadtree()
        radius = self.FIRE_QUADTREE_RADIUS if radius is DEFAULT else radius
        return sim_quadtree.query(sims4.geometry.QtCircle(position, radius), surface_id=surface_id, flags=flags, filter=filter_type)

    def _derail_routing_sims_if_necessary(self, fire):
        fire_footprint = fire.footprint_polygon
        for sim in services.sim_info_manager().instanced_sims_on_active_lot_gen():
            current_path = sim.routing_component.current_path
            if current_path and current_path.nodes:
                nodes_list = list(current_path.nodes)
                for (prev, curr) in zip(nodes_list, nodes_list[1:]):
                    path_rectangle = sims4.geometry.CompoundPolygon([sims4.geometry.build_rectangle_from_two_points_and_radius(sims4.math.Vector3(*prev.position), sims4.math.Vector3(*curr.position), 1.0)])
                    if path_rectangle.intersects(fire_footprint):
                        sim.queue.transition_controller.derail(DerailReason.NAVMESH_UPDATED, sim)
                        break

    def _fire_object_state_changed_callback(self, owner, state, old_value, new_value):
        if state is self.FIRE_OBJECT_FIRE_STATE and new_value is self.FIRE_OBJECT_EXTINGUISHED_STATE_VALUE and not owner.get_users():
            owner.destroy(source=owner, cause='Fire is being extinguished.')

    def is_fire_allowed(self, transform, routing_surface, run_placement_tests=True):
        if not fire_enabled:
            logger.info('Trying to spawn fire when fire is disabled. Please use |fire.toggle_enabled cheat to turn fire on.')
            return False
        if not services.active_lot().is_position_on_lot(transform.translation):
            logger.info('Trying to spawn fire on a lot other than the active lot.')
            return False
        if not services.venue_service().venue.allows_fire:
            logger.info("Trying to spawn a fire on a venue that doesn't allow fire.")
            return False
        elif run_placement_tests and not self._placement_tests(transform.translation, routing_surface):
            logger.info('Trying to spawn a fire on a lot at a position that is not valid.')
            return False
        return True

    def _spawn_fire(self, transform, routing_surface, run_placement_tests=True):
        if not self.is_fire_allowed(transform, routing_surface, run_placement_tests=run_placement_tests):
            return
        fire_object = system.create_object(self.FIRE_OBJECT_DEF)
        fire_object.move_to(transform=transform, routing_surface=routing_surface)
        first_fire_on_lot = False if self._fire_objects else True
        self._fire_objects.add(fire_object)
        fire_object.add_state_changed_callback(self._fire_object_state_changed_callback)
        self.start_objects_burning(fire_object)
        self.add_scorch_mark(fire_object.position, fire_object.routing_surface.secondary_id)
        build_buy.remove_floor_feature(build_buy.FloorFeatureType.LEAF, fire_object.position, fire_object.routing_surface.secondary_id)
        self._derail_routing_sims_if_necessary(fire_object)
        if first_fire_on_lot:
            self._start_fire_brigade_situation()
            self._start_fire_situations()
            self.activate_fire_alarms()
            self.activate_sprinkler_system()
            self._show_fire_notification()
            services.get_persistence_service().lock_save(self)
            self.register_for_sim_active_lot_status_changed_callback()
        if self._fire_spread_alarm is None:
            time_span = date_and_time.create_time_span(minutes=self.FIRE_SPREAD_INTIAL_TIME_IN_SIM_MINUTES)
            repeating_time_span = date_and_time.create_time_span(minutes=self.FIRE_SPREAD_REPEATING_TIME_IN_SIM_MINUTES)
            self._fire_spread_alarm = alarms.add_alarm(self, time_span, self._fire_spread_alarm_callback, repeating=True, repeating_time_span=repeating_time_span)
        return fire_object

    def spawn_fire_at_object(self, obj, num_fires=1):
        fire_object = self._spawn_fire(obj.transform, obj.routing_surface)
        if fire_object is None or num_fires <= 1:
            return
        created_fire_objects = (fire_object,)
        for _ in range(1, num_fires):
            self.spread_fire(fire_object_list_override=created_fire_objects)

    def _show_fire_notification(self):
        client = services.client_manager().get_first_client()
        dialog = self.FIRE_STARTED_NOTIFICATION(client.active_sim)
        dialog.show_dialog()

    def spread_fire(self, fire_object_list_override=None):
        if not self._fire_objects:
            return
        logger.debug('Starting to attempt to spread fire.')
        fire_object_list = fire_object_list_override or list(self._fire_objects)
        for attempt in range(self.MAX_NUM_ATTEMPTS_TO_PLACE_FIRE):
            logger.debug('Attempt {} to spread fire.', attempt)
            fire_object = random.choice(fire_object_list)
            distance_in_radii = self.FIRE_PLACEMENT_RANGE.random_float()*self.FIRE_QUADTREE_RADIUS
            new_position = fire_object.position + fire_object.forward*distance_in_radii
            new_position.y = terrain.get_terrain_height(new_position.x, new_position.z, fire_object.routing_surface)
            fire_object.move_to(transform=fire_object.transform, orientation=sims4.random.random_orientation())
            if not self._placement_tests(new_position, surface_id=fire_object.routing_surface, fire_object=fire_object):
                pass
            else:
                transform = sims4.math.Transform(new_position, sims4.random.random_orientation())
                self._spawn_fire(transform, fire_object.routing_surface, run_placement_tests=False)
                logger.debug('Successfully placed fire object on attempt {}', attempt)
                return

    def _placement_tests(self, new_position, surface_id=None, fire_object=None):
        zone_id = services.current_zone_id()
        if surface_id is not None:
            if build_buy.has_floor_at_location(zone_id, new_position, surface_id.secondary_id) and (build_buy.is_location_pool(zone_id, new_position, surface_id.secondary_id) or build_buy.is_location_pool(zone_id, new_position, surface_id.secondary_id + 1)):
                logger.debug("failed to place fire at a location because there is no floor or it's pool.")
                return False
            if terrain.get_water_depth(new_position.x, new_position.z) > 0:
                return False
        if fire_object is not None and abs(fire_object.position.y - new_position.y) > self.FIRE_SPREAD_HEIGHT_THRESHOLD:
            return False
        if fire_object is not None:
            plex_zone_id = services.get_plex_service().get_plex_zone_at_position(new_position, fire_object.location.level)
            plex_building_type = services.get_plex_service().get_plex_building_type(zone_id)
            if (plex_building_type == PlexBuildingType.FULLY_CONTAINED_PLEX or plex_building_type == PlexBuildingType.PENTHOUSE_PLEX) and (plex_zone_id is None or plex_zone_id != zone_id):
                return False
        location = sims4.math.Vector2(new_position.x, new_position.z)
        result = self.query_quadtree_for_fire_object(location, surface_id=surface_id)
        if result:
            logger.debug('failed to place fire at a location because it overlaps with another fire object.')
            return False
        result = self._query_quadtree_for_sim(location, surface_id, int(placement.ItemType.SIM_POSITION))
        if any(not self.FIRE_CAN_SPREAD_TO_SIM_TESTS.run_tests(SingleSimResolver(entry[0].sim_info)) for entry in result):
            return False
        else:
            result = self._query_quadtree_for_flammable_object(location, surface_id=surface_id)
            if any(x.fire_retardant for x in result):
                return False
        return True

    def is_object_flammable(self, obj):
        tracker = obj.get_tracker(self.FLAMMABLE_COMMODITY)
        if tracker is None or not tracker.has_statistic(self.FLAMMABLE_COMMODITY):
            return False
        return True

    def set_object_burning(self, obj):
        tracker = obj.get_tracker(self.FLAMMABLE_COMMODITY)
        if tracker is None or not tracker.has_statistic(self.FLAMMABLE_COMMODITY):
            return
        stat = tracker.get_statistic(self.FLAMMABLE_COMMODITY)
        value = sims4.math.clamp(stat.convergence_value, stat.get_value() - self.FLAMMABLE_COMMODITY_DECAY_PER_FIRE, stat.max_value)
        stat.set_value(value)
        stat.add_decay_rate_modifier(self.FLAMMABLE_COMMODITY_DECAY_PER_FIRE)

    def add_to_flammable_quadtree(self, obj):
        if not obj.is_fire_related_object:
            return
        location = sims4.math.Vector2(obj.position.x, obj.position.z)
        if obj.is_in_inventory() and location == TunableVector2.DEFAULT_ZERO:
            return
        obj.append_tags({FireTuning.FLAMMABLE_TAG})
        if self._flammable_objects_quadtree is None:
            self._flammable_objects_quadtree = sims4.geometry.QuadTree()
        object_bounds = obj.object_bounds_for_flammable_object(self.FIRE_RETARDANT_EXTRA_OBJECT_RADIUS)
        self._flammable_objects_quadtree.insert(obj, object_bounds)

    def flammable_object_location_changed(self, obj, *_, **__):
        zone = services.current_zone()
        if zone.is_zone_loading:
            return
        if isinstance(obj, Fire):
            self._remove_fire_from_quadtree(obj)
            self._add_fire_to_quadtree(obj)
        else:
            self.remove_from_flammable_quadtree(obj)
            self.add_to_flammable_quadtree(obj)

    def remove_from_flammable_quadtree(self, obj):
        if self._flammable_objects_quadtree is None:
            return
        self._flammable_objects_quadtree.remove(obj)

    def start_objects_burning(self, fire_object):
        location = sims4.math.Vector2(fire_object.position.x, fire_object.position.z)
        fire_surface = fire_object.routing_surface
        result = self._query_quadtree_for_flammable_object(location)
        if result is not None:
            for obj in result:
                parent_or_obj = obj.get_parenting_root()
                if parent_or_obj is None or parent_or_obj.is_sim:
                    routing_surface = obj.routing_surface
                else:
                    routing_surface = parent_or_obj.routing_surface
                if routing_surface != fire_surface:
                    pass
                else:
                    placement_flags = build_buy.get_object_placement_flags(obj.definition.id)
                    if placement_flags & build_buy.PlacementFlags.CEILING and not placement_flags & build_buy.PlacementFlags.WALL_GRAPH_PLACEMENT:
                        pass
                    else:
                        logger.debug('Fire object ({}) overlaps with {}\n', fire_object, obj)
                        if self._burning_objects is None:
                            self._burning_objects = {}
                        if fire_object not in self._burning_objects:
                            self._burning_objects[fire_object] = []
                        self._burning_objects[fire_object].append(obj)
                        self.set_object_burning(obj)
            fire_object.raycast_context_dirty = True
        result = self._query_quadtree_for_sim(location, surface_id=fire_surface, filter_type=placement.ItemType.SIM_POSITION)
        if result is not None:
            for (sim, _, _, _) in result:
                if not self.sim_is_on_fire(sim):
                    self._burn_sim(sim, fire_object)

    def _burn_sim(self, sim, fire_object):
        resolver = SingleSimResolver(sim.sim_info)
        chance = self.FIRE_SIM_ON_FIRE_CHANCE.get_chance(resolver)
        if random.random() > chance:
            return
        context = InteractionContext(sim, InteractionContext.SOURCE_SCRIPT, Priority.Critical, client=None, pick=None)
        result = sim.push_super_affordance(self.FIRE_SIM_ON_FIRE_AFFORDANCE, None, context)
        if result:
            result.interaction.add_liability(FireImmunityLiability.LIABILITY_TOKEN, FireImmunityLiability())

    def _extinguish_sim(self, sim):
        tracker = sim.get_tracker(self.FLAMMABLE_COMMODITY)
        if tracker is not None and tracker.has_statistic(self.FLAMMABLE_COMMODITY):
            tracker.set_max(self.FLAMMABLE_COMMODITY)

    def check_for_catching_on_fire(self, sim):
        if not self.fire_is_active:
            return False
        for interaction in sim.get_all_running_and_queued_interactions():
            fire_immunity_liability = interaction.get_liability(FireImmunityLiability.LIABILITY_TOKEN)
            if fire_immunity_liability is not None:
                return False
            if interaction.affordance is UserFootprintHelper.MOVE_SIM_AFFORDANCE:
                return False
        if not self.FIRE_CAN_SPREAD_TO_SIM_TESTS.run_tests(SingleSimResolver(sim.sim_info)):
            return False
        location = sims4.math.Vector2(sim.position.x, sim.position.z)
        has_fire_at_location = self.query_quadtree_for_fire_object(location, radius=self.ROUTING_FIRE_CHECK_RADIUS, surface_id=sim.routing_surface)
        for fire_object in has_fire_at_location:
            tracker = fire_object.get_tracker(self.FIRE_STRENGTH_COMMODITY)
            if tracker is None:
                pass
            else:
                stat = tracker.get_statistic(self.FIRE_STRENGTH_COMMODITY)
                if stat is None:
                    pass
                else:
                    stat_value = stat.get_value()
                    if stat_value > stat.min_value:
                        self._burn_sim(sim, has_fire_at_location[0])
                        return True
        return False

    def remove_fire_object(self, fire_object):
        if fire_object in self._burning_objects:
            for obj in self._burning_objects[fire_object]:
                self._stop_object_burning(obj, fire_object)
            del self._burning_objects[fire_object]
        if self._burning_objects and fire_object in self._fire_objects:
            self._fire_objects.remove(fire_object)
            fire_object.remove_state_changed_callback(self._fire_object_state_changed_callback)
        tracker = fire_object.get_tracker(self.FIRE_BEEN_EXTINGUISHED_COMMODITY)
        if tracker is not None:
            stat = tracker.get_statistic(self.FIRE_BEEN_EXTINGUISHED_COMMODITY)
            if stat is not None and stat.get_value() > 0:
                self._remove_fire_from_quadtree(fire_object)
        if not self._fire_objects:
            self._fire_quadtree = None
            self._alerted_sims = False
            self._advance_situations_to_postfire()
            self._advance_fire_brigade_to_postfire()
            self._fire_brigade_situation_sim_ids = []
            self._fire_brigade_situation_id = None
            self._award_insurance_money()
            services.get_persistence_service().unlock_save(self)
            self.unregister_for_panic_callback()
            self.unregister_for_sim_active_lot_status_changed_callback()
            self.deactivate_fire_alarms()

    def _stop_object_burning(self, obj, fire_object):
        tracker = obj.get_tracker(self.FLAMMABLE_COMMODITY)
        if tracker is None or not tracker.has_statistic(self.FLAMMABLE_COMMODITY):
            return
        if not obj.is_sim:
            stat = tracker.get_statistic(self.FLAMMABLE_COMMODITY)
            stat.remove_decay_rate_modifier(self.FLAMMABLE_COMMODITY_DECAY_PER_FIRE)
            if stat.get_value() > self.FLAMMABLE_COMMODITY_BURNT_VALUE:
                tracker.set_max(self.FLAMMABLE_COMMODITY)
            if self._burning_objects is not None:
                self._burning_objects[fire_object].remove(obj)
                fire_object.raycast_context_dirty = True

    def objects_burning_from_fire_object(self, fire_object):
        if self._burning_objects is None or fire_object not in self._burning_objects:
            return []
        else:
            return self._burning_objects[fire_object]

    def extinguish_nearby_fires(self, subject):
        translation = subject.location.transform.translation
        location = sims4.math.Vector2(translation.x, translation.z)
        surface_id = subject.routing_surface
        fires_at_location = self.query_quadtree_for_fire_object(location, radius=self.FIRE_EXTNIGUISH_NEARBY_RADIUS, surface_id=surface_id)
        for fire in fires_at_location:
            if fire is not subject:
                self._suppress_fire(fire, immediate=True)
        nearby_sims = self._query_quadtree_for_sim(location, surface_id=surface_id, filter_type=placement.ItemType.SIM_POSITION, radius=self.FIRE_EXTNIGUISH_NEARBY_RADIUS)
        if nearby_sims is not None:
            for (sim, _, _, _) in nearby_sims:
                if sim is not subject:
                    self._extinguish_sim(sim)

    @classmethod
    def _set_scorch_amount(cls, position, surface_id, amount):
        zone_id = services.current_zone_id()
        with build_buy.floor_feature_update_context(zone_id, build_buy.FloorFeatureType.BURNT):
            position = sims4.math.Vector3(position.x, position.y, position.z)
            return build_buy.set_floor_feature(zone_id, build_buy.FloorFeatureType.BURNT, position, surface_id, amount)

    @classmethod
    def add_scorch_mark(cls, position, surface_id):
        return cls._set_scorch_amount(position, surface_id, 1.0)

    @classmethod
    def remove_scorch_mark(cls, position, surface_id):
        return cls._set_scorch_amount(position, surface_id, 0.0)

    def add_delayed_scorch_mark(self, position, surface_id, delay_time_span):
        if self._scorch_delay_alarms is None:
            self._scorch_delay_alarms = []

        def add_scorch_mark_from_alarm(handle, position, surface_id):
            if handle in self._scorch_delay_alarms:
                self._scorch_delay_alarms.remove(handle)
                self.add_scorch_mark(position, surface_id.secondary_id)

        scorch_handle = alarms.add_alarm(self, delay_time_span, lambda handle: add_scorch_mark_from_alarm(handle, position, surface_id))
        self._scorch_delay_alarms.append(scorch_handle)

    def _start_fire_situations(self):
        self._reset_situations_to_unaware()
        situation_manager = services.current_zone().situation_manager
        for sim in services.sim_info_manager().instanced_sims_on_active_lot_gen():
            self._create_fire_situation_on_sim(sim, situation_manager=situation_manager)

    def _start_fire_brigade_situation(self):
        if self.FIRE_BRIGADE_SITUATION is None:
            return
        if not self.FIRE_BRIGADE_SITUATION.should_create_volunteer_brigade():
            return
        situation_manager = services.current_zone().situation_manager
        guest_list = self.FIRE_BRIGADE_SITUATION.get_predefined_guest_list()
        situation_id = situation_manager.create_situation(self.FIRE_BRIGADE_SITUATION, guest_list=guest_list, user_facing=False)
        self._fire_brigade_situation_id = situation_id
        for x in guest_list.invited_guest_infos_gen():
            self._fire_brigade_situation_sim_ids.append(x.sim_id)

    def _create_fire_situation_on_sim(self, sim, situation_manager=None):
        if sim.id in self._situation_ids:
            return
        if sim.id in self._fire_brigade_situation_sim_ids:
            return
        if situation_manager is None:
            situation_manager = services.current_zone().situation_manager
        guest_list = SituationGuestList(invite_only=True)
        guest_info = SituationGuestInfo.construct_from_purpose(sim.sim_id, self.FIRE_JOB, SituationInvitationPurpose.INVITED)
        guest_list.add_guest_info(guest_info)
        situation_id = situation_manager.create_situation(self.FIRE_SITUATION, guest_list=guest_list, user_facing=False)
        self._situation_ids[sim.id] = situation_id
        if self._alerted_sims:
            fire_situation = situation_manager.get(situation_id)
            if fire_situation is not None:
                fire_situation.advance_to_panic()

    def remove_fire_situation(self, sim):
        if sim.id in self._situation_ids:
            del self._situation_ids[sim.id]

    def alert_all_sims(self):
        if self._alerted_sims:
            return
        situation_manager = services.current_zone().situation_manager
        for situation_id in self._situation_ids.values():
            situation = situation_manager.get(situation_id)
            if situation is not None:
                situation.advance_to_panic()
        self._alerted_sims = True

    def _push_fire_reaction_affordance(self, sim, target):
        context = InteractionContext(sim, InteractionContext.SOURCE_SCRIPT, Priority.High, client=None, pick=None)
        result = sim.push_super_affordance(self.START_PANIC_INTERACTION, target, context)
        return result

    def register_for_panic_callback(self):
        if not self._registered_for_panic_start:
            services.get_event_manager().register_single_event(self, TestEvent.InteractionComplete)
            self._registered_for_panic_start = True

    def unregister_for_panic_callback(self):
        if self._registered_for_panic_start:
            services.get_event_manager().unregister_single_event(self, TestEvent.InteractionComplete)
            self._registered_for_panic_start = False

    def register_for_sim_active_lot_status_changed_callback(self):
        services.get_event_manager().register_single_event(self, TestEvent.SimActiveLotStatusChanged)

    def unregister_for_sim_active_lot_status_changed_callback(self):
        services.get_event_manager().unregister_single_event(self, TestEvent.SimActiveLotStatusChanged)

    def handle_event(self, sim_info, event, resolver):
        if issubclass(type(resolver.interaction), self.START_PANIC_INTERACTION):
            sim = sim_info.get_sim_instance()
            dialog = self.FIRE_REACTION_NOTIFICATION(sim, resolver=SingleSimResolver(sim_info))
            dialog.show_dialog()
            self.alert_all_sims()
            self.unregister_for_panic_callback()
            for sim_on_lot in services.sim_info_manager().instanced_sims_on_active_lot_gen():
                if sim_on_lot is not sim:
                    self._push_fire_reaction_affordance(sim_on_lot, resolver.interaction.target)
        if event is TestEvent.InteractionComplete and event is TestEvent.SimActiveLotStatusChanged and resolver.get_resolved_arg('on_active_lot'):
            sim = sim_info.get_sim_instance()
            if sim is not None:
                self._create_fire_situation_on_sim(sim)

    def _advance_situations_to_postfire(self):
        self._toddlers_to_save = None
        situation_manager = services.get_zone_situation_manager()
        if self._situation_ids is not None:
            for situation_id in self._situation_ids.values():
                situation = situation_manager.get(situation_id)
                if situation is not None:
                    situation.advance_to_post_fire()

    def _advance_fire_brigade_to_postfire(self):
        if self._fire_brigade_situation_id is None:
            return
        fire_brigade_situation = services.get_zone_situation_manager().get(self._fire_brigade_situation_id)
        if fire_brigade_situation is None:
            return
        fire_brigade_situation.advance_to_post_fire()

    def _reset_situations_to_unaware(self):
        situation_manager = services.get_zone_situation_manager()
        if self._situation_ids is not None:
            for situation_id in self._situation_ids.values():
                situation = situation_manager.get(situation_id)
                if situation is not None:
                    situation.reset_to_unaware()
        self._toddlers_to_save = set()
        for sim in services.sim_info_manager().instanced_sims_on_active_lot_gen():
            if sim.sim_info.is_toddler:
                self._toddlers_to_save.add(sim)

    def _stop_fire_situations(self):
        situation_manager = services.get_zone_situation_manager()
        if self._situation_ids is not None:
            for situation_id in self._situation_ids.values():
                situation_manager.destroy_situation_by_id(situation_id)

    def fire_interaction_test(self, affordance, context):
        if not InteractionCancelCompatibility.check_if_source_should_be_canceled(context):
            return TestResult.TRUE
        if self.fire_is_active and context.sim is not None:
            for buff_type in self.FIRE_PANIC_BUFFS:
                if context.sim.has_buff(buff_type):
                    break
            return TestResult.TRUE
            if InteractionCancelCompatibility.can_cancel_interaction_for_reason(affordance, InteractionCancelReason.FIRE):
                return TestResult(False, '{} is not allowed because there is a fire object on the lot', affordance)
        return TestResult.TRUE

    def sim_is_on_fire(self, sim):
        for interaction in sim.get_all_running_and_queued_interactions():
            if interaction.affordance is self.FIRE_SIM_ON_FIRE_AFFORDANCE:
                return True
        return False

    def start(self):
        object_manager = services.object_manager()
        object_manager.register_callback(CallbackTypes.ON_OBJECT_REMOVE, self.remove_from_flammable_quadtree)
        self._create_or_replace_scorch_cleanup_alarm()

    def stop(self):
        self._fire_objects = None
        self._fire_spread_alarm = None
        self._burning_objects = None
        self._stop_fire_situations()
        self.deactivate_sprinkler_system()
        self.deactivate_fire_alarms()
        self._sprinkler_heads = None
        self._sprinkler_floor_objects = None
        self._sprinkler_system_objects = None
        self._fire_objects_being_suppressed = None
        self._unsuppressible_fires = None
        self._sprinkler_alarm = None
        self._fire_alarm_alarm = None
        self._fire_alarm_objects = None
        self._activated_fire_alarms = None
        self._sprinkler_has_been_activated = False
        self._toddlers_to_save = None
        if self._scorch_cleanup_alarm is not None:
            alarms.cancel_alarm(self._scorch_cleanup_alarm)
            self._scorch_cleanup_alarm = None
        object_manager = services.object_manager()
        object_manager.unregister_callback(CallbackTypes.ON_OBJECT_REMOVE, self.remove_from_flammable_quadtree)
        self.unregister_for_panic_callback()

    def on_client_disconnect(self, client):
        services.get_persistence_service().unlock_save(self)

    def kill(self):
        for fire_object in list(self._fire_objects):
            fire_object.destroy(source=fire_object, cause='Killing all fire on lot')

    def activate_fire_alarms(self):
        object_manager = services.object_manager()
        self._fire_alarm_objects = weakref.WeakSet(object_manager.get_objects_of_type_gen(self.FIRE_ALARM_OBJECT_DEF))
        if not self._fire_alarm_objects:
            return
        time_span = date_and_time.create_time_span(minutes=self.FIRE_ALARM_CYCLE_TIME)
        repeating_time_span = date_and_time.create_time_span(minutes=self.FIRE_ALARM_CYCLE_TIME)
        self._fire_alarm_alarm = alarms.add_alarm(self, time_span, self._fire_alarm_callback, repeating=True, repeating_time_span=repeating_time_span)

    def deactivate_fire_alarms(self):
        if self._fire_alarm_alarm:
            alarms.cancel_alarm(self._fire_alarm_alarm)
            self._fire_alarm_alarm = None
        for fire_alarm in self._fire_alarm_objects:
            fire_alarm.set_state(self.FIRE_ALARM_DEACTIVATED_STATE.state, self.FIRE_ALARM_DEACTIVATED_STATE)
        self._fire_alarm_objects = weakref.WeakSet()
        self._activated_fire_alarms = weakref.WeakSet()

    def _fire_alarm_callback(self, handle):
        if not self.fire_is_active:
            alarms.cancel_alarm(handle)
            self._fire_alarm_alarm = None
            self.deactivate_fire_alarms()
            return
        deactivated_fire_alarms = self._fire_alarm_objects - self._activated_fire_alarms
        for deactivated_fire_alarm in deactivated_fire_alarms:
            alarm_position = deactivated_fire_alarm.position
            fires_in_range = self.query_quadtree_for_fire_object(sims4.math.Vector2(alarm_position.x, alarm_position.z), radius=self.FIRE_ALARM_ACTIVATION_RADIUS, surface_id=deactivated_fire_alarm.routing_surface)
            if fires_in_range:
                deactivated_fire_alarm.set_state(self.FIRE_ALARM_ACTIVE_STATE.state, self.FIRE_ALARM_ACTIVE_STATE)
                self._activated_fire_alarms.add(deactivated_fire_alarm)
        if self._activated_fire_alarms:
            self.alert_all_sims()
            fire_object = next(iter(self._fire_objects))
            for sim_on_lot in services.sim_info_manager().instanced_sims_on_active_lot_gen():
                if sim_on_lot.sim_id in self._fire_brigade_situation_sim_ids:
                    pass
                else:
                    self._push_fire_reaction_affordance(sim_on_lot, fire_object)

    def activate_sprinkler_system(self):
        object_manager = services.object_manager()
        if self._sprinkler_system_objects is None:
            self._sprinkler_system_objects = weakref.WeakSet()
        self._sprinkler_system_objects.update(object_manager.get_objects_with_tag_gen(self.SPRINKLER_BOX_OBJECT_TAG))
        if self._sprinkler_floor_objects is None:
            self._sprinkler_floor_objects = weakref.WeakSet()
        self._sprinkler_floor_objects.update(object_manager.get_objects_with_tag_gen(self.SPRINKLER_FLOOR_OBJECT_TAG))
        if self._sprinkler_system_objects or not self._sprinkler_floor_objects:
            return
        self._sprinkler_heads = set()
        time_span = date_and_time.create_time_span(minutes=self.SPRINKLER_ACTIVATION_TIME)
        repeating_time_span = date_and_time.create_time_span(minutes=self.SPRINKLER_RUN_TIME)
        self._sprinkler_alarm = alarms.add_alarm(self, time_span, self._sprinkler_alarm_callback, repeating=True, repeating_time_span=repeating_time_span)

    def deactivate_sprinkler_system(self):
        self._sprinkler_has_been_activated = False
        if self._sprinkler_system_objects is not None:
            for sprinkler_system_object in self._sprinkler_system_objects:
                sprinkler_system_object.set_state(self.FIRE_SPRINKLER_DEACTIVATED_STATE.state, self.FIRE_SPRINKLER_DEACTIVATED_STATE)
        if self._sprinkler_alarm:
            alarms.cancel_alarm(self._sprinkler_alarm)
            self._sprinkler_alarm = None
        if self._sprinkler_heads is not None:
            for sprinkler in self._sprinkler_heads:
                sprinkler.destroy(source=sprinkler, cause='Destroying sprinklers.')
        self._sprinkler_system_objects = None
        self._sprinkler_floor_objects = None
        self._sprinkler_heads = None
        self._fire_objects_being_suppressed = weakref.WeakSet()
        self._unsuppressible_fires = weakref.WeakSet()

    def _sprinkler_alarm_callback(self, handle):
        if not self.fire_is_active:
            alarms.cancel_alarm(handle)
            self._sprinkler_alarm = None
            self.deactivate_sprinkler_system()
            return
        if not self._sprinkler_has_been_activated:
            self._sprinkler_has_been_activated = True
            for sprinkler_system_object in self._sprinkler_system_objects:
                sprinkler_system_object.set_state(self.FIRE_SPRINKLER_ACTIVE_STATE.state, self.FIRE_SPRINKLER_ACTIVE_STATE)
        active_floor_sprinklers = set(sprinkler for sprinkler in self._sprinkler_floor_objects if sprinkler.state_value_active(self.FIRE_SPRINKLER_ACTIVE_STATE))
        new_fire_objects = set(self._fire_objects - self._fire_objects_being_suppressed - self._unsuppressible_fires)
        if new_fire_objects:
            for sprinkler in self._sprinkler_heads:
                new_fire_objects = self.find_and_suppress_fires_under_sprinkler(sprinkler, None, new_fire_objects, self.SPRINKLER_HEAD_SUPPRESSION_RADIUS)
            for sprinkler in active_floor_sprinklers:
                new_fire_objects = self.find_and_suppress_fires_under_sprinkler(sprinkler, None, new_fire_objects, self.SPRINKLER_FLOOR_SUPPRESSION_RADIUS)
            while new_fire_objects:
                initiating_fire = new_fire_objects.pop()
                new_sprinkler = self._spawn_sprinkler(initiating_fire)
                if new_sprinkler:
                    new_fire_objects = self.find_and_suppress_fires_under_sprinkler(new_sprinkler, initiating_fire, new_fire_objects, self.SPRINKLER_HEAD_SUPPRESSION_RADIUS)
            if new_fire_objects:
                self._unsuppressible_fires = self._unsuppressible_fires | new_fire_objects

    def find_and_suppress_fires_under_sprinkler(self, sprinkler, initiating_fire, new_fire_objects, suppression_radius):
        suppressed_fires = set()
        sprinkler_position = sims4.math.Vector2(sprinkler.position.x, sprinkler.position.z)
        sprinkler_surface = sprinkler.routing_surface
        fires_under_sprinkler = self.query_quadtree_for_fire_object(sprinkler_position, radius=suppression_radius, surface_id=sprinkler_surface)
        for fire in fires_under_sprinkler:
            if not fire == initiating_fire:
                if fire in new_fire_objects:
                    self._suppress_fire(fire)
                    suppressed_fires.add(fire)
            self._suppress_fire(fire)
            suppressed_fires.add(fire)
        if suppressed_fires:
            new_fire_objects = new_fire_objects - suppressed_fires
            self._fire_objects_being_suppressed = self._fire_objects_being_suppressed | suppressed_fires
        sims_under_sprinkler = self._query_quadtree_for_sim(sprinkler_position, surface_id=sprinkler_surface, filter_type=placement.ItemType.SIM_POSITION, radius=suppression_radius)
        if sims_under_sprinkler is not None:
            for (sim, _, _, _) in sims_under_sprinkler:
                self._extinguish_sim(sim)
        return new_fire_objects

    def _suppress_fire(self, fire, immediate=False):
        tracker = fire.get_tracker(self.FIRE_STRENGTH_COMMODITY)
        if tracker is not None and tracker.has_statistic(self.FIRE_STRENGTH_COMMODITY):
            stat = tracker.get_statistic(self.FIRE_STRENGTH_COMMODITY)
            rate = self.IMMEDIATE_SUPPRESSION_RATE if immediate else self.FIRE_STRENGTH_COMMODITY_SUPRESSION_DECAY
            stat.add_decay_rate_modifier(rate)
        tracker = fire.get_tracker(self.FIRE_BEEN_EXTINGUISHED_COMMODITY)
        if tracker is not None:
            tracker.set_max(self.FIRE_BEEN_EXTINGUISHED_COMMODITY)

    def _spawn_sprinkler(self, fire):
        zone_id = services.current_zone_id()
        new_level = fire.location.level + 1
        if not build_buy.has_floor_at_location(zone_id, fire.position, new_level):
            return
        sprinkler_head = system.create_object(self.SPRINKLER_HEAD_OBJECT_DEF)
        fire_location = fire.location
        new_translation = sims4.math.Vector3(*fire.position)
        height = terrain.get_lot_level_height(fire_location.transform.translation.x, fire_location.transform.translation.z, new_level, zone_id)
        new_translation.y = height - self.SPRINKLER_HEAD_CEILING_OFFSET
        transform = sims4.math.Transform(new_translation, fire_location.transform.orientation)
        sprinkler_head.set_location(location=fire_location.clone(transform=transform))
        self._sprinkler_heads.add(sprinkler_head)
        sprinkler_head.vfx = FireService.SPRINKLER_EFFECT(sprinkler_head)
        sprinkler_head.vfx.start()
        return sprinkler_head

    def _create_or_replace_scorch_cleanup_alarm(self):
        if self._scorch_cleanup_alarm:
            alarms.cancel_alarm(self._scorch_cleanup_alarm)
            self._scorch_cleanup_alarm = None
        now = services.time_service().sim_now
        time_span_until = clock.time_until_hour_of_day(now, self.SCORCH_TERRAIN_CLEANUP_HOUR)
        repeat_length = date_and_time.create_time_span(hours=24)
        self._scorch_cleanup_alarm = alarms.add_alarm(self, time_span_until, self._cleanup_scorch_marks_on_terrain, repeating=True, repeating_time_span=repeat_length)

    def _cleanup_scorch_marks_on_terrain(self, handle):
        if self.fire_is_active:
            return
        zone_id = services.current_zone_id()
        list_result = build_buy.list_floor_features(zone_id, build_buy.FloorFeatureType.BURNT)
        if list_result:
            with build_buy.floor_feature_update_context(zone_id, build_buy.FloorFeatureType.BURNT):
                for tile in list_result:
                    if build_buy.is_location_natural_ground(zone_id, tile[0], tile[1]):
                        build_buy.remove_floor_feature(build_buy.FloorFeatureType.BURNT, tile[0], tile[1])

    def find_cleanable_scorch_mark_locations_within_radius(self, location, level, radius):
        found_scorch_marks = set()
        zone_id = services.current_zone_id()
        radius_squared = radius*radius
        all_scorch_marks = build_buy.list_floor_features(zone_id, build_buy.FloorFeatureType.BURNT)
        for scorch_mark in all_scorch_marks:
            scorch_level = scorch_mark[1]
            if scorch_level == level and not build_buy.is_location_natural_ground(zone_id, scorch_mark[0], scorch_level):
                scorch_location = scorch_mark[0]
                if (location - scorch_location).magnitude_squared() <= radius_squared:
                    found_scorch_marks.add(scorch_location)
        return found_scorch_marks

    def increment_insurance_claim(self, value, burnt_object):
        if household_manager.HouseholdManager.get_active_sim_home_zone_id() == burnt_object.zone_id:
            if not self.fire_is_active:
                return
            self._insurance_value += value*self.FIRE_INSURANCE_CLAIM_PERCENTAGE

    def _award_insurance_money(self):
        client = services.client_manager().get_first_client()
        active_sim = client.active_sim
        if active_sim is not None:
            services.active_household().funds.add(self._insurance_value, Consts_pb2.TELEMETRY_INTERACTION_COST, None)
            dialog = self.FIRE_INSURANCE_CLAIM_NOTIFICATION(active_sim, SingleSimResolver(active_sim))
            dialog.show_dialog(additional_tokens=(self._insurance_value,))
            self._insurance_value = 0
