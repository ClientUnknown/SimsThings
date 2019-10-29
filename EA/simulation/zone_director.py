from _hashutil import hash32from _math import Vector2, Quaternionimport itertoolsimport mathimport randomfrom protocolbuffers import Routing_pb2, GameplaySaveData_pb2from build_buy import register_build_buy_exit_callback, unregister_build_buy_exit_callbackfrom business.business_enums import BusinessTypefrom date_and_time import DateAndTimefrom default_property_stream_reader import DefaultPropertyStreamReaderfrom event_testing.resolver import SingleObjectResolver, SingleSimResolverfrom gsi_handlers import zone_director_handlersfrom interactions.constraints import Constraintfrom objects.components.state import TunableStateValueReference, TunablePackSafeStateValueReferencefrom objects.definition_manager import TunableDefinitionListfrom objects.system import create_objectfrom open_street_director.open_street_director_manager import OpenStreetDirectorManagerfrom placement import FGLSearchFlagfrom restaurants.restaurant_tuning import RestaurantTuning, get_restaurant_zone_directorfrom services.fire_service import FireServicefrom sims.baby.baby_utils import run_baby_spawn_behaviorfrom sims.outfits.outfit_enums import OutfitCategoryfrom sims.sim_info_types import SimZoneSpinUpActionfrom sims.sim_spawner import SimSpawnerfrom sims4 import geometryfrom sims4.math import UP_AXISfrom sims4.resources import Typesfrom sims4.tuning.geometric import TunableVector2from sims4.tuning.instances import HashedTunedInstanceMetaclassfrom sims4.tuning.tunable import HasTunableReference, Tunable, OptionalTunable, TunableList, TunableTuple, TunableVariant, TunableInterval, AutoFactoryInit, HasTunableSingletonFactory, TunableReference, TunableAngle, TunableEnumWithFilterfrom singletons import DEFAULTfrom situations.service_npcs.modify_lot_items_tuning import TunableObjectModifyTestSet, ModifyAllLotItemsfrom tag import Tag, SPAWN_PREFIXfrom ui.ui_dialog_notification import TunableUiDialogNotificationSnippetfrom venues.attractor_creation_director_mixin import AttractorCreationDirectorMixinfrom venues.venue_constants import NPCSummoningPurposefrom world.spawn_point import SpawnPointOption, SpawnPointimport build_buyimport date_and_timeimport distributor.rollbackimport enumimport placementimport routingimport servicesimport simsimport sims4.logimport sims4.resourcesimport sims4.utilsimport terrainlogger = sims4.log.Logger('ZoneDirector')
class _ZoneSavedSimOp(enum.Int, export=False):
    MAINTAIN = ...
    REINITIATE = ...
    CLEAR = ...

class _OpenStreetSavedSimOp(enum.Int, export=False):
    MAINTAIN = ...
    CLEAR = ...

def _get_connectivity_source_handle():
    current_zone = services.current_zone()
    spawn_point = current_zone.get_spawn_point()
    if spawn_point is not None:
        return routing.connectivity.Handle(spawn_point.get_approximate_center(), spawn_point.routing_surface)
    corner = current_zone.lot.corners[0]
    routing_surface = routing.SurfaceIdentifier(current_zone.id, 0, routing.SurfaceType.SURFACETYPE_WORLD)
    return routing.connectivity.Handle(corner, routing_surface)

class CreateRandomObjectSetup(HasTunableSingletonFactory, AutoFactoryInit):
    FACTORY_TUNABLES = {'objects_to_choose_from': TunableDefinitionList(description='\n            An object will be randomly chosen from this list and placed near\n            whichever object passed the tuned tests for this crime scene\n            change.\n            '), 'maximum_distance': Tunable(description='\n            New objects will be spawned within this distance of objects that\n            pass the tuned tests for this crime scene change.\n            ', tunable_type=float, default=3.0)}

    def apply(self, obj, setup_log):
        object_definition = random.choice(self.objects_to_choose_from)
        created_obj = create_object(object_definition)
        if created_obj is None or obj.routing_surface is None:
            return
        search_flags = placement.FGLSearchFlagsDefault | FGLSearchFlag.SHOULD_TEST_BUILDBUY | FGLSearchFlag.STAY_IN_CURRENT_BLOCK
        starting_location = placement.create_starting_location(location=obj.location)
        fgl_context = placement.create_fgl_context_for_object(starting_location, created_obj, search_flags=search_flags, max_distance=self.maximum_distance, random_range_weighting=sims4.math.MAX_INT32)
        (position, orientation) = placement.find_good_location(fgl_context)
        if position is None:
            created_obj.destroy()
            return
        source_handles = [_get_connectivity_source_handle()]
        dest_handles = [routing.connectivity.Handle(position, obj.routing_surface)]
        connectivity = routing.test_connectivity_batch(source_handles, dest_handles, allow_permissive_connections=True)
        if connectivity is None:
            created_obj.destroy()
            return
        created_obj.location = sims4.math.Location(sims4.math.Transform(position, orientation), obj.routing_surface)
        setup_log.append({'action': 'Create Random Object', 'description': 'Obj Def: {0}'.format(object_definition.name)})
        return DestroyObjects(objects_to_destroy=(created_obj,))

    def fill_quota(self, count, setup_log):
        zone = services.current_zone()
        lot = zone.lot
        terrain = services.terrain_service.terrain_object()
        min_level = lot.min_level
        max_level = lot.max_level
        source_handles = [_get_connectivity_source_handle()]
        dest_handles = []
        num_points = count*2*(1 + max_level - min_level)
        positions = geometry.random_uniform_points_in_polygon(lot.corners, num=num_points)
        for position in positions:
            level = random.randint(min_level, max_level)
            surface = routing.SurfaceIdentifier(zone.id, level, routing.SurfaceType.SURFACETYPE_WORLD)
            handle = routing.connectivity.Handle(position, surface)
            dest_handles.append(handle)
        connectivity = routing.test_connectivity_batch(source_handles, dest_handles, allow_permissive_connections=True)
        if connectivity is None:
            return ()
        random.shuffle(connectivity)
        objects = []
        for (_, handle, _) in connectivity:
            orientation = sims4.math.angle_to_yaw_quaternion(random.uniform(0, 2*sims4.math.PI))
            (x, _, z) = handle.polygons[0][0]
            y = terrain.get_routing_surface_height_at(x, z, handle.routing_surface_id)
            location = sims4.math.Location(sims4.math.Transform(sims4.math.Vector3(x, y, z), orientation), handle.routing_surface_id)
            object_definition = random.choice(self.objects_to_choose_from)
            (result, _) = build_buy.test_location_for_object(None, object_definition.id, location=location)
            if result:
                obj = create_object(object_definition)
                obj.location = location
                objects.append(obj)
                setup_log.append({'action': 'Create Random Object', 'description': 'Obj Def: {0}'.format(object_definition.name)})
                if len(objects) == count:
                    break
        if not objects:
            return ()
        return (DestroyObjects(objects_to_destroy=objects),)

