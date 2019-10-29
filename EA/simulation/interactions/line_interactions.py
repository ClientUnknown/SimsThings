from interactions import ParticipantTypefrom interactions.constraints import ANYWHEREfrom interactions.context import InteractionContext, QueueInsertStrategyfrom interactions.interaction_finisher import FinishingTypefrom interactions.utils.satisfy_constraint_interaction import SatisfyConstraintSuperInteraction, SitOrStandSuperInteractionfrom objects.components.line_of_sight_component import LineOfSightComponentfrom objects.components.types import WAITING_LINE_COMPONENTfrom sims4.tuning.instances import lock_instance_tunablesfrom sims4.utils import flexmethodfrom singletons import DEFAULTimport element_utilsimport interactions.constraintsimport sims4.logimport sims4.mathlogger = sims4.log.Logger('Waiting-Line', default_owner='ayarger')
class WaitInLineSuperInteraction(SitOrStandSuperInteraction):

    def __init__(self, *args, interaction_data=None, line_head_data=None, **kwargs):
        super().__init__(*args, **kwargs)
        self._stored_aop = interaction_data[0]
        self._stored_context = interaction_data[1]
        self._stored_key = interaction_data[2]
        self._line_head_data = line_head_data
        self._adjustment_interaction = None
        self._instanced_stored_interaction = None
        (self._waiting_line, self._waiting_line_component) = self._initialize_line_component_on_target()
        self._current_adjustment_constraint = None
        self.register_on_finishing_callback(self._waiting_line_finish_callback)
        self.maybe_enter_stored_interaction()

    def _initialize_line_component_on_target(self):
        target = self._stored_aop.target.part_owner if self._stored_aop.target.is_part else self._stored_aop.target
        target.add_dynamic_component(WAITING_LINE_COMPONENT)
        return (target.waiting_line_component.join_line(self), target.waiting_line_component)

    def prepare_gen(self, timeline, **kwargs):
        if not self.maybe_enter_stored_interaction():
            self._push_adjustment_interaction()
        result = yield from super().prepare_gen(timeline, **kwargs)
        return result

    def maybe_enter_stored_interaction(self, *args, **kwargs):
        if self._waiting_line.is_first_in_line(self) and (self._instanced_stored_interaction or self.may_reserve_on_stored_target()):
            self._begin_stored_interaction()
            return True
        return False

    def _begin_stored_interaction(self):
        self.leave_socials()
        if self._adjustment_interaction is not None:
            self._adjustment_interaction.cancel(FinishingType.WAIT_IN_LINE, 'Canceled')
            self._adjustment_interaction = None
        if self._instanced_stored_interaction:
            logger.error('Attempting to run stored interaction {} twice!', self._instanced_stored_interaction)
            return
        self._stored_context.insert_strategy = QueueInsertStrategy.NEXT
        result = self._stored_aop.test_and_execute(self._stored_context)
        if result.interaction is not None:
            self._instanced_stored_interaction = result.interaction
            self.sim.routing_component.stand_slot_reservation_removed_callbacks.register(self._stand_slot_released_callback)
            self._instanced_stored_interaction.register_on_finishing_callback(self._stored_interaction_finished_callback)
        self.cancel(FinishingType.FAILED_TESTS, cancel_reason_msg='Attempted to execute stored interaction.')

    def adjust_sim_behind_me(self, timeline):
        interaction_behind = self._waiting_line.get_neighboring_interaction(self, offset=1)
        if interaction_behind is not None:
            interaction_behind._push_adjustment_interaction()

    def _push_adjustment_interaction(self):
        if self._instanced_stored_interaction:
            return
        self.leave_socials()
        if self._adjustment_interaction is not None:
            self._adjustment_interaction.cancel(FinishingType.WAIT_IN_LINE, 'Canceled')
            self._adjustment_interaction = None
        self._current_adjustment_constraint = self.get_adjustment_constraint()
        adjust_context = InteractionContext(self.sim, self._stored_context.source, self.priority, insert_strategy=QueueInsertStrategy.FIRST, cancel_if_incompatible_in_queue=True)
        run_element = element_utils.build_element((self.adjust_sim_behind_me, self.maybe_enter_stored_interaction))
        result = self.sim.push_super_affordance(SatisfyConstraintSuperInteraction, None, adjust_context, constraint_to_satisfy=self._current_adjustment_constraint, allow_posture_changes=True, set_work_timestamp=False, name_override='AdjustWaitingLinePosition', run_element=run_element, cancel_incompatible_with_posture_on_transition_shutdown=False)
        self._adjustment_interaction = result.interaction

    def may_reserve_on_stored_target(self):
        stored_basic_reserve = self._stored_aop.affordance.basic_reserve_object
        if stored_basic_reserve is None:
            return True
        targets = self._stored_aop.target.parts if self._stored_aop.target.parts else (self._stored_aop.target,)
        for target in targets:
            target_reservation_handler = stored_basic_reserve(self.sim, self, reserve_target=target)
            if target_reservation_handler.may_reserve():
                return True
        return False

    @property
    def waiting_line_key(self):
        return self._stored_key

    @property
    def line_head_data(self):
        return self._line_head_data

    @flexmethod
    def constraint_intersection(cls, inst, sim=DEFAULT, participant_type=ParticipantType.Actor, **kwargs):
        if inst._instanced_stored_interaction:
            return ANYWHERE
        if inst._current_adjustment_constraint is not None:
            return inst._current_adjustment_constraint
        else:
            return inst.get_adjustment_constraint()

    @flexmethod
    def get_adjustment_constraint(cls, inst, sim=DEFAULT, participant_type=ParticipantType.Actor, **kwargs):
        if inst._instanced_stored_interaction:
            logger.error("generating an adjustment constraint after we we've begun our interaction transition.")
        rotation_of_cone = inst._waiting_line._line_head_angle + sims4.math.yaw_quaternion_to_angle(inst._stored_aop.target.orientation)
        rotation_of_target = sims4.math.yaw_quaternion_to_angle(inst._stored_aop.target.orientation)
        tuned_forward_vector = sims4.math.vector3_rotate_axis_angle(sims4.math.Vector3(0, 0, 1), rotation_of_cone, sims4.math.Vector3(0, 1, 0))
        constraint_list = []
        interaction_in_front_of_me = inst._waiting_line.get_neighboring_interaction(inst, offset=-1)
        sim_in_front_of_me = interaction_in_front_of_me.sim if interaction_in_front_of_me is not None else None
        if inst._waiting_line.is_first_in_line(inst) or sim_in_front_of_me is not None and interaction_in_front_of_me._instanced_stored_interaction is not None:
            offset_vector = sims4.math.Vector3(inst._waiting_line._line_head_position.x, 0, inst._waiting_line._line_head_position.y)
            rotated_offset_vector = sims4.math.vector3_rotate_axis_angle(offset_vector, rotation_of_target, sims4.math.Vector3(0, 1, 0))
            destination_vector = inst._stored_aop.target.position + rotated_offset_vector
            if inst._stored_aop.target.lineofsight_component is None:
                new_los_component = LineOfSightComponent(inst._stored_aop.target, 0.1, inst._waiting_line._line_head_los_constraint)
                inst._stored_aop.target.add_component(new_los_component)
            constraint_list.append(inst._stored_aop.target.lineofsight_component.constraint)
            facing_constraint = interactions.constraints.Facing(inst._stored_aop.target)
            constraint_list.append(facing_constraint)
            cone_constraint = inst._waiting_line._line_cone.create_constraint(sim, None, target_position=destination_vector, target_forward=tuned_forward_vector, routing_surface=inst._stored_aop.target.routing_surface)
            constraint_list.append(cone_constraint)
        else:
            if sim_in_front_of_me is None:
                logger.error('Sim {} is not first in line for aop {}, but there is no one in front of him/her!', inst.sim, inst._stored_aop)
                return
            constraint_list.append(sim_in_front_of_me.lineofsight_component.constraint)
            facing_constraint = interactions.constraints.Facing(sim_in_front_of_me)
            constraint_list.append(facing_constraint)
            desired_position = sim_in_front_of_me.intended_position
            sim_2_in_front_to_sim_in_front_vector = tuned_forward_vector
            interaction_2_in_front_of_me = inst._waiting_line.get_neighboring_interaction(interaction_in_front_of_me, offset=-1)
            if not interaction_2_in_front_of_me._instanced_stored_interaction:
                sim_2_in_front_of_me = interaction_2_in_front_of_me.sim
                sim_2_in_front_to_sim_in_front_vector = sim_in_front_of_me.intended_position - sim_2_in_front_of_me.intended_position
            combined_vector = sims4.math.vector_normalize(sim_2_in_front_to_sim_in_front_vector + tuned_forward_vector)
            line_cone_constraint = inst._waiting_line._line_cone.create_constraint(sim, None, target_position=desired_position, target_forward=combined_vector, routing_surface=inst._stored_aop.target.routing_surface)
            constraint_list.append(line_cone_constraint)
        if not constraint_list:
            logger.error('The production of waiting-line adjustment constraints yielded no constraints.')
            return ANYWHERE
        total_constraint = constraint_list[0]
        for constraint in constraint_list[1:]:
            total_constraint = total_constraint.intersect(constraint)
        return total_constraint

    def leave_socials(self):
        social_group = self.sim.get_main_group()
        if social_group is None:
            return
        my_sis = list(social_group.get_sis_registered_for_sim(self.sim))
        for si in my_sis:
            si.cancel(FinishingType.WAIT_IN_LINE, cancel_reason_msg='Socials canceled due to waiting-line adjustment interaction.')

    def prevents_distress(self, stat_type):
        if super().prevents_distress(stat_type):
            return True
        elif stat_type in self._stored_aop.affordance.commodity_flags:
            return True
        return False

    @classmethod
    def _get_icon(cls, interaction_resolver):
        return (None, interaction_resolver.interaction._stored_aop.target)

    def _get_resource_instance_hash(self):
        return self._stored_aop.affordance.guid64

    def _get_save_object(self):
        return self._stored_aop.target

    def _stand_slot_released_callback(self, sim):
        if self._waiting_line.is_in_line(self):
            self._waiting_line_component.remove_from_lines(self)
        if self._instanced_stored_interaction.will_exit:
            self.sim.routing_component.stand_slot_reservation_removed_callbacks.unregister(self._stand_slot_released_callback)
        self._waiting_line_component.notify_heads_of_lines()

    def _waiting_line_finish_callback(self, interaction):
        interaction.unregister_on_finishing_callback(self._waiting_line_finish_callback)
        neighbor_behind = self._waiting_line.get_neighboring_interaction(interaction, offset=1)
        if self._instanced_stored_interaction is None:
            self._waiting_line_component.remove_from_lines(self)
        if neighbor_behind is not None:
            neighbor_behind._push_adjustment_interaction()

    def _stored_interaction_finished_callback(self, interaction):
        if self._waiting_line.is_in_line(self):
            self._waiting_line_component.remove_from_lines(self)
        self.unregister_on_finishing_callback(self._stored_interaction_finished_callback)
lock_instance_tunables(WaitInLineSuperInteraction, basic_reserve_object=None)