from protocolbuffers import SimObjectAttributes_pb2 as protocolsfrom objects.gardening.gardening_component import _GardeningComponentimport objects.components.types
class GardeningShootComponent(_GardeningComponent, component_name=objects.components.types.GARDENING_COMPONENT, persistence_key=protocols.PersistenceMaster.PersistableData.GardeningComponent):

    @property
    def is_shoot(self):
        return True
