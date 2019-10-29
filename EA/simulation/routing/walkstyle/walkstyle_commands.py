from weakref import WeakKeyDictionaryfrom routing.walkstyle.walkstyle_request import WalkStyleRequestfrom server_commands.argument_helpers import OptionalTargetParam, get_optional_targetfrom sims4.math import MAX_INT32import sims4.commandsimport sims4.hash_utilimport sims4.resources_walk_style_requests = WeakKeyDictionary()
@sims4.commands.Command('walkstyle.request')
def set_walkstyle(walkstyle:str, opt_sim:OptionalTargetParam=None, _connection=None):
    sim = get_optional_target(opt_sim, _connection)
    if sim is None:
        return False
    walkstyle_request = _walk_style_requests.get(sim)
    if walkstyle_request is not None:
        walkstyle_request.stop()
    walkstyle = sims4.hash_util.hash32(walkstyle)
    walkstyle_request = WalkStyleRequest(sim, walkstyle=walkstyle, priority=MAX_INT32)
    walkstyle_request.start()
    _walk_style_requests[sim] = walkstyle_request
    return True

@sims4.commands.Command('walkstyle.clear')
def clear_walkstyle(opt_sim:OptionalTargetParam=None, _connection=None):
    sim = get_optional_target(opt_sim, _connection)
    walkstyle_request = _walk_style_requests.get(sim)
    if walkstyle_request is not None:
        walkstyle_request.stop()
        del _walk_style_requests[sim]

@sims4.commands.Command('walkstyle.list')
def list_walkstyles(_connection=None):
    sims4.commands.output('Available walkstyles:', _connection)
    for walkstyle in sims4.resources.list(type=sims4.resources.Types.WALKSTYLE):
        sims4.commands.output('    {}'.format(walkstyle), _connection)
    return True
