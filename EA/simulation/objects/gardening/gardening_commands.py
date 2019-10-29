from objects.components import typesfrom objects.components.types import GARDENING_COMPONENTfrom objects.gardening.gardening_component_fruit import GardeningFruitComponentimport servicesimport sims4.commands
@sims4.commands.Command('gardening.cleanup_gardening_objects')
def cleanup_gardening_objects(_connection=None):
    for obj in services.object_manager().get_all_objects_with_component_gen(GARDENING_COMPONENT):
        gardening_component = obj.get_component(types.GARDENING_COMPONENT)
        if not isinstance(gardening_component, GardeningFruitComponent):
            pass
        elif obj.parent is None and not (obj.is_in_inventory() or obj.is_on_active_lot()):
            sims4.commands.output('Destroyed object {} on open street was found without a parent at position {}, parent_type {}.'.format(obj, obj.position, obj.parent_type), _connection)
            obj.destroy(source=obj, cause='Fruit/Flower with no parent on open street')
    sims4.commands.output('Gardening cleanup complete', _connection)
    return True
