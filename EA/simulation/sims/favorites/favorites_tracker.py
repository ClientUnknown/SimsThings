import servicesfrom distributor.rollback import ProtocolBufferRollbackfrom event_testing.test_events import TestEventfrom protocolbuffers import SimObjectAttributes_pb2from sims.sim_info_lod import SimInfoLODLevelfrom sims.sim_info_tracker import SimInfoTrackerimport sims4.logfrom sims4.utils import classpropertylogger = sims4.log.Logger('FavoritesTracker', default_owner='trevor')OBJ_ID = 0DEF_ID = 1
class FavoritesTracker(SimInfoTracker):

    def __init__(self, sim_info):
        self._owner = sim_info
        self._favorites = None

    @classproperty
    def _tracker_lod_threshold(cls):
        return SimInfoLODLevel.BASE

    @property
    def favorites(self):
        return self._favorites

    def has_favorite(self, tag):
        return self._favorites and tag in self._favorites

    def set_favorite(self, tag, obj_id=None, obj_def_id=None):
        if self._favorites is None:
            self._favorites = {}
            services.get_event_manager().register_single_event(self, TestEvent.ObjectDestroyed)
        if tag in self._favorites:
            logger.debug('Old favorite with object ID {} object definition ID {} is being overwritten by object ID {} object definition ID {} for tag {}.', self._favorites[tag][OBJ_ID], self._favorites[tag][DEF_ID], obj_id, obj_def_id, tag)
        if obj_def_id is None:
            obj = services.object_manager().get(obj_id)
            if obj is not None:
                obj_def_id = obj.definition.id
        self._favorites[tag] = (obj_id, obj_def_id)
        return True

    def unset_favorite(self, tag, obj_id=None, obj_def_id=None):
        (fav_obj_id, fav_def_id) = self.get_favorite(tag)
        del self._favorites[tag]
        if (fav_obj_id is not None and fav_obj_id == obj_id or fav_def_id is not None) and fav_def_id == obj_def_id and not self._favorites:
            self.clean_up()

    def clear_favorite_type(self, tag):
        del self._favorites[tag]
        if tag in self._favorites and not self._favorites:
            self.clean_up()

    def _unset_favorite_object(self, obj_id=None, obj_def_id=None):
        if self._favorites is None:
            return
        favorite_types = []
        for (favorite_type, fav) in self._favorites.items():
            if not fav[OBJ_ID] == obj_id:
                if fav[DEF_ID] is not None and fav[DEF_ID] == obj_def_id:
                    favorite_types.append(favorite_type)
            favorite_types.append(favorite_type)
        for favorite_type in favorite_types:
            self.unset_favorite(favorite_type, obj_id, obj_def_id)

    def get_favorite(self, tag):
        if self._favorites is None:
            return (None, None)
        return self._favorites.get(tag, (None, None))

    def get_favorite_object_id(self, tag):
        (fav_obj_id, _) = self.get_favorite(tag)
        return fav_obj_id

    def is_favorite(self, tag, obj):
        (fav_obj_id, fav_def_id) = self.get_favorite(tag)
        if fav_obj_id is not None and fav_obj_id == obj.id:
            return True
        elif fav_def_id is not None and fav_def_id == obj.definition.id:
            return True
        return False

    def get_favorite_definition_id(self, tag):
        (_, fav_def_id) = self.get_favorite(tag)
        return fav_def_id

    def clean_up(self):
        if self._favorites is not None:
            self._favorites = None
            services.get_event_manager().unregister_single_event(self, TestEvent.ObjectDestroyed)

    def handle_event(self, _, event, resolver):
        if event == TestEvent.ObjectDestroyed:
            destroyed_obj_id = resolver.get_resolved_arg('obj').id
            self._unset_favorite_object(destroyed_obj_id)

    def on_lod_update(self, old_lod, new_lod):
        if new_lod < self._tracker_lod_threshold:
            self.clean_up()
        elif old_lod < self._tracker_lod_threshold:
            msg = services.get_persistence_service().get_sim_proto_buff(self._owner.id)
            if msg is not None:
                self.load(msg.attributes.favorites_tracker)

    def save(self):
        data = SimObjectAttributes_pb2.PersistableFavoritesTracker()
        if self._favorites is None:
            return data
        for (tag, (object_id, object_def_id)) in self._favorites.items():
            with ProtocolBufferRollback(data.favorites) as entry:
                entry.favorite_type = tag
                if object_id is not None:
                    entry.favorite_id = object_id
                if object_def_id is not None:
                    entry.favorite_def_id = object_def_id
        return data

    def load(self, data):
        self.clean_up()
        for favorite in data.favorites:
            favorite_id = favorite.favorite_id
            if favorite_id is 0:
                favorite_id = None
            favorite_def_id = favorite.favorite_def_id
            if favorite_def_id is 0:
                favorite_def_id = None
            self.set_favorite(favorite.favorite_type, favorite_id, favorite_def_id)
