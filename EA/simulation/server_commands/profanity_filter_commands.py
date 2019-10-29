import collectionsimport itertoolsimport randomimport weakrefimport sims4.commandsimport sims4.zone_utilsimport _profanity_filter
@sims4.commands.Command('profanity_filter.check_text', command_type=sims4.commands.CommandType.Live)
def profanity_check_text(text_to_check, _connection=None):
    ret_tuple = _profanity_filter.check(text_to_check)
    sims4.commands.output('check_text for string {} found {} violations -- replacement string is {}'.format(text_to_check, ret_tuple[0], ret_tuple[1]), _connection)
    return ret_tuple

@sims4.commands.Command('profanity_filter.scan_text', command_type=sims4.commands.CommandType.Live)
def profanity_scan_text(text_to_check, _connection=None):
    num_violations = _profanity_filter.scan(text_to_check)
    sims4.commands.output('check_text for string {} found {} violations'.format(text_to_check, num_violations), _connection)
    return num_violations
