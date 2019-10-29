from gsi_handlers.gameplay_archiver import GameplayArchiverfrom gsi_handlers.gsi_utils import parse_filter_to_listfrom sims4.gsi.dispatcher import GsiHandlerfrom sims4.gsi.schema import GsiGridSchema, GsiFieldVisualizersimport enumimport servicesimport sims4drama_schema = GsiGridSchema(label='Drama Nodes/Drama Scheduler')drama_schema.add_field('drama_node_id', label='Drama Node Id', unique_field=True)drama_schema.add_field('drama_node', label='Drama Node', width=3)drama_schema.add_field('status', label='Status', width=3)drama_schema.add_field('time_left', label='Time Left')drama_schema.add_field('receiver_sim', label='Receiver Sim')drama_schema.add_field('sender_sim', label='Sender Sim')NONPICKERDRAMANODES_DRAMA_NODES_FILTER = 'non-picker drama nodes'PICKER_DRAMA_NODE_SUBSTRING = 'pickerdramanode'drama_schema.add_filter(NONPICKERDRAMANODES_DRAMA_NODES_FILTER)drama_schema.add_filter('actorcareer')drama_schema.add_filter('freelancer')drama_schema.add_filter('oddjob')
@GsiHandler('drama', drama_schema)
def generate_drama_scheduler_data(zone_id:int=None, filter=None):
    all_nodes = []
    filter_list = parse_filter_to_list(filter)
    drama_scheduler = services.drama_scheduler_service()
    if drama_scheduler is None:
        return all_nodes

    def drama_node_matches_filters(drama_node):
        if filter_list is None:
            return True
        drama_node_string = type(drama_node).__name__.lower()
        if NONPICKERDRAMANODES_DRAMA_NODES_FILTER in filter_list and PICKER_DRAMA_NODE_SUBSTRING not in drama_node_string:
            return True
        elif any(a_filter in drama_node_string for a_filter in filter_list):
            return True
        return False

    for drama_node in drama_scheduler.active_nodes_gen():
        if drama_node_matches_filters(drama_node):
            all_nodes.append({'drama_node_id': str(drama_node.uid), 'status': 'Active', 'drama_node': str(drama_node), 'receiver_sim': str(drama_node.get_receiver_sim_info()), 'sender_sim': str(drama_node.get_sender_sim_info())})
    for drama_node in drama_scheduler.scheduled_nodes_gen():
        if drama_node_matches_filters(drama_node):
            all_nodes.append({'drama_node_id': str(drama_node.uid), 'drama_node': str(drama_node), 'status': 'Scheduled', 'time_left': str(drama_node.get_time_remaining()), 'receiver_sim': str(drama_node.get_receiver_sim_info()), 'sender_sim': str(drama_node.get_sender_sim_info())})
    return all_nodes
drama_tuning_data_schema = GsiGridSchema(label='Drama Nodes/Drama Tuning Data')drama_tuning_data_schema.add_field('drama_node_name', label='Node Name', width=2)drama_tuning_data_schema.add_field('sunday', label='Sunday')drama_tuning_data_schema.add_field('monday', label='Monday')drama_tuning_data_schema.add_field('tuesday', label='Tuesday')drama_tuning_data_schema.add_field('wednesday', label='Wednesday')drama_tuning_data_schema.add_field('thursday', label='Thursday')drama_tuning_data_schema.add_field('friday', label='Friday')drama_tuning_data_schema.add_field('saturday', label='Saturday')with drama_tuning_data_schema.add_view_cheat('drama.schedule_node', label='Schedule') as cheat:
    cheat.add_token_param('drama_node_name')with drama_tuning_data_schema.add_view_cheat('drama.run_node', label='Run') as cheat:
    cheat.add_token_param('drama_node_name')
@GsiHandler('drama_tuning', drama_tuning_data_schema)
def generate_drama_tuning_data(zone_id:int=None):
    all_nodes = []
    dnm = services.get_instance_manager(sims4.resources.Types.DRAMA_NODE)
    for node_type in dnm.types.values():
        node_data = {}
        node_data['drama_node_name'] = node_type.__name__
        valid_time_strings = node_type.get_debug_valid_time_strings()
        for (day, valid_hours) in valid_time_strings.items():
            day_name = day.name.lower()
            time_string = ','.join(valid_hours)
            node_data[day_name] = time_string
        all_nodes.append(node_data)
    return all_nodes

class GSIRejectedDramaNodeScoringData:

    def __init__(self, drama_node, reason, *args, score=0, score_details='', receiver=None, sender=None):
        self.drama_node = drama_node
        self.reason = reason.format(*args)
        self.score = score
        self.score_details = score_details
        self.receiver = str(receiver)
        self.sender = str(sender)

    def get_gsi_view_dictionary(self):
        return {'drama_node': str(self.drama_node), 'reason': self.reason, 'score': str(self.score), 'score_details': self.score_details, 'receiver': self.receiver, 'sender': self.sender}

