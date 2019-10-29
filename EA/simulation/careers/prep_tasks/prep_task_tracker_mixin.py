from careers.prep_tasks.prep_tasks_tracker import PrepTaskTrackerimport sims4.loglogger = sims4.log.Logger('Prep Tasks', default_owner='jdimailig')
class PrepTaskTrackerMixin:

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._prep_task_tracker = None

    def prep_time_start(self, owning_sim_info, prep_tasks, gig_uid, audio_on_task_complete):
        if self._prep_task_tracker is not None:
            logger.error('Attempting to start prep task time when tracker is already populated.')
            self._prep_task_tracker.on_prep_time_end()
            self._prep_task_tracker.cleanup_prep_statistics()
        self._prep_task_tracker = PrepTaskTracker(owning_sim_info, gig_uid, prep_tasks, audio_on_task_complete)
        self._prep_task_tracker.on_prep_time_start()

    def prep_time_end(self):
        if self._prep_task_tracker is not None:
            self._prep_task_tracker.on_prep_time_end()

    def prep_task_cleanup(self):
        if self._prep_task_tracker is not None:
            self._prep_task_tracker.cleanup_prep_statistics()
            self._prep_task_tracker = None
