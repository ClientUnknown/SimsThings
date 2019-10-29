from placement import ScoringFunctionRadial, ScoringFunctionAngular, ScoringFunctionLinearfrom sims4.geometry import AbsoluteOrientationRange, RelativeFacingRange, RelativeFacingWithCirclefrom sims4.tuning.geometric import TunableVector3from sims4.tuning.tunable import TunableInterval, TunableAngle, TunableVariant, TunableFactory, Tunableimport sims4
class TunableOrientationRangeRestriction(TunableFactory):

    @staticmethod
    def _factory(angle, ideal_angle, **kwargs):
        location = kwargs['location']
        base_angle = sims4.math.yaw_quaternion_to_angle(location.transform.orientation)
        return AbsoluteOrientationRange(min_angle=angle.lower_bound + base_angle, max_angle=angle.upper_bound + base_angle, ideal_angle=ideal_angle + base_angle, weight=1.0)

    FACTORY_TYPE = _factory

    def __init__(self, description='A tunable orientation restriction.', **kwargs):
        super().__init__(angle=TunableInterval(description='\n                Tunable angle range for orientation of the target\n                relative to the orientation of the original location.\n                ', tunable_type=TunableAngle, default_upper=0, default_lower=0), ideal_angle=TunableAngle(description='\n                Ideal angle for orientation of the target.\n                ', default=0), description=description, **kwargs)

class TunableRelativeFacingRangeRestriction(TunableFactory):

    @staticmethod
    def _factory(angle, target_offset, **kwargs):
        location = kwargs['location']
        if target_offset != TunableVector3.DEFAULT_ZERO:
            calculated_transform = sims4.math.Transform.concatenate(sims4.math.Transform(target_offset, location.transform.orientation), location.transform)
        else:
            calculated_transform = location.transform
        return RelativeFacingRange(target=calculated_transform.translation, angle=angle)

    FACTORY_TYPE = _factory

    def __init__(self, description='A tunable relative facing orientation restriction.', **kwargs):
        super().__init__(angle=TunableAngle(description='\n                Facing range to the object.\n                ', default=0), target_offset=TunableVector3(description='\n                Offset relative to starting point to face.\n                ', default=TunableVector3.DEFAULT_ZERO, locked_args={'y': 0}), description=description, **kwargs)

class TunableRelativeFacingCircleRestriction(TunableFactory):

    @staticmethod
    def _factory(angle, radius, target_offset, **kwargs):
        location = kwargs['location']
        if target_offset != TunableVector3.DEFAULT_ZERO:
            calculated_transform = sims4.math.Transform.concatenate(sims4.math.Transform(target_offset, location.transform.orientation), location.transform)
        else:
            calculated_transform = location.transform
        return RelativeFacingWithCircle(calculated_transform.translation, angle, radius)

    FACTORY_TYPE = _factory

    def __init__(self, description='Orientation facing in a radius around a circle.', **kwargs):
        super().__init__(angle=TunableAngle(description='\n                Facing range to the circle.\n                ', default=0), radius=Tunable(description='\n                Radius around the given point up to which will be tested.\n                ', tunable_type=float, default=1), target_offset=TunableVector3(description='\n                Offset relative to starting point as center of circle.\n                ', default=TunableVector3.DEFAULT_ZERO, locked_args={'y': 0}), description=description, **kwargs)

class TunableRadialDistanceScoring(TunableFactory):

    @staticmethod
    def _factory(optimal_distance, width, max_distance, ignore_surface, **kwargs):
        location = kwargs['location']
        routing_surface = location.routing_surface if not ignore_surface else None
        scoring_function = ScoringFunctionRadial(location.transform.translation, optimal_distance, width, max_distance, routing_surface)
        return scoring_function

    FACTORY_TYPE = _factory

    def __init__(self, description='Score by distance from starting point.', **kwargs):
        super().__init__(optimal_distance=Tunable(description='\n                Optimal distance in meters from the starting point.\n                ', tunable_type=float, default=1), width=Tunable(description='\n                Absolute distance from optimal width where location will\n                attain the max score of 1.0 for this function.\n                ', tunable_type=float, default=0), max_distance=Tunable(description='\n                Max distance from optimal before the score becomes zero.\n                ', tunable_type=float, default=1), ignore_surface=Tunable(description='\n                If unset, will ensure the location and the tested position\n                share the same routing surface.  Otherwise, scoring will not\n                care if the two positions have different surfaces.\n                ', tunable_type=bool, default=False), description=description, **kwargs)

