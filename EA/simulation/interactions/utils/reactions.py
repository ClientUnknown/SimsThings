import weakreffrom autonomy.content_sets import get_valid_aops_genfrom element_utils import build_critical_section_with_finallyfrom event_testing.results import TestResultfrom interactions import ParticipantType, ParticipantTypeReactionfrom interactions.constraint_variants import TunableGeometricConstraintVariantfrom interactions.constraints import Anywherefrom interactions.context import InteractionContext, InteractionSource, QueueInsertStrategyfrom interactions.interaction_finisher import FinishingTypefrom interactions.join_liability import JOIN_INTERACTION_LIABILITY, JoinInteractionLiabilityfrom interactions.priority import Priority, can_displacefrom interactions.utils.interaction_elements import XevtTriggeredElementfrom interactions.utils.loot_basic_op import BaseLootOperationfrom objects import ALL_HIDDEN_REASONSfrom sims4.tuning.tunable import TunableReference, TunableEnumEntry, TunableList, Tunable, OptionalTunable, HasTunableSingletonFactory, AutoFactoryInit, TunableFactory, TunableSingletonFactoryfrom singletons import DEFAULTimport interactions.constraintsimport servicesimport sims4.loglogger = sims4.log.Logger('Reactions', default_owner='rmccord')
class ReactionSi(AutoFactoryInit):
    FACTORY_TUNABLES = {'affordance_target': OptionalTunable(description='\n            If enabled, the pushed interaction will target a specified\n            participant.\n            ', tunable=TunableEnumEntry(description='\n                The participant to be targeted by the pushed interaction.\n                ', tunable_type=ParticipantTypeReaction, default=ParticipantTypeReaction.TargetSim), enabled_by_default=True), 'affordance_run_priority': OptionalTunable(description="\n            If enabled, specify the priority at which the affordance runs. This\n            may be different than 'affordance_priority'. For example. you might\n            want an affordance to push at high priority such that it cancels\n            existing interactions, but it runs at a lower priority such that it\n            can be more easily canceled.\n            ", tunable=TunableEnumEntry(description='\n                The run priority for the specified affordance.\n                ', tunable_type=Priority, default=Priority.Low))}

    @TunableFactory.factory_option
    def get_affordance(pack_safe=False):
        return {'affordance': TunableReference(description='\n                The affordance to push on the subject.\n                ', manager=services.affordance_manager(), class_restrictions=('SuperInteraction',), pack_safe=pack_safe)}

    @TunableFactory.factory_option
    def get_priority(enable_priority=True):
        if enable_priority:
            return {'affordance_priority': TunableEnumEntry(description='\n                The priority at which the specified affordance is to be pushed.\n                \n                IMPORTANT: This will cancel any incompatible interactions the Sim\n                is currently running if they are at a lower priority. Autonomous\n                interactions are pushed at Low priority.\n                ', tunable_type=Priority, default=Priority.Low)}
        else:
            return {}

    def _get_target_and_context(self, sim, resolver, source=DEFAULT, priority=DEFAULT, insert_strategy=QueueInsertStrategy.NEXT, must_run_next=False):
        affordance_target = resolver.get_participant(self.affordance_target) if self.affordance_target is not None else None
        if affordance_target.is_sim:
            affordance_target = affordance_target.get_sim_instance()
        source = InteractionSource.SCRIPT if affordance_target is not None and source is DEFAULT else source
        priority = self.affordance_priority if priority is DEFAULT else priority
        context = InteractionContext(sim, source, priority, run_priority=self.affordance_run_priority, insert_strategy=insert_strategy, must_run_next=must_run_next)
        return (affordance_target, context)

    def __call__(self, sim, resolver, source=DEFAULT, priority=DEFAULT, insert_strategy=QueueInsertStrategy.NEXT, must_run_next=False, **kwargs):
        (target, context) = self._get_target_and_context(sim, resolver, source=source, priority=priority, insert_strategy=insert_strategy, must_run_next=must_run_next)
        return sim.push_super_affordance(self.affordance, target, context, **kwargs)
