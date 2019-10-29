from _collections import defaultdictfrom sims4.service_manager import Serviceimport sims4.geometry
class GardeningService(Service):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._gardening_quadtrees = defaultdict(sims4.geometry.QuadTree)

    def add_gardening_object(self, obj):
        quadtree = self._gardening_quadtrees[obj.level]
        quadtree.insert(obj, obj.get_bounding_box())

    def get_gardening_objects(self, *, level, center, radius):
        if level not in self._gardening_quadtrees:
            return
        if isinstance(center, sims4.math.Vector3):
            center = sims4.math.Vector2(center.x, center.z)
        bounds = sims4.geometry.QtCircle(center, radius)
        quadtree = self._gardening_quadtrees[level]
        results = quadtree.query(bounds)
        return results

    def move_gardening_object(self, obj):
        for quadtree in self._gardening_quadtrees.values():
            quadtree.remove(obj)
        self.add_gardening_object(obj)

    def remove_gardening_object(self, obj):
        quadtree = self._gardening_quadtrees[obj.level]
        quadtree.remove(obj)
