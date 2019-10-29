from _weakrefset import WeakSetimport servicesimport sims4.logimport sims4.reloadlogger = sims4.log.Logger('Pools', default_owner='bhill')with sims4.reload.protected(globals()):
    cached_pool_objects = WeakSet()POOL_LANDING_SURFACE = 'Water'
def get_main_pool_objects_gen():
    yield from cached_pool_objects

def get_pool_by_block_id(block_id):
    for pool in get_main_pool_objects_gen():
        if pool.block_id == block_id:
            return pool
    zone = services.current_zone()
    if zone is not None and not services.current_zone().is_in_build_buy:
        logger.error('No Pool Matching block Id: {}', block_id, owner='camilogarcia')
