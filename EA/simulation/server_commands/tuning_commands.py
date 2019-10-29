from collections import Counterimport osimport reimport timefrom sims4 import resourcesfrom sims4.resources import INSTANCE_TUNING_DEFINITIONSfrom sims4.tuning.merged_tuning_manager import get_managerimport date_and_timeimport pathsimport servicesimport sims4.commandsimport sims4.logimport sims4.tuning.merged_tuning_managerlogger = sims4.log.Logger('Tuning', default_owner='manus')
def get_managers():
    managers = {}
    for definition in INSTANCE_TUNING_DEFINITIONS:
        label = definition.TypeNames.lower()
        instance_type = definition.TYPE_ENUM_VALUE
        if instance_type == sims4.resources.Types.TUNING:
            label = 'module_tuning'
        managers[label] = services.get_instance_manager(instance_type)
    return managers

@sims4.commands.Command('tuning.import')
def tuning_import(instance_type=None, name=None, _connection=None):
    instance_manager = get_managers().get(instance_type, None)
    if instance_manager is None or name is None:
        sims4.commands.output('Usage: tuning.import instance_type instance_name', _connection)
    if instance_manager is None:
        sims4.commands.output('Valid instance types:', _connection)
        for name in sorted(get_managers()):
            sims4.commands.output('   {}'.format(name), _connection)
        return
    if name is None:
        sims4.commands.output('Valid {} instance names:'.format(instance_type), _connection)
        keys = resources.list(type=instance_manager.TYPE)
        names = [resources.get_name_from_key(key) for key in keys]
        names = [name.split('.')[0] for name in names]
        for name in sorted(names):
            sims4.commands.output('    {}'.format(name), _connection)
        return
    instance = instance_manager.get(name)
    sims4.commands.output(repr(instance), _connection)
    if hasattr(instance, 'debug_dump'):
        instance.debug_dump(dump=lambda s: sims4.commands.output(s, _connection))
    return True

@sims4.commands.Command('tuning.print_debug_statistics')
def print_debug_statistics(instance_type=None, _connection=None):
    instance_mgr = get_managers().get(instance_type)
    if instance_mgr is None:
        sims4.commands.output('Usage: tuning.print_debug_statistics instance_type', _connection)
        return
    for (name, value) in instance_mgr.get_debug_statistics():
        sims4.commands.output('{:30}{:20}'.format(name, value), _connection)

@sims4.commands.Command('tuning.reload')
def tuning_reload(_connection=None):
    if not paths.SUPPORT_RELOADING_RESOURCES:
        sims4.commands.output('Tuning reloading requires the --enable_tuning_reload flag.', _connection)
        return False
    if not paths.LOCAL_WORK_ENABLED:
        logger.warn("Attempting to reload tuning with 'ignore local work'. This is probably incorrect.")
    sims4.callback_utils.invoke_callbacks(sims4.callback_utils.CallbackEvent.TUNING_CODE_RELOAD)
    done = set()
    dependents = set()
    for manager in get_managers().values():
        for changed in manager.get_changed_files():
            done.add(changed)
            new_dependents = manager.reload_by_key(changed)
            if new_dependents is not None:
                dependents.update(new_dependents)
    dependents.difference_update(done)
    while dependents:
        next_dependent = dependents.pop()
        done.add(next_dependent)
        next_type = next_dependent.type
        manager = services.get_instance_manager(next_type)
        new_dependents = manager.reload_by_key(next_dependent)
        if new_dependents is not None:
            new_dependents.difference_update(done)
            dependents.update(new_dependents)
    sims4.commands.output('Reloading definitions tags: Begin.', _connection)
    services.definition_manager().refresh_build_buy_tag_cache()
    sims4.commands.output('Reloading definitions tags: End.', _connection)
    sims4.commands.output('Refreshing cached localwork.', _connection)
    sims4.resources.cache_localwork()
    sims4.commands.output('Reload done', _connection)
    return True

@sims4.commands.Command('tuning.localwork.refresh_cache')
def localwork_refresh_cache(_connection=None):
    sims4.resources.cache_localwork()

@sims4.commands.Command('tuning.localwork.analyze')
def localwork_analyze(_connection=None):
    output = sims4.commands.Output(_connection)
    output('localwork size: {}'.format(len(sims4.resources.localwork)))
    output('localwork_no_groupid size: {}'.format(len(sims4.resources.localwork_no_groupid)))

@sims4.commands.Command('tuning.resend_clock_tuning')
def tuning_resend_clock_tuning():
    date_and_time.send_clock_tuning()
    return True

@sims4.commands.Command('tuning.print_load_cache_info')
def show_load_cache_info(_connection=None):
    mtg = get_manager()
    ref_dict = mtg.index_ref_record
    c = Counter({k: len(v) for (k, v) in ref_dict.items()})
    if not c:
        return False
    output = sims4.commands.Output(_connection)
    output('Cache size: {}'.format(len(c)))
    output('Average cache size: {}'.format(sum(c.values())/len(c)))
    output('Most common keys:')
    for (key, count) in c.most_common(32):
        output('\t{}: {}'.format(key, count))
    return True
NAME_PATTERN = re.compile('.*\\((.*?)\\)')
@sims4.commands.Command('tuning.dump_load_cache')
def dump_load_cache(_connection=None):
    sims4.commands.output('Enable DEBUG_MERGED_TUNING_DATA to run this command', _connection)
    return False
