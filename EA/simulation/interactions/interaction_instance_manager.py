from animation.animation_ac_cache import read_ac_cache_from_resourcefrom sims4.common import Packfrom sims4.tuning.instance_manager import InstanceManagerimport cachesimport servicesimport sims4.loglogger = sims4.log.Logger('InteractionManager', default_owner='manus')BUILD_AC_CACHE = FalsePACK_TO_BUILD_AC_CACHE = None
class InteractionInstanceManager(InstanceManager):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._ac_cache = {}
        self._pack_resources = None

    def purge_cache(self):
        self._ac_cache.clear()

    def on_start(self):
        super().on_start()
        if BUILD_AC_CACHE:
            self._build_animation_constraint_cache()
        else:
            self._use_animation_constraint_cache()

    def create_class_instances(self):
        super().create_class_instances()
        if BUILD_AC_CACHE:
            self._pack_resources = {}
            for (stripped_key, pack_specific_key) in self._remapped_keys.items():
                self._pack_resources[pack_specific_key] = stripped_key

    def get_base_game_keys(self):
        return [key for key in self.types.keys() if key not in self._pack_resources.values()]

    def _build_animation_constraint_cache(self):
        print('Building animation constraint cache for active pack {}'.format(PACK_TO_BUILD_AC_CACHE))
        if PACK_TO_BUILD_AC_CACHE == Pack.BASE_GAME:
            keys = self.types.keys()
        else:
            keys = [key for (key_group, key) in self._pack_resources.items() if key_group.group == PACK_TO_BUILD_AC_CACHE]
        print('Interactions being cached: {:5} / {:5}.'.format(len(keys), len(self.types)))
        for key in keys:
            cls = self.types[key]
            if cls._auto_constraints is not None:
                self._ac_cache[cls.__name__] = cls._auto_constraints
            else:
                self._ac_cache[cls.__name__] = {}

    def _use_animation_constraint_cache(self):
        logger.info('Using the animation constraint caches.')
        if self._ac_cache:
            logger.error('Animation Constraint Cache is already set up. Illegal request to re-populate the cache.')
            return
        self._ac_cache.update(read_ac_cache_from_resource())
        if not self._ac_cache:
            logger.warn('Animation Constraint Cache not built or obsolete.\n  Any interaction or animation element not exported via OE (export all via shoelacer is not sufficient) may result in missing auto-constraints.')
            return
        cache_enabled = caches.USE_ACC_AND_BCC & caches.AccBccUsage.ACC
        for cls in self.types.values():
            if not (cls._animation_constraint_dirty or cache_enabled):
                self._ac_cache[cls.__name__] = cls._auto_constraints
            cached_constraints = self._ac_cache.get(cls.__name__)
            if cls._auto_constraints is None and cached_constraints is not None:
                valid_constraints = {}
                for (key, constraint) in cached_constraints.items():
                    valid_constraints[key] = constraint.remove_constraints_with_unset_postures()
                cls._auto_constraints = valid_constraints

def get_animation_constraint_cache_debug_information():
    interaction_manager = services.get_instance_manager(sims4.resources.Types.INTERACTION)
    acc_size = len(interaction_manager._ac_cache) if interaction_manager is not None else 0
    return [('BUILD_AC_CACHE', str(BUILD_AC_CACHE), 'Whether we are currently building AC Cache'), ('AC_CACHE SIZE', acc_size, 'dict size of _ac_cache')]
