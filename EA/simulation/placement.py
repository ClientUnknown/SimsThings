import timefrom sims4.sim_irq_service import yield_to_irqfrom sims4.tuning.tunable import Tunable, TunableAngleimport enumimport gsi_handlers.routing_handlersimport routingimport servicesimport sims4.geometryimport sims4.logimport sims4.mathtry:
    import _placement
    get_sim_quadtree_for_zone = _placement.get_sim_quadtree_for_zone
    get_placement_footprint_compound_polygon = _placement.get_placement_footprint_compound_polygon
    get_placement_footprint_polygon = _placement.get_placement_footprint_polygon
    get_accurate_placement_footprint_polygon = _placement.get_accurate_placement_footprint_polygon
    get_placement_footprint_bounds = _placement.get_placement_footprint_bounds
    get_routing_footprint_polygon = _placement.get_routing_footprint_polygon
    get_object_surface_footprint_polygon = _placement.get_object_surface_footprint_polygon
    has_object_surface_footprint = _placement.has_object_surface_footprint
    validate_sim_location = _placement.validate_sim_location
    validate_los_source_location = _placement.validate_los_source_location
    surface_supports_object_placement = _placement.surface_supports_object_placement
    FGLSearch = _placement.FGLSearch
    FGLResult = _placement.FGLResult
    FGLResultStrategyDefault = _placement.FGLResultStrategyDefault
    FGLSearchStrategyRouting = _placement.FGLSearchStrategyRouting
    FGLSearchStrategyRoutingGoals = _placement.FGLSearchStrategyRoutingGoals
    ScoringFunctionLinear = _placement.ScoringFunctionLinear
    ScoringFunctionRadial = _placement.ScoringFunctionRadial
    ScoringFunctionAngular = _placement.ScoringFunctionAngular
    ScoringFunctionPolygon = _placement.ScoringFunctionPolygon
    ObjectQuadTree = _placement.ObjectQuadTree

    class ItemType(enum.Int, export=False):
        UNKNOWN = _placement.ITEMTYPE_UNKNOWN
        SIM_POSITION = _placement.ITEMTYPE_SIM_POSITION
        SIM_INTENDED_POSITION = _placement.ITEMTYPE_SIM_INTENDED_POSITION
        ROUTE_GOAL_SUPPRESSOR = _placement.ITEMTYPE_ROUTE_GOAL_SUPPRESSOR
        ROUTE_GOAL_PENALIZER = _placement.ITEMTYPE_ROUTE_GOAL_PENALIZER
        SIM_ROUTING_CONTEXT = _placement.ITEMTYPE_SIM_ROUTING_CONTEXT
        GOAL = _placement.ITEMTYPE_GOAL
        GOAL_SLOT = _placement.ITEMTYPE_GOAL_SLOT
        ROUTABLE_OBJECT_SURFACE = _placement.ITEMTYPE_ROUTABLE_OBJECT_SURFACE

    class FGLSearchType(enum.Int, export=False):
        NONE = _placement.FGL_SEARCH_TYPE_NONE
        ROUTING = _placement.FGL_SEARCH_TYPE_ROUTING
        ROUTING_GOALS = _placement.FGL_SEARCH_TYPE_ROUTING_GOALS

    class FGLSearchDataType(enum.Int, export=False):
        UNKNOWN = _placement.FGL_SEARCH_DATA_TYPE_UNKNOWN
        START_LOCATION = _placement.FGL_SEARCH_DATA_TYPE_START_LOCATION
        POLYGON = _placement.FGL_SEARCH_DATA_TYPE_POLYGON
        SCORING_FUNCTION = _placement.FGL_SEARCH_DATA_TYPE_SCORING_FUNCTION
        POLYGON_CONSTRAINT = _placement.FGL_SEARCH_DATA_TYPE_POLYGON_CONSTRAINT
        RESTRICTION = _placement.FGL_SEARCH_DATA_TYPE_RESTRICTION
        ROUTING_CONTEXT = _placement.FGL_SEARCH_DATA_TYPE_ROUTING_CONTEXT
        FLAG_CONTAINS_NOWHERE_CONSTRAINT = _placement.FGL_SEARCH_DATA_TYPE_FLAG_CONTAINS_NOWHERE_CONSTRAINT
        FLAG_CONTAINS_ANYWHERE_CONSTRAINT = _placement.FGL_SEARCH_DATA_TYPE_FLAG_CONTAINS_ANYWHERE_CONSTRAINT

    class FGLSearchResult(enum.Int, export=False):
        SUCCESS = _placement.FGL_SEARCH_RESULT_SUCCESS
        NOT_INITIALIZED = _placement.FGL_SEARCH_RESULT_NOT_INITIALIZED
        IN_PROGRESS = _placement.FGL_SEARCH_RESULT_IN_PROGRESS
        FAIL_PATHPLANNER_NOT_INITIALIZED = _placement.FGL_SEARCH_RESULT_FAIL_PATHPLANNER_NOT_INITIALIZED
        FAIL_CANNOT_LOCK_PATHPLANNER = _placement.FGL_SEARCH_RESULT_FAIL_CANNOT_LOCK_PATHPLANNER
        FAIL_BUILDBUY_SYSTEM_UNAVAILABLE = _placement.FGL_SEARCH_RESULT_FAIL_BUILDBUY_SYSTEM_UNAVAILABLE
        FAIL_LOT_UNAVAILABLE = _placement.FGL_SEARCH_RESULT_FAIL_LOT_UNAVAILABLE
        FAIL_INVALID_INPUT = _placement.FGL_SEARCH_RESULT_FAIL_INVALID_INPUT
        FAIL_INVALID_INPUT_START_LOCATION = _placement.FGL_SEARCH_RESULT_FAIL_INVALID_INPUT_START_LOCATION
        FAIL_INVALID_INPUT_POLYGON = _placement.FGL_SEARCH_RESULT_FAIL_INVALID_INPUT_POLYGON
        FAIL_INVALID_INPUT_OBJECT_ID = _placement.FGL_SEARCH_RESULT_FAIL_INVALID_INPUT_OBJECT_ID
        FAIL_INCOMPATIBLE_SEARCH_STRATEGY = _placement.FGL_SEARCH_RESULT_FAIL_INCOMPATIBLE_SEARCH_STRATEGY
        FAIL_INCOMPATIBLE_RESULT_STRATEGY = _placement.FGL_SEARCH_RESULT_FAIL_INCOMPATIBLE_RESULT_STRATEGY
        FAIL_NO_RESULTS = _placement.FGL_SEARCH_RESULT_FAIL_NO_RESULTS
        FAIL_UNKNOWN = _placement.FGL_SEARCH_RESULT_FAIL_UNKNOWN

