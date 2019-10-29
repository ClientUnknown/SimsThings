from _collections import defaultdictimport itertoolsimport refrom gsi_handlers.gameplay_archiver import GameplayArchiverfrom gsi_handlers.gsi_utils import parse_filter_to_listfrom objects.game_object import GameObjectfrom routing.portals.portal_tuning import PortalFlagsfrom server.live_drag_tuning import LiveDragPermissionfrom sims4.common import Pack, get_pack_enumfrom sims4.gsi.dispatcher import GsiHandler, add_cheat_schemafrom sims4.gsi.schema import GsiGridSchema, GSIGlobalCheatSchema, GsiFieldVisualizersimport build_buyimport gsi_handlers.gsi_utilsimport objects.components.typesimport servicesimport sims4import tagglobal_object_cheats_schema = GSIGlobalCheatSchema()global_object_cheats_schema.add_cheat('objects.clear_lot', label='Clear Lot')add_cheat_schema('global_object_cheats', global_object_cheats_schema)object_manager_schema = GsiGridSchema(label='Object Manager')object_manager_schema.add_field('mgr', label='Manager', width=1, hidden=True)object_manager_schema.add_field('objId', label='Object Id', width=3, unique_field=True)object_manager_schema.add_field('classStr', label='Class', width=3)object_manager_schema.add_field('definitionStr', label='Definition', width=3)object_manager_schema.add_field('modelStr', label='Model', width=3)object_manager_schema.add_field('locX', label='X', width=1)object_manager_schema.add_field('locY', label='Y', width=1)object_manager_schema.add_field('locZ', label='Z', width=1)object_manager_schema.add_field('on_active_lot', label='On Active Lot', width=1, hidden=True)object_manager_schema.add_field('current_value', label='Value', width=1)object_manager_schema.add_field('isSurface', label='Surface', width=1)object_manager_schema.add_field('parent', label='Parent', width=2)object_manager_schema.add_field('bb_parent', label='BB_Parent', width=2)object_manager_schema.add_field('lockouts', label='Lockouts', width=2)object_manager_schema.add_field('transient', label='Transient', width=1, hidden=True)object_manager_schema.add_field('is_interactable', label='Interactable', width=1, hidden=True)object_manager_schema.add_field('footprint', label='Footprint', width=1, hidden=True)object_manager_schema.add_field('inventory_owner_id', label='inventory owner id', width=2, hidden=True)object_manager_schema.add_filter('on_active_lot')object_manager_schema.add_filter('open_street')object_manager_schema.add_filter('inventory')object_manager_schema.add_filter('game_objects')object_manager_schema.add_filter('prototype_objects')object_manager_schema.add_filter('sim_objects')with object_manager_schema.add_view_cheat('objects.destroy', label='Delete') as cheat:
    cheat.add_token_param('objId')with object_manager_schema.add_view_cheat('objects.reset', label='Reset') as cheat:
    cheat.add_token_param('objId')with object_manager_schema.add_view_cheat('objects.focus_camera_on_object', label='Focus On Selected Object') as cheat:
    cheat.add_token_param('objId')with object_manager_schema.add_has_many('commodities', GsiGridSchema) as sub_schema:
    sub_schema.add_field('commodity', label='Commodity')
    sub_schema.add_field('value', label='value')
    sub_schema.add_field('convergence_value', label='convergence value')
    sub_schema.add_field('decay_rate', label='decay')
    sub_schema.add_field('change_rate', label='change rate')with object_manager_schema.add_has_many('postures', GsiGridSchema) as sub_schema:
    sub_schema.add_field('interactionName', label='Interaction Name')
    sub_schema.add_field('providedPosture', label='Provided Posture')with object_manager_schema.add_has_many('states', GsiGridSchema) as sub_schema:
    sub_schema.add_field('state_type', label='State')
    sub_schema.add_field('state_value', label='Value')with object_manager_schema.add_has_many('reservations', GsiGridSchema) as sub_schema:
    sub_schema.add_field('reservation_sim', label='Owner', width=1)
    sub_schema.add_field('reservation_target', label='Target', width=1)
    sub_schema.add_field('reservation_type', label='Type', width=1)
    sub_schema.add_field('reservation_interaction', label='Interaction', width=1)with object_manager_schema.add_has_many('parts', GsiGridSchema) as sub_schema:
    sub_schema.add_field('part_group_index', label='Part Group Index', width=0.5)
    sub_schema.add_field('part_suffix', label='Part Suffix', width=0.5)
    sub_schema.add_field('subroot_index', label='SubRoot', width=0.5)
    sub_schema.add_field('is_mirrored', label='Mirrored', width=0.5)with object_manager_schema.add_has_many('slots', GsiGridSchema) as sub_schema:
    sub_schema.add_field('slot', label='Slot')
    sub_schema.add_field('children', label='Children')with object_manager_schema.add_has_many('inventory', GsiGridSchema) as sub_schema:
    sub_schema.add_field('objId', label='Object Id', width=2, unique_field=True)
    sub_schema.add_field('classStr', label='Class', width=2)
    sub_schema.add_field('stack_count', label='Stack Count', width=1, type=GsiFieldVisualizers.INT)
    sub_schema.add_field('stack_sort_order', label='Stack Sort Order', width=1, type=GsiFieldVisualizers.INT)
    sub_schema.add_field('hidden', label='In Hidden', width=1)with object_manager_schema.add_has_many('additional_data', GsiGridSchema) as sub_schema:
    sub_schema.add_field('dataId', label='Data', unique_field=True)
    sub_schema.add_field('dataValue', label='Value')with object_manager_schema.add_has_many('object_relationships', GsiGridSchema) as sub_schema:
    sub_schema.add_field('relationshipNumber', label='Relationship Number', width=0.5)
    sub_schema.add_field('simValue', label='Sim', width=0.25, unique_field=True)
    sub_schema.add_field('relationshipValue', label='Relationship Value', width=0.25)
    sub_schema.add_field('relationshipStatInfo', label='Relationship Stat Info')with object_manager_schema.add_has_many('portal_lock', GsiGridSchema) as sub_schema:
    sub_schema.add_field('lock_type', label='Lock Type', width=0.5)
    sub_schema.add_field('lock_priority', label='Lock Priority', width=0.25)
    sub_schema.add_field('lock_side', label='Lock Side', width=0.25)
    sub_schema.add_field('should_persist', label='Should Persist', width=0.25)
    sub_schema.add_field('exceptions', label='Exceptions')with object_manager_schema.add_has_many('awareness', GsiGridSchema) as sub_schema:
    sub_schema.add_field('awareness_role', label='Role', width=0.25)
    sub_schema.add_field('awareness_channel', label='Channel', width=0.25)
    sub_schema.add_field('awareness_data', label='Data', width=2)with object_manager_schema.add_has_many('component', GsiGridSchema) as sub_schema:
    sub_schema.add_field('component_name', label='Name', width=0.25)with object_manager_schema.add_has_many('live_drag', GsiGridSchema) as sub_schema:
    sub_schema.add_field('live_drag_data_name', label='Data', unique_field=True)
    sub_schema.add_field('live_drag_data_value', label='Value')with object_manager_schema.add_has_many('ownership', GsiGridSchema) as sub_schema:
    sub_schema.add_field('ownership_household_owner', label='Household Owner')
    sub_schema.add_field('ownership_sim_owner', label='Sim Owner')
    sub_schema.add_field('ownership_crafter_sim', label='Crafter Sim')
    sub_schema.add_field('ownership_preference_sim', label='Preference Sims')with object_manager_schema.add_has_many('walkstyles', GsiGridSchema, label='Walkstyles') as sub_schema:
    sub_schema.add_field('walkstyle_priority', label='Priority', width=0.5)
    sub_schema.add_field('walkstyle_type', label='Style', width=0.75)
    sub_schema.add_field('walkstyle_short', label='Short Replacement', width=0.75)
    sub_schema.add_field('walkstyle_combo_replacement', label='Combo replacement', width=1)
    sub_schema.add_field('walkstyle_is_current', label='Is Current', width=0.25)
    sub_schema.add_field('walkstyle_is_default', label='Is Default', width=0.25)with object_manager_schema.add_has_many('portals', GsiGridSchema, label='Routable Portal Flags') as sub_schema:
    sub_schema.add_field('portal_flag', label='Flags')INFINITY_SYMBOL = '∞'
