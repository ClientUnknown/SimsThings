from _math import Vector3, Transformfrom carry.carry_elements import exit_carry_while_holdingfrom carry.carry_postures import CarrySystemTerrainTarget, CarrySystemCustomAnimationTarget, CarryingObjectfrom carry.put_down_interactions import create_put_down_on_ground_constraint, PutAwayBasefrom element_utils import build_critical_section_with_finallyfrom event_testing.results import TestResultfrom interactions import ParticipantTypefrom interactions.aop import AffordanceObjectPairfrom interactions.base.basic import TunableBasicContentSetfrom interactions.base.super_interaction import SuperInteractionfrom placement import FGLSearchFlagfrom postures import posture_graphfrom sims4.tuning.tunable import TunableVariant, AutoFactoryInit, HasTunableSingletonFactory, OptionalTunablefrom sims4.utils import flexmethod, classpropertyfrom singletons import UNSETimport interactions.constraintsimport services
class _PutDownBehaviorRunInteraction(HasTunableSingletonFactory, AutoFactoryInit):
    FACTORY_TUNABLES = {'affordance': OptionalTunable(description='\n            The interaction to run once the Sim is put down.\n            ', tunable=SuperInteraction.TunableReference(description='\n                The interaction to run once the Sim is put down.\n                '), disabled_name='Use_Default_Affordance', enabled_name='Use_Specific_Affordance')}

    def get_provided_posture(self):
        if self.affordance is None:
            return posture_graph.SIM_DEFAULT_POSTURE_TYPE
        return self.affordance.provided_posture_type

    def get_target_si(self, interaction):
        sim = interaction.carry_target or interaction.target
        if self.affordance is None:
            interaction = sim.create_default_si()
        else:
            for running_interaction in sim.get_all_running_and_queued_interactions():
                if not running_interaction.transition is None:
                    if running_interaction.is_finishing:
                        pass
                    elif running_interaction.get_interaction_type() is not self.affordance:
                        pass
                    elif running_interaction.target is not interaction.target:
                        pass
                    else:
                        return (running_interaction, TestResult.TRUE)
            context = interaction.context.clone_for_sim(sim, carry_target=None, continuation_id=None)
            aop = AffordanceObjectPair(self.affordance, interaction.target, self.affordance, None)
            interaction = aop.interaction_factory(context).interaction
        return (interaction, TestResult.TRUE)

class PutDownSimInteraction(PutAwayBase):
    INSTANCE_SUBCLASSES_ONLY = True
    INSTANCE_TUNABLES = {'basic_content': TunableBasicContentSet(no_content=True, default='no_content'), 'put_down_behavior': TunableVariant(description='\n            Define what the carried Sim does once they are put down.\n            ', run_affordance=_PutDownBehaviorRunInteraction.TunableFactory(), default='run_affordance')}

    def __init__(self, *args, **kwargs):
        self._target_si = None
        super().__init__(*args, **kwargs)

    @classproperty
    def is_putdown(cls):
        return True

    @classmethod
    def get_provided_posture(cls):
        return cls.put_down_behavior.get_provided_posture()

    @classproperty
    def can_holster_incompatible_carries(cls):
        return False

    def build_basic_content(self, sequence, **kwargs):
        sequence = super(SuperInteraction, self).build_basic_content(sequence, **kwargs)

        def change_cancelable_for_target_si(cancelable):
            if self._target_si is not None:
                target_si = self._target_si[0]
                target_si._cancelable_by_user = cancelable
                target_si.sim.ui_manager.update_interaction_cancel_status(target_si)

        def unparent_carried_sim(*_, **__):
            sim = self.carry_target or self.target
            routing_surface = sim.routing_surface
            new_location = sim.location.clone(parent=None, routing_surface=routing_surface)
            sim.set_location_without_distribution(new_location)
            sim.update_intended_position_on_active_lot(update_ui=True)

        carry_system_target = self._get_carry_system_target(unparent_carried_sim)
        target_si_cancelable = self._target_si[0]._cancelable_by_user
        sequence = exit_carry_while_holding(self, use_posture_animations=True, carry_system_target=carry_system_target, sequence=sequence)
        sequence = build_critical_section_with_finally(lambda _: change_cancelable_for_target_si(False), sequence, lambda _: change_cancelable_for_target_si(target_si_cancelable))
        return sequence

    def perform_gen(self, timeline):
        self._must_run_instance = True
        return super().perform_gen(timeline)

    def _exited_pipeline(self, *args, **kwargs):
        if self._target_si is not None:
            (target_interaction, _) = self._target_si
            if target_interaction is not None:
                target_interaction.unregister_on_finishing_callback(self._on_target_si_finished)
        return super()._exited_pipeline(*args, **kwargs)

    def _on_target_si_finished(self, interaction):
        interaction.unregister_on_finishing_callback(self._on_target_si_finished)
        if self._target_si is not None:
            (target_interaction, _) = self._target_si
            if target_interaction is interaction:
                self._target_si = None

    def get_target_si(self):
        if self._target_si is None:
            self._target_si = self.put_down_behavior.get_target_si(self)
            (target_interaction, _) = self._target_si
            if target_interaction is not None:
                target_interaction.register_on_finishing_callback(self._on_target_si_finished)
        return self._target_si

    def _get_carry_system_target(self, callback):
        raise NotImplementedError

    def set_target(self, target):
        if self._target_si is not None and self._target_si[0].target is self.target:
            self._target_si[0].set_target(target)
        super().set_target(target)

