from fire.flammability import ObjectFootprintFlammabilityfrom objects.game_object import GameObjectfrom sims4.tuning.instances import lock_instance_tunablesimport distributor.fieldsimport distributor.ops
class Rug(GameObject):
    INSTANCE_TUNABLES = {'flammable_area': ObjectFootprintFlammability.TunableFactory()}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._sort_order = 0

    @distributor.fields.Field(op=distributor.ops.SetSortOrder)
    def sort_order(self):
        return self._sort_order

    @sort_order.setter
    def sort_order(self, value):
        self._sort_order = value
lock_instance_tunables(Rug, provides_terrain_interactions=False)