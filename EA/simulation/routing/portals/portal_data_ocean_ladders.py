import routingimport sims4.logfrom postures.base_postures import MobilePosturefrom postures.posture_specs import get_origin_spec, get_origin_spec_carryfrom protocolbuffers import Routing_pb2from routing import Locationfrom routing.portals.portal_data_base import _PortalTypeDataBasefrom routing.portals.portal_enums import PathSplitTypefrom routing.portals.portal_location import _PortalLocationfrom routing.portals.portal_tuning import PortalType, PortalFlagsfrom routing.route_enums import RouteEventTypefrom routing.route_events.route_event import RouteEventfrom routing.route_events.route_event_provider import RouteEventProviderMixinfrom sims4 import hash_utilfrom sims4.tuning.tunable import TunableRange, TunableTuplelogger = sims4.log.Logger('OceanLaddersPortalData', default_owner='trevor')
class _PortalTypeDataOceanLadders(RouteEventProviderMixin, _PortalTypeDataBase):
    FACTORY_TUNABLES = {'climb_up_locations': TunableTuple(description='\n            Location tunables for climbing up the ladder.\n            ', location_start=_PortalLocation.TunableFactory(description='\n                The location at the bottom of the ladder where climbing up starts.\n                '), location_end=_PortalLocation.TunableFactory(description='\n                The location at the top of the ladder where climbing up ends.\n                ')), 'climb_down_locations': TunableTuple(description='\n            Location tunables for climbing down the ladder.\n            ', location_start=_PortalLocation.TunableFactory(description='\n                The location at the top of the ladder where climbing down starts.\n                '), location_end=_PortalLocation.TunableFactory(description='\n                The location at the bottom of the ladder where climbing down ends.\n                ')), 'climb_up_route_event': RouteEvent.TunableReference(description="\n            The route event to set a posture while climing up the ladder portal.\n            Currently, only Set Posture is supported. If any other route events\n            are tuned here there's a good chance they won't work as expected.\n            "), 'climb_down_route_event': RouteEvent.TunableReference(description="\n            The route even tto set a posture while climbing down the ladder portal.\n            Currently, only Set Posture is supported. If any other route events\n            are tuned here there's a good chance they won't work as expected.\n            "), 'posture_start': MobilePosture.TunableReference(description='\n            Define the entry posture as you cross through this portal. e.g. For\n            the pool, the start posture is stand.\n            '), 'posture_end': MobilePosture.TunableReference(description='\n            Define the exit posture as you cross through this portal.\n            '), 'route_event_time_offset': TunableRange(description='\n            The amount of time after the start of the ladder portal to schedule \n            the route event. \n            ', tunable_type=float, default=0.5, minimum=0, maximum=1)}
    LADDER_RUNG_DISTANCE = 0.25
    LADDER_UP_START_CYCLE = 'ladder_up_start'
    LADDER_UP_CLIMB_CYCLE = 'ladder_up_cycle_r'
    LADDER_UP_STOP_CYCLE = 'ladder_up_stop'
    LADDER_DOWN_START_CYCLE = 'ladder_down_start'
    LADDER_DOWN_CLIMB_CYCLE = 'ladder_down_cycle_r'
    LADDER_DOWN_STOP_CYCLE = 'ladder_down_stop'
    WALKSTYLE_DURATION = 'duration'
    WALKSTYLE_WALK = sims4.hash_util.hash32('Walk')
    WALKSTYLE_SWIM = sims4.hash_util.hash32('Swim')

    @property
    def portal_type(self):
        return PortalType.PortalType_Animate

    @property
    def requires_los_between_points(self):
        return False

    @property
    def outfit_change(self):
        pass

    @property
    def lock_portal_on_use(self):
        return False

    def split_path_on_portal(self):
        return PathSplitType.PathSplitType_LadderSplit

    def add_portal_data(self, actor, portal_instance, is_mirrored, walkstyle):
        op = Routing_pb2.RouteLadderData()
        op.traversing_up = not is_mirrored
        op.step_count = 0
        node_data = Routing_pb2.RouteNodeData()
        node_data.type = Routing_pb2.RouteNodeData.DATA_LADDER
        node_data.data = op.SerializeToString()
        node_data.do_stop_transition = True
        node_data.do_start_transition = True
        return node_data

    def get_portal_duration(self, portal_instance, is_mirrored, _, age, gender, species):
        if is_mirrored:
            walkstyle = self.WALKSTYLE_WALK
            start_cycle = self.LADDER_DOWN_START_CYCLE
            stop_cycle = self.LADDER_DOWN_STOP_CYCLE
            climb_cycle = self.LADDER_DOWN_CLIMB_CYCLE
        else:
            walkstyle = self.WALKSTYLE_SWIM
            start_cycle = self.LADDER_UP_START_CYCLE
            stop_cycle = self.LADDER_UP_STOP_CYCLE
            climb_cycle = self.LADDER_UP_CLIMB_CYCLE
        walkstyle_info_dict = routing.get_walkstyle_info_full(walkstyle, age, gender, species)
        walkstyle_duration = self._get_duration_for_cycle(start_cycle, walkstyle_info_dict) + self._get_duration_for_cycle(climb_cycle, walkstyle_info_dict)*self._get_num_rungs(portal_instance.obj) + self._get_duration_for_cycle(stop_cycle, walkstyle_info_dict)
        return walkstyle_duration

    def _get_num_rungs(self, ladder):
        rung_start = self.climb_up_locations.location_start(ladder).position.y
        rung_end = self.climb_up_locations.location_end(ladder).position.y - self.LADDER_RUNG_DISTANCE
        return (rung_end - rung_start)//self.LADDER_RUNG_DISTANCE + 1

    def _get_duration_for_cycle(self, clip, walkstyle_info_dict):
        builder_name = hash_util.hash32(clip)
        if builder_name not in walkstyle_info_dict:
            logger.error("Can't find the ladder clip {} in the  walkstyle info.", clip)
            return 0
        return walkstyle_info_dict[builder_name][self.WALKSTYLE_DURATION]

    def get_portal_locations(self, obj):
        up_start = self.climb_up_locations.location_start(obj)
        up_end = self.climb_up_locations.location_end(obj)
        down_start = self.climb_down_locations.location_start(obj)
        down_end = self.climb_down_locations.location_end(obj)
        locations = [(Location(up_start.position, orientation=up_start.orientation, routing_surface=up_start.routing_surface), Location(up_end.position, orientation=up_end.orientation, routing_surface=up_end.routing_surface), Location(down_start.position, orientation=down_start.orientation, routing_surface=down_start.routing_surface), Location(down_end.position, orientation=down_end.orientation, routing_surface=down_end.routing_surface), PortalFlags.STAIRS_PORTAL_LONG)]
        return locations

    def provide_route_events(self, route_event_context, sim, path, is_mirrored=True, node=None, **kwargs):
        route_event = self.climb_down_route_event if is_mirrored else self.climb_up_route_event
        if route_event_context.route_event_already_scheduled(route_event, provider=self) or not route_event_context.route_event_already_fully_considered(route_event, self):
            route_event_context.add_route_event(RouteEventType.LOW_SINGLE, route_event(provider=self, time=node.time + self.route_event_time_offset))

    def is_route_event_valid(self, route_event, time, sim, path):
        return True

    def get_posture_change(self, portal_instance, is_mirrored, initial_posture):
        if initial_posture is not None and initial_posture.carry_target is not None:
            start_posture = get_origin_spec_carry(self.posture_start)
            end_posture = get_origin_spec_carry(self.posture_end)
        else:
            start_posture = get_origin_spec(self.posture_start)
            end_posture = get_origin_spec(self.posture_end)
        if is_mirrored:
            return (end_posture, start_posture)
        return (start_posture, end_posture)