except ImportError:

    class _placement:

        @staticmethod
        def test_object_placement(pos, ori, resource_key):
            return False

    class ScoringFunctionLinear:

        def __init__(self, *args, **kwargs):
            pass

    class ScoringFunctionRadial:

        def __init__(self, *args, **kwargs):
            pass

    class ScoringFunctionAngular:

        def __init__(self, *args, **kwargs):
            pass

    class ScoringFunctionPolygon:

        def __init__(self, *args, **kwargs):
            pass

    @staticmethod
    def get_sim_quadtree_for_zone(*_, **__):
        pass

    @staticmethod
    def get_placement_footprint_compound_polygon(*_, **__):
        pass

    @staticmethod
    def get_placement_footprint_polygon(*_, **__):
        pass

    @staticmethod
    def get_accurate_placement_footprint_polygon(*_, **__):
        pass

    @staticmethod
    def get_placement_footprint_bounds(*_, **__):
        pass

    @staticmethod
    def get_object_surface_footprint_polygon(*_, **__):
        pass

    @staticmethod
    def has_object_surface_footprint(*_, **__):
        pass

    @staticmethod
    def get_routing_footprint_polygon(*_, **__):
        pass

    class ItemType(enum.Int, export=False):
        UNKNOWN = 0
        SIM_POSITION = 5
        SIM_INTENDED_POSITION = 6
        GOAL = 7
        GOAL_SLOT = 8
        ROUTE_GOAL_SUPPRESSOR = 30
        ROUTE_GOAL_PENALIZER = 31
        ROUTABLE_OBJECT_SURFACE = 32

    class FGLSearchType(enum.Int, export=False):
        UNKNOWN = 0

    class FGLSearchDataType(enum.Int, export=False):
        UNKNOWN = 0

    class FGLSearchResult(enum.Int, export=False):
        FAIL_UNKNOWN = 11

    class ObjectQuadTree:

        def __init__(self, *args, **kwargs):
            pass

    class FGLSearch:

        def __init__(self, *args, **kwargs):
            pass

    class FGLResultStrategyDefault:

        def __init__(self, *args, **kwargs):
            pass

    class FGLSearchStrategyRoutingGoals:

        def __init__(self, *args, **kwargs):
            pass

