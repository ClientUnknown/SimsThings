from interactions.utils.loot_basic_op import BaseLootOperationimport servicesfrom sims4.tuning.tunable import Tunablefrom business.business_zone_director_mixin import BusinessZoneDirectorMixin
class ModifyCustomerFlow(BaseLootOperation):
    FACTORY_TUNABLES = {'allow_customers': Tunable(description='\n            If checked then set the current business, if there is one active,\n            to allow for customers to arrive.\n            \n            If unchecked then set the current business, if there is one active,\n            to disallow customers from arriving.\n            ', tunable_type=bool, default=True), 'locked_args': {'subject': None}}

    def __init__(self, *args, allow_customers=True, **kwargs):
        super().__init__(*args, **kwargs)
        self._allow_customers = allow_customers

    def _apply_to_subject_and_target(self, subject, target, resolver):
        business_manager = services.business_service().get_business_manager_for_zone()
        if business_manager is None:
            return
        zone_director = services.venue_service().get_zone_director()
        if zone_director is None:
            return
        if not isinstance(zone_director, BusinessZoneDirectorMixin):
            return
        zone_director.set_customers_allowed(self._allow_customers)
