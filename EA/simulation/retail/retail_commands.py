from protocolbuffers import Consts_pb2, Dialog_pb2, UI_pb2, InteractionOps_pb2from business.business_enums import BusinessTypefrom distributor import shared_messagesfrom distributor.rollback import ProtocolBufferRollbackfrom distributor.system import Distributorfrom retail.retail_balance_transfer_dialog import FundsTransferDialogfrom retail.retail_customer_situation import RetailCustomerSituationfrom retail.retail_utils import RetailUtilsfrom server_commands.argument_helpers import OptionalSimInfoParam, get_optional_target, RequiredTargetParamfrom sims.funds import transfer_fundsfrom sims4.commands import CommandTypefrom sims4.common import Packimport distributorimport servicesimport sims4.commandslogger = sims4.log.Logger('Retail', default_owner='trevor')
@sims4.commands.Command('retail.get_retail_info')
def get_retail_info(_connection=None):
    output = sims4.commands.Output(_connection)
    business_manager = services.business_service().get_business_manager_for_zone()
    if business_manager is None:
        output("This doesn't appear to be a retail lot.")
        return False
    is_open = business_manager.is_open
    output('Funds: {}'.format(business_manager.funds.money))
    output('Curb Appeal: {}'.format(business_manager.get_curb_appeal()))
    output('Employee Count: {}'.format(business_manager.employee_count))
    output('Markup Multiplier: {}X'.format(business_manager.markup_multiplier))
    output('Median Item Price: {}'.format(business_manager.get_median_item_value()))
    output('The store is {}.'.format('OPEN' if is_open else 'CLOSED'))
    if is_open:
        output('Items Sold: {}'.format(business_manager.daily_items_sold))
        output('Gross Income: {}'.format(business_manager.funds))
    format_msg = '{sim:>24} {career_level:>32} {salary:>12} {desired_salary:>12}'
    output(format_msg.format(sim='Sim', career_level='Career Level', salary='Current Salary', desired_salary='Desired Salary'))
    for employee_sim in business_manager.get_employees_gen():
        career_level = business_manager.get_employee_career_level(employee_sim)
        desired_career_level = business_manager.RETAIL_CAREER.start_track.career_levels[business_manager.get_employee_desired_career_level(employee_sim)]
        output(format_msg.format(sim=employee_sim.full_name, career_level=str(career_level.__name__), salary=career_level.simoleons_per_hour, desired_salary=desired_career_level.simoleons_per_hour))
    return True

@sims4.commands.Command('retail.show_summary_dialog', command_type=CommandType.Live, pack=Pack.EP01)
def show_retail_summary_dialog(_connection=None):
    business_manager = services.business_service().get_business_manager_for_zone()
    if business_manager is None:
        return False
    business_manager.show_summary_dialog()
    return True

@sims4.commands.Command('retail.show_retail_dialog', command_type=CommandType.Live, pack=Pack.EP01)
def show_retail_dialog(opt_sim:OptionalSimInfoParam=None, _connection=None):
    sim_info = get_optional_target(opt_sim, target_type=OptionalSimInfoParam, _connection=_connection)
    if sim_info is None:
        return False
    business_manager = services.business_service().get_business_manager_for_zone()
    if business_manager is None or business_manager.business_type != BusinessType.RETAIL:
        return False
    msg = Dialog_pb2.RetailManageEmployeesDialog()
    msg.hiring_sim_id = sim_info.sim_id

    def populate_employee_msg(sim_info, employee_msg):
        employee_msg.sim_id = sim_info.sim_id
        for skill_type in business_manager.EMPLOYEE_SKILLS:
            with ProtocolBufferRollback(employee_msg.skill_data) as employee_skill_msg:
                employee_skill_msg.skill_id = skill_type.guid64
                employee_skill_msg.curr_points = int(sim_info.get_stat_value(skill_type))
        if business_manager.is_employee(sim_info):
            satisfaction_stat = sim_info.get_statistic(business_manager.EMPLOYEE_SATISFACTION_COMMODITY)
            statisfaction_state_index = satisfaction_stat.get_state_index()
            if statisfaction_state_index is not None:
                employee_msg.satisfaction_string = satisfaction_stat.states[statisfaction_state_index].buff.buff_type.buff_name(sim_info)
            career_level = business_manager.get_employee_career_level(sim_info)
            employee_msg.pay = career_level.simoleons_per_hour
            career = business_manager.get_employee_career(sim_info)
            employee_msg.current_career_level = career.level
            employee_msg.max_career_level = len(career.current_track_tuning.career_levels) - 1
        else:
            desired_level = business_manager.get_employee_desired_career_level(sim_info)
            career_level = business_manager.RETAIL_CAREER.start_track.career_levels[desired_level]
            employee_msg.pay = career_level.simoleons_per_hour
            employee_msg.current_career_level = desired_level
            employee_msg.max_career_level = len(business_manager.RETAIL_CAREER.start_track.career_levels) - 1

    for employee_sim_info in business_manager.get_employees_gen():
        with ProtocolBufferRollback(msg.employees) as employee_msg:
            populate_employee_msg(employee_sim_info, employee_msg)

    def get_sim_filter_gsi_name():
        return 'Retail Command: Create Employees for Hire'

    results = services.sim_filter_service().submit_matching_filter(number_of_sims_to_find=business_manager.EMPLOYEE_POOL_SIZE, sim_filter=business_manager.EMPLOYEE_POOL_FILTER, requesting_sim_info=sim_info, allow_yielding=False, gsi_source_fn=get_sim_filter_gsi_name)
    for result in results:
        with ProtocolBufferRollback(msg.available_sims) as employee_msg:
            populate_employee_msg(result.sim_info, employee_msg)
    op = shared_messages.create_message_op(msg, Consts_pb2.MSG_RETAIL_MANAGE_EMPLOYEES)
    Distributor.instance().add_op_with_no_owner(op)

