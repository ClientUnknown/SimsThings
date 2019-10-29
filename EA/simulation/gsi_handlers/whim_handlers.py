from sims4.gsi.dispatcher import GsiHandlerfrom sims4.gsi.schema import GsiGridSchema, GsiFieldVisualizersimport servicesimport sims4.resourcessim_whim_schema = GsiGridSchema(label='Whims/Whims Current', sim_specific=True)sim_whim_schema.add_field('sim_id', label='Sim ID', hidden=True)sim_whim_schema.add_field('whim', label='Whim', unique_field=True, width=3)sim_whim_schema.add_field('instance', label='Instance', width=3)sim_whim_schema.add_field('whimset', label='Whimset', width=3)sim_whim_schema.add_field('target', label='Target', width=2)sim_whim_schema.add_field('value', label='Value', width=1, type=GsiFieldVisualizers.INT)
@GsiHandler('sim_whim_view', sim_whim_schema)
def generate_sim_whim_view_data(sim_id:int=None):
    whim_view_data = []
    sim_info_manager = services.sim_info_manager()
    if sim_info_manager is not None:
        for sim_info in sim_info_manager.objects:
            if sim_info.sim_id == sim_id:
                whim_tracker = sim_info._whim_tracker
                if whim_tracker is None:
                    pass
                else:
                    for (whim, source_whimset) in whim_tracker.whims_and_parents_gen():
                        whim_data = {'sim_id': str(sim_info.sim_id), 'whim': whim.get_gsi_name(), 'instance': whim.__class__.__name__, 'whimset': source_whimset.__name__, 'target': str(whim_tracker.get_whimset_target(source_whimset)), 'value': whim.score}
                        whim_view_data.append(whim_data)
    return whim_view_data
sim_activeset_schema = GsiGridSchema(label='Whims/Whimsets Active', sim_specific=True)sim_activeset_schema.add_field('sim_id', label='Sim ID', hidden=True)sim_activeset_schema.add_field('whimset', label='Whimset', unique_field=True, width=3)sim_activeset_schema.add_field('priority', label='Priority', width=1, type=GsiFieldVisualizers.INT)sim_activeset_schema.add_field('target', label='Current Target', width=2)with sim_activeset_schema.add_view_cheat('whims.give_whim_from_whimset', label='Give from Whimset', dbl_click=True) as cheat:
    cheat.add_token_param('whimset')
    cheat.add_token_param('sim_id')with sim_activeset_schema.add_has_many('potential_whims_view', GsiGridSchema, label='Potential Whims') as sub_schema:
    sub_schema.add_field('whim', label='Whim', width=3)
    sub_schema.add_field('status', label='Status', width=5)
    sub_schema.add_field('weight', label='Weight', width=1, type=GsiFieldVisualizers.FLOAT)
@GsiHandler('sim_activeset_view', sim_activeset_schema)
def generate_sim_activeset_view_data(sim_id:int=None):
    activeset_view_data = []
    sim_info_manager = services.sim_info_manager()
    if sim_info_manager is not None:
        for sim_info in sim_info_manager.objects:
            if sim_info.sim_id == sim_id:
                whim_tracker = sim_info._whim_tracker
                if whim_tracker is None:
                    pass
                else:
                    active_sets = []
                    emotional_whimset = whim_tracker.get_emotional_whimset()
                    if emotional_whimset is not None:
                        active_sets.append(emotional_whimset)
                    active_sets.extend(whim_tracker.get_active_whimsets())
                    for whimset in active_sets:
                        set_data = {'sim_id': str(sim_info.sim_id), 'whimset': whimset.__name__, 'priority': whim_tracker.get_priority(whimset), 'target': str(whim_tracker.get_whimset_target(whimset))}
                        sub_data = []
                        for whim in whimset.whims:
                            test_result = 'Not Chosen'
                            if whim.goal in whim_tracker._test_results_map:
                                test_result = whim_tracker._test_results_map[whim.goal]
                            whim_data = {'whim': whim.goal.__name__, 'status': test_result, 'weight': whim.weight}
                            sub_data.append(whim_data)
                        set_data['potential_whims_view'] = sub_data
                        activeset_view_data.append(set_data)
    return activeset_view_data
sim_whimset_schema = GsiGridSchema(label='Whims/Whimsets All', sim_specific=True)sim_whimset_schema.add_field('simId', label='Sim ID', hidden=True)sim_whimset_schema.add_field('whimset', label='WhimSet', unique_field=True, width=3)sim_whimset_schema.add_field('priority', label='Priority', width=1, type=GsiFieldVisualizers.INT)sim_whimset_schema.add_field('target', label='Target', width=2)sim_whimset_schema.add_field('active_priority', label='Activated', width=1, type=GsiFieldVisualizers.INT)sim_whimset_schema.add_field('chained_priority', label='Chained', width=1, type=GsiFieldVisualizers.INT)sim_whimset_schema.add_field('whims_in_set', label='Whims In Set', width=3)with sim_whimset_schema.add_view_cheat('whims.activate_whimset', label='Activate Whimset', dbl_click=True) as cheat:
    cheat.add_token_param('whimset')
    cheat.add_token_param('simId')
@GsiHandler('sim_whimset_view', sim_whimset_schema)
def generate_sim_whimset_view_data(sim_id:int=None):
    whimset_view_data = []
    sim_info_manager = services.sim_info_manager()
    if sim_info_manager is not None:
        sim_info = sim_info_manager.get(sim_id)
        if sim_info is not None:
            whim_tracker = sim_info._whim_tracker
            if whim_tracker is None:
                return whimset_view_data
            else:
                whim_set_list = []
                for whim_set in services.get_instance_manager(sims4.resources.Types.ASPIRATION).all_whim_sets_gen():
                    priority = whim_tracker.get_priority(whim_set)
                    whim_set_list.append((priority, whim_set))
                    whim_set_list = sorted(whim_set_list, key=lambda whim_set: whim_set[0])
                    whim_set_list.reverse()
                if whim_set_list is not None:
                    for whim_set_data in whim_set_list:
                        whim_set = whim_set_data[1]
                        whims_in_set_str = ', '.join(whim.goal.__name__ for whim in whim_set.whims)
                        whim_set_entry = {'simId': str(sim_id), 'whimset': whim_set.__name__, 'priority': whim_tracker.get_priority(whim_set), 'target': str(whim_tracker.get_whimset_target(whim_set)), 'active_priority': getattr(whim_set, 'activated_priority', None), 'chained_priority': getattr(whim_set, 'chained_priority', None), 'whims_in_set': whims_in_set_str}
                        whimset_view_data.append(whim_set_entry)
                return whimset_view_data
