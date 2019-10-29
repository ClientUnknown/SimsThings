import argparseimport sims4.log_Logger = sims4.log.Logger
class PerfLogger(sims4.log.Logger):

    def log(self, message, *args, level, owner=None, trigger_breakpoint=False):
        _Logger.always(self, message, *args, color=level, owner=owner, trigger_breakpoint=trigger_breakpoint)

    def debug(self, message, *args, owner=None, trigger_breakpoint=False):
        _Logger.always(self, message, *args, color=sims4.log.LEVEL_DEBUG, owner=owner, trigger_breakpoint=trigger_breakpoint)

    def info(self, message, *args, owner=None, trigger_breakpoint=False):
        _Logger.always(self, message, *args, color=sims4.log.LEVEL_INFO, owner=owner, trigger_breakpoint=trigger_breakpoint)

    def warn(self, message, *args, owner=None, trigger_breakpoint=False):
        _Logger.always(self, message, *args, color=sims4.log.LEVEL_WARN, owner=owner, trigger_breakpoint=trigger_breakpoint)

    def error(self, message, *args, owner=None, trigger_breakpoint=False):
        _Logger.always(self, message, *args, color=sims4.log.LEVEL_ERROR, owner=owner, trigger_breakpoint=trigger_breakpoint)

def has_profile_log_group_arg(group):
    parser = argparse.ArgumentParser()
    parser.add_argument('--profile-log-group', action='append')
    (args, unused_args) = parser.parse_known_args()
    return args.profile_log_group is not None and group in args.profile_log_group

def profile_logging_enabled(group):
    return has_profile_log_group_arg(group)

def get_logger(group, *, default_owner=None, key_words=None):
    if has_profile_log_group_arg(group):
        return PerfLogger(group, default_owner=default_owner, key_words=key_words)
    else:
        return sims4.log.Logger(group, default_owner=default_owner, key_words=key_words)
