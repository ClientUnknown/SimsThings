import randomfrom sims4.tuning.tunable import TunableList, TunableReferenceimport servicesimport sims4logger = sims4.log.Logger('SuntannerSituation', default_owner='msundaram')
class GiveJobObjectSituationMixin:
    OBJECT_TOKEN = 'situation_created_object_id'
    OBJECT_OWNER_TOKEN = 'situation_object_owner_id'
    INSTANCE_TUNABLES = {'objects_to_create': TunableList(description='\n            A list of object definitions to choose from to spawn an object\n            when the sim is assigned a job.\n            ', tunable=TunableReference(description='\n                An object to create.\n                ', manager=services.definition_manager()), unique_entries=True)}

    def __init__(self, *arg, **kwargs):
        super().__init__(*arg, **kwargs)
        reader = self._seed.custom_init_params_reader
        self._object_ids = self._load_objects(reader, self.OBJECT_TOKEN, self.OBJECT_OWNER_TOKEN)

    def _load_objects(self, reader, obj_token, owner_token):
        ids = dict()
        if reader is None:
            return ids
        obj_ids = reader.read_uint64s(obj_token, None)
        owner_ids = reader.read_uint64s(owner_token, None)
        for (obj_id, owner_id) in zip(obj_ids, owner_ids):
            if obj_id is None:
                logger.warn('{} failed to load saved object for sim with id {}: object id is None. Likely the save file is corrupted.', type(self), owner_id)
            elif owner_id is None:
                logger.warn('{} failed to load saved object with object id {}: sim id is None. Likely the save file is corrupted.', type(self), obj_id)
            elif not services.sim_info_manager().is_sim_id_valid(owner_id):
                logger.warn('{} failed to load saved object with object id {}: sim with id {} has been culled', type(self), obj_id, owner_id)
            else:
                self._claim_object(obj_id)
                ids[owner_id] = obj_id
        return ids

    def _spawn_object_for_sim(self, sim):
        if sim.id in self._object_ids:
            return
        object_to_create = random.choice(self.objects_to_create)
        target = self._create_object_for_situation(sim, object_to_create)
        if target is not None:
            self._object_ids[sim.id] = target.id

    def _remove_object_for_sim(self, sim):
        if sim is None:
            logger.error('{} cannot remove object from sim. Sim is None', type(self))
            return
        if sim.id not in self._object_ids:
            logger.error('{} attempting to remove object from {} who does not have a stored object.', type(self), sim)
            return
        self._remove_object(self._object_ids[sim.id])
        self._object_ids.pop(sim.id, None)

    def _remove_object(self, obj_id):
        obj = services.object_manager().get(obj_id)
        if obj is None:
            obj = services.inventory_manager().get(obj_id)
            if obj is None:
                logger.error('{} cannot remove object. Object with id {} is not in Object or Inventory Manager', type(self), obj_id)
                return
        obj.make_transient()

    def _on_set_sim_job(self, sim, job_type):
        super()._on_set_sim_job(sim, job_type)
        self._spawn_object_for_sim(sim)

    def _on_remove_sim_from_situation(self, sim):
        super()._on_remove_sim_from_situation(sim)
        if not self._object_ids:
            return
        self._remove_object_for_sim(sim)

    def _destroy(self):
        super()._destroy()
        if not self._object_ids:
            return
        for obj_id in self._object_ids.values():
            self._remove_object(obj_id)
        self._object_ids.clear()

    def _save_custom_situation(self, writer):
        super()._save_custom_situation(writer)
        if not self._object_ids:
            return
        writer.write_uint64s(self.OBJECT_TOKEN, self._object_ids.values())
        writer.write_uint64s(self.OBJECT_OWNER_TOKEN, self._object_ids.keys())