class SetStateSetup(HasTunableSingletonFactory, AutoFactoryInit):
    FACTORY_TUNABLES = {'prepare_state': TunablePackSafeStateValueReference(description='\n            The state value we want to apply to the object when we prepare this\n            zone director.\n            ', allow_none=True), 'cleanup_state': TunablePackSafeStateValueReference(description='\n            The state value to apply to the object when we cleanup this zone\n            director.\n            ', allow_none=True), 'require_connectivity': Tunable(description='\n            If enabled, we will require the object to be in a good location\n            where its connectivity handles are valid.\n            ', tunable_type=bool, default=False)}

    @classmethod
    def _verify_tuning_callback(cls):
        if cls.prepare_state is not None and cls.cleanup_state is not None and cls.prepare_state.state is not cls.cleanup_state.state:
            logger.error('{} has a prepare state value {} and cleanup state value {} that do not share the same state. Please separate these into separate actions.', cls, cls.prepare_state, cls.cleanup_state, owner='rmccord')

    def _should_apply(self, obj):
        if not obj.state_component:
            return False
        prepare_state_value = self.prepare_state
        cleanup_state_value = self.cleanup_state
        if prepare_state_value is None and cleanup_state_value is None:
            return False
        if prepare_state_value is not None and not obj.has_state(prepare_state_value.state):
            return False
        if cleanup_state_value is not None and not obj.has_state(cleanup_state_value.state):
            return False
        elif self.require_connectivity:
            routing_context = routing.PathPlanContext()
            routing_context.set_key_mask(routing.FOOTPRINT_KEY_ON_LOT | routing.FOOTPRINT_KEY_OFF_LOT)
            for parent in obj.parenting_hierarchy_gen():
                if parent.routing_context and parent.routing_context.object_footprint_id:
                    routing_context.ignore_footprint_contour(parent.routing_context.object_footprint_id)
            source_handles = [_get_connectivity_source_handle()]
            (reference_pt, _) = Constraint.get_validated_routing_position(obj)
            dest_handles = [routing.connectivity.Handle(reference_pt, obj.routing_surface)]
            connectivity = routing.test_connectivity_batch(source_handles, dest_handles, routing_context=routing_context, allow_permissive_connections=True)
            if connectivity is None:
                return False
        return True

    def apply(self, obj, setup_log):
        if not self._should_apply(obj):
            return
        prepare_state_value = self.prepare_state
        cleanup_state_value = self.cleanup_state
        applied_actions = False
        if prepare_state_value is not None:
            obj.set_state(prepare_state_value.state, prepare_state_value, immediate=True)
            applied_actions = True
        cleanup_action = None
        if cleanup_state_value is not None:
            cleanup_action = SetStateCleanup(((obj, cleanup_state_value.state, cleanup_state_value),))
            applied_actions = True
        if applied_actions:
            setup_log.append({'action': 'Set State', 'description': 'Prepare State:{0}, Cleanup State:{1}'.format(str(prepare_state_value), str(cleanup_state_value))})
        return cleanup_action

    def fill_quota(self, count, setup_log):
        return ()

class CreateScorchSetup(HasTunableSingletonFactory, AutoFactoryInit):
    FACTORY_TUNABLES = {'max_distance': Tunable(description='\n            The maximum distance, in meters, that floor scorch marks will be\n            spawned from the target object.\n            ', tunable_type=float, default=3.0)}

    def apply(self, obj, setup_log):
        random_angle = random.uniform(0, 2*math.pi)
        random_distance = random.triangular(0, self.max_distance, self.max_distance)
        offset = sims4.math.Vector3(random_distance*math.cos(random_angle), 0, random_distance*math.sin(random_angle))
        position = obj.position + offset
        level = obj.location.level
        if not FireService.add_scorch_mark(position, level):
            return
        setup_log.append({'action': 'Create Scorch Mark', 'description': 'Position:{0}, Level:{1}'.format(position, level)})
        return CleanScorchMark(position, level)

    def fill_quota(self, count, setup_log):
        lot = services.current_zone().lot
        min_level = lot.min_level
        max_level = lot.max_level
        cleanup_actions = []
        for _ in range(2*count):
            level = random.randint(min_level, max_level)
            x = lot.center.x + random.uniform(-lot.size_x/2, lot.size_x/2)
            z = lot.center.z + random.uniform(-lot.size_z/2, lot.size_z/2)
            position = sims4.math.Vector3(x, 0, z)
            if not FireService.add_scorch_mark(position, level):
                pass
            else:
                setup_log.append({'action': 'Create Scorch Mark', 'description': 'Position:{0}, Level:{1}'.format(position, level)})
                cleanup_actions.append(CleanScorchMark(position, level))
                if len(cleanup_actions) >= count:
                    break
        return cleanup_actions