class TunableLinearDistanceScoring(TunableFactory):

    @staticmethod
    def _factory(initial_point, secondary_point, optimal_distance, max_distance, ignore_surface, **kwargs):
        location = kwargs['location']
        routing_surface = location.routing_surface if not ignore_surface else None
        initial_transform = sims4.math.Transform.concatenate(sims4.math.Transform(initial_point, location.transform.orientation), location.transform)
        if secondary_point != initial_point:
            second_transform = sims4.math.Transform.concatenate(sims4.math.Transform(secondary_point, location.transform.orientation), location.transform)
        else:
            raise ValueError('Secondary point cannot be equal to initial point')
        scoring_function = ScoringFunctionLinear(initial_transform.translation, second_transform.translation, optimal_distance, max_distance, routing_surface)
        return scoring_function

    FACTORY_TYPE = _factory

    def __init__(self, description='Score by distance from a defined line.', **kwargs):
        super().__init__(initial_point=TunableVector3(description='\n                Position relative to starting location\n                used as first point in the line used for scoring.\n                ', default=TunableVector3.DEFAULT_ZERO, locked_args={'y': 0}), secondary_point=TunableVector3(description='\n                Secondary point used to create a line from initial point.\n                This is relative to the starting location.\n                Distance from this line will be measured.\n                ', default=sims4.math.Vector3(1, 0, 0), locked_args={'y': 0}), optimal_distance=Tunable(description='\n                Optimal distance in meters from the tested location.\n                ', tunable_type=float, default=0), max_distance=Tunable(description='\n                Max distance from optimal before the score becomes zero.\n                ', tunable_type=float, default=1), ignore_surface=Tunable(description='\n                If unset, will ensure the location and the tested position\n                share the same routing surface.  Otherwise, scoring will not\n                care if the two positions have different surfaces.\n                ', tunable_type=bool, default=False), description=description, **kwargs)

class TunableAngularScoring(TunableFactory):

    @staticmethod
    def _factory(optimal_angle, width, max_distance, **kwargs):
        location = kwargs['location']
        base_angle = sims4.math.yaw_quaternion_to_angle(location.transform.orientation)
        scoring_function = ScoringFunctionAngular(location.transform.translation, optimal_angle + base_angle, width, max_distance)
        return scoring_function

    FACTORY_TYPE = _factory

    def __init__(self, description='Score by position within a given angle.', **kwargs):
        super().__init__(optimal_angle=TunableAngle(description='\n                Optimal angle from the tested location. Will score highest.\n                ', default=0), width=TunableAngle(description='\n                Absolute distance in meters from optimal angle \n                (relative to location orientation) where location will\n                attain the max score of 1.0 for this function.\n                ', default=0), max_distance=TunableAngle(description='\n                Max distance from optimal angle before the score becomes zero.\n                ', default=1), description=description, **kwargs)

class TunableOrientationRestriction(TunableVariant):

    def __init__(self, **kwargs):
        super().__init__(absolute_orientation=TunableOrientationRangeRestriction(), relative_facing_range=TunableRelativeFacingRangeRestriction(), relative_facing_circle=TunableRelativeFacingCircleRestriction(), default='absolute_orientation', **kwargs)

class TunablePlacementScoringFunction(TunableVariant):

    def __init__(self, **kwargs):
        super().__init__(radial_distance_scoring=TunableRadialDistanceScoring(), angular_scoring=TunableAngularScoring(), linear_distance_scoring=TunableLinearDistanceScoring(), default='radial_distance_scoring', **kwargs)
