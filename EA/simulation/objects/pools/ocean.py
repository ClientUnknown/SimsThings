from _math import Vector3, Quaternion, Transformfrom sims4.math import Location, vector_cross, UP_AXIS, vector_normalize, vector_dot, VECTOR3_ZERO, FORWARD_AXIS, EPSILONfrom singletons import DEFAULTimport cachesimport sims4.logfrom animation.posture_manifest_constants import SWIM_AT_NONE_CONSTRAINT, STAND_AT_NONE_CONSTRAINTfrom interactions.constraints import WaterDepthIntervals, OceanStartLocationConstraint, ANYWHEREfrom objects.components.types import PORTAL_COMPONENTfrom objects.game_object import GameObjectfrom objects.pools.swimming_mixin import SwimmingMixinfrom objects.terrain import OceanPointfrom plex.plex_enums import PlexBuildingTypefrom routing import SurfaceIdentifier, SurfaceTypefrom sims.sim_info_types import SpeciesExtendedfrom terrain import adjust_locations_for_target_water_depth, adjust_locations_for_coastline, get_water_depthfrom world.ocean_tuning import OceanTuningimport build_buyimport serviceslogger = sims4.log.Logger('Ocean', default_owner='rmccord')
class Ocean(SwimmingMixin, GameObject):
    EDGE_PORTAL_BACKSET = FORWARD_AXIS*-0.25
    EDGE_TEST_POINT_OFFSET = FORWARD_AXIS*0.05

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._off_lot_portals_created = False
        self._constraint_starts = dict()
        self._lot_locator_transforms = []
        self._lot_constraint_starts_base_lengths = dict()
        self._lot_portals = []
        portal_component = self.get_component(PORTAL_COMPONENT)
        if portal_component is None:
            logger.error('{} has no portal component.', self)
        else:
            portal_component.refresh_enabled = False

    @property
    def is_valid_posture_graph_object(self):
        return True

    def get_bounding_box(self):
        p = self.transform.translation
        p = sims4.math.Vector2(p.x, p.z)
        return sims4.geometry.QtRect(p + sims4.math.Vector2(-0.5, -0.5), p + sims4.math.Vector2(0.5, 0.5))

    def _get_lot_locator_transforms(self):
        persistence_service = services.get_persistence_service()
        current_zone_id = services.current_zone_id()
        house_description_id = persistence_service.get_house_description_id(current_zone_id)
        building_type = PlexBuildingType(services.get_building_type(house_description_id))
        if building_type == PlexBuildingType.COASTAL:
            active_lot = services.active_lot()
            return active_lot.get_front_side_transforms()
        return []

    def _clean_lot_transforms_and_portals(self):
        for (key, base_length) in self._lot_constraint_starts_base_lengths.items():
            if key in self._constraint_starts:
                self._constraint_starts[key] = self._constraint_starts[key][:base_length]
        portal_component = self.get_component(PORTAL_COMPONENT)
        if self._lot_portals and portal_component is not None:
            portal_component.remove_custom_portals(self._lot_portals)
        self._lot_locator_transforms.clear()
        self._lot_constraint_starts_base_lengths.clear()
        self._lot_portals.clear()

    @staticmethod
    def _get_raw_normal(t0, t1):
        original_forward = t0.transform_vector(sims4.math.FORWARD_AXIS)
        cross = vector_cross(UP_AXIS, t1.translation - t0.translation)
        if EPSILON < cross.magnitude_squared():
            n = vector_normalize(cross)
            original_forward = t0.transform_vector(sims4.math.FORWARD_AXIS)
            if vector_dot(n, original_forward) < 0.0:
                n = n*-1.0
        else:
            n = original_forward
        return n

    @staticmethod
    def _get_transform_1(p, n0):
        return Transform(p, Quaternion.from_forward_vector(n0))

    @staticmethod
    def _get_transform_2(p, n0, n1):
        return Transform(p, Quaternion.from_forward_vector(n0*0.5 + n1*0.5))

    @staticmethod
    def _get_transform_3(p, n0, n1, n2):
        return Transform(p, Quaternion.from_forward_vector(n0*0.25 + n1*0.5 + n2*0.25))

    def _reorient_lot_transforms(self, lot_transforms):
        length = len(lot_transforms)
        if length > 2:
            raw_normals = []
            for i in range(length - 2):
                raw_normal = Ocean._get_raw_normal(lot_transforms[i], lot_transforms[i + 1])
                raw_normals.append(raw_normal)
            raw_normals.append(raw_normals[-1])
            new_transforms = []
            new_transforms.append(Ocean._get_transform_2(lot_transforms[0].translation, raw_normals[0], raw_normals[1]))
            for i in range(1, length - 1):
                new_transforms.append(Ocean._get_transform_3(lot_transforms[i].translation, raw_normals[i], raw_normals[i], raw_normals[i]))
            new_transforms.append(Ocean._get_transform_2(lot_transforms[-1].translation, raw_normals[-2], raw_normals[-1]))
            return new_transforms
        elif length == 2:
            raw_normal = Ocean._get_raw_normal(lot_transforms[0], lot_transforms[1])
            new_transforms = []
            new_transforms.append(Ocean._get_transform_2(lot_transforms[0].translation, raw_normal, raw_normal))
            new_transforms.append(Ocean._get_transform_2(lot_transforms[-1].translation, raw_normal, raw_normal))
            return new_transforms
        return lot_transforms

    def _create_all_transforms_and_portals_for_initial_transforms(self, initial_transforms, lot_transforms=False, prior_lengths=None, store_portal_ids=None):
        portal_component = self.get_component(PORTAL_COMPONENT)
        if portal_component is None:
            return

        def _store_transforms(species, ages, interval, transforms):
            for age in ages:
                key = (species, age, interval)
                if key in self._constraint_starts:
                    if prior_lengths is not None:
                        prior_lengths[key] = len(self._constraint_starts[key])
                    self._constraint_starts[key].extend(transforms)
                else:
                    if prior_lengths is not None:
                        prior_lengths[key] = 0
                    self._constraint_starts[key] = transforms

        routing_surface = SurfaceIdentifier(services.current_zone_id(), 0, SurfaceType.SURFACETYPE_WORLD)
        edge_transforms = adjust_locations_for_coastline(initial_transforms)

        def _get_water_depth_at_edge(i):
            transform = edge_transforms[i]
            translation = transform.translation + transform.orientation.transform_vector(Ocean.EDGE_TEST_POINT_OFFSET)
            return get_water_depth(translation.x, translation.z)

        for (species, age_data) in OceanTuning.OCEAN_DATA.items():
            for age_ocean_data in age_data:
                ocean_data = age_ocean_data.ocean_data
                beach_portal = ocean_data.beach_portal_data
                wading_depth = ocean_data.wading_interval.lower_bound
                max_wading_depth = wading_depth + ocean_data.water_depth_error
                swim_depth = ocean_data.wading_interval.upper_bound
                min_swim_depth = swim_depth - ocean_data.water_depth_error
                transforms = adjust_locations_for_target_water_depth(wading_depth, ocean_data.water_depth_error, initial_transforms)
                wading_transforms = []
                for i in range(len(transforms) - 1):
                    transform = transforms[i]
                    if transform.translation == VECTOR3_ZERO:
                        depth = _get_water_depth_at_edge(i)
                        if depth <= max_wading_depth:
                            wading_transforms.append(edge_transforms[i])
                    else:
                        wading_transforms.append(transform)
                transforms = adjust_locations_for_target_water_depth(swim_depth, ocean_data.water_depth_error, initial_transforms)
                portal_transforms = []
                for i in range(len(transforms) - 1):
                    transform = transforms[i]
                    if transform.translation == VECTOR3_ZERO:
                        depth = _get_water_depth_at_edge(i)
                        if min_swim_depth <= depth:
                            edge_transform = edge_transforms[i]
                            translation = edge_transform.translation + edge_transform.orientation.transform_vector(Ocean.EDGE_PORTAL_BACKSET)
                            portal_transforms.append(Transform(translation, edge_transform.orientation))
                    else:
                        portal_transforms.append(transform)
                _store_transforms(species, age_ocean_data.ages, WaterDepthIntervals.WET, edge_transforms.copy())
                _store_transforms(species, age_ocean_data.ages, WaterDepthIntervals.WADE, wading_transforms)
                _store_transforms(species, age_ocean_data.ages, WaterDepthIntervals.SWIM, portal_transforms)
                if beach_portal is None:
                    pass
                else:
                    if lot_transforms:
                        portal_transforms = self._reorient_lot_transforms(portal_transforms)
                    portal_creation_mask = SpeciesExtended.get_portal_flag(species)
                    for portal_transform in portal_transforms:
                        portal_location = Location(portal_transform, routing_surface=routing_surface)
                        portal_ids = portal_component.add_custom_portal(OceanPoint(portal_location), beach_portal, portal_creation_mask)
                        add_portals = []
                        remove_portals = []
                        for portal_id in portal_ids:
                            portal_instance = portal_component.get_portal_by_id(portal_id)
                            if portal_instance is not None:
                                location = None
                                if portal_id == portal_instance.there:
                                    location = portal_instance.there_entry
                                elif portal_id == portal_instance.back:
                                    location = portal_instance.back_exit
                                if location and build_buy.is_location_natural_ground(location.routing_surface.primary_id, location.position, location.routing_surface.secondary_id):
                                    add_portals.append(portal_id)
                                else:
                                    remove_portals.append(portal_id)
                        if remove_portals:
                            portal_component.remove_custom_portals(remove_portals)
                        if add_portals and store_portal_ids is not None:
                            store_portal_ids.extend(add_portals)

    def on_finalize_load(self):
        super().on_finalize_load()
        portal_component = self.get_component(PORTAL_COMPONENT)
        if portal_component is None:
            return
        locator_manager = services.locator_manager()
        locators = locator_manager.get(OceanTuning.get_beach_locator_definition().id)
        initial_transforms = [locator.transform for locator in locators]
        street_instance = services.current_zone().street
        if street_instance is not None:
            for beach_data in street_instance.beaches:
                beach_forward = Vector3(beach_data.forward.x, 0, beach_data.forward.y)
                orientation = Quaternion.from_forward_vector(beach_forward)
                transform = Transform(translation=beach_data.position, orientation=orientation)
                initial_transforms.append(transform)
        if not initial_transforms:
            self._off_lot_portals_created = False
            return
        off_lot_portal_ids = []
        self._create_all_transforms_and_portals_for_initial_transforms(initial_transforms, store_portal_ids=off_lot_portal_ids)
        self._off_lot_portals_created = bool(off_lot_portal_ids)
        self._lot_locator_transforms = self._get_lot_locator_transforms()
        if self._lot_locator_transforms:
            self._create_all_transforms_and_portals_for_initial_transforms(self._lot_locator_transforms, lot_transforms=True, prior_lengths=self._lot_constraint_starts_base_lengths, store_portal_ids=self._lot_portals)
        if self._off_lot_portals_created or self._lot_portals:
            services.object_manager().add_portal_to_cache(self)

    def on_location_changed(self, old_location):
        self._build_routing_surfaces()
        super().on_location_changed(old_location)

    def on_buildbuy_exit(self):
        currently_in_portal_cache = self._off_lot_portals_created or bool(self._lot_portals)
        self._clean_lot_transforms_and_portals()
        self._lot_locator_transforms = self._get_lot_locator_transforms()
        if self._lot_locator_transforms:
            self._create_all_transforms_and_portals_for_initial_transforms(self._lot_locator_transforms, lot_transforms=True, prior_lengths=self._lot_constraint_starts_base_lengths, store_portal_ids=self._lot_portals)
        portals_created = self._off_lot_portals_created or bool(self._lot_portals)
        if currently_in_portal_cache and not portals_created:
            services.object_manager().remove_portal_from_cache(self)
        elif currently_in_portal_cache or portals_created:
            services.object_manager().add_portal_to_cache(self)
        super().on_buildbuy_exit()

    def get_edge_constraint(self, constraint_width=1.0, inward_dir=False, return_constraint_list=False, los_reference_point=DEFAULT, sim=None):
        constraint_list = []
        if inward_dir:
            constraint_list.append(SWIM_AT_NONE_CONSTRAINT)
            routing_surface = SurfaceIdentifier(services.current_zone_id(), 0, SurfaceType.SURFACETYPE_POOL)
            interval = WaterDepthIntervals.SWIM
        else:
            constraint_list.append(STAND_AT_NONE_CONSTRAINT)
            routing_surface = SurfaceIdentifier(services.current_zone_id(), 0, SurfaceType.SURFACETYPE_WORLD)
            interval = WaterDepthIntervals.WET
        constraint = OceanStartLocationConstraint.create_simple_constraint(interval, constraint_width, sim, routing_surface=routing_surface, los_reference_point=los_reference_point)
        if not constraint.valid:
            constraint = ANYWHERE
        if return_constraint_list:
            constraint_list.append(constraint)
            return constraint_list
        for other_constraint in constraint_list:
            constraint = constraint.intersect(other_constraint)
        return constraint

    @caches.cached
    def get_nearest_constraint_start_location(self, species, age, start_position, interval:WaterDepthIntervals):
        surface_type = None
        if interval == WaterDepthIntervals.WALK or interval == WaterDepthIntervals.WET or interval == WaterDepthIntervals.WADE:
            surface_type = SurfaceType.SURFACETYPE_WORLD
        elif interval == WaterDepthIntervals.SWIM:
            surface_type = SurfaceType.SURFACETYPE_POOL
        else:
            logger.error('Unhandled water depth interval {}'.format(interval))
        surface_id = SurfaceIdentifier(services.current_zone_id(), 0, surface_type)
        if interval == WaterDepthIntervals.WALK:
            interval = WaterDepthIntervals.WADE
        key = (species, age, interval)
        if key not in self._constraint_starts:
            return
        else:
            starts = self._constraint_starts[key]
            if starts:
                best_start = starts[0]
                best_distSq = (start_position - best_start.translation).magnitude_squared()
                for start in starts[1:]:
                    distSq = (start_position - start.translation).magnitude_squared()
                    if distSq < best_distSq:
                        best_start = start
                        best_distSq = distSq
                return Location(best_start, surface_id)

