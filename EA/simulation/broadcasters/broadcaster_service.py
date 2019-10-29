from _collections import defaultdictfrom _weakrefset import WeakSetfrom collections import namedtuplefrom alarms import add_alarm_real_time, cancel_alarm, add_alarmfrom clock import interval_in_real_secondsfrom indexed_manager import CallbackTypesfrom routing.route_enums import RouteEventTypefrom sims4.callback_utils import CallableListfrom sims4.service_manager import Servicefrom sims4.tuning.tunable import TunableRealSecondimport servicesimport sims4.geometryimport sims4.logimport sims4.mathlogger = sims4.log.Logger('Broadcaster', default_owner='epanero')
class BroadcasterService(Service):
    INTERVAL = TunableRealSecond(description='\n        The time between broadcaster pulses. A lower number will impact\n        performance.\n        ', default=5)
    DEFAULT_QUADTREE_RADIUS = 0.1

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._alarm_handle = None
        self._processing_task = None
        self._on_update_callbacks = CallableList()
        self._pending_broadcasters = []
        self._active_broadcasters = []
        self._cluster_requests = {}
        self._object_cache = None
        self._object_cache_tags = None
        self._pending_update = False
        self._quadtrees = defaultdict(sims4.geometry.QuadTree)

    def create_update_alarm(self):
        self._alarm_handle = add_alarm(self, interval_in_real_seconds(self.INTERVAL), self._on_update, repeating=True, use_sleep_time=False)

    def start(self):
        self.create_update_alarm()
        object_manager = services.object_manager()
        object_manager.register_callback(CallbackTypes.ON_OBJECT_LOCATION_CHANGED, self._update_object_cache)
        object_manager.register_callback(CallbackTypes.ON_OBJECT_ADD, self._update_object_cache)
        services.current_zone().wall_contour_update_callbacks.append(self._on_wall_contours_changed)

    def stop(self):
        if self._alarm_handle is not None:
            cancel_alarm(self._alarm_handle)
            self._alarm_handle = None
        if self._processing_task is not None:
            self._processing_task.stop()
            self._processing_task = None
        object_manager = services.object_manager()
        object_manager.unregister_callback(CallbackTypes.ON_OBJECT_LOCATION_CHANGED, self._update_object_cache)
        object_manager.unregister_callback(CallbackTypes.ON_OBJECT_ADD, self._update_object_cache)
        services.current_zone().wall_contour_update_callbacks.remove(self._on_wall_contours_changed)

    def add_broadcaster(self, broadcaster):
        if broadcaster not in self._pending_broadcasters:
            self._pending_broadcasters.append(broadcaster)
            if broadcaster.immediate:
                self._pending_update = True
            self._on_update_callbacks()

    def remove_broadcaster(self, broadcaster):
        if broadcaster in self._pending_broadcasters:
            self._pending_broadcasters.remove(broadcaster)
        if broadcaster in self._active_broadcasters:
            self._remove_from_cluster_request(broadcaster)
            self._remove_broadcaster_from_quadtree(broadcaster)
            self._active_broadcasters.remove(broadcaster)
        broadcaster.on_removed()
        self._on_update_callbacks()

    def _activate_pending_broadcasters(self):
        for broadcaster in self._pending_broadcasters:
            self._active_broadcasters.append(broadcaster)
            self.update_cluster_request(broadcaster)
            self._update_object_cache()
        self._pending_broadcasters.clear()

    def _add_broadcaster_to_quadtree(self, broadcaster):
        self._remove_broadcaster_from_quadtree(broadcaster)
        broadcaster_quadtree = self._quadtrees[broadcaster.routing_surface.secondary_id]
        broadcaster_bounds = sims4.geometry.QtCircle(sims4.math.Vector2(broadcaster.position.x, broadcaster.position.z), self.DEFAULT_QUADTREE_RADIUS)
        broadcaster_quadtree.insert(broadcaster, broadcaster_bounds)
        return broadcaster_quadtree

    def _remove_broadcaster_from_quadtree(self, broadcaster):
        broadcaster_quadtree = broadcaster.quadtree
        if broadcaster_quadtree is not None:
            broadcaster_quadtree.remove(broadcaster)

    def update_cluster_request(self, broadcaster):
        if broadcaster not in self._active_broadcasters:
            return
        clustering_request = broadcaster.get_clustering()
        if clustering_request is None:
            return
        self._remove_from_cluster_request(broadcaster)
        cluster_request_key = (type(broadcaster), broadcaster.routing_surface.secondary_id)
        if cluster_request_key in self._cluster_requests:
            cluster_request = self._cluster_requests[cluster_request_key]
            cluster_request.set_object_dirty(broadcaster)
        else:
            cluster_quadtree = self._quadtrees[broadcaster.routing_surface.secondary_id]
            cluster_request = clustering_request(lambda : self._get_broadcasters_for_cluster_request_gen(*cluster_request_key), quadtree=cluster_quadtree)
            self._cluster_requests[cluster_request_key] = cluster_request
        quadtree = self._add_broadcaster_to_quadtree(broadcaster)
        broadcaster.on_added_to_quadtree_and_cluster_request(quadtree, cluster_request)

    def _remove_from_cluster_request(self, broadcaster):
        cluster_request = broadcaster.cluster_request
        if cluster_request is not None:
            cluster_request.set_object_dirty(broadcaster)

    def _is_valid_cache_object(self, obj):
        if obj.is_sim:
            return False
        elif self._object_cache_tags:
            object_tags = obj.get_tags()
            if object_tags & self._object_cache_tags:
                return True
            else:
                return False
        return False
        return True

    def get_object_cache_info(self):
        return (self._object_cache, self._object_cache_tags)

    def _generate_object_cache(self):
        self._object_cache = WeakSet(obj for obj in services.object_manager().valid_objects() if self._is_valid_cache_object(obj))

    def _update_object_cache(self, obj=None):
        if obj is None:
            self._object_cache = None
            self._object_cache_tags = None
            return
        if self._object_cache is not None and self._is_valid_cache_object(obj):
            self._object_cache.add(obj)

    def _is_valid_broadcaster(self, broadcaster):
        broadcasting_object = broadcaster.broadcasting_object
        if broadcasting_object is None or not broadcasting_object.visible_to_client:
            return False
        if broadcasting_object.is_in_inventory():
            return False
        elif broadcasting_object.parent is not None and broadcasting_object.parent.is_sim:
            return False
        return True

    def _get_broadcasters_for_cluster_request_gen(self, broadcaster_type, broadcaster_level):
        for broadcaster in self._active_broadcasters:
            if broadcaster.guid == broadcaster_type.guid and broadcaster.should_cluster() and broadcaster.routing_surface.secondary_id == broadcaster_level:
                yield broadcaster

    def get_broadcasters_debug_gen(self):
        for cluster_request in self._cluster_requests.values():
            for cluster in cluster_request.get_clusters_gen():
                broadcaster_iter = cluster.objects_gen()
                yield next(broadcaster_iter)
            yield from cluster_request.get_rejects()
        for broadcaster in self._active_broadcasters:
            if broadcaster.should_cluster() or self._is_valid_broadcaster(broadcaster):
                yield broadcaster

    def get_broadcasters_gen(self):
        for (cluster_request_key, cluster_request) in self._cluster_requests.items():
            is_cluster_dirty = cluster_request.is_dirty()
            for broadcaster in self._get_broadcasters_for_cluster_request_gen(*cluster_request_key):
                broadcaster.regenerate_constraint()
            for cluster in cluster_request.get_clusters_gen():
                broadcaster_iter = cluster.objects_gen()
                master_broadcaster = next(broadcaster_iter)
                master_broadcaster.set_linked_broadcasters(list(broadcaster_iter))
                yield master_broadcaster
            yield from cluster_request.get_rejects()
        for broadcaster in self._active_broadcasters:
            if broadcaster.should_cluster() or self._is_valid_broadcaster(broadcaster):
                yield broadcaster

    PathSegmentData = namedtuple('PathSegmentData', ('prev_pos', 'cur_pos', 'segment_vec', 'segment_mag_sq', 'segment_normal'))

    def get_broadcasters_along_route_gen(self, sim, path, start_time=0, end_time=0):
        path_segment_datas = {}
        start_index = max(0, path.node_at_time(start_time).index - 1)
        end_index = min(len(path) - 1, path.node_at_time(end_time).index)
        for broadcaster in self.get_broadcasters_gen():
            if broadcaster.route_events:
                if not broadcaster.can_affect(sim):
                    pass
                else:
                    constraint = broadcaster.get_constraint()
                    geometry = constraint.geometry
                    if geometry is None:
                        pass
                    else:
                        polygon = geometry.polygon
                        if polygon is None:
                            pass
                        elif not constraint.valid:
                            pass
                        else:
                            constraint_pos = polygon.centroid()
                            constraint_radius_sq = polygon.radius()
                            constraint_radius_sq = constraint_radius_sq*constraint_radius_sq
                            for index in range(end_index, start_index, -1):
                                prev_index = index - 1
                                prev_node = path.nodes[prev_index]
                                if not constraint.is_routing_surface_valid(prev_node.routing_surface_id):
                                    pass
                                else:
                                    segment_key = (prev_index, index)
                                    segment_data = path_segment_datas.get(segment_key, None)
                                    if segment_data is None:
                                        cur_node = path.nodes[index]
                                        cur_pos = sims4.math.Vector3(*cur_node.position)
                                        prev_pos = sims4.math.Vector3(*prev_node.position)
                                        segment_vec = cur_pos - prev_pos
                                        segment_vec.y = 0
                                        segment_mag_sq = segment_vec.magnitude_2d_squared()
                                        if sims4.math.almost_equal_sq(segment_mag_sq, 0):
                                            segment_normal = None
                                        else:
                                            segment_normal = segment_vec/sims4.math.sqrt(segment_mag_sq)
                                        segment_data = BroadcasterService.PathSegmentData(prev_pos, cur_pos, segment_vec, segment_mag_sq, segment_normal)
                                        path_segment_datas[segment_key] = segment_data
                                    else:
                                        (prev_pos, cur_pos, segment_vec, segment_mag_sq, segment_normal) = segment_data
                                    if segment_normal is None:
                                        constraint_vec = constraint_pos - prev_pos
                                        constraint_dist_sq = constraint_vec.magnitude_2d_squared()
                                        if constraint_radius_sq < constraint_dist_sq:
                                            pass
                                        else:
                                            for (transform, _, time) in path.get_location_data_along_segment_gen(prev_index, index):
                                                if not geometry.test_transform(transform):
                                                    pass
                                                else:
                                                    yield (time, broadcaster)
                                                    break
                                            break
                                    else:
                                        constraint_vec = constraint_pos - prev_pos
                                        constraint_vec.y = 0
                                        contraint_proj = constraint_vec - segment_normal*sims4.math.vector_dot_2d(constraint_vec, segment_normal)
                                        if constraint_radius_sq < contraint_proj.magnitude_2d_squared():
                                            pass
                                        else:
                                            for (transform, _, time) in path.get_location_data_along_segment_gen(prev_index, index):
                                                if not geometry.test_transform(transform):
                                                    pass
                                                else:
                                                    yield (time, broadcaster)
                                                    break
                                            break
                                    for (transform, _, time) in path.get_location_data_along_segment_gen(prev_index, index):
                                        if not geometry.test_transform(transform):
                                            pass
                                        else:
                                            yield (time, broadcaster)
                                            break
                                    break

    def get_pending_broadcasters_gen(self):
        yield from self._pending_broadcasters

    def _get_all_objects_gen(self):
        is_any_broadcaster_allowing_objects = True if self._object_cache else False
        if not is_any_broadcaster_allowing_objects:
            for broadcaster in self._active_broadcasters:
                (allow_objects, allow_objects_tags) = broadcaster.allow_objects.is_affecting_objects()
                if allow_objects:
                    is_any_broadcaster_allowing_objects = True
                    if allow_objects_tags is None:
                        self._object_cache_tags = None
                        break
                    else:
                        if self._object_cache_tags is None:
                            self._object_cache_tags = set()
                        self._object_cache_tags |= allow_objects_tags
        if is_any_broadcaster_allowing_objects:
            if self._object_cache is None:
                self._generate_object_cache()
            yield from list(self._object_cache)
        else:
            self._object_cache = None
            self._object_cache_tags = None
        yield from services.sim_info_manager().instanced_sims_gen()

    def register_callback(self, callback):
        if callback not in self._on_update_callbacks:
            self._on_update_callbacks.append(callback)

    def unregister_callback(self, callback):
        if callback in self._on_update_callbacks:
            self._on_update_callbacks.remove(callback)

    def _on_update(self, _):
        self._pending_update = True

    def _on_wall_contours_changed(self, *_, **__):
        self._update_object_cache()

    def provide_route_events(self, route_event_context, sim, path, failed_types=None, start_time=0, end_time=0, **kwargs):
        for (time, broadcaster) in self.get_broadcasters_along_route_gen(sim, path, start_time=start_time, end_time=end_time):
            resolver = broadcaster.get_resolver(sim)
            for route_event in broadcaster.route_events:
                if not failed_types is None:
                    pass
                if route_event_context.route_event_already_scheduled(route_event, provider=broadcaster) or route_event.test(resolver):
                    route_event_context.add_route_event(RouteEventType.BROADCASTER, route_event(time=time, provider=broadcaster, provider_required=True))

    def update(self):
        if self._pending_update:
            self._pending_update = False
            self._update()

    def _is_location_affected(self, constraint, transform, routing_surface):
        if constraint.geometry is not None and not constraint.geometry.test_transform(transform):
            return False
        elif not constraint.is_routing_surface_valid(routing_surface):
            return False
        return True

    def update_broadcasters_one_shot(self, broadcasters):
        for obj in self._get_all_objects_gen():
            object_transform = None
            routing_surface = obj.routing_surface
            for broadcaster in broadcasters:
                if broadcaster.can_affect(obj):
                    constraint = broadcaster.get_constraint()
                    if not constraint.valid:
                        pass
                    else:
                        if object_transform is None:
                            parent = obj.parent
                            if parent is None:
                                object_transform = obj.transform
                            else:
                                object_transform = parent.transform
                        if self._is_location_affected(constraint, object_transform, routing_surface):
                            broadcaster.apply_broadcaster_effect(obj)
                            broadcaster.remove_broadcaster_effect(obj)

    def _update(self):
        try:
            self._activate_pending_broadcasters()
            current_broadcasters = set(self.get_broadcasters_gen())
            for obj in self._get_all_objects_gen():
                object_transform = None
                is_affected = False
                for broadcaster in current_broadcasters:
                    if broadcaster.can_affect(obj):
                        constraint = broadcaster.get_constraint()
                        if not constraint.valid:
                            pass
                        else:
                            if object_transform is None:
                                parent = obj.parent
                                if parent is None:
                                    object_transform = obj.transform
                                else:
                                    object_transform = parent.transform
                            if self._is_location_affected(constraint, object_transform, obj.routing_surface):
                                broadcaster.apply_broadcaster_effect(obj)
                                is_affected = True
                if is_affected or self._object_cache is not None:
                    self._object_cache.discard(obj)
            for broadcaster in current_broadcasters:
                broadcaster.on_processed()
        finally:
            self._on_update_callbacks()

class BroadcasterRealTimeService(BroadcasterService):

    def create_update_alarm(self):
        self._alarm_handle = add_alarm_real_time(self, interval_in_real_seconds(self.INTERVAL), self._on_update, repeating=True, use_sleep_time=False)
