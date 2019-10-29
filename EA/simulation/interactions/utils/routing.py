from protocolbuffers import DistributorOps_pb2 as protocolsfrom animation.animation_utils import flush_all_animationsfrom distributor.ops import GenericProtocolBufferOpfrom element_utils import soft_sleep_forever, build_critical_sectionfrom placement import FGLTuningfrom routing import SurfaceType, SurfaceIdentifierfrom routing.portals.portal_enums import PathSplitTypefrom routing.walkstyle.walkstyle_behavior import WalksStyleBehaviorfrom sims4.geometry import QtCircle, build_rectangle_from_two_points_and_radiusfrom sims4.tuning.tunable import Tunablefrom sims4.utils import Resultfrom teleport.teleport_helper import TeleportHelperfrom terrain import get_water_depth_at_location, get_water_depthfrom world.ocean_tuning import OceanTuningimport build_buyimport clockimport distributor.opsimport element_utilsimport elementsimport enumimport gsi_handlers.routing_handlersimport id_generatorimport objects.systemimport placementimport routingimport servicesimport sims4.logimport sims4.mathimport sims4.telemetryimport telemetry_helperlogger = sims4.log.Logger('Routing')TELEMETRY_GROUP_ROUTING = 'ROUT'TELEMETRY_HOOK_ROUTE_FAILURE = 'RTFL'TELEMETRY_FIELD_ID = 'idrt'TELEMETRY_FIELD_POSX = 'posx'TELEMETRY_FIELD_POSY = 'posy'TELEMETRY_FIELD_POSZ = 'posz'writer = sims4.telemetry.TelemetryWriter(TELEMETRY_GROUP_ROUTING)
class RouteTargetType(enum.Int, export=False):
    NONE = 1
    OBJECT = 2
    PARTS = 3

class PathNodeAction(enum.Int, export=False):
    PATH_NODE_WALK_ACTION = 0
    PATH_NODE_PORTAL_WARP_ACTION = 1
    PATH_NODE_PORTAL_WALK_ACTION = 2
    PATH_NODE_PORTAL_ANIMATE_ACTION = 3
    PATH_NODE_UNDEFINED_ACTION = 4294967295

