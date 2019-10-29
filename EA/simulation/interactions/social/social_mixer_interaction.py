import functoolsimport itertoolsfrom animation.arb_accumulator import with_skippable_animation_timefrom element_utils import build_critical_section_with_finallyfrom event_testing import test_eventsfrom event_testing.resolver import DoubleSimResolverfrom event_testing.results import TestResultfrom interactions import TargetType, ParticipantTypefrom interactions.base.interaction import Interactionfrom interactions.base.interaction_constants import InteractionQueuePreparationStatusfrom interactions.base.mixer_interaction import MixerInteractionfrom interactions.social import SocialInteractionMixinfrom interactions.utils.outcome import TunableOutcomefrom postures.transition import PostureTransitionfrom sims.sim_info_tests import GenderPreferenceTestfrom sims4.tuning.tunable import Tunable, OptionalTunable, TunableTuple, TunableInterval, TunableSimMinute, TunableList, TunableReferencefrom sims4.tuning.tunable_base import GroupNamesfrom sims4.utils import flexmethod, classpropertyfrom singletons import DEFAULTfrom socials.social_tests import SocialContextTestfrom tag import Tagimport element_utilsimport servicesimport sims4.logimport taglogger = sims4.log.Logger('Socials')with sims4.reload.protected(globals()):
    tunable_tests_enabled = True