@sims4.commands.Command('retail.employee_hire', command_type=CommandType.Live, pack=Pack.EP01)
def hire_retail_employee(sim:RequiredTargetParam, _connection=None):
    business_manager = services.business_service().get_business_manager_for_zone()
    if business_manager is None:
        return False
    target_sim = sim.get_target(manager=services.sim_info_manager())
    if target_sim is None:
        return False
    return business_manager.run_employee_interaction(business_manager.EMPLOYEE_INTERACTION_HIRE, target_sim)

@sims4.commands.Command('retail.employee_fire', command_type=CommandType.Live, pack=Pack.EP01)
def fire_retail_employee(sim:RequiredTargetParam, _connection=None):
    business_manager = services.business_service().get_business_manager_for_zone()
    if business_manager is None:
        return False
    target_sim = sim.get_target(manager=services.sim_info_manager())
    if target_sim is None:
        return False
    return business_manager.run_employee_interaction(business_manager.EMPLOYEE_INTERACTION_FIRE, target_sim)

@sims4.commands.Command('retail.employee_promote', command_type=CommandType.Live, pack=Pack.EP01)
def promote_retail_employee(sim:RequiredTargetParam, _connection=None):
    business_manager = services.business_service().get_business_manager_for_zone()
    if business_manager is None:
        return False
    target_sim = sim.get_target(manager=services.sim_info_manager())
    if target_sim is None:
        return False
    return business_manager.run_employee_interaction(business_manager.EMPLOYEE_INTERACTION_PROMOTE, target_sim)

@sims4.commands.Command('retail.employee_demote', command_type=CommandType.Live, pack=Pack.EP01)
def demote_retail_employee(sim:RequiredTargetParam, _connection=None):
    business_manager = services.business_service().get_business_manager_for_zone()
    if business_manager is None:
        return False
    target_sim = sim.get_target(manager=services.sim_info_manager())
    if target_sim is None:
        return False
    return business_manager.run_employee_interaction(business_manager.EMPLOYEE_INTERACTION_DEMOTE, target_sim)

@sims4.commands.Command('retail.add_funds')
def add_retail_funds(amount:int=1000, _connection=None):
    output = sims4.commands.Output(_connection)
    business_manager = services.business_service().get_business_manager_for_zone()
    if business_manager is None:
        output("This doesn't appear to be a retail lot.")
        return False
    business_manager.modify_funds(amount, from_item_sold=False)

@sims4.commands.Command('retail.sell_lot', command_type=CommandType.Live)
def sell_retail_lot(_connection=None):
    output = sims4.commands.Output(_connection)
    business_manager = services.business_service().get_business_manager_for_zone()
    if business_manager is None:
        output("Trying to sell a lot that isn't a retail lot.")
        return False
    current_zone = services.current_zone()
    lot_value = current_zone.lot.furnished_lot_value
    sell_value = max(0.0, business_manager._funds.money + lot_value)
    dialog = business_manager.SELL_STORE_DIALOG(current_zone)
    dialog.show_dialog(on_response=sell_retail_lot_response, additional_tokens=(sell_value,))

