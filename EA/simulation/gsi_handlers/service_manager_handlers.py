from sims4.gsi.dispatcher import GsiHandlerfrom sims4.gsi.schema import GsiGridSchema, GsiFieldVisualizersimport collectionsimport game_servicesimport servicesimport sims4.gsi.archive
class ServiceDetailsArchive(sims4.gsi.archive.BaseArchiver):
    __slots__ = ('_time_counter', '_last_message')

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._time_counter = collections.Counter()
        self._last_message = {}

    def cumulative_time(self, service_type):
        if service_type in self._time_counter:
            return self._time_counter[service_type]
        return 0

    def get_last_message(self, service_type):
        return self._last_message.get(service_type, '')

    def accumulate_time(self, service_type, time_s):
        self._time_counter[service_type] += round(time_s*1000)

    def set_last_message(self, service_type, message):
        self._last_message[service_type] = message

    def clear_archive(self, sim_id=None):
        self._time_counter.clear()
        self._last_message.clear()
service_manager_schema = GsiGridSchema(label='Service Manager')service_manager_schema.add_field('name', label='Name', type=GsiFieldVisualizers.STRING, unique_field=True)service_manager_schema.add_field('category', label='Category', type=GsiFieldVisualizers.STRING)service_manager_schema.add_field('zone_id', label='Zone ID', type=GsiFieldVisualizers.INT)service_manager_schema.add_field('cumulative_time', label='Cumulative Time (ms)', type=GsiFieldVisualizers.INT)service_manager_schema.add_field('last_message', label='Message', type=GsiFieldVisualizers.STRING)
def _custom_archiver_enable_fn(*args, enableLog=False, **kwargs):
    if enableLog:
        sims4.service_manager.set_gsi_reporter(service_manager_archiver)
    else:
        sims4.service_manager.set_gsi_reporter(None)
service_manager_archiver = ServiceDetailsArchive(type_name='service_manager', enable_archive_by_default=True, add_to_archive_enable_functions=True, custom_enable_fn=_custom_archiver_enable_fn)_custom_archiver_enable_fn(enableLog=service_manager_archiver.enabled)
def populate_services(info_list, manager, category, zone_id=0):
    if manager is None:
        return
    for service in manager.services:
        cumulative_time = service_manager_archiver.cumulative_time(type(service))
        last_message = service_manager_archiver.get_last_message(type(service))
        record = {'name': str(service), 'category': category, 'zone_id': zone_id, 'cumulative_time': cumulative_time, 'last_message': last_message}
        info_list.append(record)

@GsiHandler('service_manager', service_manager_schema)
def generate_service_manager_schema_data():
    service_info = []
    populate_services(service_info, sims4.core_services.service_manager, 'Core')
    populate_services(service_info, game_services.service_manager, 'Game')
    zone = services.current_zone()
    if zone is not None:
        populate_services(service_info, zone.service_manager, 'Zone', zone_id=zone.id)
    return service_info

def is_archive_enabled():
    return service_manager_archiver.enabled
