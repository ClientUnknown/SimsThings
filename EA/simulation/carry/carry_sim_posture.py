from animation.animation_utils import flush_all_animationsfrom animation.arb import Arbfrom animation.arb_element import distribute_arb_elementfrom animation.posture_manifest import Handfrom carry.carry_postures import CarryingObjectfrom carry.carry_utils import SCRIPT_EVENT_ID_STOP_CARRY, SCRIPT_EVENT_ID_START_CARRYfrom element_utils import build_critical_section, build_critical_section_with_finallyfrom interactions.aop import AffordanceObjectPairfrom interactions.context import InteractionContextfrom interactions.priority import Priorityfrom postures.posture import Posture, TRANSITION_POSTURE_PARAM_NAMEfrom postures.posture_animation_data import AnimationDataByActorAndTargetSpeciesfrom postures.posture_specs import PostureSpecVariable, PostureAspectBody, PostureAspectSurfacefrom postures.posture_state import PostureStatefrom sims4.tuning.tunable import Tunablefrom sims4.tuning.tunable_base import GroupNamesimport element_utilsimport sims4.loglogger = sims4.log.Logger('Carry', default_owner='epanero')
class CarryingSim(CarryingObject):
    INSTANCE_TUNABLES = {'_animation_data': AnimationDataByActorAndTargetSpecies.TunableFactory(animation_data_options={'locked_args': {'_idle_animation': None}, 'is_two_handed_carry': Tunable(description='\n                    If checked, then this is a two-handed carry, and Sims will\n                    not be able to simultaneously run interactions requiring\n                    either hand while in this posture.\n                    ', tunable_type=bool, default=False)}, tuning_group=GroupNames.ANIMATION), 'carried_linked_posture_type': Posture.TunableReference(description='\n            The posture to be linked to this carry. This is the body posture\n            that is set on the carried Sim. The source interaction for this\n            posture is whichever posture providing interaction can be found on\n            the Sim that is doing the carrying.\n            ', tuning_group=GroupNames.POSTURE)}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._carried_linked_posture = None
        self._carried_linked_previous_posture_state = self.target.posture_state
        self._carried_linked_posture_spec = self._carried_linked_previous_posture_state.spec.clone(body=PostureAspectBody((self.carried_linked_posture_type, self.sim)), surface=PostureAspectSurface((None, None, None)))
        self._carried_linked_posture_exit_transition = None

    @property
    def is_two_handed_carry(self):
        animation_data = self.get_animation_data()
        return animation_data.is_two_handed_carry

    def set_carried_linked_posture_exit_transition(self, transition, next_body_posture):
        next_body_posture.previous_posture = self._carried_linked_posture
        self._carried_linked_posture_exit_transition = transition

    def _get_carried_linked_source_interaction(self):
        for super_affordance in self.sim.super_affordances():
            if super_affordance.provided_posture_type is self.carried_linked_posture_type and super_affordance._provided_posture_type_species == self.target.species:
                break
        raise RuntimeError('{} does not provide an appropriate affordance to {}'.format(self.sim, self))
        context = InteractionContext(self.target, InteractionContext.SOURCE_SCRIPT, Priority.Low)
        aop = AffordanceObjectPair(super_affordance, self.sim, super_affordance, None, force_inertial=True)
        result = aop.interaction_factory(context)
        if not result:
            raise RuntimeError("Unable to execute 'Be Carried' posture providing AOP: {} ({})".format(aop, result.reason))
        return result.interaction

    def set_target_linked_posture_data(self):
        posture_state = PostureState(self.target, self._carried_linked_previous_posture_state, self._carried_linked_posture_spec, {PostureSpecVariable.HAND: (Hand.LEFT,)})
        self._carried_linked_posture = posture_state.body
        self._carried_linked_posture.previous_posture = self._carried_linked_previous_posture_state.body
        self._carried_linked_posture.rebind(self.sim, animation_context=self.animation_context)
        self._carried_linked_posture.source_interaction = self._get_carried_linked_source_interaction()
        return posture_state

    def _start_carried_linked_posture_gen(self, timeline):
        posture_state = self.set_target_linked_posture_data()
        self.target.posture_state = posture_state

    def kickstart_linked_carried_posture_gen(self, timeline):
        yield from element_utils.run_child(timeline, (self.target.posture.get_idle_behavior(), flush_all_animations))
        begin_element = self._carried_linked_posture.get_begin(Arb(), self.target.posture_state, self.target.routing_surface)
        yield from element_utils.run_child(timeline, begin_element)
        yield from self._carried_linked_posture.kickstart_source_interaction_gen(timeline)
        yield from element_utils.run_child(timeline, self._carried_linked_previous_posture_state.body.end())

    def _setup_asm_target_for_transition(self, *args, **kwargs):
        result = super()._setup_asm_target_for_transition(*args, **kwargs)
        if self._carried_linked_posture_exit_transition is None:
            transition_posture = self._carried_linked_previous_posture_state.body
        else:
            previous_posture = self._carried_linked_previous_posture_state.body
            (previous_target, previous_target_name) = previous_posture.get_target_and_target_name()
            if previous_target is not None and previous_target_name is not None:
                self.asm.remove_virtual_actor(previous_target_name, previous_target, previous_posture.get_part_suffix())
            transition_posture = self._carried_linked_posture_exit_transition.dest_state.body
        (transition_target, transition_target_name) = transition_posture.get_target_and_target_name()
        if transition_target is not None and transition_target_name is not None:
            self.asm.add_potentially_virtual_actor(self.get_target_name(), self.target, transition_target_name, transition_target)
        self.asm.set_actor_parameter(self.get_target_name(), self.target, TRANSITION_POSTURE_PARAM_NAME, transition_posture.name)
        return result

    def add_transition_extras(self, sequence, **kwargs):
        sequence = super().add_transition_extras(sequence, **kwargs)
        sequence = build_critical_section(self._start_carried_linked_posture_gen, sequence, self.kickstart_linked_carried_posture_gen)
        return sequence

    def append_transition_to_arb(self, arb, *args, in_xevt_handler=False, **kwargs):

        def _on_linked_posture_transition(*_, **__):
            self._carried_linked_posture.append_transition_to_arb(arb, *args, in_xevt_handler=in_xevt_handler, **kwargs)
            if in_xevt_handler:
                self._carried_linked_posture.append_idle_to_arb(arb)

        if in_xevt_handler:
            _on_linked_posture_transition()
        else:
            arb.register_event_handler(_on_linked_posture_transition, handler_id=SCRIPT_EVENT_ID_START_CARRY)
        return super().append_transition_to_arb(arb, *args, in_xevt_handler=in_xevt_handler, **kwargs)

    def append_idle_to_arb(self, arb):
        self._carried_linked_posture.append_idle_to_arb(arb)
        return super().append_idle_to_arb(arb)

    def append_exit_to_arb(self, arb, *args, exit_while_holding=False, **kwargs):
        if self._carried_linked_posture_exit_transition is not None:
            destination_posture = self._carried_linked_posture_exit_transition.dest_state.body
        else:
            destination_posture = None

        def _on_linked_posture_exit(*_, **__):
            linked_arb = Arb()
            self._carried_linked_posture.append_exit_to_arb(linked_arb, *args, **kwargs)
            if destination_posture is not None:
                destination_posture.append_transition_to_arb(linked_arb, self._carried_linked_posture)
                destination_posture.append_idle_to_arb(linked_arb)
            distribute_arb_element(linked_arb, master=self.target)

        arb.register_event_handler(_on_linked_posture_exit, handler_id=SCRIPT_EVENT_ID_STOP_CARRY)
        return super().append_exit_to_arb(arb, *args, exit_while_holding=exit_while_holding, **kwargs)

    def _on_reset(self):
        super()._on_reset()
        if self.target is not None:
            routing_surface = self.target.routing_surface
            self.target.move_to(parent=None, translation=self.sim.position, routing_surface=routing_surface)
