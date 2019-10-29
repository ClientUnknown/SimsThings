from protocolbuffers import Consts_pb2, InteractionOps_pb2, Business_pb2from business.business_enums import BusinessEmployeeType, BusinessType, BusinessAdvertisingType, BusinessQualityTypefrom business.business_manager import TELEMETRY_GROUP_BUSINESS, TELEMETRY_HOOK_NEW_GAME_BUSINESS_PURCHASED, TELEMETRY_HOOK_BUSINESS_TYPE, TELEMETRY_HOOK_BUSINESS_SOLDfrom distributor import shared_messagesfrom distributor.rollback import ProtocolBufferRollbackfrom distributor.shared_messages import create_icon_info_msg, IconInfoDatafrom distributor.system import Distributorfrom interactions.context import InteractionContextfrom interactions.priority import Priorityfrom retail.retail_balance_transfer_dialog import FundsTransferDialogfrom server_commands.argument_helpers import OptionalSimInfoParam, get_optional_target, RequiredTargetParam, TunableInstanceParamfrom sims4.commands import CommandTypeimport distributorimport servicesimport sims4.commandsimport sims4.logimport telemetry_helperlogger = sims4.log.Logger('Business', default_owner='trevor')business_telemetry_writer = sims4.telemetry.TelemetryWriter(TELEMETRY_GROUP_BUSINESS)
@sims4.commands.Command('business.set_open', command_type=CommandType.Live)
def set_open(is_open:bool, zone_id:int=None, _connection=None):
    business_manager = services.business_service().get_business_manager_for_zone(zone_id=zone_id)
    if business_manager is None:
        logger.error('Trying to open or close a business but there is no business in the provided zone, {}.', zone_id)
        return False
    business_manager.set_open(is_open)
    sims4.commands.automation_output('BusinessOpenResponse; Status:{0}'.format('Open' if business_manager.is_open else 'Closed'), _connection)

@sims4.commands.Command('business.set_customers_allowed', command_type=sims4.commands.CommandType.Automation)
def set_customers_allowed(customers_allowed:bool, zone_id:int=None, _connection=None):
    business_manager = services.business_service().get_business_manager_for_zone()
    if business_manager is None:
        logger.error('Trying to change customers allowed but there is no business in the zone, {}.', zone_id)
        return False
    venue_service = services.venue_service()
    if venue_service is None:
        return
    zone_director = venue_service.get_zone_director()
    if zone_director is None:
        return False
    zone_director.set_customers_allowed(customers_allowed)
    return True

@sims4.commands.Command('business.show_summary_dialog', command_type=CommandType.Live)
def show_summary_dialog(zone_id:int=None, _connection=None):
    business_manager = services.business_service().get_business_manager_for_zone(zone_id)
    if business_manager is None:
        return False
    business_manager.show_summary_dialog()
    return True

@sims4.commands.Command('business.show_balance_transfer_dialog', command_type=CommandType.Live)
def show_balance_transfer_dialog(_connection=None):
    FundsTransferDialog.show_dialog()

@sims4.commands.Command('business.set_star_rating_value', command_type=CommandType.Live)
def set_star_rating_value(rating_value:float, _connection=None):
    business_manager = services.business_service().get_business_manager_for_zone()
    if business_manager is None:
        return False
    business_manager.set_star_rating_value(rating_value)

@sims4.commands.Command('business.push_active_sim_to_buy_business', command_type=CommandType.Live)
def push_active_sim_to_buy_business(business_type:BusinessType, _connection=None):
    output = sims4.commands.Output(_connection)
    active_sim = services.get_active_sim()
    if active_sim is None:
        output('There is no active sim.')
        return False
    business_tuning = services.business_service().get_business_tuning_data_for_business_type(business_type)
    if business_tuning is None:
        output("Couldn't find tuning for business type: {}", business_type)
        return False
    context = InteractionContext(active_sim, InteractionContext.SOURCE_SCRIPT, Priority.High)
    if not active_sim.push_super_affordance(business_tuning.buy_business_lot_affordance, active_sim, context):
        output('Failed to push the buy affordance on the active sim.')
        return False
    with telemetry_helper.begin_hook(business_telemetry_writer, TELEMETRY_HOOK_NEW_GAME_BUSINESS_PURCHASED, household=active_sim.household) as hook:
        hook.write_enum(TELEMETRY_HOOK_BUSINESS_TYPE, business_type)
    return True

