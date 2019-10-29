import sims4.commandsimport sims4.common
@sims4.commands.Command('mtx.show_pack_entitlements')
def show_pack_entitlements(_connection=None):
    output = sims4.commands.Output(_connection)
    output('Available packs:')
    for pack in sims4.common.get_available_packs():
        output('    {}'.format(pack))
    return True
