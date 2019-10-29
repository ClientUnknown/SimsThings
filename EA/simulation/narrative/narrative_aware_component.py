from objects.components import Componentfrom objects.components.state import TunableStateValueReferencefrom objects.components.types import NARRATIVE_AWARE_COMPONENTfrom sims4.resources import Typesfrom sims4.tuning.tunable import HasTunableFactory, AutoFactoryInit, TunableMapping, TunableReference, TunableListimport services
class NarrativeAwareComponent(Component, HasTunableFactory, AutoFactoryInit, component_name=NARRATIVE_AWARE_COMPONENT):
    FACTORY_TUNABLES = {'narrative_state_mapping': TunableMapping(description='\n            A tunable mapping linking a narrative to the states the component\n            owner should have.\n            ', key_type=TunableReference(description='\n                The narrative we are interested in.\n                ', manager=services.get_instance_manager(Types.NARRATIVE)), value_type=TunableList(description='\n                A tunable list of states to apply to the owning object of\n                this component when this narrative is active.\n                ', tunable=TunableStateValueReference(pack_safe=True)))}

    def on_add(self):
        self.on_narratives_set(services.narrative_service().active_narratives)

    def on_finalize_load(self):
        self.on_narratives_set(services.narrative_service().active_narratives)

    def on_narratives_set(self, narratives):
        for narrative in narratives:
            if narrative in self.narrative_state_mapping:
                for state_value in self.narrative_state_mapping[narrative]:
                    self.owner.set_state(state_value.state, state_value)
