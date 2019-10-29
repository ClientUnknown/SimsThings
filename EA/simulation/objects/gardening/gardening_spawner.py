from objects.components import types
class FruitSpawnerData(SpawnerTuning):
    INSTANCE_SUBCLASSES_ONLY = True

    class _SpawnerOption:
        spawn_type = SpawnerTuning.SLOT_SPAWNER
        slot_type = None
        state_mapping = None
        force_initialization_spawn = None

    def __init__(self, *, spawn_weight):
        spawner_option = self._SpawnerOption()
        spawner_option.slot_type = GardeningTuning.GARDENING_SLOT
        super().__init__(object_reference=(), spawn_weight=spawn_weight, spawn_chance=100, spawner_option=spawner_option, spawn_times=None)

    def set_fruit(self, fruit_definition):
        self.object_reference += (fruit_definition,)

    @flexmethod
    def create_spawned_object(cls, inst, mother, definition, loc_type=ItemLocation.ON_LOT):
        scale = GardeningTuning.SCALE_COMMODITY.default_value
        child = None
        try:
            child = create_object(definition, loc_type=loc_type)
            gardening_component = child.get_component(types.GARDENING_COMPONENT)
            if gardening_component.is_shoot or mother.has_state(GardeningTuning.QUALITY_STATE_VALUE):
                quality_state = mother.get_state(GardeningTuning.QUALITY_STATE_VALUE)
                child.set_state(quality_state.state, quality_state)
                scale *= GardeningTuning.SCALE_VARIANCE.random_float()
                child.set_stat_value(GardeningTuning.SCALE_COMMODITY, scale)
            mother.spawner_component._spawned_objects.add(child)
        except:
            logger.exception('Failed to spawn.')
            if child is not None:
                child.destroy(source=mother, cause='Exception spawning child fruit.')
                child = None
        return child

    @property
    def main_spawner(self):
        return self.object_reference[0]
