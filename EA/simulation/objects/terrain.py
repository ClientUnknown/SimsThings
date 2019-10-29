from _sims4_collections import frozendictfrom _weakrefset import WeakSetfrom weakref import WeakKeyDictionaryfrom protocolbuffers import InteractionOps_pb2, DistributorOps_pb2from animation.posture_manifest_constants import STAND_OR_MOVING_STAND_POSTURE_MANIFESTfrom clock import ClockSpeedModefrom distributor.ops import GenericProtocolBufferOpfrom event_testing.results import TestResultfrom interactions import ParticipantTypefrom interactions.aop import AffordanceObjectPairfrom interactions.base.basic import TunableBasicContentSetfrom interactions.base.immediate_interaction import ImmediateSuperInteractionfrom interactions.base.super_interaction import SuperInteractionfrom interactions.context import InteractionContextfrom objects.base_object import BaseObjectfrom objects.components.state import TunableStateValueReferencefrom objects.object_enums import PersistenceTypefrom objects.proxy import ProxyObjectfrom objects.script_object import ScriptObjectfrom postures.posture_graph import supress_posture_graph_buildfrom server.pick_info import PICK_UNGREETED, PickInfo, PickTypefrom services import definition_managerfrom sims.baby.baby_utils import create_and_place_babyfrom sims.pregnancy.pregnancy_tracker import PregnancyTrackerfrom sims.sim_info_types import Gender, Age, Speciesfrom sims4.hash_util import hash32from sims4.math import Vector2, Vector3, Quaternion, Transform, Locationfrom sims4.repr_utils import standard_repr, standard_float_tuple_reprfrom sims4.resources import Typesfrom sims4.tuning.geometric import TunableVector2from sims4.tuning.instances import lock_instance_tunablesfrom sims4.tuning.tunable import TunableReference, Tunable, TunableTuple, TunableList, TunableRange, TunableEnumEntry, OptionalTunablefrom sims4.utils import setdefault_callable, classproperty, flexmethod, constpropertyimport build_buyimport cachesimport distributorimport objects.systemimport routingimport servicesimport sims.sim_spawnerimport sims4.logimport sims4.mathimport terrainlogger = sims4.log.Logger('Terrain')
def get_venue_instance_from_pick_location(pick):
    if pick is None:
        return
    lot_id = pick.lot_id
    if lot_id is None:
        return
    else:
        persistence_service = services.get_persistence_service()
        lot_owner_info = persistence_service.get_lot_proto_buff(lot_id)
        if lot_owner_info is not None:
            venue_key = lot_owner_info.venue_key
            venue_instance = services.get_instance_manager(sims4.resources.Types.VENUE).get(venue_key)
            return venue_instance

class TerrainInteractionMixin:
    POSTURE_MANIFEST = STAND_OR_MOVING_STAND_POSTURE_MANIFEST

    @classmethod
    def _get_target_position_surface_and_test_off_lot(cls, target, context):
        (position, surface) = (None, None)
        if target is not None or context.pick is not None:
            (position, surface) = cls._get_position_and_surface(target, context)
            if position is None:
                return (position, surface, TestResult(False, 'Cannot Travel without a pick or target.'))
            zone = services.current_zone()
            if context.sim is not target and zone.lot.is_position_on_lot(position):
                return (position, surface, TestResult(False, 'Cannot Travel inside the bounds of the zone!'))
        return (position, surface, TestResult.TRUE)

    @classmethod
    def _get_position_and_surface(cls, target, context):
        if context.pick is not None:
            return (context.pick.location, context.pick.routing_surface)
        elif target is not None:
            return (target.position, target.routing_surface)
        return (None, None)

    @classmethod
    def _get_level_of_target(cls, target, context):
        if target is not None:
            return target.level
        if context.pick is not None:
            return context.pick.level
        if context.sim is not None:
            return context.sim.level
        logger.error('terrain._get_level_of_target() could not find a target with a level, returning 0')
        return 0

    @classmethod
    def _define_supported_postures(cls):
        supported_postures = super()._define_supported_postures()
        if supported_postures:
            return supported_postures
        return frozendict({ParticipantType.Actor: cls.POSTURE_MANIFEST})

    @classmethod
    def supports_posture_type(cls, posture_type, *args, **kwargs):
        if not posture_type.mobile:
            return False
        return super().supports_posture_type(posture_type, *args, **kwargs)

    @flexmethod
    def constraint_gen(cls, inst, sim, target, participant_type=ParticipantType.Actor):
        inst_or_cls = cls if inst is None else inst
        for constraint in inst_or_cls._constraint_gen(sim, target, participant_type):
            constraint = constraint.get_multi_surface_version()
            yield constraint

