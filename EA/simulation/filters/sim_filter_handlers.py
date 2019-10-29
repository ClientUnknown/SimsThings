from gsi_handlers.gameplay_archiver import GameplayArchiverfrom sims4.gsi.schema import GsiGridSchema, GsiFieldVisualizers
class SimFilterGSILoggingData:

    def __init__(self, request_type, sim_filter_type, gsi_source_fn):
        self.request_type = request_type
        self.sim_filter_type = sim_filter_type
        self.gsi_source_fn = gsi_source_fn
        self.filters = {}

    def add_filter(self, filter_term, score):
        self.filters[filter_term] = score
sim_filter_archive_schema = GsiGridSchema(label='Sim Filter Archive', sim_specific=True)sim_filter_archive_schema.add_field('sim_id', label='simID', type=GsiFieldVisualizers.INT, hidden=True)sim_filter_archive_schema.add_field('source', label='Source', width=3)sim_filter_archive_schema.add_field('request_type', label='Request Type')sim_filter_archive_schema.add_field('filter_type', label='Filter Type', width=2.5)sim_filter_archive_schema.add_field('rejected', label='Is Rejected', width=1)sim_filter_archive_schema.add_field('reason', label='Reason', width=1)with sim_filter_archive_schema.add_has_many('Filter Breakdown', GsiGridSchema) as sub_schema:
    sub_schema.add_field('filter', label='Filter', width=1)
    sub_schema.add_field('score', label='Score', width=1)archiver = GameplayArchiver('sim_filter', sim_filter_archive_schema)
def archive_filter_request(sim_info, gsi_logging_data, *, rejected, reason):
    entry = {}
    entry['sim_id'] = sim_info.id
    entry['request_type'] = str(gsi_logging_data.request_type)
    entry['source'] = gsi_logging_data.gsi_source_fn()
    entry['filter_type'] = str(gsi_logging_data.sim_filter_type)
    entry['rejected'] = rejected
    entry['reason'] = reason
    filter_list = []
    for (key, value) in gsi_logging_data.filters.items():
        filter_list = [{'filter': key, 'score': value} for (key, value) in gsi_logging_data.filters.items()]
    entry['Filter Breakdown'] = filter_list
    archiver.archive(data=entry, object_id=sim_info.id)
