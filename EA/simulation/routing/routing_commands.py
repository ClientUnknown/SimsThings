from _geometry import CompoundPolygonfrom _math import Vector3from timeit import itertoolsfrom elements import GeneratorElementfrom interactions.constraints import Circle, Constraint, create_constraint_setfrom interactions.utils.routing import PlanRoute, FollowPathfrom objects.components.types import ROUTING_COMPONENTfrom server_commands.argument_helpers import OptionalTargetParam, get_optional_target, TunableInstanceParamfrom server_commands.visualization_commands import extract_floats, find_substring_in_repr, POLYGON_STR, POLYGON_END_PARAMfrom sims4.commands import CommandTypefrom sims4.geometry import RestrictedPolygonimport debugvisimport element_utilsimport posturesimport routingimport servicesimport sims4.commands
@sims4.commands.Command('routing.debug.follow')
def routing_debug_follow(x:float=None, y:float=None, z:float=None, obj:OptionalTargetParam=None, _connection=None):
    if x is None or y is None or z is None:
        return False
    obj = get_optional_target(obj, _connection=_connection)
    if obj is None:
        return False
    routing_component = obj.get_component(ROUTING_COMPONENT)
    if routing_component is None:
        return False

    def _do_route_gen(timeline):
        location = routing.Location(Vector3(x, y, z), routing_surface=obj.routing_surface)
        goal = routing.Goal(location)
        routing_context = obj.get_routing_context()
        route = routing.Route(obj.routing_location, (goal,), routing_context=routing_context)
        plan_primitive = PlanRoute(route, obj)
        result = yield from element_utils.run_child(timeline, plan_primitive)
        if not result:
            return result
        nodes = plan_primitive.path.nodes
        if not (nodes and nodes.plan_success):
            return False
        else:
            follow_path_element = FollowPath(obj, plan_primitive.path)
            result = yield from element_utils.run_child(timeline, follow_path_element)
            if not result:
                return result
        return True

    timeline = services.time_service().sim_timeline
    timeline.schedule(GeneratorElement(_do_route_gen))
    return True

@sims4.commands.Command('routing.debug.waypoints')
def routing_debug_waypoints(*waypoint_data, _connection=None):
    obj = get_optional_target(None, _connection=_connection)
    if obj is None:
        return False
    routing_component = obj.get_component(ROUTING_COMPONENT)
    if routing_component is None:
        return False
    object_manager = services.object_manager()
    waypoints = []
    for (is_float, data_points) in itertools.groupby(waypoint_data, lambda d: '.' in d):
        while True:
            try:
                if is_float:
                    position = Vector3(float(next(data_points)), float(next(data_points)), float(next(data_points)))
                    routing_surface = routing.SurfaceIdentifier(services.current_zone_id(), 0, routing.SurfaceType.SURFACETYPE_WORLD)
                    location = routing.Location(position, routing_surface=routing_surface)
                else:
                    o = object_manager.get(int(next(data_points)))
                    if o is None:
                        continue
                    routing_surface = o.provided_routing_surface
                    if routing_surface is None:
                        continue
                    location = routing.Location(o.position, routing_surface=routing_surface)
                waypoints.append((routing.Goal(location),))
            except StopIteration:
                break

    def _do_route_gen(timeline):
        routing_context = obj.get_routing_context()
        route = routing.Route(obj.routing_location, waypoints[-1], waypoints=waypoints[:-1], routing_context=routing_context)
        plan_primitive = PlanRoute(route, obj)
        result = yield from element_utils.run_child(timeline, plan_primitive)
        if not result:
            return result
        nodes = plan_primitive.path.nodes
        if not (nodes and nodes.plan_success):
            return False
        else:
            follow_path_element = FollowPath(obj, plan_primitive.path)
            result = yield from element_utils.run_child(timeline, follow_path_element)
            if not result:
                return result
        return True

    timeline = services.time_service().sim_timeline
    timeline.schedule(GeneratorElement(_do_route_gen))
    return True