class TerrainSuperInteraction(TerrainInteractionMixin, SuperInteraction):
    INSTANCE_TUNABLES = {'basic_content': TunableBasicContentSet(one_shot=True, no_content=True, default='no_content')}

    @classmethod
    def _constraint_gen(cls, *args, **kwargs):
        for constraint in super()._constraint_gen(*args, **kwargs):
            yield constraint
        zone = services.current_zone()
        if zone is not None:
            yield zone.get_spawn_point_ignore_constraint()
lock_instance_tunables(TerrainSuperInteraction, basic_reserve_object=None, basic_focus=None)
class TerrainImmediateSuperInteraction(TerrainInteractionMixin, ImmediateSuperInteraction):
    INSTANCE_SUBCLASSES_ONLY = True

class TravelMixin:

    def __init__(self, *args, to_zone_id=0, **kwargs):
        super().__init__(*args, to_zone_id=to_zone_id, **kwargs)
        self.to_zone_id = to_zone_id

    @classmethod
    def travel_test(cls, context):
        return TestResult.TRUE

    @classmethod
    def travel_pick_info_test(cls, target, context, **kwargs):
        (position, surface, result) = cls._get_target_position_surface_and_test_off_lot(target, context)
        if not result:
            return result
        location = routing.Location(position, sims4.math.Quaternion.IDENTITY(), surface)
        routable = routing.test_connectivity_permissions_for_handle(routing.connectivity.Handle(location), context.sim.routing_context)
        if routable:
            return TestResult(False, 'Cannot Travel from routable terrain !')
        result = cls.travel_test(context)
        if not result:
            return result
        to_zone_id = context.pick.get_zone_id_from_pick_location()
        if to_zone_id is None:
            return TestResult(False, 'Could not resolve lot id: {} into a valid zone id.', context.pick.lot_id)
        return TestResult.TRUE

    def show_travel_dialog(self):
        if self.sim.client is None:
            return
        travel_info = InteractionOps_pb2.TravelMenuCreate()
        travel_info.sim_id = self.sim.sim_id
        travel_info.selected_lot_id = self.to_zone_id
        travel_info.selected_world_id = self._kwargs.get('world_id', 0)
        travel_info.selected_lot_name = self._kwargs.get('lot_name', '')
        travel_info.friend_account = self._kwargs.get('friend_account', '')
        system_distributor = distributor.system.Distributor.instance()
        system_distributor.add_op_with_no_owner(GenericProtocolBufferOp(DistributorOps_pb2.Operation.TRAVEL_MENU_SHOW, travel_info))

class TravelSuperInteraction(TravelMixin, TerrainSuperInteraction):
    INSTANCE_SUBCLASSES_ONLY = True

    @classmethod
    def _test(cls, target, context, **kwargs):
        (position, _, result) = cls._get_target_position_surface_and_test_off_lot(target, context)
        if not result:
            return result
        if position is not None and not terrain.is_position_in_street(position):
            return TestResult(False, 'Cannot Travel from terrain outside of the street!')
        result = cls.travel_test(context)
        if not result:
            return result
        return TestResult.TRUE

    def _run_interaction_gen(self, timeline):
        if not services.get_persistence_service().is_save_locked():
            self.show_travel_dialog()
            services.game_clock_service().set_clock_speed(ClockSpeedMode.PAUSED)

