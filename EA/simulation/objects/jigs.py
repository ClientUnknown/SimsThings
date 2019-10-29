import objects.game_objectimport objects.object_enumsimport objects.persistence_groupsimport sims4.tuning.instances
class Jig(objects.game_object.GameObject):

    @property
    def persistence_group(self):
        return objects.persistence_groups.PersistenceGroups.NONE

    def save_object(self, object_list, *args, item_location=objects.object_enums.ItemLocation.ON_LOT, container_id=0, **kwargs):
        pass

    @property
    def is_valid_posture_graph_object(self):
        return False
sims4.tuning.instances.lock_instance_tunables(Jig, _persistence=objects.object_enums.PersistenceType.NONE, _world_file_object_persists=False)