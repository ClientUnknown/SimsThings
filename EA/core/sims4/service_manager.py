import refrom sims4.common import is_available_pack, Packfrom sims4.utils import classpropertyimport persistence_error_typesimport sims4.logimport sims4.perf_logimport sims4.profiler_utilsimport sims4.reloadwith sims4.reload.protected(globals()):
    _gsi_reporter = None
def set_gsi_reporter(reporter):
    global _gsi_reporter
    _gsi_reporter = reporter
logger = sims4.log.Logger('Services', default_owner='manus')perf_logger = sims4.perf_log.get_logger('ServicePerf', default_owner='pingebretson')PERF_FINISHED_MSG = 'Service {1} {2} finished after {0:f} seconds'PERF_INCREMENTAL_FINISHED_MSG = 'Incremental service {1} {2} finished after {0:f} seconds'PERF_ERROR_MSG = 'Service {1} {2} interrupted by exception after {0:f} seconds'LOG_THRESHOLD_SECONDS = 0.0001
class Service:

    def setup(self, gameplay_zone_data=None, save_slot_data=None):
        pass

    @classproperty
    def required_packs(cls):
        return (Pack.BASE_GAME,)

    @classproperty
    def save_error_code(cls):
        return persistence_error_types.ErrorCodes.GENERIC_ERROR

    def start(self):
        pass

    def stop(self):
        pass

    def pre_save(self):
        pass

    def save(self, object_list=None, zone_data=None, open_street_data=None, store_travel_group_placed_objects=False, save_slot_data=None):
        pass

    def load(self, zone_data=None):
        pass

    def save_options(self, options_proto):
        pass

    def load_options(self, options_proto):
        pass

    def on_client_connect(self, client):
        pass

    def on_client_disconnect(self, client):
        pass

    def on_zone_load(self):
        pass

    def on_zone_unload(self):
        pass

    def on_all_households_and_sim_infos_loaded(self, client):
        pass

    def on_cleanup_zone_objects(self, client):
        pass

    def on_sim_reset(self, sim):
        pass

    @property
    def can_incremental_start(self):
        return False

    def update_incremental_start(self):
        pass

    def get_zone_variable_name(self):
        return re.sub('(?<!^)(?=[A-Z])', '_', type(self).__name__).lower()

    def get_buckets_for_memory_tracking(self):
        return (self,)

    def __str__(self):
        return self.get_zone_variable_name()

