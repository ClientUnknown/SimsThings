import operatorfrom protocolbuffers import UI_pb2, DistributorOps_pb2from audio.primitive import play_tunable_audiofrom careers.prep_tasks.linked_statistic_updater import LinkedStatisticUpdaterfrom distributor.ops import Opfrom distributor.rollback import ProtocolBufferRollbackfrom distributor.system import Distributorfrom sims4.math import Thresholdimport servicesimport sims4.resourcesprotocol_constants = DistributorOps_pb2.Operationlogger = sims4.log.Logger('Prep Tasks', default_owner='jdimailig')
class PrepTaskUpdateOp(Op):

    def __init__(self, sim_info, gig_uid, prep_tasks):
        super().__init__()
        msg = UI_pb2.PrepTaskUpdate()
        msg.sim_id = sim_info.sim_id
        msg.gig_uid = gig_uid
        for task in prep_tasks:
            with ProtocolBufferRollback(msg.prep_tasks) as task_data:
                task_data.task_name = task.get_prep_task_display_name(sim_info)
                task_data.task_icon = sims4.resources.get_protobuff_for_key(task.task_icon)
                task_data.is_completed = task.is_completed(sim_info)
                if task.task_tooltip is not None:
                    task_data.task_tooltip = task.task_tooltip()
        self._op_msg = msg

    def write(self, msg):
        self.serialize_op(msg, self._op_msg, protocol_constants.UPDATE_PREP_TASKS)

class PrepTaskTracker:

    def __init__(self, sim_info, gig_uid, prep_tasks, audio_on_task_complete):
        self._sim_info = sim_info
        self._gig_uid = gig_uid
        self._prep_tasks = prep_tasks
        self._prep_task_statistic_listeners = []
        self._linked_statistic_updaters = []
        self._audio_on_task_complete = audio_on_task_complete

    def on_prep_time_start(self):
        for prep_task in self._prep_tasks:
            self._sim_info.get_statistic(prep_task.statistic, add=True)
        self._add_prep_task_statistic_change_listeners()
        self._setup_linked_stat_updaters()
        self.send_prep_task_update()

    def on_prep_time_end(self):
        self._cleanup_listeners()

    def cleanup_prep_statistics(self):
        self._cleanup_listeners()
        for prep_task in self._prep_tasks:
            self._sim_info.remove_statistic(prep_task.statistic)

    def _cleanup_listeners(self):
        self._remove_prep_task_statistic_change_listeners()
        self._remove_linked_stat_updaters()

    def send_prep_task_update(self):
        if services.current_zone().is_zone_shutting_down or not self._sim_info.valid_for_distribution:
            return
        update_op = PrepTaskUpdateOp(self._sim_info, self._gig_uid, self._prep_tasks)
        Distributor.instance().add_op(self._sim_info, update_op)

    def _on_prep_task_statistic_change(self, stat_inst):
        if self._audio_on_task_complete is not None:
            sim = self._sim_info.get_sim_instance()
            if sim is not None:
                play_audio = any(prep_task.statistic is type(stat_inst) and prep_task.is_completed(self._sim_info) for prep_task in self._prep_tasks)
                if play_audio:
                    play_tunable_audio(self._audio_on_task_complete, owner=sim)
        self.send_prep_task_update()
        self._refresh_prep_task_statistic_change_listeners()

    def _refresh_prep_task_statistic_change_listeners(self):
        self._remove_prep_task_statistic_change_listeners()
        self._add_prep_task_statistic_change_listeners()

    def _setup_linked_stat_updaters(self):
        for prep_task in self._prep_tasks:
            for updater in self._create_linked_statistic_updaters(self._sim_info, prep_task):
                self._linked_statistic_updaters.append(updater)
                updater.setup_watcher()

    def _remove_linked_stat_updaters(self):
        for updater in self._linked_statistic_updaters:
            updater.remove_watcher()
        self._linked_statistic_updaters.clear()

    def _add_prep_task_statistic_change_listeners(self):
        for prep_task in self._prep_tasks:
            task_stat = prep_task.statistic
            tracker = self._sim_info.get_tracker(task_stat)
            (lower_threshold, upper_threshold) = prep_task.get_prep_task_progress_thresholds(self._sim_info)
            if lower_threshold:
                threshold = Threshold(lower_threshold.threshold, operator.lt)
                handle = tracker.create_and_add_listener(task_stat, threshold, self._on_prep_task_statistic_change)
                self._prep_task_statistic_listeners.append((task_stat, handle))
            if upper_threshold:
                threshold = Threshold(upper_threshold.threshold, operator.ge)
                handle = tracker.create_and_add_listener(task_stat, threshold, self._on_prep_task_statistic_change)
                self._prep_task_statistic_listeners.append((task_stat, handle))

    def _remove_prep_task_statistic_change_listeners(self):
        for (stat_type, handle) in self._prep_task_statistic_listeners:
            tracker = self._sim_info.get_tracker(stat_type)
            tracker.remove_listener(handle)
        self._prep_task_statistic_listeners.clear()

    def _create_linked_statistic_updaters(self, sim_info, prep_task):
        updaters = []
        for linked_statistic in prep_task.linked_statistics:
            updaters.append(LinkedStatisticUpdater(sim_info, prep_task.statistic, linked_statistic.stat_type, linked_statistic.multiplier))
        return updaters
