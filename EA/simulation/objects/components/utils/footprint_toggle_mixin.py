from objects.helpers.user_footprint_helper import UserFootprintHelperfrom routing.route_enums import RoutingStageEventfrom sims4.tuning.tunable import OptionalTunable, TunableList, TunableTuple, Tunablefrom sims4.tuning.tunable_hash import TunableStringHash32import sims4logger = sims4.log.Logger('FootprintToggle', default_owner='nsavalani')
class FootprintToggleMixin:
    FACTORY_TUNABLES = {'footprint_toggles': OptionalTunable(description="\n            If enabled, we will turn off footprints for this vehicle while it's\n            routing.\n            ", tunable=TunableList(description='\n                List of footprints to toggle.\n                ', tunable=TunableTuple(footprint_hash=TunableStringHash32(description='\n                        Name of the footprint to toggle.\n                        '), push_sims=Tunable(description='\n                        If enabled, Sims will be pushed from this footprint when\n                        it is turned on.\n                        ', tunable_type=bool, default=True)), minlength=1))}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.footprints_enabled = True

    def register_routing_event_callbacks(self):
        self.owner.register_routing_stage_event(RoutingStageEvent.ROUTE_START, self._on_route_start)
        self.owner.register_routing_stage_event(RoutingStageEvent.ROUTE_END, self._on_route_end)

    def unregister_routing_event_callbacks(self):
        self.owner.unregister_routing_stage_event(RoutingStageEvent.ROUTE_START, self._on_route_start)
        self.owner.unregister_routing_stage_event(RoutingStageEvent.ROUTE_END, self._on_route_end)

    def _on_route_start(self, *_, **__):
        if not self.footprint_toggles:
            return
        footprint_component = self.owner.footprint_component
        if footprint_component is None:
            logger.error('Attempt to toggle a footprint on a vehicle ({}) with no footprint component.', self.owner)
            return
        if footprint_component.footprints_enabled:
            self.footprints_enabled = False
            for toggle in self.footprint_toggles:
                footprint_component.start_toggle_footprint(False, toggle.footprint_hash)

    def _on_route_end(self, *_, **__):
        if not self.footprint_toggles:
            return
        if not self.footprints_enabled:
            footprint_component = self.owner.footprint_component
            if footprint_component is None:
                logger.error('Attempt to toggle a footprint on a vehicle ({}) with no footprint component.', self.owner)
                return
            enabled_footprints = set()
            for toggle in self.footprint_toggles:
                footprint_component.stop_toggle_footprint(False, toggle.footprint_hash)
                if toggle.push_sims:
                    enabled_footprints.add(toggle.footprint_hash)
            if enabled_footprints:
                compound_polygon = self.owner.get_polygon_from_footprint_name_hashes(enabled_footprints)
                if compound_polygon is not None:
                    exclude = None
                    if hasattr(self, 'driver'):
                        exclude = (self.driver,) if self.driver is not None else None
                    UserFootprintHelper.force_move_sims_in_polygon(compound_polygon, self.owner.routing_surface, exclude=exclude)