class FGLTuning:
    MAX_FGL_DISTANCE = Tunable(description='\n        The maximum distance searched by the Find Good Location code.\n        ', tunable_type=float, default=100.0)
    SOCIAL_FGL_HEIGHT_TOLERANCE = Tunable(description='\n        Maximum height tolerance on the terrain we will use for the placement \n        of social jigs.\n        If this value needs to be retuned a GPE, an Animator and Motech should\n        be involved.\n        ', tunable_type=float, default=0.1)
logger = sims4.log.Logger('Placement')
def generate_routing_goals_for_polygon(sim, polygon, polygon_surface, orientation_restrictions=None, object_ids_to_ignore=None, flush_planner=False, sim_location_bonus=0.0, add_sim_location_as_goal=True, los_reference_pt=None, max_points=100, ignore_outer_penalty_amount=2, target_object=2, target_object_id=0, even_coverage_step=2, single_goal_only=False, los_routing_context=None, all_blocking_edges_block_los=False, provided_points=(), min_water_depth=None, max_water_depth=None, terrain_tags=None):
    yield_to_irq()
    routing_context = sim.get_routing_context()
    if los_routing_context is None:
        los_routing_context = routing_context
    return _placement.generate_routing_goals_for_polygon(sim.routing_location, polygon, polygon_surface, None, orientation_restrictions, object_ids_to_ignore, routing_context, flush_planner, -sim_location_bonus, add_sim_location_as_goal, los_reference_pt, 2.5, max_points, ignore_outer_penalty_amount, target_object_id, even_coverage_step, single_goal_only, los_routing_context, all_blocking_edges_block_los, provided_points, min_water_depth, max_water_depth, terrain_tags)

class FGLSearchFlag(enum.IntFlags):
    NONE = 0
    USE_RANDOM_WEIGHTING = 1
    USE_RANDOM_ORIENTATION = 2
    ALLOW_TOO_CLOSE_TO_OBSTACLE = 4
    ALLOW_GOALS_IN_SIM_POSITIONS = 8
    ALLOW_GOALS_IN_SIM_INTENDED_POSITIONS = 16
    STAY_IN_SAME_CONNECTIVITY_GROUP = 32
    STAY_IN_CONNECTED_CONNECTIVITY_GROUP = 64
    SHOULD_TEST_BUILDBUY = 128
    SHOULD_TEST_ROUTING = 256
    CALCULATE_RESULT_TERRAIN_HEIGHTS = 512
    DONE_ON_MAX_RESULTS = 1024
    USE_SIM_FOOTPRINT = 2048
    STAY_IN_CURRENT_BLOCK = 4096
    STAY_OUTSIDE = 8192
    ALLOW_INACTIVE_PLEX = 16384
    SHOULD_RAYTEST = 32768
    SPIRAL_INWARDS = 65536
    STAY_IN_LOT = 131072