class ZoneDirectorBase(AttractorCreationDirectorMixin, HasTunableReference, metaclass=HashedTunedInstanceMetaclass, manager=services.get_instance_manager(sims4.resources.Types.ZONE_DIRECTOR)):
    INSTANCE_TUNABLES = {'allow_venue_background_situations': Tunable(description='\n            If checked, venues will be allowed to run their background situations\n            (e.g. museum patrons will still show up and look at the art). If\n            unchecked, no venue-specific background situations will be created\n            (but walkbys may still occur).\n            ', tunable_type=bool, default=True), 'cleanup_zone_actions': ModifyAllLotItems.TunableFactory(description='\n            Actions to cleanup the zone every time we load. Happens before lot\n            preparations, but after venue cleanup.\n            \n            WARNING: Consider whether you actually need to do these actions\n            every time you load the game. Most actions are done in Venue\n            Service module tuning for cleanup. Things you do here will likely\n            be hidden behind a loading screen and could mess with what the\n            player saw when they saved the game or traveled.\n            '), 'lot_preparations': TunableList(description='\n            A list of changes to objects when preparing the lot. \n            \n            Note: We do not do these actions if this zone director was loaded.\n            ', tunable=TunableTuple(tests=TunableObjectModifyTestSet(description='\n                    Tests to specify what objects to apply actions to.\n                    Every test in at least one of the sublists must pass\n                    for the action associated with this tuning to be run.\n                    '), action=TunableVariant(description='\n                    The action that will be applied to objects when preparing\n                    the lot.\n                    ', set_state=SetStateSetup.TunableFactory(), create_random_object_nearby=CreateRandomObjectSetup.TunableFactory(), create_scorch_mark=CreateScorchSetup.TunableFactory()), number_of_changes=TunableInterval(description='\n                    The minimum and maximum number of allowed changes of this\n                    type for the lot preparation. The exact number will be\n                    chosen randomly and according to how many objects meet the\n                    criteria for state changes.\n                    ', tunable_type=int, minimum=0, default_lower=1, default_upper=5), on_lot_only=Tunable(description='\n                    If True, only objects on lot will be considered. Otherwise,\n                    all objects will be considered. Disable with care, as\n                    testing all objects will result in a performance hit,\n                    especially when there are a lot of objects on the open\n                    street.\n                    ', tunable_type=bool, default=True))), 'objects_to_spawn': TunableList(description='\n            A list of objects to spawn on the lot. Objects will be cleaned up\n            when this zone director stops.\n            ', tunable=TunableTuple(description='\n                Object and position.\n                ', definition=TunableReference(description='\n                    Definition of the object to spawn.\n                    ', manager=services.definition_manager()), position=TunableVector2(description='\n                    Position on lot to spawn object at. Height is automatically\n                    set as the height of the terrain.\n                    ', default=Vector2.ZERO()), angle=TunableAngle(description='\n                    Orientation of the object.\n                    ', default=0), init_state_values=TunableList(description='\n                    List of states the created object will be pushed to.\n                    ', tunable=TunableStateValueReference()), children=TunableList(description='\n                    Children to slot into object.\n                    ', tunable=TunableTuple(definition=TunableReference(description='\n                            The child object to create.  It will appear in the\n                            first available slot in which it fits, subject to\n                            additional restrictions specified in the other\n                            values of this tuning.\n                            ', manager=services.definition_manager()), part_index=OptionalTunable(description='\n                            If specified, restrict slot selection to the given\n                            part index.\n                            ', tunable=Tunable(tunable_type=int, default=0)), parent_slot=TunableVariant(description='\n                            Restrict slot selection to the given slot.\n                            ', bone_name=Tunable(description='\n                                Restrict slot by bone name.\n                                ', tunable_type=str, default='_ctnm_chr_'), slot_reference=TunableReference(description='\n                                Restrict slot by slot reference.\n                                ', manager=services.get_instance_manager(Types.SLOT_TYPE))), init_state_values=TunableList(description='\n                            List of states the children object will be set to.\n                            ', tunable=TunableStateValueReference()))))), 'init_actions': TunableTuple(description="\n            Actions to apply when this zone director starts up for the first\n            time on a zone. For example, the player loads into a zone and\n            ZoneDirectorA is chosen to run but ZoneDirectorB was previously\n            running on the zone. ZoneDirectorA's Init Actions will be applied.\n            The player then saves and loads back into the zone. Init Actions\n            will not be applied again.\n            ", stop_saved_situations=Tunable(description='\n                If enabled, any running situation saved on the zone will not be\n                loaded, so when the loading screen lifts, the only situations\n                running are those created during zone load (e.g. situations\n                created by this zone director).\n                ', tunable_type=bool, default=False), send_saved_npcs_home=Tunable(description="\n                If enabled, NPCs that do not live on the lot will be sent home\n                so that any Sims left on the lot will be the player's Sims,\n                the Sims that live on the zone, and any Sim spawned in by\n                situations (e.g. traveled Sims, bartenders).\n                ", tunable_type=bool, default=False)), 'venue_owed_payment_data': TunableTuple(description='\n            Data to handle payment owed if player travel away from current zone.\n            ', payment_succeed_notification=OptionalTunable(description='\n                A notification which pops up when payment owed from this zone\n                is deducted.\n                ', tunable=TunableUiDialogNotificationSnippet()), payment_fail_notification=OptionalTunable(description='\n                A notification which pops up when payment owed from this zone\n                fails to be deducted.\n                ', tunable=TunableUiDialogNotificationSnippet())), 'arrival_spawn_point_override': OptionalTunable(description='\n            If enabled, spawn points are different depending on\n            greeted/ungreeted status.\n            ', tunable=TunableTuple(player_greeted_spawn_point=TunableEnumWithFilter(tunable_type=Tag, default=Tag.INVALID, invalid_enums=(Tag.INVALID,), filter_prefixes=SPAWN_PREFIX), player_ungreeted_spawn_point=TunableEnumWithFilter(tunable_type=Tag, default=Tag.INVALID, invalid_enums=(Tag.INVALID,), filter_prefixes=SPAWN_PREFIX)))}
    resource_key = None

    def __init__(self):
        super().__init__()
        self._cleanup_actions = []
        self._traveled_sim_infos = set()
        self._zone_saved_sim_infos = set()
        self._plex_group_saved_sim_infos = set()
        self._open_street_saved_sim_infos = set()
        self._resident_sim_infos = set()
        self._injected_into_zone_sim_infos = set()
        self._zone_saved_sim_op = _ZoneSavedSimOp.MAINTAIN
        self._open_street_saved_sim_op = _OpenStreetSavedSimOp.MAINTAIN
        self.was_loaded = False
        self._open_street_director_manager = None

    @property
    def open_street_director(self):
        if self._open_street_director_manager is None:
            return
        return self._open_street_director_manager.open_street_director

    @property
    def open_street_manager(self):
        return self._open_street_director_manager

    @property
    def instance_name(self):
        return type(self).__name__

    def on_startup(self):
        super().on_startup()
        self.send_startup_telemetry_event()
        zone_director_handlers.log_zone_director_event(self, services.current_zone(), 'startup', services.venue_service().venue)
        self._create_automatic_objects()
        register_build_buy_exit_callback(self._create_automatic_objects)

    def send_startup_telemetry_event(self):
        pass

    def on_cleanup_zone_objects(self):
        cleanup = self.cleanup_zone_actions()
        cleanup.modify_objects()

    def prepare_lot(self):
        if self.was_loaded:
            logger.error('Zone director {} attempting to prepare lot on save/load. This should only happen the first time the lot is loaded into with the zone director.', self, owner='bhill')
            return
        cleanup_actions = []
        lot_preparation_log = []
        for lot_preparation in self.lot_preparations:
            num_changes = 0
            target_num_changes = lot_preparation.number_of_changes.random_int()
            if target_num_changes <= 0:
                pass
            else:
                all_objects = list(services.object_manager().values())
                random.shuffle(all_objects)
                for obj in all_objects:
                    if obj.is_sim:
                        pass
                    elif lot_preparation.on_lot_only and not obj.is_on_active_lot():
                        pass
                    else:
                        resolver = SingleObjectResolver(obj)
                        if not lot_preparation.tests.run_tests(resolver):
                            pass
                        else:
                            cleanup_action = lot_preparation.action.apply(obj, lot_preparation_log)
                            if cleanup_action is not None:
                                cleanup_actions.append(cleanup_action)
                                num_changes += 1
                                if num_changes == target_num_changes:
                                    break
                if target_num_changes != num_changes:
                    new_actions = lot_preparation.action.fill_quota(target_num_changes - num_changes, lot_preparation_log)
                    cleanup_actions.extend(new_actions)
        spawn_objects_log = []
        spawn_cleanup_action = self._spawn_objects(spawn_objects_log)
        if spawn_cleanup_action is not None:
            cleanup_actions.append(spawn_cleanup_action)
        zone_director_handlers.log_lot_preparations(self, services.current_zone(), services.venue_service().venue, lot_preparation_log)
        zone_director_handlers.log_spawn_objects(self, services.current_zone(), services.venue_service().venue, spawn_objects_log)
        for cleanup_action in reversed(cleanup_actions):
            self.add_cleanup_action(cleanup_action)

    def on_shutdown(self):
        super().on_shutdown()
        self.send_shutdown_telemetry_event()
        unregister_build_buy_exit_callback(self._create_automatic_objects)
        self.destroy_open_street_directors()

    def on_exit_buildbuy(self):
        super().on_exit_buildbuy()

    def send_shutdown_telemetry_event(self):
        pass

    def load(self, zone_director_proto, preserve_state):
        self._cleanup_actions = _load_cleanup_actions(zone_director_proto)
        if zone_director_proto.HasField('resource_key'):
            previous_resource_key = sims4.resources.get_key_from_protobuff(zone_director_proto.resource_key)
        else:
            previous_resource_key = None
        if preserve_state and previous_resource_key == self.resource_key:
            self.was_loaded = True
            if zone_director_proto.HasField('custom_data'):
                reader = DefaultPropertyStreamReader(zone_director_proto.custom_data)
            else:
                reader = None
            self._load_custom_zone_director(zone_director_proto, reader)
        else:
            self.process_cleanup_actions()

    def _load_custom_zone_director(self, zone_director_proto, reader):
        pass

    def save(self, zone_director_proto, open_street_proto):
        if self.resource_key is not None:
            zone_director_proto.resource_key = sims4.resources.get_protobuff_for_key(self.resource_key)
        _save_cleanup_actions(zone_director_proto, self._cleanup_actions)
        writer = sims4.PropertyStreamWriter()
        self._save_custom_zone_director(zone_director_proto, writer)
        data = writer.close()
        if writer.count > 0:
            zone_director_proto.custom_data = data
        if self.open_street_director is not None:
            open_street_director_proto = GameplaySaveData_pb2.OpenStreetDirectorData()
            self.open_street_director.save(open_street_director_proto)
            open_street_proto.open_street_director = open_street_director_proto

    def _save_custom_zone_director(self, zone_director_proto, writer):
        pass

    def handle_command(self, command, *_, **__):
        pass

    def add_cleanup_action(self, action):
        self._cleanup_actions.append(action)

    def process_cleanup_actions(self):
        old_cleanup_actions = self._cleanup_actions
        self._cleanup_actions = []
        for cleanup_action in old_cleanup_actions:
            try:
                cleanup_action.process_cleanup_action()
            except:
                logger.exception('Error running cleanup action {}', cleanup_action)

    def _create_automatic_objects(self):
        venue_tuning = services.venue_service().venue
        if venue_tuning is None:
            return
        starting_position = services.active_lot().get_default_position()
        object_manager = services.object_manager()
        for tag_pair in venue_tuning.automatic_objects:
            obj = None
            try:
                existing_objects = set(object_manager.get_objects_with_tag_gen(tag_pair.tag))
                obj = self._create_object(tag_pair.default_value, starting_position)
            except:
                logger.error('Automatic object {} could not be created in venue {} (zone: {}).', tag_pair.default_value, venue_tuning, services.current_zone_id())
                if obj is not None:
                    obj.destroy(cause='Failed to place automatic object required by venue.')

    def _create_object(self, definition, position, orientation=None, state_values=()):
        obj = create_object(definition)
        if obj is None:
            return
        starting_location = placement.create_starting_location(position=position, orientation=orientation)
        fgl_context = placement.create_fgl_context_for_object(starting_location, obj, ignored_object_ids=(obj.id,))
        (position, orientation) = placement.find_good_location(fgl_context)
        if position is not None:
            obj.location = sims4.math.Location(sims4.math.Transform(position, orientation), routing.SurfaceIdentifier(services.current_zone_id(), 0, routing.SurfaceType.SURFACETYPE_WORLD))
        else:
            obj.destroy()
            return
        for state in state_values:
            obj.set_state(state.state, state)
        return obj

    def _create_child_object(self, definition, parent, slot_types=None, bone_name_hash=None, state_values=()):
        for runtime_slot in parent.get_runtime_slots_gen(slot_types=slot_types, bone_name_hash=bone_name_hash):
            if runtime_slot.is_valid_for_placement(definition=definition):
                break
        return
        child = create_object(definition)
        runtime_slot.add_child(child)
        for state_value in state_values:
            child.set_state(state_value.state, state_value)
        return child

    def _spawn_objects(self, spawn_objects_log):
        spawned_objects = []
        lot = services.current_zone().lot
        for info in self.objects_to_spawn:
            position = sims4.math.Vector3(float(info.position.x), terrain.get_terrain_height(info.position.x, info.position.y), float(info.position.y))
            orientation = Quaternion.from_axis_angle(info.angle, UP_AXIS)
            lot_transform = sims4.math.Transform(position, orientation)
            world_transform = lot.convert_to_world_coordinates(lot_transform)
            obj = self._create_object(info.definition, world_transform.translation, orientation=world_transform.orientation, state_values=info.init_state_values)
            if obj is None:
                pass
            else:
                spawned_objects.append(obj)
                spawn_objects_log.append({'obj_id': str(obj.id), 'obj_def': info.definition.name, 'parent_id': 0, 'position': str(world_transform), 'states': str(info.init_state_values)})
                for child_info in info.children:
                    slot_owner = obj
                    if child_info.part_index is not None:
                        for obj_part in obj.parts:
                            if obj_part.subroot_index == child_info.part_index:
                                slot_owner = obj_part
                                break
                    if isinstance(child_info.parent_slot, str):
                        slot_types = None
                        bone_name_hash = hash32(child_info.parent_slot)
                    else:
                        slot_types = {child_info.parent_slot}
                        bone_name_hash = None
                    child = self._create_child_object(child_info.definition, slot_owner, slot_types=slot_types, bone_name_hash=bone_name_hash, state_values=child_info.init_state_values)
                    if child is not None:
                        spawned_objects.append(child)
                        spawn_objects_log.append({'obj_id': str(child.id), 'obj_def': child_info.definition.name, 'parent_id': str(obj.id), 'position': 0, 'states': str(child_info.init_state_values)})
        if spawned_objects:
            return DestroyObjects(objects_to_destroy=reversed(spawned_objects))

    def process_traveled_and_persisted_and_resident_sims(self, traveled_sim_infos, zone_saved_sim_infos, plex_group_saved_sim_infos, open_street_saved_sim_infos, injected_into_zone_sim_infos):
        self._zone_saved_sim_op = self._determine_zone_saved_sim_op()
        self._open_street_saved_sim_op = self._determine_open_street_saved_sim_op()
        self._traveled_sim_infos = set(traveled_sim_infos)
        self._zone_saved_sim_infos = set(zone_saved_sim_infos)
        self._plex_group_saved_sim_infos = set(plex_group_saved_sim_infos)
        self._open_street_saved_sim_infos = set(open_street_saved_sim_infos)
        self._resident_sim_infos = self._get_resident_sims()
        self._injected_into_zone_sim_infos = set(injected_into_zone_sim_infos)
        self._zone_saved_sim_infos.difference_update(self._traveled_sim_infos)
        self._open_street_saved_sim_infos.difference_update(self._traveled_sim_infos)
        self._injected_into_zone_sim_infos.difference_update(self._traveled_sim_infos)
        self._send_home_sims_who_overstayed()
        if not self.was_loaded:
            weather_service = services.weather_service()
            if weather_service is not None:
                sim_infos = set(self._traveled_sim_infos)
                sim_infos.update(self._resident_sim_infos)
                weather_service.process_weather_outfit_change(sim_infos)
        for sim_info in tuple(self._traveled_sim_infos):
            self._process_traveled_sim(sim_info)
        for sim_info in tuple(self._resident_sim_infos):
            self._process_resident_sim(sim_info)
        for sim_info in tuple(self._injected_into_zone_sim_infos):
            self._process_injected_sim(sim_info)
        for sim_info in tuple(self._plex_group_saved_sim_infos):
            self._process_plex_group_saved_sim(sim_info)
        for sim_info in tuple(self._zone_saved_sim_infos):
            self._process_zone_saved_sim(sim_info)
        for sim_info in tuple(self._open_street_saved_sim_infos):
            self._process_open_street_saved_sim(sim_info)

    def _determine_zone_saved_sim_op(self):
        if self.was_loaded or self.init_actions.send_saved_npcs_home:
            return _ZoneSavedSimOp.CLEAR
        current_zone = services.current_zone()
        if current_zone.lot_owner_household_changed_between_save_and_load() or current_zone.venue_type_changed_between_save_and_load():
            return _ZoneSavedSimOp.CLEAR
        if current_zone.active_household_changed_between_save_and_load() or services.current_zone().time_has_passed_in_world_since_zone_save():
            return _ZoneSavedSimOp.REINITIATE
        return _ZoneSavedSimOp.MAINTAIN

    def _determine_open_street_saved_sim_op(self):
        if self.was_loaded or self.init_actions.send_saved_npcs_home:
            return _OpenStreetSavedSimOp.CLEAR
        current_zone = services.current_zone()
        if current_zone.time_has_passed_in_world_since_open_street_save():
            return _OpenStreetSavedSimOp.CLEAR
        return _OpenStreetSavedSimOp.MAINTAIN

    def _request_spawning_of_sim_at_location(self, sim_info, sim_spawn_reason, startup_location=DEFAULT, spin_up_action=SimZoneSpinUpAction.NONE):
        if sim_info.is_baby:
            run_baby_spawn_behavior(sim_info)
        else:
            if startup_location is DEFAULT:
                startup_location = sim_info.startup_sim_location
            sim_spawn_request = sims.sim_spawner_service.SimSpawnRequest(sim_info, sim_spawn_reason, sims.sim_spawner_service.SimSpawnLocationStrategy(startup_location), from_load=True, spin_up_action=spin_up_action)
            services.sim_spawner_service().submit_request(sim_spawn_request)

    def _request_spawning_of_sim_at_spawn_point(self, sim_info, sim_spawn_reason, spawner_tags=DEFAULT, spawn_point_option=SpawnPointOption.SPAWN_SAME_POINT, spawn_action=None, spin_up_action=SimZoneSpinUpAction.NONE):
        if spawner_tags is DEFAULT:
            spawner_tags = (SpawnPoint.ARRIVAL_SPAWN_POINT_TAG,)
            if not sim_info.is_npc:
                is_greeted = services.get_zone_situation_manager().is_player_greeted()
                if is_greeted:
                    spawner_tags = (self.arrival_spawn_point_override.player_greeted_spawn_point,)
                else:
                    spawner_tags = (self.arrival_spawn_point_override.player_ungreeted_spawn_point,)
        if sim_info.is_baby:
            run_baby_spawn_behavior(sim_info)
        else:
            sim_spawn_request = sims.sim_spawner_service.SimSpawnRequest(sim_info, sim_spawn_reason, sims.sim_spawner_service.SimSpawnPointStrategy(spawner_tags, spawn_point_option, spawn_action), from_load=True, spin_up_action=spin_up_action)
            services.sim_spawner_service().submit_request(sim_spawn_request)

    def _send_home_sims_who_overstayed(self):
        for sim_info in tuple(itertools.chain(self._zone_saved_sim_infos, self._open_street_saved_sim_infos)):
            send_home = self._did_sim_overstay(sim_info)
            if send_home:
                self._send_sim_home(sim_info)

    def _did_sim_overstay(self, sim_info):
        if sim_info.is_selectable:
            return False
        if sim_info.lives_here:
            return False
        if sim_info.game_time_bring_home is None:
            return False
        else:
            time_to_expire = DateAndTime(sim_info.game_time_bring_home)
            if services.time_service().sim_now < time_to_expire:
                return False
        return True

    def _send_sim_home(self, sim_info):
        if not sim_info.lives_here:
            logger.debug('Sending home:{}', sim_info)
            self._traveled_sim_infos.discard(sim_info)
            self._zone_saved_sim_infos.discard(sim_info)
            self._open_street_saved_sim_infos.discard(sim_info)
            sim_info.inject_into_inactive_zone(sim_info.vacation_or_home_zone_id, skip_daycare=True)

    def _process_traveled_sim(self, sim_info):
        if sim_info.get_current_outfit()[0] == OutfitCategory.SLEEP:
            random_everyday_outfit = sim_info.get_random_outfit((OutfitCategory.EVERYDAY,))
            sim_info.set_current_outfit(random_everyday_outfit)
        if sim_info.is_toddler and get_restaurant_zone_director():
            resolver = SingleSimResolver(sim_info)
            dialog = RestaurantTuning.TODDLER_SENT_TO_DAYCARE_FOR_RESTAURANTS(sim_info, resolver)
            dialog.show_dialog()
            services.sim_info_manager().remove_sim_from_traveled_sims(sim_info.id)
            self._send_sim_home(sim_info)
            return
        plex_service = services.get_plex_service()
        location = sim_info.startup_sim_location
        if location is not None and sim_info.zone_id in plex_service.get_plex_zones_in_group(services.current_zone_id()) and plex_service.is_position_in_common_area_or_active_plex(location.world_transform.translation, location.level):
            self._request_spawning_of_sim_at_location(sim_info, sims.sim_spawner_service.SimSpawnReason.TRAVELING)
            return
        spawner_tags = self._get_spawner_tags_for_traveling_sim(sim_info.id)
        if spawner_tags is None:
            spawner_tags = DEFAULT
        self._request_spawning_of_sim_at_spawn_point(sim_info, sims.sim_spawner_service.SimSpawnReason.TRAVELING, spawner_tags)

    def _get_spawner_tags_for_traveling_sim(self, sim_id):
        situation_manager = services.get_zone_situation_manager()
        arriving_seed = situation_manager.get_arriving_seed_during_zone_spin()
        if arriving_seed is not None and arriving_seed.situation_type.use_spawner_tags_on_travel:
            guest_list = arriving_seed.guest_list
            guest_info = guest_list.get_guest_info_for_sim_id(sim_id)
            return guest_info.job_type.sim_spawner_tags

    def _get_resident_sims(self):
        return set()

    def _process_resident_sim(self, sim_info):
        pass

    def _process_injected_sim(self, sim_info):
        self._request_spawning_of_sim_at_spawn_point(sim_info, sims.sim_spawner_service.SimSpawnReason.DEFAULT, spin_up_action=sims.sim_info_types.SimZoneSpinUpAction.PREROLL)

    def _process_plex_group_saved_sim(self, sim_info):
        if self._zone_saved_sim_op != _ZoneSavedSimOp.MAINTAIN:
            return
        location = sim_info.startup_sim_location
        if location is None:
            return
        plex_service = services.get_plex_service()
        plex_zone_id = plex_service.get_plex_zone_at_position(location.world_transform.translation, location.level)
        if plex_zone_id is not None and plex_zone_id != services.current_zone_id():
            return
        self._on_maintain_zone_saved_sim(sim_info)

    def _process_zone_saved_sim(self, sim_info):
        if self._zone_saved_sim_op == _ZoneSavedSimOp.CLEAR:
            self._on_clear_zone_saved_sim(sim_info)
        elif self._zone_saved_sim_op == _ZoneSavedSimOp.REINITIATE:
            self._on_reinitiate_zone_saved_sim(sim_info)
        else:
            self._on_maintain_zone_saved_sim(sim_info)

    def _on_clear_zone_saved_sim(self, sim_info):
        if sim_info.is_selectable:
            self._request_spawning_of_sim_at_location(sim_info, sims.sim_spawner_service.SimSpawnReason.SAVED_ON_ZONE, spin_up_action=SimZoneSpinUpAction.PREROLL)
            return
        self._send_sim_home(sim_info)

    def _on_reinitiate_zone_saved_sim(self, sim_info):
        self._request_spawning_of_sim_at_location(sim_info, sims.sim_spawner_service.SimSpawnReason.SAVED_ON_ZONE, spin_up_action=SimZoneSpinUpAction.PREROLL)

    def _on_maintain_zone_saved_sim(self, sim_info):
        self._request_spawning_of_sim_at_location(sim_info, sims.sim_spawner_service.SimSpawnReason.SAVED_ON_ZONE, spin_up_action=SimZoneSpinUpAction.RESTORE_SI)

    def _process_open_street_saved_sim(self, sim_info):
        if self._open_street_saved_sim_op == _OpenStreetSavedSimOp.CLEAR:
            self._on_clear_open_street_saved_sim(sim_info)
        else:
            self._on_maintain_open_street_saved_sim(sim_info)

    def _on_clear_open_street_saved_sim(self, sim_info):
        if sim_info.is_selectable:
            self._request_spawning_of_sim_at_location(sim_info, sims.sim_spawner_service.SimSpawnReason.SAVED_ON_OPEN_STREETS)
            return
        self._send_sim_home(sim_info)

    def _on_maintain_open_street_saved_sim(self, sim_info):
        spin_up_action = SimZoneSpinUpAction.RESTORE_SI
        if sim_info not in self._traveled_sim_infos:
            spin_up_action = SimZoneSpinUpAction.PUSH_GO_HOME
        self._request_spawning_of_sim_at_location(sim_info, sims.sim_spawner_service.SimSpawnReason.SAVED_ON_OPEN_STREETS, spin_up_action=spin_up_action)

    def determine_which_situations_to_load(self):
        situation_manager = services.get_zone_situation_manager()
        arriving_seed = situation_manager.get_arriving_seed_during_zone_spin()
        if arriving_seed is not None:
            arriving_seed.allow_creation = self._decide_whether_to_load_arriving_situation_seed(arriving_seed)
        zone_seeds = situation_manager.get_zone_persisted_seeds_during_zone_spin_up()
        for seed in zone_seeds:
            seed.allow_creation = self._decide_whether_to_load_zone_situation_seed(seed)
        open_street_seeds = situation_manager.get_open_street_persisted_seeds_during_zone_spin_up()
        for seed in open_street_seeds:
            seed.allow_creation = self._decide_whether_to_load_open_street_situation_seed(seed)

    def get_user_controlled_sim_infos(self):
        return [sim_info for sim_info in itertools.chain(self._traveled_sim_infos, self._injected_into_zone_sim_infos, self._zone_saved_sim_infos, self._open_street_saved_sim_infos, self._resident_sim_infos) if not sim_info.is_npc]

    def _decide_whether_to_load_arriving_situation_seed(self, seed):
        if services.current_zone().id != seed.zone_id:
            logger.debug('Travel situation :{} not loaded. Expected zone :{} but is on zone:{}', seed.situation_type, seed.zone_id, services.current_zone().id)
            return False
        if seed.travel_time is None:
            logger.debug("Not loading traveled situation {} because it's missing travel_time")
            return False
        else:
            time_since_travel_seed_created = services.time_service().sim_now - seed.travel_time
            if time_since_travel_seed_created > date_and_time.TimeSpan.ZERO:
                logger.debug('Not loading traveled situation :{} because time has passed {}', seed.situation_type, time_since_travel_seed_created)
                return False
        return True

    def _decide_whether_to_load_zone_situation_seed(self, seed):
        if self.was_loaded or self.init_actions.stop_saved_situations:
            return False
        return seed.situation_type.should_seed_be_loaded(seed)

    def _decide_whether_to_load_open_street_situation_seed(self, seed):
        if self.was_loaded or self.init_actions.stop_saved_situations:
            return False
        return seed.situation_type.should_seed_be_loaded(seed)

    def create_situations_during_zone_spin_up(self):
        pass

    @property
    def forward_ungreeted_front_door_interactions_to_terrain(self):
        return True

    @property
    def should_create_venue_background_situation(self):
        return self.allow_venue_background_situations

    def handle_active_lot_changing_edge_cases(self):
        situation_manager = services.get_zone_situation_manager()
        if services.current_zone().time_has_passed_in_world_since_zone_save() or services.current_zone().active_household_changed_between_save_and_load():
            sim_infos_to_fix_up = []
            for sim_info in self._zone_saved_sim_infos:
                sim = sim_info.get_sim_instance()
                if sim is not None and sim_info.is_npc and not (sim_info.lives_here or situation_manager.get_situations_sim_is_in(sim)):
                    sim_infos_to_fix_up.append(sim_info)
            if sim_infos_to_fix_up:
                logger.debug('Fixing up npcs {} during zone fixup', sim_infos_to_fix_up, owner='sscholl')
                services.current_zone().venue_service.venue.zone_fixup(sim_infos_to_fix_up, purpose=NPCSummoningPurpose.ZONE_FIXUP)

    def _prune_stale_situations(self, situation_ids):
        situation_manager = services.get_zone_situation_manager()
        return [situation_id for situation_id in situation_ids if situation_id in situation_manager]

    def handle_sim_summon_request(self, sim_info, purpose):
        SimSpawner.spawn_sim(sim_info)

    def on_loading_screen_animation_finished(self):
        self._traveled_sim_infos.clear()
        self._zone_saved_sim_infos.clear()
        self._open_street_saved_sim_infos.clear()
        self._resident_sim_infos.clear()
        self._injected_into_zone_sim_infos.clear()

    def apply_zone_outfit(self, sim_info, situation):
        pass

    def get_zone_outfit(self, sim_info):
        return (None, None)

    def get_zone_dress_code(self):
        pass

    def zone_director_specific_destination_tests(self, sim, obj):
        return True

    def additional_social_picker_tests(self, actor, target):
        return True

    def disable_sim_affinity_posture_scoring(self, sim):
        return False

    @property
    def supports_open_street_director(self):
        return True

    def refresh_open_street_director_status(self):
        if self._open_street_director_manager is None:
            return
        if self.supports_open_street_director:
            if not self._open_street_director_manager.active:
                self._open_street_director_manager.activate()
        elif self._open_street_director_manager.active:
            self._open_street_director_manager.deactivate()

    def transfer_open_street_director(self, zone_director):
        self._open_street_director_manager = zone_director._open_street_director_manager
        zone_director._open_street_director_manager = None
        self.refresh_open_street_director_status()

    def setup_open_street_director_manager(self, initial_requests, prior_open_street_director_proto):
        self._open_street_director_manager = OpenStreetDirectorManager(prior_open_street_director_proto=prior_open_street_director_proto)
        for request in initial_requests:
            self.request_new_open_street_director(request)
        if self.supports_open_street_director:
            self._open_street_director_manager.activate(from_load=True)
        else:
            self._open_street_director_manager.deactivate(from_load=True)

    def request_new_open_street_director(self, open_street_director_request):
        if self._open_street_director_manager is not None:
            self._open_street_director_manager.add_open_street_director_request(open_street_director_request)

    def destroy_open_street_directors(self):
        if self._open_street_director_manager is not None:
            self._open_street_director_manager.destroy_all_requests()

    def destroy_current_open_street_director(self):
        if self._open_street_director_manager is not None:
            self._open_street_director_manager.shutdown_active_request()

    def on_spawn_sim_for_zone_spin_up_completed(self):
        pass

    def on_sim_added_to_skewer(self, sim_info):
        pass

    def on_zone_director_aspiration_completed(self, completed_aspiration, sim_info):
        pass

    @property
    def supported_business_types(self):
        return ()

    def supports_business_type(self, business_type:BusinessType):
        return business_type in self.supported_business_types

