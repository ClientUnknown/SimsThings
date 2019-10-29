from animation import animation_constantsfrom animation.arb_element import distribute_arb_elementfrom interactions.social.social_mixer_interaction import SocialMixerInteractionfrom sims.sim_info_types import Agefrom sims4.tuning.geometric import TunableVector3from sims4.tuning.tunable import TunableRange, OptionalTunable, TunableTuple, Tunable, TunableMapping, TunableEnumEntryfrom vfx import PlayEffectimport animationimport servicesimport sims4.mathlogger = sims4.log.Logger('SocialThrow', default_owner='camilogarcia')
class SocialThrowMixerInteraction(SocialMixerInteraction):
    INSTANCE_TUNABLES = {'throw_impact_data': OptionalTunable(description='\n            If enabled, the object thrown will trigger a reaction at a\n            specific timing of the throw on the target.\n            If disabled, throw will happen but target will not react.\n            ', tunable=TunableTuple(description='\n                Specific tuning defining the target reaction.\n                ', event_id=TunableRange(description='\n                    Id number of the event the ballistic controller will throw\n                    to trigger the reaction.\n                    ', tunable_type=int, default=123, minimum=1, maximum=1000), destroy_event_id=TunableRange(description='\n                    Id number of the event the for the thrown object to be\n                    destroyed.\n                    By default, ballistic controller has an event at 668 at the\n                    end of the throw, unless animation requests it, that\n                    should be used. \n                    ', tunable_type=int, default=668, minimum=1, maximum=1000), event_timing_offset=TunableRange(description='\n                    Offset in seconds when the event_id should trigger with\n                    reference to the ending of the throw.\n                    This means that a value of 0.2 will trigger this event 0.2\n                    seconds before the object thrown hits its target. \n                    ', tunable_type=float, default=0.2, minimum=0.0, maximum=10.0), impact_effect=OptionalTunable(description='\n                    When enabled, effect will play on the thrown object \n                    position at the time given by event_timing_offset.\n                    Effect will not be parented, this is to trigger effects\n                    like a snowball explosion etc.\n                    ', tunable=PlayEffect.TunableFactory(description='\n                        Effect to play.\n                        '), enabled_name='play_effect', disabled_name='no_effect'), asm_state_name=Tunable(description='\n                    State name that will be called on the ASM of the mixer \n                    when the impact happens.\n                    ', tunable_type=str, default=None), impact_offset=TunableMapping(description='\n                    Offsets for the impact position by age of the target Sim.\n                    ', key_type=TunableEnumEntry(description='\n                        Age for which this offset should be applied.\n                        ', tunable_type=Age, default=Age.YOUNGADULT), value_type=TunableVector3(description='\n                        Offset from the impact position where the ballistic\n                        controller should aim the object.\n                        For example, for an impact on a Sims feet, offset should \n                        be (0,0,0), but if we want a miss or another part we \n                        may want to push it higher.\n                        ', default=sims4.math.Vector3.ZERO())))), 'social_group_scoring': OptionalTunable(description='\n            If enabled, the thrower and target of this group will have an \n            additional score to be the next person that generates the social\n            adjustment.\n            The higher the value, the more likely they will move after this\n            mixer has ran.\n            ', tunable=TunableTuple(description='\n                Thrower and target tuning to affect the adjustment scoring.\n                ', thrower_score=TunableRange(description='\n                    Score to be added on the weight the thrower of this\n                    mixer to be more likely to move on the next social\n                    adjustment. \n                    ', tunable_type=int, default=0, minimum=0, maximum=10), receiver_score=TunableRange(description='\n                    Score to be added on the weight the receiver of this\n                    mixer to be more likely to move on the next social\n                    adjustment. \n                    ', tunable_type=int, default=0, minimum=0, maximum=10)))}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._throw_asm = None
        self._finished = False

    @classmethod
    def get_mixer_key_override(cls, target):
        return target.id

    def on_throw_impact(self, event_data):
        if self._throw_asm is None or self._finished:
            return
        if self._finished or self.throw_impact_data.asm_state_name is not None:
            impact_arb = animation.arb.Arb(additional_blockers={self.sim})
            self._throw_asm.request(self.throw_impact_data.asm_state_name, impact_arb)
            distribute_arb_element(impact_arb, master=self.target)
        self._finished = True

    def on_throw_destroy(self, event_data):
        prop_id = event_data.event_data.get('event_actor_id')
        if prop_id is not None:
            if self.throw_impact_data.impact_effect is not None:
                thrown_obj = services.prop_manager().get(prop_id)
                if thrown_obj is not None:
                    fade_out_vfx = self.throw_impact_data.impact_effect(thrown_obj)
                    fade_out_vfx.start_one_shot()
            self.animation_context.destroy_prop_from_actor_id(prop_id)

    def build_basic_content(self, *args, **kwargs):
        if self.throw_impact_data is not None:
            self.store_event_handler(self.on_throw_impact, handler_id=self.throw_impact_data.event_id)
            self.store_event_handler(self.on_throw_destroy, handler_id=self.throw_impact_data.destroy_event_id)
        if self.social_group_scoring is not None:
            self.super_interaction.social_group.update_adjustment_scoring(self.sim.id, self.social_group_scoring.thrower_score)
            self.super_interaction.social_group.update_adjustment_scoring(self.target.id, self.social_group_scoring.receiver_score)
        return super().build_basic_content(*args, **kwargs)

    def _get_facing_angle(self, actor, target):
        f1 = actor.forward
        f2 = target.position - actor.position
        angle = sims4.math.vector3_angle(f1) - sims4.math.vector3_angle(f2)
        if angle > sims4.math.PI:
            angle = angle - sims4.math.TWO_PI
        elif angle < -sims4.math.PI:
            angle = sims4.math.TWO_PI + angle
        return sims4.math.rad_to_deg(angle)

    def get_asm(self, *args, **kwargs):
        self._throw_asm = super().get_asm(*args, **kwargs)
        if self._finished:
            return self._throw_asm
        position_offset = self.throw_impact_data.impact_offset.get(self.target.sim_info.age)
        if position_offset is None:
            logger.error('Age {} not supported in throw tuning for mixer {}', self.target.sim_info.age, self)
            return self._throw_asm
        self._throw_asm.set_parameter(animation_constants.ASM_THROW_ANGLE, self._get_facing_angle(self.sim, self.target))
        self._throw_asm.set_parameter(animation_constants.ASM_HIT_ANGLE, -self._get_facing_angle(self.target, self.sim))
        target_position = self.target.position + self.target.orientation.transform_vector(position_offset)
        self._throw_asm.set_parameter(animation_constants.ASM_TARGET_TRANSLATION, target_position)
        self._throw_asm.set_parameter(animation_constants.ASM_TARGET_ORIENTATION, self.target.orientation)
        if self.throw_impact_data is not None:
            self._throw_asm.set_parameter(animation_constants.ASM_SCRIPT_EVENT_ID, self.throw_impact_data.event_id)
            self._throw_asm.set_parameter(animation_constants.ASM_SCRIPT_EVENT_PLACEMENT, self.throw_impact_data.event_timing_offset)
        self._throw_asm.set_parameter(animation_constants.ASM_LANDING_SURFACE, 'None')
        return self._throw_asm