def _get_model_name(cur_obj):
    model_name = 'Unexpected Repr'
    model = getattr(cur_obj, 'model', None)
    if model is not None:
        split_model_name = re.split('[\\(\\)]', str(cur_obj.model))
        if len(split_model_name) > 1:
            model_name = split_model_name[1]
    return model_name

@GsiHandler('object_manager', object_manager_schema)
def generate_object_manager_data(*args, zone_id:int=None, filter=None, **kwargs):
    filter_list = parse_filter_to_list(filter)
    lockout_data = {}
    obj_preference_data = defaultdict(list)
    zone = services.get_zone(zone_id)
    sim_info_manager = services.sim_info_manager()
    for sim_info in list(sim_info_manager.objects):
        sim = sim_info.get_sim_instance()
        if sim is not None:
            for (obj, time) in sim.get_lockouts_gen():
                lockouts = lockout_data.setdefault(obj, [])
                lockouts.append((sim, time))
            for (_, obj_id) in sim.sim_info.autonomy_scoring_preferences.items():
                obj_preference_data[obj_id].append(sim.sim_info.id)
            for (_, obj_id) in sim.sim_info.autonomy_use_preferences.items():
                obj_preference_data[obj_id].append(sim.sim_info.id)
    all_object_data = []
    for cur_obj in list(itertools.chain(zone.object_manager.objects, zone.prop_manager.objects, zone.inventory_manager.objects)):
        class_str = gsi_handlers.gsi_utils.format_object_name(cur_obj)
        definition_str = str(cur_obj.definition.name)
        on_active_lot = cur_obj.is_on_active_lot() if hasattr(cur_obj, 'is_on_active_lot') else False
        if on_active_lot:
            if 'on_active_lot' in filter_list and on_active_lot:
                obj_loc = cur_obj.position
                model_name = _get_model_name(cur_obj)
                ret_dict = {'mgr': str(cur_obj.manager).replace('_manager', ''), 'objId': hex(cur_obj.id), 'classStr': class_str, 'definitionStr': definition_str, 'modelStr': model_name, 'locX': round(obj_loc.x, 3), 'locY': round(obj_loc.y, 3), 'locZ': round(obj_loc.z, 3), 'on_active_lot': str(on_active_lot), 'current_value': cur_obj.current_value, 'is_interactable': 'x' if getattr(cur_obj, 'interactable', False) else '', 'footprint': str(cur_obj.footprint_polygon) if getattr(cur_obj, 'footprint_polygon', None) else ''}
                ret_dict['additional_data'] = []
                if cur_obj.location is not None:
                    ret_dict['additional_data'].append({'dataId': 'Location', 'dataValue': str(cur_obj.location)})
                if cur_obj.visibility is not None:
                    ret_dict['additional_data'].append({'dataId': 'Visibility', 'dataValue': str(cur_obj.visibility.visibility)})
                    ret_dict['additional_data'].append({'dataId': 'Opacity', 'dataValue': str(cur_obj.opacity)})
                ret_dict['additional_data'].append({'dataId': 'Model State', 'dataValue': str(cur_obj.state_index)})
                if hasattr(cur_obj, 'commodity_flags'):
                    commodity_flags_by_name = sorted([str(commodity_flag.__name__) for commodity_flag in cur_obj.commodity_flags])
                else:
                    commodity_flags_by_name = []
                ret_dict['additional_data'].append({'dataId': 'Commodity Flags', 'dataValue': '\n'.join(commodity_flags_by_name)})
                parent = cur_obj.parent
                bb_parent = cur_obj.bb_parent
                if parent is not None:
                    ret_dict['parent'] = gsi_handlers.gsi_utils.format_object_name(parent)
                    ret_dict['additional_data'].append({'dataId': 'Parent Id', 'dataValue': hex(parent.id)})
                    ret_dict['additional_data'].append({'dataId': 'Parent Slot', 'dataValue': cur_obj.parent_slot.slot_name_or_hash})
                if bb_parent is not None:
                    ret_dict['bb_parent'] = gsi_handlers.gsi_utils.format_object_name(bb_parent)
                focus_component = cur_obj.focus_component
                if focus_component is not None:
                    ret_dict['additional_data'].append({'dataId': 'Focus Bone', 'dataValue': str(focus_component.get_focus_bone())})
                    ret_dict['additional_data'].append({'dataId': 'Focus Score', 'dataValue': str(focus_component.focus_score)})
                ret_dict['object_relationships'] = []
                if cur_obj.objectrelationship_component is not None:
                    sims_in_relationships = list(cur_obj.objectrelationship_component.relationships.keys())
                    if len(sims_in_relationships) == 0:
                        relationship_entry = {'relationshipNumber': "This object hasn't formed any relationships, but could if it wanted to.", 'simValue': '', 'relationshipValue': '', 'relationshipStatInfo': ''}
                        ret_dict['object_relationships'].append(relationship_entry)
                    for (sim_number, sim_id) in enumerate(sims_in_relationships):
                        sim = services.sim_info_manager().get(sim_id)
                        if sim is None:
                            sim_name = str(sim_id)
                        else:
                            sim_name = sim.full_name
                        relationship_number_value = str(sim_number + 1) + ' out of '
                        number_of_allowed_relationships = cur_obj.objectrelationship_component.get_number_of_allowed_relationships()
                        if number_of_allowed_relationships is None:
                            relationship_number_value += INFINITY_SYMBOL
                        else:
                            relationship_number_value += str(number_of_allowed_relationships)
                        relationship_value = cur_obj.objectrelationship_component.get_relationship_value(sim_id)
                        relationship_str = str(relationship_value)
                        relationship_info_str = 'Max: ' + str(cur_obj.objectrelationship_component.get_relationship_max_value())
                        relationship_info_str += ' Min: ' + str(cur_obj.objectrelationship_component.get_relationship_min_value())
                        relationship_info_str += ' Initial: ' + str(cur_obj.objectrelationship_component.get_relationship_initial_value())
                        relationship_entry = {'relationshipNumber': relationship_number_value, 'simValue': sim_name, 'relationshipValue': relationship_str, 'relationshipStatInfo': relationship_info_str}
                        ret_dict['object_relationships'].append(relationship_entry)
                else:
                    relationship_entry = {'relationshipNumber': 'This object has no capacity for love.', 'simValue': '', 'relationshipValue': '', 'relationshipStatInfo': ''}
                    ret_dict['object_relationships'].append(relationship_entry)
                ret_dict['isSurface'] = cur_obj.is_surface()
                if cur_obj in lockout_data:
                    lockouts = ('{} ({})'.format(*lockout) for lockout in lockouts)
                    ret_dict['lockouts'] = ', '.join(lockouts)
                ret_dict['states'] = []
                if cur_obj.state_component:
                    for (state_type, state_value) in cur_obj.state_component.items():
                        state_entry = {'state_type': str(state_type), 'state_value': str(state_value)}
                        ret_dict['states'].append(state_entry)
                if isinstance(cur_obj, GameObject):
                    users = 'None'
                    ret_dict['transient'] = cur_obj.transient
                    object_tags_by_name = [str(tag.Tag(object_tag)) if type(object_tag) is int else str(object_tag) for object_tag in cur_obj.get_tags()]
                    ret_dict['additional_data'].append({'dataId': 'Category Tags', 'dataValue': ', '.join(object_tags_by_name)})
                    if cur_obj.is_in_inventory():
                        if cur_obj.inventoryitem_component.last_inventory_owner is not None:
                            ret_dict['inventory_owner_id'] = hex(cur_obj.inventoryitem_component.last_inventory_owner.id)
                        ret_dict['additional_data'].append({'dataId': 'New In Inventory', 'dataValue': cur_obj.new_in_inventory})
                    ret_dict['commodities'] = []
                    for commodity in list(cur_obj.get_all_stats_gen()):
                        com_entry = {'commodity': type(commodity).__name__, 'value': commodity.get_value()}
                        if commodity.continuous:
                            com_entry['convergence_value'] = (commodity.convergence_value,)
                            com_entry['decay_rate'] = (commodity.base_decay_rate,)
                            com_entry['change_rate'] = (commodity.get_change_rate,)
                        ret_dict['commodities'].append(com_entry)
                    ret_dict['postures'] = []
                    for affordance in list(cur_obj.super_affordances()):
                        if affordance.provided_posture_type is not None:
                            posture_entry = {'interactionName': affordance.__name__, 'providedPosture': affordance.provided_posture_type.__name__}
                            ret_dict['postures'].append(posture_entry)
                    ret_dict['reservations'] = []
                    while True:
                        for reservation_target in itertools.chain((cur_obj,), cur_obj.parts if cur_obj.parts is not None else ()):
                            for reservation_handler in reservation_target.get_reservation_handlers():
                                reservation_entry = {'reservation_sim': str(reservation_handler.sim), 'reservation_target': str(reservation_handler.target), 'reservation_type': str(type(reservation_handler)), 'reservation_interaction': str(reservation_handler.reservation_interaction)}
                                ret_dict['reservations'].append(reservation_entry)
                    ret_dict['parts'] = []
                    if cur_obj.parts is not None:
                        for part in cur_obj.parts:
                            part_entry = {'part_group_index': part.part_group_index, 'part_suffix': part.part_suffix, 'subroot_index': part.subroot_index, 'is_mirrored': str(part.is_mirrored())}
                            ret_dict['parts'].append(part_entry)
                    ret_dict['slots'] = []
                    for runtime_slot in cur_obj.get_runtime_slots_gen():
                        slot_entry = {'slot': str(runtime_slot), 'children': ', '.join(gsi_handlers.gsi_utils.format_object_name(child) for child in runtime_slot.children)}
                        ret_dict['slots'].append(slot_entry)
                    ret_dict['inventory'] = []
                    inventory = cur_obj.inventory_component
                    if inventory is not None:
                        for obj in inventory:
                            inv_entry = {}
                            inv_entry['objId'] = hex(obj.id)
                            inv_entry['classStr'] = gsi_handlers.gsi_utils.format_object_name(obj)
                            inv_entry['stack_count'] = obj.stack_count()
                            inv_entry['stack_sort_order'] = obj.get_stack_sort_order(inspect_only=True)
                            inv_entry['hidden'] = inventory.is_object_hidden(obj)
                            ret_dict['inventory'].append(inv_entry)
                    ret_dict['portal_lock'] = []
                    portal_locking_component = cur_obj.portal_locking_component
                    if portal_locking_component is not None:
                        for lock_data in portal_locking_component.lock_datas.values():
                            inv_entry = {}
                            inv_entry['lock_type'] = str(lock_data.lock_type)
                            inv_entry['lock_priority'] = str(lock_data.lock_priority)
                            inv_entry['lock_side'] = str(lock_data.lock_sides)
                            inv_entry['should_persist'] = lock_data.should_persist
                            inv_entry['exceptions'] = lock_data.get_exception_data()
                            ret_dict['portal_lock'].append(inv_entry)
                    ret_dict['awareness'] = []
                    awareness_scores = cur_obj.awareness_scores
                    if awareness_scores is not None:
                        for (awareness_channel, awareness_score) in awareness_scores.items():
                            ret_dict['awareness'].append({'awareness_role': 'Provider', 'awareness_channel': str(awareness_channel), 'awareness_data': 'Score: {}'.format(awareness_score)})
                    if cur_obj.awareness_component is not None:
                        for (awareness_channel, awareness_options) in cur_obj.awareness_component.awareness_modifiers.items():
                            ret_dict['awareness'].append({'awareness_role': 'Recipient', 'awareness_channel': str(awareness_channel), 'awareness_data': 'Modifiers: {}'.format(', '.join(str(m) for m in awareness_options) if awareness_options else 'Default')})
                    ret_dict['component'] = []
                    for component in cur_obj.components:
                        if component is not None:
                            inv_entry = {}
                            inv_entry['component_name'] = component.__class__.__name__
                            ret_dict['component'].append(inv_entry)
                    if cur_obj.is_sim:
                        for component in cur_obj.sim_info.components:
                            if component is not None:
                                inv_entry = {}
                                inv_entry['component_name'] = component.__class__.__name__ + ' - SIM_INFO'
                                ret_dict['component'].append(inv_entry)
                    ret_dict['ownership'] = []
                    data = {}
                    household_name = 'None'
                    house_id = cur_obj.get_household_owner_id()
                    if house_id is not None:
                        household = services.household_manager().get(house_id)
                        if household is not None:
                            household_name = household.name
                            data['ownership_household_owner'] = str(house_id) + ', ' + household_name
                    sim_id = cur_obj.get_sim_owner_id()
                    if sim_id is not None:
                        sim_info = sim_info_manager.get(sim_id)
                        sim_name = sim_info.full_name
                        data['ownership_sim_owner'] = str(sim_id) + ', ' + sim_name
                    if cur_obj.has_component(objects.components.types.CRAFTING_COMPONENT):
                        crafting_process = cur_obj.get_crafting_process()
                        if crafting_process is not None:
                            crafter_sim_id = crafting_process.crafter_sim_id
                            if crafter_sim_id is not None:
                                crafter_sim_info = sim_info_manager.get(crafter_sim_id)
                                if crafter_sim_info is not None:
                                    crafter_sim_name = crafter_sim_info.full_name
                                    data['ownership_crafter_sim'] = str(crafter_sim_id) + ', ' + crafter_sim_name
                    if cur_obj.id in obj_preference_data:
                        is_head = True
                        preference_sims_list = obj_preference_data[cur_obj.id]
                        for sim_id in preference_sims_list:
                            sim_info = sim_info_manager.get(sim_id)
                            sim_name = sim_info.full_name
                            if is_head:
                                is_head = False
                                data['ownership_preference_sim'] = str(sim_id) + ', ' + sim_name
                                ret_dict['ownership'].append(data)
                            else:
                                ret_dict['ownership'].append({'ownership_preference_sim': str(sim_id) + ', ' + sim_name})
                    else:
                        ret_dict['ownership'].append(data)
                    ret_dict['live_drag'] = []
                    live_drag_component = cur_obj.live_drag_component
                    if live_drag_component is not None:
                        ret_dict['live_drag'].append({'live_drag_data_name': 'Can Live Drag', 'live_drag_data_value': live_drag_component.can_live_drag})
                        in_use_permission = live_drag_component.get_permission(LiveDragPermission.NOT_IN_USE)
                        if not in_use_permission:
                            in_use_by = 'Disallowed, In use by: {}'.format(users)
                        else:
                            in_use_by = 'Allowed, Not in use'
                        ret_dict['live_drag'].append({'live_drag_data_name': 'In Use Permission', 'live_drag_data_value': in_use_by})
                        household_permission = live_drag_component.get_permission(LiveDragPermission.HOUSEHOLD)
                        if household_permission:
                            owned_by = 'Allowed, Owned by: {}'.format(household_name)
                        else:
                            owned_by = 'Disallowed, Owned by: {}'.format(household_name)
                        ret_dict['live_drag'].append({'live_drag_data_name': 'Active Household Permission', 'live_drag_data_value': owned_by})
                        state_permission = live_drag_component.get_permission(LiveDragPermission.STATE)
                        if not state_permission:
                            states_disabling = 'Disallowed, Disabled by: {}'.format(gsi_handlers.gsi_utils.format_object_list_names(live_drag_component.get_state_op_owners()))
                        else:
                            states_disabling = 'Allowed'
                        ret_dict['live_drag'].append({'live_drag_data_name': 'State Permission', 'live_drag_data_value': states_disabling})
                    walkstyle_info = []
                    ret_dict['walkstyles'] = walkstyle_info
                    ret_dict['portals'] = []
                    routing_component = cur_obj.routing_component
                    if routing_component is not None:
                        walkstyle = cur_obj.get_walkstyle()
                        walkstyle_behavior = cur_obj.get_walkstyle_behavior()
                        walkstyle_list = cur_obj.get_walkstyle_list()
                        for walkstyle_request in cur_obj.get_walkstyle_requests():
                            combo_replacement_tuple = walkstyle_behavior.get_combo_replacement(walkstyle_request.walkstyle, walkstyle_list)
                            if combo_replacement_tuple is not None:
                                combo_replacement_str = '{}({})'.format(combo_replacement_tuple.result, ','.join(str(x) for x in combo_replacement_tuple.key_combo_list))
                                short_replacement_str = '{} (Combo: {})'.format(walkstyle_behavior.get_short_walkstyle(walkstyle_request.walkstyle, cur_obj), walkstyle_behavior.get_short_walkstyle(combo_replacement_tuple.result, cur_obj))
                            else:
                                combo_replacement_str = ''
                                short_replacement_str = '{}'.format(walkstyle_behavior.get_short_walkstyle(walkstyle_request.walkstyle, cur_obj))
                            walkstyle_entry = {'walkstyle_priority': '{} ({})'.format(str(walkstyle_request.priority), int(walkstyle_request.priority)), 'walkstyle_type': str(walkstyle_request.walkstyle), 'walkstyle_short': short_replacement_str, 'walkstyle_combo_replacement': combo_replacement_str, 'walkstyle_is_current': 'X' if sim is not None and walkstyle is walkstyle_request.walkstyle else '', 'walkstyle_is_default': 'X' if sim is not None and walkstyle_behavior.default_walkstyle is walkstyle_request.walkstyle else ''}
                            walkstyle_info.append(walkstyle_entry)
                        routing_context = routing_component.get_routing_context()
                        portal_key_mask = routing_context.get_portal_key_mask()
                        ret_dict['portals'] = [{'portal_flag': portal_flag.name} for portal_flag in PortalFlags if portal_flag & portal_key_mask]
                all_object_data.append(ret_dict)
        obj_loc = cur_obj.position
        model_name = _get_model_name(cur_obj)
        ret_dict = {'mgr': str(cur_obj.manager).replace('_manager', ''), 'objId': hex(cur_obj.id), 'classStr': class_str, 'definitionStr': definition_str, 'modelStr': model_name, 'locX': round(obj_loc.x, 3), 'locY': round(obj_loc.y, 3), 'locZ': round(obj_loc.z, 3), 'on_active_lot': str(on_active_lot), 'current_value': cur_obj.current_value, 'is_interactable': 'x' if (filter_list is None or 'sim_objects' in filter_list) and (cur_obj.is_sim or 'inventory' in filter_list) and (cur_obj.is_in_inventory() or 'prototype_objects' in filter_list) and (class_str == 'prototype' or 'game_objects' in filter_list) and (class_str != 'prototype' or 'open_street' in filter_list) and getattr(cur_obj, 'interactable', False) else '', 'footprint': str(cur_obj.footprint_polygon) if getattr(cur_obj, 'footprint_polygon', None) else ''}
        ret_dict['additional_data'] = []
        if cur_obj.location is not None:
            ret_dict['additional_data'].append({'dataId': 'Location', 'dataValue': str(cur_obj.location)})
        if cur_obj.visibility is not None:
            ret_dict['additional_data'].append({'dataId': 'Visibility', 'dataValue': str(cur_obj.visibility.visibility)})
            ret_dict['additional_data'].append({'dataId': 'Opacity', 'dataValue': str(cur_obj.opacity)})
        ret_dict['additional_data'].append({'dataId': 'Model State', 'dataValue': str(cur_obj.state_index)})
        if hasattr(cur_obj, 'commodity_flags'):
            commodity_flags_by_name = sorted([str(commodity_flag.__name__) for commodity_flag in cur_obj.commodity_flags])
        else:
            commodity_flags_by_name = []
        ret_dict['additional_data'].append({'dataId': 'Commodity Flags', 'dataValue': '\n'.join(commodity_flags_by_name)})
        parent = cur_obj.parent
        bb_parent = cur_obj.bb_parent
        if parent is not None:
            ret_dict['parent'] = gsi_handlers.gsi_utils.format_object_name(parent)
            ret_dict['additional_data'].append({'dataId': 'Parent Id', 'dataValue': hex(parent.id)})
            ret_dict['additional_data'].append({'dataId': 'Parent Slot', 'dataValue': cur_obj.parent_slot.slot_name_or_hash})
        if bb_parent is not None:
            ret_dict['bb_parent'] = gsi_handlers.gsi_utils.format_object_name(bb_parent)
        focus_component = cur_obj.focus_component
        if focus_component is not None:
            ret_dict['additional_data'].append({'dataId': 'Focus Bone', 'dataValue': str(focus_component.get_focus_bone())})
            ret_dict['additional_data'].append({'dataId': 'Focus Score', 'dataValue': str(focus_component.focus_score)})
        ret_dict['object_relationships'] = []
        if cur_obj.objectrelationship_component is not None:
            sims_in_relationships = list(cur_obj.objectrelationship_component.relationships.keys())
            if len(sims_in_relationships) == 0:
                relationship_entry = {'relationshipNumber': "This object hasn't formed any relationships, but could if it wanted to.", 'simValue': '', 'relationshipValue': '', 'relationshipStatInfo': ''}
                ret_dict['object_relationships'].append(relationship_entry)
            for (sim_number, sim_id) in enumerate(sims_in_relationships):
                sim = services.sim_info_manager().get(sim_id)
                if sim is None:
                    sim_name = str(sim_id)
                else:
                    sim_name = sim.full_name
                relationship_number_value = str(sim_number + 1) + ' out of '
                number_of_allowed_relationships = cur_obj.objectrelationship_component.get_number_of_allowed_relationships()
                if number_of_allowed_relationships is None:
                    relationship_number_value += INFINITY_SYMBOL
                else:
                    relationship_number_value += str(number_of_allowed_relationships)
                relationship_value = cur_obj.objectrelationship_component.get_relationship_value(sim_id)
                relationship_str = str(relationship_value)
                relationship_info_str = 'Max: ' + str(cur_obj.objectrelationship_component.get_relationship_max_value())
                relationship_info_str += ' Min: ' + str(cur_obj.objectrelationship_component.get_relationship_min_value())
                relationship_info_str += ' Initial: ' + str(cur_obj.objectrelationship_component.get_relationship_initial_value())
                relationship_entry = {'relationshipNumber': relationship_number_value, 'simValue': sim_name, 'relationshipValue': relationship_str, 'relationshipStatInfo': relationship_info_str}
                ret_dict['object_relationships'].append(relationship_entry)
        else:
            relationship_entry = {'relationshipNumber': 'This object has no capacity for love.', 'simValue': '', 'relationshipValue': '', 'relationshipStatInfo': ''}
            ret_dict['object_relationships'].append(relationship_entry)
        ret_dict['isSurface'] = cur_obj.is_surface()
        if cur_obj in lockout_data:
            lockouts = ('{} ({})'.format(*lockout) for lockout in lockouts)
            ret_dict['lockouts'] = ', '.join(lockouts)
        ret_dict['states'] = []
        if cur_obj.state_component:
            for (state_type, state_value) in cur_obj.state_component.items():
                state_entry = {'state_type': str(state_type), 'state_value': str(state_value)}
                ret_dict['states'].append(state_entry)
        if isinstance(cur_obj, GameObject):
            users = 'None'
            ret_dict['transient'] = cur_obj.transient
            object_tags_by_name = [str(tag.Tag(object_tag)) if type(object_tag) is int else str(object_tag) for object_tag in cur_obj.get_tags()]
            ret_dict['additional_data'].append({'dataId': 'Category Tags', 'dataValue': ', '.join(object_tags_by_name)})
            if cur_obj.is_in_inventory():
                if cur_obj.inventoryitem_component.last_inventory_owner is not None:
                    ret_dict['inventory_owner_id'] = hex(cur_obj.inventoryitem_component.last_inventory_owner.id)
                ret_dict['additional_data'].append({'dataId': 'New In Inventory', 'dataValue': cur_obj.new_in_inventory})
            ret_dict['commodities'] = []
            for commodity in list(cur_obj.get_all_stats_gen()):
                com_entry = {'commodity': type(commodity).__name__, 'value': commodity.get_value()}
                if commodity.continuous:
                    com_entry['convergence_value'] = (commodity.convergence_value,)
                    com_entry['decay_rate'] = (commodity.base_decay_rate,)
                    com_entry['change_rate'] = (commodity.get_change_rate,)
                ret_dict['commodities'].append(com_entry)
            ret_dict['postures'] = []
            for affordance in list(cur_obj.super_affordances()):
                if affordance.provided_posture_type is not None:
                    posture_entry = {'interactionName': affordance.__name__, 'providedPosture': affordance.provided_posture_type.__name__}
                    ret_dict['postures'].append(posture_entry)
            ret_dict['reservations'] = []
            while True:
                for reservation_target in itertools.chain((cur_obj,), cur_obj.parts if cur_obj.parts is not None else ()):
                    for reservation_handler in reservation_target.get_reservation_handlers():
                        reservation_entry = {'reservation_sim': str(reservation_handler.sim), 'reservation_target': str(reservation_handler.target), 'reservation_type': str(type(reservation_handler)), 'reservation_interaction': str(reservation_handler.reservation_interaction)}
                        ret_dict['reservations'].append(reservation_entry)
            ret_dict['parts'] = []
            if cur_obj.parts is not None:
                for part in cur_obj.parts:
                    part_entry = {'part_group_index': part.part_group_index, 'part_suffix': part.part_suffix, 'subroot_index': part.subroot_index, 'is_mirrored': str(part.is_mirrored())}
                    ret_dict['parts'].append(part_entry)
            ret_dict['slots'] = []
            for runtime_slot in cur_obj.get_runtime_slots_gen():
                slot_entry = {'slot': str(runtime_slot), 'children': ', '.join(gsi_handlers.gsi_utils.format_object_name(child) for child in runtime_slot.children)}
                ret_dict['slots'].append(slot_entry)
            ret_dict['inventory'] = []
            inventory = cur_obj.inventory_component
            if inventory is not None:
                for obj in inventory:
                    inv_entry = {}
                    inv_entry['objId'] = hex(obj.id)
                    inv_entry['classStr'] = gsi_handlers.gsi_utils.format_object_name(obj)
                    inv_entry['stack_count'] = obj.stack_count()
                    inv_entry['stack_sort_order'] = obj.get_stack_sort_order(inspect_only=True)
                    inv_entry['hidden'] = inventory.is_object_hidden(obj)
                    ret_dict['inventory'].append(inv_entry)
            ret_dict['portal_lock'] = []
            portal_locking_component = cur_obj.portal_locking_component
            if portal_locking_component is not None:
                for lock_data in portal_locking_component.lock_datas.values():
                    inv_entry = {}
                    inv_entry['lock_type'] = str(lock_data.lock_type)
                    inv_entry['lock_priority'] = str(lock_data.lock_priority)
                    inv_entry['lock_side'] = str(lock_data.lock_sides)
                    inv_entry['should_persist'] = lock_data.should_persist
                    inv_entry['exceptions'] = lock_data.get_exception_data()
                    ret_dict['portal_lock'].append(inv_entry)
            ret_dict['awareness'] = []
            awareness_scores = cur_obj.awareness_scores
            if awareness_scores is not None:
                for (awareness_channel, awareness_score) in awareness_scores.items():
                    ret_dict['awareness'].append({'awareness_role': 'Provider', 'awareness_channel': str(awareness_channel), 'awareness_data': 'Score: {}'.format(awareness_score)})
            if cur_obj.awareness_component is not None:
                for (awareness_channel, awareness_options) in cur_obj.awareness_component.awareness_modifiers.items():
                    ret_dict['awareness'].append({'awareness_role': 'Recipient', 'awareness_channel': str(awareness_channel), 'awareness_data': 'Modifiers: {}'.format(', '.join(str(m) for m in awareness_options) if awareness_options else 'Default')})
            ret_dict['component'] = []
            for component in cur_obj.components:
                if component is not None:
                    inv_entry = {}
                    inv_entry['component_name'] = component.__class__.__name__
                    ret_dict['component'].append(inv_entry)
            if cur_obj.is_sim:
                for component in cur_obj.sim_info.components:
                    if component is not None:
                        inv_entry = {}
                        inv_entry['component_name'] = component.__class__.__name__ + ' - SIM_INFO'
                        ret_dict['component'].append(inv_entry)
            ret_dict['ownership'] = []
            data = {}
            household_name = 'None'
            house_id = cur_obj.get_household_owner_id()
            if house_id is not None:
                household = services.household_manager().get(house_id)
                if household is not None:
                    household_name = household.name
                    data['ownership_household_owner'] = str(house_id) + ', ' + household_name
            sim_id = cur_obj.get_sim_owner_id()
            if sim_id is not None:
                sim_info = sim_info_manager.get(sim_id)
                sim_name = sim_info.full_name
                data['ownership_sim_owner'] = str(sim_id) + ', ' + sim_name
            if cur_obj.has_component(objects.components.types.CRAFTING_COMPONENT):
                crafting_process = cur_obj.get_crafting_process()
                if crafting_process is not None:
                    crafter_sim_id = crafting_process.crafter_sim_id
                    if crafter_sim_id is not None:
                        crafter_sim_info = sim_info_manager.get(crafter_sim_id)
                        if crafter_sim_info is not None:
                            crafter_sim_name = crafter_sim_info.full_name
                            data['ownership_crafter_sim'] = str(crafter_sim_id) + ', ' + crafter_sim_name
            if cur_obj.id in obj_preference_data:
                is_head = True
                preference_sims_list = obj_preference_data[cur_obj.id]
                for sim_id in preference_sims_list:
                    sim_info = sim_info_manager.get(sim_id)
                    sim_name = sim_info.full_name
                    if is_head:
                        is_head = False
                        data['ownership_preference_sim'] = str(sim_id) + ', ' + sim_name
                        ret_dict['ownership'].append(data)
                    else:
                        ret_dict['ownership'].append({'ownership_preference_sim': str(sim_id) + ', ' + sim_name})
            else:
                ret_dict['ownership'].append(data)
            ret_dict['live_drag'] = []
            live_drag_component = cur_obj.live_drag_component
            if live_drag_component is not None:
                ret_dict['live_drag'].append({'live_drag_data_name': 'Can Live Drag', 'live_drag_data_value': live_drag_component.can_live_drag})
                in_use_permission = live_drag_component.get_permission(LiveDragPermission.NOT_IN_USE)
                if not in_use_permission:
                    in_use_by = 'Disallowed, In use by: {}'.format(users)
                else:
                    in_use_by = 'Allowed, Not in use'
                ret_dict['live_drag'].append({'live_drag_data_name': 'In Use Permission', 'live_drag_data_value': in_use_by})
                household_permission = live_drag_component.get_permission(LiveDragPermission.HOUSEHOLD)
                if household_permission:
                    owned_by = 'Allowed, Owned by: {}'.format(household_name)
                else:
                    owned_by = 'Disallowed, Owned by: {}'.format(household_name)
                ret_dict['live_drag'].append({'live_drag_data_name': 'Active Household Permission', 'live_drag_data_value': owned_by})
                state_permission = live_drag_component.get_permission(LiveDragPermission.STATE)
                if not state_permission:
                    states_disabling = 'Disallowed, Disabled by: {}'.format(gsi_handlers.gsi_utils.format_object_list_names(live_drag_component.get_state_op_owners()))
                else:
                    states_disabling = 'Allowed'
                ret_dict['live_drag'].append({'live_drag_data_name': 'State Permission', 'live_drag_data_value': states_disabling})
            walkstyle_info = []
            ret_dict['walkstyles'] = walkstyle_info
            ret_dict['portals'] = []
            routing_component = cur_obj.routing_component
            if routing_component is not None:
                walkstyle = cur_obj.get_walkstyle()
                walkstyle_behavior = cur_obj.get_walkstyle_behavior()
                walkstyle_list = cur_obj.get_walkstyle_list()
                for walkstyle_request in cur_obj.get_walkstyle_requests():
                    combo_replacement_tuple = walkstyle_behavior.get_combo_replacement(walkstyle_request.walkstyle, walkstyle_list)
                    if combo_replacement_tuple is not None:
                        combo_replacement_str = '{}({})'.format(combo_replacement_tuple.result, ','.join(str(x) for x in combo_replacement_tuple.key_combo_list))
                        short_replacement_str = '{} (Combo: {})'.format(walkstyle_behavior.get_short_walkstyle(walkstyle_request.walkstyle, cur_obj), walkstyle_behavior.get_short_walkstyle(combo_replacement_tuple.result, cur_obj))
                    else:
                        combo_replacement_str = ''
                        short_replacement_str = '{}'.format(walkstyle_behavior.get_short_walkstyle(walkstyle_request.walkstyle, cur_obj))
                    walkstyle_entry = {'walkstyle_priority': '{} ({})'.format(str(walkstyle_request.priority), int(walkstyle_request.priority)), 'walkstyle_type': str(walkstyle_request.walkstyle), 'walkstyle_short': short_replacement_str, 'walkstyle_combo_replacement': combo_replacement_str, 'walkstyle_is_current': 'X' if sim is not None and walkstyle is walkstyle_request.walkstyle else '', 'walkstyle_is_default': 'X' if sim is not None and walkstyle_behavior.default_walkstyle is walkstyle_request.walkstyle else ''}
                    walkstyle_info.append(walkstyle_entry)
                routing_context = routing_component.get_routing_context()
                portal_key_mask = routing_context.get_portal_key_mask()
                ret_dict['portals'] = [{'portal_flag': portal_flag.name} for portal_flag in PortalFlags if portal_flag & portal_key_mask]
        all_object_data.append(ret_dict)
    return all_object_data