TunableReactionSi = TunableSingletonFactory.create_auto_factory(ReactionSi)
class ReactionMixer(AutoFactoryInit):
    FACTORY_TUNABLES = {'affordance_target': OptionalTunable(description='\n            If enabled, the pushed interaction will target a specified\n            participant.\n            ', tunable=TunableEnumEntry(description='\n                The participant to be targeted by the pushed interaction.\n                ', tunable_type=ParticipantTypeReaction, default=ParticipantTypeReaction.TargetSim)), 'super_affordance_override': OptionalTunable(description="\n            If enabled, this super affordance will be the SI for the reaction\n            mixer. If disabled, we use the posture's SI. \n            \n            Note: This should only be tuned if we are trying to push a\n            SocialMixerInteraction as a reaction mixer. In that case you want\n            to push its SocialSuperInteraction.\n            \n            Furthermore, if the pusher of this reaction is a Social interaction\n            whose SI matches the override type, we'll reuse that SI as the\n            mixer's SI.\n            ", tunable=TunableReference(description='\n                The super affordance to use for this reaction mixer.\n                ', manager=services.affordance_manager(), class_restrictions=('SocialSuperInteraction',), pack_safe=True))}

    @TunableFactory.factory_option
    def get_affordance(pack_safe=False):
        return {'affordance': TunableReference(description='\n                The affordance to push on the subject.\n                ', manager=services.affordance_manager(), class_restrictions=('MixerInteraction',), pack_safe=pack_safe)}

    def __call__(self, sim, resolver, insert_strategy=QueueInsertStrategy.NEXT, must_run_next=False, **kwargs):
        if self.super_affordance_override is not None:
            push_super_on_prepare = True
            source_interaction = None
            source_affordance = self.super_affordance_override
            for super_interaction in sim.running_interactions_gen(self.super_affordance_override):
                source_interaction = super_interaction
                push_super_on_prepare = False
                break
        else:
            push_super_on_prepare = False
            source_interaction = sim.posture.source_interaction
            if source_interaction is None:
                logger.error('{} in posture {} does not have a source interaction', sim, sim.posture)
                return TestResult(False, '{} in posture {} does not have a source interaction', sim, sim.posture)
            source_affordance = source_interaction.super_affordance
        sim_specific_lockout = self.affordance.lock_out_time.target_based_lock_out if self.affordance.lock_out_time is not None else False
        if sim_specific_lockout and sim.is_sub_action_locked_out(self.affordance):
            return TestResult(False, 'Reaction Mixer Affordance {} is currently locked out.', self.affordance)
        if self.affordance_target is not None:
            targets = [target.get_sim_instance() if target.is_sim else target for target in resolver.get_participants(self.affordance_target) if target is not None]
        else:
            targets = [None]
            if source_interaction is not None:
                potential_targets = source_interaction.get_potential_mixer_targets()
                targets.extend(self.affordance.filter_mixer_targets(source_interaction, potential_targets, sim))
        context = InteractionContext(sim, InteractionSource.REACTION, Priority.High, insert_strategy=insert_strategy, must_run_next=must_run_next)
        for target in targets:
            for (aop, test_result) in get_valid_aops_gen(target, self.affordance, source_affordance, source_interaction, context, False, push_super_on_prepare=push_super_on_prepare, aop_kwargs=kwargs):
                if not test_result:
                    pass
                else:
                    interaction_constraint = aop.constraint_intersection(sim=sim, posture_state=None)
                    posture_constraint = sim.posture_state.posture_constraint_strict
                    constraint_intersection = interaction_constraint.intersect(posture_constraint)
                    if constraint_intersection.valid:
                        mixer_result = aop.execute(context)
                        if not mixer_result:
                            pass
                        else:
                            if sim.queue.always_start_inertial:
                                running_interaction = sim.queue.running
                                if running_interaction is not None and not running_interaction.is_super:
                                    running_interaction.cancel(FinishingType.DISPLACED, cancel_reason_msg='Reaction displaced mixer.')
                            return mixer_result
        return TestResult(False, "Could not push reaction affordance {} on {}. It's likely that the Sim is in a posture that is incompatible with this mixer.", self.affordance, sim)
TunableReactionMixer = TunableSingletonFactory.create_auto_factory(ReactionMixer)
class ReactionLootOp(BaseLootOperation):
    FACTORY_TUNABLES = {'si_reaction': OptionalTunable(description='\n            A Super Interaction that is pushed on the Subject when this\n            loot op is applied. If the SI cannot displace other\n            interactions in the queue and a mixer reaction is tuned, then\n            the mixer will get pushed.\n            ', tunable=TunableReactionSi(description='\n                A Super Interaction that is pushed on the Subject when this\n                loot op is applied.\n                ', get_affordance={'pack_safe': True}, get_priority={'enable_priority': True})), 'mixer_reaction': OptionalTunable(description="\n            A mixer interaction to push on the subject. This will be attached\n            to the posture's SI so it must meet the constraints of the posture\n            or else it will not run. This interaction should primarily be used\n            to animate the Sim. Mixers are useful for reactions because we can\n            inject them into staging SIs.\n            \n            If an SI Reaction is tuned in addition to this mixer, then the\n            mixer will act as a fallback to the SI.\n            ", tunable=TunableReactionMixer(description='"\n                A reaction mixer that is pushed when this loot op runs. It will\n                only run if an SI reaction is not tuned, fails to run, or does\n                not run in a timely manner.\n                ', get_affordance={'pack_safe': True}))}

    def __init__(self, *args, si_reaction, mixer_reaction, **kwargs):
        super().__init__(*args, **kwargs)
        self.si_reaction = si_reaction
        self.mixer_reaction = mixer_reaction

    def _push_mixer_reaction(self, sim, resolver):
        return self.mixer_reaction(sim, resolver)

    def _push_si_reaction(self, sim, resolver):
        return self.si_reaction(sim, resolver)

    def _should_fallback_to_mixer_reaction(self, sim, interaction):
        for running_interaction in sim.si_state:
            if not running_interaction.is_guaranteed():
                pass
            elif can_displace(interaction, running_interaction):
                pass
            elif sim.si_state.are_sis_compatible(running_interaction, interaction):
                pass
            else:
                return True
        return False

    def _apply_to_subject_and_target(self, subject, target, resolver):
        if subject is None:
            logger.error('Attempting to play a reaction on a None subject for participant {}. Loot: {}', self.subject, self, owner='rmccord')
            return
        if not subject.is_sim:
            logger.error('Attempting to play a reaction on subject: {}, that is not a Sim. Loot: {}', self.subject, self, owner='rmccord')
            return
        sim = subject.get_sim_instance()
        if sim is None:
            return
        if self.si_reaction is not None:
            result = self._push_si_reaction(sim, resolver)
            if self.mixer_reaction is not None and result and self._should_fallback_to_mixer_reaction(sim, result.execute_result.interaction):
                self._push_mixer_reaction(sim, resolver)
        elif self.mixer_reaction is not None:
            self._push_mixer_reaction(sim, resolver)