class SlotGoal(routing.Goal):
    __slots__ = ('slot_params', 'containment_transform')

    def __init__(self, *args, containment_transform, slot_params=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.slot_params = slot_params
        self.containment_transform = containment_transform

    def __repr__(self):
        return '<SlotGoal, loc({}), containment({}), orientation({}), cost({}), params({})'.format(self.location.position, self.containment_transform, self.location.orientation, self.cost, self.slot_params)

    def clone(self):
        new_goal = type(self)(self.location, self.containment_transform)
        self._copy_data(new_goal)
        return new_goal

    def _copy_data(self, new_goal):
        super()._copy_data(new_goal)
        new_goal.slot_params = self.slot_params
        new_goal.containment_transform = self.containment_transform
        new_goal.path_id = self.path_id

    @property
    def has_slot_params(self):
        return True

class FollowPath(distributor.ops.ElementDistributionOpMixin, elements.SubclassableGeneratorElement):
    ROUTE_GATE_REQUEST = 2
    ROUTE_MINIMUM_TIME_REMAINING_FOR_CANCELLATION = 0.5
    ROUTE_SIM_POSITION_UPDATE_FREQUENCY = 1
    ROUTE_COMPARE_EPSILON = 0.001
    ROUTE_APPROXIMATE_ROUTE_CANCELLATION_TIME_PADDING = 0.5
    ROUTE_CANCELLATION_APPROX_STOP_ACTION_TIME = 0.5
    DISTANCE_TO_RECHECK_INUSE = Tunable(float, 5.0, description="Distance at which a Sim will start checking their LoS and in use on the object they're routing to and cancel if it's taken.")
    DISTANCE_TO_RECHECK_STAND_RESERVATION = Tunable(float, 3.0, description='Distance at which a Sim will stop if there are still other Sims standing in the way.')

    class Action(enum.Int, export=False):
        CONTINUE = 0
        CANCEL = 1

    @staticmethod
    def should_follow_path(sim, path):
        final_path_node = path.nodes[-1]
        final_position = sims4.math.Vector3(*final_path_node.position)
        final_orientation = sims4.math.Quaternion(*final_path_node.orientation)
        if sims4.math.vector3_almost_equal_2d(final_position, sim.position, epsilon=FollowPath.ROUTE_COMPARE_EPSILON) and (sims4.math.quaternion_almost_equal(final_orientation, sim.orientation, epsilon=FollowPath.ROUTE_COMPARE_EPSILON) or final_orientation == sims4.math.Quaternion.ZERO()) and final_path_node.routing_surface_id == sim.routing_surface:
            return False
        return True

    def __init__(self, actor, path, track_override=None, callback_fn=None, mask_override=None):
        super().__init__()
        self.actor = actor
        self.path = path
        self.id = id_generator.generate_object_id()
        self.start_time = None
        self.update_walkstyle = False
        self.track_override = track_override
        self.mask_override = mask_override
        self._callback_fn = callback_fn
        self._time_to_shave = 0
        self.wait_time = 0
        self.finished = False
        self._time_offset = 0.0
        self.canceled = False
        self.canceled_msg_sent = False
        self._sleep_element = None
        self._animation_sleep_end = 0

    def _current_time(self):
        return (services.time_service().sim_now - self.start_time).in_real_world_seconds()

    def _time_left(self, current_time):
        return clock.interval_in_real_seconds(self.path.nodes[-1].time - current_time - self._time_to_shave)

    def _next_update_interval(self, current_time):
        update_interval = clock.interval_in_real_seconds(self.ROUTE_SIM_POSITION_UPDATE_FREQUENCY)
        return update_interval

    def attach(self, *args, **kwargs):
        if hasattr(self.actor, 'on_follow_path'):
            self.actor.on_follow_path(self, True)
        super().attach(*args, **kwargs)
        self.actor.routing_component.set_follow_path(self)

    def detach(self, *args, **kwargs):
        self.actor.routing_component.clear_follow_path()
        if hasattr(self.actor, 'on_follow_path'):
            self.actor.on_follow_path(self, False)
        super().detach(*args, **kwargs)
        self.canceled = True

    def set_animation_sleep_end(self, duration):
        new_time = self._current_time() + duration
        if new_time > self._animation_sleep_end:
            self._animation_sleep_end = new_time

    def is_traversing_portal(self):
        current_time = self._current_time()
        index = self.actor.routing_component.current_path.node_at_time(current_time).index - 1
        if index < 0:
            return False
        return self.actor.routing_component.current_path.nodes[index].portal_object_id != 0

    def get_next_non_portal_node(self):
        current_time = self._current_time()
        index = self.actor.routing_component.current_path.node_at_time(current_time).index - 1
        if index < 0:
            return
        if self.actor.routing_component.current_path.nodes[index].portal_object_id == 0:
            return
        while index < len(self.actor.routing_component.current_path.nodes) - 1:
            index += 1
            node = self.actor.routing_component.current_path.nodes[index]
            if node.portal_object_id == 0:
                return node

    def is_traversing_invalid_portal(self):
        current_time = self._current_time()
        index = self.actor.routing_component.current_path.node_at_time(current_time).index - 1
        if index < 0:
            return False
        node = self.actor.routing_component.current_path.nodes[index]
        portal_object_id = node.portal_object_id
        if not portal_object_id:
            return False
        else:
            portal_object = objects.system.find_object(portal_object_id)
            if portal_object is not None:
                portal_id = node.portal_id
                if any(portal_id in portal_pair for portal_pair in portal_object.get_portal_pairs()):
                    if not routing.is_portal_valid(portal_id, self.actor.routing_context):
                        return True
                    else:
                        return False
        return False
        return True

    def get_remaining_distance(self, seconds_left):
        path_nodes = self.path.nodes
        total_distance_left = 0
        if seconds_left <= 0:
            return 0
        for index in range(len(path_nodes) - 1, 0, -1):
            cur_node = path_nodes[index]
            prev_node = path_nodes[index - 1]
            segment_time = cur_node.time - prev_node.time
            position_diff = sims4.math.Vector3(cur_node.position[0] - prev_node.position[0], cur_node.position[1] - prev_node.position[1], cur_node.position[2] - prev_node.position[2])
            segment_distance = position_diff.magnitude()
            if seconds_left > segment_time:
                total_distance_left += segment_distance
                seconds_left -= segment_time
            else:
                finished_segment_time = segment_time - seconds_left
                if finished_segment_time > 0:
                    ratio = seconds_left/segment_time
                    total_distance_left += segment_distance*ratio
                else:
                    total_distance_left += segment_distance
                return total_distance_left
        return total_distance_left

    def _hide_held_props(self):
        for si in self.actor.si_state:
            if si.preserve_held_props_during_route:
                pass
            else:
                si.animation_context.set_all_prop_visibility(False, held_only=True)

    def _run_gen(self, timeline):
        if self.actor.is_sim:
            self._hide_held_props()
        if self.actor.should_route_instantly():
            final_path_node = self.path.nodes[-1]
            final_position = sims4.math.Vector3(*final_path_node.position)
            final_orientation = sims4.math.Quaternion(*final_path_node.orientation)
            routing_surface = final_path_node.routing_surface_id
            final_position.y = services.terrain_service.terrain_object().get_routing_surface_height_at(final_position.x, final_position.z, routing_surface)
            self.actor.location = sims4.math.Location(sims4.math.Transform(final_position, final_orientation), routing_surface)
            return True
        time_debt = 0
        self._time_to_shave = 0
        self.wait_time = 0
        new_time_debt = 0
        if self.actor.is_sim:
            (teleport_routing, cost, from_tuned_liability) = self.actor.sim_info.get_active_teleport_style()
            override_teleport = self.actor.get_walkstyle() in WalksStyleBehavior.WALKSTYLES_OVERRIDE_TELEPORT and not from_tuned_liability
            routing_slave_prevents_teleport = TeleportHelper.does_routing_slave_prevent_teleport(self.actor)
            if teleport_routing is not None and not (override_teleport or routing_slave_prevents_teleport):
                final_path_node = self.path.nodes[-1]
                final_position = sims4.math.Vector3(*final_path_node.position)
                final_orientation = sims4.math.Quaternion(*final_path_node.orientation)
                final_routing_surface = final_path_node.routing_surface_id
                distance = (self.actor.position - final_position).magnitude_2d_squared()
                level = self.actor.routing_surface.secondary_id
                is_in_water = self.actor.should_be_swimming_at_position(final_position, level)
                if is_in_water or (self.path.force_ghost_route or distance > teleport_routing.teleport_min_distance) or from_tuned_liability:
                    (sequence, animation_interaction) = TeleportHelper.generate_teleport_sequence(self.actor, teleport_routing, final_position, final_orientation, final_routing_surface, cost)
                    if sequence is not None and animation_interaction is not None:
                        try:
                            result = yield from element_utils.run_child(timeline, build_critical_section(sequence, flush_all_animations))
                        finally:
                            animation_interaction.on_removed_from_queue()
                        return result
            current_zone = services.current_zone()
            if current_zone.is_zone_running or services.sim_spawner_service().sim_is_leaving(self.actor):

                def is_zone_running():
                    return current_zone.is_zone_running

                yield from element_utils.run_child(timeline, elements.BusyWaitElement(soft_sleep_forever(), is_zone_running))
            accumulator = services.current_zone().arb_accumulator_service
            if accumulator.MAXIMUM_TIME_DEBT > 0:
                time_debt = accumulator.get_time_debt((self.actor,))
                self._time_to_shave = accumulator.get_shave_time_given_duration_and_debt(self.path.duration(), time_debt)
                self.wait_time = time_debt
                new_time_debt = time_debt + self._time_to_shave
        try:
            if self.canceled:
                return False
            if self.path.nodes:
                try:
                    final_path_node = self.path.nodes[-1]
                    final_position = sims4.math.Vector3(*final_path_node.position)
                    final_orientation = self.path.final_orientation_override or sims4.math.Quaternion(*final_path_node.orientation)
                    self.actor.set_routing_path(self.path)
                    self.start_time = services.time_service().sim_now
                    if self.actor.is_sim:
                        self.start_time += clock.interval_in_real_seconds(time_debt)
                    self._time_offset = 0
                    if self.actor.primitives:
                        for primitive in tuple(self.actor.primitives):
                            if isinstance(primitive, FollowPath):
                                primitive.detach(self.actor)
                    with distributor.system.Distributor.instance().dependent_block():
                        self.attach(self.actor)
                        self.actor.routing_component.schedule_and_process_route_events_for_new_path(self.path)
                    if self.actor.is_sim:
                        self.actor.last_animation_factory = None
                        if not self.actor.posture.rerequests_idles:
                            yield from element_utils.run_child(timeline, build_critical_section(self.actor.posture.get_idle_behavior(), flush_all_animations))
                    for slave_data in self.actor.get_routing_slave_data():
                        if slave_data.slave.is_sim:
                            slave_data.slave.last_animation_factory = None
                    self._sleep_element = elements.SoftSleepElement(self._next_update_interval(self._current_time()))
                    yield from element_utils.run_child(timeline, self._sleep_element)
                    self._sleep_element = None
                    self._animation_sleep_end = 0
                    while True:
                        current_time = self._current_time() + time_debt
                        update_client = False
                        if self._callback_fn is not None:
                            time_left = self._time_left(current_time).in_real_world_seconds()
                            distance_left = self.get_remaining_distance(time_left)
                            route_action = self._callback_fn(distance_left)
                            if route_action == FollowPath.Action.CANCEL:
                                self.canceled = True
                        if self.canceled:
                            break
                        if self.finished:
                            if self.actor.routing_component.route_event_context.has_scheduled_events() or current_time > self._animation_sleep_end:
                                break
                        else:
                            if self.update_walkstyle:
                                update_client = True
                                time_offset = current_time + 0.5
                                self.actor.update_routing_path(time_offset)
                                self.update_walkstyle = False
                            else:
                                self.update_routing_location(current_time)
                            update_client |= self.actor.routing_component.update_route_events_for_current_path(self.path, current_time, self._time_offset)
                            if update_client:
                                self.send_updated_msg()
                        if current_time > self.path.nodes[-1].time*2.0 + 5.0:
                            break
                        next_interval = self._next_update_interval(current_time)
                        self._sleep_element = elements.SoftSleepElement(next_interval)
                        yield from element_utils.run_child(timeline, self._sleep_element)
                        self._sleep_element = None
                    if not self.canceled_msg_sent:
                        cancellation_info = self.choose_cancellation_time()
                        if cancellation_info:
                            (transform, routing_surface) = self.path.get_location_data_at_time(cancellation_info[0])
                            location = self.actor.location.clone(routing_surface=routing_surface, transform=transform)
                            self.send_canceled_msg(cancellation_info[0], transform.orientation)
                            self.canceled_msg_sent = True
                            if location.parent is not None:
                                interaction = self.actor.transition_controller.interaction if self.actor.transition_controller is not None else None
                                logger.error('{} is following a path but was somehow parented to {}. Interaction: {}', self.actor, location.parent, interaction)
                            self.path.add_intended_location_to_quadtree(location)
                            if self.actor.is_sim:
                                with telemetry_helper.begin_hook(writer, TELEMETRY_HOOK_ROUTE_FAILURE, sim=self.actor) as hook:
                                    hook.write_int(TELEMETRY_FIELD_ID, self.id)
                                    hook.write_float(TELEMETRY_FIELD_POSX, transform.translation.x)
                                    hook.write_float(TELEMETRY_FIELD_POSY, transform.translation.y)
                                    hook.write_float(TELEMETRY_FIELD_POSZ, transform.translation.z)
                            self.actor.location = location
                            self.actor.update_slave_positions_for_path(self.path, transform, transform.orientation, routing_surface, canceled=True)
                            while True:
                                if self.finished:
                                    break
                                current_time = self._current_time()
                                if current_time > self.path.nodes[-1].time*2.0 + 5.0:
                                    break
                                next_interval = self._next_update_interval(current_time)
                                self._sleep_element = elements.SoftSleepElement(next_interval)
                                yield from element_utils.run_child(timeline, self._sleep_element)
                                self._sleep_element = None
                            return False
                        with telemetry_helper.begin_hook(writer, TELEMETRY_HOOK_ROUTE_FAILURE) as hook:
                            hook.write_int(TELEMETRY_FIELD_ID, self.id)
                    routing_surface = final_path_node.routing_surface_id
                    final_position.y = services.terrain_service.terrain_object().get_routing_surface_height_at(final_position.x, final_position.z, routing_surface)
                    transform = sims4.math.Transform(final_position, final_orientation)
                    self.actor.location = self.actor.location.clone(routing_surface=routing_surface, transform=transform)
                    self.actor.update_slave_positions_for_path(self.path, transform, final_orientation, routing_surface)
                finally:
                    self.detach(self.actor)
                    self.actor.set_routing_path(None)
                    self._sleep_element = None
            return True
        finally:
            if self.actor.is_sim and accumulator.MAXIMUM_TIME_DEBT > 0:
                accumulator.set_time_debt((self.actor,), new_time_debt)

    def _soft_stop(self):
        self.canceled = True
        if self._sleep_element is not None:
            self._sleep_element.trigger_soft_stop()
        return True

    def update_routing_location(self, current_time=None):
        if current_time is None:
            current_time = self._current_time()
        (transform, routing_surface) = self.path.get_location_data_at_time(current_time)
        location = self.actor.location.clone(routing_surface=routing_surface, transform=transform)
        self.actor.set_location_without_distribution(location)
        self.actor.update_slave_positions_for_path(self.path, transform, location.transform.orientation, routing_surface, distribute=False)

    def get_approximate_cancel_location(self):
        cancellation_info = self.choose_cancellation_time()
        if cancellation_info is None:
            return
        time = cancellation_info[0] + self.ROUTE_APPROXIMATE_ROUTE_CANCELLATION_TIME_PADDING
        return self.path.get_location_data_at_time(time)

    def _get_routing_polygon(self, actor, translation, orientation):
        routing_context = actor.get_routing_context()
        routing_polygon = routing_context.get_quadtree_polygon(translation, orientation)
        if isinstance(routing_polygon, QtCircle):
            length_vector = orientation.transform_vector(sims4.math.Vector3.Z_AXIS())*routing_polygon.radius/2
            routing_polygon = build_rectangle_from_two_points_and_radius(translation + length_vector, translation - length_vector, routing_polygon.radius)
        return routing_polygon

    def _get_routing_polygons(self, actor, transform):
        routing_polygons = []
        routing_polygon = self._get_routing_polygon(actor, transform.translation, transform.orientation)
        if routing_polygon is not None:
            routing_polygons.append(routing_polygon)
        for slave_data in actor.get_routing_slave_data():
            offset = sims4.math.Vector3.ZERO()
            for attachment_info in slave_data.attachment_info_gen():
                offset.x = offset.x + attachment_info.parent_offset.x - attachment_info.offset.x
                offset.z = offset.z + attachment_info.parent_offset.y - attachment_info.offset.y
            transformed_point = transform.transform_point(offset)
            slave_polygon = self._get_routing_polygon(slave_data.slave, transformed_point, transform.orientation)
            if slave_polygon is not None:
                routing_polygons.append(slave_polygon)
        return routing_polygons

    def choose_cancellation_time(self):
        path_duration = self.path.duration()
        if path_duration > 0:
            server_delay = (services.time_service().sim_timeline.future - services.time_service().sim_now).in_real_world_seconds()
            min_time = self.ROUTE_MINIMUM_TIME_REMAINING_FOR_CANCELLATION + server_delay
            current_time = (services.time_service().sim_now - self.start_time).in_real_world_seconds() - self._time_offset
            min_time = max(min_time, self._animation_sleep_end - current_time)
            fallback_for_ladder = None
            while path_duration - current_time > min_time:
                cancellation_time = current_time + min_time
                cancel_node = self.path.node_at_time(cancellation_time)
                if cancel_node is None:
                    return
                if cancel_node.index > 0:
                    cancel_node = self.path.nodes[cancel_node.index - 1]
                while cancel_node.action != PathNodeAction.PATH_NODE_WALK_ACTION:
                    cancel_node = self.path.nodes[cancel_node.index + 1]
                    cancellation_time = cancel_node.time
                routing_surface_id = cancel_node.routing_surface_id
                (transform, _) = self.path.get_location_data_at_time(cancellation_time)
                for _ in placement.get_nearby_sims_gen(transform.translation, routing_surface_id, radius=routing.get_default_agent_radius(), exclude=[self.actor], stop_at_first_result=True, only_sim_position=False, only_sim_intended_position=False):
                    break
                routing_polygons = self._get_routing_polygons(self.actor, transform)
                if self.path.nodes[cancel_node.index - 1].action == PathNodeAction.PATH_NODE_PORTAL_ANIMATE_ACTION:
                    fallback_for_ladder = (cancellation_time, self.ROUTE_CANCELLATION_APPROX_STOP_ACTION_TIME + (cancellation_time - current_time))
                all_placements_passed = True
                for routing_polygon in routing_polygons:
                    if routing.test_polygon_placement_in_navmesh(routing_surface_id, routing_polygon) == False:
                        all_placements_passed = False
                        break
                if fallback_for_ladder is not None and cancel_node.index > 0 and all_placements_passed:
                    return (cancellation_time, self.ROUTE_CANCELLATION_APPROX_STOP_ACTION_TIME + (cancellation_time - current_time))
                else:
                    current_time = cancellation_time
                    if fallback_for_ladder is None:
                        return
                    else:
                        return fallback_for_ladder
        if fallback_for_ladder is None:
            return
        else:
            return fallback_for_ladder

    def write(self, msg):
        if self.actor.should_route_instantly():
            return
        try:
            msg_src = distributor.ops.create_route_msg_src(self.id, self.actor, self.path, self.start_time, self.wait_time, track_override=self.track_override, mask_override=self.mask_override)
            self.actor.routing_component.append_route_events_to_route_msg(msg_src)
            self.serialize_op(msg, msg_src, protocols.Operation.FOLLOW_ROUTE)
        except Exception as e:
            logger.error('_FollowPath.write: {0}', e)

    def distribute_path_asynchronously(self):
        self._hide_held_props()
        accumulator = services.current_zone().arb_accumulator_service
        time_debt = 0
        if accumulator.MAXIMUM_TIME_DEBT > 0:
            time_debt = accumulator.get_time_debt((self.actor,))
        start_time = services.time_service().sim_now + clock.interval_in_real_seconds(time_debt)
        wait_time = time_debt
        try:
            self.actor.set_routing_path(self.path)
            self.actor.routing_component.schedule_and_process_route_events_for_new_path(self.path)
            with distributor.system.Distributor.instance().dependent_block():
                msg_src = distributor.ops.create_route_msg_src(self.id, self.actor, self.path, start_time, wait_time, track_override=self.track_override, mask_override=self.mask_override)
                self.actor.routing_component.append_route_events_to_route_msg(msg_src)
                msg = GenericProtocolBufferOp(protocols.Operation.FOLLOW_ROUTE, msg_src)
                distributor.system.Distributor.instance().add_op(self.actor, msg)
        except Exception as e:
            logger.error('FollowPath asynchronous route: {0}', e)
        finally:
            final_path_node = self.path.nodes[-1]
            final_position = sims4.math.Vector3(*final_path_node.position)
            routing_surface = final_path_node.routing_surface_id
            final_position.y = services.terrain_service.terrain_object().get_routing_surface_height_at(final_position.x, final_position.z, routing_surface)
            final_orientation = sims4.math.Quaternion(*final_path_node.orientation)
            transform = sims4.math.Transform(final_position, final_orientation)
            self.actor.move_to(routing_surface=routing_surface, transform=transform)
            self.actor.set_routing_path(None)

    def send_canceled_msg(self, time, orientation):
        cancel_op = distributor.ops.RouteCancel(self.id, time, orientation)
        distributor.ops.record(self.actor, cancel_op)

    def send_updated_msg(self):
        with distributor.system.Distributor.instance().dependent_block():
            op = distributor.ops.RouteUpdate(self.id, self.actor, self.path, self.start_time, self.wait_time, track_override=self.track_override)
            distributor.ops.record(self.actor, op)
            self.actor.routing_component.process_updated_route_events()

    def request_walkstyle_update(self):
        self.update_walkstyle = True
        if self._sleep_element is not None:
            self._sleep_element.trigger_soft_stop()

    def route_finished(self, path_id):
        if self.id == path_id:
            self.finished = True
            if self._sleep_element is not None:
                self._sleep_element.trigger_soft_stop()
        else:
            logger.debug("Routing: route_finished current path id doesn't match, ignoring. This can happen when the client is running way behind the server or the route was cancelled")

    def route_time_update(self, path_id, current_client_time):
        if self.id == path_id:
            self._time_offset = self._current_time() - current_client_time
        else:
            logger.debug("Routing: route_time_update current path id doesn't match, ignoring.")

class PlanRoute(elements.SubclassableGeneratorElement):

    def __init__(self, route, sim, reserve_final_location=True, is_failure_route=False, interaction=None):
        super().__init__()
        self.route = route
        self.path = routing.Path(sim, route)
        self.sim = sim
        self.reserve_final_location = reserve_final_location
        self._is_failure_route = is_failure_route
        self._interaction = interaction

    @classmethod
    def shortname(cls):
        return 'PlanRoute'

    def _run_gen(self, timeline):
        context = self.route.context
        force_ghost = False
        try:
            effective_ghost_route = context.ghost_route
            effective_discourage_key_mask = context.get_discourage_key_mask()
            teleport_style_data = None
            if self.sim.is_sim:
                teleport_style_data = TeleportHelper.get_teleport_style_data_used_for_interaction_route(self.sim, self._interaction)
                from carry.carry_utils import get_carried_objects_gen
                for (_, _, carry_object) in get_carried_objects_gen(self.sim):
                    if carry_object.is_sim and not carry_object.routing_context.ghost_route:
                        context.ghost_route = False
                        break
                if context.ghost_route:
                    routing_slave_data = self.sim.get_routing_slave_data()
                    for data in routing_slave_data:
                        if not data.slave.get_routing_context().ghost_route:
                            context.ghost_route = False
                            break
                wading_interval = OceanTuning.get_actor_wading_interval(self.sim)
            else:
                teleport_style_data = None
                wading_interval = None
            if teleport_style_data is not None:
                conectivity_result = routing.test_connectivity_pt_pt(self.sim.routing_location, self.path.route.goals[0].location, self.sim.routing_context)
                if not conectivity_result:
                    context.ghost_route = True
                    force_ghost = True
            if effective_ghost_route or wading_interval is not None:
                start_location = self.sim.routing_location
                water_height_at_start_location = get_water_depth_at_location(start_location)
                target_location = self.path.route.goals[0].location
                water_height_at_target_location = get_water_depth_at_location(target_location)
                if water_height_at_start_location > wading_interval.lower_bound or water_height_at_target_location > wading_interval.lower_bound:
                    context.set_discourage_key_mask(effective_discourage_key_mask | routing.FOOTPRINT_DISCOURAGE_KEY_LANDINGSTRIP)
            if self.path.status == routing.Path.PLANSTATUS_NONE:
                yield from self.generate_path(timeline)
            if effective_ghost_route or teleport_style_data is not None:
                path_final_location = self.path.final_location
                if path_final_location is not None:
                    sim_target_distance = (path_final_location.position - self.sim.routing_location.position).magnitude_squared()
                    if sim_target_distance < teleport_style_data.teleport_min_distance and self.path.length_squared() > teleport_style_data.teleport_min_distance and self.path.portal_obj is None:
                        context.ghost_route = True
                        force_ghost = True
                        yield from self.generate_path(timeline)
            self.path.force_ghost_route = force_ghost
            context.path_goals_id = 0
            if self.path.status == routing.Path.PLANSTATUS_READY:
                if self.reserve_final_location:
                    self.path.add_destination_to_quad_tree()
                return True
            return False
        finally:
            context.ghost_route = effective_ghost_route
            context.set_discourage_key_mask(effective_discourage_key_mask)

    def generate_path(self, timeline):
        start_time = services.time_service().sim_now
        ticks = 0
        try:
            self.path.status = routing.Path.PLANSTATUS_PLANNING
            self.path.nodes.clear_route_data()
            if not self.route.goals:
                self.path.status = routing.Path.PLANSTATUS_FAILED
            else:
                for goal in self.route.goals:
                    self.path.add_goal(goal)
                for origin in self.route.origins:
                    self.path.add_start(origin)
                for (waypoint_group, waypoints) in enumerate(self.route.waypoints):
                    for waypoint in waypoints:
                        waypoint.group = waypoint_group
                        self.path.add_waypoint(waypoint)
                self.sim.routing_component.on_plan_path(self.route.goals, True)
                if self.path.nodes.make_path() is True:
                    plan_in_progress = True

                    def is_planning_done():
                        nonlocal ticks, plan_in_progress
                        ticks += 1
                        plan_in_progress = self.path.nodes.plan_in_progress
                        return not plan_in_progress

                    yield from element_utils.run_child(timeline, elements.BusyWaitElement(soft_sleep_forever(), is_planning_done))
                    if plan_in_progress:
                        self.path.status = routing.Path.PLANSTATUS_FAILED
                    else:
                        self.path.nodes.finalize(self._is_failure_route)
                else:
                    self.path.status = routing.Path.PLANSTATUS_FAILED
                new_route = routing.Route(self.route.origin, self.route.goals, additional_origins=self.route.origins, routing_context=self.route.context)
                new_route.path.copy(self.route.path)
                new_path = routing.Path(self.path.sim, new_route)
                new_path.status = self.path.status
                new_path.start_ids = self.path.start_ids
                new_path.goal_ids = self.path.goal_ids
                result_path = new_path
                if gsi_handlers.routing_handlers.archiver.enabled:
                    gsi_handlers.routing_handlers.archive_plan(self.sim, self.path, ticks, (services.time_service().sim_now - start_time).in_real_world_seconds())
                num_nodes = len(new_path.nodes)
                if num_nodes > 0 and self.sim.is_sim:
                    start_index = 0
                    current_index = 0
                    object_manager = services.object_manager(services.current_zone_id())
                    for n in self.path.nodes:
                        if n.portal_object_id != 0:
                            portal_id = n.portal_id
                            portal_object = object_manager.get(n.portal_object_id)
                            if portal_object is not None:
                                path_split_type = portal_object.split_path_on_portal(portal_id)
                                if path_split_type == PathSplitType.PathSplitType_Split:
                                    (new_path, start_index) = self._split_path_at_portal(start_index, current_index, new_path, portal_object, portal_id, start_time, ticks, num_nodes)
                                elif path_split_type == PathSplitType.PathSplitType_LadderSplit:
                                    (new_path, start_index) = self._split_path_at_ladder_portal(start_index, current_index, new_path, portal_object, portal_id)
                        current_index += 1
                    if new_path is not None and start_index > 0:
                        end_index = current_index - 1
                        new_path.nodes.clip_nodes(start_index, end_index)
                        if gsi_handlers.routing_handlers.archiver.enabled:
                            gsi_handlers.routing_handlers.archive_plan(self.sim, new_path, ticks, (services.time_service().sim_now - start_time).in_real_world_seconds())
                self.route = result_path.route
                self.path = result_path
                self.sim.routing_component.on_plan_path(self.route.goals, False)
        except Exception:
            logger.exception('Exception in generate_path')
            self.path.status = routing.Path.PLANSTATUS_FAILED
            self.sim.routing_component.on_plan_path(self.route.goals, False)
        if self.path.status == routing.Path.PLANSTATUS_PLANNING:
            self.path.set_status(routing.Path.PLANSTATUS_READY)
        else:
            self.path.set_status(routing.Path.PLANSTATUS_FAILED)

    def _split_path_at_portal(self, start_index, current_index, new_path, portal_object, portal_id, start_time, ticks, num_nodes):
        logger.assert_raise(start_index < current_index, 'Start index is less than current index while trying to split paths.')
        new_path.nodes.clip_nodes(start_index, current_index)
        start_index = current_index + 1
        if gsi_handlers.routing_handlers.archiver.enabled:
            gsi_handlers.routing_handlers.archive_plan(self.sim, new_path, ticks, (services.time_service().sim_now - start_time).in_real_world_seconds())
        if start_index < num_nodes:
            new_route = routing.Route(self.route.origin, self.route.goals, additional_origins=self.route.origins, routing_context=self.route.context)
            new_route.path.copy(self.route.path)
            next_path = routing.Path(self.path.sim, new_route)
            next_path.status = self.path.status
            next_path.start_ids = self.path.start_ids
            next_path.goal_ids = self.path.goal_ids
            new_path.portal_obj = portal_object.get_portal_owner(portal_id)
            new_path.portal_id = portal_id
            new_path.next_path = next_path
            new_path = next_path
        else:
            new_path = None
        return (new_path, start_index)

    def _split_path_at_ladder_portal(self, start_index, current_index, new_path, portal_object, portal_id):
        new_path.nodes.clip_nodes(start_index, current_index + 1)
        new_path.portal_obj = portal_object.get_portal_owner(portal_id)
        new_path.portal_id = portal_id
        portal_inst = portal_object.get_portal_by_id(portal_id)
        portal_loc = portal_inst.get_portal_locations(portal_id)[1]
        new_path.final_orientation_override = portal_loc.orientation
        second_route = routing.Route(self.route.origin, self.route.goals, additional_origins=self.route.origins, routing_context=self.route.context)
        second_route.path.copy(self.route.path)
        second_path = routing.Path(self.path.sim, second_route)
        second_path.status = self.path.status
        second_path.start_ids = self.path.start_ids
        second_path.goal_ids = self.path.goal_ids
        new_path.next_path = second_path
        return (second_path, current_index + 1)

def get_route_element_for_path(sim, path, interaction=None, lockout_target=None, handle_failure=False, callback_fn=None, force_follow_path=False, track_override=None, mask_override=None):
    routing_agent = sim
    parent_obj = sim.parent
    if not parent_obj.routing_component is None:
        routing_agent = parent_obj

    def route_gen(timeline):
        result = yield from do_route(timeline, routing_agent, path, lockout_target, handle_failure, interaction=interaction, callback_fn=callback_fn, force_follow_path=force_follow_path, track_override=track_override, mask_override=mask_override)
        return result

    return route_gen

def do_route(timeline, agent, path, lockout_target, handle_failure, interaction=None, callback_fn=None, force_follow_path=False, track_override=None, mask_override=None):
    from autonomy.autonomy_modes import AutonomyMode

    def _route(timeline):
        origin_location = agent.routing_location
        agent_is_sim = agent.is_sim
        if path.status == routing.Path.PLANSTATUS_READY:
            if force_follow_path or not FollowPath.should_follow_path(agent, path):
                if callback_fn is not None:
                    result = callback_fn(0)
                    if result == FollowPath.Action.CANCEL:
                        return False
                return True
            distance_left = path.length()
            if callback_fn is not None and distance_left < FollowPath.DISTANCE_TO_RECHECK_INUSE:
                route_action = callback_fn(distance_left)
                if route_action == FollowPath.Action.CANCEL:
                    return False
            if agent.position != origin_location.position:
                logger.error("Route-to-position has outdated starting location. Sim's position ({}) is {:0.2f}m from the original starting position ({})", agent.position, (agent.position - origin_location.position).magnitude(), origin_location.position)
            sequence = FollowPath(agent, path, callback_fn=callback_fn, track_override=track_override, mask_override=mask_override)
            if agent_is_sim:
                for buff in agent.get_active_buff_types():
                    periodic_stat_change = buff.routing_periodic_stat_change
                    if periodic_stat_change is None:
                        pass
                    else:
                        sequence = periodic_stat_change(interaction, sequence=sequence)
                sequence = agent.with_skill_bar_suppression(sequence=sequence)
            if interaction is not None and path.is_route_fail():
                if handle_failure:
                    yield from element_utils.run_child(timeline, sequence)
                if lockout_target is not None and agent_is_sim:
                    agent.add_lockout(lockout_target, AutonomyMode.LOCKOUT_TIME)
                return Result.ROUTE_FAILED
            critical_element = elements.WithFinallyElement(sequence, lambda _: path.remove_intended_location_from_quadtree())
            result = yield from element_utils.run_child(timeline, critical_element)
            return result
        if lockout_target is not None and agent_is_sim:
            agent.add_lockout(lockout_target, AutonomyMode.LOCKOUT_TIME)
        return Result.ROUTE_PLAN_FAILED

    result = yield from _route(timeline)
    return result

class PoolSurfaceOverride:

    def __init__(self, water_depth, model_suite_state_index=None):
        self.water_depth = water_depth
        self.model_suite_state_index = model_suite_state_index

def get_fgl_context_for_jig_definition(jig_definition, sim, target_sim=None, ignore_sim=True, max_dist=None, height_tolerance=None, stay_outside=False, stay_in_connectivity_group=True, ignore_restrictions=False, fallback_routing_surface=None, object_id=None, participant_to_face=None, facing_radius=None, stay_on_world=False, use_intended_location=True, model_suite_state_index=None, force_pool_surface_water_depth=None, min_water_depth=None, max_water_depth=None, fallback_starting_position=None, fallback_min_water_depth=None, fallback_max_water_depth=None):
    max_facing_angle_diff = sims4.math.PI*2
    if max_dist is None:
        max_dist = FGLTuning.MAX_FGL_DISTANCE
    if target_sim is None:
        relative_obj = sim
        if ignore_sim:
            ignored_object_ids = (sim.id,)
        else:
            ignored_object_ids = None
    else:
        relative_obj = target_sim
        ignored_object_ids = (sim.id, target_sim.id)
    if relative_obj.parent is not None:
        relative_obj = relative_obj.parent
    if use_intended_location:
        if relative_obj.routing_component is not None:
            (reference_transform, reference_routing_surface) = relative_obj.routing_component.get_approximate_cancel_location()
        else:
            reference_transform = relative_obj.intended_transform
            reference_routing_surface = relative_obj.intended_routing_surface
        if not placement.surface_supports_object_placement(reference_routing_surface, jig_definition.id):
            reference_transform = relative_obj.transform
            reference_routing_surface = relative_obj.routing_surface
    else:
        reference_transform = relative_obj.transform
        reference_routing_surface = relative_obj.routing_surface
    if force_pool_surface_water_depth is not None:
        depth = get_water_depth(reference_transform.translation.x, reference_transform.translation.z, reference_routing_surface.secondary_id)
        if force_pool_surface_water_depth.water_depth < depth:
            reference_routing_surface = SurfaceIdentifier(reference_routing_surface.primary_id, reference_routing_surface.secondary_id, SurfaceType.SURFACETYPE_POOL)
            if force_pool_surface_water_depth.model_suite_state_index is not None:
                model_suite_state_index = force_pool_surface_water_depth.model_suite_state_index
            if min_water_depth is None:
                min_water_depth = force_pool_surface_water_depth.water_depth
            else:
                min_water_depth = max(min_water_depth, force_pool_surface_water_depth.water_depth)
        elif max_water_depth is None:
            max_water_depth = force_pool_surface_water_depth.water_depth
        else:
            max_water_depth = min(max_water_depth, force_pool_surface_water_depth.water_depth)
    reference_forward = reference_transform.orientation.transform_vector(relative_obj.forward_direction_for_picking)
    if reference_routing_surface.type != SurfaceType.SURFACETYPE_POOL and relative_obj.is_sim:
        additional_interaction_jig_fgl_distance = relative_obj.posture_state.body.additional_interaction_jig_fgl_distance
    else:
        additional_interaction_jig_fgl_distance = 0
    starting_position = reference_transform.translation
    if fallback_routing_surface is not None and not placement.surface_supports_object_placement(reference_routing_surface, jig_definition.id):
        fgl_routing_surface = fallback_routing_surface
        if fallback_starting_position is not None:
            starting_position = fallback_starting_position
        min_water_depth = fallback_min_water_depth
        max_water_depth = fallback_max_water_depth
    elif stay_on_world:
        if relative_obj.level is None:
            fgl_level = sim.level
        else:
            fgl_level = relative_obj.level
        fgl_routing_surface = routing.SurfaceIdentifier(services.current_zone_id(), fgl_level, routing.SurfaceType.SURFACETYPE_WORLD)
    elif stay_outside:
        fgl_routing_surface = routing.SurfaceIdentifier(services.current_zone_id(), 0, routing.SurfaceType.SURFACETYPE_WORLD)
    else:
        fgl_routing_surface = reference_routing_surface
    if additional_interaction_jig_fgl_distance != 0:
        extended_transform = sims4.math.Transform(reference_transform.translation, reference_transform.orientation)
        extended_position = starting_position + reference_forward*additional_interaction_jig_fgl_distance
        extended_transform.translation = extended_position
        (result, _) = relative_obj.check_line_of_sight(extended_transform, verbose=True)
        if result == routing.RAYCAST_HIT_TYPE_NONE:
            starting_position = extended_position
    search_flags = placement.FGLSearchFlag.SHOULD_TEST_ROUTING | placement.FGLSearchFlag.ALLOW_TOO_CLOSE_TO_OBSTACLE | placement.FGLSearchFlag.CALCULATE_RESULT_TERRAIN_HEIGHTS
    if stay_in_connectivity_group:
        search_flags |= placement.FGLSearchFlag.STAY_IN_CONNECTED_CONNECTIVITY_GROUP
    if stay_outside:
        search_flags |= placement.FGLSearchFlag.STAY_OUTSIDE
    if object_id is not None:
        search_flags |= placement.FGLSearchFlag.SHOULD_TEST_BUILDBUY
    if participant_to_face is not None and facing_radius is not None:
        starting_location = placement.create_starting_location(participant_to_face.position, routing_surface=fgl_routing_surface)
        if ignore_restrictions:
            restrictions = None
        else:
            restrictions = (sims4.geometry.RelativeFacingWithCircle(participant_to_face.position, sims4.math.PI, facing_radius),)
        offset_restrictions = None
    else:
        starting_location = placement.create_starting_location(position=starting_position, orientation=reference_transform.orientation, routing_surface=fgl_routing_surface)
        if ignore_restrictions:
            restrictions = None
            offset_restrictions = None
        else:
            facing_angle = sims4.math.yaw_quaternion_to_angle(reference_transform.orientation)
            restrictions = (sims4.geometry.AbsoluteOrientationRange(min_angle=facing_angle - max_facing_angle_diff, max_angle=facing_angle + max_facing_angle_diff, ideal_angle=facing_angle, weight=1.0),)
            offset_restrictions = (sims4.geometry.RelativeFacingRange(reference_transform.translation, max_facing_angle_diff*2),)
    score_max_dist = max(max_dist, 2.0*(reference_transform.translation - starting_location.transform.translation).magnitude())
    scoring_functions = (placement.ScoringFunctionRadial(reference_transform.translation, 0, 0, score_max_dist),)
    object_footprint = jig_definition.get_footprint(0 if model_suite_state_index is None else model_suite_state_index)
    try:
        (lower_bound, upper_bound) = placement.get_placement_footprint_bounds(object_footprint)
        delta_x = upper_bound.x - lower_bound.x
        delta_z = upper_bound.z - lower_bound.z
        position_increment = min(delta_x, delta_z)*placement.FGL_FOOTPRINT_POSITION_INCREMENT_MULTIPLIER
        position_increment = max(position_increment, placement.FGL_DEFAULT_POSITION_INCREMENT)
    except RuntimeError:
        position_increment = placement.FGL_DEFAULT_POSITION_INCREMENT
    fgl_context = placement.FindGoodLocationContext(starting_location, routing_context=sim.routing_context, ignored_object_ids=ignored_object_ids, max_distance=max_dist, height_tolerance=height_tolerance, restrictions=restrictions, offset_restrictions=offset_restrictions, scoring_functions=scoring_functions, object_id=object_id, object_def_state_index=model_suite_state_index, object_footprints=(object_footprint,), max_results=1, max_steps=10, search_flags=search_flags, min_water_depth=min_water_depth, max_water_depth=max_water_depth, position_increment=position_increment)
    return fgl_context

def get_two_person_transforms_for_jig(jig_definition, jig_transform, routing_surface, sim_index, target_index):
    object_slots = jig_definition.get_slots_resource(0)
    slot_transform_sim = object_slots.get_slot_transform_by_index(sims4.ObjectSlots.SLOT_ROUTING, sim_index)
    sim_transform = sims4.math.Transform.concatenate(slot_transform_sim, jig_transform)
    slot_transform_target = object_slots.get_slot_transform_by_index(sims4.ObjectSlots.SLOT_ROUTING, target_index)
    target_transform = sims4.math.Transform.concatenate(slot_transform_target, jig_transform)
    return (sim_transform, target_transform, routing_surface)

def get_transforms_for_jig(jig_definition, jig_transform, num_of_sims):
    sim_index = 0
    transform_result = []
    object_slots = jig_definition.get_slots_resource(0)
    while sim_index < num_of_sims:
        slot_transform = object_slots.get_slot_transform_by_index(sims4.ObjectSlots.SLOT_ROUTING, sim_index)
        sim_transform = sims4.math.Transform.concatenate(slot_transform, jig_transform)
        transform_result.append(sim_transform)
        sim_index += 1
    return transform_result

def fgl_and_get_two_person_transforms_for_jig(jig_definition, sim, sim_index, target_sim, target_index, stay_outside, constraint_polygon=None, fallback_routing_surface=None, **kwargs):
    if constraint_polygon is None:
        key = (sim.id, sim_index, target_sim.id, target_index, jig_definition.id)
        data = target_sim.two_person_social_transforms.get(key)
        if data is not None:
            return data
    else:
        key = None
    fgl_context = get_fgl_context_for_jig_definition(jig_definition, sim, target_sim, height_tolerance=FGLTuning.SOCIAL_FGL_HEIGHT_TOLERANCE, stay_outside=stay_outside, fallback_routing_surface=fallback_routing_surface, **kwargs)
    if constraint_polygon is not None:
        if isinstance(constraint_polygon, sims4.geometry.CompoundPolygon):
            for cp in constraint_polygon:
                fgl_context.search_strategy.add_scoring_function(placement.ScoringFunctionPolygon(cp))
        else:
            fgl_context.search_strategy.add_scoring_function(placement.ScoringFunctionPolygon(constraint_polygon))
    (position, orientation) = placement.find_good_location(fgl_context)
    if position is None or orientation is None:
        result = (None, None, None)
    else:
        jig_transform = sims4.math.Transform(position, orientation)
        result = get_two_person_transforms_for_jig(jig_definition, jig_transform, fgl_context.search_strategy.start_location.routing_surface, sim_index, target_index)
    if key is not None:
        target_sim.two_person_social_transforms[key] = result
    return result
