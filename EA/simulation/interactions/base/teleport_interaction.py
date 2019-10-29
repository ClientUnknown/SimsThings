from animation.animation_utils import flush_all_animationsfrom event_testing.results import TestResultfrom interactions.base.interaction_constants import InteractionQueuePreparationStatusfrom interactions.base.super_interaction import SuperInteractionfrom objects.system import create_objectfrom objects.terrain import TerrainSuperInteractionfrom sims4.tuning.tunable import OptionalTunable, TunableReference, Tunable, TunableEnumEntryfrom sims4.tuning.tunable_base import GroupNamesfrom sims4.utils import classproperty, constpropertyfrom teleport.teleport_enums import TeleportStylefrom teleport.teleport_helper import TeleportHelperimport element_utilsimport placementimport routingimport servicesimport sims4.logimport sims4.mathlogger = sims4.log.Logger('Teleport')
class TeleportHereInteraction(TerrainSuperInteraction):
    INSTANCE_TUNABLES = {'target_jig': OptionalTunable(description='\n            If enabled, a jig can be tuned to place at the target location of\n            the teleport. If placement fails, the interaction will fail.\n            ', tunable=TunableReference(description='\n                The jig to test the target location against.\n                ', manager=services.definition_manager(), class_restrictions='Jig'), tuning_group=GroupNames.CORE), '_teleporting': Tunable(description='\n            If checked, sim will be instantly be teleported without playing\n             any type of animation.\n             ', tunable_type=bool, default=True)}
    _ignores_spawn_point_footprints = True

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.dest_goals = None

    @classmethod
    def _test(cls, target, context, **kwargs):
        (position, surface) = cls._get_position_and_surface(target, context)
        if position is None or surface is None:
            return TestResult(False, 'Cannot go here without a pick or target.')
        location = routing.Location(position, sims4.math.Quaternion.IDENTITY(), surface)
        if not routing.test_connectivity_permissions_for_handle(routing.connectivity.Handle(location), context.sim.routing_context):
            return TestResult(False, 'Cannot TeleportHere! Unroutable area.')
        return TestResult.TRUE

    def _run_interaction_gen(self, timeline):
        if not self._teleporting:
            return True
        starting_loc = placement.create_starting_location(transform=self.target.transform, routing_surface=self.target.routing_surface)
        if self.target_jig is not None:
            fgl_context = placement.create_fgl_context_for_object(starting_loc, self.target_jig)
        else:
            fgl_context = placement.create_fgl_context_for_sim(starting_loc, self.sim)
        (position, orientation) = placement.find_good_location(fgl_context)
        if position is None:
            return False
        end_transform = sims4.math.Transform(position, orientation)
        self.sim.routing_component.on_slot = None
        ending_location = sims4.math.Location(end_transform, self.target.routing_surface)
        self.sim.location = ending_location
        self.sim.refresh_los_constraint()
        return True

    @classproperty
    def is_teleport_style_injection_allowed(cls):
        return False

    @constproperty
    def should_perform_routing_los_check():
        return False

class TeleportInteraction(SuperInteraction):
    _teleporting = True

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.dest_goals = []

    def _run_interaction_gen(self, timeline):
        for goal in self.dest_goals:
            goal_transform = sims4.math.Transform(goal.location.transform.translation, self.sim.location.transform.orientation)
            goal_surface = goal.routing_surface_id
            goal_location = sims4.math.Location(goal_transform, goal_surface)
            self.sim.set_location(goal_location)
            break
        result = yield from super()._run_interaction_gen(timeline)
        return result

    @classproperty
    def is_teleport_style_injection_allowed(cls):
        return False

    @constproperty
    def should_perform_routing_los_check():
        return False

