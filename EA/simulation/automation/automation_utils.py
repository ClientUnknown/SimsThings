from sims4.commands import automation_outputimport servicesimport sims4.reloadwith sims4.reload.protected(globals()):
    dispatch_automation_events = False
def automation_event(message, **msg_data):
    if not dispatch_automation_events:
        return
    connection = services.client_manager().get_first_client_id()
    if msg_data:
        data_str = ['{}: {}'.format(k, v) for (k, v) in msg_data.items()]
        data_str = ', '.join(data_str)
        automation_output('{0}; {1}'.format(message, data_str), connection)
    else:
        automation_output('{0};'.format(message), connection)