FGLSearchFlagsDefault = FGLSearchFlag.STAY_IN_CONNECTED_CONNECTIVITY_GROUP | FGLSearchFlag.SHOULD_TEST_ROUTING | FGLSearchFlag.CALCULATE_RESULT_TERRAIN_HEIGHTS | FGLSearchFlag.DONE_ON_MAX_RESULTSFGLSearchFlagsDefaultForObject = FGLSearchFlagsDefault | FGLSearchFlag.SHOULD_TEST_BUILDBUYFGLSearchFlagsDefaultForSim = FGLSearchFlagsDefault | FGLSearchFlag.USE_SIM_FOOTPRINT
class PlacementConstants:
    rotation_increment = TunableAngle(sims4.math.PI/8, description='The size of the angle-range that sims should use when determining facing constraints.')

def _get_nearby_items_gen(position, surface_id, radius=None, exclude=None, flags=sims4.geometry.ObjectQuadTreeQueryFlag.NONE, *, query_filter):
    radius = routing.get_default_agent_radius()
    position_2d = sims4.math.Vector2(position.x, position.z)
    bounds = sims4.geometry.QtCircle(position_2d, radius)
    exclude_ids = []
    for routing_agent in exclude:
        exclude_ids.append(routing_agent.id)
    query = services.sim_quadtree().query(bounds, surface_id, filter=query_filter, flags=flags, exclude=exclude_ids)
    for q in query:
        obj = q[0]
        if not exclude or obj in exclude:
            pass
        else:
            yield q[0]

def get_nearby_sims_gen(position, surface_id, radius=None, exclude=None, stop_at_first_result=False, only_sim_position=False, only_sim_intended_position=False, check_all_surfaces_on_level=False):
    query_filter = (ItemType.SIM_POSITION, ItemType.SIM_INTENDED_POSITION)
    if only_sim_position:
        query_filter = ItemType.SIM_POSITION
    else:
        query_filter = ItemType.SIM_INTENDED_POSITION
    flags = sims4.geometry.ObjectQuadTreeQueryFlag.NONE
    flags |= sims4.geometry.ObjectQuadTreeQueryFlag.STOP_AT_FIRST_RESULT
    flags |= sims4.geometry.ObjectQuadTreeQueryFlag.IGNORE_SURFACE_TYPE
    for obj in _get_nearby_items_gen(position=position, surface_id=surface_id, radius=radius, exclude=exclude, flags=flags, query_filter=query_filter):
        if not obj.is_sim:
            pass
        else:
            yield obj
fgl_id = 0
def find_good_location(context):
    global fgl_id
    if context is None:
        return (None, None)
    fgl_id = fgl_id + 1
    start_time = 0
    if gsi_handlers.routing_handlers.FGL_archiver.enabled:
        start_time = time.time()
    context.search.search()
    search_result = FGLSearchResult(context.search.search_result)
    if gsi_handlers.routing_handlers.FGL_archiver.enabled:
        gsi_handlers.routing_handlers.archive_FGL(fgl_id, context, search_result, time.time() - start_time)
    if search_result == FGLSearchResult.SUCCESS:
        temp_list = context.search.get_results()
        if temp_list is not None and len(temp_list) > 0:
            fgl_loc = temp_list[0]
            fgl_pos = sims4.math.Vector3(fgl_loc.position.x, fgl_loc.position.y, fgl_loc.position.z)
            if not context.result_strategy.calculate_result_terrain_heights:
                terrain_instance = services.terrain_service.terrain_object()
                fgl_pos.y = terrain_instance.get_routing_surface_height_at(fgl_loc.position.x, fgl_loc.position.z, fgl_loc.routing_surface_id)
            return (fgl_pos, fgl_loc.orientation)
    elif search_result == FGLSearchResult.FAIL_NO_RESULTS:
        logger.debug('FGL search returned 0 results.')
    else:
        logger.warn('FGL search failed: {0}.', str(search_result))
    return (None, None)
