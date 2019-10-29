from _collections import defaultdictfrom gsi_handlers.gameplay_archiver import GameplayArchiverfrom gsi_handlers.gsi_utils import format_enum_namefrom objects import ALL_HIDDEN_REASONSfrom sims4.gsi.dispatcher import GsiHandlerfrom sims4.gsi.schema import GsiGridSchema, GsiFieldVisualizersimport date_and_timeimport servicessituation_sim_schema = GsiGridSchema(label='Situations/Situation Manager')situation_sim_schema.add_field('situation_id', label='Situation Id', width=1, unique_field=True)situation_sim_schema.add_field('situation', label='Situation Name', width=3)situation_sim_schema.add_field('state', label='State', width=1.5)situation_sim_schema.add_field('time_left', label='Time Left')situation_sim_schema.add_field('sim_count', label='Number of Sims', type=GsiFieldVisualizers.INT, width=0.5)situation_sim_schema.add_field('score', label='Score', type=GsiFieldVisualizers.FLOAT, width=0.5)situation_sim_schema.add_field('level', label='Level', width=1, hidden=True)situation_sim_schema.add_field('exclusivity', label='Exclusivity', width=1)situation_sim_schema.add_field('creation_source', label='Source', width=1.5)with situation_sim_schema.add_view_cheat('situations.destroy', label='Destroy') as cheat:
    cheat.add_token_param('situation_id')with situation_sim_schema.add_view_cheat('sims.focus_camera_on_sim', label='Focus Camera', dbl_click=False) as cheat:
    cheat.add_token_param('sim_Id')with situation_sim_schema.add_has_many('Sims', GsiGridSchema) as sub_schema:
    sub_schema.add_field('sim_Id', label='Sim ID')
    sub_schema.add_field('sim_name', label='Sim')
    sub_schema.add_field('sim_score', label='Score', type=GsiFieldVisualizers.FLOAT)
    sub_schema.add_field('sim_job', label='Job')
    sub_schema.add_field('sim_role', label='Role')
    sub_schema.add_field('sim_emotion', label='Emotion')
    sub_schema.add_field('sim_on_active_lot', label='On Active Lot')with situation_sim_schema.add_has_many('Goals', GsiGridSchema) as sub_schema:
    sub_schema.add_field('goal', label='Goal')
    sub_schema.add_field('goal_set', label='Goal Set')
    sub_schema.add_field('time_created', label='Time Created')
    sub_schema.add_field('time_completed', label='Time Completed')
    sub_schema.add_field('score', label='Score', type=GsiFieldVisualizers.INT, width=1)with situation_sim_schema.add_has_many('Churn', GsiGridSchema) as sub_schema:
    sub_schema.add_field('sim_job', label='Job')
    sub_schema.add_field('min', label='Min', type=GsiFieldVisualizers.INT, width=1)
    sub_schema.add_field('max', label='Max', type=GsiFieldVisualizers.INT, width=1)
    sub_schema.add_field('here', label='Sims Here', type=GsiFieldVisualizers.INT, width=1)
    sub_schema.add_field('coming', label='Sims Coming', type=GsiFieldVisualizers.INT, width=1)
    sub_schema.add_field('time_left', label='Time Until Churn')with situation_sim_schema.add_has_many('Shifts', GsiGridSchema) as sub_schema:
    sub_schema.add_field('sim_job', label='Job')
    sub_schema.add_field('num', label='Tuned Staffing', type=GsiFieldVisualizers.INT, width=1)
    sub_schema.add_field('here', label='Sims Here', type=GsiFieldVisualizers.INT, width=1)
    sub_schema.add_field('coming', label='Sims Coming', type=GsiFieldVisualizers.INT, width=1)
    sub_schema.add_field('change_time_left', label='Time Until Shift Change')
    sub_schema.add_field('churn_time_left', label='Time Until Churn')with situation_sim_schema.add_has_many('Tags', GsiGridSchema) as sub_schema:
    sub_schema.add_field('tag', label='Tag')with situation_sim_schema.add_has_many('Additional Data', GsiGridSchema) as sub_schema:
    sub_schema.add_field('field', label='Field')
    sub_schema.add_field('data', label='Data')
