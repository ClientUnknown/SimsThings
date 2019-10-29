import itertoolsfrom sims4.tuning.geometric import TunableDistanceSquaredfrom sims4.tuning.tunable import HasTunableSingletonFactory, AutoFactoryInit, TunableRange, TunableVariantimport sims4.math
class _WaypointStitchingBase(HasTunableSingletonFactory, AutoFactoryInit):

    def __call__(self, waypoints, loops=1):
        raise NotImplementedError

class _WaypointStitchingWaypoints(_WaypointStitchingBase, HasTunableSingletonFactory, AutoFactoryInit):
    FACTORY_TUNABLES = {'max_distance': TunableDistanceSquared(description="\n            If the route's cumulative distance is more than this value, the\n            route is split.\n            ", default=500), 'max_goals': TunableRange(description='\n            If the route has more than this number of goals, the route is\n            split.\n            ', tunable_type=int, minimum=0, default=200)}

    def __call__(self, waypoints, loops=1):
        waypoint_groups = [[]]
        group_dist = 0
        group_num_goals = 0
        previous_centroid = None
        for goals in itertools.chain.from_iterable(itertools.repeat(waypoints, loops)):
            num_goals = len(goals)
            centroid = sum([goal.position for goal in goals], sims4.math.Vector3.ZERO())/num_goals
            dist = (previous_centroid - centroid).magnitude_2d_squared() if previous_centroid is not None else 0
            current_group = waypoint_groups[-1]
            if num_goals + group_num_goals > self.max_goals:
                waypoint_groups.append(current_group)
                current_group = [current_group[-1]]
                group_dist = 0
                group_num_goals = len(current_group[0])
            current_group.append(goals)
            group_dist += dist
            group_num_goals += num_goals
            previous_centroid = centroid
        yield from waypoint_groups

class _WaypointStitchingNone(_WaypointStitchingBase, HasTunableSingletonFactory, AutoFactoryInit):

    def __call__(self, waypoints, loops=1):
        for _ in range(loops):
            for goals in waypoints:
                yield [goals]

class WaypointStitchingVariant(TunableVariant):

    def __init__(self, *args, **kwargs):
        variants = {'waypoints': _WaypointStitchingWaypoints.TunableFactory(), 'none': _WaypointStitchingNone.TunableFactory(), 'default': 'none'}
        kwargs.update(variants)
        super().__init__(*args, **kwargs)