class GoHereSuperInteraction(TerrainSuperInteraction):
    _ignores_spawn_point_footprints = True

    @classmethod
    def _test(cls, target, context, **kwargs):
        (position, surface) = cls._get_position_and_surface(target, context)
        if position is None:
            return TestResult(False, 'Cannot go here without a pick or target.')
        if context.pick is not None and context.pick.pick_type == PickType.PICK_POOL_EDGE:
            return TestResult.TRUE
        plex_service = services.get_plex_service()
        if plex_service.is_active_zone_a_plex():
            plex_zone_id_at_pick = plex_service.get_plex_zone_at_position(position, surface.secondary_id)
            if plex_zone_id_at_pick is not None and plex_zone_id_at_pick != services.current_zone_id():
                return TestResult(False, 'Pick point in inactive plex')
        routing_location = routing.Location(position, sims4.math.Quaternion.IDENTITY(), surface)
        routing_context = context.sim.get_routing_context()
        objects_to_ignore = set()
        if target is not None and target.is_sim:
            posture_target = target.posture_target
            if posture_target is not None:
                objects_to_ignore.update(posture_target.parenting_hierarchy_gen())
        if context.sim is not None:
            posture_target = context.sim.posture_target
            if posture_target.vehicle_component is not None:
                posture_target = posture_target.part_owner if posture_target.is_part else posture_target
                objects_to_ignore.add(posture_target)
        try:
            for obj in objects_to_ignore:
                footprint_component = obj.footprint_component
                if footprint_component is not None:
                    routing_context.ignore_footprint_contour(footprint_component.get_footprint_id())
            if not routing.test_connectivity_permissions_for_handle(routing.connectivity.Handle(routing_location), routing_context):
                return TestResult(False, 'Cannot GoHere! Unroutable area.')
        finally:
            for obj in objects_to_ignore:
                footprint_component = obj.footprint_component
                if footprint_component is not None:
                    routing_context.remove_footprint_contour_override(footprint_component.get_footprint_id())
        return TestResult.TRUE

    @classmethod
    def potential_interactions(cls, target, context, **kwargs):
        (position, surface) = cls._get_position_and_surface(target, context)
        main_group = context.sim.get_visible_group()
        group_constraint = next(iter(main_group.get_constraint(context.sim)))
        for constraint in group_constraint:
            group_geometry = constraint.geometry
            if not group_geometry is not None or group_geometry.contains_point(position):
                yield AffordanceObjectPair(cls, target, cls, None, ignore_party=True, **kwargs)
                return
        for aop in cls.get_rallyable_aops_gen(target, context, **kwargs):
            yield aop
        if not (position is not None and (context is not None and (context.sim is not None and main_group is not None)) and (main_group.is_solo or group_constraint is not None and group_constraint.routing_surface == surface and cls._can_rally(context)) and cls.only_available_as_rally):
            yield cls.generate_aop(target, context, **kwargs)

    @classmethod
    def create_special_load_target(cls, sim):
        target = objects.terrain.TerrainPoint(sim.sim_info.startup_sim_location)
        return target

    @classmethod
    def create_load_context(cls, sim, source, priority):
        location = sim.sim_info.startup_sim_location
        target = objects.terrain.TerrainPoint(location)
        pick_type = PickType.PICK_TERRAIN
        if build_buy.is_location_pool(sim.zone_id, location.transform.translation, location.level):
            pick_type = PickType.PICK_POOL_SURFACE
        pick = PickInfo(pick_type=pick_type, target=target, location=location.transform.translation, routing_surface=location.routing_surface)
        context = InteractionContext(sim, source, priority, pick=pick, restored_from_load=True)
        return context

