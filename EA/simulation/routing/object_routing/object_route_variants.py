from _weakrefset import WeakSetimport itertoolsfrom animation.object_animation import ObjectAnimationElementfrom balloon.balloon_enums import BALLOON_TYPE_LOOKUPfrom balloon.balloon_request import BalloonRequestfrom balloon.balloon_variant import BalloonVariantfrom balloon.tunable_balloon import TunableBalloonfrom event_testing.resolver import SingleObjectResolver, DoubleObjectResolverfrom interactions.constraints import Circlefrom interactions.utils.animation_reference import TunableRoutingSlotConstraintfrom objects.components import typesfrom placement import find_good_locationfrom routing import Goal, SurfaceType, SurfaceIdentifierfrom routing.waypoints.waypoint_generator import WaypointContextfrom routing.waypoints.waypoint_generator_variant import TunableWaypointGeneratorVariantfrom routing.waypoints.waypoint_stitching import WaypointStitchingVariantfrom sims4 import randomfrom sims4.math import vector3_almost_equalfrom sims4.random import weighted_random_itemfrom sims4.tuning.tunable import OptionalTunable, HasTunableFactory, AutoFactoryInit, Tunable, TunableReference, TunableEnumEntryfrom sims4.tuning.tunable_base import GroupNamesfrom tag import TunableTagsimport placementimport routingimport servicesimport sims4.resources
class _ObjectRoutingBehaviorBase(HasTunableFactory, AutoFactoryInit):
    FACTORY_TUNABLES = {'route_fail': OptionalTunable(description='\n            If enabled, show a route failure balloon if the agent is unable to\n            route to the routing slot constraint.\n            ', tunable=BalloonVariant.TunableFactory(), enabled_name='show_balloon')}

    def __init__(self, obj, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._obj = obj
        self._target = None

    def do_route_fail_gen(self, timeline):
        if self.route_fail is None:
            return
        target = self.get_target()
        if target is None:
            resolver = SingleObjectResolver(self._obj)
        else:
            resolver = DoubleObjectResolver(self._obj, target)
        balloons = self.route_fail.get_balloon_icons(resolver)
        if not balloons:
            return
        balloon = weighted_random_item(balloons)
        if balloon is None:
            return
        icon_info = balloon.icon(resolver, balloon_target_override=None)
        if icon_info[0] is None and icon_info[1] is None:
            return
        category_icon = None
        if balloon.category_icon is not None:
            category_icon = balloon.category_icon(resolver, balloon_target_override=None)
        (balloon_type, priority) = BALLOON_TYPE_LOOKUP[balloon.balloon_type]
        balloon_overlay = balloon.overlay
        request = BalloonRequest(self._obj, icon_info[0], icon_info[1], balloon_overlay, balloon_type, priority, TunableBalloon.BALLOON_DURATION, 0, 0, category_icon)
        request.distribute()

    def get_routes_gen(self):
        raise NotImplementedError

    def get_target(self):
        return self._target

    def get_randomize_orientation(self):
        return False

class ObjectRoutingBehaviorFromWaypointGenerator(_ObjectRoutingBehaviorBase):
    FACTORY_TUNABLES = {'waypoint_generator': TunableWaypointGeneratorVariant(tuning_group=GroupNames.ROUTING), 'waypoint_count': Tunable(description='\n            The number of waypoints per loop.\n            ', tunable_type=int, default=10), 'waypoint_stitching': WaypointStitchingVariant(tuning_group=GroupNames.ROUTING), 'return_to_starting_point': OptionalTunable(description='\n            If enabled then the route will return to the starting position\n            within a circle constraint that has a radius of the value tuned\n            here.\n            ', tunable=Tunable(description='\n                The radius of the circle constraint to build to satisfy the\n                return to starting point feature.\n                ', tunable_type=int, default=6), enabled_name='radius_to_return_within'), 'randomize_orientation': Tunable(description='\n            Make Waypoint orientation random.  Default is velocity aligned.\n            ', tunable_type=bool, default=False)}

    def get_routes_gen(self):
        waypoint_generator = self.waypoint_generator(WaypointContext(self._obj), None)
        waypoints = []
        constraints = itertools.chain((waypoint_generator.get_start_constraint(),), waypoint_generator.get_waypoint_constraints_gen(self._obj, self.waypoint_count))
        obj_start_constraint = Circle(self._obj.position, self.return_to_starting_point, routing_surface=self._obj.routing_surface, los_reference_point=None)
        constraints = itertools.chain(constraints, obj_start_constraint)
        for constraint in constraints:
            goals = list(itertools.chain.from_iterable(h.get_goals() for h in constraint.get_connectivity_handles(self._obj)))
            if not goals:
                pass
            else:
                for goal in goals:
                    goal.orientation = sims4.math.angle_to_yaw_quaternion(random.uniform(0.0, sims4.math.TWO_PI))
                waypoints.append(goals)
        if not (self.return_to_starting_point is not None and waypoints):
            return False
        routing_context = self._obj.get_routing_context()
        for route_waypoints in self.waypoint_stitching(waypoints, waypoint_generator.loops):
            route = routing.Route(self._obj.routing_location, route_waypoints[-1], waypoints=route_waypoints[:-1], routing_context=routing_context)
            yield route
        return True

    def get_randomize_orientation(self):
        return self.randomize_orientation

class ObjectRoutingBehaviorFromRoutingSlotConstraint(_ObjectRoutingBehaviorBase):
    _unavailable_objects = WeakSet()
    FACTORY_TUNABLES = {'tags': TunableTags(description='\n            Route to an object matching these tags.\n            ', filter_prefixes=('Func',)), 'constraint': TunableRoutingSlotConstraint(description='\n            Use the point on the found object defined by this animation boundary\n            condition.\n            ', class_restrictions=(ObjectAnimationElement,)), 'route_fail': OptionalTunable(description='\n            If enabled, show a route failure balloon if the agent is unable to\n            route to the routing slot constraint.\n            ', tunable=BalloonVariant.TunableFactory(), enabled_name='show_balloon'), 'parent_relation': Tunable(description="\n            If checked, then this routing behavior is affected by the object's\n            parenting relation:\n             * We'll prefer to route to our previous parent, if it still exists\n             * We'll only route to objects that have no children\n             * We won't route to objects that other objects have picked to route to\n             * We'll stop routing if an object becomes the target's child\n            ", tunable_type=bool, default=False)}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        objects = services.object_manager().get_objects_matching_tags(self.tags)
        if self.parent_relation:
            object_routing_component = self._obj.get_component(types.OBJECT_ROUTING_COMPONENT)
            objects = sorted(objects, key=lambda o: o is not object_routing_component.previous_parent)
        for target in objects:
            if not target.is_connected(self._obj):
                pass
            else:
                if self.parent_relation:
                    if target.children:
                        pass
                    elif target in self._unavailable_objects:
                        pass
                    else:
                        target.register_for_on_children_changed_callback(self._on_target_changed)
                        target.register_on_location_changed(self._on_target_changed)
                        self._target = target
                        self._unavailable_objects.add(target)
                        break
                target.register_on_location_changed(self._on_target_changed)
                self._target = target
                self._unavailable_objects.add(target)
                break
        self._target = None

    def _on_target_changed(self, child, *_, **__):
        self._target.unregister_for_on_children_changed_callback(self._on_target_changed)
        self._target.unregister_on_location_changed(self._on_target_changed)
        self._unavailable_objects.discard(self._target)
        if child is not self._obj:
            object_routing_component = self._obj.get_component(types.OBJECT_ROUTING_COMPONENT)
            object_routing_component.restart_running_behavior()

    def get_routes_gen(self):
        if self._target is None:
            return False
        routing_slot_constraint = self.constraint.create_constraint(self._obj, self._target)
        goals = list(itertools.chain.from_iterable(h.get_goals() for h in routing_slot_constraint.get_connectivity_handles(self._obj)))
        routing_context = self._obj.get_routing_context()
        route = routing.Route(self._obj.routing_location, goals, routing_context=routing_context)
        yield route

class ObjectRouteFromRoutingFormation(_ObjectRoutingBehaviorBase):
    FACTORY_TUNABLES = {'formation_type': TunableReference(description='\n            The formation type to look for on the target. This is the routing\n            formation that we want to satisfy constraints for.\n            ', manager=services.get_instance_manager(sims4.resources.Types.SNIPPET), class_restrictions=('RoutingFormation',))}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        routing_component = self._obj.routing_component
        routing_master = routing_component.routing_master
        if routing_master is not None:
            self._target = routing_master
        else:
            self._target = None

    def get_routes_gen(self):
        if self._target is None:
            return False
        slave_data = self._target.get_formation_data_for_slave(self._obj)
        if slave_data is None:
            return False
        starting_location = self._target.intended_location
        transform = slave_data.find_good_location_for_slave(starting_location)
        if transform is None:
            return False
        goal = Goal(routing.Location(transform.translation, transform.orientation, starting_location.routing_surface))
        routing_context = self._obj.get_routing_context()
        route = routing.Route(self._obj.routing_location, (goal,), routing_context=routing_context)
        yield route

class ObjectRouteFromFGL(_ObjectRoutingBehaviorBase):
    FACTORY_TUNABLES = {'surface_type_override': OptionalTunable(description="\n            If enabled, we will use this surface type instead of the one from\n            the object's location.\n            ", tunable=TunableEnumEntry(description='\n                The surface type we want to force.\n                ', tunable_type=SurfaceType, default=SurfaceType.SURFACETYPE_WORLD, invalid_enums=(SurfaceType.SURFACETYPE_UNKNOWN,)))}

    def get_routes_gen(self):
        routing_surface = self._obj.routing_surface
        routing_surface = SurfaceIdentifier(routing_surface.primary_id, routing_surface.secondary_id, self.surface_type_override)
        starting_location = placement.create_starting_location(transform=self._obj.location.transform, routing_surface=routing_surface)
        fgl_context = placement.create_fgl_context_for_object(starting_location, self._obj)
        (position, orientation) = find_good_location(fgl_context)
        if self.surface_type_override is not None and position is None or orientation is None:
            return False
        if vector3_almost_equal(position, starting_location.position):
            return True
        goal = Goal(routing.Location(position, orientation, starting_location.routing_surface))
        routing_context = self._obj.get_routing_context()
        route = routing.Route(self._obj.routing_location, (goal,), routing_context=routing_context)
        yield route
