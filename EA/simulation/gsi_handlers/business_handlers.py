from business.business_enums import BusinessType, BusinessEmployeeTypefrom gsi_handlers.gameplay_archiver import GameplayArchiverfrom sims4.gsi.dispatcher import GsiHandlerfrom sims4.gsi.schema import GsiGridSchema, GsiFieldVisualizersimport servicesbusiness_managers_schema = GsiGridSchema(label='Business Managers')business_managers_schema.add_field('household_id', label='Household Id', width=1, unique_field=True)business_managers_schema.add_field('household_name', label='Household Name')business_managers_schema.add_field('business_type', label='BusinessType', width=1.5)business_managers_schema.add_field('zone_id', label='ZoneID')business_managers_schema.add_field('is_open', label='Open', width=0.5)business_managers_schema.add_field('time_since_open', label='Time Since Open', width=0.5)business_managers_schema.add_field('star_rating_value', label='Star Value', type=GsiFieldVisualizers.FLOAT, width=0.5)business_managers_schema.add_field('star_rating', label='Star', type=GsiFieldVisualizers.INT, width=0.5)business_managers_schema.add_field('funds', label='Funds', type=GsiFieldVisualizers.FLOAT, width=0.5)business_managers_schema.add_field('daily_revenue', label='Daily Revenue', type=GsiFieldVisualizers.FLOAT, width=0.5)with business_managers_schema.add_has_many('other_data', GsiGridSchema) as sub_schema:
    sub_schema.add_field('key', label='Data Name', width=0.5)
    sub_schema.add_field('value', label='Data Value')with business_managers_schema.add_has_many('customer_data', GsiGridSchema) as sub_schema:
    sub_schema.add_field('sim_id', label='SimID', width=0.5)
    sub_schema.add_field('sim_name', label='SimName', width=0.5)
    sub_schema.add_field('star_rating_value', label='StarValue', type=GsiFieldVisualizers.FLOAT, width=0.5)
    sub_schema.add_field('star_rating', label='Stars', type=GsiFieldVisualizers.INT, width=0.5)
    sub_schema.add_field('buff_bucket_totals', label='Buff Bucket', width=2)with business_managers_schema.add_has_many('employee_data', GsiGridSchema) as sub_schema:
    sub_schema.add_field('employee_sim_id', label='SimID', width=0.6)
    sub_schema.add_field('employee_sim_name', label='SimName', width=0.5)
    sub_schema.add_field('employee_type', label='EmployeeType', width=1)
    sub_schema.add_field('career_level_buff', label='CareerBuff', width=0.5)
    sub_schema.add_field('daily_employee_wages', label='DailyWages', type=GsiFieldVisualizers.INT, width=0.5)
    sub_schema.add_field('clocked_in_time', label='ClockInTime', width=0.5)
    sub_schema.add_field('payroll_data', label='Payroll_data')