class DebugSetupLotInteraction(TerrainImmediateSuperInteraction):
    INSTANCE_TUNABLES = {'setup_lot_destroy_old_objects': Tunable(bool, False, description='Destroy objects previously created by this interaction.'), 'setup_lot_objects': TunableList(TunableTuple(definition=TunableReference(definition_manager()), position=TunableVector2(Vector2.ZERO()), angle=TunableRange(int, 0, -360, 360), children=TunableList(TunableTuple(definition=TunableReference(definition_manager(), description='The child object to create.  It will appear in the first available slot in which it fits, subject to additional restrictions specified in the other values of this tuning.'), part_index=OptionalTunable(Tunable(int, 0, description='If specified, restrict slot selection to the given part index.')), bone_name=OptionalTunable(Tunable(str, '_ctnm_chr_', description='If specified, restrict slot selection to one with this exact bone name.')), slot_type=OptionalTunable(TunableReference(manager=services.get_instance_manager(Types.SLOT_TYPE), description='If specified, restrict slot selection to ones that support this type of slot.')), init_state_values=TunableList(description='\n                                List of states the children object will be set to.\n                                ', tunable=TunableStateValueReference()))), init_state_values=TunableList(description='\n                    List of states the created object will be pushed to.\n                    ', tunable=TunableStateValueReference())))}
    _zone_to_cls_to_created_objects = WeakKeyDictionary()

    @classproperty
    def destroy_old_objects(cls):
        return cls.setup_lot_destroy_old_objects

    @classproperty
    def created_objects(cls):
        created_objects = cls._zone_to_cls_to_created_objects.setdefault(services.current_zone(), {})
        return setdefault_callable(created_objects, cls, WeakSet)

    def _run_interaction_gen(self, timeline):
        with supress_posture_graph_build():
            if self.destroy_old_objects:
                while self.created_objects:
                    obj = self.created_objects.pop()
                    obj.destroy(source=self, cause='Destroying old objects in setup debug lot.')
            position = self.context.pick.location
            self.spawn_objects(position)
        return True

    def _create_object(self, definition_id, position=Vector3.ZERO(), orientation=Quaternion.IDENTITY(), level=0, owner_id=0):
        obj = objects.system.create_object(definition_id)
        if obj is not None:
            transform = Transform(position, orientation)
            location = Location(transform, self.context.pick.routing_surface)
            obj.location = location
            obj.set_household_owner_id(owner_id)
            self.created_objects.add(obj)
        return obj

    def spawn_objects(self, position):
        root = sims4.math.Vector3(position.x, position.y, position.z)
        zone = services.current_zone()
        lot = zone.lot
        owner_id = lot.owner_household_id
        if not self.contained_in_lot(lot, root):
            closest_point = self.find_nearest_point_on_lot(lot, root)
            if closest_point is None:
                return False
            radius = (self.top_right_pos - self.bottom_left_pos).magnitude_2d()/2
            root = closest_point + sims4.math.vector_normalize(sims4.math.vector_flatten(lot.center) - closest_point)*(radius + 1)
            if not self.contained_in_lot(lot, root):
                sims4.log.warn('Placement', "Placed the lot objects but the entire bounding box isn't inside the lot. This is ok. If you need them to be inside the lot run the interaction again at a diffrent location.")

        def _generate_vector(offset_x, offset_z):
            ground_obj = services.terrain_service.terrain_object()
            ret_vector = sims4.math.Vector3(root.x + offset_x, root.y, root.z + offset_z)
            ret_vector.y = ground_obj.get_height_at(ret_vector.x, ret_vector.z)
            return ret_vector

        def _generate_quat(rot):
            return sims4.math.Quaternion.from_axis_angle(rot, sims4.math.Vector3(0, 1, 0))

        for info in self.setup_lot_objects:
            new_pos = _generate_vector(info.position.x, info.position.y)
            new_rot = _generate_quat(sims4.math.PI/180*info.angle)
            new_obj = self._create_object(info.definition, new_pos, new_rot, owner_id=owner_id)
            if new_obj is None:
                sims4.log.error('SetupLot', 'Unable to create object: {}', info)
            else:
                for state_value in info.init_state_values:
                    new_obj.set_state(state_value.state, state_value)
                for child_info in info.children:
                    slot_owner = new_obj
                    if child_info.part_index is not None:
                        for obj_part in new_obj.parts:
                            if obj_part.subroot_index == child_info.part_index:
                                slot_owner = obj_part
                                break
                    bone_name_hash = None
                    if child_info.bone_name is not None:
                        bone_name_hash = hash32(child_info.bone_name)
                    slot_type = None
                    if child_info.slot_type is not None:
                        slot_type = child_info.slot_type
                    for runtime_slot in slot_owner.get_runtime_slots_gen(slot_types={slot_type}, bone_name_hash=bone_name_hash):
                        if runtime_slot.is_valid_for_placement(definition=child_info.definition):
                            break
                    sims4.log.error('SetupLot', 'Unable to find slot for child object: {}', child_info)
                    child = self._create_object(child_info.definition, owner_id=owner_id)
                    if child is None:
                        sims4.log.error('SetupLot', 'Unable to create child object: {}', child_info)
                    else:
                        runtime_slot.add_child(child)
                        for state_value in child_info.init_state_values:
                            child.set_state(state_value.state, state_value)

    def contained_in_lot(self, lot, root):
        self.find_corner_points(root)
        return True

    def find_corner_points(self, root):
        max_x = 0
        min_x = 0
        max_z = 0
        min_z = 0
        for info in self.setup_lot_objects:
            if info.position.x > max_x:
                max_x = info.position.x
            if info.position.x < min_x:
                min_x = info.position.x
            if info.position.y > max_z:
                max_z = info.position.y
            if info.position.y < min_z:
                min_z = info.position.y
        self.top_right_pos = sims4.math.Vector3(root.x + max_x, root.y, root.z + max_z)
        self.bottom_right_pos = sims4.math.Vector3(root.x + max_x, root.y, root.z + min_z)
        self.top_left_pos = sims4.math.Vector3(root.x + min_x, root.y, root.z + max_z)
        self.bottom_left_pos = sims4.math.Vector3(root.x + min_x, root.y, root.z + min_z)

    def find_nearest_point_on_lot(self, lot, root):
        lot_corners = lot.corners
        segments = [(lot_corners[0], lot_corners[1]), (lot_corners[1], lot_corners[2]), (lot_corners[2], lot_corners[3]), (lot_corners[3], lot_corners[1])]
        dist = 0
        closest_point = None
        for segment in segments:
            new_point = sims4.math.get_closest_point_2D(segment, root)
            new_distance = (new_point - root).magnitude()
            if dist == 0:
                dist = new_distance
                closest_point = new_point
            elif new_distance < dist:
                dist = new_distance
                closest_point = new_point
        return closest_point