FGL_DEFAULT_POSITION_INCREMENT = 0.3FGL_FOOTPRINT_POSITION_INCREMENT_MULTIPLIER = 0.5
class FindGoodLocationContext:

    def __init__(self, starting_routing_location, object_id=None, object_def_id=None, object_def_state_index=None, object_footprints=None, object_polygons=None, routing_context=None, ignored_object_ids=None, min_distance=None, max_distance=None, position_increment=None, additional_avoid_sim_radius=0, restrictions=None, scoring_functions=None, offset_distance=None, offset_restrictions=None, random_range_weighting=None, max_results=0, max_steps=1, height_tolerance=None, terrain_tags=None, raytest_start_offset=None, raytest_end_offset=None, raytest_radius=None, raytest_ignore_flags=None, raytest_start_point_override=None, search_flags=FGLSearchFlagsDefault, min_water_depth=None, max_water_depth=None, **kwargs):
        self.search_strategy = _placement.FGLSearchStrategyRouting(start_location=starting_routing_location)
        self.result_strategy = _placement.FGLResultStrategyDefault()
        self.search = _placement.FGLSearch(self.search_strategy, self.result_strategy)
        if object_id is not None:
            self.search_strategy.object_id = object_id
        if object_def_id is not None:
            self.search_strategy.object_def_id = object_def_id
        if object_def_state_index is not None:
            self.search_strategy.object_def_state_index = object_def_state_index
        if object_polygons is not None:
            for polygon_wrapper in object_polygons:
                if isinstance(polygon_wrapper, sims4.geometry.Polygon):
                    self.search_strategy.add_polygon(polygon_wrapper, starting_routing_location.routing_surface)
                else:
                    p = polygon_wrapper[0]
                    p_routing_surface = polygon_wrapper[1]
                    if p_routing_surface is None:
                        p_routing_surface = starting_routing_location.routing_surface
                    self.search_strategy.add_polygon(p, p_routing_surface)
        self.object_footprints = object_footprints
        if object_footprints is not None:
            for footprint_wrapper in object_footprints:
                if footprint_wrapper is None:
                    logger.error('None footprint wrapper found during FGL: {}', self)
                elif isinstance(footprint_wrapper, sims4.resources.Key):
                    compound_polygon = _placement.get_placement_footprint_compound_polygon(starting_routing_location.position, starting_routing_location.orientation, starting_routing_location.routing_surface, footprint_wrapper)
                    for polygon in compound_polygon:
                        self.search_strategy.add_polygon(polygon, starting_routing_location.routing_surface)
                else:
                    fp_key = footprint_wrapper[0]
                    t = footprint_wrapper[1]
                    p_routing_surface = footprint_wrapper[2]
                    if p_routing_surface is None:
                        p_routing_surface = starting_routing_location.routing_surface
                    compound_polygon = _placement.get_placement_footprint_compound_polygon(t.translation, t.orientation, p_routing_surface, fp_key)
                    for polygon in compound_polygon:
                        self.search_strategy.add_polygon(polygon, p_routing_surface)
        if routing_context is not None:
            self.search_strategy.routing_context = routing_context
        if ignored_object_ids is not None:
            for obj_id in ignored_object_ids:
                self.search_strategy.add_ignored_object_id(obj_id)
        if min_distance is not None:
            self.search_strategy.min_distance = min_distance
        self.search_strategy.max_distance = FGLTuning.MAX_FGL_DISTANCE if max_distance is None else max_distance
        self.search_strategy.rotation_increment = PlacementConstants.rotation_increment
        if position_increment is None:
            position_increment = FGL_DEFAULT_POSITION_INCREMENT
        self.search_strategy.position_increment = position_increment
        if restrictions is not None:
            for r in restrictions:
                self.search_strategy.add_restriction(r)
        if scoring_functions is not None:
            for sf in scoring_functions:
                self.search_strategy.add_scoring_function(sf)
        if offset_distance > 0:
            self.search_strategy.offset_distance = offset_distance
            self.search_strategy.start_offset_orientation = sims4.math.angle_to_yaw_quaternion(0.0)
            if offset_restrictions is not None:
                for r in offset_restrictions:
                    self.search_strategy.add_offset_restriction(r)
        if offset_distance is not None and additional_avoid_sim_radius > 0:
            self.search_strategy.avoid_sim_radius = additional_avoid_sim_radius
        self.result_strategy.max_results = max_results
        self.search_strategy.max_steps = max_steps
        if height_tolerance is not None:
            self.search_strategy.height_tolerance = height_tolerance
        if terrain_tags is not None:
            self.search_strategy.terrain_tags = terrain_tags
        if random_range_weighting is not None:
            self.search_strategy.use_random_weighting = True
            self.search_strategy.random_range_weighting = random_range_weighting
        if raytest_start_offset is not None:
            self.search_strategy.raytest_start_offset = raytest_start_offset
        if raytest_end_offset is not None:
            self.search_strategy.raytest_end_offset = raytest_end_offset
        if raytest_radius is not None:
            self.search_strategy.raytest_radius = raytest_radius
        if raytest_ignore_flags is not None:
            self.search_strategy.raytest_ignore_flags = raytest_ignore_flags
        if raytest_start_point_override is None:
            self.search_strategy.raytest_start_point = starting_routing_location.position
        else:
            self.search_strategy.raytest_start_point = raytest_start_point_override
        if search_flags is not None:
            self.search_strategy.use_random_orientation = search_flags & FGLSearchFlag.USE_RANDOM_ORIENTATION
            self.search_strategy.allow_too_close_to_obstacle = search_flags & FGLSearchFlag.ALLOW_TOO_CLOSE_TO_OBSTACLE
            self.search_strategy.allow_goals_in_sim_positions = search_flags & FGLSearchFlag.ALLOW_GOALS_IN_SIM_POSITIONS
            self.search_strategy.allow_goals_in_sim_intended_positions = search_flags & FGLSearchFlag.ALLOW_GOALS_IN_SIM_INTENDED_POSITIONS
            self.search_strategy.stay_in_same_connectivity_group = search_flags & FGLSearchFlag.STAY_IN_SAME_CONNECTIVITY_GROUP
            self.search_strategy.stay_in_connected_connectivity_group = search_flags & FGLSearchFlag.STAY_IN_CONNECTED_CONNECTIVITY_GROUP
            self.search_strategy.should_test_buildbuy = search_flags & FGLSearchFlag.SHOULD_TEST_BUILDBUY
            self.search_strategy.should_test_routing = search_flags & FGLSearchFlag.SHOULD_TEST_ROUTING
            self.search_strategy.use_sim_footprint = search_flags & FGLSearchFlag.USE_SIM_FOOTPRINT
            self.result_strategy.calculate_result_terrain_heights = search_flags & FGLSearchFlag.CALCULATE_RESULT_TERRAIN_HEIGHTS
            self.result_strategy.done_on_max_results = search_flags & FGLSearchFlag.DONE_ON_MAX_RESULTS
            self.search_strategy.stay_in_current_block = search_flags & FGLSearchFlag.STAY_IN_CURRENT_BLOCK
            self.search_strategy.stay_outside = search_flags & FGLSearchFlag.STAY_OUTSIDE
            self.search_strategy.should_raytest = search_flags & FGLSearchFlag.SHOULD_RAYTEST
            self.search_strategy.spiral_inwards = search_flags & FGLSearchFlag.SPIRAL_INWARDS
            self.search_strategy.stay_in_lot = search_flags & FGLSearchFlag.STAY_IN_LOT
        if min_water_depth is not None:
            self.search_strategy.min_water_depth = min_water_depth
        if max_water_depth is not None:
            self.search_strategy.max_water_depth = max_water_depth
        if gsi_handlers.routing_handlers.FGL_archiver.enabled:
            self.__dict__.update(locals())

