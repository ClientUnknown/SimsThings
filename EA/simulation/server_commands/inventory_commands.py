from collections import Counterfrom protocolbuffers import Consts_pb2from protocolbuffers import SimObjectAttributes_pb2from objects.components.inventory_enums import StackSchemefrom objects.system import create_objectfrom server_commands.argument_helpers import OptionalTargetParam, get_optional_target, RequiredTargetParam, TunableInstanceParamfrom sims4.commands import CommandTypeimport servicesimport sims4.commands
@sims4.commands.Command('inventory.create_in_hidden')
def create_object_in_hidden_inventory(definition_id:int, _connection=None):
    lot = services.active_lot()
    if lot is not None:
        return lot.create_object_in_hidden_inventory(definition_id) is not None
    return False

@sims4.commands.Command('inventory.list_hidden')
def list_objects_in_hidden_inventory(_connection=None):
    lot = services.active_lot()
    if lot is not None:
        hidden_inventory = lot.get_hidden_inventory()
        if hidden_inventory is not None:
            for obj in hidden_inventory:
                sims4.commands.output(str(obj), _connection)
            return True
    return False

@sims4.commands.Command('qa.objects.inventory.list', command_type=sims4.commands.CommandType.Automation)
def automation_list_active_situations(inventory_obj_id:int=None, _connection=None):
    manager = services.object_manager()
    if inventory_obj_id not in manager:
        sims4.commands.automation_output('ObjectInventory; Status:NoObject, ObjectId:{}'.format(inventory_obj_id), _connection)
        return
    inventory_obj = manager.get(inventory_obj_id)
    if inventory_obj.inventory_component != None:
        sims4.commands.automation_output('ObjectInventory; Status:Begin, ObjectId:{}'.format(inventory_obj_id), _connection)
        for obj in inventory_obj.inventory_component:
            sims4.commands.automation_output('ObjectInventory; Status:Data, Id:{}, DefId:{}'.format(obj.id, obj.definition.id), _connection)
        sims4.commands.automation_output('ObjectInventory; Status:End', _connection)
    else:
        sims4.commands.automation_output('ObjectInventory; Status:NoInventory, ObjectId:{}'.format(inventory_obj_id), _connection)

@sims4.commands.Command('inventory.purge', command_type=sims4.commands.CommandType.Cheat)
def purge_sim_inventory(opt_target:OptionalTargetParam=None, _connection=None):
    target = get_optional_target(opt_target, _connection)
    if target is not None:
        target.inventory_component.purge_inventory()
    return False

@sims4.commands.Command('inventory.purchase_picker_response', command_type=sims4.commands.CommandType.Live)
def purchase_picker_response(inventory_target:RequiredTargetParam, mailman_purchase:bool=False, *def_ids_and_amounts, _connection=None):
    total_price = 0
    current_purchased = 0
    objects_to_buy = []
    definition_manager = services.definition_manager()
    for (def_id, amount) in zip(def_ids_and_amounts[::2], def_ids_and_amounts[1::2]):
        definition = definition_manager.get(def_id)
        if definition is None:
            sims4.commands.output('inventory.purchase_picker_response: Definition not found with id {}'.format(def_id), _connection)
            return False
        purchase_price = definition.price*amount
        total_price += purchase_price
        objects_to_buy.append((definition, amount))
    client = services.client_manager().get(_connection)
    if client is None:
        sims4.commands.output('inventory.purchase_picker_response: No client found to make purchase.', _connection)
        return False
    household = client.household
    if household.funds.money < total_price:
        sims4.commands.output('inventory.purchase_picker_response: Insufficient funds for household to purchase items.', _connection)
        return False
    if mailman_purchase:
        inventory = services.active_lot().get_hidden_inventory()
    else:
        inventory_owner = inventory_target.get_target()
        inventory = inventory_owner.inventory_component
    if inventory is None:
        sims4.commands.output('inventory.purchase_picker_response: Inventory not found for items to be purchased into.', _connection)
        return False
    for (definition, amount) in objects_to_buy:
        obj = create_object(definition)
        if obj is None:
            sims4.commands.output('inventory.purchase_picker_response: Failed to create object with definition {}.'.format(definition), _connection)
        else:
            obj.set_stack_count(amount)
            if not inventory.player_try_add_object(obj):
                sims4.commands.output('inventory.purchase_picker_response: Failed to add object into inventory: {}'.format(obj), _connection)
                obj.destroy(source=inventory, cause='inventory.purchase_picker_response: Failed to add object into inventory.')
            else:
                obj.set_household_owner_id(household.id)
                obj.try_post_bb_fixup(force_fixup=True, active_household_id=services.active_household_id())
                purchase_price = definition.price*amount
                current_purchased += purchase_price
    return household.funds.try_remove(current_purchased, Consts_pb2.TELEMETRY_OBJECT_BUY)
