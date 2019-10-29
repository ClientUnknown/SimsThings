from protocolbuffers import SimObjectAttributes_pb2 as protocols
class ObjectClaimComponent(Component, HasTunableFactory, AutoFactoryInit, component_name=types.OBJECT_CLAIM_COMPONENT, persistence_key=protocols.PersistenceMaster.PersistableData.ObjectClaimComponent, allow_dynamic=True):
    FACTORY_TUNABLES = {}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._claim_status = ObjectClaimStatus.UNCLAIMED
        self._requires_claiming = False

    def has_not_been_reclaimed(self):
        return services.object_manager().has_object_failed_claiming(self.owner)

    @property
    def requires_claiming(self):
        return self._requires_claiming

    def claim(self):
        self._claim_status = ObjectClaimStatus.CLAIMED

    def save(self, persistence_master_message):
        persistable_data = protocols.PersistenceMaster.PersistableData()
        persistable_data.type = protocols.PersistenceMaster.PersistableData.ObjectClaimComponent
        object_claim_save = persistable_data.Extensions[protocols.PersistableObjectClaimComponent.persistable_data]
        if self._claim_status == ObjectClaimStatus.CLAIMED:
            object_claim_save.requires_claiming = True
        else:
            object_claim_save.requires_claiming = False
        persistence_master_message.data.extend([persistable_data])

    def load(self, message):
        data = message.Extensions[protocols.PersistableObjectClaimComponent.persistable_data]
        self._requires_claiming = data.requires_claiming