@sims4.commands.Command('business.show_employee_management_dialog', command_type=CommandType.Live)
def show_employee_management_dialog(opt_sim:OptionalSimInfoParam=None, _connection=None):
    sim_info = get_optional_target(opt_sim, target_type=OptionalSimInfoParam, _connection=_connection)
    if sim_info is None:
        return False
    business_services = services.business_service()
    business_manager = business_services.get_business_manager_for_zone()
    if business_manager is None:
        return False
    business_tracker = business_services.get_business_tracker_for_household(sim_info.household_id, business_manager.business_type)
    msg = Business_pb2.ManageEmployeesDialog()
    msg.hiring_sim_id = sim_info.sim_id

    def get_sim_filter_gsi_name():
        return 'Business Command: Get New Possible Employees'

    for (business_employee_type, business_employee_data) in business_manager.tuning_data.employee_data_map.items():
        with ProtocolBufferRollback(msg.jobs) as employee_job_msg:
            total_unlocked_slots = business_employee_data.employee_count_default + business_tracker.get_additional_employee_slots(business_employee_type)
            employee_job_msg.open_slots = total_unlocked_slots - business_manager.get_employee_count(business_employee_type)
            employee_job_msg.locked_slots = business_employee_data.employee_count_max - total_unlocked_slots
            employee_job_msg.job_type = int(business_employee_type)
            employee_job_msg.job_name = business_employee_data.job_name
            employee_job_msg.job_icon = create_icon_info_msg(IconInfoData(business_employee_data.job_icon))
            current_employees = business_manager.get_employees_by_type(business_employee_type)
            sim_info_manager = services.sim_info_manager()
            for employee_sim_id in current_employees:
                employee_sim_info = sim_info_manager.get(employee_sim_id)
                with ProtocolBufferRollback(employee_job_msg.employees) as employee_msg:
                    business_manager.populate_employee_msg(employee_sim_info, employee_msg, business_employee_type, business_employee_data)
            results = services.sim_filter_service().submit_matching_filter(number_of_sims_to_find=business_employee_data.potential_employee_pool_size, sim_filter=business_employee_data.potential_employee_pool_filter, requesting_sim_info=sim_info, allow_yielding=False, gsi_source_fn=get_sim_filter_gsi_name)
            for result in results:
                with ProtocolBufferRollback(employee_job_msg.available_sims) as employee_msg:
                    business_manager.populate_employee_msg(result.sim_info, employee_msg, business_employee_type, business_employee_data)
    op = shared_messages.create_message_op(msg, Consts_pb2.MSG_MANAGE_EMPLOYEES_DIALOG)
    Distributor.instance().add_op_with_no_owner(op)

@sims4.commands.Command('business.employee_hire', command_type=CommandType.Live)
def hire_business_employee(sim:RequiredTargetParam, employee_type:BusinessEmployeeType, _connection=None):
    business_manager = services.business_service().get_business_manager_for_zone()
    if business_manager is None:
        return False
    target_sim = sim.get_target(manager=services.sim_info_manager())
    if target_sim is None:
        return False
    return business_manager.run_hire_interaction(target_sim, employee_type)

@sims4.commands.Command('business.employee_fire', command_type=CommandType.Live)
def fire_business_employee(sim:RequiredTargetParam, _connection=None):
    business_manager = services.business_service().get_business_manager_for_zone()
    if business_manager is None:
        return False
    target_sim = sim.get_target(manager=services.sim_info_manager())
    if target_sim is None:
        return False
    return business_manager.run_fire_employee_interaction(target_sim)

@sims4.commands.Command('business.employee_promote', command_type=CommandType.Live)
def promote_business_employee(sim:RequiredTargetParam, _connection=None):
    business_manager = services.business_service().get_business_manager_for_zone()
    if business_manager is None:
        return False
    target_sim = sim.get_target(manager=services.sim_info_manager())
    if target_sim is None:
        return False
    return business_manager.run_promote_employee_interaction(target_sim)

@sims4.commands.Command('business.employee_demote', command_type=CommandType.Live)
def demote_business_employee(sim:RequiredTargetParam, _connection=None):
    business_manager = services.business_service().get_business_manager_for_zone()
    if business_manager is None:
        return False
    target_sim = sim.get_target(manager=services.sim_info_manager())
    if target_sim is None:
        return False
    return business_manager.run_demote_employee_interaction(target_sim)

@sims4.commands.Command('business.set_markup', command_type=CommandType.Live)
def set_markup_multiplier(markup_multiplier:float, _connection=None):
    business_manager = services.business_service().get_business_manager_for_zone()
    if business_manager is None:
        logger.error('Trying to set business markup when not in a business zone.', owner='camilogarcia')
        return
    business_manager.set_markup_multiplier(markup_multiplier)

@sims4.commands.Command('business.sell_lot', command_type=CommandType.Live)
def sell_lot(_connection=None):
    output = sims4.commands.Output(_connection)
    business_manager = services.business_service().get_business_manager_for_zone()
    if business_manager is None:
        output("Trying to sell a lot that isn't a business lot.")
        return False
    current_zone = services.current_zone()
    lot_value = current_zone.lot.furnished_lot_value
    sell_value = max(0.0, business_manager._funds.money + lot_value)
    dialog = business_manager.tuning_data.sell_store_dialog(current_zone)
    dialog.show_dialog(on_response=sell_lot_response, additional_tokens=(sell_value,))

