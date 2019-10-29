from objects.components import Componentfrom objects.components.types import SPAWN_POINT_COMPONENTfrom sims4.tuning.geometric import TunableVector3from sims4.tuning.tunable import HasTunableFactory, TunableList, TunableTuple, TunableSet, TunableEnumWithFilter, AutoFactoryInit, Tunable, TunableRange, TunableEnumEntryfrom world.dynamic_object_spawn_point import DynamicObjectSpawnPointfrom world.spawn_point_enums import SpawnPointPriorityimport servicesimport tag
class SpawnPointComponent(Component, HasTunableFactory, AutoFactoryInit, component_name=SPAWN_POINT_COMPONENT, allow_dynamic=True):
    FACTORY_TUNABLES = {'spawn_points': TunableList(description='\n        Spawn points that this object has.\n        ', tunable=TunableTuple(description='\n            Tuning for spawn point.\n            ', spawner_tags=TunableSet(description="\n                Tags for this spawn point. Sim spawn requests come with a tag.\n                If this spawn point matches a request's tag, then this spawn\n                point is a valid point for the Sim to be positioned at.\n                ", tunable=TunableEnumWithFilter(tunable_type=tag.Tag, filter_prefixes=tag.SPAWN_PREFIX, default=tag.Tag.INVALID, invalid_enums=(tag.Tag.INVALID,))), bone_name=Tunable(description='\n                The bone on the object to center the spawn point on.\n                ', tunable_type=str, default=''), bone_offset=TunableVector3(description='\n                The offset of the spawn field relative to the bone.\n                ', default=TunableVector3.DEFAULT_ZERO), rows=TunableRange(description='\n                The spawn point has multiple spawn slots arranged in a\n                rectangle. This controls how many rows of spawn slot there are.\n                The total number of Sims that can spawn simultaneously before\n                they start overlapping is number of rows * number of columns.\n                ', tunable_type=int, default=2, minimum=1), columns=TunableRange(description='\n                The spawn point has multiple spawn slots arranged in a\n                rectangle. This controls how many columns of spawn slot there\n                are. The total number of Sims that can spawn simultaneously\n                before they start overlapping is number of rows * number of\n                columns.\n                ', tunable_type=int, default=4, minimum=1), scale=TunableRange(description='\n                The distance between spawn slots.\n                ', tunable_type=float, default=1, minimum=0), priority=TunableEnumEntry(description='\n                The priority of the spawn point.\n                ', tunable_type=SpawnPointPriority, default=SpawnPointPriority.DEFAULT)))}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._spawn_points = set()

    def on_add(self):
        for point in self.spawn_points:
            self._add_spawn_point(point)

    def on_remove(self):
        for spawn_point in tuple(self._spawn_points):
            self._remove_spawn_point(spawn_point)

    def _add_spawn_point(self, point):
        spawn_point = DynamicObjectSpawnPoint(self.owner, point.spawner_tags, bone_name=point.bone_name, bone_offset=point.bone_offset, rows=point.rows, columns=point.columns, scale=point.scale, priority=point.priority)
        self._spawn_points.add(spawn_point)
        services.current_zone().add_dynamic_spawn_point(spawn_point)

    def _remove_spawn_point(self, spawn_point):
        if spawn_point in self._spawn_points:
            self._spawn_points.remove(spawn_point)
            services.current_zone().remove_dynamic_spawn_point(spawn_point)
