from interactions.context import InteractionContextfrom interactions.priority import Priorityfrom interactions.utils.loot_basic_op import BaseLootOperation, BaseTargetedLootOperationfrom restaurants.restaurant_tuning import RestaurantTuning, get_restaurant_zone_directorimport servicesimport sims4.loglogger = sims4.log.Logger('Restaurant Loot', default_owner='rfleig')
class ClaimRestaurantTable(BaseLootOperation):

    def _apply_to_subject_and_target(self, subject, target, resolver):
        zone_director = get_restaurant_zone_director()
        if zone_director is None:
            return
        zone_director.claim_table(subject)

class ClaimRestaurantSeat(BaseTargetedLootOperation):

    def _apply_to_subject_and_target(self, subject, target, resolver):
        zone_director = get_restaurant_zone_director()
        if zone_director is None:
            logger.error('Trying to claim a restaurant seat on a non restaurant venue.')
            return
        (subjects_seat_id, subjects_chair_part_id) = zone_director.get_sims_seat(subject)
        if subjects_seat_id is target:
            return
        target_part = None
        if resolver.context.pick is not None:
            parts = target.get_closest_parts_to_position(resolver.context.pick.location)
            if parts:
                target_part = parts.pop()
        if target_part is None:
            target_part = target
        object_manager = services.object_manager()
        if object_manager is None:
            return
        old_seat = object_manager.get(subjects_seat_id)
        use_old_table_as_seat = zone_director.is_picnic_table(old_seat)
        if not old_seat.is_part:
            old_seat = old_seat.get_part_by_part_group_index(subjects_chair_part_id)
        old_dining_spot = zone_director.get_dining_spot_by_seat(subjects_seat_id, chair_part_index=subjects_chair_part_id, use_table_as_seat=use_old_table_as_seat)
        use_new_table_as_seat = zone_director.is_picnic_table(target_part)
        target_dining_spot = zone_director.get_dining_spot_by_seat(target_part.id, chair_part_index=target_part.part_group_index if use_old_table_as_seat and target_part.is_part else None, use_table_as_seat=use_new_table_as_seat)
        if target_dining_spot is not None:
            previous_owner = zone_director.reassign_dining_spot(subject.id, target_dining_spot)
            zone_director.reassign_dining_spot(previous_owner, old_dining_spot)
            sim = object_manager.get(previous_owner)
            if sim is not None:
                seat = object_manager.get(target_dining_spot.seat_id)
                if seat is not None and sim.posture_state.body.target is seat:
                    context = InteractionContext(sim, InteractionContext.SOURCE_SCRIPT, Priority.High)
                    sim.push_super_affordance(RestaurantTuning.SWITCH_SEAT_INTERACTION, old_seat, context)

class ReleaseRestaurantTable(BaseLootOperation):

    def _apply_to_subject_and_target(self, subject, target, resolver):
        zone_director = get_restaurant_zone_director()
        if zone_director is None:
            return
        zone_director.release_table(sim=resolver.context.sim)

class RestaurantExpediteGroupOrder(BaseLootOperation):

    def _apply_to_subject_and_target(self, subject, target, resolver):
        zone_director = get_restaurant_zone_director()
        if zone_director is None:
            return
        if not zone_director.has_group_order(subject.id):
            logger.warn("Trying to rush an order for {} but they don't have an order to rush", subject)
        group_order = zone_director.get_group_order(subject.id)
        if group_order is not None:
            group_order.expedited = True
