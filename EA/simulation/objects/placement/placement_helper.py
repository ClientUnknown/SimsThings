from interactions import ParticipantTypefrom objects import ALL_HIDDEN_REASONSfrom placement import FGLSearchFlag, FGLSearchFlagsDefault, create_starting_location, create_fgl_context_for_object_off_lot, create_fgl_context_for_object, find_good_locationfrom routing import SurfaceType, SurfaceIdentifierfrom sims4 import randomfrom sims4.random import pop_weightedfrom sims4.tuning.geometric import TunableVector3from sims4.tuning.tunable import AutoFactoryInit, HasTunableSingletonFactory, TunableEnumEntry, TunableVariant, TunableTuple, OptionalTunable, TunableInterval, TunableAngle, Tunable, TunableReference, TunableList, TunableFactory, TunableEnumSetfrom tag import TunableTagsfrom tunable_multiplier import TunableMultiplierfrom world.lot_enums import LotPositionStrategyfrom world.terrain_enums import TerrainTagimport servicesimport sims4.math
class _ObjectsFromParticipant(HasTunableSingletonFactory, AutoFactoryInit):

    @TunableFactory.factory_option
    def participant_type_default(participant_type_default=ParticipantType.Actor):
        return {'participant': TunableEnumEntry(description='\n                The participant that determines the object to be used for the\n                specified placement strategy.\n                ', tunable_type=ParticipantType, default=participant_type_default)}

    def get_objects_gen(self, resolver):
        yield resolver.get_participant(self.participant)

class _ObjectsFromTags(HasTunableSingletonFactory, AutoFactoryInit):
    FACTORY_TUNABLES = {'tags': TunableTags(description='\n            For each tag, in order, gather objects that match that have that\n            tag. If the placement fails, consider another object, then consider\n            objects for the next tag.\n            ')}

    def get_objects_gen(self, resolver):
        for tag in self.tags:
            yield from services.object_manager().get_objects_with_tag_gen(tag)

class _LocationFromLot(HasTunableSingletonFactory, AutoFactoryInit):
    FACTORY_TUNABLES = {'lot_location_strategy': TunableEnumEntry(description='\n            Strategy for how we will determine a location on the lot.\n            Default: Tries to retrieve the position of the front door, otherwise\n            uses an arbitrary corner (will always be the same corner)\n            Random: Retrieves a random point on the lot\n            ', tunable_type=LotPositionStrategy, default=LotPositionStrategy.DEFAULT)}

    def get_objects_gen(self, resolver):
        lot = services.active_lot()
        pos = lot.get_lot_position(self.lot_location_strategy)
        from objects.terrain import TerrainPoint
        yield TerrainPoint.create_for_position_and_orientation(position=pos, routing_surface=SurfaceIdentifier(services.current_zone_id(), 0, SurfaceType.SURFACETYPE_WORLD))

class _FrontDoorObject(HasTunableSingletonFactory, AutoFactoryInit):

    def get_objects_gen(self, resolver):
        front_door = services.get_door_service().get_front_door()
        if front_door is not None:
            yield front_door

class _PlacementStrategy(HasTunableSingletonFactory, AutoFactoryInit):

    def _get_reference_objects_gen(self, obj, resolver, **kwargs):
        raise NotImplementedError

    def try_place_object(self, obj, resolver, **kwargs):
        for target_obj in self._get_reference_objects_gen(obj, resolver, **kwargs):
            if target_obj.is_sim:
                target_obj = target_obj.sim_info.get_sim_instance()
            if target_obj is not None and target_obj is None:
                pass
            elif self._try_place_object_internal(obj, target_obj, resolver, **kwargs):
                return True
        return False