class DebugCreateSimWithGenderAndAgeInteraction(TerrainImmediateSuperInteraction):
    INSTANCE_TUNABLES = {'gender': TunableEnumEntry(description='\n            The gender of the Sim to be created.\n            ', tunable_type=Gender, default=Gender.MALE), 'age': TunableEnumEntry(description='\n            The age of the Sim to be created.\n            ', tunable_type=Age, default=Age.ADULT), 'species': TunableEnumEntry(description='\n            The species of the Sim to be created.\n            ', tunable_type=Species, default=Species.HUMAN, invalid_enums=(Species.INVALID,)), 'breed_picker': OptionalTunable(description='\n            Breed picker to use if using a non-human species.\n            \n            If disabled, breed will be random.\n            ', tunable=TunableReference(manager=services.get_instance_manager(sims4.resources.Types.INTERACTION), class_restrictions=('BreedPickerSuperInteraction',), allow_none=True))}

    def _run_interaction_gen(self, timeline):
        if self.species == Species.HUMAN or self.breed_picker is None:
            position = self.context.pick.location
            routing_surface = self.context.pick.routing_surface
            actor_sim_info = self.sim.sim_info
            household = actor_sim_info.household if self.age == Age.BABY else None
            sim_creator = sims.sim_spawner.SimCreator(age=self.age, gender=self.gender, species=self.species)
            (sim_info_list, _) = sims.sim_spawner.SimSpawner.create_sim_infos((sim_creator,), household=household, account=actor_sim_info.account, zone_id=actor_sim_info.zone_id, creation_source='cheat: DebugCreateSimInteraction', is_debug=True)
            sim_info = sim_info_list[0]
            if sim_info.age == Age.BABY:
                PregnancyTracker.initialize_sim_info(sim_info, actor_sim_info, None)
                create_and_place_baby(sim_info, position=position, routing_surface=routing_surface)
            else:
                sims.sim_spawner.SimSpawner.spawn_sim(sim_info, sim_position=position, is_debug=True)
        else:
            self.sim.push_super_affordance(self.breed_picker, self.target, self.context, picked_object=self.target, age=self.age, gender=self.gender, species=self.species)
        return True

