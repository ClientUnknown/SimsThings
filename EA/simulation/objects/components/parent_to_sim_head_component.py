from protocolbuffers import SimObjectAttributes_pb2from protocolbuffers import SimObjectAttributes_pb2 as protocolsfrom objects import ALL_HIDDEN_REASONSfrom objects.components import typesfrom objects.parenting_utils import SetAsHeadimport objects.componentsimport servicesimport sims4.logimport zone_typeslogger = sims4.log.Logger('ParentToSimHeadComponent', default_owner='camilogarcia')
class ParentToSimHeadComponent(objects.components.Component, allow_dynamic=True, component_name=objects.components.types.PARENT_TO_SIM_HEAD_COMPONENT, persistence_key=SimObjectAttributes_pb2.PersistenceMaster.PersistableData.ParentToSimHeadComponent):

    def __init__(self, *args, parent_sim_info_id=None, bone_hash=None, **kwargs):
        super().__init__(*args, **kwargs)
        self._parent_sim_info_id = parent_sim_info_id
        self._bone_hash = bone_hash

    def __repr__(self):
        return '{} SimId: {} BoneHash: {}'.format(super().__repr__(), self._parent_sim_info_id, self._bone_hash)

    def save(self, persistence_master_message):
        persistable_data = protocols.PersistenceMaster.PersistableData()
        persistable_data.type = protocols.PersistenceMaster.PersistableData.ParentToSimHeadComponent
        head_component_data = persistable_data.Extensions[protocols.PersistableParentToSimHeadComponent.persistable_data]
        if self._parent_sim_info_id is not None:
            head_component_data.parent_sim_info_id = self._parent_sim_info_id
            head_component_data.bone_hash = self.owner.bone_name_hash
        persistence_master_message.data.extend([persistable_data])

    def load(self, persistable_data):
        head_component_data = persistable_data.Extensions[protocols.PersistableParentToSimHeadComponent.persistable_data]
        self._parent_sim_info_id = head_component_data.parent_sim_info_id
        self._bone_hash = head_component_data.bone_hash
        zone = services.current_zone()
        if not zone.is_zone_running:
            zone.register_callback(zone_types.ZoneState.RUNNING, self._on_zone_running_update)

    def _on_zone_running_update(self):
        self._reparent_object()
        services.current_zone().unregister_callback(zone_types.ZoneState.RUNNING, self._on_zone_running_update)

    def _reparent_object(self):
        inventory_owner = self.owner.get_inventory()
        if inventory_owner is not None:
            remove_success = inventory_owner.try_remove_object_by_id(self.owner.id)
            if not remove_success:
                return
        sim_info = services.sim_info_manager().get(self._parent_sim_info_id)
        if sim_info is None:
            self.owner.remove_component(types.PARENT_TO_SIM_HEAD_COMPONENT)
            return
        sim_instance = sim_info.get_sim_instance(allow_hidden_flags=ALL_HIDDEN_REASONS)

        def cleanup():
            self.owner.remove_component(types.PARENT_TO_SIM_HEAD_COMPONENT)
            if sim_instance is not None:
                sim_instance.current_object_set_as_head = None

        if sim_instance is None or not self._bone_hash:
            logger.error('Object {} was saved with an invalid state: {}', self.owner, self)
            cleanup()
            return
        try:
            SetAsHead.set_head_object(sim_instance, self.owner, self._bone_hash)
        except Exception as e:
            logger.error("Failure to parent to {}'s head. Removing ParentToSimHeadComponent. ({})\nException:{}", sim_instance, self, e)
            cleanup()