class _PlacementStrategyLocation(_PlacementStrategy):
    POSITION_INCREMENT = 0.5
    FACTORY_TUNABLES = {'initial_location': TunableVariant(description='\n            The FGL search initial position is determined by this. If more than\n            one initial position is available, all are considered up to the\n            specified upper bound.\n            ', from_participant=_ObjectsFromParticipant.TunableFactory(), from_tags=_ObjectsFromTags.TunableFactory(), from_lot=_LocationFromLot.TunableFactory(), front_door_object=_FrontDoorObject.TunableFactory(), default='from_participant'), 'initial_location_offset': TunableTuple(default_offset=TunableVector3(description="\n                The default Vector3 offset from the location target's\n                position.\n                ", default=sims4.math.Vector3.ZERO()), x_randomization_range=OptionalTunable(tunable=TunableInterval(description='\n                    A random number in this range will be applied to the\n                    default offset along the x axis.\n                    ', tunable_type=float, default_lower=0, default_upper=0)), z_randomization_range=OptionalTunable(tunable=TunableInterval(description='\n                    A random number in this range will be applied to the\n                    default offset along the z axis.\n                    ', tunable_type=float, default_lower=0, default_upper=0))), 'facing': OptionalTunable(description='\n            If enabled, the final location will ensure that the placed object\n            faces a specific location.\n            ', tunable=TunableTuple(target=OptionalTunable(description='\n                    The location to face.\n                    ', tunable=TunableEnumEntry(description='\n                        Specify a participant that needs to be faced.\n                        ', tunable_type=ParticipantType, default=ParticipantType.Actor), disabled_name='face_initial_location'), angle=TunableAngle(description='\n                    The angle that facing will trying to keep inside while test\n                    FGL. The larger the number is, the more offset the facing\n                    could be, but the chance will be higher to succeed in FGL.\n                    ', default=0.5*sims4.math.PI, minimum=0, maximum=sims4.math.PI))), 'perform_fgl_check': Tunable(description='\n            If checked (default), FGL will be used to find an unblocked location \n            for the object to be placed after it is created.\n            \n            If unchecked, FGL will not be performed, and the object will be \n            placed at the location + orientation specified, even if it overlaps\n            other footprints.\n            \n            Ideally this should be used in conjunction with another system that\n            assures objects will not overlap.  This is useful for placing an\n            object on top of a jig, but probably should not be used for placing\n            a build buy object that intersects with another build buy object.\n            \n            It should also be noted that object collisions will not play nice\n            with save/load, and objects that overlap may be deleted when \n            loading a save.  This should be used with objects that are temporary.\n            ', tunable_type=bool, default=True), 'ignore_bb_footprints': Tunable(description='\n            Ignores the build buy object footprints when trying to find a\n            position for creating this object. This will allow objects to appear\n            on top of each other.\n            \n            e.g. Trash cans when tipped over want to place the trash right under\n            them so it looks like the pile came out from the object while it was\n            tipped.\n            ', tunable_type=bool, default=True), 'allow_off_lot_placement': Tunable(description='\n            If checked, objects will be allowed to be placed off-lot. If\n            unchecked, we will always attempt to place created objects on the\n            active lot.\n            ', tunable_type=bool, default=False), 'stay_outside_placement': Tunable(description='\n            If checked, objects will run their placement search only for\n            positions that are considered outside.\n            ', tunable_type=bool, default=False), 'in_same_room': Tunable(description='\n            If checked, objects will be placed in the same block/room of the\n            initial location. If there is not enough space to put down the\n            object in the same block, the placement will fail.\n            ', tunable_type=bool, default=False), 'terrain_tags': OptionalTunable(description='\n            If enabled, a set of allowed terrain tags. At least one tag must\n            match the terrain under each vertex of the footprint of the supplied\n            object.\n            ', tunable=TunableEnumSet(enum_type=TerrainTag, enum_default=TerrainTag.INVALID)), 'stay_in_connected_connectivity_group': Tunable(description='\n            If unchecked then the object will be allowed to be placed in\n            a connectivity group that is currently disconnected from\n            the starting location.\n            \n            If checked then the placement will fail if there is not a\n            position inside a connected connectivity group from the\n            starting position that can be used for placement.\n            ', tunable_type=bool, default=True), 'surface_type_override': OptionalTunable(description='\n            If enabled, we will override the routing surface type of the\n            location to whatever is tuned here. Otherwise, we use the routing\n            surface of the initial location.\n            \n            Example: The initial location may be in a pool but you want the\n            created object to be placed on the ground.\n            ', tunable=TunableEnumEntry(description='\n                The routing surface we want to force the object to be placed on.\n                ', tunable_type=SurfaceType, default=SurfaceType.SURFACETYPE_WORLD)), 'min_water_depth': OptionalTunable(description='\n            (float) If provided, each vertex of the test polygon along with its centroid will\n            be tested to determine whether the ocean water at the test location is at least this deep.\n            Values <= 0 indicate placement on land is valid.\n            ', tunable=Tunable(description='\n                Value of the min water depth allowed.\n                ', tunable_type=float, default=-1.0)), 'max_water_depth': OptionalTunable(description='\n            (float) If provided, each vertex of the test polygon along with its centroid will\n            be tested to determine whether the ocean water at the test location is at most this deep.\n            Values <= 0 indicate placement in ocean is invalid.\n            ', tunable=Tunable(description='\n                Value of the max water depth allowed.\n                ', tunable_type=float, default=1000.0)), 'ignore_sim_positions': Tunable(description='\n            If checked, the FGL search will ignore current Sim positions and \n            any positions Sims are intending to go.  If unchecked, these Sim\n            positions will be taken into account when placing the object.\n            ', tunable_type=bool, default=True), 'raytest': OptionalTunable(description='\n            If enabled then we will run a raytest to make sure that the object remains within LOS.\n            ', tunable=TunableTuple(description='\n                Data related to running a raytest to a position.\n                ', starting_position=OptionalTunable(description='\n                    Use either the previously calculated starting point or perform a raytest in regards to a specific\n                    participant.\n                    ', tunable=TunableEnumEntry(description="\n                        A partcipant's location that we will perform the raytest to.\n                        ", tunable_type=ParticipantType, default=ParticipantType.Actor), enabled_name='use_participants_location', disabled_name='use_initial_location'), raytest_radius=Tunable(description='\n                    The radius of the ray.  0.1 is acceptable for a line of sight check.\n                    ', tunable_type=float, default=0.1), raytest_start_height_offset=Tunable(description='\n                    The height offset of the start height.  1.5 is the height of a Sim.\n                    ', tunable_type=float, default=1.5), raytest_end_height_offset=Tunable(description='\n                    The height offset of end point of the ray.  1.5 is the height of a Sim.\n                    ', tunable_type=float, default=1.5)))}

    def _get_reference_objects_gen(self, obj, resolver, **kwargs):
        yield from self.initial_location.get_objects_gen(resolver)

    def _try_place_object_internal(self, obj, target_obj, resolver, ignored_object_ids=None, **kwargs):
        offset_tuning = self.initial_location_offset
        default_offset = sims4.math.Vector3(offset_tuning.default_offset.x, offset_tuning.default_offset.y, offset_tuning.default_offset.z)
        x_range = offset_tuning.x_randomization_range
        z_range = offset_tuning.z_randomization_range
        start_orientation = sims4.random.random_orientation()
        if x_range is not None:
            x_axis = start_orientation.transform_vector(sims4.math.Vector3.X_AXIS())
            default_offset += x_axis*random.uniform(x_range.lower_bound, x_range.upper_bound)
        if z_range is not None:
            z_axis = start_orientation.transform_vector(sims4.math.Vector3.Z_AXIS())
            default_offset += z_axis*random.uniform(z_range.lower_bound, z_range.upper_bound)
        offset = sims4.math.Transform(default_offset, sims4.math.Quaternion.IDENTITY())
        start_position = sims4.math.Transform.concatenate(offset, target_obj.transform).translation
        routing_surface = target_obj.routing_surface
        active_lot = services.active_lot()
        search_flags = FGLSearchFlag.CALCULATE_RESULT_TERRAIN_HEIGHTS | FGLSearchFlag.DONE_ON_MAX_RESULTS
        if self.surface_type_override is not None:
            routing_surface = SurfaceIdentifier(routing_surface.primary_id, routing_surface.secondary_id, self.surface_type_override)
        else:
            search_flags |= FGLSearchFlag.SHOULD_TEST_ROUTING
        if self.ignore_sim_positions:
            search_flags |= FGLSearchFlag.ALLOW_GOALS_IN_SIM_POSITIONS | FGLSearchFlag.ALLOW_GOALS_IN_SIM_INTENDED_POSITIONS
        if self.in_same_room:
            search_flags |= FGLSearchFlag.STAY_IN_CURRENT_BLOCK
        if self.stay_in_connected_connectivity_group:
            search_flags |= FGLSearchFlag.STAY_IN_CONNECTED_CONNECTIVITY_GROUP
        if self.stay_outside_placement:
            search_flags |= FGLSearchFlag.STAY_OUTSIDE
        raytest_kwargs = {}
        if self.raytest:
            search_flags |= FGLSearchFlag.SHOULD_RAYTEST
            raytest_kwargs.update({'raytest_radius': self.raytest.raytest_radius, 'raytest_start_offset': self.raytest.raytest_start_height_offset, 'raytest_end_offset': self.raytest.raytest_end_height_offset})
            if self.raytest.starting_position is not None:
                raytest_target = resolver.get_participant(self.raytest.starting_position)
                if raytest_target is not None:
                    if raytest_target.is_sim:
                        raytest_target = raytest_target.get_sim_instance(allow_hidden_flags=ALL_HIDDEN_REASONS)
                    raytest_kwargs['raytest_start_point_override'] = raytest_target.transform.translation
        restrictions = None
        if self.facing is not None:
            if self.facing.target is None:
                facing_target = target_obj
            else:
                facing_target = resolver.get_participant(self.facing.target)
            if facing_target is not None:
                restriction = sims4.geometry.RelativeFacingRange(facing_target.position, self.facing.angle)
                restrictions = (restriction,)
        terrain_tags = list(self.terrain_tags) if self.terrain_tags else []
        if self.allow_off_lot_placement and not active_lot.is_position_on_lot(start_position):
            obj.location = sims4.math.Location(sims4.math.Transform(start_position, start_orientation), routing_surface)
            starting_location = create_starting_location(position=start_position, orientation=start_orientation, routing_surface=routing_surface)
            context = create_fgl_context_for_object_off_lot(starting_location, obj, terrain_tags=terrain_tags, search_flags=search_flags, ignored_object_ids=(obj.id,), restrictions=restrictions, min_water_depth=self.min_water_depth, max_water_depth=self.max_water_depth, **raytest_kwargs)
        else:
            if self.allow_off_lot_placement or not active_lot.is_position_on_lot(start_position):
                return False
            if not self.ignore_bb_footprints:
                if routing_surface.type != SurfaceType.SURFACETYPE_WORLD:
                    search_flags |= FGLSearchFlag.SHOULD_TEST_BUILDBUY
                else:
                    search_flags |= FGLSearchFlag.SHOULD_TEST_BUILDBUY | FGLSearchFlag.STAY_IN_CURRENT_BLOCK
                if not active_lot.is_position_on_lot(start_position):
                    start_position = active_lot.get_default_position(position=start_position)
                else:
                    position_inside_plex = self._get_plex_postion_for_object_creation(start_position, routing_surface.secondary_id)
                    if position_inside_plex is not None:
                        start_position = position_inside_plex
            starting_location = create_starting_location(position=start_position, orientation=start_orientation, routing_surface=routing_surface)
            context = create_fgl_context_for_object(starting_location, obj, terrain_tags=terrain_tags, search_flags=search_flags, ignored_object_ids=ignored_object_ids, position_increment=self.POSITION_INCREMENT, restrictions=restrictions, min_water_depth=self.min_water_depth, max_water_depth=self.max_water_depth, **raytest_kwargs)
        if self.perform_fgl_check:
            (translation, orientation) = find_good_location(context)
            if translation is not None:
                obj.move_to(routing_surface=routing_surface, translation=translation, orientation=orientation)
                return True
        elif starting_location is not None:
            obj.move_to(routing_surface=routing_surface, translation=starting_location.position, orientation=starting_location.orientation)
            return True
        return False

    def _get_plex_postion_for_object_creation(self, start_position, level):
        plex_service = services.get_plex_service()
        is_active_zone_a_plex = plex_service.is_active_zone_a_plex()
        if not is_active_zone_a_plex:
            return
        if plex_service.get_plex_zone_at_position(start_position, level) is not None:
            return
        front_door = services.get_door_service().get_front_door()
        if front_door is not None:
            (front_position, back_position) = front_door.get_door_positions()
            front_zone_id = plex_service.get_plex_zone_at_position(front_position, front_door.level)
            if front_zone_id is not None:
                return front_position
            else:
                back_zone_id = plex_service.get_plex_zone_at_position(back_position, front_door.level)
                if back_zone_id is not None:
                    return back_position