class TeleportStyleSuperInteraction(TerrainSuperInteraction):
    INSTANCE_TUNABLES = {'destination_jig': OptionalTunable(description='\n            If a jig is needed to reserve space where the Sim will teleport to, \n            this should be enabled.\n            ', tunable=TunableReference(manager=services.definition_manager()), tuning_group=GroupNames.CORE), 'destination_must_be_outside': Tunable(description='\n            Whether the jig can only be placed outside.\n            ', tunable_type=bool, default=False, tuning_group=GroupNames.CORE), 'teleport_style_tuning': TunableEnumEntry(description='\n            Teleport style that is used to get the Sim from their start to end\n            points.\n            ', tunable_type=TeleportStyle, default=TeleportStyle.NONE, invalid_enums=(TeleportStyle.NONE,), pack_safe=True, tuning_group=GroupNames.CORE), 'required_destination_surface': OptionalTunable(description='\n            If a destination routing surface is required, it should be\n            specified here.  If it is not specified, the routing surface\n            of the target will be used to place jigs or to specify a location\n            to teleport to.\n            ', tunable=TunableEnumEntry(description='\n                The routing surface that must be used when planning a teleport\n                destination.\n                ', tunable_type=routing.SurfaceType, default=routing.SurfaceType.SURFACETYPE_UNKNOWN, invalid_enums=(routing.SurfaceType.SURFACETYPE_UNKNOWN,)), tuning_group=GroupNames.CORE)}

    def __init__(self, context, *args, **kwargs):
        super().__init__(context, *args, **kwargs)
        self._teleport_location = None
        self._destination_jig_object = None

    @classmethod
    def _test(cls, target, context, **kwargs):
        result = super()._test(target, context, **kwargs)
        if not result:
            return result
        (position, surface) = cls._get_position_and_surface(target, context)
        if position is None or surface is None:
            return TestResult(False, 'No pick or target.')
        location = routing.Location(position, sims4.math.Quaternion.IDENTITY(), surface)
        if not routing.test_connectivity_permissions_for_handle(routing.connectivity.Handle(location), context.sim.routing_context):
            return TestResult(False, 'Unroutable area.')
        return TestResult.TRUE

    def prepare_gen(self, timeline, *args, **kwargs):
        if not self.sim.can_sim_teleport_using_teleport_style():
            return InteractionQueuePreparationStatus.FAILURE
        try:
            (starting_position, routing_surface_id) = self._get_position_and_surface(self.target, self.context)
            desired_level = self._get_level_of_target(self.target, self.context)
            if desired_level is not None:
                if self.required_destination_surface is not None:
                    zone_id = services.current_zone_id()
                    routing_surface_id = routing.SurfaceIdentifier(zone_id or 0, desired_level, self.required_destination_surface)
                starting_location = routing.Location(starting_position, routing_surface=routing_surface_id)
                if self.destination_jig is not None:
                    self._destination_jig_object = self._create_jig_object()
                    if self._destination_jig_object is not None:
                        (position, orientation) = TeleportHelper.get_fgl_at_destination_for_teleport(starting_location, self._destination_jig_object, destination_must_be_outside=self.destination_must_be_outside)
                        if orientation is not None:
                            self._destination_jig_object.move_to(translation=position, orientation=orientation, routing_surface=routing_surface_id)
                            object_slots = self.destination_jig.get_slots_resource(0)
                            jig_slot_transform = object_slots.get_slot_transform_by_index(sims4.ObjectSlots.SLOT_ROUTING, 0)
                            jig_slot_concat_transform = sims4.math.Transform.concatenate(sims4.math.Transform(position, orientation), jig_slot_transform)
                            self._teleport_location = routing.Location(jig_slot_concat_transform.translation, orientation=jig_slot_concat_transform.orientation, routing_surface=routing_surface_id)
                else:
                    (position, orientation) = TeleportHelper.get_fgl_at_destination_for_teleport(starting_location, self.sim, destination_must_be_outside=self.destination_must_be_outside)
                    if services.current_zone().lot.is_position_on_lot(starting_position):
                        front_door = services.get_door_service().get_front_door()
                        if front_door:
                            door_location = routing.Location(front_door.position, routing_surface=front_door.routing_surface)
                            (position, orientation) = TeleportHelper.get_fgl_at_destination_for_teleport(door_location, self.sim, destination_must_be_outside=self.destination_must_be_outside, ignore_connectivity=True)
                    if orientation is not None:
                        self._teleport_location = routing.Location(position, orientation=orientation, routing_surface=routing_surface_id)
        except Exception as exception:
            logger.exception('Exception while getting teleport location for TeleportStyleSuperInteraction: ', exc=exception, level=sims4.log.LEVEL_ERROR)
            self._try_destroy_jig_object()
        if self._teleport_location is None:
            return InteractionQueuePreparationStatus.FAILURE
        result = yield from super().prepare_gen(timeline, **kwargs)
        return result

    def build_basic_content(self, sequence=(), *args, **kwargs):

        def _perform_teleport(timeline):
            active_multiplier = self.sim.sim_info.get_active_teleport_multiplier()
            (teleport_style_data, cost) = self.sim.sim_info.get_teleport_data_and_cost(self.teleport_style_tuning, active_multiplier)
            (sequence, animation_interaction) = TeleportHelper.generate_teleport_sequence(self.sim, teleport_style_data, self._teleport_location.position, self._teleport_location.orientation, self._teleport_location.routing_surface, cost)
            if sequence is not None and animation_interaction is not None:
                try:
                    result = yield from element_utils.run_child(timeline, element_utils.build_critical_section(sequence, flush_all_animations))
                finally:
                    animation_interaction.on_removed_from_queue()
                return result

        def _set_up_teleport_style_interaction(_):
            if self._destination_jig_object is not None:
                self.sim.routing_context.ignore_footprint_contour(self._destination_jig_object.routing_context.object_footprint_id)

        def _clean_up_teleport_style_interaction(_):
            self._try_destroy_jig_object()

        sequence = element_utils.build_critical_section(sequence, _perform_teleport)
        sequence = super().build_basic_content(sequence, **kwargs)
        sequence = element_utils.build_critical_section_with_finally(_set_up_teleport_style_interaction, sequence, _clean_up_teleport_style_interaction)
        return sequence

    def _clean_behavior(self):
        self._try_destroy_jig_object()
        super()._clean_behavior()

    def _create_jig_object(self):
        jig_object = create_object(self.destination_jig)
        return jig_object

    def _try_destroy_jig_object(self):
        if self._destination_jig_object is not None:
            if self._destination_jig_object.routing_context is not None:
                self.sim.routing_context.remove_footprint_contour_override(self._destination_jig_object.routing_context.object_footprint_id)
            self._destination_jig_object.destroy()
            self._destination_jig_object = None

    @classproperty
    def is_teleport_style_injection_allowed(cls):
        return False

    @constproperty
    def should_perform_routing_los_check():
        return False
