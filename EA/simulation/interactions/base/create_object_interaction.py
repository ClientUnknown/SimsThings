from animation.animation_utils import flush_all_animationsfrom carry.carry_elements import enter_carry_while_holdingfrom element_utils import build_critical_sectionfrom interactions import ParticipantTypefrom interactions.aop import AffordanceObjectPairfrom interactions.base.super_interaction import SuperInteractionfrom interactions.social.social_super_interaction import SocialSuperInteractionfrom interactions.utils.tested_variant import TunableTestedVariantfrom interactions.utils.tunable import TunableContinuationfrom objects.components.state import TunableStateValueReferencefrom objects.helpers.create_object_helper import CreateObjectHelperfrom postures import PostureTrackfrom sims4.tuning.tunable import TunableReference, OptionalTunable, TunableEnumEntry, TunableList, TunableTuple, TunableMapping, TunableFactoryfrom sims4.tuning.tunable_base import GroupNamesfrom singletons import DEFAULTimport element_utilsimport servicesimport sims4.loglogger = sims4.log.Logger('Carry')
class ObjectDefinition(TunableFactory):

    @staticmethod
    def verify_tunable_callback(instance_class, tunable_name, source, definition):
        if definition.cls is None or definition.cls.tuned_components.carryable is None:
            logger.error('{} is attempting to create {} as a carry, but its object tuning {} does not have a carryable component.', instance_class, definition, definition.cls)

    @staticmethod
    def factory(definition, **kwargs):
        return definition

    FACTORY_TYPE = factory

    def __init__(self, **kwargs):
        super().__init__(definition=TunableReference(description='\n                The definition of the object.\n                ', manager=services.definition_manager(), **kwargs), verify_tunable_callback=ObjectDefinition.verify_tunable_callback)

class CreateCarriedObjectMixin:
    INTERACTION_PARAM_KEY = 'CreateCarriedObjectRuntimeObjectDefinition'
    INSTANCE_TUNABLES = {'definition': OptionalTunable(description="\n            The object to create; this can be set at runtime.\n            \n            If 'runtime parameter' is chosen, it will look at the parameter \n            passed in at runtime to determine which object to create.\n            The primary use of the 'runtime parameter' option is if\n            the interaction is pushed from code so consult a GPE before using it.\n            ", tunable=TunableTestedVariant(description='\n                The object to create.\n                ', tunable_type=ObjectDefinition(pack_safe=True)), tuning_group=GroupNames.CREATE_CARRYABLE, disabled_name='runtime_parameter', enabled_name='tuned_definition', enabled_by_default=True), 'carry_track_override': OptionalTunable(description='\n            If enabled, specify which carry track the Sim must use to carry the\n            created object.\n            ', tuning_group=GroupNames.CREATE_CARRYABLE, tunable=TunableEnumEntry(description='\n                Which hand to carry the object in.\n                ', tunable_type=PostureTrack, default=PostureTrack.RIGHT)), 'initial_states': TunableList(description='\n            A list of states to apply to the finished object as soon as it is\n            created.\n            ', tuning_group=GroupNames.CREATE_CARRYABLE, tunable=TunableStateValueReference()), 'continuation': SuperInteraction.TunableReference(description='\n            An interaction to push as a continuation to the carry.\n            ', allow_none=True), 'continuation_with_affordance_overrides': OptionalTunable(description="\n            If enabled, allows you to specify a continuation to the\n            carry based on a participant's object definition.\n            This continuation will be pushed in addition to the tunable continuation,\n            although you will rarely need to tune both at the same time.\n            ", tunable=TunableTuple(continuation=TunableContinuation(description='\n                    A tunable continuation to push based on the parameters provided.\n                    '), participant=TunableEnumEntry(description='\n                    When using the affordance_override mapping, this\n                    is the participant we will use to get the definition.\n                    ', tunable_type=ParticipantType, default=ParticipantType.PickedObject), affordance_override=TunableMapping(description="\n                    Based on the participants's object definition, you can override\n                    the affordance on the tunable continuation.\n                    ", key_type=TunableReference(description='\n                        The object definition to look for.\n                        ', manager=services.definition_manager()), value_type=SuperInteraction.TunableReference())), tuning_group=GroupNames.CREATE_CARRYABLE)}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._chosen_definition = None

    @property
    def create_target(self):
        return self._get_chosen_definition()

    def _get_chosen_definition(self):
        if self._chosen_definition is None:
            if self.definition is None:
                self._chosen_definition = self.interaction_parameters.get(self.INTERACTION_PARAM_KEY, None)
            else:
                self._chosen_definition = self.definition(resolver=self.get_resolver())
        return self._chosen_definition

    def _get_create_continuation_affordance(self):

        def create_continuation_affordance():
            context = self.context.clone_for_continuation(self)
            aop = AffordanceObjectPair(self.continuation, self.created_target, self.continuation, None)
            return (aop, context)

        def create_continuation_affordance_with_overrides():
            obj = self.get_participant(self.continuation_with_affordance_overrides.participant)
            if obj is not None:
                affordance_override = self.continuation_with_affordance_overrides.affordance_override.get(obj.definition)
            else:
                affordance_override = None
            interaction_parameters = {}
            if 'picked_item_ids' in self.interaction_parameters:
                interaction_parameters['picked_item_ids'] = self.interaction_parameters['picked_item_ids']
            for continuation in reversed(self.continuation_with_affordance_overrides.continuation):
                local_actors = self.get_participants(continuation.actor)
                if self.sim in local_actors:
                    aops_and_context = self.get_continuation_aop_and_context(continuation, self.sim, affordance_override=affordance_override, **interaction_parameters)
                    if aops_and_context:
                        return aops_and_context
            return (None, None)

        if self.continuation_with_affordance_overrides is not None:
            return create_continuation_affordance_with_overrides
        elif self.continuation is not None:
            return create_continuation_affordance

    def build_basic_content(self, sequence, **kwargs):
        super_build_basic_content = super().build_basic_content

        def setup_object(obj):
            for initial_state in reversed(self.initial_states):
                obj.set_state(initial_state.state, initial_state)
            obj.set_household_owner_id(self.sim.household.id)

        self._object_create_helper = CreateObjectHelper(self.sim, self._get_chosen_definition(), self, init=setup_object, tag='CreateCarriedObjectMixin')

        def claim_object(*_, **__):
            self._object_create_helper.claim()

        def set_carry_target(_):
            if self.carry_track_override:
                self.track = self.carry_track_override
            else:
                self.track = DEFAULT
            if self.track is None:
                return False
            self.map_create_target(self.created_target)

        def enter_carry(timeline):
            result = yield from element_utils.run_child(timeline, enter_carry_while_holding(self, self.created_target, callback=claim_object, create_si_fn=self._get_create_continuation_affordance(), track=self.track, sequence=build_critical_section(super_build_basic_content(sequence, **kwargs), flush_all_animations)))
            return result

        return (self._object_create_helper.create(set_carry_target, enter_carry), lambda _: self._object_create_helper.claimed)

class CreateCarriedObjectSuperInteraction(CreateCarriedObjectMixin, SuperInteraction):
    pass

class CreateCarriedObjectSocialSuperInteraction(CreateCarriedObjectMixin, SocialSuperInteraction):
    pass