@GsiHandler('situations', situation_sim_schema)
def generate_situation_data(zone_id:int=None):
    all_situations = []
    sit_man = services.get_zone_situation_manager(zone_id=zone_id)
    if sit_man is None:
        return all_situations
    situations = list(sit_man._objects.values())
    for sit in situations:
        sim_data = []
        for (sim, situation_sim) in tuple(sit._situation_sims.items()):
            if sim:
                sim_data.append({'sim_Id': str(hex(sim.sim_id)), 'sim_name': sim.full_name, 'sim_job': situation_sim.current_job_type.__name__ if situation_sim.current_job_type is not None else 'None', 'sim_role': situation_sim.current_role_state_type.__name__ if situation_sim.current_role_state_type is not None else 'None', 'sim_emotion': situation_sim.emotional_buff_name, 'sim_on_active_lot': sim.is_on_active_lot()})
        goal_data = []
        goals = sit.get_situation_goal_info()
        if goals is not None:
            for (goal, tuned_goal_set) in goals:
                goal_data.append({'goal': goal.get_gsi_name(), 'goal_set': tuned_goal_set.__name__ if tuned_goal_set is not None else 'None', 'time_created': str(goal.created_time), 'time_completed': str(goal.completed_time), 'score': goal.score})
            completed_goals = sit.get_situation_completed_goal_info()
            if completed_goals is not None:
                for (goal, tuned_goal_set) in completed_goals:
                    goal_data.append({'goal': goal.get_gsi_name(), 'goal_set': tuned_goal_set.__name__ if tuned_goal_set is not None else 'None', 'time_created': str(goal.created_time), 'time_completed': str(goal.completed_time), 'score': goal.score})
        churn_data = []
        for job_data in sit.gsi_all_jobs_data_gen():
            if job_data.gsi_has_churn():
                churn_data.append({'sim_job': job_data.gsi_get_job_name(), 'min': job_data.gsi_get_churn_min(), 'max': job_data.gsi_get_churn_max(), 'here': job_data.gsi_get_num_churn_sims_here(), 'coming': job_data.gsi_get_num_churn_sims_coming(), 'time_left': str(job_data.gsi_get_remaining_time_until_churn())})
        shift_data = []
        for job_data in sit.gsi_all_jobs_data_gen():
            if job_data.gsi_has_shifts():
                shift_data.append({'sim_job': job_data.gsi_get_job_name(), 'num': job_data.gsi_get_shifts_staffing(), 'here': job_data.gsi_get_num_churn_sims_here(), 'coming': job_data.gsi_get_num_churn_sims_coming(), 'change_time_left': str(job_data.gsi_get_remaining_time_until_shift_change()), 'churn_time_left': str(job_data.gsi_get_remaining_time_until_churn())})
        tag_data = [{'tag': tag.name} for tag in sit.tags]
        additional_data = sit.gsi_additional_data('field', 'data')
        all_situations.append({'situation_id': str(sit.id), 'situation': str(sit), 'time_left': str(sit._get_remaining_time_for_gsi()) if sit._get_remaining_time_for_gsi() is not None else 'Forever', 'state': sit.get_phase_state_name_for_gsi(), 'sim_count': len(sit._situation_sims), 'score': sit.score, 'level': str(sit.get_level()), 'exclusivity': sit.exclusivity.name, 'creation_source': sit.creation_source, 'Sims': sim_data, 'Goals': goal_data, 'Churn': churn_data, 'Shifts': shift_data, 'Tags': tag_data, 'Additional Data': additional_data})
    return all_situations

def _setup_bouncer_schema(bouncer_schema):
    bouncer_schema.add_field('bouncer_id', label='Bouncer Id', type=GsiFieldVisualizers.INT, width=1)
    bouncer_schema.add_field('situation', label='Situation')
    bouncer_schema.add_field('situation_id', label='Situation Id', type=GsiFieldVisualizers.INT, width=1)
    bouncer_schema.add_field('job', label='Job')
    bouncer_schema.add_field('filter', label='Filter')
    bouncer_schema.add_field('status', label='Status')
    bouncer_schema.add_field('klout', label='Klout', type=GsiFieldVisualizers.INT, width=1)
    bouncer_schema.add_field('priority', label='Priority')
    bouncer_schema.add_field('sim_name', label='Assigned Sim')
    bouncer_schema.add_field('spawning_option', label='Spawning Option')
    bouncer_schema.add_field('additional_filter_terms', label='Additional Filter Terms')
    bouncer_schema.add_field('unique', label='unique', unique_field=True, hidden=True)

def _get_bouncer_request_gsi_data(request):
    return {'bouncer_id': str(request._creation_id), 'situation': str(request._situation), 'situation_id': str(request._situation.id), 'job': request._job_type.__name__, 'filter': request._sim_filter.__name__ if request._sim_filter is not None else 'None', 'status': request._status.name, 'klout': request._get_request_klout() if request._get_request_klout() is not None else 10000, 'priority': request._request_priority.name, 'sim_name': request.assigned_sim.full_name if request.assigned_sim is not None else 'None', 'spawning_option': request.spawning_option.name, 'additional_filter_terms': str(request.get_additional_filter_terms()), 'unique': str(id(request))}
situation_bouncer_schema = GsiGridSchema(label='Situations/Situation Bouncer')_setup_bouncer_schema(situation_bouncer_schema)
@GsiHandler('situation_bouncer', situation_bouncer_schema)
def generate_situation_bouncer_data(zone_id:int=None):
    all_requests = []
    situation_manager = services.get_zone_situation_manager(zone_id=zone_id)
    if situation_manager is None:
        return all_requests
    bouncer = situation_manager.bouncer
    for request in bouncer._all_requests_gen():
        all_requests.append(_get_bouncer_request_gsi_data(request))
    return all_requests
