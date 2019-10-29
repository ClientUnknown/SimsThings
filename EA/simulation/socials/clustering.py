from contextlib import contextmanagerimport itertoolsimport mathimport weakrefimport timefrom indexed_manager import CallbackTypesfrom interactions.constraints import Constraint, TunableLineOfSightDatafrom objects.components.line_of_sight_component import LineOfSightfrom sims4.geometry import Polygon, interval_from_facing_angle, test_point_in_polygon, build_rectangle_from_two_points_and_radiusfrom sims4.math import vector3_angle, vector3_almost_equal_2dfrom sims4.service_manager import Servicefrom sims4.tuning.geometric import TunableDistanceSquaredfrom sims4.tuning.tunable import TunableAngle, TunableRange, AutoFactoryInit, HasTunableFactory, OptionalTunableimport interactions.constraintsimport servicesimport sims4.geometryimport sims4.logimport sims4.mathlogger = sims4.log.Logger('Clustering', default_owner='epanero')
class ObjectCluster:

    def __init__(self, position, constraint, objects, routing_surface):
        self._position = position
        self._constraint = constraint
        self._objects = objects
        self._routing_surface = routing_surface

    @property
    def position(self):
        return self._position

    @property
    def forward(self):
        return sims4.math.Vector3.Z_AXIS()

    @property
    def polygon(self):
        return self._constraint.geometry.polygon

    @property
    def constraint(self):
        return self._constraint

    @property
    def routing_surface(self):
        return self._routing_surface

    def objects_gen(self):
        for obj in self._objects:
            yield obj

    def __contains__(self, obj):
        return obj in self._objects

class ObjectClusterService(Service):
    CLUSTER_TIMESLICE = 0.1

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._cluster_requests = weakref.WeakSet()
        self._dirty_cluster_cache = False

    def _set_dirty(self):
        for cluster_request in self._cluster_requests:
            cluster_request.set_dirty(full_update=True)

    def start(self, *args, **kwargs):
        super().start(*args, **kwargs)
        services.current_zone().wall_contour_update_callbacks.append(self._set_dirty)

    def stop(self, *args, **kwargs):
        super().stop(*args, **kwargs)
        services.current_zone().wall_contour_update_callbacks.remove(self._set_dirty)

    def register_cluster_request(self, request):
        self._cluster_requests.add(request)

    def set_cluster_cache_dirty(self):
        self._dirty_cluster_cache = True

    def update(self):
        if self._dirty_cluster_cache:
            end_time = time.monotonic() + self.CLUSTER_TIMESLICE
            for cluster_request in self._cluster_requests:
                if not cluster_request.timeslice_cache_generation(end_time):
                    break
            self._dirty_cluster_cache = False

    def on_teardown(self):
        for cluster_request in self._cluster_requests:
            cluster_request.on_teardown()