class Terrain(ScriptObject):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._raycast_context = routing.PathPlanContext()
        self._raycast_context.footprint_key = sims.sim_info.SimInfo.get_sim_definition(Species.HUMAN).get_footprint(0)
        self._raycast_context.agent_id = 0
        self._raycast_context.agent_radius = routing.get_default_agent_radius()
        self._raycast_context.set_key_mask(routing.FOOTPRINT_KEY_ON_LOT | routing.FOOTPRINT_KEY_OFF_LOT)

    @BaseObject.visible_to_client.getter
    def visible_to_client(self):
        return True

    @property
    def persistence_group(self):
        pass

    def raycast_context(self, for_carryable=False):
        return self._raycast_context

    def get_height_at(self, x, z):
        return terrain.get_terrain_height(x, z)

    def get_routing_surface_height_at(self, x, z, routing_surface):
        if routing_surface is None:
            return 0
        return terrain.get_lot_level_height(x, z, routing_surface.secondary_id, routing_surface.primary_id, routing_surface.type)

    def get_routing_surface_height_and_surface_object_at(self, x, z, routing_surface):
        if routing_surface is None:
            return (0, 0)
        return terrain.get_lot_level_height_and_surface_object(x, z, routing_surface.secondary_id, routing_surface.primary_id, routing_surface.type)

    def get_center(self):
        return services.active_lot().center

    def is_position_on_lot(self, position):
        return services.active_lot().is_position_on_lot(position)

    def _get_ungreeted_overrides(self, context, **kwargs):
        zone_director = services.venue_service().get_zone_director()
        if not zone_director.forward_ungreeted_front_door_interactions_to_terrain:
            return
        if context.pick.pick_type not in PICK_UNGREETED:
            return
        if context.pick.lot_id and context.pick.lot_id != services.active_lot().lot_id:
            return
        if not services.get_zone_situation_manager().is_player_waiting_to_be_greeted():
            return
        front_door = services.get_door_service().get_front_door()
        if front_door is None:
            return
        yield from front_door.potential_interactions(context, **kwargs)

    def potential_interactions(self, context, **kwargs):
        yield from super().potential_interactions(context, **kwargs)
        yield from self._get_ungreeted_overrides(context, **kwargs)

    @property
    def routing_location(self):
        lot = services.active_lot()
        return routing.Location(lot.position, orientation=lot.orientation, routing_surface=routing.SurfaceIdentifier(services.current_zone().id, 0, routing.SurfaceType.SURFACETYPE_WORLD))

    def get_routing_location_for_transform(self, transform, **__):
        return routing.Location(transform.translation, transform.orientation, routing_surface=self.routing_location.routing_surface)

    def populate_localization_token(self, token):
        pass

    def register_on_location_changed(self, callback):
        pass

    def unregister_on_location_changed(self, callback):
        pass

    check_line_of_sight = caches.uncached(ScriptObject.check_line_of_sight)