@sims4.commands.Command('routing.debug.generate_routing_goals_geometry', command_type=CommandType.DebugOnly)
def routing_debug_generate_routing_goals_from_geometry(*args, obj:OptionalTargetParam=None, _connection=None):
    output = sims4.commands.Output(_connection)
    obj = get_optional_target(obj, _connection=_connection)
    if obj is None:
        return False
    routing_component = obj.get_component(ROUTING_COMPONENT)
    if routing_component is None:
        return False
    total_string = ''.join(args)
    polygon_strs = find_substring_in_repr(total_string, POLYGON_STR, POLYGON_END_PARAM)
    if not polygon_strs:
        output('No valid polygons. must start with {} and end with {}'.format(POLYGON_STR, POLYGON_END_PARAM))
        return
    constraints = []
    routing_surface = routing.SurfaceIdentifier(services.current_zone_id(), 0, routing.SurfaceType.SURFACETYPE_OBJECT)
    for poly_str in polygon_strs:
        point_list = extract_floats(poly_str)
        if point_list and len(point_list) % 2 != 0:
            output('Point list is not valid length. Too few or one too many.')
            return
        vertices = []
        for index in range(0, len(point_list), 2):
            vertices.append(sims4.math.Vector3(point_list[index], 0.0, point_list[index + 1]))
        polygon = sims4.geometry.Polygon(vertices)
        geometry = RestrictedPolygon(polygon, [])
        constraints.append(Constraint(geometry=geometry, routing_surface=routing_surface))
    constraint_set = create_constraint_set(constraints)
    if not postures.posture_graph.enable_debug_goals_visualization:
        sims4.commands.execute('debugvis.goals.enable', _connection)
    handles = constraint_set.get_connectivity_handles(obj)
    handles_str = 'Handles: {}'.format(len(handles))
    sims4.commands.output(handles_str, _connection)
    all_goals = []
    for handle in handles:
        goal_list = handle.get_goals()
        goals_str = '\tGoals: {}'.format(len(goal_list))
        sims4.commands.output(goals_str, _connection)
        all_goals.extend(goal_list)
    if postures.posture_graph.enable_debug_goals_visualization:
        for constraint in constraints:
            with debugvis.Context('goal_scoring', routing_surface=constraint.routing_surface) as layer:
                for polygon in constraint.geometry.polygon:
                    layer.add_polygon(polygon, routing_surface=constraint.routing_surface)
                for goal in all_goals:
                    position = goal.location.transform.translation
                    layer.add_point(position, routing_surface=constraint.routing_surface)

@sims4.commands.Command('routing.debug.generate_routing_goals_circle', command_type=CommandType.DebugOnly)
def routing_debug_generate_routing_goals(x:float=None, y:float=None, z:float=None, radius:int=None, obj:OptionalTargetParam=None, _connection=None):
    if x is None or (y is None or z is None) or radius is None:
        sims4.commands.output('Please enter 4 floats for x,y,z and radius', _connection)
        return False
    obj = get_optional_target(obj, _connection=_connection)
    if obj is None:
        return False
    routing_component = obj.get_component(ROUTING_COMPONENT)
    if routing_component is None:
        return False
    if not postures.posture_graph.enable_debug_goals_visualization:
        sims4.commands.execute('debugvis.goals.enable', _connection)
    position = Vector3(x, y, z)
    routing_surface = routing.SurfaceIdentifier(services.current_zone_id(), 0, routing.SurfaceType.SURFACETYPE_WORLD)
    constraint = Circle(position, radius, routing_surface)
    handles = constraint.get_connectivity_handles(obj)
    handles_str = 'Handles: {}'.format(len(handles))
    sims4.commands.output(handles_str, _connection)
    all_goals = []
    for handle in handles:
        goal_list = handle.get_goals()
        goals_str = '\tGoals: {}'.format(len(goal_list))
        sims4.commands.output(goals_str, _connection)
        all_goals.extend(goal_list)
    if postures.posture_graph.enable_debug_goals_visualization:
        with debugvis.Context('goal_scoring', routing_surface=routing_surface) as layer:
            for polygon in constraint.geometry.polygon:
                layer.add_polygon(polygon, routing_surface=routing_surface)
            for goal in all_goals:
                position = goal.location.transform.translation
                layer.add_point(position, routing_surface=routing_surface)

@sims4.commands.Command('routing.debug.set_behavior')
def routing_debug_set_behavior(object_routing_behavior:TunableInstanceParam(sims4.resources.Types.SNIPPET), obj:OptionalTargetParam=None, _connection=None):
    if object_routing_behavior is None:
        return False
    obj = get_optional_target(obj)
    if obj is None:
        return False
    routing_component = obj.get_component(ROUTING_COMPONENT)
    if routing_component is None:
        return False
    timeline = services.time_service().sim_timeline
    timeline.schedule(object_routing_behavior(obj))
    return True