class CleanupAction:

    @classmethod
    def get_guid(cls):
        if not hasattr(cls, 'GUID'):
            raise NotImplementedError('Each cleanup action must define a 32-bit GUID class attribute')
        return cls.GUID

    def process_cleanup_action(self):
        pass

    def save(self, cleanup_action_proto):
        cleanup_action_proto.guid = self.get_guid()

    def load(self, cleanup_action_proto):
        logger.assert_raise(cleanup_action_proto.guid == self.get_guid(), 'Incorrect GUID {} for cleanup action {} (guid {})', cleanup_action_proto.guid, self, self.get_guid())

class DestroyObjects(CleanupAction):
    GUID = 150212831

    def __init__(self, objects_to_destroy=()):
        self.object_ids_to_destroy = [obj.id for obj in objects_to_destroy]

    def process_cleanup_action(self):
        zone = services.current_zone()
        object_manager = zone.object_manager
        inventory_manager = zone.inventory_manager
        objects_to_destroy = []
        for object_id in self.object_ids_to_destroy:
            obj = object_manager.get(object_id) or inventory_manager.get(object_id)
            if obj is not None:
                objects_to_destroy.append(obj)
        services.get_reset_and_delete_service().trigger_batch_destroy(objects_to_destroy)

    def save(self, cleanup_action_proto):
        super().save(cleanup_action_proto)
        cleanup_action_proto.object_ids.extend(self.object_ids_to_destroy)

    def load(self, cleanup_action_proto):
        super().load(cleanup_action_proto)
        self.object_ids_to_destroy = list(cleanup_action_proto.object_ids)

