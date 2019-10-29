from event_testing.resolver import SingleSimResolverfrom routing import Locationfrom teleport.teleport_type_liability import TeleportStyleInjectionLiabilityimport placementimport servicesimport sims4logger = sims4.log.Logger('Teleport', default_owner='camilogarcia')
class TeleportHelper:

    @classmethod
    def generate_teleport_sequence(cls, teleporting_sim, teleport_data, position, orientation, routing_surface, cost=None):

        def _start_vfx(_):
            if teleport_data.fade_out_effect is not None:
                fade_out_vfx = teleport_data.fade_out_effect(teleporting_sim, store_target_position=True)
                fade_out_vfx.start_one_shot()
            fade_out_resolver = SingleSimResolver(teleporting_sim)
            for effect in teleport_data.tested_fade_out_effect(resolver=fade_out_resolver):
                fade_out_vfx = effect(teleporting_sim, store_target_position=True)
                fade_out_vfx.start_one_shot()

        def _fade_sim(_):
            teleporting_sim.fade_out(fade_duration=teleport_data.fade_duration)
            for routing_slave_data in teleporting_sim.get_routing_slave_data():
                if routing_slave_data.allow_slave_to_teleport_with_master:
                    routing_slave_data.slave.fade_out(fade_duration=teleport_data.fade_duration)

        def _teleport_sim(_):
            position.y = services.terrain_service.terrain_object().get_routing_surface_height_at(position.x, position.z, routing_surface)
            teleporting_sim.move_to(translation=position, orientation=orientation, routing_surface=routing_surface)
            sim_location = Location(position, routing_surface=routing_surface)
            for routing_slave_data in teleporting_sim.get_routing_slave_data():
                if routing_slave_data.allow_slave_to_teleport_with_master:
                    (fgl_position, fgl_orientation) = TeleportHelper.get_fgl_at_destination_for_teleport(sim_location, routing_slave_data.slave)
                    if fgl_position is not None and fgl_orientation is not None:
                        fgl_position.y = services.terrain_service.terrain_object().get_routing_surface_height_at(fgl_position.x, fgl_position.z, routing_surface)
                        routing_slave_data.slave.move_to(translation=fgl_position, orientation=fgl_orientation, routing_surface=routing_surface)
                        routing_slave_data.slave.fade_in(fade_duration=teleport_data.fade_duration)
            if teleport_data.teleport_effect is not None:
                fade_in_vfx = teleport_data.teleport_effect(teleporting_sim)
                fade_in_vfx.start_one_shot()
            teleporting_sim.fade_in(fade_duration=teleport_data.fade_duration)
            if cost is not None:
                stat_instance = teleporting_sim.get_stat_instance(teleport_data.teleport_cost.teleport_statistic)
                if stat_instance is None:
                    logger.error('Statistic {}, not found on Sim {} for teleport action', teleport_data.teleport_statistic, teleporting_sim)
                    return
                stat_instance.add_value(cost if teleport_data.teleport_cost.cost_is_additive else -cost)

        animation_interaction = teleporting_sim.create_animation_interaction()
        resolver = SingleSimResolver(teleporting_sim)
        weights = []
        for animation_weight_item in teleport_data.animation_outcomes:
            weight = animation_weight_item.weight.get_multiplier(resolver)
            if weight > 0:
                weights.append((weight, animation_weight_item.animation))
        selected_animation = sims4.random.weighted_random_item(weights)
        if selected_animation is None:
            logger.error('No animation selected when generating teleport sequence {}', teleport_data)
            return (None, None)
        sequence = selected_animation(animation_interaction, sequence=())
        animation_interaction.store_event_handler(_start_vfx, handler_id=teleport_data.start_teleport_vfx_xevt)
        animation_interaction.store_event_handler(_fade_sim, handler_id=teleport_data.start_teleport_fade_sim_xevt)
        animation_interaction.store_event_handler(_teleport_sim, handler_id=teleport_data.teleport_xevt)
        return (sequence, animation_interaction)

    @classmethod
    def get_teleport_style_data_used_for_interaction_route(cls, sim, interaction):
        (_, _, teleport_style_data_from_aop) = sim.get_teleport_style_interaction_aop(interaction)
        if teleport_style_data_from_aop is not None:
            return teleport_style_data_from_aop
        (teleport_style_data_from_sim_info, _, _) = sim.sim_info.get_active_teleport_style()
        return teleport_style_data_from_sim_info

    @classmethod
    def can_teleport_style_be_injected_before_interaction(cls, sim, interaction):
        if interaction.is_teleport_style_injection_allowed and interaction.get_liability(TeleportStyleInjectionLiability.LIABILITY_TOKEN) is not None:
            return False
        elif not sim.can_sim_teleport_using_teleport_style():
            return False
        return True

    @classmethod
    def does_routing_slave_prevent_teleport(cls, sim):
        routing_slave_datas = sim.get_routing_slave_data()
        for slave_data in routing_slave_datas:
            if not slave_data.allow_slave_to_teleport_with_master:
                return True
        return False

    @classmethod
    def get_fgl_at_destination_for_teleport(cls, ideal_location, destination_object, destination_must_be_outside=False, ignore_connectivity=False):
        search_flags = placement.FGLSearchFlagsDefault
        if destination_must_be_outside:
            search_flags |= placement.FGLSearchFlag.STAY_OUTSIDE
        fgl_context = None
        if destination_object.is_sim:
            search_flags |= placement.FGLSearchFlagsDefaultForSim
            if ignore_connectivity:
                search_flags &= ~placement.FGLSearchFlag.STAY_IN_CONNECTED_CONNECTIVITY_GROUP
            fgl_context = placement.create_fgl_context_for_sim(ideal_location, destination_object, search_flags=search_flags)
        else:
            search_flags |= placement.FGLSearchFlagsDefaultForObject
            if ignore_connectivity:
                search_flags &= ~placement.FGLSearchFlag.STAY_IN_CONNECTED_CONNECTIVITY_GROUP
            fgl_context = placement.create_fgl_context_for_object(ideal_location, destination_object, search_flags=search_flags)
        if fgl_context is not None:
            return placement.find_good_location(fgl_context)
        return (None, None)
