import collectionsimport itertoolsimport sims4.reloadwith sims4.reload.protected(globals()):
    zone_id = None
    _zone_changed_callback = None
    zone_id_counter = itertools.count(1)
    zone_numbers = collections.defaultdict(lambda : next(zone_id_counter), {0: 0})
def set_current_zone_id(_zone_id):
    global zone_id
    zone_id = _zone_id
    if _zone_changed_callback is not None:
        _zone_changed_callback(zone_id)

def register_zone_change_callback(callback):
    global _zone_changed_callback
    _zone_changed_callback = callback
