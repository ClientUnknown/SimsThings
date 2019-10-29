from protocolbuffers import Routing_pb2 as routing_protocolsfrom animation import get_throwaway_animation_context, animation_constantsfrom animation.animation_utils import StubActorfrom animation.arb import Arbfrom animation.asm import create_asmfrom routing.portals.portal_data_locomotion import _PortalTypeDataLocomotionfrom routing.portals.portal_tuning import PortalTypefrom sims4.tuning.tunable import TunableReferenceimport servicesimport sims4
class _PortalTypeDataVariableJump(_PortalTypeDataLocomotion):
    FACTORY_TUNABLES = {'animation_element': TunableReference(description='\n            The animation to play when a Sim traverses this portal.\n            ', manager=services.get_instance_manager(sims4.resources.Types.ANIMATION))}

    @property
    def portal_type(self):
        return PortalType.PortalType_Animate

    def _get_arb(self, actor, portal_instance, *, is_mirrored):
        arb = Arb()
        asm = create_asm(self.animation_element.asm_key, context=get_throwaway_animation_context())
        asm.set_actor(self.animation_element.actor_name, actor)
        if is_mirrored:
            entry_location = portal_instance.back_entry
            exit_location = portal_instance.back_exit
        else:
            entry_location = portal_instance.there_entry
            exit_location = portal_instance.there_exit
        asm.set_actor_parameter(self.animation_element.actor_name, actor, 'InitialTranslation', entry_location.position)
        asm.set_actor_parameter(self.animation_element.actor_name, actor, 'InitialOrientation', entry_location.orientation)
        asm.set_actor_parameter(self.animation_element.actor_name, actor, animation_constants.ASM_TARGET_TRANSLATION, exit_location.position)
        asm.set_actor_parameter(self.animation_element.actor_name, actor, animation_constants.ASM_TARGET_ORIENTATION, entry_location.orientation)
        self.animation_element.append_to_arb(asm, arb)
        return arb

    def add_portal_data(self, actor, portal_instance, is_mirrored, walkstyle):
        arb = self._get_arb(actor, portal_instance, is_mirrored=is_mirrored)
        op = routing_protocols.RouteAnimateData()
        op.arb_data = arb._bytes()
        node_data = routing_protocols.RouteNodeData()
        node_data.type = routing_protocols.RouteNodeData.DATA_ANIMATE
        node_data.data = op.SerializeToString()
        return node_data

    def get_portal_duration(self, portal_instance, is_mirrored, walkstyle, age, gender, species):
        actor = StubActor(1, species=species)
        arb = self._get_arb(actor, portal_instance, is_mirrored=is_mirrored)
        (_, duration, _) = arb.get_timing()
        return duration