USE_DEFINITION_PRICE = -1
@sims4.commands.Command('inventory.purchase_picker_response_by_ids', command_type=sims4.commands.CommandType.Live)
def purchase_picker_response_by_ids(inventory_target:RequiredTargetParam, inventory_source:RequiredTargetParam, mailman_purchase:bool=False, object_ids_or_definition_ids:bool=False, *ids_and_amounts_and_price, _connection=None):
    total_price = 0
    current_purchased = 0
    objects_to_buy = []
    definition_manager = services.definition_manager()
    inventory_manager = services.inventory_manager()
    for (def_or_obj_id, amount, price) in zip(ids_and_amounts_and_price[::3], ids_and_amounts_and_price[1::3], ids_and_amounts_and_price[2::3]):
        if object_ids_or_definition_ids:
            obj_or_definition = inventory_manager.get(def_or_obj_id)
        else:
            obj_or_definition = definition_manager.get(def_or_obj_id)
        if obj_or_definition is None:
            sims4.commands.output('inventory.purchase_picker_response: Object or Definition not found with id {}'.format(def_or_obj_id), _connection)
            return False
        if price == USE_DEFINITION_PRICE:
            price = obj_or_definition.definition.price
        purchase_price = price*amount
        total_price += purchase_price
        objects_to_buy.append((obj_or_definition, price, amount))
    client = services.client_manager().get(_connection)
    if client is None:
        sims4.commands.output('inventory.purchase_picker_response: No client found to make purchase.', _connection)
        return False
    household = client.household
    if household.funds.money < total_price:
        sims4.commands.output('inventory.purchase_picker_response: Insufficient funds for household to purchase items.', _connection)
        return False
    if mailman_purchase:
        to_inventory = services.active_lot().get_hidden_inventory()
    else:
        to_inventory_owner = inventory_target.get_target()
        to_inventory = to_inventory_owner.inventory_component
    if to_inventory is None:
        sims4.commands.output('inventory.purchase_picker_response: Inventory not found for items to be purchased into.', _connection)
        return False
    if inventory_source.target_id != 0:
        from_inventory_owner = inventory_source.get_target()
        from_inventory = from_inventory_owner.inventory_component
    else:
        from_inventory_owner = None
        from_inventory = None
    if object_ids_or_definition_ids and from_inventory is None:
        sims4.commands.output('inventory.purchase_picker_response: Source Inventory not found for items to be cloned from.', _connection)
        return False
    inventory_manager = services.inventory_manager()
    for (obj_or_def, price, amount) in objects_to_buy:
        amount_left = amount
        if object_ids_or_definition_ids:
            from_inventory.try_remove_object_by_id(obj_or_def.id, obj_or_def.stack_count())
            obj = obj_or_def.clone()
            from_inventory.system_add_object(obj_or_def)
        else:
            obj = create_object(obj_or_def)
            if obj is None:
                sims4.commands.output('inventory.purchase_picker_response: Failed to create object with definition {}.'.format(obj_or_def), _connection)
                amount_left = 0
            else:
                if obj.inventoryitem_component.stack_scheme == StackScheme.NONE:
                    amount_left = amount_left - 1
                else:
                    obj.set_stack_count(amount)
                    amount_left = 0
                obj.set_household_owner_id(household.id)
                if not to_inventory.player_try_add_object(obj):
                    sims4.commands.output('inventory.purchase_picker_response: Failed to add object into inventory: {}'.format(obj), _connection)
                    obj.destroy(source=to_inventory, cause='inventory.purchase_picker_response: Failed to add object into inventory.')
                else:
                    obj.try_post_bb_fixup(force_fixup=True, active_household_id=services.active_household_id())
                    purchase_price = price if obj.inventoryitem_component.stack_scheme == StackScheme.NONE else price*amount
                    current_purchased += purchase_price
        if obj.inventoryitem_component.stack_scheme == StackScheme.NONE:
            amount_left = amount_left - 1
        else:
            obj.set_stack_count(amount)
            amount_left = 0
        obj.set_household_owner_id(household.id)
        if not to_inventory.player_try_add_object(obj):
            sims4.commands.output('inventory.purchase_picker_response: Failed to add object into inventory: {}'.format(obj), _connection)
            obj.destroy(source=to_inventory, cause='inventory.purchase_picker_response: Failed to add object into inventory.')
        else:
            obj.try_post_bb_fixup(force_fixup=True, active_household_id=services.active_household_id())
            purchase_price = price if obj.inventoryitem_component.stack_scheme == StackScheme.NONE else price*amount
            current_purchased += purchase_price
    return household.funds.try_remove(current_purchased, Consts_pb2.TELEMETRY_OBJECT_BUY)

