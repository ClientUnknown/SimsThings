from objects.object_enums import ResetReasonfrom server_commands.argument_helpers import get_optional_target, OptionalSimInfoParamfrom sims.aging.aging_tuning import AgingTuningfrom sims.sim_info_types import Ageimport servicesimport sims4.commands
@sims4.commands.Command('sims.age_add_progress')
def add_age_progress(amount_to_add:float=1.0, opt_sim:OptionalSimInfoParam=None, _connection=None):
    sim_info = get_optional_target(opt_sim, target_type=OptionalSimInfoParam, _connection=_connection)
    if sim_info is not None:
        sim_info.advance_age_progress(amount_to_add)
        return True
    return False

@sims4.commands.Command('sims.age_max_progress')
def age_max_progress(opt_sim:OptionalSimInfoParam=None, _connection=None):
    sim_info = get_optional_target(opt_sim, target_type=OptionalSimInfoParam, _connection=_connection)
    if sim_info is not None:
        sim_info.advance_age_progress(sim_info.time_until_age_up)
        return True
    return False

@sims4.commands.Command('sims.age_up', command_type=sims4.commands.CommandType.Automation)
def advance_to_next_age(opt_sim:OptionalSimInfoParam=None, _connection=None):
    sim_info = get_optional_target(opt_sim, target_type=OptionalSimInfoParam, _connection=_connection)
    if sim_info is not None:
        sim_info.callback_auto_age()
        return True
    return False

@sims4.commands.Command('sims.age_down', command_type=sims4.commands.CommandType.Automation)
def reverse_to_previous_age(opt_sim:OptionalSimInfoParam=None, _connection=None):
    sim_info = get_optional_target(opt_sim, target_type=OptionalSimInfoParam, _connection=_connection)
    if sim_info is not None:
        sim_info.reverse_age()
        sim_instance = sim_info.get_sim_instance()
        if sim_instance is not None:
            sim_instance.reset(reset_reason=ResetReason.RESET_EXPECTED)
        return True
    return False

@sims4.commands.Command('sims.phase_up')
def advance_to_next_phase(opt_sim:OptionalSimInfoParam=None, _connection=None):
    sim_info = get_optional_target(opt_sim, target_type=OptionalSimInfoParam, _connection=_connection)
    if sim_info is not None:
        sim_info.advance_age_phase()
        return True
    return False

@sims4.commands.Command('sims.request_age_progress_update', command_type=sims4.commands.CommandType.Live)
def request_age_progress_update(opt_sim:OptionalSimInfoParam=None, _connection=None):
    sim_info = get_optional_target(opt_sim, target_type=OptionalSimInfoParam, _connection=_connection)
    if sim_info is not None:
        sim_info.resend_age_progress_data()
        return True
    return False

@sims4.commands.Command('sims.set_age_speed_option', command_type=sims4.commands.CommandType.Live)
def set_age_speed_option(speed:int, _connection=None):
    if speed is None or speed < 0 or speed > 2:
        sims4.commands.output('Invalid speed setting, valid speeds are 0, 1, or 2.', _connection)
        return False
    sims4.commands.output('Speed setting changed to speed {}'.format(speed), _connection)
    services.get_aging_service().set_aging_speed(speed)

@sims4.commands.Command('sims.set_aging_enabled_option', command_type=sims4.commands.CommandType.Live)
def set_aging_enabled_option(enabled:int, _connection=None):
    sims4.commands.output('Auto aging for played household set to: {}'.format(enabled), _connection)
    services.get_aging_service().set_aging_enabled(enabled)

@sims4.commands.Command('sims.set_aging_unplayed_sims', command_type=sims4.commands.CommandType.Live)
def set_aging_unplayed_sims(enabled:bool, _connection=None):
    sims4.commands.output('Auto aging for unplayed household toggled to: {}'.format(enabled), _connection)
    services.get_aging_service().set_unplayed_aging_enabled(enabled)
