import mathimport randomfrom event_testing.resolver import SingleObjectResolverfrom interactions.context import InteractionContext, InteractionSource, QueueInsertStrategyfrom interactions.priority import Priorityfrom interactions.utils.loot import LootOperationListfrom objects.terrain import TerrainPointfrom terrain import get_terrain_heightfrom weather.lightning_tuning import LightningTuningimport build_buyimport clockimport objectsimport placementimport routingimport servicesimport sims4.logimport sims4.mathimport sims4.randomlogger = sims4.log.Logger('Lightning', default_owner='rmccord')
class LightningStrike:

    @staticmethod
    def perform_active_lightning_strike():
        lightning_tuning = LightningTuning.ACTIVE_LIGHTNING
        lightning_weights = lightning_tuning.weights
        weighted_strike_fns = ((lightning_weights.weight_terrain, LightningStrike.strike_terrain), (lightning_weights.weight_object, LightningStrike.strike_object), (lightning_weights.weight_sim, LightningStrike.strike_sim))
        lightning_strike_fn = sims4.random.weighted_random_item(weighted_strike_fns)
        if lightning_strike_fn is not None:
            lightning_strike_fn()

    @staticmethod
    def _get_terrain_position_and_routing_surface_for_lightning_strike():
        lot_center = services.active_lot().center
        zone = services.current_zone()
        max_dist = math.sqrt(max((lot_center - spawn_point.get_approximate_center()).magnitude_squared() for spawn_point in zone.spawn_points_gen()))
        zone_id = zone.id

        def _get_random_position_and_routing_surface():
            theta = random.random()*sims4.math.TWO_PI
            scaled_dist = random.random()*max_dist
            x = scaled_dist*math.cos(theta) + lot_center.x
            z = scaled_dist*math.sin(theta) + lot_center.z
            routing_surface = routing.get_routing_surface_at_or_below_position(sims4.math.Vector3(x, sims4.math.MAX_FLOAT, z))
            y = get_terrain_height(x, z, routing_surface=routing_surface)
            return (sims4.math.Vector3(x, y, z), routing_surface)

        count = 20
        (position, routing_surface) = _get_random_position_and_routing_surface()
        while count and not build_buy.is_location_outside(zone_id, position, routing_surface.secondary_id):
            (position, routing_surface) = _get_random_position_and_routing_surface()
            count -= 1
        if not count:
            return (None, None)
        return (position, routing_surface)

    @staticmethod
    def create_collectible_from_lightning_strike(location):
        create_tuning = LightningTuning.STRIKE_TERRAIN_TUNING.create_object_tuning
        weighted_items = [(def_weight.weight, def_weight.definition) for def_weight in create_tuning.definition_weights]
        obj_def = sims4.random.weighted_random_item(weighted_items)
        search_flags = placement.FGLSearchFlag.STAY_IN_CONNECTED_CONNECTIVITY_GROUP | placement.FGLSearchFlag.CALCULATE_RESULT_TERRAIN_HEIGHTS | placement.FGLSearchFlag.DONE_ON_MAX_RESULTS | placement.FGLSearchFlag.ALLOW_GOALS_IN_SIM_POSITIONS
        starting_location = placement.create_starting_location(location=location)
        fgl_context = placement.create_fgl_context_for_object(starting_location, obj_def, search_flags=search_flags)
        (new_position, new_orientation) = placement.find_good_location(fgl_context)
        if new_position is None or new_orientation is None:
            logger.info('No good location found for {} from a lightning strike at {}.', obj_def, location, owner='rmccord')
            return
        new_location = sims4.math.Location(sims4.math.Transform(new_position, new_orientation), location.routing_surface)
        created_obj = objects.system.create_object(obj_def)
        if created_obj is not None:
            created_obj.opacity = 0
            created_obj.fade_in()
            created_obj.set_location(new_location)
            created_obj.set_household_owner_id(None)

    @staticmethod
    def strike_terrain(position=None):
        lightning_strike_tuning = LightningTuning.STRIKE_TERRAIN_TUNING
        if position is None:
            (position, routing_surface) = LightningStrike._get_terrain_position_and_routing_surface_for_lightning_strike()
            if position is None:
                return
        else:
            routing_surface = routing.SurfaceIdentifier(services.current_zone_id(), 0, routing.SurfaceType.SURFACETYPE_WORLD)
        terrain_point = TerrainPoint.create_for_position_and_orientation(position, routing_surface)
        lot = services.active_lot()
        if lot.is_position_on_lot(position):
            fire_service = services.get_fire_service()
            fire_service.add_delayed_scorch_mark(position, routing_surface, clock.interval_in_real_seconds(lightning_strike_tuning.scorch_mark_delay))
            effect = lightning_strike_tuning.effect_on_lot(None, transform_override=terrain_point.transform)
        else:
            effect = lightning_strike_tuning.effect_off_lot(None, transform_override=terrain_point.transform)
        effect.start_one_shot()
        broadcaster_request = lightning_strike_tuning.broadcaster(terrain_point)
        broadcaster_request.start_one_shot()
        create_tuning = lightning_strike_tuning.create_object_tuning
        if random.random() < create_tuning.chance:
            weather_service = services.weather_service()
            weather_service.create_lightning_collectible_alarm(clock.interval_in_real_seconds(lightning_strike_tuning.scorch_mark_delay), terrain_point.location)

    @staticmethod
    def _get_object_for_lightning_strike():
        lightning_strike_tuning = LightningTuning.STRIKE_OBJECT_TUNING
        object_manager = services.object_manager()
        lightning_objects = []
        for obj in object_manager.get_objects_with_tags_gen(*lightning_strike_tuning.tags):
            if obj.is_sim:
                pass
            elif not obj.is_outside:
                pass
            else:
                weight = obj.get_lightning_strike_multiplier()
                if not weight:
                    pass
                else:
                    lightning_objects.append((weight, obj))
        return sims4.random.weighted_random_item(lightning_objects)

    @staticmethod
    def strike_object(obj_to_strike=None):
        lightning_strike_tuning = LightningTuning.STRIKE_OBJECT_TUNING
        if obj_to_strike is None:
            obj_to_strike = LightningStrike._get_object_for_lightning_strike()
        if obj_to_strike is None:
            LightningStrike.strike_terrain()
            return
        lot = services.active_lot()
        position = obj_to_strike.position
        if lot.is_position_on_lot(position):
            fire_service = services.get_fire_service()
            fire_service.add_delayed_scorch_mark(position, obj_to_strike.routing_surface, clock.interval_in_real_seconds(lightning_strike_tuning.scorch_mark_delay))
        effect = lightning_strike_tuning.effect(obj_to_strike)
        effect.start_one_shot()
        broadcaster_request = lightning_strike_tuning.broadcaster(obj_to_strike)
        broadcaster_request.start_one_shot()
        loot_ops_list = LootOperationList(SingleObjectResolver(obj_to_strike), lightning_strike_tuning.generic_loot_on_strike)
        loot_ops_list.apply_operations()
        if obj_to_strike.weather_aware_component is not None:
            obj_to_strike.weather_aware_component.on_struck_by_lightning()

    @staticmethod
    def _get_sim_for_lightning_strike():
        sim_info_manager = services.sim_info_manager()
        lightning_sims = []
        for sim in sim_info_manager.instanced_sims_gen():
            if not sim.is_outside:
                pass
            else:
                weight = sim.get_lightning_strike_multiplier()
                if not weight:
                    pass
                else:
                    lightning_sims.append((weight, sim))
        return sims4.random.weighted_random_item(lightning_sims)

    @staticmethod
    def strike_sim(sim_to_strike=None):
        lightning_strike_tuning = LightningTuning.STRIKE_SIM_TUNING
        if sim_to_strike is None:
            sim_to_strike = LightningStrike._get_sim_for_lightning_strike()
            specific_sim = False
        else:
            specific_sim = True
        if sim_to_strike is not None and lightning_strike_tuning.affordance is not None:
            context = InteractionContext(sim_to_strike, InteractionSource.SCRIPT, priority=Priority.Critical, run_priority=Priority.Critical, insert_strategy=QueueInsertStrategy.FIRST)
            result = sim_to_strike.push_super_affordance(lightning_strike_tuning.affordance, None, context)
            if result:
                return
        if specific_sim:
            logger.error('Lightning affordance could not be pushed on {}', sim_to_strike)
        LightningStrike.strike_object()