class ObjectClusterRequest(HasTunableFactory, AutoFactoryInit):
    FACTORY_TUNABLES = {'density_epsilon': TunableDistanceSquared(description='\n            A constant that defines whether or not two objects are reachable.\n            ', default=2.82), 'facing_angle': OptionalTunable(description='\n            If set, then objects in a cluster must satisfy facing requirements.\n            ', tunable=TunableAngle(description='\n                An angle that defines the facing requirements for the purposes\n                of clustering and centroid facing.\n                ', default=sims4.math.PI)), 'minimum_size': TunableRange(description='\n            The minimum required size for clusters. Group of objects less than\n            this constant will not form clusters.\n            ', tunable_type=int, minimum=2, default=3), 'line_of_sight_constraint': TunableLineOfSightData(description='\n            The line of sight parameters for generated clusters.\n            '), 'radius_buffer': TunableRange(description='\n            An additional distance (in meters) that will be added to the radius\n            of a cluster. The size of a cluster is based on the objects in it.\n            We need to add an additional amount to ensure that the object is\n            included in the (non-exact) circle constraint.\n            ', tunable_type=float, minimum=0, default=0.5)}
    FACING_EPSILON = 0.01

    def __init__(self, get_objects_gen, quadtree=None, **kwargs):
        super().__init__(**kwargs)
        self._clusters = []
        self._get_objects_gen = get_objects_gen
        self._cache = None
        self._dirty = True
        self._quadtree = quadtree
        self._rejects = ()
        self._clusters_to_update_cache = None
        self._combination_to_update_cache = None
        self._reachable_cache = {}
        services.current_zone().object_cluster_service.register_cluster_request(self)

    def on_teardown(self):
        self._reachable_cache = {}

    def get_clusters_gen(self, regenerate=False):
        if self._dirty or regenerate:
            self._generate_clusters()
            self._clusters_to_update_cache = list(self._clusters)
            services.current_zone().object_cluster_service.set_cluster_cache_dirty()
        for cluster in self._clusters:
            yield cluster

    def timeslice_cache_generation(self, end_time):
        while time.monotonic() < end_time:
            if self._combination_to_update_cache:
                (a, b) = self._combination_to_update_cache.pop()
                self._is_reachable(a, b)
            elif self._clusters_to_update_cache:
                objects_to_process = self._clusters_to_update_cache.pop().objects_gen()
                self._combination_to_update_cache = list(itertools.combinations(objects_to_process, 2))
            else:
                return True
        return False

    def get_rejects(self):
        return self._rejects

    def _get_score(self, cluster, p):
        return (cluster.position - p).magnitude_squared()

    def get_closest_valid_cluster(self, constraint, radius=None):
        best_score = None
        best_cluster = None
        for cluster in self.get_clusters_gen():
            for sub_constraint in constraint:
                if sub_constraint.routing_surface != cluster.routing_surface:
                    pass
                else:
                    constraint_position = sub_constraint.average_position
                    if radius is not None and (constraint_position - cluster.position).magnitude_2d() > radius:
                        pass
                    elif not sub_constraint.intersect(cluster.constraint).valid:
                        pass
                    else:
                        score = self._get_score(cluster, constraint_position)
                        if not best_score is None:
                            if score < best_score:
                                best_score = score
                                best_cluster = cluster
                        best_score = score
                        best_cluster = cluster
        return best_cluster

    def set_dirty(self, full_update=False):
        self._dirty = True
        self._clusters_to_update_cache = None
        self._combination_to_update_cache = None
        if full_update:
            self._reachable_cache.clear()

    def set_object_dirty(self, obj):
        object_id = obj.id
        invalid_keys = [cache_key for cache_key in self._reachable_cache if object_id in cache_key]
        for cache_key in invalid_keys:
            del self._reachable_cache[cache_key]
        self.set_dirty()

    def is_dirty(self):
        return self._dirty

    @contextmanager
    def _caching(self):
        self._cache = {}
        try:
            yield None
        finally:
            self._cache = None
            self._dirty = False

    def _is_facing(self, a, b):
        interval = interval_from_facing_angle(vector3_angle(a.position - b.position), self.facing_angle + self.FACING_EPSILON)
        facing = vector3_angle(b.forward)
        return facing in interval

    def _is_reachable(self, a, b):
        if b.id > a.id:
            cache_key = (a.id, b.id)
        else:
            cache_key = (b.id, a.id)
        if cache_key in self._reachable_cache:
            return self._reachable_cache[cache_key]
        result = self._is_reachable_no_cache(a, b)
        self._reachable_cache[cache_key] = result
        return result

    def _is_reachable_no_cache(self, a, b):
        if a.routing_surface != b.routing_surface:
            return False
        if (a.position - b.position).magnitude_squared() <= self.density_epsilon:
            if not (self.facing_angle is not None and self._is_facing(a, b) and self._is_facing(b, a)):
                return False
            else:
                point_constraint = interactions.constraints.Position(a.lineofsight_component.default_position, routing_surface=a.routing_surface)
                test_constraint = point_constraint.intersect(b.lineofsight_component.constraint)
                if test_constraint.valid:
                    return True
        return False

    def _get_reachable_objects(self, obj, objects, can_cache=True):
        reachable_objects = self._cache.get(obj, None)
        if reachable_objects is not None:
            reachable_objects = reachable_objects & objects
        else:
            reachable_objects = set()
            for other_obj in self._get_reachable_objects_candidates(obj, objects):
                if other_obj is not obj and self._is_reachable(obj, other_obj):
                    reachable_objects.add(other_obj)
        if can_cache:
            self._cache[obj] = reachable_objects.copy()
        return reachable_objects

    def _has_enough_reachable_neighbors(self, obj, neighbor_objects, count):
        reachable_objects = self._cache.get(obj, None)
        if reachable_objects is not None:
            for obj in reachable_objects:
                if obj in neighbor_objects:
                    count -= 1
                    if count == 0:
                        return True
            return len(reachable_objects & neighbor_objects) >= count
        for other_obj in self._get_reachable_objects_candidates(obj, neighbor_objects):
            if other_obj is not obj and self._is_reachable(obj, other_obj):
                count -= 1
                if count == 0:
                    return True
        return False

    def _get_reachable_objects_candidates(self, obj, objects):
        if self._quadtree is not None:
            query_bounds = sims4.geometry.QtCircle(sims4.math.Vector2(obj.position.x, obj.position.z), math.sqrt(self.density_epsilon))
            return tuple(quadtree_obj for quadtree_obj in self._quadtree.query(query_bounds) if quadtree_obj in objects)
        return objects

    def _get_cluster_radius(self, position, objects):
        max_obj_dist_sq = 0
        for obj in objects:
            if obj.parts:
                for part in obj.parts:
                    dist_sq = (part.position - position).magnitude_2d_squared()
                    if dist_sq > max_obj_dist_sq:
                        max_obj_dist_sq = dist_sq
            else:
                dist_sq = (obj.position - position).magnitude_2d_squared()
                if dist_sq > max_obj_dist_sq:
                    max_obj_dist_sq = dist_sq
        obj_dist = sims4.math.sqrt(max_obj_dist_sq) + self.radius_buffer
        return min(obj_dist, self.line_of_sight_constraint.max_line_of_sight_radius)

    def _get_cluster_polygon(self, position, objects):
        hull_points = [position]
        for obj in objects:
            if obj.parts:
                for part in obj.parts:
                    hull_points.append(part.position)
            else:
                hull_points.append(obj.position)
        polygon = Polygon(hull_points)
        polygon = polygon.get_convex_hull()
        if len(polygon) == 2 or polygon.too_thin or polygon.too_small:
            sorted_x = sorted(hull_points, key=lambda p: p.x)
            sorted_z = sorted(hull_points, key=lambda p: p.z)
            delta_x = sorted_x[-1].x - sorted_x[0].x
            delta_z = sorted_z[-1].z - sorted_z[0].z
            extents = sorted_x if delta_x > delta_z else sorted_z
            a = extents[0]
            b = extents[-1]
            polygon = build_rectangle_from_two_points_and_radius(a, b, self.radius_buffer)
        else:
            polygon = sims4.geometry.inflate_polygon(polygon, self.radius_buffer)
        compound_polygon = sims4.geometry.CompoundPolygon([polygon])
        return compound_polygon

    def _generate_cluster(self, position, objects):
        radius = self._get_cluster_radius(position, objects)
        los = LineOfSight(radius, self.line_of_sight_constraint.map_divisions, self.line_of_sight_constraint.simplification_ratio, self.line_of_sight_constraint.boundary_epsilon, debug_str_data=('_generate_cluster LOS Constraint, Cluster Objects: {}', objects))
        routing_surface = next(iter(objects)).routing_surface
        los.generate(position, routing_surface, build_convex=True)
        valid_objects = []
        rejects = []
        if los.constraint_convex.geometry is not None:
            for obj in objects:
                for polygon in los.constraint_convex.geometry.polygon:
                    if test_point_in_polygon(obj.lineofsight_component.default_position, polygon):
                        valid_objects.append(obj)
                        break
                rejects.append(obj)
        else:
            rejects = objects
        if not valid_objects:
            (rejected_ne, rejected_nw, rejected_se, rejected_sw) = ([], [], [], [])
            for reject in rejects:
                reject_position = reject.lineofsight_component.default_position
                if reject_position.x >= position.x and reject_position.z >= position.z:
                    rejected_ne.append(reject)
                elif reject_position.z >= position.z:
                    rejected_nw.append(reject)
                elif reject_position.x < position.x and reject_position.z < position.z:
                    rejected_sw.append(reject)
                else:
                    rejected_se.append(reject)
            return (rejected_ne, rejected_nw, rejected_se, rejected_sw)
        convex_hull_poly = self._get_cluster_polygon(position, valid_objects)
        convex_hull_constraint = Constraint(debug_name='ClusterConvexHull', routing_surface=routing_surface, allow_small_intersections=True, geometry=sims4.geometry.RestrictedPolygon(convex_hull_poly, []))
        cluster_constraint = los.constraint_convex.intersect(convex_hull_constraint)
        if cluster_constraint.valid:
            cluster = ObjectCluster(position, cluster_constraint, valid_objects, routing_surface)
            self._clusters.append(cluster)
        return [rejects]

    def _get_clusters(self, objects):
        closed = set()
        clusters = []
        for obj in objects:
            if obj not in closed:
                closed.add(obj)
                pending_neighbors = self._get_reachable_objects(obj, objects)
                if len(pending_neighbors) >= self.minimum_size - 1:
                    cluster = set()
                    cluster.add(obj)
                    all_neighbors = set(pending_neighbors)
                    all_neighbors.add(obj)
                    non_neighbor_objects = objects - all_neighbors
                    while pending_neighbors:
                        neighbor = pending_neighbors.pop()
                        if neighbor not in closed:
                            closed.add(neighbor)
                            new_neighbors = self._get_reachable_objects(neighbor, non_neighbor_objects, False)
                            if new_neighbors:
                                required = self.minimum_size - 1 - len(new_neighbors)
                                if required <= 0 or self._has_enough_reachable_neighbors(neighbor, all_neighbors, required):
                                    all_neighbors.update(new_neighbors)
                                    pending_neighbors.update(new_neighbors)
                                    non_neighbor_objects -= new_neighbors
                        if not any(neighbor in c for c in itertools.chain(self._clusters, clusters)):
                            cluster.add(neighbor)
                    clusters.append(cluster)
        return clusters

    def _generate_clusters(self):
        with self._caching():
            del self._clusters[:]
            objects = [set(self._get_objects_gen())]
            all_rejects = set()
            while objects:
                clusters = self._get_clusters(objects.pop())
                for cluster in clusters:
                    polygon = Polygon([obj.position for obj in cluster])
                    centroid = polygon.centroid()
                    facing_rejects = []
                    for obj in list(cluster):
                        if self.facing_angle is not None:
                            interval = interval_from_facing_angle(vector3_angle(centroid - obj.position), self.facing_angle + self.FACING_EPSILON)
                            facing = vector3_angle(obj.forward)
                            is_facing = facing in interval
                        else:
                            is_facing = True
                        if is_facing or not vector3_almost_equal_2d(centroid, obj.position, epsilon=0.01):
                            cluster.remove(obj)
                            facing_rejects.append(obj)
                    if len(cluster) >= self.minimum_size:
                        rejected_sets = self._generate_cluster(centroid, cluster)
                        for rejected_set in itertools.chain((facing_rejects,), rejected_sets):
                            unused_rejects = set(obj for obj in rejected_set if obj not in all_rejects)
                            all_rejects.update(unused_rejects)
                            if len(unused_rejects) >= self.minimum_size:
                                objects.append(unused_rejects)
            self._rejects = [reject for reject in all_rejects if not any(reject in cluster for cluster in self._clusters)]

