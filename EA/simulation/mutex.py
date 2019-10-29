from collections import defaultdictimport element_utilsimport sims4.reloadwith sims4.reload.protected(globals()):
    mutex_data = defaultdict(list)
def with_mutex(key, sequence):

    def do_acquire(timeline):
        key_data = mutex_data[key]
        if key_data:
            waiting_element = element_utils.soft_sleep_forever()
            key_data.append(waiting_element)
            yield from element_utils.run_child(timeline, waiting_element)
        else:
            key_data.append(None)
        yield from element_utils.run_child(timeline, sequence)
        key_data = mutex_data[key]
        del key_data[0]
        if key_data:
            key_data[0].trigger_soft_stop()
        else:
            del mutex_data[key]
        return True

    return do_acquire
