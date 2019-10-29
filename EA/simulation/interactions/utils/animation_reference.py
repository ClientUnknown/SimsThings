from collections import defaultdictfrom animation import get_throwaway_animation_contextfrom animation.asm import create_asmfrom interactions import ParticipantTypefrom interactions.constraints import RequiredSlotSingle, create_constraint_set, Nowherefrom native.animation import ASM_ACTORTYPE_SIMfrom sims4 import reloadfrom sims4.tuning.tunable import TunableReferenceFactory, TunableSingletonFactoryfrom singletons import DEFAULTimport animation.asmimport cachesimport interactions.interaction_instance_managerimport servicesimport sims4.loglogger = sims4.log.Logger('Animation')with reload.protected(globals()):
    _animation_reference_usage = defaultdict(lambda : defaultdict(lambda : 0))
def get_animation_reference_usage():
    return _animation_reference_usage

class TunableAnimationReference(TunableReferenceFactory):

    @staticmethod
    def get_default_callback(interaction_asm_type):

        def callback(cls, fields, source, *, factory, overrides, actor_participant_type=ParticipantType.Actor, target_participant_type=ParticipantType.TargetSim, **kwargs):
            if cls is None:
                return
            participant_constraint_lists = {}
            run_in_sequence = factory.run_in_sequence
            for animation_element_factory in factory.animation_element_gen():
                animation_element = animation_element_factory()
                asm_key = animation_element.asm_key
                actor_name = animation_element.actor_name
                target_name = animation_element.target_name
                carry_target_name = animation_element.carry_target_name
                create_target_name = animation_element.create_target_name
                initial_state = animation_element.initial_state
                begin_states = animation_element.begin_states
                end_states = animation_element.end_states
                base_object_name = animation_element.base_object_name
                instance_overrides = overrides()
                total_overrides = animation_element.overrides(overrides=instance_overrides)
                cls.register_tuned_animation(interaction_asm_type, asm_key, actor_name, target_name, carry_target_name, create_target_name, total_overrides, actor_participant_type, target_participant_type)
                if animation_element_factory._child_animations:
                    for child_args in animation_element_factory._child_animations:
                        cls.register_tuned_animation(*child_args)
                if interactions.interaction_instance_manager.BUILD_AC_CACHE or cls.resource_key not in sims4.resources.localwork_no_groupid and asm_key not in sims4.resources.localwork_no_groupid and caches.USE_ACC_AND_BCC & caches.AccBccUsage.ACC:
                    return
                if animation_element_factory._child_constraints:
                    for child_args in animation_element_factory._child_constraints:
                        cls.add_auto_constraint(*child_args)
                from animation.animation_constants import InteractionAsmType
                if not interaction_asm_type == InteractionAsmType.Outcome:
                    if interaction_asm_type == InteractionAsmType.Response:
                        from interactions.constraints import create_animation_constraint

                        def add_participant_constraint(participant_type, animation_constraint):
                            if animation_constraint is not None:
                                if interaction_asm_type == InteractionAsmType.Canonical:
                                    is_canonical = True
                                else:
                                    is_canonical = False
                                if run_in_sequence:
                                    cls.add_auto_constraint(participant_type, animation_constraint, is_canonical=is_canonical)
                                else:
                                    if participant_type not in participant_constraint_lists:
                                        participant_constraint_lists[participant_type] = []
                                    participant_constraint_lists[participant_type].append(animation_constraint)

                        animation_constraint_actor = None
                        try:
                            animation_constraint_actor = create_animation_constraint(asm_key, actor_name, target_name, carry_target_name, create_target_name, initial_state, begin_states, end_states, total_overrides, base_object_name=base_object_name)
                        except:
                            if interaction_asm_type != InteractionAsmType.Outcome:
                                logger.exception('Exception while processing tuning for {}', cls)
                        add_participant_constraint(actor_participant_type, animation_constraint_actor)
                        if target_name is not None:
                            animation_context = get_throwaway_animation_context()
                            asm = animation.asm.create_asm(asm_key, animation_context, posture_manifest_overrides=total_overrides.manifests)
                            target_actor_definition = asm.get_actor_definition(target_name)
                            if target_actor_definition.actor_type == ASM_ACTORTYPE_SIM and not target_actor_definition.is_virtual:
                                animation_constraint_target = create_animation_constraint(asm_key, target_name, actor_name, carry_target_name, create_target_name, initial_state, begin_states, end_states, total_overrides, base_object_name=base_object_name)
                                add_participant_constraint(target_participant_type, animation_constraint_target)
                from interactions.constraints import create_animation_constraint

                def add_participant_constraint(participant_type, animation_constraint):
                    if animation_constraint is not None:
                        if interaction_asm_type == InteractionAsmType.Canonical:
                            is_canonical = True
                        else:
                            is_canonical = False
                        if run_in_sequence:
                            cls.add_auto_constraint(participant_type, animation_constraint, is_canonical=is_canonical)
                        else:
                            if participant_type not in participant_constraint_lists:
                                participant_constraint_lists[participant_type] = []
                            participant_constraint_lists[participant_type].append(animation_constraint)

                animation_constraint_actor = None
                try:
                    animation_constraint_actor = create_animation_constraint(asm_key, actor_name, target_name, carry_target_name, create_target_name, initial_state, begin_states, end_states, total_overrides, base_object_name=base_object_name)
                except:
                    if interaction_asm_type != InteractionAsmType.Outcome:
                        logger.exception('Exception while processing tuning for {}', cls)
                add_participant_constraint(actor_participant_type, animation_constraint_actor)
                if interaction_asm_type == InteractionAsmType.Interaction or interaction_asm_type == InteractionAsmType.Canonical or target_name is not None:
                    animation_context = get_throwaway_animation_context()
                    asm = animation.asm.create_asm(asm_key, animation_context, posture_manifest_overrides=total_overrides.manifests)
                    target_actor_definition = asm.get_actor_definition(target_name)
                    if target_actor_definition.actor_type == ASM_ACTORTYPE_SIM and not target_actor_definition.is_virtual:
                        animation_constraint_target = create_animation_constraint(asm_key, target_name, actor_name, carry_target_name, create_target_name, initial_state, begin_states, end_states, total_overrides, base_object_name=base_object_name)
                        add_participant_constraint(target_participant_type, animation_constraint_target)
            if participant_constraint_lists is not None:
                for (participant_type, constraints_list) in participant_constraint_lists.items():
                    cls.add_auto_constraint(participant_type, create_constraint_set(constraints_list))

        return callback

    def __init__(self, class_restrictions=DEFAULT, callback=DEFAULT, interaction_asm_type=DEFAULT, allow_reactionlets=True, override_animation_context=False, participant_enum_override=DEFAULT, **kwargs):
        if interaction_asm_type is DEFAULT:
            from animation.animation_constants import InteractionAsmType
            interaction_asm_type = InteractionAsmType.Interaction
        if callback is DEFAULT:
            callback = self.get_default_callback(interaction_asm_type)
        if class_restrictions is DEFAULT:
            class_restrictions = ('AnimationElement', 'AnimationElementSet')
        from animation.tunable_animation_overrides import TunableAnimationOverrides
        super().__init__(callback=callback, manager=services.animation_manager(), class_restrictions=class_restrictions, overrides=TunableAnimationOverrides(allow_reactionlets=allow_reactionlets, override_animation_context=override_animation_context, participant_enum_override=participant_enum_override, description='The overrides for interaction to replace the tunings on the animation elements'), **kwargs)