class DestroyObjectsOfType(CleanupAction):
    GUID = 1460378648

    def __init__(self):
        self.object_definitions_to_destroy = []

    def process_cleanup_action(self):
        zone = services.current_zone()
        object_manager = zone.object_manager
        inventory_manager = zone.inventory_manager
        definitions_to_destroy = set(self.object_definitions_to_destroy)
        objects_to_destroy = []
        for obj in itertools.chain(object_manager.values(), inventory_manager.values()):
            if obj.definition in definitions_to_destroy:
                objects_to_destroy.append(obj)
        services.get_reset_and_delete_service().trigger_batch_destroy(objects_to_destroy)

    def save(self, cleanup_action_proto):
        super().save(cleanup_action_proto)
        for object_definition in self.object_definitions_to_destroy:
            resource_key = sims4.resources.Key(sims4.resources.Types.OBJECTDEFINITION, object_definition.id, 0)
            key_proto = sims4.resources.get_protobuff_for_key(resource_key)
            cleanup_action_proto.resource_keys.append(key_proto)

    def load(self, cleanup_action_proto):
        super().load(cleanup_action_proto)
        object_definitions_to_destroy = []
        for key_proto in cleanup_action_proto.resource_keys:
            resource_key = sims4.resources.get_key_from_protobuff(key_proto)
            object_definition = services.definition_manager().get(resource_key.instance)
            if object_definition is not None:
                object_definitions_to_destroy.append(object_definition)
        self.object_definitions_to_destroy = object_definitions_to_destroy