def sell_retail_lot_response(dialog):
    if not dialog.accepted:
        return
    business_service = services.business_service()
    business_manager = business_service.get_business_manager_for_zone()
    current_zone = services.current_zone()
    lot = current_zone.lot
    lot_value = lot.furnished_lot_value
    business_manager.modify_funds(lot_value)
    business_manager.transfer_balance_to_household()
    zone_id = current_zone.id
    services.get_zone_manager().clear_lot_ownership(zone_id)
    business_service.remove_owner(zone_id, household_id=business_manager.owner_household_id)
    msg = InteractionOps_pb2.SellRetailLot()
    msg.retail_zone_id = current_zone.id
    distributor.system.Distributor.instance().add_event(Consts_pb2.MSG_SELL_RETAIL_LOT, msg)

@sims4.commands.Command('retail.toggle_for_sale_vfx', command_type=CommandType.Live, pack=Pack.EP01)
def toggle_for_sale_vfx(_connection=None):
    business_manager = services.business_service().get_business_manager_for_zone()
    if business_manager is None:
        logger.error('Trying to toggle for sale VFX when not in a retail zone.', owner='tastle')
        return
    business_manager.toggle_for_sale_vfx()

@sims4.commands.Command('retail.show_balance_transfer_dialog', command_type=CommandType.Live, pack=Pack.EP01)
def show_retail_balance_transfer_dialog(_connection=None):
    FundsTransferDialog.show_dialog()

@sims4.commands.Command('retail.transfer_funds', command_type=CommandType.Live)
def transfer_retail_funds(amount:int, from_zone_id:int, to_zone_id:int, _connection=None):
    output = sims4.commands.Output(_connection)
    if amount < 1:
        output('You can only transfer positive, non-zero amounts.')
        return False
    from_business_manager = services.business_service().get_business_manager_for_zone(zone_id=from_zone_id)
    to_business_manager = services.business_service().get_business_manager_for_zone(zone_id=to_zone_id)
    if from_business_manager is None and to_business_manager is None:
        output('Invalid transfer request. Neither zone was a retail zone. At least one retail zone is required.')
        return False
    if from_business_manager is None:
        household = services.household_manager().get(to_business_manager.owner_household_id)
        transfer_funds(amount, from_funds=household.funds, to_funds=to_business_manager.funds)
    elif to_business_manager is None:
        household = services.household_manager().get(from_business_manager.owner_household_id)
        transfer_funds(amount, from_funds=from_business_manager.funds, to_funds=household.funds)
    else:
        transfer_funds(amount, from_funds=from_business_manager.funds, to_funds=to_business_manager.funds)
    if from_business_manager is not None:
        from_business_manager.send_business_funds_update()
    if to_business_manager is not None:
        to_business_manager.send_business_funds_update()
    return True

@sims4.commands.Command('retail.get_owned_lot_count_message', command_type=CommandType.Live, pack=Pack.EP01)
def get_owned_retail_lot_count_message(_connection=None):
    lot_count = 0
    active_household = services.active_household()
    if active_household is not None:
        retail_tracker = services.business_service().get_business_tracker_for_household(active_household.id, BusinessType.RETAIL)
        if retail_tracker is not None:
            lot_count = len(retail_tracker.business_managers)
    lot_count_msg = UI_pb2.OwnedRetailLotCountMessage()
    lot_count_msg.owned_lot_count = lot_count
    op = shared_messages.create_message_op(lot_count_msg, Consts_pb2.MSG_RETAIL_OWNED_LOT_COUNT)
    Distributor.instance().add_op_with_no_owner(op)

@sims4.commands.Command('retail.get_retail_objects', command_type=CommandType.Automation, pack=Pack.EP01)
def get_retail_objects(_connection=None):
    automation_output = sims4.commands.AutomationOutput(_connection)
    automation_output('GetRetailObjects; Status:Begin')
    for obj in RetailUtils.get_all_retail_objects():
        automation_output('GetRetailObjects; Status:Data, ObjId:{}'.format(obj.id))
    automation_output('GetRetailObjects; Status:End')

@sims4.commands.Command('retail.set_purchase_intents_to_almost_max', command_type=CommandType.Automation, pack=Pack.EP01)
def set_purchase_intents_to_almost_max(_connection=None):
    stat_type = RetailCustomerSituation.PURCHASE_INTENT_STATISTIC
    almost_max_value = stat_type.max_value - 1
    for sim in services.sim_info_manager().instanced_sims_gen():
        stat = sim.get_statistic(stat_type, add=False)
        if stat is not None and stat.get_value() < almost_max_value:
            stat.set_value(almost_max_value)