@sims4.commands.Command('inventory.open_ui', command_type=sims4.commands.CommandType.Live)
def open_inventory_ui(inventory_obj:RequiredTargetParam, _connection=None):
    obj = inventory_obj.get_target()
    if obj is None:
        sims4.commands.output('Failed to get inventory_obj: {}.'.format(inventory_obj), _connection)
        return False
    comp = obj.inventory_component
    if comp is None:
        sims4.commands.output('inventory_obj does not have an inventory component: {}.'.format(inventory_obj), _connection)
        return False
    comp.open_ui_panel()
    return True

@sims4.commands.Command('inventory.view_update', command_type=sims4.commands.CommandType.Live)
def inventory_view_update(obj_id:int=0, _connection=None):
    obj = services.current_zone().find_object(obj_id)
    if obj is not None:
        obj.inventory_view_update()
        return True
    return False

@sims4.commands.Command('inventory.sim_inventory_census.instanced_sims', command_type=CommandType.Automation)
def sim_inventory_census_instances_sims(_connection=None):
    output = sims4.commands.CheatOutput(_connection)
    for sim in services.sim_info_manager().instanced_sims_gen():
        inv_comp = sim.inventory_component
        output('{:50} Inventory: {:4} Shelved: {:4}'.format(inv_comp, len(inv_comp), inv_comp.get_shelved_object_count()))

@sims4.commands.Command('inventory.sim_inventory_census.save_slot', command_type=CommandType.Automation)
def sim_inventory_census_save_slot(_connection=None):
    output = sims4.commands.CheatOutput(_connection)
    definition_manager = services.definition_manager()
    active_household_id = services.active_household_id()
    total_objs = 0
    total_objs_active_house = 0
    total_objs_all_player_houses = 0
    counter = Counter()
    stack_counter = Counter()
    for sim_info in services.sim_info_manager().values():
        inventory_objs = len(sim_info.inventory_data.objects)
        for obj in sim_info.inventory_data.objects:
            obj_def = definition_manager.get(obj.guid)
            if obj_def is not None:
                counter[obj_def] += 1
            save_data = SimObjectAttributes_pb2.PersistenceMaster()
            save_data.ParseFromString(obj.attributes)
            for data in save_data.data:
                if data.type == SimObjectAttributes_pb2.PersistenceMaster.PersistableData.InventoryItemComponent:
                    comp_data = data.Extensions[SimObjectAttributes_pb2.PersistableInventoryItemComponent.persistable_data]
                    stack_counter[obj_def] += comp_data.stack_count
        total_objs += inventory_objs
        if sim_info.is_player_sim:
            total_objs_all_player_houses += inventory_objs
        if sim_info.household.id == active_household_id:
            total_objs_active_house += inventory_objs
    dump = []
    dump.append(('#inventory objs', total_objs))
    dump.append(('#inventory objs active house', total_objs_active_house))
    dump.append(('#inventory objs all player houses', total_objs_all_player_houses))
    for (name, value) in dump:
        output('{:50} : {}'.format(name, value))
    output('{}'.format('----------------------------------------------------------------------------------------------------'))
    output('{:75} : {} / {}'.format('Obj Definition', 'PlayerFacing', 'Stacks'))
    for (obj_def, count) in stack_counter.most_common():
        output('{:75} : {:4} / {:4}'.format(obj_def, count, counter.get(obj_def)))
    return dump

@sims4.commands.Command('inventory.create_and_add_object_to_inventory')
def create_and_add_object_to_inventory(to_inventory_object_id:RequiredTargetParam, definition_id:int, _connection=None):
    to_inventory_owner = to_inventory_object_id.get_target()
    to_inventory = to_inventory_owner.inventory_component
    if to_inventory is None:
        sims4.commands.output('to inventory object does not have an inventory component: {}'.format(to_inventory_owner), _connection)
        return False
    obj = create_object(definition_id)
    if not to_inventory.player_try_add_object(obj):
        sims4.commands.output('object failed to be placed into inventory: {}'.format(obj), _connection)
        obj.destroy(source=to_inventory, cause='object failed to be placed into inventory')
        return False
    sims4.commands.output('object {} placed into inventory'.format(obj), _connection)
    return True

@sims4.commands.Command('qa.object_def.valid_inventory_types', command_type=sims4.commands.CommandType.Automation)
def qa_object_def_valid_inventory_types(object_definition:TunableInstanceParam(sims4.resources.Types.OBJECT), _connection=None):
    sims4.commands.automation_output('QaObjDefValidInventoryTypes; Status:Begin', _connection)
    if object_definition is None:
        sims4.commands.automation_output('QaObjDefValidInventoryTypes; Status:End')
        return False
    if object_definition.cls._components.inventory_item is not None:
        valid_inventory_types = object_definition.cls._components.inventory_item._tuned_values.valid_inventory_types
        if valid_inventory_types is not None:
            for inventory_type in valid_inventory_types:
                sims4.commands.automation_output('QaObjDefValidInventoryTypes; Status:Data, InventoryType:{}'.format(inventory_type), _connection)
    sims4.commands.automation_output('QaObjDefValidInventoryTypes; Status:End', _connection)
