from server_commands.argument_helpers import OptionalSimInfoParam, get_optional_target, RequiredTargetParamfrom sims4.commands import CommandTypefrom ui.notebook_tuning import NotebookCategoriesimport servicesimport sims4
@sims4.commands.Command('notebook.generate_notebook', command_type=CommandType.Live)
def generate_notebook(opt_sim:OptionalSimInfoParam=None, initial_category:int=None, _connection=None):
    sim_info = get_optional_target(opt_sim, target_type=OptionalSimInfoParam, _connection=_connection)
    if sim_info is not None and sim_info.notebook_tracker is not None:
        initial_selected_category = None if initial_category is None else NotebookCategories(initial_category)
        sim_info.notebook_tracker.generate_notebook_information(initial_selected_category=initial_selected_category)
    return True

@sims4.commands.Command('notebook.mark_entry_as_seen', command_type=CommandType.Live)
def mark_entry_as_seen(sim:RequiredTargetParam, subcategory_id:int, entry_id:int, _connection=None):
    sim_info = sim.get_target(manager=services.sim_info_manager())
    if sim_info is None:
        sims4.commands.output('Sim with id {} is not found to mark notebook entry as seen.'.format(sim.target_id), _connection)
        return False
    if sim_info.notebook_tracker is None:
        sims4.commands.output('Notebook tracker is not found on Sim {} to mark notebook entry as seen'.format(sim_info), _connection)
        return False
    sim_info.notebook_tracker.mark_entry_as_seen(subcategory_id, entry_id)
    return True
