from _collections import defaultdictimport randomfrom sims4.tuning.tunable import OptionalTunable, Tunable, TunableList, TunableTuple, TunableRange, TunableEnumSetfrom tunable_utils.create_object import ObjectCreatorfrom world.terrain_enums import TerrainTagimport placementimport routingimport servicesimport sims4.loglogger = sims4.log.Logger('AttractorCreationDirectorMixin', default_owner='rrodgers')
class AttractorCreationDirectorMixin:
    INSTANCE_TUNABLES = {'attractors': TunableList(description='\n            Attractors are invisible game objects that can be placed by a zone\n            director. These objects can be used to attract sims to special\n            locations on the zone. They can also be used to interface various\n            gameplay systems with "areas of interest" (for instance, a beach).\n            ', tunable=TunableTuple(description='\n                ', placement_circle=TunableTuple(description='\n                   An circle which will be used as the placement footprint to\n                   determine the valid locations for attractor objects.\n                   ', radius=TunableRange(description='\n                        The radius of the placement circle.\n                        ', tunable_type=float, minimum=0, default=1), number_of_sides=TunableRange(description='\n                        The number of sides of the placement circle. More sides\n                        will create a more accurate result but will be less\n                        performant.\n                        ', tunable_type=int, minimum=6, default=10)), samples_per_axis=Tunable(description="\n                    The number of samples we should make along the lot's x axis\n                    when finding good locations for attractor objects.\n                    ", tunable_type=int, default=4), placement_radius=TunableRange(description='\n                    The maxiumum distance we should search to find a good\n                    location for a potential attractor point. This should\n                    rarely be tuned above the default since doing so has serious\n                    performance implications. Beware.\n                    ', tunable_type=float, minimum=0, default=0), attractor_object=ObjectCreator.TunableFactory(description=' \n                    The attractor object that will be placed.\n                    ', get_definition=(True,)), terrain_tags=OptionalTunable(description='\n                    If enabled, a set of allowed terrain tags. The attractor\n                    will be placed in position that matches these terrain tags.\n                    ', tunable=TunableEnumSet(enum_type=TerrainTag, enum_default=TerrainTag.INVALID)), min_water_depth=OptionalTunable(description='\n                    (float) If provided, each vertex of the placement polygon along with its centroid will\n                    be tested to determine whether the ocean water at the test location is at least this deep.\n                    0 indicates that all water placement is valid. To allow land placement, leave untuned.\n                    ', tunable=TunableRange(description='\n                        Value of the min water depth allowed.\n                        ', minimum=0, tunable_type=float, default=0)), max_water_depth=OptionalTunable(description='\n                    (float) If provided, each vertex of the placement polygon along with its centroid will\n                    be tested to determine whether the ocean water at the test location is at most this deep.\n                    To disallow water placement, set to 0. Note that we currently only support placement on the\n                    terrain surface, so will place attractors under water if need be (but not on the surface).\n                    ', tunable=TunableRange(description='\n                        Value of the max water depth allowed.\n                        ', tunable_type=float, minimum=0, maximum=1000.0, default=1000.0)), number_of_attractors=TunableRange(description='\n                    The number of attractors that should be placed on the lot.\n                    ', tunable_type=int, minimum=0, default=3)), tuning_group='Attractors')}

    def __init__(self, *args, **kwargs):
        self._valid_attractor_positions = defaultdict(list)
        self._attractor_ids = defaultdict(list)

    def on_startup(self):
        self._update_attractor_locations()

    def on_exit_buildbuy(self):
        self._update_attractor_locations()

    def on_shutdown(self):
        self._destroy_attractors()

    def _update_attractor_locations(self):
        self._calculate_valid_locations()
        self._place_attractors()

    def _calculate_valid_locations(self):
        self._valid_attractor_positions.clear()
        for attractor_tuning in self.attractors:
            terrain_tags = list(attractor_tuning.terrain_tags) if attractor_tuning.terrain_tags else []
            objects_to_ignore = self._attractor_ids[attractor_tuning]
            sample_points = services.active_lot().get_uniform_sampling_of_points(attractor_tuning.samples_per_axis, attractor_tuning.samples_per_axis)
            for point in sample_points:
                starting_location_for_sample = placement.create_starting_location(position=point)
                placement_polygon = sims4.geometry.generate_circle_constraint(attractor_tuning.placement_circle.number_of_sides, point, attractor_tuning.placement_circle.radius)
                fgl_context = placement.FindGoodLocationContext(starting_location_for_sample, object_polygons=(placement_polygon,), ignored_object_ids=objects_to_ignore, max_distance=attractor_tuning.placement_radius, terrain_tags=terrain_tags, min_water_depth=attractor_tuning.min_water_depth, max_water_depth=attractor_tuning.max_water_depth, search_flags=placement.FGLSearchFlagsDefault | placement.FGLSearchFlag.ALLOW_GOALS_IN_SIM_POSITIONS | placement.FGLSearchFlag.ALLOW_GOALS_IN_SIM_INTENDED_POSITIONS)
                (position, orientation) = placement.find_good_location(fgl_context)
                if position:
                    self._valid_attractor_positions[attractor_tuning].append((position, orientation))

    def _remove_invalid_attractors(self):
        for attractor_tuning in self.attractors:
            attractor_IDs_to_remove = []
            for attractor_id in self._attractor_ids[attractor_tuning]:
                attractor = services.object_manager().get(attractor_id)
                if not attractor:
                    attractor_IDs_to_remove.append(attractor_id)
                elif not any(attractor.position == loc[0] and attractor.orientation == loc[1] for loc in self._valid_attractor_positions[attractor_tuning]):
                    attractor.destroy()
                    attractor_IDs_to_remove.append(attractor_id)
                else:
                    self._valid_attractor_positions[attractor_tuning].remove((attractor.position, attractor.orientation))
            self._attractor_ids[attractor_tuning] = list(x for x in self._attractor_ids[attractor_tuning] if x not in attractor_IDs_to_remove)

    def _place_attractors(self):
        self._remove_invalid_attractors()
        zone_id = services.current_zone_id()
        world_routing_surface = routing.SurfaceIdentifier(zone_id, 0, routing.SurfaceType.SURFACETYPE_WORLD)
        for attractor_tuning in self.attractors:
            num_attractors_to_place = min(attractor_tuning.number_of_attractors - len(self._attractor_ids[attractor_tuning]), len(self._valid_attractor_positions[attractor_tuning]))
            chosen_locations = random.sample(self._valid_attractor_positions[attractor_tuning], num_attractors_to_place)
            for location in chosen_locations:
                attractor = attractor_tuning.attractor_object()
                attractor.move_to(routing_surface=world_routing_surface, translation=location[0], orientation=location[1])
                self._attractor_ids[attractor_tuning].append(attractor.id)

    def _destroy_attractors(self):
        for attractor_tuning in self.attractors:
            for attractor_id in self._attractor_ids[attractor_tuning]:
                attractor = services.object_manager().get(attractor_id)
                if attractor:
                    attractor.destroy()
        self._attractor_ids.clear()
