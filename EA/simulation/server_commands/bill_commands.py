from sims.bills_enums import AdditionalBillSourcefrom sims.household_utilities.utility_types import Utilitiesimport servicesimport sims4.commandsimport sims4.loglogger = sims4.log.Logger('Commands', default_owner='tastle')
@sims4.commands.Command('households.toggle_bill_notifications', 'households.toggle_bill_dialogs', 'bills.toggle_bill_notifications', command_type=sims4.commands.CommandType.Automation)
def toggle_bill_notifications(enable:bool=None, _connection=None):
    household = services.active_household()
    if household is None:
        sims4.commands.output('No active household.', _connection)
        return
    bills_manager = household.bills_manager
    enable_notifications = enable if enable is not None else not bills_manager.bill_notifications_enabled
    if enable_notifications:
        bills_manager.bill_notifications_enabled = True
        sims4.commands.output('Bill notifications for household {} enabled.'.format(household), _connection)
    else:
        bills_manager.bill_notifications_enabled = False
        sims4.commands.output('Bill notifications for household {} disabled.'.format(household), _connection)

@sims4.commands.Command('households.make_bill_source_delinquent', 'bills.make_bill_source_delinquent')
def make_bill_source_delinquent(additional_bill_source_name='Miscellaneous', _connection=None):
    try:
        additional_bill_source = AdditionalBillSource(additional_bill_source_name)
    except:
        sims4.commands.output('{0} is not a valid AdditionalBillSource.'.format(additional_bill_source_name), _connection)
        return False
    if additional_bill_source is None:
        sims4.commands.output('No additional bill source found.', _connection)
        return
    household = services.active_household()
    if household is None:
        sims4.commands.output('No active household.', _connection)
        return
    bills_manager = household.bills_manager
    bills_manager.add_additional_bill_cost(additional_bill_source, 1)
    make_bills_delinquent(_connection=_connection)

@sims4.commands.Command('households.make_bills_delinquent', 'bills.make_bills_delinquent')
def make_bills_delinquent(_connection=None):
    household = services.active_household()
    if household is None:
        sims4.commands.output('No active household.', _connection)
        return
    bills_manager = household.bills_manager
    if bills_manager.current_payment_owed is None:
        previous_send_notification = bills_manager.bill_notifications_enabled
        bills_manager.bill_notifications_enabled = False
        bills_manager.allow_bill_delivery()
        bills_manager.trigger_bill_notifications_from_delivery()
        for utility in Utilities:
            bills_manager._shut_off_utility(utility)
        bills_manager.bill_notifications_enabled = previous_send_notification

@sims4.commands.Command('households.pay_bills', 'bills.pay_bills')
def pay_bills(_connection=None):
    household = services.active_household()
    if household is None:
        sims4.commands.output('No active household.', _connection)
        return
    bills_manager = household.bills_manager
    bills_manager.pay_bill()

@sims4.commands.Command('households.force_bills_due', 'bills.force_bills_due', command_type=sims4.commands.CommandType.Automation)
def force_bills_due(_connection=None):
    household = services.active_household()
    if household is None:
        sims4.commands.output('No active household.', _connection)
        return
    bills_manager = household.bills_manager
    if bills_manager.current_payment_owed is None:
        previous_send_notification = bills_manager.bill_notifications_enabled
        bills_manager.bill_notifications_enabled = False
        bills_manager.allow_bill_delivery()
        bills_manager.trigger_bill_notifications_from_delivery()
        bills_manager.bill_notifications_enabled = previous_send_notification

@sims4.commands.Command('bills.put_bills_in_hidden_inventory')
def put_bills_in_hidden_inventory(_connection=None):
    household = services.active_household()
    if household is None:
        sims4.commands.output('No active household.', _connection)
        return
    bills_manager = household.bills_manager
    if bills_manager.current_payment_owed is None:
        bills_manager.allow_bill_delivery()

@sims4.commands.Command('households.autopay_bills', 'bills.autopay_bills', command_type=sims4.commands.CommandType.Cheat)
def autopay_bills(enable:bool=None, _connection=None):
    household = services.active_household()
    if household is None:
        sims4.commands.output('No active household.', _connection)
        return
    bills_manager = household.bills_manager
    autopay_bills = enable if enable is not None else not bills_manager.autopay_bills
    bills_manager.autopay_bills = autopay_bills
    sims4.commands.output('Autopay Bills for household {} set to {}.'.format(household, autopay_bills), _connection)
