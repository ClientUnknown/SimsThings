from _math import Vector2, Vector3from routing import PathPlanContextfrom routing.path_planner.path_plan_enums import FootprintKeyMaskBitsfrom routing.portals.portal_tuning import PortalFlagsfrom sims.sim_info_types import SpeciesExtended, Agefrom sims4.geometry import QtCircle, build_rectangle_from_two_points_and_radiusfrom sims4.tuning.tunable import AutoFactoryInit, HasTunableFactory, TunableRange, OptionalTunable, TunableEnumFlags, HasTunableSingletonFactory, TunableVariant, TunableEnumEntry, TunableMappingfrom singletons import DEFAULTimport placementimport routingimport services
class PathPlanContextWrapper(HasTunableFactory, AutoFactoryInit, PathPlanContext):

    class _AgentShapeCircle(HasTunableSingletonFactory, AutoFactoryInit):
        FACTORY_TUNABLES = {'radius': TunableRange(description="\n                The circle's radius, The circle is built around the agent's\n                center point.\n                ", tunable_type=float, minimum=0, default=0.123)}

        def get_quadtree_polygon(self, position, orientation):
            return QtCircle(Vector2(position.x, position.z), self.radius)

    class _AgentShapeRectangle(HasTunableSingletonFactory, AutoFactoryInit):
        FACTORY_TUNABLES = {'length': TunableRange(description="\n                The rectangle's length. This is parallel to the agent's forward\n                vector.\n                ", tunable_type=float, minimum=0, default=1.5), 'width': TunableRange(description="\n                The rectangle's width. This is perpendicular to the agent's\n                forward vector.\n                ", tunable_type=float, minimum=0, default=0.5)}

        def get_quadtree_polygon(self, position, orientation):
            length_vector = orientation.transform_vector(Vector3.Z_AXIS())*self.length/2
            return build_rectangle_from_two_points_and_radius(position + length_vector, position - length_vector, self.width)

    FACTORY_TUNABLES = {'_agent_radius': TunableRange(description='\n            The size of the agent (as a circle radius), when computing a path.\n            This determines how much space is required for the agent to route\n            through space.\n            ', tunable_type=float, minimum=0, default=0.123), '_agent_shape': TunableVariant(description="\n            The shape used to represent the agent's position and intended\n            position in the quadtree.\n            ", circle=_AgentShapeCircle.TunableFactory(), rectangle=_AgentShapeRectangle.TunableFactory(), default='circle'), '_agent_goal_radius': TunableRange(description='\n            The clearance required (as a circle radius) at the end of a route.\n            ', tunable_type=float, minimum=0, default=0.123), '_agent_extra_clearance_modifier': TunableRange(description="\n            The clearance that the agent will try to maintain from other objects\n            (and go around them), defined as a multiple of the agent's radius.\n            ", tunable_type=float, minimum=0, default=2.5), '_allowed_portal_flags': OptionalTunable(TunableEnumFlags(description='\n                Required portal flags can be set on portals. If these flags are\n                also set on the actor, then that actor is allowed to traverse\n                that portal type.\n                \n                e.g. Counter Surface portals have the "Counter" flag set on the\n                portals. If the "Counter" flag is set on a routing context, then\n                your able to go through counter portals.\n                ', enum_type=PortalFlags)), '_discouraged_portal_flags': OptionalTunable(TunableEnumFlags(description="\n                Flags to set on the Sim to match the discouragement flags on\n                a portal.  If the flags don't match, the Sim will be \n                discouraged from routing through this portal. \n                \n                e.g. Regular doors have a discouragement flag that matches\n                only humans, this way pets will try to use pet doors over \n                regular doors.\n                ", enum_type=PortalFlags)), '_allowed_heights': OptionalTunable(TunableEnumFlags(description='\n                All of the flags that define what this agent is able to route\n                under. Each Flag has a specific height assigned to it.\n                \n                FOOTPRINT_KEY_REQUIRE_SMALL_HEIGHT = 0.5m\n                FOOTPRINT_KEY_REQUIRE_TINY_HEIGHT = 0.25m\n                FOOTPRINT_KEY_REQUIRE_FLOATING = flying agent\n                ', enum_type=FootprintKeyMaskBits, default=FootprintKeyMaskBits.SMALL_HEIGHT)), 'surface_preference_scoring': TunableMapping(description='\n            Surface type and additional score to apply to the cost of goals on \n            this surface.\n            This allows for geometric constraints with multi surface goals, to \n            have preference to specific surface types. i.e Cats always prefer\n            to target surface object goals, so we make the ground more \n            expensive.\n            This will only be applied for multi surface geometric constraints.\n            ', key_type=TunableEnumEntry(description='\n                The surface type for scoring to be applied to.\n                ', tunable_type=routing.SurfaceType, default=routing.SurfaceType.SURFACETYPE_WORLD, invalid_enums=(routing.SurfaceType.SURFACETYPE_UNKNOWN,)), value_type=TunableRange(description='\n                Additive cost to apply when calculating goals for multi surface \n                constraints.\n                ', tunable_type=float, default=10, minimum=0))}

    def __init__(self, agent, **kwargs):
        super().__init__(**kwargs)
        self._agent = agent
        self.agent_id = agent.id
        self.agent_radius = self._agent_radius
        self.agent_extra_clearance_multiplier = self._agent_extra_clearance_modifier
        self.agent_goal_radius = self._agent_goal_radius
        self.footprint_key = agent.definition.get_footprint(0)
        full_keymask = routing.FOOTPRINT_KEY_ON_LOT | routing.FOOTPRINT_KEY_OFF_LOT
        if self._allowed_heights is not None:
            full_keymask |= self._allowed_heights
        self.set_key_mask(full_keymask)
        full_portal_keymask = PortalFlags.DEFAULT
        species = getattr(self._agent, 'extended_species', DEFAULT)
        full_portal_keymask |= SpeciesExtended.get_portal_flag(species)
        age = getattr(self._agent, 'age', DEFAULT)
        full_portal_keymask |= Age.get_portal_flag(age)
        if self._allowed_portal_flags is not None:
            full_portal_keymask |= self._allowed_portal_flags
        self.set_portal_key_mask(full_portal_keymask)
        portal_discouragement_flags = 0
        if self._discouraged_portal_flags is not None:
            portal_discouragement_flags |= self._discouraged_portal_flags
        self.set_portal_discourage_key_mask(portal_discouragement_flags)

    def get_quadtree_polygon(self, position=DEFAULT, orientation=DEFAULT):
        position = self._agent.position if position is DEFAULT else position
        orientation = self._agent.orientation if orientation is DEFAULT else orientation
        return self._agent_shape.get_quadtree_polygon(position, orientation)

    def add_location_to_quadtree(self, placement_type, position=DEFAULT, orientation=DEFAULT, routing_surface=DEFAULT, index=0):
        position = self._agent.position if position is DEFAULT else position
        orientation = self._agent.orientation if orientation is DEFAULT else orientation
        routing_surface = self._agent.routing_surface if routing_surface is DEFAULT else routing_surface
        if placement_type in (placement.ItemType.SIM_POSITION, placement.ItemType.SIM_INTENDED_POSITION):
            quadtree_geometry = self.get_quadtree_polygon(position=position, orientation=orientation)
        else:
            quadtree_geometry = QtCircle(Vector2(position.x, position.z), self.agent_goal_radius)
        services.sim_quadtree().insert(self._agent, self._agent.id, placement_type, quadtree_geometry, routing_surface, False, index)

    def remove_location_from_quadtree(self, placement_type, index=0):
        services.sim_quadtree().remove(self._agent.id, placement_type, index)
