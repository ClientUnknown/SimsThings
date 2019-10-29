from animation.arb import Arbfrom animation.arb_element import distribute_arb_elementfrom carry.carry_elements import exit_carry_while_holdingfrom element_utils import build_element, build_critical_section_with_finallyfrom interactions.constraints import GLOBAL_STUB_CARRY_TARGETfrom routing.route_events.route_event_type_create_carry import _RouteEventTypeCarryfrom sims4.tuning.tunable import TunableEnumWithFilterfrom tag import Tagimport servicesimport sims4.loglogger = sims4.log.Logger('RouteEvents', default_owner='bosee')
class RouteEventTypeExitCarry(_RouteEventTypeCarry):
    FACTORY_TUNABLES = {'stop_carry_object_tag': TunableEnumWithFilter(description='\n            Tag used to find the object to stop carrying.\n            ', tunable_type=Tag, default=Tag.INVALID, invalid_enums=(Tag.INVALID,), filter_prefixes=('func',))}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._owned_object = None
        self._actually_run_prepare = self._duration_override is None
        self._override_valid_for_scheduling = not self._actually_run_prepare

    @classmethod
    def test(cls, actor, event_data_tuning):
        return super().test(actor, event_data_tuning, ignore_carry=True)

    def prepare(self, actor):
        if not self._actually_run_prepare:
            self._actually_run_prepare = True
            return True

        def set_target(asm):
            asm.set_current_state('entry')
            asm.set_actor(self.animation_element.actor_name, actor)
            asm.set_actor(self.animation_element.target_name, GLOBAL_STUB_CARRY_TARGET)
            return True

        super().prepare(actor, setup_asm_override=set_target)

    def is_valid_for_scheduling(self, actor, path):
        if self._override_valid_for_scheduling:
            return True
        return super().is_valid_for_scheduling(actor, path)

    def should_remove_on_execute(self):
        return False

    def _execute_internal(self, actor):
        left_carry_target = actor.posture_state.left.target
        right_carry_target = actor.posture_state.right.target
        carry_target = None
        if left_carry_target is not None and left_carry_target.has_tag(self.stop_carry_object_tag):
            carry_target = left_carry_target
        elif right_carry_target.has_tag(self.stop_carry_object_tag):
            carry_target = right_carry_target
        if carry_target is None:
            actor.routing_component.remove_route_event_by_data(self)
            return
        for exit_carry_event in actor.routing_component.route_event_context.route_event_of_data_type_gen(type(self)):
            if exit_carry_event.event_data._owned_object is carry_target:
                actor.routing_component.remove_route_event_by_data(self)
                return
        self._owned_object = carry_target

        def set_target(asm):
            asm.set_current_state('entry')
            asm.set_actor(self.animation_element.actor_name, actor)
            asm.set_actor(self.animation_element.target_name, carry_target)
            return True

        route_interaction = actor.routing_component.route_interaction
        route_event_animation = self.animation_element(route_interaction, setup_asm_additional=set_target, enable_auto_exit=False)
        asm = route_event_animation.get_asm(use_cache=False)
        if asm is None:
            logger.warn('Unable to get a valid Route Event ASM ({}) for {}.', route_event_animation, actor)
            actor.routing_component.remove_route_event_by_data(self)
            return
        self.arb = Arb()

        def _send_arb(timeline):
            route_event_animation.append_to_arb(asm, self.arb)
            route_event_animation.append_exit_to_arb(asm, self.arb)
            distribute_arb_element(self.arb, master=actor, immediate=True)
            return True

        exit_carry_element = exit_carry_while_holding(route_interaction, target=carry_target, sequence=build_element(_send_arb), arb=self.arb)

        def event_finished(_):
            self._owned_object = None
            if actor.routing_component is None:
                return
            actor.routing_component.remove_route_event_by_data(self)

        exit_carry_element = build_critical_section_with_finally(exit_carry_element, event_finished)
        umbrella_timeline = services.time_service().sim_timeline
        umbrella_timeline.schedule(exit_carry_element)
