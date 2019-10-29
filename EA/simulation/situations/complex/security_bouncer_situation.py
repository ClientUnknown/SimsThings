from event_testing.resolver import SingleActorAndObjectResolver, SingleSimResolver, SingleObjectResolverfrom interactions.utils.loot import LootActionsfrom objects.components.portal_lock_data import LockAllWithSimIdExceptionDatafrom objects.components.portal_locking_enums import LockType, ClearLock, LockPriority, LockSidefrom sims4.tuning.tunable import TunableListfrom sims4.tuning.tunable_base import GroupNamesfrom situations.ambient.tend_object_situation import TendObjectSituationimport sims4.loglogger = sims4.log.Logger('SecurityBouncerSituation', default_owner='mkartika')EXCEPTION_SIM_ID_LIST_TOKEN = 'sim_id_list'
class SecurityBouncerSituation(TendObjectSituation):
    INSTANCE_TUNABLES = {'_loots_on_create': TunableList(description='\n            Loot Actions that will be applied to staffed object in this \n            situation on situation create.\n            ', tunable=LootActions.TunableReference(), tuning_group=GroupNames.SPECIAL_CASES), '_loots_on_set_sim_job': TunableList(description='\n            Loot Actions that will be applied to a sim and staffed object in \n            this situation when the sim has been assigned a job.\n            ', tunable=LootActions.TunableReference(), tuning_group=GroupNames.SPECIAL_CASES), '_loots_on_remove_sim_from_situation': TunableList(description='\n            Loot Actions that will be applied to a sim and staffed object in \n            this situation when the sim is removed from situation.\n            ', tunable=LootActions.TunableReference(), tuning_group=GroupNames.SPECIAL_CASES), '_loots_on_destroy': TunableList(description='\n            Loot Actions that will be applied to staff member and staffed \n            object in this situation on situation destroy.\n            ', tunable=LootActions.TunableReference(), tuning_group=GroupNames.SPECIAL_CASES)}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._except_sim_ids = None
        self._persisted_sim_id = None
        self._load_sim_id_exception_lock_data()
        self._apply_loots(self._loots_on_create)

    def _on_set_sim_job(self, sim, job_type):
        super()._on_set_sim_job(sim, job_type)
        self._apply_loots(self._loots_on_set_sim_job)
        if self._persisted_sim_id is not None:
            if self._persisted_sim_id == sim.sim_id:
                self._apply_sim_id_exception_lock_data()
            self._persisted_sim_id = None

    def _on_remove_sim_from_situation(self, sim):
        if sim is self._staff_member:
            self._apply_loots(self._loots_on_remove_sim_from_situation)
        super()._on_remove_sim_from_situation(sim)

    def _destroy(self):
        self._apply_loots(self._loots_on_destroy)
        super()._destroy()

    def _apply_loots(self, loots):
        sim_info = None if self._staff_member is None else self._staff_member.sim_info
        obj = self._staffed_object
        if sim_info is not None:
            if obj is not None:
                resolver = SingleActorAndObjectResolver(sim_info, obj, self)
            else:
                resolver = SingleSimResolver(sim_info)
        elif obj is not None:
            resolver = SingleObjectResolver(obj)
        else:
            return
        for loot_action in loots:
            loot_action.apply_to_resolver(resolver)

    def load_situation(self):
        persisted_guest_info = next(iter(self._guest_list.get_persisted_sim_guest_infos()), None)
        if persisted_guest_info is not None:
            self._persisted_sim_id = persisted_guest_info.sim_id
        return super().load_situation()

    def _load_sim_id_exception_lock_data(self):
        reader = self._seed.custom_init_params_reader
        if reader is None:
            return
        self._except_sim_ids = reader.read_uint64s(EXCEPTION_SIM_ID_LIST_TOKEN, None)

    def _apply_sim_id_exception_lock_data(self):
        if self._staffed_object is None:
            return
        if not self._except_sim_ids:
            return
        lock_data = LockAllWithSimIdExceptionData(lock_priority=LockPriority.PLAYER_LOCK, lock_sides=LockSide.LOCK_FRONT, should_persist=False, except_actor=False, except_household=False)
        lock_data.except_sim_ids = self._except_sim_ids
        self._staffed_object.add_lock_data(lock_data, clear_existing_locks=ClearLock.CLEAR_NONE)

    def _save_sim_id_exception_lock_data(self, writer):
        if self._staffed_object is None:
            return
        portal_locking_component = self._staffed_object.portal_locking_component
        if portal_locking_component is None:
            return
        lock_datas = portal_locking_component.lock_datas
        if LockType.LOCK_ALL_WITH_SIMID_EXCEPTION not in lock_datas:
            return
        except_sim_ids = lock_datas[LockType.LOCK_ALL_WITH_SIMID_EXCEPTION].except_sim_ids
        writer.write_uint64s(EXCEPTION_SIM_ID_LIST_TOKEN, except_sim_ids)

    def _save_custom_situation(self, writer):
        super()._save_custom_situation(writer)
        self._save_sim_id_exception_lock_data(writer)
