from element_utils import build_critical_section_with_finallyfrom elements import SubclassableGeneratorElementfrom interactions import ParticipantTypefrom placement import FGLTuningfrom sims4.tuning.tunable import HasTunableFactory, AutoFactoryInit, TunableSet, TunableEnumWithFilter, TunableEnumEntry, Tunablefrom world.spawn_point import SpawnPointimport element_utilsimport interactions.constraintsimport placementimport routingimport servicesimport sims4.logimport taglogger = sims4.log.Logger('Spawn Points', default_owner='rmccord')
class DynamicInteractionSpawnPoint(SpawnPoint):
    POSITION_INCREMENT = 0.5

    def __init__(self, interaction, participant_type, distance_to_participant, tag_set, lot_id, zone_id, allow_spawning_on_non_world_routing_surfaces):
        self._interaction = interaction
        self._participant_type = participant_type
        self._distance_to_participant = distance_to_participant
        self._tags = tag_set
        self._allow_spawning_on_non_world_routing_surfaces = allow_spawning_on_non_world_routing_surfaces
        self._routing_surface_override = None
        routing_surface = None
        participant = self._get_participant()
        if participant is not None:
            if participant.routing_surface.type == routing.SurfaceType.SURFACETYPE_WORLD or allow_spawning_on_non_world_routing_surfaces:
                routing_surface = participant.routing_surface
            else:
                level = participant.routing_surface.secondary_id
                routing_surface = routing.SurfaceIdentifier(services.current_zone().id, level, routing.SurfaceType.SURFACETYPE_WORLD)
        super().__init__(lot_id, zone_id, routing_surface=routing_surface)

    def get_approximate_transform(self):
        return sims4.math.Transform(self.next_spawn_spot())

    def get_approximate_center(self):
        participant = self._get_participant()
        if participant is not None:
            return participant.position
        fallback_point = services.current_zone().get_spawn_point(lot_id=self.lot_id)
        (translation, _) = fallback_point.next_spawn_spot()
        return translation

    @property
    def routing_surface(self):
        if self._routing_surface_override is not None:
            return self._routing_surface_override
        return self._routing_surface

    def next_spawn_spot(self):
        trans = self._get_pos()
        orient = self._get_orientation_to_participant(trans)
        return (trans, orient)

    def get_tags(self):
        return self._tags

    def get_name(self):
        participant = self._interaction.get_participant(participant_type=self._participant_type)
        return 'Dynamic Spawn Point near {} in {}'.format(participant, self._interaction)

    def _get_participant(self):
        if self._interaction is None:
            return
        return self._interaction.get_participant(self._participant_type)

    def _get_pos(self):
        participant = self._get_participant()
        trans = None
        if participant is not None:
            scoring_function = placement.ScoringFunctionRadial(participant.location.transform.translation, self._distance_to_participant, 0, FGLTuning.MAX_FGL_DISTANCE)
            search_flags = placement.FGLSearchFlag.STAY_IN_CONNECTED_CONNECTIVITY_GROUP | placement.FGLSearchFlag.USE_SIM_FOOTPRINT | placement.FGLSearchFlag.CALCULATE_RESULT_TERRAIN_HEIGHTS | placement.FGLSearchFlag.SHOULD_TEST_ROUTING
            starting_location = placement.create_starting_location(position=participant.position, orientation=participant.orientation, routing_surface=self.routing_surface)
            fgl_context = placement.FindGoodLocationContext(starting_location, max_distance=FGLTuning.MAX_FGL_DISTANCE, additional_avoid_sim_radius=routing.get_default_agent_radius(), max_steps=10, position_increment=self.POSITION_INCREMENT, offset_distance=self._distance_to_participant, scoring_functions=(scoring_function,), search_flags=search_flags)
            (trans, _) = placement.find_good_location(fgl_context)
        if trans is None:
            fallback_point = services.current_zone().get_spawn_point(lot_id=self.lot_id)
            (trans, _) = fallback_point.next_spawn_spot()
            self._routing_surface_override = fallback_point.routing_surface
            return trans
        return trans

    def _get_orientation_to_participant(self, position):
        participant = self._get_participant()
        if participant is None:
            return sims4.math.Quaternion.IDENTITY()
        target_location = participant.location
        vec_to_target = target_location.transform.translation - position
        theta = sims4.math.vector3_angle(vec_to_target)
        return sims4.math.angle_to_yaw_quaternion(theta)

    def get_position_constraints(self, generalize=False):
        trans = self._get_pos()
        return [interactions.constraints.Position(trans, routing_surface=self.routing_surface, objects_to_ignore=set([self.spawn_point_id]))]

    def validate_connectivity(self, dest_handles):
        pass

    def get_footprint_polygon(self):
        pass

    def get_valid_and_invalid_positions(self):
        return ([self._get_pos()], [])

class DynamicSpawnPointElement(SubclassableGeneratorElement, HasTunableFactory, AutoFactoryInit):
    FACTORY_TUNABLES = {'description': '\n            This Element will create a Dynamic Spawn Point which is registered\n            to a particular participant within the interaction. It will be\n            added to the zone and available for use by any Sims who want to\n            spawn.\n            ', 'tags': TunableSet(description="\n            A set of tags to add to the dynamic spawn point when it's created.\n            This is how we can use this spawn point to spawn particular Sims\n            without interfering with walkbys and other standard Sims that are\n            spawned.\n            ", tunable=TunableEnumWithFilter(tunable_type=tag.Tag, default=tag.Tag.INVALID, filter_prefixes=tag.SPAWN_PREFIX)), 'participant': TunableEnumEntry(description='\n            The Participant of the interaction that we want the spawn point to be near.\n            ', tunable_type=ParticipantType, default=ParticipantType.Actor), 'attach_to_active_lot': Tunable(description='\n            If checked, the spawn point will be attached to the active lot.\n            This helps Sims who are looking to visit the current lot find a\n            spawn point nearby.\n            ', tunable_type=bool, default=False), 'distance_to_participant': Tunable(description='\n            The Distance from the participant that Sims should spawn.\n            ', tunable_type=float, default=7.0), 'allow_spawning_on_non_world_routing_surfaces': Tunable(description='\n            If checked, this spawn point can be generated on routing surfaces\n            of any type. If unchecked, it can only be generated on world\n            routing surfaces.\n            \n            If this tunable is unchecked and the participant is not on a world\n            routing surface, the spawn point will be generated with the world\n            surface type on the same level as the participant.\n            ', tunable_type=bool, default=False)}

    def __init__(self, interaction, *args, sequence=(), **kwargs):
        super().__init__(*args, **kwargs)
        self.interaction = interaction
        self.sequence = sequence
        self.spawn_point = None

    def _run_gen(self, timeline):
        result = yield from element_utils.run_child(timeline, build_critical_section_with_finally(self.start, self.sequence, self.stop))
        return result

    def start(self, *_, **__):
        zone = services.current_zone()
        lot_id = 0 if not self.attach_to_active_lot else zone.lot.lot_id
        self.spawn_point = DynamicInteractionSpawnPoint(self.interaction, self.participant, self.distance_to_participant, self.tags, lot_id, zone.id, self.allow_spawning_on_non_world_routing_surfaces)
        services.current_zone().add_dynamic_spawn_point(self.spawn_point)

    def stop(self, *_, **__):
        services.current_zone().remove_dynamic_spawn_point(self.spawn_point)
        self.spawn_point = None
