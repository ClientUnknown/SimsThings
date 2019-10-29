from cas.cas import get_tags_from_outfitfrom server_commands.argument_helpers import OptionalTargetParam, get_optional_target, TunableInstanceParam, get_tunable_instancefrom sims.sim_info_types import Species, Agefrom sims.sim_spawner import SimSpawnerimport filtersimport servicesimport sims.sim_spawnerimport sims4.commandsimport sims4.loglogger = sims4.log.Logger('SimFilter')
def _find_sims_with_filter(filter_type, requesting_sim, callback, _connection=None):
    if callback is None:
        sims4.commands.output('No callback supplied for _execute_filter', _connection)
        return
    requesting_sim_info = requesting_sim.sim_info if requesting_sim is not None else None

    def get_sim_filter_gsi_name():
        return 'Sim Filter Command: Find Sims with Filter'

    services.sim_filter_service().submit_filter(filter_type, callback, None, requesting_sim_info=requesting_sim_info, gsi_source_fn=get_sim_filter_gsi_name)
    sims4.commands.output('Processing filter: {}'.format(filter_type), _connection)

@sims4.commands.Command('filter.find')
def filter_find(filter_type:TunableInstanceParam(sims4.resources.Types.SIM_FILTER), opt_sim:OptionalTargetParam=None, _connection=None):

    def _print_found_sims(results, callback_event_data):
        if results:
            for result in results:
                sims4.commands.output('   {}, score: {}'.format(result.sim_info, result.score), _connection)
            logger.info('Sims ID matching request {0}', results)
        else:
            sims4.commands.output('No Match Found', _connection)

    sim = get_optional_target(opt_sim, _connection)
    _find_sims_with_filter(filter_type, sim, _print_found_sims, _connection)

@sims4.commands.Command('filter.invite')
def filter_invite(filter_type:TunableInstanceParam(sims4.resources.Types.SIM_FILTER), opt_sim:OptionalTargetParam=None, _connection=None):

    def _spawn_found_sims(results, callback_event_data):
        if results is not None:
            for result in results:
                sims4.commands.output('Sim : {}'.format(result.sim_info.id), _connection)
                sims.sim_spawner.SimSpawner.load_sim(result.sim_info.id)
            logger.info('Sims ID matching request {0}', results)
        else:
            sims4.commands.output('No sims found!', _connection)

    sim = get_optional_target(opt_sim, _connection)
    _find_sims_with_filter(filter_type, sim, _spawn_found_sims, _connection)

@sims4.commands.Command('filter.spawn_sim')
def filter_spawn_sim(sim_id:int, _connection=None):
    zone_id = services.current_zone_id()
    if sims.sim_spawner.SimSpawner.load_sim(sim_id):
        sims4.commands.output('Sim ID: {} has been invited to lot: {}'.format(sim_id, zone_id), _connection)
    else:
        sims4.commands.output('filter.spawn_sim command faild for sim id: {}  to lot id: {}'.format(sim_id, zone_id), _connection)

@sims4.commands.Command('filter.create', command_type=sims4.commands.CommandType.Automation)
def filter_create(filter_type:TunableInstanceParam(sims4.resources.Types.SIM_FILTER), continue_if_constraints_fail:bool=False, opt_sim:OptionalTargetParam=None, num_of_sims:int=1, spawn_sims:bool=True, _connection=None):

    def callback(filter_results, callback_event_data):
        sims4.commands.automation_output('FilterResults; SimCount: {}'.format(len(filter_results)), _connection)
        if filter_results:
            situation_manager = services.get_zone_situation_manager()
            sim_infos = [result.sim_info for result in filter_results]
            for sim_info in sim_infos:
                if spawn_sims:
                    situation_manager.add_debug_sim_id(sim_info.id)
                    sims.sim_spawner.SimSpawner.spawn_sim(sim_info, None)
                    sims4.commands.output('Spawned {} with id {}'.format(sim_info, sim_info.id), _connection)
                sims4.commands.automation_output('FilterResultSim; SimId: {}'.format(sim_info.id), _connection)
        else:
            sims4.commands.output('No filter with {}'.format(callback_event_data), _connection)

    instanced_sim_ids = tuple(sim.sim_info.id for sim in services.sim_info_manager().instanced_sims_gen())
    household_sim_ids = tuple(sim_info.id for sim_info in services.active_household().sim_info_gen())
    blacklist_sim_ids = set(instanced_sim_ids + household_sim_ids)
    sim = get_optional_target(opt_sim, _connection)

    def get_sim_filter_gsi_name():
        return 'Sim Filter Command: Create Sim to Match Filter'

    filter_name = str(filter_type)
    services.sim_filter_service().submit_matching_filter(number_of_sims_to_find=num_of_sims, sim_filter=filter_type, callback=callback, callback_event_data=filter_name, requesting_sim_info=sim.sim_info, blacklist_sim_ids=blacklist_sim_ids, continue_if_constraints_fail=continue_if_constraints_fail, gsi_source_fn=get_sim_filter_gsi_name)
    sims4.commands.output('Processing filter: {}'.format(filter_name), _connection)