class SocialMixerInteraction(SocialInteractionMixin, MixerInteraction):
    REMOVE_INSTANCE_TUNABLES = ('basic_reserve_object', 'basic_focus')
    basic_reserve_object = None
    GENDER_PREF_CONTENT_SCORE_PENALTY = Tunable(description='\n        Penalty applied to content score when the social fails the gender preference test.\n        ', tunable_type=int, default=-1500)
    INSTANCE_TUNABLES = {'outcome': TunableOutcome(allow_multi_si_cancel=True, tuning_group=GroupNames.CORE), 'use_swing_distance_parameter': Tunable(description='\n            If enabled this mixer will set the distance parameter in swing.\n            This parameter will calculate the distance between the actor\n            and the target sim and use that to set LOW-MID-HIGH distance\n            on swing so we can play different animations depending on the \n            location of the sims.\n            Distance parameter should be used for object parts distance like\n            adjacent sits (low distance), corner sits (mid distance) and high\n            for anything above that. \n            ', tunable_type=bool, default=False, tuning_group=GroupNames.ANIMATION), 'acquire_social_group_as_resource': Tunable(description='\n            If checked, this interaction requires the Social Group to be an\n            available resource. No two interactions with this requirement can\n            ever run concurrently. If you want two Social Mixer interactions to\n            run at the same time, uncheck this.\n            \n            e.g. Foosball mixer interactions run concurrently, and therefore\n            have this unchecked.\n            ', tunable_type=bool, default=True), 'ignores_greetings': Tunable(description="\n            If True, this mixer will tell the Social Super Interaction to\n            ignore greetings if this interaction is the first social mixer\n            being run for that Social SI and the Sim should greet.\n            \n            Example: We don't want Introductions to also play greetings,\n            because greetings don't matter that early in the Sim's\n            relationship. We want to ignore greetings when two Sims first\n            meet.\n            ", tunable_type=bool, default=False), 'social_lock_out_time': OptionalTunable(description='\n            If enabled, this mixer is prevented from being run repeatedly for\n            any given Sim in the Social Group. For instanced, if this were set\n            to 8, no Sim would be able to run this mixer if any other Sim in the\n            Social Group had run it within the previous 8 Sim minutes.\n            ', tunable=TunableTuple(description='\n                Define how the lock out is supposed to work.\n                ', interval=TunableInterval(description='\n                    Time in sim minutes in which this affordance will not be\n                    valid for.\n                    ', tunable_type=TunableSimMinute, default_lower=1, default_upper=1, minimum=0), additional_affordances=TunableList(description='\n                    When this lock out hits, these additional affordances are\n                    also locked out. NOTE: These affordances are locked out for\n                    a duration defined by this interval.\n                    ', tunable=TunableReference(description='\n                        An affordance to also lock out.\n                        ', manager=services.affordance_manager(), class_restrictions='SocialMixerInteraction'))), tuning_group=GroupNames.MIXER)}

    @classproperty
    def is_social(cls):
        return True

    @property
    def social_group(self):
        if self.super_interaction is not None:
            return self.super_interaction.social_group

    @staticmethod
    def _tunable_tests_enabled():
        return tunable_tests_enabled

    @classmethod
    def _test(cls, target, context, *args, **kwargs):
        if context.sim is target:
            return TestResult(False, 'Social Mixer Interactions cannot target self!')
        if context.pick is not None:
            pick_target = context.pick.target if context.source == context.SOURCE_PIE_MENU else None
            if context.sim is pick_target:
                return TestResult(False, 'Social Mixer Interactions cannot target self!')
        return MixerInteraction._test(target, context, *args, **kwargs)

    @flexmethod
    def test(cls, inst, *args, **kwargs):
        if inst.social_group is not None:
            if inst.social_group.is_locked_out(inst.affordance):
                return TestResult(False, 'Social Mixer is locked out.')
        else:
            return TestResult(False, 'Social Mixer {} has no Social Group.', inst)
        return super(SocialMixerInteraction, inst if inst is not None and inst.social_group is not None and inst is not None else cls).test(*args, **kwargs)

    @classmethod
    def filter_mixer_targets(cls, super_interaction, *args, **kwargs):
        social_group = super_interaction.social_group if super_interaction is not None else None
        if social_group is not None and social_group.is_locked_out(cls):
            return
        return super().filter_mixer_targets(super_interaction, *args, **kwargs)

    def should_insert_in_queue_on_append(self):
        if super().should_insert_in_queue_on_append():
            return True
        if self.super_affordance is None:
            logger.error('{} being added to queue without a super interaction or super affordance', self)
            return False
        ui_group_tag = self.super_affordance.visual_type_override_data.group_tag
        if ui_group_tag == tag.Tag.INVALID:
            return False
        for si in self.sim.si_state:
            if si.visual_type_override_data.group_tag == ui_group_tag:
                return True
        return False

    def _can_share_asm(self):
        if self.target_type == TargetType.TARGET and self.super_interaction.target_type == TargetType.TARGET:
            linked_interaction_type = self.super_interaction.linked_interaction_type
            if linked_interaction_type is not None and linked_interaction_type is not self.super_interaction.affordance:
                return True
            elif self.target is not None and self.target.is_sim:
                return False
        elif self.target is not None and self.target.is_sim:
            return False
        return True

    def get_asm(self, *args, **kwargs):
        if self._can_share_asm():
            return super().get_asm(*args, **kwargs)
        return Interaction.get_asm(self, *args, **kwargs)

    def prepare_gen(self, timeline, **kwargs):
        if self.super_interaction is not None and self.super_interaction.is_finishing:
            return InteractionQueuePreparationStatus.FAILURE
        result = yield from super().prepare_gen(timeline, **kwargs)
        return result

    def perform_gen(self, timeline):
        if self.social_group is None:
            raise AssertionError('Social mixer interaction {} has no social group. [bhill]'.format(self))
        result = yield from super().perform_gen(timeline)
        return result

    def _build_outcome_sequence(self, *args, **kwargs):
        sequence = super()._build_outcome_sequence(*args, **kwargs)
        social_group = self.social_group
        if social_group is not None:

            def _surpress_social_group_update(_):
                social_group.suppress_social_group_update_message = True

            def _send_social_group_update(_):
                social_group.suppress_social_group_update_message = False
                social_group.on_social_context_changed()

        sequence = build_critical_section_with_finally(_surpress_social_group_update, sequence, _send_social_group_update)
        return sequence

    def build_basic_elements(self, sequence=()):
        sequence = super().build_basic_elements(sequence=sequence)
        if self.super_interaction.social_group is not None:
            listen_animation_factory = self.super_interaction.listen_animation
        else:
            listen_animation_factory = None
            for group in self.sim.get_groups_for_sim_gen():
                si = group.get_si_registered_for_sim(self.sim)
                if si is not None:
                    listen_animation_factory = si.listen_animation
                    break
        if listen_animation_factory is not None:
            for sim in self.required_sims():
                if sim is self.sim:
                    pass
                else:
                    sequence = listen_animation_factory(sim.animation_interaction, sequence=sequence)
                    sequence = with_skippable_animation_time((sim,), sequence=sequence)

        def defer_cancel_around_sequence_gen(s, timeline):
            deferred_sis = []
            for sim in self.required_sims():
                if sim is self.sim or not self.social_group is None:
                    if sim not in self.social_group:
                        pass
                    else:
                        sis = self.social_group.get_sis_registered_for_sim(sim)
                        if sis:
                            deferred_sis.extend(sis)
            with self.super_interaction.cancel_deferred(deferred_sis):
                result = yield from element_utils.run_child(timeline, s)
                return result

        sequence = functools.partial(defer_cancel_around_sequence_gen, sequence)
        if self.target_type & TargetType.ACTOR:
            return element_utils.build_element(sequence)
        if self.target_type & TargetType.TARGET and self.target is not None:
            if self.social_group is not None:
                sequence = self.social_group.with_target_focus(self.sim, self.sim, self.target, sequence)
        elif self.social_group is not None:
            sequence = self.social_group.with_social_focus(self.sim, self.sim, self.required_sims(), sequence)
        else:
            for social_group in self.sim.get_groups_for_sim_gen():
                sequence = social_group.with_social_focus(self.sim, self.sim, self.required_sims(), sequence)
        return element_utils.build_element(sequence)

    def cancel_parent_si_for_participant(self, participant_type, finishing_type, cancel_reason_msg, **kwargs):
        social_group = self.social_group
        if social_group is None:
            return
        participants = self.get_participants(participant_type)
        for sim in participants:
            if sim is not None:
                social_group.remove(sim)
        group_tag = self.super_interaction.visual_type_override_data.group_tag
        if group_tag != Tag.INVALID:
            for si in self.sim.si_state:
                if si is not self.super_interaction and si.visual_type_override_data.group_tag == group_tag:
                    social_group = si.social_group
                    if social_group is not None:
                        for sim in participants:
                            if sim in social_group:
                                social_group.remove(sim)

    @flexmethod
    def get_participants(cls, inst, participant_type:ParticipantType, sim=DEFAULT, **kwargs) -> set:
        inst_or_cls = inst if inst is not None else cls
        result = super(MixerInteraction, inst_or_cls).get_participants(participant_type, sim=sim, **kwargs)
        result = set(result)
        sim = inst.sim if sim is DEFAULT else sim
        if inst.target_type & TargetType.GROUP:
            for other_sim in itertools.chain(*list(sim.get_groups_for_sim_gen())):
                if other_sim is sim:
                    pass
                elif other_sim.ignore_group_socials(excluded_group=inst.social_group):
                    pass
                else:
                    result.add(other_sim)
        return tuple(result)

    def _trigger_interaction_start_event(self):
        super()._trigger_interaction_start_event()
        target_sim = self.get_participant(ParticipantType.TargetSim)
        if target_sim is not None:
            services.get_event_manager().process_event(test_events.TestEvent.InteractionStart, sim_info=target_sim.sim_info, interaction=self, custom_keys=self.get_keys_to_process_events())
            self._register_target_event_auto_update()

    def setup_asm_default(self, asm, *args, **kwargs):
        result = super().setup_asm_default(asm, *args, **kwargs)
        if self.use_swing_distance_parameter:
            distance_param = PostureTransition.calculate_distance_param(self.sim, self.target)
            asm.set_parameter('distance', distance_param)
        return result

    def required_resources(self):
        resources = super().required_resources()
        if self.acquire_social_group_as_resource:
            resources.add(self.social_group)
        return resources
