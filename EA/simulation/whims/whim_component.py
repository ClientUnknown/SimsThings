from objects.components import Componentfrom objects.components.types import WHIM_COMPONENTfrom sims4.tuning.tunable import HasTunableFactory, AutoFactoryInit, TunableReferenceimport servicesimport sims4.resources
class WhimComponent(Component, HasTunableFactory, AutoFactoryInit, component_name=WHIM_COMPONENT):
    FACTORY_TUNABLES = {'whim_set': TunableReference(description='\n            The whim set that is active when this object is on the lot.\n            ', manager=services.get_instance_manager(sims4.resources.Types.ASPIRATION), class_restrictions=('ObjectivelessWhimSet',))}

    def on_add(self):
        self.owner.manager.add_active_whim_set(self.whim_set)

    def on_remove(self):
        self.owner.manager.remove_active_whim_set(self.whim_set)