object_definitions_schema = GsiGridSchema(label='Object Definitions', auto_refresh=False, exclude_from_dump=True)object_definitions_schema.add_field('obj_name', label='Name', width=4)object_definitions_schema.add_field('instance_id', label='Inst ID', unique_field=True, type=GsiFieldVisualizers.INT)object_definitions_schema.add_field('pack_id', label='Pack')object_definitions_schema.add_view_cheat('objects.clear_lot', label='Clear Objs', refresh_view=False)pack_names = []for pack in sims4.common.get_available_packs():
    pack_names.append(str(pack))for pack_name in sorted(pack_names):
    object_definitions_schema.add_filter(pack_name)with object_definitions_schema.add_view_cheat('objects.gsi_create_obj', label='Create Obj', dbl_click=True, refresh_view=False) as cheat:
    cheat.add_token_param('instance_id')with object_definitions_schema.add_view_cheat('objects.gsi_create_objs_from_pack', label='Create Obj From Pack', refresh_view=False) as cheat:
    cheat.add_token_param('instance_id')with object_definitions_schema.add_view_cheat('objects.gsi_create_obj_and_variants', label='Create Variants', refresh_view=False) as cheat:
    cheat.add_token_param('instance_id')with object_definitions_schema.add_view_cheat('objects.gsi_create_obj_in_inventory', label='Inv +1', refresh_view=False) as cheat:
    cheat.add_token_param('instance_id')with object_definitions_schema.add_view_cheat('objects.gsi_create_obj_in_inventory', label='Inv +20', refresh_view=False) as cheat:
    cheat.add_token_param('instance_id')
    cheat.add_static_param('20')