lock_instance_tunables(Terrain, _persistence=PersistenceType.NONE, _world_file_object_persists=False, provides_terrain_interactions=False)
class _LocationPoint(ProxyObject):
    _unproxied_attributes = ProxyObject._unproxied_attributes | {'_pick_location'}

    def __new__(cls, location, proxy_obj, *args, **kwargs):
        return super().__new__(cls, proxy_obj, *args, **kwargs)

    def __init__(self, location, proxy_obj, *args, **kwargs):
        super().__init__(proxy_obj, *args, **kwargs)
        self._pick_location = location

    @classmethod
    def create_for_position_and_orientation(cls, position, routing_surface):
        pick_location = sims4.math.Location(sims4.math.Transform(position), routing_surface)
        return cls(pick_location)

    def __repr__(self):
        return standard_repr(self, standard_float_tuple_repr(*self.position))

    @property
    def location(self):
        return self._pick_location

    @property
    def transform(self):
        return self._pick_location.transform

    @property
    def position(self):
        return self.transform.translation

    @property
    def orientation(self):
        return self.transform.orientation

    @property
    def forward(self):
        return self.transform.orientation.transform_vector(sims4.math.Vector3.Z_AXIS())

    @property
    def routing_surface(self):
        return self._pick_location.routing_surface

    def is_routing_surface_overlapped_at_position(self, position):
        return False

    @property
    def provided_routing_surface(self):
        pass

    @property
    def level(self):
        if self.routing_surface is None:
            return
        return self.routing_surface.secondary_id

    @property
    def intended_transform(self):
        return self.transform

    @property
    def intended_position(self):
        return self.position

    @property
    def intended_forward(self):
        return self.forward

    @property
    def intended_routing_surface(self):
        return self.routing_surface

    @property
    def is_part(self):
        return False

    def get_or_create_routing_context(self):
        pass

    @property
    def routing_location(self):
        return routing.Location(self._pick_location.transform.translation, orientation=self._pick_location.transform.orientation, routing_surface=self._pick_location.routing_surface)

    def check_line_of_sight(self, transform, verbose=False, **kwargs):
        (result, _) = Terrain.check_line_of_sight(self, transform, verbose=True, **kwargs)
        if result == routing.RAYCAST_HIT_TYPE_IMPASSABLE:
            result = routing.RAYCAST_HIT_TYPE_NONE
        if verbose:
            return (result, 0)
        return (result == routing.RAYCAST_HIT_TYPE_NONE, 0)

    @property
    def routing_context(self):
        pass

    @property
    def footprint_polygon(self):
        return sims4.geometry.CompoundPolygon([sims4.geometry.Polygon((self.position,))])

    @property
    def object_radius(self):
        return 0.0

    @object_radius.setter
    def object_radius(self, value):
        logger.error('Object radius set on proxy: {}', self)

    @property
    def connectivity_handles(self):
        pass

    @property
    def part_suffix(self):
        pass

    @property
    def children(self):
        return ()

    def get_users(self, *args, **kwargs):
        return ()

    @constproperty
    def is_sim():
        return False

    @constproperty
    def is_terrain():
        return True

    def is_hidden(self):
        return False

    def is_outside(self):
        return build_buy.is_location_outside(services.current_zone_id(), self.position, self.level)

    def is_on_natural_ground(self):
        return build_buy.is_location_natural_ground(services.current_zone_id(), self.position, self.level)

    @caches.cached(maxsize=10)
    def is_on_active_lot(self, tolerance=0):
        lot = services.active_lot()
        return lot.is_position_on_lot(self.position, tolerance)

class TerrainPoint(_LocationPoint):

    def __new__(cls, location):
        return super().__new__(cls, location, services.terrain_service.terrain_object())

    def __init__(self, location):
        super().__init__(location, services.terrain_service.terrain_object())

class OceanPoint(_LocationPoint):

    def __new__(cls, location):
        return super().__new__(cls, location, services.terrain_service.ocean_object())

    def __init__(self, location):
        super().__init__(location, services.terrain_service.ocean_object())

class PoolPoint(_LocationPoint):

    def __new__(cls, location, pool):
        return super().__new__(cls, location, pool)

    def __init__(self, location, pool):
        super().__init__(location, pool)