class SocialGroupClusterService(Service):
    CLUSTER_REQUEST = ObjectClusterRequest.TunableFactory(description='\n        Specify how social clusters are generated.\n        ')

    def start(self, *args, **kwargs):
        super().start(*args, **kwargs)
        self._cluster_request = self.CLUSTER_REQUEST(self._get_objects_gen)
        object_manager = services.object_manager()
        object_manager.register_callback(CallbackTypes.ON_OBJECT_ADD, self._on_update)
        object_manager.register_callback(CallbackTypes.ON_OBJECT_LOCATION_CHANGED, self._on_update)
        object_manager.register_callback(CallbackTypes.ON_OBJECT_REMOVE, self._on_update)

    def stop(self, *args, **kwargs):
        super().stop(*args, **kwargs)
        object_manager = services.object_manager()
        object_manager.unregister_callback(CallbackTypes.ON_OBJECT_ADD, self._on_update)
        object_manager.unregister_callback(CallbackTypes.ON_OBJECT_LOCATION_CHANGED, self._on_update)
        object_manager.unregister_callback(CallbackTypes.ON_OBJECT_REMOVE, self._on_update)

    def _is_datapoint(self, obj):
        social_clustering = obj.social_clustering
        if social_clustering is not None:
            return social_clustering.is_datapoint
        return False

    def _on_update(self, obj):
        if self._is_datapoint(obj):
            self._cluster_request.set_object_dirty(obj)

    def _get_objects_gen(self):
        for obj in services.object_manager().valid_objects():
            if self._is_datapoint(obj):
                yield obj

    def get_clusters_gen(self, *args, **kwargs):
        return self._cluster_request.get_clusters_gen(*args, **kwargs)

    def get_closest_valid_cluster(self, *args, **kwargs):
        return self._cluster_request.get_closest_valid_cluster(*args, **kwargs)
