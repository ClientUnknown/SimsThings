import randomfrom business.business_enums import BusinessTypefrom business.business_zone_director_mixin import BusinessZoneDirectorMixinfrom event_testing.resolver import SingleSimResolverfrom retail.retail_customer_situation import RetailCustomerSituationfrom retail.retail_employee_situation import RetailEmployeeSituationfrom retail.retail_manager import RetailManagerfrom sims4.math import MAX_FLOAT, almost_equalfrom sims4.random import weighted_random_itemfrom sims4.tuning.geometric import TunableCurvefrom sims4.tuning.tunable import TunableMapping, TunableTuple, TunableInterval, TunableList, Tunablefrom sims4.tuning.tunable_base import GroupNamesfrom venues.scheduling_zone_director import SchedulingZoneDirectorfrom zone_director import ZoneDirectorBaseimport servicesimport sims4.logSUPPORTED_BUSINESS_TYPES = (BusinessType.RETAIL,)logger = sims4.log.Logger('Retail', default_owner='trevor')
class RetailZoneDirector(BusinessZoneDirectorMixin, SchedulingZoneDirector):
    INSTANCE_TUNABLES = {'customer_count_curb_appeal_curve': TunableCurve(description='\n            The number of customers we want on the lot based on the curb appeal of\n            the lot. This only determines how many customers we want on the lot.\n            The type of customer is driven by the Customer Data Map and the average\n            value of sellable items on the lot.\n            ', x_axis_name='Curb Appeal', y_axis_name='Customer Count', tuning_group=GroupNames.BUSINESS), 'customer_situations': TunableMapping(description='\n            A mapping that defines which customer situations are spawned based\n            on certain properties of the retail lot.\n            ', key_name='Markup Multiplier', key_type=Tunable(description="\n                The store's price multiplier.\n                ", tunable_type=float, default=1), value_type=TunableList(description='\n                A list of tuple defining the customer data for this multiplier.\n                ', tunable=TunableTuple(required_median_value=TunableInterval(description='\n                        The median value of all items in the store must fall within\n                        this interval, which is inclusive.\n                        ', tunable_type=float, default_lower=0, default_upper=MAX_FLOAT, minimum=0), weighted_situations=TunableList(description='\n                        A list of situations that are available in the specified\n                        markup and price range combination. The situations are\n                        weighted relative to one another within this list.\n                        ', tunable=TunableTuple(situation=RetailCustomerSituation.TunableReference(description="\n                                The situation defining the customer's behavior.\n                                ", pack_safe=True), weight=Tunable(description="\n                                This situation's weight, relative to other\n                                situations in this list.\n                                ", tunable_type=float, default=1))))), tuning_group=GroupNames.BUSINESS), 'employee_situations': TunableList(description='\n            The list of possible employee situations. Right now, one will be\n            assigned at random when the employee comes to work.\n            ', tunable=RetailEmployeeSituation.TunableReference(), tuning_group=GroupNames.BUSINESS), 'npc_employee_situation': RetailEmployeeSituation.TunableReference(description='\n            The situation NPC employees will run.\n            ', tuning_group=GroupNames.BUSINESS)}
    CUSTOMER_SITUATION_LIST_GUID = 258695776
    EMPLOYEE_SITUATION_LIST_GUID = 2967593715

    def _should_create_npc_business_manager(self):
        return True

    def _get_new_npc_business_manager(self):
        npc_business_manager = RetailManager()
        npc_business_manager.set_zone_id(services.current_zone_id())
        npc_business_manager.set_owner_household_id(None)
        return npc_business_manager

    def _load_custom_zone_director(self, zone_director_proto, reader):
        for situation_data_proto in zone_director_proto.situations:
            if situation_data_proto.situation_list_guid == self.CUSTOMER_SITUATION_LIST_GUID:
                self._customer_situation_ids.extend(situation_data_proto.situation_ids)
            elif situation_data_proto.situation_list_guid == self.EMPLOYEE_SITUATION_LIST_GUID:
                self._employee_situation_id_list.extend(situation_data_proto.situation_ids)
        super()._load_custom_zone_director(zone_director_proto, reader)

    def _load_employee_situations(self, zone_director_proto, reader):
        pass

    def _save_custom_zone_director(self, zone_director_proto, writer):
        situation_data_proto = zone_director_proto.situations.add()
        situation_data_proto.situation_list_guid = self.CUSTOMER_SITUATION_LIST_GUID
        situation_data_proto.situation_ids.extend(self._customer_situation_ids)
        if not self.business_manager.is_owned_by_npc:
            situation_data_proto = zone_director_proto.situations.add()
            situation_data_proto.situation_list_guid = self.EMPLOYEE_SITUATION_LIST_GUID
            for situation_ids in self._employee_situation_ids.values():
                situation_data_proto.situation_ids.extend(situation_ids)
        super()._save_custom_zone_director(zone_director_proto, writer)

    def _save_employee_situations(self, zone_director_proto, writer):
        pass

    def _get_employee_situation_for_employee_type(self, employee_type):
        return random.choice(self.employee_situations)

    def _get_npc_employee_situation_for_employee_type(self, employee_type):
        return self.npc_employee_situation

    def create_situations_during_zone_spin_up(self):
        is_owned_business = self.business_manager is not None and self.business_manager.owner_household_id is not None
        if is_owned_business and (self.business_manager.is_owner_household_active or (services.current_zone().time_has_passed_in_world_since_zone_save() or services.current_zone().active_household_changed_between_save_and_load()) and self.business_manager.is_open):
            self._business_manager.start_already_opened_business()
        if is_owned_business:
            return
        super().create_situations_during_zone_spin_up()

    def _get_valid_customer_situations(self, business_manager):
        median_item_value = business_manager.get_median_item_value()
        markup_multiplier = business_manager.markup_multiplier
        for (customer_situation_markup_multiplier, customer_situation_datas) in self.customer_situations.items():
            if almost_equal(markup_multiplier, customer_situation_markup_multiplier):
                break
        return ()
        valid_situations = []
        resolver = SingleSimResolver(services.active_sim_info())
        for customer_situation_data in customer_situation_datas:
            if median_item_value in customer_situation_data.required_median_value:
                valid_situations.extend((pair.weight, pair.situation) for pair in customer_situation_data.weighted_situations if pair.situation.can_start_situation(resolver))
        return valid_situations

    def _on_customer_situation_request(self):
        self.remove_stale_customer_situations()
        desired_situation_count = self.customer_count_curb_appeal_curve.get(self._business_manager.get_curb_appeal())
        valid_weighted_situations = self._get_valid_customer_situations(self._business_manager)
        if not valid_weighted_situations:
            logger.warn('Tried finding a valid starting situation for customer but no situations matches were found.')
            return
        while desired_situation_count > len(self._customer_situation_ids):
            situation_to_start = weighted_random_item(valid_weighted_situations)
            if situation_to_start is None:
                break
            self.start_customer_situation(situation_to_start)

    @property
    def supported_business_types(self):
        return SUPPORTED_BUSINESS_TYPES
