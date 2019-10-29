import enumimport placementimport servicesimport sims4.logimport sims4.mathfrom animation.animation_utils import StubActorfrom interactions.constraint_variants import TunableConstraintVariantfrom interactions.constraints import ANYWHEREfrom placement import FGLSearchFlagsDefaultForSim, FGLSearchFlagsDefault, FGLSearchFlag, FindGoodLocationContextfrom postures import DerailReasonfrom protocolbuffers import Routing_pb2from routing.formation.formation_type_base import FormationTypeBase, FormationRoutingTypefrom sims4 import mathfrom sims4.geometry import RelativeFacingRangefrom sims4.math import Vector2, Vector3, MAX_INT32, Quaternionfrom sims4.tuning.geometric import TunableVector2from sims4.tuning.tunable import TunableList, Tunable, TunableTuple, TunableInterval, OptionalTunable, TunableRangefrom sims4.utils import classpropertyfrom world.ocean_tuning import OceanTuninglogger = sims4.log.Logger('RoutingFormations', default_owner='rmccord')
class RoutingFormationFollowType(enum.Int, export=False):
    NODE_TYPE_FOLLOW_LEADER = 0
    NODE_TYPE_CHAIN = 1

class _RoutingFormationAttachmentNode:
    __slots__ = ('_parent_offset', '_offset', '_radius', '_angle_constraint', '_flags', '_type')

    def __init__(self, parent_offset:Vector2, offset:Vector2, radius, angle_constraint, flags, node_type):
        self._parent_offset = parent_offset
        self._offset = offset
        self._radius = radius
        self._angle_constraint = angle_constraint
        self._flags = flags
        self._type = node_type

    @property
    def parent_offset(self):
        return self._parent_offset

    @property
    def offset(self):
        return self._offset

    @property
    def radius(self):
        return self._radius

    @property
    def node_type(self):
        return self._type

    def populate_attachment_pb(self, attachment_pb):
        attachment_pb.parent_offset.x = self._parent_offset.x
        attachment_pb.parent_offset.y = self._parent_offset.y
        attachment_pb.offset.x = self._offset.x
        attachment_pb.offset.y = self._offset.y
        attachment_pb.radius = self._radius
        attachment_pb.angle_constraint = self._angle_constraint
        attachment_pb.flags = self._flags
        attachment_pb.type = self._type

