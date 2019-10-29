from _animation import get_joint_transform_from_rigfrom _math import Vector2, Vector3, Quaternion, Transform, Vector3Immutable, QuaternionImmutable, minimum_distancefrom _math import mod_2pifrom collections import namedtuplefrom math import pi as PI, sqrt, fmod, floor, atan2, acos, asin, ceil, pi, eimport operatorfrom sims4.repr_utils import standard_reprfrom singletons import DEFAULTimport enumimport native.animationimport sims4.hash_utilimport sims4.logTWO_PI = PI*2EPSILON = 1.192092896e-07EPSILON_SQ = EPSILON*EPSILONQUATERNION_EPSILON = 0.001MAX_FLOAT = 3.402823466e+38MAX_UINT64 = 18446744073709551615MAX_INT64 = 922337203685477580MAX_UINT32 = 4294967295MAX_INT32 = 2147483647MAX_UINT16 = 65535MAX_INT16 = 32767POS_INFINITY = float('inf')NEG_INFINITY = float('-inf')FORWARD_AXIS = Vector3.Z_AXIS()UP_AXIS = Vector3.Y_AXIS()VECTOR3_ZERO = Vector3.ZERO()logger = sims4.log.Logger('Sims4Math')
def clamp(lower_bound, x, upper_bound):
    if x < lower_bound:
        return lower_bound
    elif x > upper_bound:
        return upper_bound
    return x

def interpolate(starting_value, ending_value, fraction):
    return (1 - fraction)*starting_value + ending_value*fraction

def linear_seq_gen(start, stop, step, max_count=None):
    delta = stop - start
    num = floor(abs(delta/step))
    num = min(num, max_count - 1)
    if max_count is not None and num > 0:
        for i in range(0, num + 1):
            yield start + i*delta/num
    else:
        yield start
        if stop != start:
            yield stop

def deg_to_rad(deg):
    return deg*PI/180

def rad_to_deg(rad):
    return rad*180/PI

def is_angle_in_between(a, start, end):
    _a = sims4.math.mod_2pi(a)
    _start = sims4.math.mod_2pi(start)
    _end = sims4.math.mod_2pi(end)
    if _start <= _end:
        return _start <= _a <= _end
    return _start <= _a or _a <= _end

def angle_abs_difference(a1, a2):
    delta = mod_2pi(a1 - a2)
    if delta > PI:
        delta = TWO_PI - delta
    return delta

def vector_from_seq(list_or_tuple):
    if not list_or_tuple:
        return
    length = len(list_or_tuple)
    if length >= 3:
        return Vector3(list_or_tuple[0], list_or_tuple[1], list_or_tuple[2])
    elif length == 2:
        return Vector2(list_or_tuple[0], list_or_tuple[1])

def vector_dot(a, b):
    return a.x*b.x + a.y*b.y + a.z*b.z

def vector_dot_2d(a, b):
    return a.x*b.x + a.z*b.z

def vector_cross(a, b):
    return Vector3(a.y*b.z - a.z*b.y, a.z*b.x - a.x*b.z, a.x*b.y - a.y*b.x)

def vector_cross_2d(a, b):
    return a.z*b.x - a.x*b.z

def vector_normalize(v):
    return v/v.magnitude()

def vector_normalize_2d(v):
    s = 1/v.magnitude_2d()
    return Vector3(v.x*s, 0, v.z*s)

def vector_flatten(v):
    return Vector3(v.x, 0, v.z)

def vector_interpolate(a, b, fraction):
    return a + (b - a)*fraction

def almost_equal(a, b, epsilon=EPSILON):
    return abs(a - b) < epsilon

def almost_equal_sq(a, b, epsilon_sq=EPSILON_SQ):
    return abs(a - b) < epsilon_sq

def vector3_almost_equal(v1, v2, epsilon=EPSILON):
    return abs(v1.x - v2.x) < epsilon and (abs(v1.y - v2.y) < epsilon and abs(v1.z - v2.z) < epsilon)

def vector3_almost_equal_2d(v1, v2, epsilon=EPSILON):
    return abs(v1.x - v2.x) < epsilon and abs(v1.z - v2.z) < epsilon

def quaternion_almost_equal(q1, q2, epsilon=QUATERNION_EPSILON):
    if abs(q1.x - q2.x) < epsilon and (abs(q1.y - q2.y) < epsilon and abs(q1.z - q2.z) < epsilon) and abs(q1.w - q2.w) < epsilon:
        return True
    elif abs(q1.x + q2.x) < epsilon and (abs(q1.y + q2.y) < epsilon and abs(q1.z + q2.z) < epsilon) and abs(q1.w + q2.w) < epsilon:
        return True
    return False