def create_fgl_context_for_object(starting_location, obj_to_place, search_flags=FGLSearchFlagsDefault, test_buildbuy_allowed=True, **kwargs):
    footprint = obj_to_place.get_footprint()
    if obj_to_place.definition is not obj_to_place:
        search_flags |= FGLSearchFlag.SHOULD_TEST_BUILDBUY
    return FindGoodLocationContext(starting_location, object_id=obj_to_place.id, object_footprints=(footprint,) if test_buildbuy_allowed and footprint is not None else None, search_flags=search_flags, **kwargs)

def create_fgl_context_for_sim(starting_location, sim_to_place, search_flags=FGLSearchFlagsDefaultForSim, **kwargs):
    return FindGoodLocationContext(starting_location, object_id=sim_to_place.id, search_flags=search_flags, **kwargs)

def create_fgl_context_for_object_off_lot(starting_location, obj_to_place, search_flags=FGLSearchFlagsDefault, location=None, footprint=None, **kwargs):
    try:
        if obj_to_place is None:
            position = location.transform.translation
            orientation = location.transform.orientation
            scale = 1.0
        else:
            position = obj_to_place.position
            orientation = obj_to_place.orientation
            scale = obj_to_place.scale
            footprint = obj_to_place.get_footprint()
        polygon = get_accurate_placement_footprint_polygon(position, orientation, scale, footprint)
    except AttributeError as exc:
        raise AttributeError('Getting footprint polygon for {} threw an error :{}'.format(obj_to_place if obj_to_place is not None else footprint, exc))
    except Exception as e:
        logger.error("Error getting polygon for {}'s footprint {}:{}".format(obj_to_place if obj_to_place is not None else footprint, footprint, e))
        raise e
    return FindGoodLocationContext(starting_location, object_polygons=(polygon,), search_flags=search_flags, **kwargs)

