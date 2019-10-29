from protocolbuffers import Audio_pb2from protocolbuffers.DistributorOps_pb2 import Operationfrom distributor.ops import GenericProtocolBufferOpfrom distributor.system import Distributorfrom element_utils import build_critical_sectionfrom interactions.aop import AffordanceObjectPairfrom interactions.base.immediate_interaction import ImmediateSuperInteractionfrom interactions.base.super_interaction import SuperInteractionfrom interactions.interaction_finisher import FinishingTypefrom interactions.utils.animation_reference import TunableAnimationReferencefrom interactions.utils.conditional_animation import conditional_animationfrom objects.components.state import TunableStateTypeReference, with_on_state_changedfrom objects.components.state_change import StateChangefrom sims4.tuning.tunable import TunableReference, Tunable, TunableTuplefrom sims4.utils import flexmethodimport element_utilsimport event_testing.state_testsimport objects.components.stateimport servicesimport sims4logger = sims4.log.Logger('Stereo')
class ListenSuperInteraction(SuperInteraction):
    INSTANCE_TUNABLES = {'required_station': objects.components.state.TunableStateValueReference(description='\n            The station that this affordance listens to.\n            '), 'remote_animation': TunableAnimationReference(description='\n            The animation for using the stereo remote.\n            '), 'off_state': objects.components.state.TunableStateValueReference(description='\n            The channel that represents the off state.\n            ')}
    CHANGE_CHANNEL_XEVT_ID = 101

    def ensure_state(self, desired_station):
        return conditional_animation(self, desired_station, self.CHANGE_CHANNEL_XEVT_ID, self.affordance.remote_animation)

    def _changed_state_callback(self, target, state, old_value, new_value):
        if new_value != self.off_state:
            object_callback = getattr(new_value, 'on_interaction_canceled_from_state_change', None)
            if object_callback is not None:
                object_callback(self)
        self.cancel(FinishingType.OBJECT_CHANGED, cancel_reason_msg='state: interaction canceled on state change ({} != {})'.format(new_value.value, self.required_station.value))

    def _run_interaction_gen(self, timeline):
        result = yield from element_utils.run_child(timeline, build_critical_section(self.ensure_state(self.affordance.required_station), objects.components.state.with_on_state_changed(self.target, self.affordance.required_station.state, self._changed_state_callback, super()._run_interaction_gen)))
        return result

class CancelOnStateChangeInteraction(SuperInteraction):
    INSTANCE_TUNABLES = {'cancel_state_test': event_testing.state_tests.TunableStateTest(description="the state test to run when the object's state changes. If this test passes, the interaction will cancel")}

    def _run_interaction_gen(self, timeline):
        result = yield from element_utils.run_child(timeline, element_utils.build_element([self._cancel_on_state_test_pass(self.cancel_state_test, super()._run_interaction_gen)]))
        return result

    def _cancel_on_state_test_pass(self, cancel_on_state_test, *sequence):
        value = cancel_on_state_test.value

        def callback_fn(target, state, old_value, new_value):
            resolver = self.get_resolver(target=target)
            if resolver(cancel_on_state_test):
                self.cancel(FinishingType.OBJECT_CHANGED, cancel_reason_msg='state: interaction canceled on state change because new state:{} {} required state:{}'.format(new_value, cancel_on_state_test.operator, value))
                object_callback = getattr(new_value, 'on_interaction_canceled_from_state_change', None)
                if object_callback is not None:
                    object_callback(self)

        return with_on_state_changed(self.target, value.state, callback_fn, sequence)

class SkipToNextSongSuperInteraction(ImmediateSuperInteraction):
    INSTANCE_TUNABLES = {'audio_state_type': TunableStateTypeReference(description='The state type that when changed, will change the audio on the target object. This is used to get the audio channel to advance the playlist.')}

    def _run_gen(self, timeline):
        play_audio_primative = self.target.get_component_managed_state_distributable('audio_state', self.affordance.audio_state_type)
        if play_audio_primative is not None:
            msg = Audio_pb2.SoundSkipToNext()
            msg.object_id = self.target.id
            if self.target.inventoryitem_component is not None:
                forward_to_owner_list = self.target.inventoryitem_component.forward_client_state_change_to_inventory_owner
                if self.target.inventoryitem_component.inventory_owner is not None:
                    msg.object_id = self.target.inventoryitem_component.inventory_owner.id
            msg.channel = play_audio_primative.channel
            distributor = Distributor.instance()
            distributor.add_op_with_no_owner(GenericProtocolBufferOp(Operation.OBJECT_AUDIO_PLAYLIST_SKIP_TO_NEXT, msg))
        return True

class StereoPieMenuChoicesInteraction(ImmediateSuperInteraction):
    INSTANCE_TUNABLES = {'channel_state_type': objects.components.state.TunableStateTypeReference(description='The state used to populate the picker.'), 'push_additional_affordances': Tunable(bool, True, description="Whether to push affordances specified by the channel. This is used for stereo's turn on and listen to... interaction"), 'off_state_pie_menu_category': TunableTuple(off_state=objects.components.state.TunableStateValueReference(description='\n                The state value at which to display the name\n                ', allow_none=True), pie_menu_category=TunableReference(description='\n                Pie menu category so we can display a submenu for each outfit category\n                ', manager=services.get_instance_manager(sims4.resources.Types.PIE_MENU_CATEGORY), allow_none=True), pie_menu_category_on_forwarded=TunableReference(description='\n                Pie menu category so when this interaction is forwarded from inventory\n                object to inventory owner.\n                ', manager=services.get_instance_manager(sims4.resources.Types.PIE_MENU_CATEGORY), allow_none=True))}

    def __init__(self, aop, context, audio_channel=None, **kwargs):
        super().__init__(aop, context, **kwargs)
        self.audio_channel = audio_channel

    @flexmethod
    def get_pie_menu_category(cls, inst, stereo=None, from_inventory_to_owner=False, **interaction_parameters):
        inst_or_cls = inst if inst is not None else cls
        if stereo is not None:
            current_state = stereo.get_state(inst_or_cls.channel_state_type)
            if current_state is inst_or_cls.off_state_pie_menu_category.off_state:
                if from_inventory_to_owner:
                    return inst_or_cls.off_state_pie_menu_category.pie_menu_category_on_forwarded
                return inst_or_cls.off_state_pie_menu_category.pie_menu_category
        if from_inventory_to_owner:
            return inst_or_cls.category_on_forwarded
        return inst_or_cls.category

    @flexmethod
    def _get_name(cls, inst, *args, audio_channel=None, **interaction_parameters):
        if inst is not None:
            return inst.audio_channel.display_name
        return audio_channel.display_name

    @classmethod
    def potential_interactions(cls, target, context, from_inventory_to_owner=False, **kwargs):
        for client_state in target.get_client_states(cls.channel_state_type):
            if client_state.show_in_picker and client_state.test_channel(target, context):
                yield AffordanceObjectPair(cls, target, cls, None, stereo=target, audio_channel=client_state, from_inventory_to_owner=from_inventory_to_owner)

    def _run_interaction_gen(self, timeline):
        self.audio_channel.activate_channel(interaction=self, push_affordances=self.push_additional_affordances)
