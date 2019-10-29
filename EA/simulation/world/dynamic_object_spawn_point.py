from _animation import get_joint_transform_from_rigfrom _math import Transform, Vector3import itertoolsimport randomfrom world.spawn_point import SpawnPointimport interactions.constraintsimport servicesimport sims4.loglogger = sims4.log.Logger('DynamicObjectSpawnPoint', default_owner='tingyul')
class DynamicObjectSpawnPoint(SpawnPoint):

    def __init__(self, owner, spawner_tags, *, bone_name, bone_offset, rows, columns, scale, priority):
        self._owner = owner
        self._bone_name = bone_name
        self._bone_offset = bone_offset
        self._scale = scale
        self._rows = rows
        self._columns = columns
        self._priority = priority
        random_indices = list(range(rows*columns))
        random.shuffle(random_indices)
        self._random_index_gen = itertools.cycle(random_indices)
        self._footprint_polygon = None
        self._tags = frozenset(spawner_tags)
        lot_id = services.active_lot_id() if owner.is_on_active_lot() else 0
        super().__init__(lot_id, owner.zone_id, routing_surface=owner.routing_surface)

    def on_add(self):
        super().on_add()
        self._build_footprint_polygon()
        self._owner.register_on_location_changed(self._on_owner_location_changed)

    def on_remove(self):
        self._owner.unregister_on_location_changed(self._on_owner_location_changed)
        super().on_remove()

    @property
    def spawn_point_priority(self):
        return self._priority

    def get_tags(self):
        return self._tags

    def get_approximate_transform(self):
        return self._get_bone_transform()

    def get_approximate_center(self):
        transform = self._get_bone_transform()
        return transform.translation

    def get_name(self):
        return 'ObjectSpawnPoint on {}'.format(self._owner)

    def next_spawn_spot(self):
        index = next(self._random_index_gen)
        pos = self._get_pos_for_index(index)
        orient = self._get_orientation_away_from_owner(pos)
        return (pos, orient)

    def _get_pos_for_index(self, index):
        row = index % self._rows
        column = index//self._rows
        x_offset = self._scale*(column - self._columns/2 + 0.5)
        z_offset = self._scale*(row - self._rows/2 + 0.5)
        offset = Vector3(x_offset, 0, z_offset)
        bone_transform = self._get_bone_transform()
        return bone_transform.transform_point(offset)

    def validate_connectivity(self, dest_handles):
        pass

    def get_valid_and_invalid_positions(self):
        valid_positions = tuple(self._get_pos_for_index(index) for index in range(self._rows*self._columns))
        invalid_positions = (self._get_bone_transform().translation,)
        return (valid_positions, invalid_positions)

    def get_position_constraints(self, generalize=False):
        if not generalize:
            (valid_positions, _) = self.get_valid_and_invalid_positions()
            pos_constraints = []
            for valid_pos in valid_positions:
                pos_constraints.append(interactions.constraints.Position(valid_pos, routing_surface=self.routing_surface, objects_to_ignore=set([self.spawn_point_id])))
            return pos_constraints
        return [interactions.constraints.Circle(self.get_approximate_center(), 2, routing_surface=self.routing_surface, objects_to_ignore=set([self.spawn_point_id]))]

    def get_footprint_polygon(self):
        return self._footprint_polygon

    def _build_footprint_polygon(self):
        bone_transform = self._get_bone_transform()
        x_offset = self._scale*self._columns/2
        z_offset = self._scale*self._rows/2
        v0 = bone_transform.transform_point(Vector3(x_offset, 0, z_offset))
        v1 = bone_transform.transform_point(Vector3(-x_offset, 0, z_offset))
        v2 = bone_transform.transform_point(Vector3(-x_offset, 0, -z_offset))
        v3 = bone_transform.transform_point(Vector3(x_offset, 0, -z_offset))
        self._footprint_polygon = sims4.geometry.Polygon([v0, v1, v2, v3])

    def _get_bone_transform(self):
        joint_transform = get_joint_transform_from_rig(self._owner.rig, self._bone_name)
        offset_from_joint = joint_transform.transform_point(self._bone_offset)
        final_transform = Transform.concatenate(Transform(offset_from_joint), self._owner.transform)
        return final_transform

    def _get_orientation_away_from_owner(self, pos):
        return self._owner.transform.orientation

    def _on_owner_location_changed(self, obj, old_location, location):
        self._routing_surface = self._owner.routing_surface
        self._remove_goal_suppression_region()
        self._build_footprint_polygon()
        self._add_goal_suppression_region()