class ServiceManager:

    def __init__(self):
        self.services = []
        self._init_critical_services = []
        self._services_to_start = []
        self._incremental_start_in_progress = False
        self._should_profile = sims4.perf_log.profile_logging_enabled('ServicePerf')
        self._TimedContext = sims4.profiler_utils.get_timed_context(self._should_profile)
        self._start_context = self._TimedContext()

    def register_service(self, service, is_init_critical=False):
        required_packs = service.required_packs
        if any(not is_available_pack(pack) for pack in required_packs):
            return False
        if not isinstance(service, Service):
            service = service()
        self.services.append(service)
        if is_init_critical:
            self._init_critical_services.append(service)

    def start_services(self, zone=None, container=None, gameplay_zone_data=None, save_slot_data=None, defer_start_to_tick=False):
        for service in self.services:
            if container is not None:
                setattr(container, service.get_zone_variable_name(), service)
            try:
                service.setup(gameplay_zone_data=gameplay_zone_data, save_slot_data=save_slot_data)
            except:
                logger.exception('Setup error for service {}. This will likely cause additional errors in the future.', service)
        logger.info('Starting all services. zone: {}. defer: {}.', zone, defer_start_to_tick)

        def _start_service(services):
            for service in services:
                try:
                    with self._start_context:
                        service.start()
                    self._perf_log(self._start_context, PERF_FINISHED_MSG, service, 'start')
                except:
                    logger.exception('Startup error for service {}. This will likely cause additional errors in the future.', service)
                    self._perf_log(self._start_context, PERF_ERROR_MSG, service, 'start')
                finally:
                    self._start_context.reset()

        if defer_start_to_tick:
            self._services_to_start = [service for service in self.services if service not in self._init_critical_services]
            _start_service(self._init_critical_services)
            logger.info('Defer {} services to load separately.', len(self._services_to_start))
        else:
            _start_service(self.services)

    def start_single_service(self):
        if not self._services_to_start:
            return True
        else:
            service = self._services_to_start[0]
            try:
                logger.info('Starting Service: {}. Pending services count: {}.', service, len(self._services_to_start))
                if self._incremental_start_in_progress:
                    with self._start_context:
                        result = service.update_incremental_start()
                    if result:
                        self._incremental_start_in_progress = False
                        self._services_to_start.pop(0)
                        self._perf_log(self._start_context, PERF_INCREMENTAL_FINISHED_MSG, service, 'start')
                        self._start_context.reset()
                    else:
                        logger.info('Incremental start in progress for service: {}.', service)
                else:
                    with self._start_context:
                        service.start()
                    if service.can_incremental_start:
                        self._incremental_start_in_progress = True
                    else:
                        self._services_to_start.pop(0)
                        self._perf_log(self._start_context, PERF_FINISHED_MSG, service, 'start')
                        self._start_context.reset()
            except Exception:
                logger.exception('Error during initialization of service {}. This will likely cause additional errors in the future.', service)
                self._incremental_start_in_progress = False
                self._services_to_start.pop(0)
                self._perf_log(self._start_context, PERF_ERROR_MSG, service, 'start')
                self._start_context.reset()
            if not self._services_to_start:
                return True
        return False

    def stop_services(self, zone=None):
        logger.debug('stop_services')
        while self.services:
            service = self.services.pop()
            logger.debug('Shutting Down Service: {}', service)
            context = self._TimedContext()
            try:
                with context:
                    service.stop()
                self._perf_log(context, PERF_FINISHED_MSG, service, 'stop')
            except Exception:
                logger.exception('Error during shutdown of service {}. This will likely cause additional errors in the future.', service)
                self._perf_log(context, PERF_ERROR_MSG, service, 'stop')
            if zone is not None:
                setattr(zone, service.get_zone_variable_name(), None)

    def on_client_connect(self, client):
        for service in self.services:
            context = self._TimedContext()
            try:
                with context:
                    service.on_client_connect(client)
                self._perf_log(context, PERF_FINISHED_MSG, service, 'on_client_connect')
            except Exception:
                logger.exception('{} failed to handle client connection due to exception', service)
                self._perf_log(context, PERF_ERROR_MSG, service, 'on_client_connect')

    def on_client_disconnect(self, client):
        for service in self.services:
            context = self._TimedContext()
            try:
                with context:
                    service.on_client_disconnect(client)
                self._perf_log(context, PERF_FINISHED_MSG, service, 'on_client_disconnect')
            except Exception:
                logger.exception('{} failed to handle client disconnect due to exception', service)
                self._perf_log(context, PERF_ERROR_MSG, service, 'on_client_disconnect')

    def on_zone_load(self):
        for service in self.services:
            context = self._TimedContext()
            try:
                with context:
                    service.on_zone_load()
                self._perf_log(context, PERF_FINISHED_MSG, service, 'on_zone_load')
            except Exception:
                logger.exception('{} failed to handle zone load due to exception', service)
                self._perf_log(context, PERF_ERROR_MSG, service, 'on_zone_load')

    def on_zone_unload(self):
        for service in self.services:
            context = self._TimedContext()
            try:
                with context:
                    service.on_zone_unload()
                self._perf_log(context, PERF_FINISHED_MSG, service, 'on_zone_unload')
            except Exception:
                logger.exception('{} failed to handle zone unload due to exception', service)
                self._perf_log(context, PERF_ERROR_MSG, service, 'on_zone_unload')

    def on_all_households_and_sim_infos_loaded(self, client):
        for service in self.services:
            context = self._TimedContext()
            try:
                with context:
                    service.on_all_households_and_sim_infos_loaded(client)
                self._perf_log(context, PERF_FINISHED_MSG, service, 'on_all_households_and_sim_infos_loaded')
            except Exception:
                logger.exception('{} failed to handle on_all_households_and_sim_infos_loaded due to exception', service)
                self._perf_log(context, PERF_ERROR_MSG, service, 'on_all_households_and_sim_infos_loaded')

    def on_cleanup_zone_objects(self, client):
        for service in self.services:
            context = self._TimedContext()
            try:
                with context:
                    service.on_cleanup_zone_objects(client)
                self._perf_log(context, PERF_FINISHED_MSG, service, 'on_cleanup_zone_objects')
            except Exception:
                logger.exception('{} failed to handle on_cleanup_zone_objects due to exception', service)
                self._perf_log(context, PERF_ERROR_MSG, service, 'on_cleanup_zone_objects')

    def on_sim_reset(self, sim):
        for service in self.services:
            context = self._TimedContext()
            try:
                with context:
                    service.on_sim_reset(sim)
                self._perf_log(context, PERF_FINISHED_MSG, service, 'on_sim_reset')
            except Exception:
                logger.exception('{} failed to handle on_sim_reset for {}, due to exception.', service, sim)
                self._perf_log(context, PERF_ERROR_MSG, service, 'on_sim_reset')

    def save_all_services(self, persistence_service, **kwargs):
        initial_persistence_error_code = persistence_service.save_error_code if persistence_service is not None else None
        for service in reversed(self.services):
            context = self._TimedContext()
            try:
                with context:
                    service.pre_save()
                self._perf_log(context, PERF_FINISHED_MSG, service, 'pre_save')
            except BaseException:
                if initial_persistence_error_code == persistence_service.save_error_code:
                    persistence_service.save_error_code = service.save_error_code
                self._perf_log(context, PERF_ERROR_MSG, service, 'pre_save')
                raise
        for service in reversed(self.services):
            context = self._TimedContext()
            try:
                with context:
                    service.save(**kwargs)
                self._perf_log(context, PERF_FINISHED_MSG, service, 'save')
            except BaseException:
                if initial_persistence_error_code == persistence_service.save_error_code:
                    persistence_service.save_error_code = service.save_error_code
                self._perf_log(context, PERF_ERROR_MSG, service, 'save')
                raise

    def load_all_services(self, zone_data=None):
        for service in self.services:
            context = self._TimedContext()
            with context:
                service.load(zone_data=zone_data)
            self._perf_log(context, PERF_FINISHED_MSG, service, 'load')

    def save_options(self, options_proto):
        for service in self.services:
            context = self._TimedContext()
            with context:
                service.save_options(options_proto)
            self._perf_log(context, PERF_FINISHED_MSG, service, 'save_options')

    def load_options(self, options_proto):
        for service in self.services:
            context = self._TimedContext()
            try:
                with context:
                    service.load_options(options_proto)
                self._perf_log(context, PERF_FINISHED_MSG, service, 'load_options')
            except:
                logger.exception('Failed to load options for {}', service)
                self._perf_log(context, PERF_ERROR_MSG, service, 'load_options')

    def _perf_log(self, context, message, service, fn_name):
        if self._should_profile:
            if context.elapsed_seconds >= LOG_THRESHOLD_SECONDS:
                perf_logger.info(message, context.elapsed_seconds, service, fn_name)
            else:
                perf_logger.debug(message, context.elapsed_seconds, service, fn_name)
        if _gsi_reporter is not None and _gsi_reporter.enabled:
            service_type = type(service)
            _gsi_reporter.accumulate_time(service_type, context.elapsed_seconds)
            msg = message.format(context.elapsed_seconds, service, fn_name)
            _gsi_reporter.set_last_message(service_type, msg)