def create_starting_location(position=None, orientation=None, transform=None, routing_surface=None, location=None):
    starting_routing_location = None
    if location is None:
        if routing_surface is None:
            zone_id = services.current_zone_id()
            routing_surface = routing.SurfaceIdentifier(zone_id, 0, routing.SurfaceType.SURFACETYPE_WORLD)
        if transform is None:
            if position is None:
                logger.error('Trying to create a starting location for a FindGoodLocationContext but position is None. If position is going to remain None then either location or transform need to be passed in instead. -trevor')
            if orientation is None:
                orientation = sims4.math.angle_to_yaw_quaternion(0.0)
            starting_routing_location = routing.Location(position, orientation, routing_surface)
        else:
            starting_routing_location = routing.Location(transform.translation, transform.orientation, routing_surface)
    else:
        starting_routing_location = routing.Location(location.transform.translation, location.transform.orientation, location.routing_surface or location.world_routing_surface)
    return starting_routing_location

def add_placement_footprint(owner):
    _placement.add_placement_footprint(owner.id, owner.zone_id, owner.footprint, owner.position, owner.orientation, owner.scale)
    owner.clear_raycast_context()

def remove_placement_footprint(owner):
    _placement.remove_placement_footprint(owner.id, owner.zone_id)
DEFAULT_RAY_RADIUS = 0.001
def ray_intersects_placement_3d(zone_id, ray_start, ray_end, objects_to_ignore=None, intersection_flags=0, radius=DEFAULT_RAY_RADIUS):
    return _placement.ray_intersects_placement_3d(zone_id, ray_start, ray_end, objects_to_ignore, intersection_flags, radius)
