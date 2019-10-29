from gsi_handlers.gameplay_archiver import GameplayArchiverfrom sims4.gsi.schema import GsiGridSchema, GsiFieldVisualizersimport services
class SimFilterServiceGSILoggingData:

    def __init__(self, request_type, sim_filter_type, yielding, gsi_source_fn):
        self.request_type = request_type
        self.sim_filter_type = sim_filter_type
        self.yielding = yielding
        self.gsi_source_fn = gsi_source_fn
        self.rejected_sim_infos = []
        self.created_sim_infos = []
        self.metadata = []

    def add_created_household(self, household, was_successful=True):
        for sim_info in household:
            self.created_sim_infos.append({'sim_info': str(sim_info), 'was successful': str(was_successful)})

    def add_rejected_sim_info(self, sim_info, reason, filter_term):
        self.rejected_sim_infos.append({'sim_info': str(sim_info), 'reason': reason, 'filter_term': str(filter_term)})

    def add_metadata(self, num_sims, allow_instanced_sims, club, blacklist_sims, optional):
        if len(blacklist_sims):
            blacklist_sims = str(blacklist_sims)
        else:
            blacklist_sims = None
        self.metadata = [num_sims, allow_instanced_sims, str(club), blacklist_sims, optional]
sim_filter_service_archive_schema = GsiGridSchema(label='Sim Filter Service Archive')sim_filter_service_archive_schema.add_field('game_time', label='Game Time', type=GsiFieldVisualizers.TIME)sim_filter_service_archive_schema.add_field('source', label='Source', width=3)sim_filter_service_archive_schema.add_field('request_type', label='Request Type')sim_filter_service_archive_schema.add_field('yielding', label='Yielding')sim_filter_service_archive_schema.add_field('matching_results', label='Num Matching', type=GsiFieldVisualizers.INT)sim_filter_service_archive_schema.add_field('created_sims', label='Num Created', type=GsiFieldVisualizers.INT)sim_filter_service_archive_schema.add_field('filter_type', label='Filter Type', width=2.5)with sim_filter_service_archive_schema.add_has_many('FilterResult', GsiGridSchema) as sub_schema:
    sub_schema.add_field('sim_info', label='Sim Info', width=1)
    sub_schema.add_field('score', label='Score', type=GsiFieldVisualizers.FLOAT, width=0.5)
    sub_schema.add_field('filter_tag', label='Tag', type=GsiFieldVisualizers.STRING, width=0.5)with sim_filter_service_archive_schema.add_has_many('Created', GsiGridSchema) as sub_schema:
    sub_schema.add_field('sim_info', label='Sim Info', width=3)
    sub_schema.add_field('was successful', label='Was Successful', width=3)with sim_filter_service_archive_schema.add_has_many('Rejected', GsiGridSchema) as sub_schema:
    sub_schema.add_field('sim_info', label='Sim Info', width=1)
    sub_schema.add_field('reason', label='Reason', width=1)
    sub_schema.add_field('filter_term', label='Filter Fail', width=2)with sim_filter_service_archive_schema.add_has_many('Metadata', GsiGridSchema) as sub_schema:
    sub_schema.add_field('club', label='Club', width=1)
    sub_schema.add_field('blacklist_sim_ids', label='Blacklist Sim Ids', width=1)
    sub_schema.add_field('optional', label='Optional', width=1)
    sub_schema.add_field('num_sims_seeking', label='Number of Sims Seeking', type=GsiFieldVisualizers.INT, width=1)
    sub_schema.add_field('allow_instanced_sims', label='Allow Instanced Sims', width=1)archiver = GameplayArchiver('sim_filter_service_archive', sim_filter_service_archive_schema)
def archive_filter_request(filter_results, gsi_logging_data):
    entry = {}
    entry['game_time'] = str(services.time_service().sim_now)
    entry['request_type'] = str(gsi_logging_data.request_type)
    entry['yielding'] = str(gsi_logging_data.yielding)
    entry['filter_type'] = str(gsi_logging_data.sim_filter_type)
    entry['matching_results'] = len(filter_results)
    entry['created_sims'] = len(gsi_logging_data.created_sim_infos)
    entry['source'] = gsi_logging_data.gsi_source_fn()
    filter_results_list = []
    for filter_result in filter_results:
        filter_results_list.append({'sim_info': str(filter_result.sim_info), 'score': filter_result.score, 'reason': filter_result.reason, 'filter_tag': str(filter_result.tag)})
    entry['FilterResult'] = filter_results_list
    entry['Created'] = list(gsi_logging_data.created_sim_infos)
    entry['Rejected'] = list(gsi_logging_data.rejected_sim_infos)
    entry['Metadata'] = [{'num_sims_seeking': gsi_logging_data.metadata[0], 'allow_instanced_sims': gsi_logging_data.metadata[1], 'club': gsi_logging_data.metadata[2], 'blacklist_sim_ids': gsi_logging_data.metadata[3], 'optional': gsi_logging_data.metadata[4]}]
    archiver.archive(data=entry)
