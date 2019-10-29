from collections import namedtuplefrom date_and_time import DateAndTime, TimeSpanfrom distributor.rollback import ProtocolBufferRollbackfrom event_testing.resolver import SingleSimResolverfrom households.household_tracker import HouseholdTrackerfrom interactions.utils import LootTypefrom sims4.resources import Typesimport alarmsimport servicesimport sims4.log_Delivery = namedtuple('_Delivery', ('sim_id', 'tuning_guid', 'expected_arrival_time'))logger = sims4.log.Logger('DeliveryTracker', default_owner='jdimailig')
class _DeliveryAlarmHandler:

    def __init__(self, tracker, delivery):
        self._tracker = tracker
        self._delivery = delivery

    def __call__(self, timeline):
        self._tracker.try_do_delivery(self._delivery)

class DeliveryTracker(HouseholdTracker):

    def __init__(self, household):
        self._household = household
        self._expected_deliveries = {}

    def request_delivery(self, sim_id, delivery_tuning_guid, time_span_from_now):
        logger.assert_raise(self._household.sim_in_household(sim_id), f'Sim {sim_id} not in household {self._household}')
        expected_arrival_time = services.time_service().sim_now + time_span_from_now
        delivery = _Delivery(sim_id, delivery_tuning_guid, expected_arrival_time)
        self._expected_deliveries[delivery] = alarms.add_alarm(self, time_span_from_now, _DeliveryAlarmHandler(self, delivery), cross_zone=True)

    def try_do_delivery(self, delivery):
        loot_tuning_manager = services.get_instance_manager(Types.ACTION)
        delivery_tuning = loot_tuning_manager.get(delivery.tuning_guid)
        if delivery_tuning is None:
            del self._expected_deliveries[delivery]
            return
        if delivery_tuning.loot_type != LootType.SCHEDULED_DELIVERY:
            logger.error(f'Could not perform delivery for {delivery_tuning}, not a delivery loot.')
            del self._expected_deliveries[delivery]
            return
        sim_info = services.sim_info_manager().get(delivery.sim_id)
        if sim_info is None:
            logger.error(f'Could not perform delivery for {delivery_tuning}, Sim {delivery.sim_id} not found.')
            del self._expected_deliveries[delivery]
            return
        resolver = SingleSimResolver(sim_info)
        if self._household.home_zone_id == services.current_zone_id():
            delivery_tuning.objects_to_deliver.apply_to_resolver(resolver)
            del self._expected_deliveries[delivery]
            at_home_notification_tuning = delivery_tuning.at_home_notification
            if at_home_notification_tuning is not None:
                at_home_notification = at_home_notification_tuning(sim_info, resolver=resolver)
                at_home_notification.show_dialog()
        else:
            not_home_notification_tuning = delivery_tuning.not_home_notification
            if not_home_notification_tuning is not None:
                not_home_notification = not_home_notification_tuning(sim_info, resolver=resolver)
                not_home_notification.show_dialog()

    def on_zone_load(self):
        if self._household.home_zone_id != services.current_zone_id():
            return
        loot_tuning_manager = services.get_instance_manager(Types.ACTION)
        sim_now = services.time_service().sim_now
        for delivery in tuple(self._expected_deliveries):
            if sim_now < delivery.expected_arrival_time:
                pass
            else:
                delivery_tuning = loot_tuning_manager.get(delivery.tuning_guid)
                if delivery_tuning is None:
                    del self._expected_deliveries[delivery]
                else:
                    if delivery_tuning.loot_type != LootType.SCHEDULED_DELIVERY:
                        logger.error(f'Could not perform delivery for {delivery_tuning}, not a delivery loot.')
                        del self._expected_deliveries[delivery]
                        return
                    sim_info = services.sim_info_manager().get(delivery.sim_id)
                    if sim_info is None:
                        logger.error(f'Could not perform delivery for {delivery_tuning}, Sim {delivery.sim_id} not found.')
                        del self._expected_deliveries[delivery]
                    else:
                        resolver = SingleSimResolver(sim_info)
                        delivery_tuning.objects_to_deliver.apply_with_placement_override(sim_info, resolver, self._place_object_in_mailbox)
                        del self._expected_deliveries[delivery]

    def _place_object_in_mailbox(self, subject_to_apply, created_object):
        sim_household = subject_to_apply.household
        if sim_household is not None:
            zone = services.get_zone(sim_household.home_zone_id)
            if zone is not None:
                mailbox_inventory = zone.lot.get_mailbox_inventory(sim_household.id)
                if mailbox_inventory is not None:
                    mailbox_inventory.player_try_add_object(created_object)

    def household_lod_cleanup(self):
        self._expected_deliveries = {}

    def load_data(self, household_proto):
        sim_now = services.time_service().sim_now
        for delivery_data in household_proto.deliveries:
            from_now = DateAndTime(delivery_data.expected_arrival_time) - sim_now
            if from_now <= TimeSpan.ZERO:
                delivery = _Delivery(delivery_data.sim_id, delivery_data.delivery_tuning_guid, delivery_data.expected_arrival_time)
                self._expected_deliveries[delivery] = None
            else:
                self.request_delivery(delivery_data.sim_id, delivery_data.delivery_tuning_guid, from_now)

    def save_data(self, household_proto):
        for delivery in self._expected_deliveries:
            with ProtocolBufferRollback(household_proto.deliveries) as delivery_data:
                delivery_data.sim_id = delivery.sim_id
                delivery_data.delivery_tuning_guid = delivery.tuning_guid
                delivery_data.expected_arrival_time = delivery.expected_arrival_time
