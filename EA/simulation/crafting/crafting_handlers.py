from gsi_handlers.gameplay_archiver import GameplayArchiverfrom sims.sim_log import _get_csv_friendly_stringfrom sims4.gsi.schema import GsiGridSchemafrom sims4.repr_utils import standard_brief_id_reprcrafting_archive_schema = GsiGridSchema(label='Crafting Log', sim_specific=True)crafting_archive_schema.add_field('recipe', label='Recipe')crafting_archive_schema.add_field('phase', label='Phase')crafting_archive_schema.add_field('affordance', label='Affordance')crafting_archive_schema.add_field('crafter', label='Crafter')with crafting_archive_schema.add_has_many('phase_details', GsiGridSchema) as sub_schema:
    sub_schema.add_field('visible', label='Visible')
    sub_schema.add_field('progress', label='Current Progress')
    sub_schema.add_field('turns', label='Max Turns')
    sub_schema.add_field('phase_type', label='Phase Type')with crafting_archive_schema.add_has_many('quality applied', GsiGridSchema) as sub_schema:
    sub_schema.add_field('skill', label='Skill adjustment')
    sub_schema.add_field('ingredient', label='Ingredient adjustment')
    sub_schema.add_field('base', label='Base quality')
    sub_schema.add_field('multiplied', label='Multiplied quality')
    sub_schema.add_field('final', label='Final quality')with crafting_archive_schema.add_has_many('ingredient consumption', GsiGridSchema) as sub_schema:
    sub_schema.add_field('ingredient', label='Ingredient consumed')
    sub_schema.add_field('quality', label='Ingredient quality')
    sub_schema.add_field('count', label='Ingredient count')archiver = GameplayArchiver('crafting', crafting_archive_schema, enable_archive_by_default=True, max_records=200, add_to_archive_enable_functions=True)
def log_process(process, sim_id, interaction, logger_crafting):
    interaction_name = '{}({})'.format(interaction.affordance.__name__, interaction.id)
    archive_data = {'recipe': process.recipe.__name__, 'affordance': interaction_name, 'phase': str(process.phase), 'crafter': _get_sim_name(process.crafter)}
    archive_data['ingredients'] = []
    archive_data['quality applied'] = []
    archive_data['phase_details'] = logger_crafting
    logger_crafting['visible'] = str(process.phase.is_visible) if process.phase is not None else 'False'
    archiver.archive(data=archive_data, object_id=sim_id)

def log_ingredient_calculation(process, sim_id, ingredient_log):
    archive_data = {'recipe': process.recipe.__name__, 'affordance': 'ingredient consumption', 'phase': 'ingredient consumption', 'crafter': _get_sim_name(process.crafter)}
    archive_data['ingredient consumption'] = ingredient_log
    archiver.archive(data=archive_data, object_id=sim_id)

def log_quality(process, sim_id, quality_entry):
    archive_data = {'recipe': process.recipe.__name__, 'affordance': 'quality applied', 'phase': 'quality applied', 'crafter': _get_sim_name(process.crafter)}
    archive_data['ingredient consumption'] = []
    archive_data['quality applied'] = quality_entry
    archiver.archive(data=archive_data, object_id=sim_id)

def _get_sim_name(sim):
    if sim is not None:
        s = '{}[{}]'.format(sim.full_name, standard_brief_id_repr(sim.id))
        s = _get_csv_friendly_string(s)
        return s
    return ''