def transform_almost_equal(t1, t2, epsilon=EPSILON, epsilon_orientation=QUATERNION_EPSILON):
    if epsilon_orientation is DEFAULT:
        epsilon_orientation = epsilon
    return vector3_almost_equal(t1.translation, t2.translation, epsilon=epsilon) and quaternion_almost_equal(t1.orientation, t2.orientation, epsilon=epsilon_orientation)

def transform_almost_equal_2d(t1, t2, epsilon=EPSILON, epsilon_orientation=QUATERNION_EPSILON):
    if epsilon_orientation is DEFAULT:
        epsilon_orientation = epsilon
    return vector3_almost_equal_2d(t1.translation, t2.translation, epsilon=epsilon) and quaternion_almost_equal(t1.orientation, t2.orientation, epsilon=epsilon_orientation)

def vector3_rotate_axis_angle(v, angle, axis):
    q = Quaternion.from_axis_angle(angle, axis)
    return q.transform_vector(v)

def vector3_angle(v):
    return atan2(v.x, v.z)

def angle_to_yaw_quaternion(angle):
    return Quaternion.from_axis_angle(angle, UP_AXIS)

def yaw_quaternion_to_angle(q):
    logger.assert_log(almost_equal(q.x, 0.0, epsilon=QUATERNION_EPSILON) and almost_equal(q.z, 0.0, epsilon=QUATERNION_EPSILON), '{} is not a rotation around y.', q)
    if almost_equal(q.y, 0.0):
        return 0
    angle = acos(q.w)*2.0
    if q.y > 0:
        return angle
    else:
        return -angle

def get_closest_point_2D(segment, p):
    a1 = segment[0]
    a2 = segment[1]
    x1 = a1.x
    x2 = a2.x
    x3 = p.x
    z1 = a1.z
    z2 = a2.z
    z3 = p.z
    dx = x2 - x1
    dz = z2 - z1
    t = ((x3 - x1)*dx + (z3 - z1)*dz)/(dx*dx + dz*dz)
    t = clamp(0, t, 1)
    x0 = x1 + t*dx
    z0 = z1 + t*dz
    return Vector3(x0, p.y, z0)

def invert_quaternion(q):
    d = 1.0/(q.x*q.x + q.y*q.y + q.z*q.z + q.w*q.w)
    return Quaternion(-d*q.x, -d*q.y, -d*q.z, d*q.w)

def get_difference_transform(transform_a, transform_b):
    v = transform_b.translation - transform_a.translation
    a_q_i = invert_quaternion(transform_a.orientation)
    q = Quaternion.concatenate(transform_b.orientation, a_q_i)
    v_prime = Quaternion.transform_vector(a_q_i, v)
    return Transform(v_prime, q)

def get_bounds_2D(points):
    min_x = min(point.x for point in points)
    max_x = max(point.x for point in points)
    min_z = min(point.z for point in points)
    max_z = max(point.z for point in points)
    return (Vector2(min_x, min_z), Vector2(max_x, max_z))

def circle_contains_position_2d(circle, position, return_dist_sq=False):
    dist_sq = pow(circle.center.x - position.x, 2) + pow(circle.center.y - position.z, 2)
    return (dist_sq < pow(circle.radius, 2) if not return_dist_sq else dist_sq < pow(circle.radius, 2), dist_sq)
