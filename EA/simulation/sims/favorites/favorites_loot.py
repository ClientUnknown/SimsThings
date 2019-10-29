from interactions.utils.loot_basic_op import BaseTargetedLootOperationimport sims4.logfrom sims4.tuning.tunable import Tunablefrom tag import TunableTaglogger = sims4.log.Logger('FavoritesLoot', default_owner='trevor')
class SetFavoriteLootOp(BaseTargetedLootOperation):
    FACTORY_TUNABLES = {'favorite_type': TunableTag(description='\n            The tag that represents this type of favorite.\n            ', filter_prefixes=('Func',)), 'unset': Tunable(description='\n            If checked, this will unset the target as the favorite instead of setting\n            it.\n            ', tunable_type=bool, default=False)}

    def __init__(self, favorite_type, unset, **kwargs):
        super().__init__(**kwargs)
        self._favorite_type = favorite_type
        self._unset = unset

    def _apply_to_subject_and_target(self, subject, target, resolver):
        if subject is None or target is None:
            logger.error('Trying to run a SetFavorite loot without a valid Subject or Target')
            return
        if target.is_sim:
            logger.error("Trying to set a Sim {} as a Favorite of another Sim {}. This isn't possible.", target, subject)
            return
        favorites_tracker = subject.sim_info.favorites_tracker
        if favorites_tracker is None:
            logger.error('Trying to set a favorite for Sim {} but they have no favorites tracker.', subject)
            return
        if self._unset:
            favorites_tracker.unset_favorite(self._favorite_type, target.id, target.definition.id)
        else:
            favorites_tracker.set_favorite(self._favorite_type, target.id, target.definition.id)
