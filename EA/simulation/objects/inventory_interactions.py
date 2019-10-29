import objectsimport servicesimport sims4
@sims4.commands.Command('inventory.clone_obj_to_inv', command_type=sims4.commands.CommandType.Automation)
def clone_obj_to_inv(obj_id:int, inventory_owner_id:int, count:int=1, _connection=None):
    obj_to_create = services.object_manager().get(obj_id)
    target_object = services.object_manager().get(inventory_owner_id)
    if obj_to_create is None or target_object is None:
        sims4.commands.output('{} or {} not found in object manager'.format(obj_id, inventory_owner_id), _connection)
        return
    inventory = target_object.inventory_component
    if inventory is None:
        sims4.commands.output("{} doesn't have an inventory".format(str(target_object)), _connection)
        return
    for _ in range(count):
        obj_instance = objects.system.create_object(obj_to_create.definition)
        if obj_instance:
            inventory.player_try_add_object(obj_instance)