@GsiHandler('business_managers', business_managers_schema)
def generate_business_service_data(zone_id:int=None):
    business_service = services.business_service()
    business_manager_data = []
    sim_info_manager = services.sim_info_manager()

    def _construct_business_manager_gsi_data(zone_id, business_manager, business_tracker=None):
        household = business_tracker._get_owner_household() if business_tracker is not None else None
        business_manager_entry = {'household_id': str(household.id) if household is not None else 'N/A', 'household_name': household.name if household is not None and household.name else '<Unnamed Household>', 'business_type': str(BusinessType(business_manager.business_type)), 'zone_id': str(hex(zone_id)), 'is_open': 'x' if business_manager.is_open else '', 'time_since_open': str(business_manager.minutes_open), 'star_rating_value': business_manager._star_rating_value, 'star_rating': business_manager.get_star_rating(), 'funds': str(business_manager.funds.money), 'daily_revenue': business_manager._daily_revenue}
        other_data = []
        other_data.append({'key': 'daily_items_sold', 'value': str(business_manager._daily_items_sold)})
        other_data.append({'key': 'markup_multiplier', 'value': str(business_manager._markup_multiplier)})
        other_data.append({'key': 'advertising_type', 'value': business_manager.get_advertising_type_for_gsi()})
        other_data.append({'key': 'quality_setting', 'value': business_manager.quality_setting.name})
        other_data.append({'key': 'session_customers_served', 'value': str(business_manager._customer_manager.session_customers_served)})
        other_data.append({'key': 'lifetime_customers_served', 'value': str(business_manager._customer_manager.lifetime_customers_served)})
        other_data.append({'key': 'funds_category_tracker', 'value': str(business_manager._funds_category_tracker)})
        other_data.append({'key': 'buff_bucket_totals', 'value': str(business_manager._buff_bucket_totals)})
        other_data.append({'key': 'open_time', 'value': str(business_manager._open_time)})
        if business_tracker is not None:
            other_data.append({'key': 'additional_employee_slots (tracker data)', 'value': str(business_tracker._additional_employee_slots)})
            other_data.append({'key': 'additional_markup_multiplier(tracker data)', 'value': business_tracker.additional_markup_multiplier})
            other_data.append({'key': 'additional_customer_count(tracker data)', 'value': business_tracker.addtitional_customer_count})
        business_manager_entry['other_data'] = other_data
        employee_gsi_data = []
        employee_manager = business_manager._employee_manager
        for (sim_id, employee_data) in employee_manager._employees.items():
            (clock_in_time, payroll_data) = employee_manager._employee_payroll.get(sim_id, (None, None))
            sim_info = sim_info_manager.get(sim_id)
            entry = {'employee_sim_id': str(sim_id), 'employee_sim_name': str(sim_info), 'employee_type': str(BusinessEmployeeType(employee_data.employee_type)), 'daily_employee_wages': employee_manager._daily_employee_wages, 'clocked_in_time': str(clock_in_time), 'payroll_data': str(payroll_data)}
            buff_type = sim_info.get_buff_type(employee_data._career_level_buff_handle)
            entry['career_level_buff'] = str(buff_type.__name__) if buff_type is not None else ''
            employee_gsi_data.append(entry)
        business_manager_entry['employee_data'] = employee_gsi_data
        customer_data = []
        for (sim_id, business_customer_data) in business_manager._customer_manager._customers.items():
            entry = {'sim_id': str(sim_id), 'sim_name': str(sim_info_manager.get(sim_id)), 'star_rating_value': business_customer_data.get_star_rating_stat_value(), 'star_rating': business_customer_data.get_star_rating(), 'buff_bucket_totals': str(business_customer_data.buff_bucket_totals)}
            customer_data.append(entry)
        business_manager_entry['customer_data'] = customer_data
        return business_manager_entry

    zone_business_manager = services.business_service().get_business_manager_for_zone(zone_id)
    if zone_business_manager is not None and zone_business_manager.is_owned_by_npc:
        business_manager_data.append(_construct_business_manager_gsi_data(zone_id, zone_business_manager))
    for (_, business_trackers) in business_service._business_trackers.items():
        for business_tracker in business_trackers:
            for (zone_id, business_manager) in business_tracker.business_managers.items():
                business_manager_data.append(_construct_business_manager_gsi_data(zone_id, business_manager, business_tracker=business_tracker))
    return business_manager_data
business_archiver_schema = GsiGridSchema(label='Business Archive')business_archiver_schema.add_field('event_from', label='EventFrom', width=0.5)business_archiver_schema.add_field('sim_id', label='SimID', width=1)business_archiver_schema.add_field('sim_name', label='SimName', width=1)business_archiver_schema.add_field('event_description', label='Reason', width=2)business_archiver = GameplayArchiver('business_archiver', business_archiver_schema)
def archive_business_event(event_from, sim, event_description, sim_id=None):
    entry = {'event_from': event_from, 'sim_id': str(sim.id) if sim is not None else str(sim_id), 'sim_name': sim.full_name if sim is not None else '', 'event_description': event_description}
    business_archiver.archive(data=entry)