_Location = namedtuple('_Location', ('transform', 'routing_surface', 'parent_ref', 'joint_name_or_hash', 'slot_hash', 'world_routing_surface', 'world_transform'))
class Location(_Location):
    __slots__ = ()
    REQUIRED_PROVIDED_SURFACE_HEIGHT = 0.1

    def __new__(cls, transform, routing_surface, parent=None, joint_name_or_hash=None, slot_hash=0):
        if parent is not None:
            world_routing_surface = cls.get_world_routing_surface(parent, transform, joint_name_or_hash, slot_hash)
            world_transform = cls.get_world_transform(parent, transform, joint_name_or_hash)
            parent = parent.ref()
            routing_surface = None
        else:
            world_transform = transform
            world_routing_surface = routing_surface
        return super().__new__(cls, transform, routing_surface, parent, joint_name_or_hash, slot_hash, world_routing_surface, world_transform)

    @staticmethod
    def get_world_routing_surface(parent, transform, joint_name_or_hash, slot_hash):
        if parent.provided_routing_surface:
            if slot_hash and transform.translation.y > Location.REQUIRED_PROVIDED_SURFACE_HEIGHT:
                return parent.provided_routing_surface
            if joint_name_or_hash:
                joint_transform = get_joint_transform_from_rig(parent.rig, joint_name_or_hash)
                if joint_transform.translation.y > Location.REQUIRED_PROVIDED_SURFACE_HEIGHT:
                    return parent.provided_routing_surface
        return parent.routing_surface

    @staticmethod
    def get_world_transform(parent, transform, joint_name_or_hash):
        if parent.is_part:
            parent_transform = parent.part_owner.transform
        else:
            parent_transform = parent.transform
        if joint_name_or_hash is None:
            if transform is None:
                return parent_transform
            return Transform.concatenate(transform, parent_transform)
        try:
            joint_transform = native.animation.get_joint_transform_from_rig(parent.rig, joint_name_or_hash)
        except (KeyError, ValueError) as e:
            return parent_transform
        if transform is None:
            return Transform.concatenate(joint_transform, parent_transform)
        local_transform = Transform.concatenate(transform, joint_transform)
        return Transform.concatenate(local_transform, parent_transform)

    def __repr__(self):
        return standard_repr(self, self.transform, self.routing_surface, parent=self.parent, joint_name_or_hash=self.joint_name_or_hash, slot_hash=self.slot_hash)

    def __eq__(self, other):
        if type(self) is not type(other):
            return False
        if self.transform != other.transform:
            return False
        if self.world_transform.translation != other.world_transform.translation:
            return False
        if self.parent != other.parent:
            return False
        if self.routing_surface != other.routing_surface:
            return False
        else:
            slot_hash0 = self.joint_name_or_hash or self.slot_hash
            slot_hash1 = other.joint_name_or_hash or other.slot_hash
            if slot_hash0 != slot_hash1:
                return False
        return True

    def almost_equal(self, other):
        if self.routing_surface != other.routing_surface:
            return False
        if not vector3_almost_equal_2d(self.transform.translation, other.transform.translation):
            return False
        elif not quaternion_almost_equal(self.transform.orientation, other.transform.orientation):
            return False
        return True

    def __ne__(self, other):
        return not self.__eq__(other)

    def __hash__(self):
        return hash((type(self), self.transform, self.parent_ref, self.routing_surface, self.joint_name_or_hash, self.slot_hash))

    @property
    def parent(self):
        if self.parent_ref is not None:
            return self.parent_ref()

    @property
    def joint_name_hash(self):
        if self.joint_name_or_hash is None:
            return 0
        if isinstance(self.joint_name_or_hash, int):
            return self.joint_name_or_hash
        else:
            return sims4.hash_util.hash32(self.joint_name_or_hash)

    @property
    def zone_id(self):
        if self.world_routing_surface.type == 1:
            return self.world_routing_surface.primary_id
        else:
            return sims4.zone_utils.zone_id

    @property
    def level(self):
        return self.world_routing_surface.secondary_id

    def duplicate(self):
        return type(self)(self.transform, self.routing_surface, self.parent, self.joint_name_or_hash, self.slot_hash)

    def clone(self, *, transform=DEFAULT, translation=DEFAULT, orientation=DEFAULT, routing_surface=DEFAULT, parent=DEFAULT, joint_name_or_hash=DEFAULT, slot_hash=DEFAULT):
        if transform is DEFAULT:
            if translation is DEFAULT:
                translation = self.transform.translation
            if orientation is DEFAULT:
                orientation = self.transform.orientation
        else:
            if transform is None:
                raise ValueError('Attempt to pass a None transform into a location clone.')
            if translation is DEFAULT:
                translation = transform.translation
            if orientation is DEFAULT:
                orientation = transform.orientation
        transform = Transform(translation, orientation)
        if routing_surface is DEFAULT:
            routing_surface = self.routing_surface
        if parent is DEFAULT:
            parent = self.parent
        if joint_name_or_hash is DEFAULT:
            joint_name_or_hash = self.joint_name_or_hash
        if slot_hash is DEFAULT:
            slot_hash = self.slot_hash
        return type(self)(transform, routing_surface, parent, joint_name_or_hash, slot_hash)

class LinearCurve:
    __slots__ = ('points',)

    def __init__(self, points):
        self.points = points
        self.points.sort(key=lambda i: i[0])

    def get(self, val):
        p_max = len(self.points) - 1
        if val <= self.points[0][0]:
            return self.points[0][1]
        if val >= self.points[p_max][0]:
            return self.points[p_max][1]
        i = p_max - 1
        while i > 0 and val < self.points[i][0]:
            i -= 1
        p1 = self.points[i]
        p2 = self.points[i + 1]
        percent = (val - p1[0])/(p2[0] - p1[0])
        return (p2[1] - p1[1])*percent + p1[1]

class WeightedUtilityCurve(LinearCurve):

    def __init__(self, points, max_y=0, weight=1):
        if max_y == 0:
            max_y = self._find_largest_y(points)
        transformed_points = [(point[0], point[1]/max_y*weight) for point in points]
        super().__init__(transformed_points)

    def _find_largest_y(self, points):
        max_y = 0
        for point in points:
            if point[1] > max_y:
                max_y = point[1]
        return max_y

