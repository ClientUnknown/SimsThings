from objects.components import Componentfrom objects.components.types import PORTAL_ANIMATION_COMPONENTfrom sims4.tuning.tunable import AutoFactoryInit, HasTunableFactory, TunableInteractionAsmResourceKey, TunableVariantfrom distributor.fields import ComponentField, Fieldfrom distributor.ops import SetActorType, SetActorStateMachine
class PortalAnimationComponent(Component, HasTunableFactory, AutoFactoryInit, component_name=PORTAL_ANIMATION_COMPONENT):
    FACTORY_TUNABLES = {'_portal_asm': TunableInteractionAsmResourceKey(description='\n            The animation to use for this portal.\n            '), '_portal_actor_type': TunableVariant(description='\n            The animation actor type for this portal. This defines client-side\n            behavior.\n            ', locked_args={'door': 2935391323}, default='door')}

    @ComponentField(op=SetActorStateMachine)
    def portal_asm(self):
        return self._portal_asm

    @ComponentField(op=SetActorType, priority=Field.Priority.HIGH)
    def portal_actor_type(self):
        return self._portal_actor_type