class TunedAnimationConstraint:

    def __init__(self, animation_ref):
        self._animation_ref = animation_ref

    def create_constraint(self, *args, **kwargs):
        animation_constraints = []
        if self._animation_ref:
            for animation_element_factory in self._animation_ref.animation_element_gen():
                animation_element = animation_element_factory()
                asm_key = animation_element.asm_key
                actor_name = animation_element.actor_name
                target_name = animation_element.target_name
                carry_target_name = animation_element.carry_target_name
                create_target_name = animation_element.create_target_name
                initial_state = animation_element.initial_state
                begin_states = animation_element.begin_states
                end_states = animation_element.end_states
                from interactions.constraints import create_animation_constraint
                animation_constraint = create_animation_constraint(asm_key, actor_name, target_name, carry_target_name, create_target_name, initial_state, begin_states, end_states, animation_element.overrides)
                animation_constraints.append(animation_constraint)
        return create_constraint_set(animation_constraints)

class TunableAnimationConstraint(TunableSingletonFactory):
    FACTORY_TYPE = TunedAnimationConstraint

    def __init__(self, description='A tunable type for creating animation-based constraints.', **kwargs):
        super().__init__(animation_ref=TunableAnimationReference(callback=None, description='\n                        The animation to use when generating the RequiredSlot constraint.'), **kwargs)

class TunableRoutingSlotConstraint(TunableSingletonFactory):

    class _TunedRoutingSlotConstraint:

        def __init__(self, animation_element):
            self.animation_element = animation_element

        def create_constraint(self, actor, target, **kwargs):
            if target is None:
                return Nowhere('{} is creating a RoutingSlotConstraint for a None Target.', actor)
            slot_constraints = []
            asm_key = self.animation_element.asm_key
            actor_name = self.animation_element.actor_name
            target_name = self.animation_element.target_name
            state_name = self.animation_element.begin_states[0]
            asm = create_asm(asm_key, context=get_throwaway_animation_context())
            asm.set_actor(actor_name, actor)
            asm.add_potentially_virtual_actor(actor_name, actor, target_name, target)
            asm.dirty_boundary_conditions()
            if actor.is_sim:
                age = actor.age.age_for_animation_cache
            else:
                age = None
            boundary_conditions = asm.get_boundary_conditions_list(actor, state_name)
            for (_, slots_to_params_entry) in boundary_conditions:
                if not slots_to_params_entry:
                    pass
                else:
                    slots_to_params_entry_absolute = []
                    for (boundary_condition_entry, param_sequences_entry) in slots_to_params_entry:
                        (routing_transform_entry, containment_transform, _, reference_joint_exit) = boundary_condition_entry.get_transforms(asm, target)
                        slots_to_params_entry_absolute.append((routing_transform_entry, reference_joint_exit, param_sequences_entry))
                    slot_constraint = RequiredSlotSingle(actor, target, asm, asm_key, None, actor_name, target_name, state_name, containment_transform, None, tuple(slots_to_params_entry_absolute), None, asm_name=asm.name, age=age)
                    slot_constraints.append(slot_constraint)
            return create_constraint_set(slot_constraints)

    FACTORY_TYPE = _TunedRoutingSlotConstraint

    def __init__(self, description='A tunable type for creating animation-based constraints.', class_restrictions=DEFAULT, **kwargs):
        super().__init__(animation_element=TunableAnimationReference(description='\n                The animation to use when generating the RoutingSlot constraint.\n                ', callback=None, class_restrictions=class_restrictions), **kwargs)
