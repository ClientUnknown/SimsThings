from gsi_handlers.gameplay_archiver import GameplayArchiverfrom sims4.gsi.dispatcher import GsiHandlerfrom sims4.gsi.schema import GsiGridSchema, GsiFieldVisualizersimport servicesstory_progression_view_schema = GsiGridSchema(label='Story Progression - State', sim_specific=True)story_progression_view_schema.add_field('action_id', label='ID', type=GsiFieldVisualizers.INT, width=1, unique_field=True)story_progression_view_schema.add_field('action_name', label='Action', width=6)story_progression_view_schema.add_field('action_duration', label='Duration', width=3)
@GsiHandler('story_progression_view', story_progression_view_schema)
def generate_story_progression_view_data(sim_id:int=None):
    sim_info_manager = services.sim_info_manager()
    if sim_info_manager is None:
        return
    sim_info = sim_info_manager.get(sim_id)
    if sim_info is None:
        return
    data = []
    if sim_info.story_progression_tracker is None:
        return data
    for story_progression_action in sim_info.story_progression_tracker.get_actions_gen():
        data.append({'action_id': story_progression_action.action_id, 'action_name': str(story_progression_action), 'action_duration': str(story_progression_action.get_duration())})
    return data
story_progression_sim_archive_schema = GsiGridSchema(label='Story Progression - Log', sim_specific=True)story_progression_sim_archive_schema.add_field('action_name', label='Action', width=5)story_progression_sim_archive_schema.add_field('action_result', label='Result', width=3)story_progression_sim_archive_schema.add_field('action_duration', label='Duration', width=3)with story_progression_sim_archive_schema.add_has_many('action_demographics', GsiGridSchema, label='Demographics') as sub_schema:
    sub_schema.add_field('demographic_name', label='Demographic', width=4)
    sub_schema.add_field('demographic_previous_error', label='Previous Error', type=GsiFieldVisualizers.FLOAT, width=2)
    sub_schema.add_field('demographic_current_error', label='Current Error', type=GsiFieldVisualizers.FLOAT, width=2)story_progression_sim_archiver = GameplayArchiver('story_progression_sim', story_progression_sim_archive_schema, add_to_archive_enable_functions=True)
def archive_sim_story_progression(sim_info, action, *, result, global_demographics=(), action_demographics=()):
    archive_data = {'action_name': str(action), 'action_result': str(result), 'action_duration': str(action.get_duration()), 'action_demographics': []}
    for (global_demographic, action_demographic) in zip(global_demographics, action_demographics):
        archive_data['action_demographics'].append({'demographic_name': str(action_demographic), 'demographic_previous_error': str(global_demographic.get_demographic_error()), 'demographic_current_error': str(action_demographic.get_demographic_error())})
    story_progression_sim_archiver.archive(data=archive_data, object_id=sim_info.sim_id)
story_progression_global_archive_schema = GsiGridSchema(label='Story Progression')story_progression_global_archive_schema.add_field('action_type', label='Type', width=1)story_progression_global_archive_schema.add_field('action_message', label='Message', type=GsiFieldVisualizers.STRING, width=10)story_progression_archiver = GameplayArchiver('story_progression', story_progression_global_archive_schema)
def archive_story_progression(action, message, *args):
    entry = {'action_type': str(action), 'action_message': message.format(*args)}
    story_progression_archiver.archive(data=entry)