@sims4.commands.Command('filter.create_many_infos')
def filter_create_many_infos(*filter_names, _connection=None):

    def callback(results, callback_event_data):
        sims4.commands.output('Filter: {}'.format(callback_event_data), _connection)
        for result in results:
            sims4.commands.output('   Sim ID:{}, score: {}'.format(result.sim_info.id, result.score), _connection)

    def get_sim_filter_gsi_name():
        return 'Sim Filter Command: Create Many Sim Infos'

    for filter_name in filter_names:
        filter_type = get_tunable_instance(sims4.resources.Types.SIM_FILTER, filter_name)
        if filter_type is not None:
            services.sim_filter_service().submit_matching_filter(number_of_sims_to_find=1, sim_filter=filter_type, callback=callback, callback_event_data=filter_name, gsi_source_fn=get_sim_filter_gsi_name)
            sims4.commands.output('Processing filter: {}'.format(filter_name), _connection)
        else:
            sims4.commands.output('Unknown filter: {}'.format(filter_name), _connection)

@sims4.commands.Command('filter.create_friends')
def filter_create_friends(number_to_create:int, opt_sim:OptionalTargetParam=None, _connection=None):

    def callback(filter_results, callback_event_data):
        if filter_results:
            sim_infos = [result.sim_info for result in filter_results]
            for sim_info in sim_infos:
                sims4.commands.output('Created info name {}'.format(sim_info.full_name), _connection)

    sim = get_optional_target(opt_sim, _connection)

    def get_sim_filter_gsi_name():
        return 'Sim Filter Command: Create Friends'

    services.sim_filter_service().submit_matching_filter(number_of_sims_to_find=number_to_create, sim_filter=filters.tunable.TunableSimFilter.ANY_FILTER, callback=callback, requesting_sim_info=sim.sim_info, continue_if_constraints_fail=True, allow_yielding=True, blacklist_sim_ids={sim_info.id for sim_info in services.sim_info_manager().values()}, gsi_source_fn=get_sim_filter_gsi_name)

@sims4.commands.Command('filter.create_from_sim_template')
def create_sim_info_from_template(sim_template:TunableInstanceParam(sims4.resources.Types.SIM_TEMPLATE), spawn_sim:bool=False, _connection=None):
    sims4.commands.output('Processing sim_template: {}'.format(sim_template), _connection)
    sim_creator = sim_template.sim_creator
    (sim_info_list, household) = SimSpawner.create_sim_infos([sim_creator], creation_source='cheat: filter.create_from_sim_template')
    if sim_info_list:
        created_sim_info = sim_info_list.pop()
        sim_template.add_template_data_to_sim(created_sim_info)
        sims4.commands.output('Finished template creation: {}'.format(household), _connection)
        if spawn_sim:
            services.get_zone_situation_manager().create_visit_situation_for_unexpected(created_sim_info)
    else:
        sims4.commands.output('Failed to create sim info from template: {}'.format(sim_template), _connection)

@sims4.commands.Command('filter.test_sim_template_generation')
def test_sim_template_generation(_connection=None):
    sim_templates = services.get_instance_manager(sims4.resources.Types.SIM_TEMPLATE).types.values()
    failed_templates = []
    for sim_template in sim_templates:
        if sim_template.template_type != filters.sim_template.SimTemplateType.SIM:
            pass
        else:
            sim_creator = sim_template.sim_creator
            sim_creation_dictionary = sim_creator.build_creation_dictionary()
            tag_set = sim_creation_dictionary['tagSet']
            if sim_creator.species != Species.HUMAN:
                pass
            elif sim_creator.age == Age.BABY:
                pass
            elif sim_creator.resource_key:
                pass
            else:
                sims4.commands.output('Processing Sim Template: {}'.format(sim_template), _connection)
                (sim_info_list, _) = SimSpawner.create_sim_infos([sim_creator], creation_source='cheat: filter.test_sim_template_generation')
                if sim_info_list:
                    created_sim_info = sim_info_list.pop()
                    (current_outfit_category, current_outfit_index) = created_sim_info.get_current_outfit()
                    tags = get_tags_from_outfit(created_sim_info._base, current_outfit_category, current_outfit_index)
                    created_tag_set = set().union(*tags.values())
                    if not tag_set.is_subset(created_tag_set):
                        failed_templates.append((sim_template, sim_creator, tag_set - created_tag_set))
    if failed_templates:
        sims4.commands.output('Failed to generate {} templates!'.format(len(failed_templates)), _connection)
        for (sim_template, sim_creator, missing_tags) in failed_templates:
            sims4.commands.output('Failed to generate {}, sim creator: {}, missing tags: {}'.format(sim_template, sim_creator, missing_tags), _connection)
    sims4.commands.output('Finished Sim Template Generation Test!', _connection)

@sims4.commands.Command('filter.create_household_from_template', command_type=sims4.commands.CommandType.Automation)
def create_household_from_filter(filter_template:TunableInstanceParam(sims4.resources.Types.SIM_TEMPLATE), count:int=1, _connection=None):
    output = sims4.commands.CheatOutput(_connection)
    while count > 0:
        household = filter_template.create_household(None, creation_source='cheat: filter.create_household_from_template')
        count -= 1
        output('Houseohld: {}  id: {}\n'.format(household, household.id))
    output('Done Creating Households!')
    return True
