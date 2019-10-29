from _sims4_collections import frozendictfrom sims4.tuning.tunable import HasTunableFactory, AutoFactoryInit, TunableMapping, TunableEnumEntry, TunableList, TunableTuple, OptionalTunableimport enumimport sims4.logimport sims4.mathfrom build_buy import is_location_outsidefrom event_testing.resolver import SingleObjectResolver, SingleSimResolverfrom interactions.utils.loot import LootActions, LootOperationListfrom objects.components import Component, componentmethod_with_fallbackfrom objects.components.types import WEATHER_AWARE_COMPONENTfrom routing import SurfaceTypefrom routing.portals.portal_tuning import PortalFlagsfrom routing.route_enums import RouteEventType, RoutingStageEventfrom routing.route_events.route_event import RouteEventfrom routing.route_events.route_event_provider import RouteEventProviderMixinfrom tunable_multiplier import TunableMultiplierfrom weather.weather_enums import WeatherTypeimport serviceslogger = sims4.log.Logger('WeatherAwareComponent', default_owner='nabaker')
class WeatherAwareComponent(RouteEventProviderMixin, Component, HasTunableFactory, AutoFactoryInit, component_name=WEATHER_AWARE_COMPONENT):

    class TunableWeatherAwareMapping(TunableMapping):

        def __init__(self, start_description=None, end_description=None, **kwargs):
            super().__init__(key_type=TunableEnumEntry(description='\n                    The weather type we are interested in.\n                    ', tunable_type=WeatherType, default=WeatherType.UNDEFINED), value_type=TunableTuple(start_loot=TunableList(description=start_description, tunable=LootActions.TunableReference(description='\n                            The loot action applied.\n                            ', pack_safe=True)), end_loot=TunableList(description=end_description, tunable=LootActions.TunableReference(description='\n                            The loot action applied.\n                            ', pack_safe=True))), **kwargs)
            self.cache_key = 'TunableWeatherAwareMapping'

        def load_etree_node(self, node=None, source=None, **kwargs):
            value = super().load_etree_node(node=node, source=source, **kwargs)
            modified_dict = {}
            for (weather_type, loots) in value.items():
                if not loots.start_loot:
                    if loots.end_loot:
                        modified_dict[weather_type] = loots
                modified_dict[weather_type] = loots
            return frozendict(modified_dict)

    FACTORY_TUNABLES = {'inside_loot': TunableWeatherAwareMapping(description="\n            A tunable mapping linking a weather type to the loot actions the \n            component owner should get when inside.\n            \n            WeatherType will be UNDEFINED if weather isn't installed.\n            ", start_description='\n                Loot actions the owner should get when the weather \n                starts if inside or when the object moves inside \n                during the specified weather.\n                ', end_description='\n                Loot actions the owner should get when the weather \n                ends if inside or when the object moves outside \n                during the specified weather.\n                '), 'outside_loot': TunableWeatherAwareMapping(description="\n            A tunable mapping linking a weather type to the loot actions the \n            component owner should get when outside.\n            \n            WeatherType will be UNDEFINED if weather isn't installed.\n            ", start_description='\n                Loot actions the owner should get when the weather \n                starts if outside or when the object moves outside \n                during the specified weather.\n                ', end_description='\n                Loot actions the owner should get when the weather \n                ends if outside or when the object moves inside \n                during the specified weather.\n                '), 'anywhere_loot': TunableWeatherAwareMapping(description="\n            A tunable mapping linking a weather type to the loot actions the \n            component owner should get regardless of inside/outside location.\n            \n            WeatherType will be UNDEFINED if weather isn't installed.\n            Anywhere actions happen after inside/outside actions when weather starts.\n            Anywhere actions happen before inside/outside actions when weather ends.\n            ", start_description='\n                Loot actions the owner should get when the weather \n                starts regardless of location.\n                ', end_description='\n                Loot actions the owner should get when the weather \n                ends regardless of location.\n                '), 'disable_loot': TunableList(description='\n            A list of loot actions to apply to the owner of this component when\n            the component is disabled.\n            ', tunable=LootActions.TunableReference(description='\n                The loot action applied.\n                ', pack_safe=True)), 'enable_loot': TunableList(description='\n            A list of loot actions to apply to the owner of this component when\n            the component is enabled.\n            ', tunable=LootActions.TunableReference(description='\n                The loot action applied.\n                ', pack_safe=True)), 'lightning_strike_loot': TunableList(description='\n            A list of loot actions to apply to the owner of this component when\n            they are struck by lightning.\n            ', tunable=LootActions.TunableReference(description='\n                The loot action applied.\n                ', pack_safe=True)), 'umbrella_route_events': OptionalTunable(description='\n            If tuned, we will consider points around inside/outside threshold\n            to handle umbrella route events.\n            ', tunable=TunableTuple(description='\n                Data used to populate fields on the path plan context.\n                ', enter_carry_event=RouteEvent.TunablePackSafeReference(description='\n                    To be moved into weather aware component.\n                    Route event to trigger umbrella carry.\n                    '), exit_carry_event=RouteEvent.TunablePackSafeReference(description='\n                    To be moved into weather aware component.\n                    Route event to trigger umbrella carry.\n                    '))), 'lightning_strike_multiplier': OptionalTunable(description='\n            If enabled, we will modify the chance that this object is struck by\n            lightning. Note that the object must be tagged as an object that\n            can be struck. See Lightning module tuning.\n            ', tunable=TunableMultiplier.TunableFactory(description='\n                A multiplier to the weight for this object to be struck by\n                lightning instead of other objects. \n                \n                Note that this affects Sims as well, but will affect the chance\n                this Sim is struck vs. other Sims, not other objects.\n                '))}

    class LocationUpdateStatus(enum.Int, export=False):
        NOT_IN_PROGRESS = 0
        IN_PROGRESS = 1
        PENDING = 2

    def __init__(self, *args, parent=True, **kwargs):
        super().__init__(*args, **kwargs)
        self._is_outside = None
        self._location_update_status = WeatherAwareComponent.LocationUpdateStatus.NOT_IN_PROGRESS
        self._inside_sensitive = True if self.outside_loot or self.inside_loot else False
        self._disabled_count = 0
        self._safety_umbrella_putaway_event = None

    def is_valid_to_add(self):
        if not super().is_valid_to_add():
            return False
        if not self.lightning_strike_loot:
            if self.umbrella_route_events is None:
                return False
            elif self.umbrella_route_events.enter_carry_event or not self.umbrella_route_events.exit_carry_event:
                return False
        return True

    def enable(self, value):
        if not value:
            if self.enabled:
                if self.owner.manager is not None and services.current_zone().is_zone_running:
                    self._update_location(disabling=True)
                    if self.owner.is_sim:
                        resolver = SingleSimResolver(self.owner.sim_info)
                    else:
                        resolver = SingleObjectResolver(self.owner)
                    loot_ops_list = LootOperationList(resolver, self.disable_loot)
                    loot_ops_list.apply_operations()
                self.on_remove()
            self._disabled_count += 1
        else:
            self._disabled_count -= 1
            if self.enabled:
                if self.owner.is_sim:
                    resolver = SingleSimResolver(self.owner.sim_info)
                else:
                    resolver = SingleObjectResolver(self.owner)
                loot_ops_list = LootOperationList(resolver, self.enable_loot)
                loot_ops_list.apply_operations()
                self.on_add()
                if self._inside_sensitive:
                    self.on_location_changed_callback()
            elif self._disabled_count < 0:
                logger.error('Unbalanced enabled/disable in weathercomponent.  Called disable once more than enable.')
                self._disabled_count = 0

    @property
    def enabled(self):
        return self._disabled_count == 0

    def on_add(self):
        if self.enabled:
            if self._inside_sensitive:
                self.owner.register_on_location_changed(self.on_location_changed_callback)
            else:
                self.on_location_changed_callback()
            if self._has_routing_events():
                self.owner.routing_component.register_routing_stage_event(RoutingStageEvent.ROUTE_END, self._on_route_finished)

    def on_remove(self):
        if self.enabled:
            self._stop()
            if self.owner.is_on_location_changed_callback_registered(self.on_location_changed_callback):
                self.owner.unregister_on_location_changed(self.on_location_changed_callback)
            if self._has_routing_events():
                self.owner.routing_component.unregister_routing_stage_event(RoutingStageEvent.ROUTE_END, self._on_route_finished)

    def _stop(self):
        weather_service = services.weather_service()
        if weather_service is not None:
            weather_service.flush_weather_aware_message(self.owner)
            if self._is_outside is not None:
                weather_types = set(self.anywhere_loot)
                if self._is_outside:
                    weather_types.update(self.outside_loot)
                else:
                    weather_types.update(self.inside_loot)
                weather_service.deregister_object(self.owner, weather_types)
        self._is_outside = None

    def on_added_to_inventory(self):
        if self.enabled:
            if not self._inside_sensitive:
                self.on_location_changed_callback()
            self._stop()

    def on_removed_from_inventory(self):
        if self.enabled:
            self.on_location_changed_callback()

    def on_finalize_load(self):
        if self.enabled and not self.owner.is_sim:
            self._update_location()

    def on_preroll_autonomy(self):
        if self.enabled:
            is_inside_override = False
            next_interaction = self.owner.queue.peek_head()
            if next_interaction.counts_as_inside:
                is_inside_override = True
            self._update_location(is_inside_override=is_inside_override)

    def on_buildbuy_exit(self):
        if self.enabled:
            self._update_location()

    def on_location_changed_callback(self, *_, **__):
        if self.enabled and self.owner.manager is not None and services.current_zone().is_zone_running:
            self._update_location()

    def _update_location(self, is_inside_override=False, disabling=False):
        if disabling:
            is_outside = None
        elif is_inside_override:
            is_outside = False
        elif self.owner.is_in_inventory():
            is_outside = None
        elif not self._inside_sensitive:
            is_outside = True
        else:
            is_outside = self.owner.is_outside
        if is_outside == self._is_outside:
            return
        if self._location_update_status != WeatherAwareComponent.LocationUpdateStatus.NOT_IN_PROGRESS:
            self._location_update_status = WeatherAwareComponent.LocationUpdateStatus.PENDING
            return
        self._location_update_status = WeatherAwareComponent.LocationUpdateStatus.IN_PROGRESS
        was_outside = self._is_outside
        self._is_outside = is_outside
        recurse = False
        try:
            weather_service = services.weather_service()
            if weather_service is not None:
                weather_types = weather_service.get_current_weather_types()
                weather_service.update_weather_aware_message(self.owner)
            else:
                weather_types = {WeatherType.UNDEFINED}
            if self.owner.is_sim:
                resolver = SingleSimResolver(self.owner.sim_info)
            else:
                resolver = SingleObjectResolver(self.owner)
            if was_outside is not None:
                if was_outside:
                    self._give_loot(weather_types, self.outside_loot, resolver, False)
                    if weather_service is not None:
                        weather_service.deregister_object(self.owner, self.outside_loot.keys())
                else:
                    self._give_loot(weather_types, self.inside_loot, resolver, False)
                    if weather_service is not None:
                        weather_service.deregister_object(self.owner, self.inside_loot.keys())
            if is_outside is not None:
                if is_outside:
                    self._give_loot(weather_types, self.outside_loot, resolver, True)
                    if weather_service is not None:
                        weather_service.register_object(self.owner, self.outside_loot.keys())
                        weather_service.register_object(self.owner, self.anywhere_loot.keys())
                else:
                    self._give_loot(weather_types, self.inside_loot, resolver, True)
                    if weather_service is not None:
                        weather_service.register_object(self.owner, self.inside_loot.keys())
                        weather_service.register_object(self.owner, self.anywhere_loot.keys())
                if was_outside is None:
                    self._give_loot(weather_types, self.anywhere_loot, resolver, True)
            else:
                self._give_loot(weather_types, self.anywhere_loot, resolver, False)
                if weather_service is not None:
                    weather_service.deregister_object(self.owner, self.anywhere_loot.keys())
            recurse = self._location_update_status == WeatherAwareComponent.LocationUpdateStatus.PENDING
        finally:
            self._location_update_status = WeatherAwareComponent.LocationUpdateStatus.NOT_IN_PROGRESS
        if recurse:
            self._update_location(is_inside_override=is_inside_override, disabling=disabling)

    def _give_loot(self, weather_types, loot_dict, resolver, is_start):
        for weather_type in weather_types & loot_dict.keys():
            loot = loot_dict[weather_type].start_loot if is_start else loot_dict[weather_type].end_loot
            for loot_action in loot:
                loot_action.apply_to_resolver(resolver)

    @componentmethod_with_fallback(lambda *_, **__: None)
    def give_weather_loot(self, weather_types, is_start):
        if self._is_outside is not None:
            if self.owner.is_sim:
                resolver = SingleSimResolver(self.owner.sim_info)
            else:
                resolver = SingleObjectResolver(self.owner)
            if not is_start:
                self._give_loot(weather_types, self.anywhere_loot, resolver, is_start)
            if self._is_outside:
                self._give_loot(weather_types, self.outside_loot, resolver, is_start)
            else:
                self._give_loot(weather_types, self.inside_loot, resolver, is_start)
            if is_start:
                self._give_loot(weather_types, self.anywhere_loot, resolver, is_start)

    @componentmethod_with_fallback(lambda *_, **__: 1.0)
    def get_lightning_strike_multiplier(self):
        if not self.enabled:
            return 0
        elif self.lightning_strike_multiplier is not None:
            return self.lightning_strike_multiplier.get_multiplier(SingleObjectResolver(self.owner))
        return 1.0

    def on_struck_by_lightning(self):
        loot_ops_list = LootOperationList(SingleObjectResolver(self.owner), self.lightning_strike_loot)
        loot_ops_list.apply_operations()

    def _on_route_finished(self, *_, **__):
        self._safety_umbrella_putaway_event = None

    def is_route_event_valid(self, route_event, time, sim, path):
        if not self.enabled:
            return False
        if self._safety_umbrella_putaway_event is route_event:
            location = path.final_location
            if is_location_outside(self.owner.zone_id, location.transform.translation, location.routing_surface.secondary_id):
                self._safety_umbrella_putaway_event = None
                return False
            elif not sims4.math.almost_equal(time, path.duration() - 0.5):
                self._safety_umbrella_putaway_event = None
                return False
        return True

    def _no_regular_put_away_scheduled(self, route_event_context):
        if self._safety_umbrella_putaway_event is None:
            return not route_event_context.route_event_already_scheduled(self.umbrella_route_events.exit_carry_event, provider=self)
        for route_event in route_event_context.route_event_of_data_type_gen(type(self._safety_umbrella_putaway_event.event_data)):
            if route_event is not self._safety_umbrella_putaway_event:
                return False
        return True

    def _has_routing_events(self):
        if self.umbrella_route_events is None or self.umbrella_route_events.enter_carry_event is None or self.umbrella_route_events.exit_carry_event is None:
            return False
        return True

    def provide_route_events(self, route_event_context, sim, path, start_time=0, end_time=0, **kwargs):
        if not self.enabled:
            return
        if not self._has_routing_events():
            return
        resolver = SingleSimResolver(sim.sim_info)
        can_carry_umbrella = self.umbrella_route_events.enter_carry_event.test(resolver)
        added_enter_carry = False
        added_exit_carry = False
        is_prev_point_outside = None
        prev_time = None
        node = None
        prev_node = None
        prev_force_no_carry = False
        for (transform, routing_surface, time) in path.get_location_data_along_path_gen(time_step=0.5, start_time=start_time, end_time=end_time):
            force_no_carry = routing_surface.type == SurfaceType.SURFACETYPE_POOL
            if not force_no_carry:
                node = path.node_at_time(time)
                if node is prev_node:
                    force_no_carry = prev_force_no_carry
                elif node.portal_object_id != 0:
                    portal_object = services.object_manager(routing_surface.primary_id).get(node.portal_object_id)
                    if portal_object is not None:
                        portal_instance = portal_object.get_portal_by_id(node.portal_id)
                        force_no_carry = portal_instance is not None and (portal_instance.portal_template is not None and (portal_instance.portal_template.required_flags is not None and portal_instance.portal_template.required_flags & PortalFlags.REQUIRE_NO_CARRY == PortalFlags.REQUIRE_NO_CARRY))
            level = 0 if routing_surface is None else routing_surface.secondary_id
            is_curr_point_outside = is_location_outside(self.owner.zone_id, transform.translation, level)
            if is_prev_point_outside is None:
                is_prev_point_outside = is_curr_point_outside
                prev_time = time
            else:
                if not route_event_context.route_event_already_scheduled(self.umbrella_route_events.enter_carry_event, provider=self):
                    route_event_context.add_route_event(RouteEventType.FIRST_OUTDOOR, self.umbrella_route_events.enter_carry_event(provider=self, time=time))
                    added_enter_carry = True
                if self._no_regular_put_away_scheduled(route_event_context):
                    route_event_context.add_route_event(RouteEventType.LAST_OUTDOOR, self.umbrella_route_events.exit_carry_event(provider=self, time=prev_time))
                    added_exit_carry = True
                if added_exit_carry:
                    break
                is_prev_point_outside = is_curr_point_outside
                prev_time = time
                prev_node = node
                prev_force_no_carry = force_no_carry
        if self._safety_umbrella_putaway_event is None:
            location = path.final_location
            if not is_location_outside(self.owner.zone_id, location.transform.translation, location.routing_surface.secondary_id):
                self._safety_umbrella_putaway_event = self.umbrella_route_events.exit_carry_event(provider=self, time=path.duration() - 0.5)
                route_event_context.add_route_event(RouteEventType.LAST_OUTDOOR, self._safety_umbrella_putaway_event)