class _PlacementStrategySlot(_PlacementStrategy):
    FACTORY_TUNABLES = {'parent': TunableVariant(description='\n            The object this object is going to be slotted into.\n            ', from_participant=_ObjectsFromParticipant.TunableFactory(participant_type_default=(ParticipantType.Object,)), from_tags=_ObjectsFromTags.TunableFactory(), default='from_participant'), 'parent_slot': TunableVariant(description='\n            The slot on location_target where the object should go. This may be\n            either the exact name of a bone on the location_target or a slot\n            type, in which case the first empty slot of the specified type in\n            which the child object fits will be used.\n            ', by_name=Tunable(description='\n                The exact name of a slot on the location_target in which the\n                target object should go.\n                ', tunable_type=str, default='_ctnm_'), by_reference=TunableReference(description='\n                A particular slot type in which the target object should go.\n                The first empty slot of this type found on the location_target\n                will be used.\n                ', manager=services.get_instance_manager(sims4.resources.Types.SLOT_TYPE))), 'use_part_owner': Tunable(description='\n            If enabled and target is a part, placement will use the part owner\n            instead of the part.\n            ', tunable_type=bool, default=False)}

    def _get_reference_objects_gen(self, obj, resolver, **kwargs):
        yield from self.parent.get_objects_gen(resolver)

    def _try_place_object_internal(self, obj, target_obj, resolver, **kwargs):
        if target_obj.is_part:
            target_obj = target_obj.part_owner
        parent_slot = self.parent_slot
        if self.use_part_owner and target_obj.slot_object(parent_slot=parent_slot, slotting_object=obj):
            return True
        return False

