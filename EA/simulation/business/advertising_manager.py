from protocolbuffers import Business_pb2, DistributorOps_pb2from business.business_enums import BusinessAdvertisingTypefrom distributor.ops import GenericProtocolBufferOpfrom distributor.system import Distributorimport servicesimport sims4logger = sims4.log.Logger('Business', default_owner='jdimailig')
class HasAdvertisingManagerMixin:

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._advertising_manager = AdvertisingManager.create_from_business_manager(self)

    def get_advertising_multiplier(self):
        return self._advertising_manager.get_advertising_multiplier()

    def set_advertising_type(self, advertising_type):
        self._advertising_manager.set_advertising_type(advertising_type)

    def get_advertising_type_for_gsi(self):
        return str(self._advertising_manager._advertising_type)

    def get_current_advertising_cost(self):
        return self._advertising_manager.get_current_advertising_cost()

class AdvertisingManager:

    @classmethod
    def create_from_business_manager(cls, business_manager):
        return AdvertisingManager(business_manager, business_manager.tuning_data.advertising_configuration)

    def __init__(self, business_manager, advertising_configuration):
        self._business_manager = business_manager
        self._configuration = advertising_configuration
        self._advertising_type = advertising_configuration.default_advertising_type
        self._advertising_update_time = None
        self._advertising_cost = 0

    def clear_state(self):
        self._advertising_cost = 0
        self._advertising_update_time = None

    def open_business(self):
        self.set_advertising_type(self._advertising_type)

    def get_current_advertising_cost(self):
        return self._advertising_cost + self._get_advertising_cost_since_last_update()

    def get_advertising_cost_per_hour(self):
        return self._configuration.get_advertising_cost_per_hour(self._advertising_type)

    def set_advertising_type(self, advertising_type):
        self._advertising_cost += self._get_advertising_cost_since_last_update()
        self._advertising_update_time = services.time_service().sim_now
        if advertising_type == BusinessAdvertisingType.INVALID:
            logger.error('Attempting to set an INVALID advertising type to {}. This will be ignored.', advertising_type)
        else:
            self._advertising_type = advertising_type
        self._send_advertisement_update_message()

    def get_advertising_multiplier(self):
        return self._configuration.get_customer_count_multiplier(self._advertising_type)

    def _get_advertising_cost_since_last_update(self):
        now = services.time_service().sim_now
        running_cost = 0
        if self._advertising_update_time is None:
            self._advertising_update_time = now
            running_cost = 0
        else:
            hours_in_ad_type = (now - self._advertising_update_time).in_hours()
            running_cost = hours_in_ad_type*self.get_advertising_cost_per_hour()
        return running_cost

    def _send_advertisement_update_message(self):
        msg = Business_pb2.BusinessAdvertisementUpdate()
        msg.zone_id = self._business_manager.business_zone_id
        msg.advertisement_chosen = self._advertising_type
        op = GenericProtocolBufferOp(DistributorOps_pb2.Operation.BUSINESS_ADVERTISEMENT_DATA_UPDATE, msg)
        Distributor.instance().add_op_with_no_owner(op)
