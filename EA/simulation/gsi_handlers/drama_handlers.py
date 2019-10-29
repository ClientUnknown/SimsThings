from gsi_handlers.gameplay_archiver import GameplayArchiver
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

    cheat.add_token_param('drama_node_name')
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

    sub_schema.add_field('drama_node', label='Drama Node')
    sub_schema.add_field('reason', label='Reason')
    sub_schema.add_field('score', label='Score')
    sub_schema.add_field('receiver', label='Receiver')
    sub_schema.add_field('sender', label='Sender')
    sub_schema.add_field('score_details', label='Score Details', width=6)
    sub_schema.add_field('drama_node', label='Drama Node')
    sub_schema.add_field('score', label='Score')
    sub_schema.add_field('receiver', label='Receiver')
    sub_schema.add_field('sender', label='Sender')
    sub_schema.add_field('score_details', label='Score Details', width=6)
    sub_schema.add_field('drama_node', label='Drama Node')
    sub_schema.add_field('score', label='Score')
    sub_schema.add_field('receiver', label='Receiver')
    sub_schema.add_field('sender', label='Sender')
    sub_schema.add_field('score_details', label='Score Details', width=6)
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
