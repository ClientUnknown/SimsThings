from animation.animation_element import animate_statesfrom balloon.balloon_enums import BalloonTypeEnum, BALLOON_TYPE_LOOKUPfrom balloon.balloon_request import BalloonRequestfrom balloon.tunable_balloon import TunableBalloonfrom element_utils import build_elementfrom interactions.utils.tunable_icon import TunableIconfrom objects.components.types import IDLE_COMPONENTfrom sims4.tuning.instances import TunedInstanceMetaclassfrom sims4.tuning.tunable import Tunable, TunableList, OptionalTunable, HasTunableReference, TunableInteractionAsmResourceKey, TunableTuple, TunableEnumEntryfrom sims4.tuning.tunable_base import SourceQueriesfrom singletons import DEFAULTimport animationimport elementsimport servicesimport sims4.logimport sims4.resourceslogger = sims4.log.Logger('ObjectAnimations', default_owner='rmccord')
class ObjectPose(HasTunableReference, metaclass=TunedInstanceMetaclass, manager=services.get_instance_manager(sims4.resources.Types.ANIMATION)):
    INSTANCE_TUNABLES = {'asm': TunableInteractionAsmResourceKey(description='\n            The animation state machine for this pose.\n            ', default=None), 'state_name': Tunable(description='\n            The animation state name for this pose.\n            ', tunable_type=str, default=None, source_location='asm', source_query=SourceQueries.ASMState)}

class ObjectAnimationElement(HasTunableReference, elements.ParentElement, metaclass=TunedInstanceMetaclass, manager=services.get_instance_manager(sims4.resources.Types.ANIMATION)):
    ASM_SOURCE = 'asm_key'
    INSTANCE_TUNABLES = {'repeat': Tunable(description='\n            If this is checked, then the begin_states will loop until the\n            controlling sequence (e.g. state change on idle component) ends. \n            At that point, end_states will play.\n            \n            This tunable allows you to create looping one-shot states. The\n            effects of this tunable on already looping states is undefined.\n            ', tunable_type=bool, default=False), 'balloon_data': OptionalTunable(description='\n            Information that will be used to create an element that represents\n            thought or speech balloons.\n            ', tunable=TunableTuple(icon=TunableIcon(description='\n                    Icon that will be used in the balloon. Object Animations\n                    elements only support Icon References.\n                    '), balloon_type=TunableEnumEntry(description='\n                    The visual style of the balloon background.\n                    ', tunable_type=BalloonTypeEnum, default=BalloonTypeEnum.SPEECH), overlay=OptionalTunable(description='\n                    The overlay of the balloon, if present.\n                    ', tunable=TunableIcon()), balloon_delay=Tunable(description='\n                    If set, the number of seconds after the start of the animation\n                    to trigger the balloon. A negative number will count backwards\n                    from the end of the animation.\n                    ', tunable_type=int, default=0), balloon_delay_random_offset=Tunable(description='\n                    The amount of randomization that added to balloon requests.\n                    Will always offset the delay time later and requires the delay\n                    time be set to a number. A value of 0 has no randomization.\n                    ', tunable_type=int, default=0))), 'end_states': TunableList(description='\n            A list of states to play after looping.\n            ', tunable=str, source_location=ASM_SOURCE, source_query=SourceQueries.ASMState), 'begin_states': TunableList(description='\n            A list of states to play.\n            ', tunable=str, source_location=ASM_SOURCE, source_query=SourceQueries.ASMState), 'initial_state': OptionalTunable(description='\n            The name of the initial state in the ASM you expect your actor to be\n            in when running this AnimationElement. If you do not tune this we\n            will use the entry state which is usually what you want.\n            ', tunable=Tunable(tunable_type=str, default=None, source_location='../' + ASM_SOURCE, source_query=SourceQueries.ASMState), disabled_value=DEFAULT, disabled_name='use_default', enabled_name='custom_state_name'), 'target_name': OptionalTunable(description='\n            If enabled, some portion of this object animation expects the actor\n            to interact with another object. The object must be set by whatever\n            system uses the ASM. In and of itself, the Idle component never sets\n            this actor.\n            ', tunable=Tunable(tunable_type=str, default=None, source_location='../' + ASM_SOURCE, source_query=SourceQueries.ASMActorAll)), 'actor_name': Tunable(description='\n            The name of the actor in the ASM.\n            ', tunable_type=str, default=None, source_location=ASM_SOURCE, source_query=SourceQueries.ASMActorAll), ASM_SOURCE: TunableInteractionAsmResourceKey(description='\n            The ASM to use.\n            ', default=None, category='asm')}

    def __init__(self, owner, use_asm_cache=True, target=None, **animate_kwargs):
        super().__init__()
        self.owner = owner
        self.target = target
        self.animate_kwargs = animate_kwargs
        self._use_asm_cache = use_asm_cache

    @classmethod
    def append_to_arb(cls, asm, arb):
        for state_name in cls.begin_states:
            asm.request(state_name, arb)

    @classmethod
    def append_exit_to_arb(cls, asm, arb):
        for state_name in cls.end_states:
            asm.request(state_name, arb)

    def get_asm(self, use_cache=True, **kwargs):
        idle_component = self.owner.get_component(IDLE_COMPONENT)
        if idle_component is None:
            logger.error('Trying to setup an object animation {}, {} on an object {} with no Idle Component.', self, self.asm_key, self.owner)
            return
        asm = idle_component.get_asm(self.asm_key, self.actor_name, use_cache=self._use_asm_cache and use_cache, **kwargs)
        if self.target_name is not None and self.target is not None:
            asm.add_potentially_virtual_actor(self.actor_name, self.owner, self.target_name, self.target)
        return asm

    def _run(self, timeline):
        if self.asm_key is None:
            return True
        asm = self.get_asm()
        if asm is None:
            return False
        if self.balloon_data is not None:
            sequence = self.animate_kwargs['sequence']
            if sequence is not None:
                self.animate_kwargs['sequence'] = (sequence, build_element(self.create_balloon_request(self.owner)))
            else:
                self.animation_kwargs['sequence'] = build_element(self.create_balloon_request(self.owner))
        return timeline.run_child(animate_states(asm, self.begin_states, self.end_states, repeat_begin_states=self.repeat, **self.animate_kwargs))

    def create_balloon_request(self, owner):
        (balloon_type, priority) = BALLOON_TYPE_LOOKUP[self.balloon_data.balloon_type]
        request = BalloonRequest(owner, self.balloon_data.icon, None, self.balloon_data.overlay, balloon_type, priority, TunableBalloon.BALLOON_DURATION, self.balloon_data.balloon_delay, self.balloon_data.balloon_delay_random_offset, None)
        return request