class SetStateCleanup(CleanupAction):
    GUID = 3024953117

    def __init__(self, state_changes=()):
        self.object_and_state_to_value = {}
        for (obj, state, state_value) in state_changes:
            self.add_state_change(obj, state, state_value)

    def add_state_change(self, obj, state, state_value):
        self.object_and_state_to_value[(obj.id, state.guid64)] = state_value.guid64

    def process_cleanup_action(self):
        zone = services.current_zone()
        object_manager = zone.object_manager
        inventory_manager = zone.inventory_manager
        state_manager = services.get_instance_manager(sims4.resources.Types.OBJECT_STATE)
        for ((object_id, state_guid64), state_value_guid64) in self.object_and_state_to_value.items():
            obj = object_manager.get(object_id) or inventory_manager.get(object_id)
            if obj is None:
                pass
            else:
                state = state_manager.get(state_guid64)
                if state is None:
                    pass
                else:
                    state_value = state_manager.get(state_value_guid64)
                    if state_value is None:
                        pass
                    else:
                        obj.set_state(state, state_value, immediate=True)

    def save(self, cleanup_action_proto):
        super().save(cleanup_action_proto)
        for ((object_id, state_guid64), state_value_guid64) in self.object_and_state_to_value.items():
            cleanup_action_proto.object_ids.append(object_id)
            with distributor.rollback.ProtocolBufferRollback(cleanup_action_proto.states) as safe_proto:
                safe_proto.state_name_hash = state_guid64
                safe_proto.value_name_hash = state_value_guid64

    def load(self, cleanup_action_proto):
        super().load(cleanup_action_proto)
        self.object_and_state_to_value = {}
        for (object_id, state_info) in zip(cleanup_action_proto.object_ids, cleanup_action_proto.states):
            self.object_and_state_to_value[(object_id, state_info.state_name_hash)] = state_info.value_name_hash

