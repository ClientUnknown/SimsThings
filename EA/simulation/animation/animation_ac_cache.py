import picklefrom sims4.common import get_available_packs, Packimport sims4.logimport sims4.resourcesfrom singletons import DEFAULTlogger = sims4.log.Logger('ACCBCC', default_owner='manus')AC_CACHE_FILENAME = 'ac_pickle_cache'AC_CACHE_PY_UNOPT_FILENAME = 'ac_pickle_cache_py_unopt'AC_FILENAME_EXTENSION = '.ach'AC_BG_DELTA = '_bg_delta'AC_CACHE_VERSION = b'version#0004'_wrong_ac_cache_version = FalseTEST_LOCAL_CACHE = False
def read_ac_cache_from_resource(available_packs=DEFAULT):
    global _wrong_ac_cache_version
    if _wrong_ac_cache_version:
        return {}
    ac_cache_combined = {}
    if available_packs is DEFAULT:
        available_packs = get_available_packs()
    logger.info('Available packs: {}', available_packs)
    if TEST_LOCAL_CACHE:
        file_name = None
        file_name = 'C:\\tmp\\ac_bc_cache\\ac_pickle_cache'
        for pack in available_packs:
            pack_name = str(pack).replace('Pack.', '')
            pack_file = file_name + '_' + pack_name + AC_FILENAME_EXTENSION
            logger.always('Loading AC cache file {}.'.format(pack_file))
            with open(pack_file, 'rb') as ac_cache_file:
                resource_version = ac_cache_file.read(len(AC_CACHE_VERSION))
                ret = pickle.load(ac_cache_file)
                logger.always('Loaded AC cache with {} entries.', len(ret))
                ac_cache_combined.update(ret)
            if pack != Pack.BASE_GAME:
                try:
                    pack_file = file_name + '_' + pack_name + AC_BG_DELTA + AC_FILENAME_EXTENSION
                    logger.always('Loading AC cache file {}.'.format(pack_file))
                    with open(pack_file, 'rb') as ac_cache_file:
                        resource_version = ac_cache_file.read(len(AC_CACHE_VERSION))
                        _merge_cached_constraints(ac_cache_combined, ac_cache_file)
                except IOError:
                    logger.debug('No pack specific base game delta cache for pack:{}', pack)
        return ac_cache_combined
    key_name = None
    key_name = AC_CACHE_FILENAME
    for pack in available_packs:
        pack_name = str(pack).replace('Pack.', '')
        pack_key = key_name + '_' + pack_name
        key = sims4.resources.Key.hash64(pack_key, sims4.resources.Types.AC_CACHE)
        loader = sims4.resources.ResourceLoader(key)
        ac_cache_file = loader.load()
        logger.info('Loading AC cache {} (key: {}) as file {}.', pack_key, key, ac_cache_file)
        if not ac_cache_file:
            logger.debug('Failed to load animation constraint cache file from the resource loader (key = {})', pack_key)
        else:
            resource_version = ac_cache_file.read(len(AC_CACHE_VERSION))
            if resource_version != AC_CACHE_VERSION:
                _wrong_ac_cache_version = True
                logger.warn('The Animation Constraint cache in the resource manager is from a different version. Current version is {}, resource manager version is {}.\nStartup will be slower until the versions are aligned.', AC_CACHE_VERSION, resource_version)
                return {}
            try:
                ac_cache_combined.update(pickle.load(ac_cache_file))
            except pickle.UnpicklingError as exc:
                logger.exception('Unpickling the Animation Constraint cache failed. Startup will be slower as a consequence.', exc=exc)
                return {}
            if pack == Pack.BASE_GAME:
                pass
            else:
                delta_pack_key = pack_key + AC_BG_DELTA
                delta_key = sims4.resources.Key.hash64(delta_pack_key, sims4.resources.Types.AC_CACHE)
                loader = sims4.resources.ResourceLoader(delta_key)
                ac_delta_cache_file = loader.load()
                logger.info('Loading AC BG delta cache {} (key: {}) as file {}.', delta_pack_key, delta_key, ac_cache_file)
                if not ac_delta_cache_file:
                    logger.debug('Failed to load animation constraint cache file from the resource loader (key = {})', delta_pack_key)
                else:
                    resource_version = ac_delta_cache_file.read(len(AC_CACHE_VERSION))
                    if resource_version != AC_CACHE_VERSION:
                        _wrong_ac_cache_version = True
                        logger.warn('The Animation Constraint Delta cache in the resource manager is from a different version. Current version is {}, resource manager version is {}.\nStartup will be slower until the versions are aligned.', AC_CACHE_VERSION, resource_version)
                    else:
                        _merge_cached_constraints(ac_cache_combined, ac_delta_cache_file)
    return ac_cache_combined

def _merge_cached_constraints(ac_cache_combined, ac_delta_cache_file):
    try:
        pack_delta_ac_cache = pickle.load(ac_delta_cache_file)
        logger.always('Loaded AC BG Delta cache with {} entries.', len(pack_delta_ac_cache), color=50)
    except pickle.UnpicklingError as exc:
        logger.exception('Failed to unpickle delta cache: {}.  Pack specific constraints will not be applied.', ac_delta_cache_file, exc=exc)
        return
    for (interaction_name, cached_delta_constraint) in pack_delta_ac_cache.items():
        cached_constraint = ac_cache_combined.get(interaction_name, None)
        if cached_constraint is not None:
            for (participant, delta_constraint) in cached_delta_constraint.items():
                cached_constraint_for_participant = cached_constraint.get(participant, None)
                if cached_constraint_for_participant is not None:
                    cached_constraint_for_participant = delta_constraint.merge_delta_constraint(cached_constraint_for_participant)
                    cached_constraint[participant] = cached_constraint_for_participant
                else:
                    cached_constraint[participant] = delta_constraint
        else:
            logger.warn('Pack cache file did not ')