class TunablePlacementStrategyVariant(TunableVariant):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, location=_PlacementStrategyLocation.TunableFactory(), slot=_PlacementStrategySlot.TunableFactory(), default='location', **kwargs)

class PlacementHelper(HasTunableSingletonFactory, AutoFactoryInit):
    FACTORY_TUNABLES = {'placement_strategy_groups': TunableList(description='\n            A list of ordered strategy groups. These are executed in order. If\n            any placement from the group succeeds, the placement is considered\n            terminated.\n            ', tunable=TunableList(description='\n                A list of weighted strategies. Each placement strategy is\n                randomly weighted against the rest. Attempts are made until all\n                strategies are exhausted. If none succeeds, the next group is\n                considered.\n                ', tunable=TunableTuple(weight=TunableMultiplier.TunableFactory(description='\n                        The weight of this strategy relative to other strategies\n                        in its group.\n                        '), placement_strategy=TunablePlacementStrategyVariant(description='\n                        The placement strategy for the object in question.\n                        ')), minlength=1), minlength=1)}

    def try_place_object(self, obj, resolver, **kwargs):
        for strategy_group in self.placement_strategy_groups:
            strategies = [(entry.weight.get_multiplier(resolver), entry.placement_strategy) for entry in strategy_group]
            while strategies:
                strategy = pop_weighted(strategies)
                if strategy.try_place_object(obj, resolver, **kwargs):
                    return True
        return False
