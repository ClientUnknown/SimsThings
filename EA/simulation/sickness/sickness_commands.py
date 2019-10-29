from server_commands.argument_helpers import OptionalSimInfoParam, TunableInstanceParam, get_optional_targetimport servicesimport sims4
@sims4.commands.Command('sickness.make_sick', command_type=sims4.commands.CommandType.Automation)
def make_sick(opt_target:OptionalSimInfoParam=None, _connection=None):
    target = get_optional_target(opt_target, _connection, target_type=OptionalSimInfoParam)
    if target is None:
        return False
    services.get_sickness_service().make_sick(target)

@sims4.commands.Command('sickness.add', command_type=sims4.commands.CommandType.Automation)
def add_sickness(sickness_type:TunableInstanceParam(sims4.resources.Types.SICKNESS), opt_target:OptionalSimInfoParam=None, _connection=None):
    target = get_optional_target(opt_target, _connection, target_type=OptionalSimInfoParam)
    if target is None:
        return False
    services.get_sickness_service().make_sick(target, sickness=sickness_type)

@sims4.commands.Command('sickness.remove', command_type=sims4.commands.CommandType.Automation)
def remove_sickness(opt_target:OptionalSimInfoParam=None, _connection=None):
    target = get_optional_target(opt_target, _connection, target_type=OptionalSimInfoParam)
    if target is None:
        return False
    services.get_sickness_service().remove_sickness(target)

@sims4.commands.Command('sickness.distribute_sicknesses')
def distribute_sicknesses(_connection=None):
    services.get_sickness_service().trigger_sickness_distribution()

@sims4.commands.Command('sickness.update_diagnosis')
def update_diagnosis(opt_target:OptionalSimInfoParam=None, _connection=None):
    target = get_optional_target(opt_target, _connection, target_type=OptionalSimInfoParam)
    if target is None or not target.has_sickness_tracking():
        return False
    target.current_sickness.update_diagnosis(target)

@sims4.commands.Command('sickness.clear_diagnosis')
def clear_diagnosis(opt_target:OptionalSimInfoParam=None, _connection=None):
    target = get_optional_target(opt_target, _connection, target_type=OptionalSimInfoParam)
    if target is None or not target.has_sickness_tracking():
        return False
    target.sickness_tracker.clear_diagnosis_data()