class FormationTypeFollow(FormationTypeBase):
    ATTACH_NODE_COUNT = 3
    ATTACH_NODE_RADIUS = 0.25
    ATTACH_NODE_ANGLE = math.PI
    ATTACH_NODE_FLAGS = 4
    RAYTRACE_HEIGHT = 1.5
    RAYTRACE_RADIUS = 0.1
    FACTORY_TUNABLES = {'formation_offsets': TunableList(description='\n            A list of offsets, relative to the master, that define where slaved\n            Sims are positioned.\n            ', tunable=TunableVector2(default=Vector2.ZERO()), minlength=1), 'formation_constraints': TunableList(description='\n            A list of constraints that slaved Sims must satisfy any time they\n            run interactions while in this formation. This can be a geometric\n            constraint, for example, that ensures Sims are always placed within\n            a radius or cone of their slaved position.\n            ', tunable=TunableConstraintVariant(constraint_locked_args={'multi_surface': True}, circle_locked_args={'require_los': False}, disabled_constraints={'spawn_points', 'relative_circle'})), '_route_length_interval': TunableInterval(description='\n            Sims are slaved in formation only if the route is within this range\n            amount, in meters.\n            \n            Furthermore, routes shorter than the minimum\n            will not interrupt behavior (e.g. a socializing Sim will not force\n            dogs to get up and move around).\n            \n            Also routes longer than the maximum will make the slaved sim  \n            instantly position next to their master\n            (e.g. if a leashed dog gets too far from the owner, we place it next to the owner).\n            ', tunable_type=float, default_lower=1, default_upper=20, minimum=0), 'fgl_on_routes': TunableTuple(description='\n            Data associated with the FGL Context on following slaves.\n            ', slave_should_face_master=Tunable(description='\n                If enabled, the Slave should attempt to face the master at the end\n                of routes.\n                ', tunable_type=bool, default=False), height_tolerance=OptionalTunable(description='\n                If enabled than we will set the height tolerance in FGL.\n                ', tunable=TunableRange(description='\n                    The height tolerance piped to FGL.\n                    ', tunable_type=float, default=0.035, minimum=0, maximum=1)))}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._attachment_chain = []
        formation_count = self.master.get_routing_slave_data_count(self._formation_cls)
        self._formation_offset = self.formation_offsets[formation_count]
        self._setup_right_angle_connections()
        self._offset = Vector3.ZERO()
        for attachment_info in self._attachment_chain:
            self._offset.x = self._offset.x + attachment_info.parent_offset.x - attachment_info.offset.x
            self._offset.z = self._offset.z + attachment_info.parent_offset.y - attachment_info.offset.y
        self._slave_constraint = None
        self._slave_lock = None
        self._final_transform = None

    @classproperty
    def routing_type(cls):
        return FormationRoutingType.FOLLOW

    @property
    def offset(self):
        return self._formation_offset

    @property
    def slave_attachment_type(self):
        return Routing_pb2.SlaveData.SLAVE_FOLLOW_ATTACHMENT

    @staticmethod
    def get_max_slave_count(tuned_factory):
        return len(tuned_factory._tuned_values.formation_offsets)

    @property
    def route_length_minimum(self):
        return self._route_length_interval.lower_bound

    @property
    def route_length_maximum(self):
        return self._route_length_interval.upper_bound

    def attachment_info_gen(self):
        yield from self._attachment_chain

    def on_master_route_start(self):
        self._build_routing_slave_constraint()
        self._lock_slave()
        if self._slave.is_sim:
            for si in self._slave.get_all_running_and_queued_interactions():
                if si.transition is not None and si.transition is not self.master.transition_controller:
                    si.transition.derail(DerailReason.CONSTRAINTS_CHANGED, self._slave)

    def on_master_route_end(self):
        self._build_routing_slave_constraint()
        if self._slave.is_sim:
            for si in self._slave.get_all_running_and_queued_interactions():
                if si.transition is not None and si.transition is not self.master.transition_controller:
                    si.transition.derail(DerailReason.CONSTRAINTS_CHANGED, self._slave)
        self._unlock_slave()
        self._final_transform = None

    def _lock_slave(self):
        self._slave_lock = self._slave.add_work_lock(self)

    def _unlock_slave(self):
        self._slave.remove_work_lock(self)

    def _build_routing_slave_constraint(self):
        self._slave_constraint = ANYWHERE
        for constraint in self.formation_constraints:
            constraint = constraint.create_constraint(self._slave, target=self._master, target_position=self._master.intended_position)
            self._slave_constraint = self._slave_constraint.intersect(constraint)

    def get_routing_slave_constraint(self):
        if self._slave_constraint is None or not self._slave_constraint.valid:
            self._build_routing_slave_constraint()
        return self._slave_constraint

    def _add_attachment_node(self, parent_offset:Vector2, offset:Vector2, radius, angle_constraint, flags, node_type):
        attachment_node = _RoutingFormationAttachmentNode(parent_offset, offset, radius, angle_constraint, flags, node_type)
        self._attachment_chain.append(attachment_node)

    def find_good_location_for_slave(self, master_location):
        restrictions = []
        fgl_kwargs = {}
        fgl_flags = 0
        fgl_tuning = self.fgl_on_routes
        slave_position = master_location.transform.transform_point(self._offset)
        orientation = master_location.transform.orientation
        routing_surface = master_location.routing_surface
        if self.slave.is_sim or isinstance(self.slave, StubActor):
            (min_water_depth, max_water_depth) = OceanTuning.make_depth_bounds_safe_for_surface_and_sim(routing_surface, self.slave)
        else:
            min_water_depth = None
            max_water_depth = None
        (min_water_depth, max_water_depth) = OceanTuning.make_depth_bounds_safe_for_surface_and_sim(routing_surface, self.master, min_water_depth=min_water_depth, max_water_depth=max_water_depth)
        fgl_kwargs.update({'min_water_depth': min_water_depth, 'max_water_depth': max_water_depth})
        if fgl_tuning.height_tolerance is not None:
            fgl_kwargs['height_tolerance'] = fgl_tuning.height_tolerance
        if fgl_tuning.slave_should_face_master:
            restrictions.append(RelativeFacingRange(master_location.transform.translation, 0))
            fgl_kwargs.update({'raytest_radius': self.RAYTRACE_RADIUS, 'raytest_start_offset': self.RAYTRACE_HEIGHT, 'raytest_end_offset': self.RAYTRACE_HEIGHT, 'ignored_object_ids': {self.master.id, self.slave.id}, 'raytest_start_point_override': master_location.transform.translation})
            fgl_flags = FGLSearchFlag.SHOULD_RAYTEST
            orientation_offset = sims4.math.angle_to_yaw_quaternion(sims4.math.vector3_angle(sims4.math.vector_normalize(self._offset)))
            orientation = Quaternion.concatenate(orientation, orientation_offset)
        starting_location = placement.create_starting_location(position=slave_position, orientation=orientation, routing_surface=routing_surface)
        if self.slave.is_sim:
            fgl_flags |= FGLSearchFlagsDefaultForSim
            fgl_context = placement.create_fgl_context_for_sim(starting_location, self.slave, search_flags=fgl_flags, restrictions=restrictions, **fgl_kwargs)
        else:
            fgl_flags |= FGLSearchFlagsDefault
            footprint = self.slave.get_footprint()
            fgl_context = FindGoodLocationContext(starting_location, object_id=self.slave.id, object_footprints=(footprint,) if footprint is not None else None, search_flags=fgl_flags, restrictions=restrictions, **fgl_kwargs)
        (new_position, new_orientation) = placement.find_good_location(fgl_context)
        if new_position is None or new_orientation is None:
            logger.info('No good location found for {} after slaved in a routing formation headed to {}.', self.slave, starting_location, owner='rmccord')
            return sims4.math.Transform(Vector3(*starting_location.position), Quaternion(*starting_location.orientation))
        new_position.y = services.terrain_service.terrain_object().get_routing_surface_height_at(new_position.x, new_position.z, master_location.routing_surface)
        final_transform = sims4.math.Transform(new_position, new_orientation)
        return final_transform

    def on_release(self):
        self._unlock_slave()

    def _setup_right_angle_connections(self):
        formation_offset_x = Vector2(self._formation_offset.x/6.0, 0.0)
        formation_offset_y = Vector2(0.0, self._formation_offset.y)
        for _ in range(self.ATTACH_NODE_COUNT):
            self._add_attachment_node(formation_offset_x, formation_offset_x*-1, self.ATTACH_NODE_RADIUS, 0, self.ATTACH_NODE_FLAGS, RoutingFormationFollowType.NODE_TYPE_FOLLOW_LEADER)
        self._setup_direct_connections(formation_offset_y)

    def _setup_direct_connections(self, formation_offset):
        formation_vector_magnitude = formation_offset.magnitude()
        normalized_offset = formation_offset/formation_vector_magnitude
        attachment_node_step = formation_vector_magnitude/((self.ATTACH_NODE_COUNT - 1)*2)
        attachment_vector = normalized_offset*attachment_node_step
        for i in range(0, self.ATTACH_NODE_COUNT - 1):
            flags = self.ATTACH_NODE_FLAGS
            if i == self.ATTACH_NODE_COUNT - 2:
                flags = 5
            self._add_attachment_node(attachment_vector, attachment_vector*-1, self.ATTACH_NODE_RADIUS, self.ATTACH_NODE_ANGLE, flags, RoutingFormationFollowType.NODE_TYPE_CHAIN)

    def should_slave_for_path(self, path):
        path_length = path.length() if path is not None else MAX_INT32
        final_path_node = path.nodes[-1]
        final_position = sims4.math.Vector3(*final_path_node.position)
        final_orientation = sims4.math.Quaternion(*final_path_node.orientation)
        routing_surface = final_path_node.routing_surface_id
        final_position.y = services.terrain_service.terrain_object().get_routing_surface_height_at(final_position.x, final_position.z, routing_surface)
        final_transform = sims4.math.Transform(final_position, final_orientation)
        slave_position = final_transform.transform_point(self._offset)
        slave_position.y = services.terrain_service.terrain_object().get_routing_surface_height_at(slave_position.x, slave_position.z, routing_surface)
        final_dist_sq = (slave_position - self.slave.position).magnitude_squared()
        if path_length >= self.route_length_minimum or final_dist_sq >= self.route_length_minimum*self.route_length_minimum:
            return True
        return False

    def build_routing_slave_pb(self, slave_pb, path=None):
        starting_location = path.final_location if path is not None else self.master.intended_location
        slave_transform = self.find_good_location_for_slave(starting_location)
        slave_loc = slave_pb.final_location_override
        (slave_loc.translation.x, slave_loc.translation.y, slave_loc.translation.z) = slave_transform.translation
        (slave_loc.orientation.x, slave_loc.orientation.y, slave_loc.orientation.z, slave_loc.orientation.w) = slave_transform.orientation
        self._final_transform = slave_transform

    def update_slave_position(self, master_transform, master_orientation, routing_surface, distribute=True, path=None, canceled=False):
        master_transform = sims4.math.Transform(master_transform.translation, master_orientation)
        if distribute and not canceled:
            slave_transform = self._final_transform if self._final_transform is not None else self.slave.transform
            slave_position = slave_transform.translation
        else:
            slave_position = master_transform.transform_point(self._offset)
            slave_transform = sims4.math.Transform(slave_position, master_orientation)
        slave_route_distance_sqrd = (self._slave.position - slave_position).magnitude_squared()
        if path is not None and path.length() < self.route_length_minimum and slave_route_distance_sqrd < self.route_length_minimum*self.route_length_minimum:
            return
        slave_too_far_from_master = False
        if slave_route_distance_sqrd > self.route_length_maximum*self.route_length_maximum:
            slave_too_far_from_master = True
        if distribute and not slave_too_far_from_master:
            self._slave.move_to(routing_surface=routing_surface, transform=slave_transform)
        else:
            location = self.slave.location.clone(routing_surface=routing_surface, transform=slave_transform)
            self.slave.set_location_without_distribution(location)