class GSIDramaNodeScoringData:

    def __init__(self, drama_node, score, score_details, receiver, sender):
        self.drama_node = drama_node
        self.score = score
        self.score_details = score_details
        self.receiver = str(receiver)
        self.sender = str(sender)

    def get_gsi_view_dictionary(self):
        return {'drama_node': str(self.drama_node), 'score': str(self.score), 'score_details': self.score_details, 'receiver': self.receiver, 'sender': self.sender}

class GSIDramaScoringData:

    def __init__(self):
        self.bucket = 'No Bucket'
        self.nodes_to_schedule = 0
        self.rejected_nodes = []
        self.potential_nodes = []
        self.chosen_nodes = []
drama_scheduler_archive_schema = GsiGridSchema(label='Drama Nodes/Drama Scoring Archive', sim_specific=False)drama_scheduler_archive_schema.add_field('game_time', label='Game/Sim Time', type=GsiFieldVisualizers.TIME)drama_scheduler_archive_schema.add_field('bucket', label='Bucket')drama_scheduler_archive_schema.add_field('nodes_to_schedule', label='Nodes to Schedule')drama_scheduler_archive_schema.add_field('nodes_scheduled', label='Nodes Scheduled')with drama_scheduler_archive_schema.add_has_many('Rejected Nodes', GsiGridSchema) as sub_schema:
    sub_schema.add_field('drama_node', label='Drama Node')
    sub_schema.add_field('reason', label='Reason')
    sub_schema.add_field('score', label='Score')
    sub_schema.add_field('receiver', label='Receiver')
    sub_schema.add_field('sender', label='Sender')
    sub_schema.add_field('score_details', label='Score Details', width=6)with drama_scheduler_archive_schema.add_has_many('Potential Nodes', GsiGridSchema) as sub_schema:
    sub_schema.add_field('drama_node', label='Drama Node')
    sub_schema.add_field('score', label='Score')
    sub_schema.add_field('receiver', label='Receiver')
    sub_schema.add_field('sender', label='Sender')
    sub_schema.add_field('score_details', label='Score Details', width=6)with drama_scheduler_archive_schema.add_has_many('Chosen Nodes', GsiGridSchema) as sub_schema:
    sub_schema.add_field('drama_node', label='Drama Node')
    sub_schema.add_field('score', label='Score')
    sub_schema.add_field('receiver', label='Receiver')
    sub_schema.add_field('sender', label='Sender')
    sub_schema.add_field('score_details', label='Score Details', width=6)scoring_archiver = GameplayArchiver('drama_scoring_archive', drama_scheduler_archive_schema, add_to_archive_enable_functions=True)
def is_scoring_archive_enabled():
    return scoring_archiver.enabled

def archive_drama_scheduler_scoring(scoring_data):
    time_service = services.time_service()
    if time_service.sim_timeline is None:
        time = 'zone not running'
    else:
        time = time_service.sim_now
    entry = {'game_time': str(time), 'bucket': str(scoring_data.bucket), 'nodes_to_schedule': scoring_data.nodes_to_schedule, 'nodes_scheduled': len(scoring_data.chosen_nodes), 'Rejected Nodes': [node.get_gsi_view_dictionary() for node in scoring_data.rejected_nodes], 'Potential Nodes': [node.get_gsi_view_dictionary() for node in scoring_data.potential_nodes], 'Chosen Nodes': [node.get_gsi_view_dictionary() for node in scoring_data.chosen_nodes]}
    scoring_archiver.archive(entry)

class DramaNodeLogActions(enum.Int, export=False):
    SCHEDULED = ...
    CANCELED = ...
    RUNNING = ...
    COMPLETED = ...
drama_node_log_schema = GsiGridSchema(label='Drama Nodes/Drama Node Log', sim_specific=False)drama_node_log_schema.add_field('game_time', label='Game/Sim Time', type=GsiFieldVisualizers.TIME)drama_node_log_schema.add_field('drama_node_id', label='Drama Node Id')drama_node_log_schema.add_field('drama_node', label='Drama Node', width=3)drama_node_log_schema.add_field('action', label='Action', width=3)drama_node_log_schema.add_field('reason', label='Reason')drama_node_log = GameplayArchiver('drama_node_log', drama_node_log_schema, add_to_archive_enable_functions=True)
def is_drama_node_log_enabled():
    return drama_node_log.enabled

def log_drama_node_scoring(drama_node, action, *args):
    time_service = services.time_service()
    if time_service.sim_timeline is None:
        time = 'zone not running'
    else:
        time = time_service.sim_now
    if args:
        reason = args[0]
        format_args = args[1:]
        reason.format(*format_args)
    else:
        reason = ''
    entry = {'game_time': str(time), 'drama_node_id': str(drama_node.uid), 'drama_node': str(drama_node), 'action': action.name, 'reason': reason}
    drama_node_log.archive(entry)
