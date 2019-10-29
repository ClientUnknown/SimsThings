import build_buyimport servicesimport sims4.commands
@sims4.commands.Command('bb.getuserinbuildbuy')
def get_user_in_buildbuy(_connection=None):
    zone_id = services.current_zone_id()
    account_id = build_buy.get_user_in_build_buy(zone_id)
    sims4.commands.output('User in Build Buy: {0}'.format(account_id), _connection)

@sims4.commands.Command('bb.initforceexit')
def init_force_exit_buildbuy(_connection=None):
    zone_id = services.current_zone_id()
    sims4.commands.output('Starting Force User out of BB...', _connection)
    build_buy.init_build_buy_force_exit(zone_id)

@sims4.commands.Command('bb.forceexit')
def force_exit_buildbuy(_connection=None):
    zone_id = services.current_zone_id()
    sims4.commands.output('Forcing User out of BB...', _connection)
    build_buy.build_buy_force_exit(zone_id)

@sims4.commands.Command('qa.is_in_build_buy', command_type=sims4.commands.CommandType.Automation)
def qa_is_in_build_buy(_connection=None):
    sims4.commands.automation_output('BuildBuy; IsInBuildBuy:{}'.format(services.current_zone().is_in_build_buy), _connection)