class CircularUtilityCurve(LinearCurve):

    def __init__(self, points, min_x, max_x):
        super().__init__(points)
        self._min_x = min_x
        self._max_x = max_x
        last_point = self.points[-1]
        distance_to_end = max_x - last_point[0]
        total_length = distance_to_end + self.points[0][1]
        distance_to_pivot_point = distance_to_end/total_length
        pivot_y_value = (self.points[0][1] - last_point[1])*distance_to_pivot_point + self.points[0][1]
        self.points.insert(0, (0, pivot_y_value))
        self.points.insert(len(self.points), (self._max_x, pivot_y_value))

    def get(self, val):
        return super().get(val)

class Operator(enum.Int):
    GREATER = 1
    GREATER_OR_EQUAL = 2
    EQUAL = 3
    NOTEQUAL = 4
    LESS_OR_EQUAL = 5
    LESS = 6

    @staticmethod
    def from_function(fn):
        if fn == operator.gt:
            return Operator.GREATER
        if fn == operator.ge:
            return Operator.GREATER_OR_EQUAL
        if fn == operator.eq:
            return Operator.EQUAL
        if fn == operator.ne:
            return Operator.NOTEQUAL
        if fn == operator.le:
            return Operator.LESS_OR_EQUAL
        elif fn == operator.lt:
            return Operator.LESS

    @property
    def function(self):
        if self.value == Operator.GREATER:
            return operator.gt
        if self.value == Operator.GREATER_OR_EQUAL:
            return operator.ge
        if self.value == Operator.EQUAL:
            return operator.eq
        if self.value == Operator.NOTEQUAL:
            return operator.ne
        if self.value == Operator.LESS_OR_EQUAL:
            return operator.le
        elif self.value == Operator.LESS:
            return operator.lt

    @property
    def inverse(self):
        if self == Operator.GREATER:
            return Operator.LESS_OR_EQUAL
        if self == Operator.GREATER_OR_EQUAL:
            return Operator.LESS
        if self == Operator.EQUAL:
            return Operator.NOTEQUAL
        if self == Operator.NOTEQUAL:
            return Operator.EQUAL
        if self == Operator.LESS_OR_EQUAL:
            return Operator.GREATER
        elif self == Operator.LESS:
            return Operator.GREATER_OR_EQUAL

    @property
    def symbol(self):
        if self == Operator.GREATER:
            return '>'
        if self == Operator.GREATER_OR_EQUAL:
            return '>='
        if self == Operator.EQUAL:
            return '=='
        if self == Operator.NOTEQUAL:
            return '!='
        if self == Operator.LESS_OR_EQUAL:
            return '<='
        elif self == Operator.LESS:
            return '<'

    @property
    def category(self):
        if self == Operator.GREATER:
            return Operator.GREATER
        if self == Operator.GREATER_OR_EQUAL:
            return Operator.GREATER
        if self == Operator.EQUAL:
            return Operator.EQUAL
        if self == Operator.NOTEQUAL:
            return Operator.EQUAL
        if self == Operator.LESS_OR_EQUAL:
            return Operator.LESS
        elif self == Operator.LESS:
            return Operator.LESS

class InequalityOperator(enum.Int):
    GREATER = Operator.GREATER
    GREATER_OR_EQUAL = Operator.GREATER_OR_EQUAL
    LESS_OR_EQUAL = Operator.LESS_OR_EQUAL
    LESS = Operator.LESS
with InequalityOperator.__reload_context__(InequalityOperator, InequalityOperator):
    InequalityOperator.from_function = Operator.from_function
    InequalityOperator.function = Operator.function
    InequalityOperator.inverse = Operator.inverse
    InequalityOperator.symbol = Operator.symbol
    InequalityOperator.category = Operator.category
class Threshold:
    __slots__ = ('value', 'comparison')

    def __init__(self, value=None, comparison=None):
        self.value = value
        self.comparison = comparison

    def compare(self, source_value):
        if self.value is not None and self.comparison is not None:
            return self.comparison(source_value, self.value)
        return False

    def compare_value(self, source_value):
        if self.value is not None and self.comparison is not None:
            return self.comparison(source_value.value, self.value.value)
        return False

    def inverse(self):
        return Threshold(self.value, Operator.from_function(self.comparison).inverse.function)

    def __str__(self):
        if self.comparison is None:
            return 'None'
        return '{} {}'.format(Operator.from_function(self.comparison).symbol, self.value)

    def __repr__(self):
        return '<Threshold {}>'.format(str(self))

    def __eq__(self, other):
        if not isinstance(other, Threshold):
            return False
        if not self.value == other.value:
            return False
        elif not self.comparison == other.comparison:
            return False
        return True

    def __hash__(self):
        return hash((self.value, self.comparison))

def safe_max(*args, default=None, **kwargs):
    try:
        return max(*args, **kwargs)
    except ValueError:
        return default

def safe_min(*args, default=None, **kwargs):
    try:
        return max(*args, **kwargs)
    except ValueError:
        return default
