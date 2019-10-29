from _collections import defaultdictfrom protocolbuffers import Business_pb2, DistributorOps_pb2from business.business_customer_data import BusinessCustomerDatafrom distributor.ops import GenericProtocolBufferOpfrom distributor.rollback import ProtocolBufferRollbackfrom distributor.system import Distributorimport servicesimport sims4.logfrom gsi_handlers import business_handlerslogger = sims4.log.Logger('Business', default_owner='trevor')
class BusinessCustomerManager:

    def __init__(self, business_manager):
        self._business_manager = business_manager
        self._customer_load_data = []
        self._customers = defaultdict(BusinessCustomerData)
        self._lifetime_customers_served = 0
        self._session_customers_served = 0

    @property
    def session_customers_served(self):
        return self._session_customers_served

    @property
    def lifetime_customers_served(self):
        return self._lifetime_customers_served

    def _clear_state(self):
        self._session_customers_served = 0
        self._send_daily_customers_served_update()

    def add_customer(self, sim_id):
        customer_data = self._customers.get(sim_id, None)
        if customer_data is None:
            customer_data = BusinessCustomerData(self._business_manager, sim_id)
            self._customers[sim_id] = customer_data
        customer_data.setup_customer()

    def remove_customer(self, sim_info, review_business=True):
        if sim_info.sim_id not in self._customers:
            return
        self._customers[sim_info.sim_id].on_remove()
        customer_data = self._customers.pop(sim_info.sim_id)
        if business_handlers.business_archiver.enabled:
            business_handlers.archive_business_event('Customer', None, 'Customer removed reviewed_business:{}'.format(review_business), sim_id=sim_info.sim_id)
        if review_business:
            self._session_customers_served += 1
            self._lifetime_customers_served += 1
            self._business_manager.process_customer_rating(sim_info, customer_data.get_star_rating(), customer_data.buff_bucket_totals)
            self._send_daily_customers_served_update()

    def get_customer_star_rating(self, sim_id):
        customer_data = self._customer_data.get(sim_id, None)
        if customer_data is not None:
            return customer_data.star_rating

    def _send_daily_customers_served_update(self):
        customers_msg = Business_pb2.BusinessDailyCustomersServedUpdate()
        customers_msg.zone_id = self._business_manager.business_zone_id
        customers_msg.daily_customers_served = self.session_customers_served
        op = GenericProtocolBufferOp(DistributorOps_pb2.Operation.BUSINESS_DAILY_CUSTOMERS_SERVED_UPDATE, customers_msg)
        Distributor.instance().add_op_with_no_owner(op)

    def save_data(self, business_save_data):
        business_save_data.lifetime_customers_served = self.lifetime_customers_served
        business_save_data.session_customers_served = self.session_customers_served
        for customer_data in self._customers.values():
            with ProtocolBufferRollback(business_save_data.customer_data) as customer_save_data:
                customer_data.save_data(customer_save_data)

    def load_data(self, business_save_data):
        self._lifetime_customers_served = business_save_data.lifetime_customers_served
        self._session_customers_served = business_save_data.session_customers_served
        self._customers.clear()
        for customer_save_data in business_save_data.customer_data:
            customer_sim_id = customer_save_data.customer_id
            new_customer_data = BusinessCustomerData(self._business_manager, customer_sim_id, from_load=True)
            new_customer_data.load_data(customer_save_data)
            self._customers[customer_sim_id] = new_customer_data

    def on_zone_load(self):
        if not self._business_manager.is_owner_household_active:
            self._customers.clear()

    def on_loading_screen_animation_finished(self):
        for customer_data in self._customers.values():
            customer_data.on_loading_screen_animation_finished()