class ReactionTriggerElement(XevtTriggeredElement):
    FACTORY_TUNABLES = {'reaction_affordance': TunableReference(description='\n            The affordance to push on other Sims.\n            ', manager=services.affordance_manager()), 'reaction_target': TunableEnumEntry(description='\n            The subject of this interaction that will be set as the target of the pushed reaction_affordance.\n            ', tunable_type=ParticipantType, default=ParticipantType.Actor), 'reaction_constraints': TunableList(description='\n            The constraints that Sims on the lot have to satisfy such that reaction_affordance is pushed on them.\n            ', tunable=TunableGeometricConstraintVariant(description='\n                The constraints that Sims on the lot have to satisfy such that reaction_affordance is pushed on them.\n                ', constraint_locked_args={'multi_surface': True}, circle_locked_args={'require_los': False}, disabled_constraints={'spawn_points', 'current_position'})), 'trigger_on_late_arrivals': Tunable(description='\n            If checked, Sims entering the reaction area after the reaction is\n            first triggered will also react, up until when the interaction is\n            canceled.\n            ', tunable_type=bool, default=False)}

    def __init__(self, interaction, *args, sequence=(), **kwargs):
        super().__init__(interaction, *args, sequence=sequence, **kwargs)
        self._reaction_target_sim = self.interaction.get_participant(self.reaction_target)
        self._reaction_constraint = None
        self._triggered_sims = _instances = weakref.WeakSet()

    @classmethod
    def on_affordance_loaded_callback(cls, affordance, reaction_trigger_element, object_tuning_id=DEFAULT):

        def sim_can_execute_affordance(interaction, sim):
            context = InteractionContext(sim, InteractionContext.SOURCE_SCRIPT, Priority.High)
            return sim.test_super_affordance(reaction_trigger_element.reaction_affordance, interaction.target, context)

        affordance.register_sim_can_violate_privacy_callback(sim_can_execute_affordance, object_tuning_id=object_tuning_id)

    def _build_outer_elements(self, sequence):
        if self.trigger_on_late_arrivals:
            return build_critical_section_with_finally(sequence, self._remove_constraints)
        return sequence

    def _do_behavior(self):
        self._reaction_constraint = Anywhere()
        for tuned_reaction_constraint in self.reaction_constraints:
            self._reaction_constraint = self._reaction_constraint.intersect(tuned_reaction_constraint.create_constraint(None, target=self._reaction_target_sim))
        if self.trigger_on_late_arrivals:
            self._reaction_target_sim.reaction_triggers[self.interaction] = self
        for sim in services.sim_info_manager().instanced_sims_gen():
            self.intersect_and_execute(sim)

    def intersect_and_execute(self, sim):
        if sim in self._triggered_sims:
            return
        participants = self.interaction.get_participants(ParticipantType.AllSims)
        if sim not in participants:
            sim_constraint = interactions.constraints.Transform(sim.transform, routing_surface=sim.routing_surface)
            context = InteractionContext(sim, InteractionContext.SOURCE_SCRIPT, Priority.High)
            if sim_constraint.intersect(self._reaction_constraint).valid:
                result = sim.push_super_affordance(self.reaction_affordance, self._reaction_target_sim, context)
                if result:
                    self.interaction.add_liability(JOIN_INTERACTION_LIABILITY, JoinInteractionLiability(result.interaction))
                self._triggered_sims.add(sim)

    def _remove_constraints(self, *_, **__):
        self._reaction_target_sim.reaction_triggers.pop(self.interaction, None)