situation_bouncer_archiver_schema = GsiGridSchema(label='Situations/Situation Bouncer Archiver')situation_bouncer_archiver_schema.add_field('script_status', label='ScriptStatus')_setup_bouncer_schema(situation_bouncer_archiver_schema)bouncer_archiver = GameplayArchiver('bouncer_archiver', situation_bouncer_archiver_schema, max_records=100, add_to_archive_enable_functions=True)
def archive_bouncer_request(request, script_status, status_reason=None, sim_override=None):
    request_data = _get_bouncer_request_gsi_data(request)
    if status_reason is not None:
        script_status = '{}: {}'.format(script_status, status_reason)
    request_data['script_status'] = script_status
    if sim_override is not None:
        request_data['sim_name'] = sim_override.full_name
    bouncer_archiver.archive(data=request_data)
sim_situation_schema = GsiGridSchema(label='Situations/Sim Situation View')sim_situation_schema.add_field('sim_id', label='Sim Id', unique_field=True)sim_situation_schema.add_field('sim', label='Sim')sim_situation_schema.add_field('time_on_lot', label='On Lot Time')sim_situation_schema.add_field('creation_source', label='Creation Source')with sim_situation_schema.add_view_cheat('sims.focus_camera_on_sim', label='Focus Camera', dbl_click=True) as cheat:
    cheat.add_token_param('sim_id')with sim_situation_schema.add_has_many('Current Situations', GsiGridSchema) as sub_schema:
    sub_schema.add_field('situation', label='Situation')
    sub_schema.add_field('job', label='Job')
    sub_schema.add_field('role', label='Role')with sim_situation_schema.add_has_many('Blacklist', GsiGridSchema) as sub_schema:
    sub_schema.add_field('tag', label='Tag')
    sub_schema.add_field('blacklist_time', label='Blacklist Time')
@GsiHandler('sim_situation_view', sim_situation_schema)
def generate_sim_situation_view(zone_id:int=None):
    sim_data = []
    situation_manager = services.get_zone_situation_manager(zone_id=zone_id)
    if situation_manager is None:
        return sim_data
    for sim_info in tuple(services.sim_info_manager().values()):
        display_sim = False
        on_lot_string = ''
        blacklist_data = []
        situation_data = []
        sim = sim_info.get_sim_instance(allow_hidden_flags=ALL_HIDDEN_REASONS)
        if sim is not None:
            on_lot_time = situation_manager.get_time_span_sim_has_been_on_lot(sim)
            if on_lot_time is not None:
                display_sim = True
                on_lot_string = str(on_lot_time)
            for situation in situation_manager.get_situations_sim_is_in(sim):
                display_sim = True
                situation_data.append({'situation': str(situation), 'job': str(situation.get_current_job_for_sim(sim)), 'role': str(situation.get_current_role_state_for_sim(sim))})
        blacklist_info = situation_manager.get_blacklist_info(sim_info.id)
        if blacklist_info is not None:
            for (tag, blacklist_time) in blacklist_info:
                display_sim = True
                blacklist_data.append({'tag': str(tag), 'blacklist_time': str(blacklist_time)})
        if display_sim:
            sim_data.append({'sim_id': str(hex(sim_info.id)), 'sim': sim_info.full_name, 'time_on_lot': on_lot_string, 'creation_source': format_enum_name(sim_info.creation_source), 'Current Situations': situation_data, 'Blacklist': blacklist_data})
    return sim_data

class SituationDataArchiver(GameplayArchiver):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._situation_data = defaultdict(list)

    def archive_event(self, situation, event, sub_event=False, final_event=False):
        time_service = services.time_service()
        if time_service.sim_timeline is not None:
            game_time = str(time_service.sim_now)
        else:
            game_time = str(services.game_clock_service().now())
        self._situation_data[situation.id].append({'game_time': game_time, 'event': event, 'source': str(situation.creation_source)})
        if not sub_event:
            data = {'situation_id': situation.id, 'situation': str(situation), 'event': event, 'Situation Events': self._situation_data[situation.id]}
            self.archive(data)
        if final_event:
            del self._situation_data[situation.id]
situation_archive_schema = GsiGridSchema(label='Situations/Situation Archive')situation_archive_schema.add_field('situation_id', label='Situation Id', width=1, type=GsiFieldVisualizers.INT)situation_archive_schema.add_field('situation', label='Situation Name', width=3)situation_archive_schema.add_field('event', label='Situation Event', width=3)situation_archive_schema.add_field('source', label='Creation Source', width=3)with situation_archive_schema.add_has_many('Situation Events', GsiGridSchema) as sub_schema:
    sub_schema.add_field('game_time', label='Game Time', type=GsiFieldVisualizers.TIME)
    sub_schema.add_field('event', label='Event')situation_archiver = SituationDataArchiver('situation_log', situation_archive_schema, add_to_archive_enable_functions=True)