@sims4.commands.Command('business.set_advertising', command_type=CommandType.Live)
def set_advertising_type(business_advertising_type_float:float, _connection=None, **kwargs):
    business_manager = services.business_service().get_business_manager_for_zone()
    if business_manager is None:
        logger.error('Trying to set business advertising type when not in a business zone.', owner='camilogarcia')
        return
    business_advertising_type = BusinessAdvertisingType(int(business_advertising_type_float))
    business_manager.set_advertising_type(business_advertising_type)

@sims4.commands.Command('business.set_quality', command_type=sims4.commands.CommandType.Live)
def set_quality(quality:BusinessQualityType, _connection=None):
    business_manager = services.business_service().get_business_manager_for_zone()
    if business_manager is None:
        sims4.commands.output('Trying to set the quality for a business but there was no valid business manager found for the current zone.')
        return False
    business_manager.set_quality_setting(quality)

@sims4.commands.Command('business.force_off_lot_update', command_type=CommandType.Live)
def force_off_lot_update(_connection=None):
    services.business_service()._off_lot_churn_callback(None)

@sims4.commands.Command('business.refresh_configuration', command_type=sims4.commands.CommandType.Live)
def refresh_configuration(_connection=None):
    business_manager = services.business_service().get_business_manager_for_zone()
    if business_manager is None:
        sims4.commands.output('Trying to refresh a business zone configuration but there was no valid business manager found for the current zone.')
        return
    venue_service = services.venue_service()
    if venue_service is None:
        return
    zone_director = venue_service.get_zone_director()
    if zone_director is not None:
        zone_director.refresh_configuration()

@sims4.commands.Command('business.request_customer_situation', 'qa.business.request_customer_situation', command_type=sims4.commands.CommandType.Automation)
def request_customer_situation(situation_type:TunableInstanceParam(sims4.resources.Types.SITUATION)=None, _connection=None):
    business_manager = services.business_service().get_business_manager_for_zone()
    if business_manager is None:
        sims4.commands.output('Trying to request a customer but there was no valid business manager found for the current zone.')
        return
    venue_service = services.venue_service()
    if venue_service is None:
        return
    zone_director = venue_service.get_zone_director()
    if zone_director is not None:
        zone_director.start_customer_situation(situation_type)

def sell_lot_response(dialog):
    if not dialog.accepted:
        return
    business_manager = services.business_service().get_business_manager_for_zone()
    current_zone = services.current_zone()
    lot = current_zone.lot
    lot_value = lot.furnished_lot_value
    business_manager.modify_funds(lot_value)
    business_manager.transfer_balance_to_household()
    services.get_zone_manager().clear_lot_ownership(current_zone.id)
    business_tracker = services.business_service().get_business_tracker_for_household(business_manager.owner_household_id, business_manager.business_type)
    if business_tracker is None:
        logger.warn('Business tracker is None for household {} for business type {}', business_manager.owner_household_id, business_manager.business_type)
        return
    business_tracker.remove_owner(current_zone.id)
    current_zone.disown_household_objects()
    with telemetry_helper.begin_hook(business_telemetry_writer, TELEMETRY_HOOK_BUSINESS_SOLD, household=services.household_manager().get(business_manager.owner_household_id)) as hook:
        hook.write_enum(TELEMETRY_HOOK_BUSINESS_TYPE, business_manager.business_type)
    msg = InteractionOps_pb2.SellRetailLot()
    msg.retail_zone_id = current_zone.id
    distributor.system.Distributor.instance().add_event(Consts_pb2.MSG_SELL_RETAIL_LOT, msg)

@sims4.commands.Command('business.get_hireable_employees', command_type=sims4.commands.CommandType.Automation)
def get_hireable_employees(employee_type:BusinessEmployeeType, _connection=None):
    automation_output = sims4.commands.AutomationOutput(_connection)
    automation_output('GetHireableEmployees; Status:Begin')
    business_services = services.business_service()
    business_manager = business_services.get_business_manager_for_zone()
    if business_manager is not None:
        employee_data = business_manager.tuning_data.employee_data_map.get(employee_type)
        if employee_data is not None:
            sim_info = services.active_sim_info()

            def get_sim_filter_gsi_name():
                return '[Automation] Business Command: Get New Possible Employees'

            results = services.sim_filter_service().submit_matching_filter(number_of_sims_to_find=employee_data.potential_employee_pool_size, sim_filter=employee_data.potential_employee_pool_filter, requesting_sim_info=sim_info, allow_yielding=False, gsi_source_fn=get_sim_filter_gsi_name)
            for result in results:
                automation_output('GetHireableEmployees; Status:Data, SimId:{}'.format(result.sim_info.id))
    automation_output('GetHireableEmployees; Status:End')