@GsiHandler('object_definitions', object_definitions_schema)
def generate_object_instances_data(*args, zone_id:int=None, filter=None, **kwargs):
    filter_list = parse_filter_to_list(filter)
    all_objects = []
    for key in sorted(sims4.resources.list(type=sims4.resources.Types.OBJECTDEFINITION)):
        pack_id = str(Pack(build_buy.get_object_pack_by_key(key.type, key.instance, key.group)))
        if filter_list is not None and pack_id not in filter_list:
            pass
        else:
            all_objects.append({'obj_name': sims4.resources.get_debug_name(key, table_type=sims4.hash_util.KEYNAMEMAPTYPE_OBJECTINSTANCES), 'instance_id': str(key.instance), 'pack_id': pack_id})
    return all_objects
object_removed_schema = GsiGridSchema(label='Object Removed Log')object_removed_schema.add_field('mgr', label='Manager', width=1, hidden=True)object_removed_schema.add_field('objId', label='Object Id', width=3, unique_field=True)object_removed_schema.add_field('classStr', label='Class', width=3)object_removed_schema.add_field('modelStr', label='Model', width=3)object_removed_schema.add_field('parent', label='Parent', width=2)object_removed_archiver = GameplayArchiver('ObjectRemoved', object_removed_schema)
def archive_object_removal(obj_removed):
    class_str = gsi_handlers.gsi_utils.format_object_name(obj_removed)
    model_name = _get_model_name(obj_removed)
    ret_dict = {'mgr': str(obj_removed.manager).replace('_manager', ''), 'objId': hex(obj_removed.id), 'classStr': class_str, 'modelStr': model_name}
    parent = getattr(obj_removed, 'parent', None)
    if parent is not None:
        ret_dict['parent'] = gsi_handlers.gsi_utils.format_object_name(parent)
    object_removed_archiver.archive(data=ret_dict)