class CleanScorchMark(CleanupAction):
    GUID = 150212820

    def __init__(self, position=None, level=None):
        self.position = position
        self.level = level

    def save(self, proto):
        super().save(proto)
        proto.location = Routing_pb2.Location()
        proto.location.transform.translation.x = self.position.x
        proto.location.transform.translation.y = self.position.y
        proto.location.transform.translation.z = self.position.z
        proto.location.surface_id.secondary_id = self.level

    def load(self, proto):
        super().load(proto)
        self.position = sims4.math.Vector3(proto.location.transform.translation.x, proto.location.transform.translation.y, proto.location.transform.translation.z)
        self.level = proto.location.surface_id.secondary_id

    def process_cleanup_action(self):
        FireService.remove_scorch_mark(self.position, self.level)

def _load_cleanup_actions(zone_director_proto):
    cleanup_actions = []
    subclasses = sims4.utils.all_subclasses(CleanupAction)
    guid_to_action = {subclass.get_guid(): subclass for subclass in subclasses}
    for cleanup_action_proto in zone_director_proto.cleanup_actions:
        action_guid = 0
        try:
            action_guid = cleanup_action_proto.guid
            action_class = guid_to_action.get(action_guid)
            if action_class is not None:
                cleanup_action = action_class()
                cleanup_action.load(cleanup_action_proto)
                cleanup_actions.append(cleanup_action)
        except:
            logger.exception('Error restoring cleanup action with GUID {}', action_guid)
    return cleanup_actions

def _save_cleanup_actions(zone_director_proto, cleanup_actions):
    for cleanup_action in cleanup_actions:
        with distributor.rollback.ProtocolBufferRollback(zone_director_proto.cleanup_actions) as cleanup_action_proto:
            cleanup_action.save(cleanup_action_proto)
