from sims4.tuning.tunable import TunableThreshold, TunableList, TunableEnumEntry, Tunableimport servicesimport sims4.logimport taglogger = sims4.log.Logger('WaterTerrainObjects', default_owner='rmccord')
class WaterTerrainObjectCache:
    OBJECT_SQ_DISTANCE_THRESHOLD = TunableThreshold(description="\n        The distance threshold between the user's click on water and objects in\n        the world that have WATER_TERRAIN_TAGS. If the user picks water, we\n        find the nearest object in this distance threshold and generate a pie\n        menu.\n        ", value=Tunable(description='\n            The value of the threshold that the collection is compared\n            against.\n            ', tunable_type=float, default=100.0), default=sims4.math.Threshold(0.0, sims4.math.Operator.LESS_OR_EQUAL.function))
    WATER_TERRAIN_TAGS = TunableList(description="\n        The Tags on Object Definitions that mark objects for caching near the\n        water. Please make exclusive tags for this, as we don't want to include\n        objects that don't make sense.\n        ", tunable=TunableEnumEntry(description='\n            A tag that marks an object for caching near the water terrain.\n            ', tunable_type=tag.Tag, default=tag.Tag.INVALID))

    def __init__(self):
        self._object_cache = []

    def get_nearest_object(self, pick_pos, check_distance=True):
        nearby_objects = []
        for cache_obj in self:
            obj_pos = cache_obj.location.transform.translation
            dist_sq = (pick_pos - obj_pos).magnitude_2d_squared()
            nearby_objects.append((cache_obj, dist_sq))
        nearest_obj = None
        if nearby_objects:
            nearest = min(nearby_objects, key=lambda x: x[1])
            if WaterTerrainObjectCache.OBJECT_SQ_DISTANCE_THRESHOLD.compare(nearest[1]):
                nearest_obj = nearest[0]
        return nearest_obj

    def refresh(self):
        self.clear()
        for obj in services.object_manager().valid_objects():
            self.add_object(obj)

    def can_add_object(self, obj):
        if obj in self._object_cache:
            return False
        definition = obj.definition
        for tag in WaterTerrainObjectCache.WATER_TERRAIN_TAGS:
            if definition.has_build_buy_tag(tag):
                return True
        return False

    def add_object(self, obj):
        if self.can_add_object(obj):
            self._object_cache.append(obj)
            return True
        return False

    def __iter__(self):
        return self._object_cache.__iter__()

    def clear(self):
        self._object_cache = []