@sims4.commands.Command('ocean.portals.stats', command_type=sims4.commands.CommandType.DebugOnly)
def dump_ocean_portal_stats(_connection=None):
    ocean = services.terrain_service.ocean_object()
    if ocean is None:
        sims4.commands.output('No ocean object instanced', _connection)
        return
    if not ocean._constraint_starts:
        sims4.commands.output('No ocean portals', _connection)
        return
    counts = 'Ocean Locators:\nTuned: {}\nEnvironment: {}\nLot: {}\nTotal: {}\nOff Lot Portal Counts:'.format(len(ocean._tuned_locator_transforms), len(ocean._beach_locator_transforms), len(ocean._lot_locator_transforms), len(ocean._locator_transforms) + len(ocean._lot_locator_transforms))
    sims4.commands.output(counts, _connection)
    total_count = 0
    for (key, count) in ocean._portal_counts.items():
        (species, ages) = key
        sims4.commands.output('    {}, {}: {}'.format(species, ages, count), _connection)
        total_count = total_count + count
    sims4.commands.output('On Lot Portal Counts:', _connection)
    for (key, count) in ocean._lot_portal_counts.items():
        (species, ages) = key
        sims4.commands.output('    {}, {}: {}'.format(species, ages, count), _connection)
        total_count = total_count + count
    sims4.commands.output('Total Portals Created: {}'.format(total_count), _connection)