class PutDownSimInObjectInteraction(PutDownSimInteraction):

    def _get_carry_system_target(self, callback):
        carry_system_target = CarrySystemCustomAnimationTarget(self.carry_target, True)
        carry_system_target.carry_event_callback = callback
        return carry_system_target

class PutDownSimOnRoutableSurfaceInteraction(PutDownSimInteraction):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._transform = UNSET

    def _get_best_location(self, obj, target):
        routing_surface = getattr(self.target, 'provided_routing_surface', None)
        if routing_surface is None:
            routing_surface = target.routing_surface
        if self._transform is UNSET:
            if target.is_terrain:
                self._transform = target.transform
            else:
                (translation, orientation) = CarryingObject.get_good_location_on_floor(obj, starting_transform=target.transform, starting_routing_surface=routing_surface, additional_search_flags=FGLSearchFlag.STAY_IN_CURRENT_BLOCK)
                if translation is None:
                    self._transform = None
                else:
                    self._transform = Transform(translation, orientation)
        return (self._transform, routing_surface)

    def _get_carry_system_target(self, callback):
        (transform, routing_surface) = self._get_best_location(self.carry_target, self.target)
        transform = Transform(transform.translation, self.sim.orientation)
        surface_height = services.terrain_service.terrain_object().get_routing_surface_height_at(transform.translation.x, transform.translation.z, routing_surface)
        transform.translation = Vector3(transform.translation.x, surface_height, transform.translation.z)
        return CarrySystemTerrainTarget(self.sim, self.carry_target, True, transform, routing_surface=routing_surface, custom_event_callback=callback)

    @flexmethod
    def _constraint_gen(cls, inst, sim, target, participant_type=ParticipantType.Actor):
        inst_or_cls = inst if inst is not None else cls
        yield from super(PutDownSimInteraction, inst_or_cls)._constraint_gen(sim, target, participant_type=participant_type)
        if participant_type != ParticipantType.Actor:
            return
        if inst is not None:
            (transform, routing_surface) = inst._get_best_location(inst.carry_target, inst.target)
            if transform is None:
                yield interactions.constraints.Nowhere('Unable to find good location to execute Put Down')
            yield create_put_down_on_ground_constraint(sim, inst.carry_target, transform, routing_surface=routing_surface)

class PutDownSimAnywhereInteraction(PutDownSimInteraction):

    def __init__(self, *args, slot_types_and_costs, world_cost, sim_inventory_cost, object_inventory_cost, terrain_transform, terrain_routing_surface, objects_with_inventory, visibility_override=None, display_name_override=None, debug_name=None, **kwargs):
        super().__init__(*args, **kwargs)
        self._terrain_transform = terrain_transform
        self._terrain_routing_surface = terrain_routing_surface
        self._world_cost = world_cost

    def _get_carry_system_target(self, callback):
        carryable_component = self._target.carryable_component
        if carryable_component is not None:
            (terrain_transform, terrain_routing_surface) = carryable_component._get_terrain_transform(self)
            if not terrain_routing_surface is None:
                self._terrain_transform = terrain_transform
                self._terrain_routing_surface = terrain_routing_surface
        self._terrain_transform.orientation = self.sim.transform.orientation
        return CarrySystemTerrainTarget(self.sim, self.target, True, self._terrain_transform, custom_event_callback=callback)

    @flexmethod
    def _constraint_gen(cls, inst, sim, target, participant_type=ParticipantType.Actor):
        inst_or_cls = inst if inst is not None else cls
        yield from super(PutDownSimInteraction, inst_or_cls)._constraint_gen(sim, target, participant_type=participant_type)
        if participant_type != ParticipantType.Actor:
            return
        if inst is not None:
            constraint = create_put_down_on_ground_constraint(sim, target, inst._terrain_transform, routing_surface=inst._terrain_routing_surface, cost=inst._world_cost)
            transform_constraint = interactions.constraints.Transform(sim.transform, routing_surface=sim.routing_surface)
            transform_constraint = transform_constraint.intersect(constraint)
            constraint = transform_constraint
            yield constraint
