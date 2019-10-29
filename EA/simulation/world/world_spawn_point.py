from _math import Vector3Immutable, Vector3import randomfrom world.spawn_point import SpawnPointimport build_buyimport interactions.constraintsimport routingimport servicesimport sims4.logimport sims4.mathimport sims4.randomlogger = sims4.log.Logger('Spawn Points', default_owner='tingyul')
class WorldSpawnPoint(SpawnPoint):
    SPAWN_POINT_SLOTS = 8
    SLOT_START_OFFSET_FROM_CENTER = Vector3Immutable(-1.5, 0, -0.5)
    FOOTPRINT_HALF_DIMENSIONS = Vector3Immutable(2.0, 0, 1.0)
    SPAWN_POINT_SLOT_ROWS = 2
    SPAWN_POINT_SLOT_COLUMNS = 4
    SPAWN_POINT_JITTER = 0.3

    def __init__(self, spawn_point_index, locator, zone_id, spawn_point_id=None):
        super().__init__(locator.lot_id, zone_id, spawn_point_id=spawn_point_id)
        self.spawn_point_index = spawn_point_index
        self._center = locator.position
        self._footprint_id = locator.footprint_id
        self._rotation = locator.rotation
        self._scale = locator.scale
        self._obj_def_guid = locator.obj_def_guid
        self._random_indices = [x for x in range(WorldSpawnPoint.SPAWN_POINT_SLOTS)]
        random.shuffle(self._random_indices)
        self._spawn_index = 0
        self._footprint_polygon = None
        self._valid_slots = 0
        self._tags = None

    @property
    def obj_def_guid(self):
        return self._obj_def_guid

    def get_approximate_transform(self):
        return sims4.math.Transform(self._center, self._rotation)

    def get_approximate_center(self):
        return self._center

    def next_spawn_spot(self):
        index = self._random_indices[self._spawn_index]
        pos = self._get_slot_pos(index)
        self._spawn_index = self._spawn_index + 1 if self._spawn_index < WorldSpawnPoint.SPAWN_POINT_SLOTS - 1 else 0
        orientation = sims4.random.random_orientation()
        pos.x += random.uniform(-WorldSpawnPoint.SPAWN_POINT_JITTER, WorldSpawnPoint.SPAWN_POINT_JITTER)
        pos.z += random.uniform(-WorldSpawnPoint.SPAWN_POINT_JITTER, WorldSpawnPoint.SPAWN_POINT_JITTER)
        pos.y = services.terrain_service.terrain_object().get_height_at(pos.x, pos.z)
        return (pos, orientation)

    def _get_slot_pos(self, index):
        if not index is None:
            if not (0 <= index and index <= WorldSpawnPoint.SPAWN_POINT_SLOTS - 1):
                logger.warn('Slot Index {} for Spawn Point is out of range.', index)
                return self._center
        logger.warn('Slot Index {} for Spawn Point is out of range.', index)
        return self._center
        offset_from_start = WorldSpawnPoint.SLOT_START_OFFSET_FROM_CENTER
        offset = Vector3(offset_from_start.x, offset_from_start.y, offset_from_start.z)
        offset.x += index % WorldSpawnPoint.SPAWN_POINT_SLOT_COLUMNS
        if index >= WorldSpawnPoint.SPAWN_POINT_SLOT_COLUMNS:
            offset.z += 1
        return self._transform_position(offset)

    def _transform_position(self, local_position):
        scale_pos = local_position*self._scale
        rotate_pos = self._rotation.transform_vector(scale_pos)
        return rotate_pos + self._center

    def get_name(self):
        definition = services.definition_manager().get(self._obj_def_guid)
        if definition is None:
            return 'None'
        return '{} lot: {}'.format(definition.name, self.lot_id)

    def get_tags(self):
        if not self._tags:
            self._tags = frozenset(build_buy.get_object_all_tags(self._obj_def_guid))
        return self._tags

    def get_position_constraints(self, generalize=False):
        constraints = []
        if not generalize:
            for index in range(WorldSpawnPoint.SPAWN_POINT_SLOTS):
                pos = self._get_slot_pos(index)
                constraints.append(interactions.constraints.Position(pos, routing_surface=self.routing_surface, objects_to_ignore=set([self.spawn_point_id])))
        else:
            constraints.append(interactions.constraints.Circle(self.get_approximate_center(), WorldSpawnPoint.FOOTPRINT_HALF_DIMENSIONS.magnitude(), routing_surface=self.routing_surface, objects_to_ignore=set([self.spawn_point_id])))
        return constraints

    def validate_connectivity(self, dest_handles):
        self._valid_slots = 0
        src_handles_to_indices = {}
        for index in range(WorldSpawnPoint.SPAWN_POINT_SLOTS):
            slot_pos = self._get_slot_pos(index)
            location = routing.Location(slot_pos, sims4.math.Quaternion.IDENTITY(), self.routing_surface)
            src_handles_to_indices[routing.connectivity.Handle(location)] = index
        routing_context = routing.PathPlanContext()
        routing_context.set_key_mask(routing.FOOTPRINT_KEY_ON_LOT | routing.FOOTPRINT_KEY_OFF_LOT)
        routing_context.ignore_footprint_contour(self._footprint_id)
        connectivity = routing.test_connectivity_batch(set(src_handles_to_indices.keys()), dest_handles, routing_context=routing_context, flush_planner=True)
        if connectivity is not None:
            for (src, _, _) in connectivity:
                index = src_handles_to_indices.get(src)
                if index is not None:
                    self._valid_slots = self._valid_slots | 1 << index

    def get_valid_and_invalid_positions(self):
        valid_positions = []
        invalid_positions = []
        for index in range(WorldSpawnPoint.SPAWN_POINT_SLOTS):
            pos = self._get_slot_pos(index)
            if self._valid_slots & 1 << index:
                valid_positions.append(pos)
            else:
                invalid_positions.append(pos)
        return (valid_positions, invalid_positions)

    def get_footprint_polygon(self):
        if self._footprint_polygon is not None:
            return self._footprint_polygon
        v0 = self._transform_position(WorldSpawnPoint.FOOTPRINT_HALF_DIMENSIONS)
        v1 = self._transform_position(sims4.math.Vector3(-WorldSpawnPoint.FOOTPRINT_HALF_DIMENSIONS.x, WorldSpawnPoint.FOOTPRINT_HALF_DIMENSIONS.y, WorldSpawnPoint.FOOTPRINT_HALF_DIMENSIONS.z))
        v2 = self._transform_position(-WorldSpawnPoint.FOOTPRINT_HALF_DIMENSIONS)
        v3 = self._transform_position(sims4.math.Vector3(WorldSpawnPoint.FOOTPRINT_HALF_DIMENSIONS.x, WorldSpawnPoint.FOOTPRINT_HALF_DIMENSIONS.y, -WorldSpawnPoint.FOOTPRINT_HALF_DIMENSIONS.z))
        self._footprint_polygon = sims4.geometry.Polygon([v0, v1, v2, v3])
        return self._footprint_polygon
