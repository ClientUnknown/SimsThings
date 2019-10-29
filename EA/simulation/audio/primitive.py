from protocolbuffers import DistributorOps_pb2 as protocolsfrom protocolbuffers.Audio_pb2 import SoundStartfrom animation.awareness.awareness_enums import AwarenessChannelfrom animation.awareness.awareness_tuning import AwarenessSourceRequestfrom distributor.ops import GenericProtocolBufferOpfrom objects.components.state_change import StateChangefrom sims4.repr_utils import standard_angle_reprfrom sims4.tuning.tunable import TunableFactory, TunableResourceKey, TunablePackSafeResourceKey, OptionalTunable, Tunablefrom sims4.tuning.tunable_hash import TunableStringHash32from singletons import DEFAULTfrom uid import unique_idimport distributor.opsimport servicesimport sims4.loglogger = sims4.log.Logger('Audio')
@unique_id('channel')
class PlaySound(distributor.ops.ElementDistributionOpMixin):

    def __init__(self, target, sound_id, is_vox=False, joint_name_hash=None, play_on_active_sim_only=False, immediate=False):
        super().__init__(immediate=immediate)
        self.target = target
        if target is not None:
            if target.is_part:
                self.target = target.part_owner
            elif target.inventoryitem_component is not None:
                forward_to_owner_list = target.inventoryitem_component.forward_client_state_change_to_inventory_owner
                if StateChange.AUDIO_STATE in forward_to_owner_list:
                    inventory_owner = target.inventoryitem_component.inventory_owner
                    if inventory_owner is not None:
                        self.target = inventory_owner
        self.sound_id = sound_id
        self.is_vox = is_vox
        self.joint_name_hash = joint_name_hash
        self.play_on_active_sim_only = play_on_active_sim_only
        self.immediate = immediate
        self._manually_distributed = False
        self._awareness_request = None

    def __repr__(self):
        return standard_angle_repr(self, self.channel)

    @property
    def _is_distributed(self):
        return self.is_attached or self._manually_distributed

    def start(self):
        if not self._is_distributed:
            if self.target is not None:
                self._awareness_request = AwarenessSourceRequest(self.target, awareness_sources={AwarenessChannel.AUDIO_VOLUME: 1})
                self._awareness_request.start()
                self.attach(self.target)
            else:
                start_msg = self.build_sound_start_msg()
                system_distributor = distributor.system.Distributor.instance()
                generic_pb_op = GenericProtocolBufferOp(protocols.Operation.SOUND_START, start_msg)
                system_distributor.add_op_with_no_owner(generic_pb_op)
                self._manually_distributed = True

    def stop(self, *_, **__):
        if self._awareness_request is not None:
            self._awareness_request.stop()
            self._awareness_request = None
        if self.is_attached:
            self.detach()
        elif self._manually_distributed:
            self._stop_sound()
        else:
            logger.error("Attempting to stop a sound that wasn't distributed. target {}, soundID {}", self.target, self.sound_id, owner='sscholl')

    def _stop_sound(self):
        if self._is_distributed:
            if not services.current_zone().is_zone_shutting_down:
                op = distributor.ops.StopSound(self.target.id, self.channel, immediate=self.immediate)
                distributor.ops.record(self.target, op)
            self._manually_distributed = False

    def detach(self, *objects):
        self._stop_sound()
        super().detach(*objects)

    def build_sound_start_msg(self):
        start_msg = SoundStart()
        if self.target is not None:
            start_msg.object_id = self.target.id
        start_msg.channel = self.channel
        start_msg.sound_id = self.sound_id
        start_msg.is_vox = self.is_vox
        start_msg.play_on_active_sim_only = self.play_on_active_sim_only
        if self.joint_name_hash is not None:
            start_msg.joint_name_hash = self.joint_name_hash
        return start_msg

    def write(self, msg):
        start_msg = self.build_sound_start_msg()
        self.serialize_op(msg, start_msg, protocols.Operation.SOUND_START)

def play_tunable_audio(tunable_play_audio, owner=DEFAULT):
    if tunable_play_audio is None:
        logger.error('Cannot play an audio clip of type None.', owner='tastle')
        return
    if owner == DEFAULT:
        client = services.client_manager().get_first_client()
        if client.active_sim is None:
            owner = None
        else:
            owner = client.active_sim
    sound = tunable_play_audio(owner)
    sound.start()
    return sound

class TunablePlayAudio(TunableFactory):

    @staticmethod
    def _factory(owner, audio, joint_name_hash, play_on_active_sim_only, immediate):
        return PlaySound(owner, audio.instance, joint_name_hash=joint_name_hash, play_on_active_sim_only=play_on_active_sim_only, immediate=immediate)

    FACTORY_TYPE = _factory

    def __init__(self, **kwargs):
        super().__init__(audio=TunableResourceKey(description='\n                The sound to play.\n                ', default=None, resource_types=(sims4.resources.Types.PROPX,)), joint_name_hash=OptionalTunable(description="\n                Specify if the audio is attached to a slot and, if so, which\n                slot. Otherwise the audio will be attached to the object's \n                origin.\n                ", tunable=TunableStringHash32(description='\n                    The name of the slot this audio is attached to.\n                    ')), play_on_active_sim_only=Tunable(description='\n                If enabled, and audio target is Sim, the audio will only be \n                played on selected Sim. Otherwise it will be played regardless \n                Sim is selected or not.\n                \n                If audio target is Object, always set this to False. Otherwise\n                the audio will never be played.\n                \n                ex. This will be useful for Earbuds where we want to hear the\n                music only when the Sim is selected.\n                ', tunable_type=bool, default=False), immediate=Tunable(description='\n                If checked, this audio will be triggered immediately, nothing\n                will block.\n                \n                ex. Earbuds audio will be played immediately while \n                the Sim is routing or animating.\n                ', tunable_type=bool, default=False), **kwargs)

class TunablePlayAudioAllPacks(TunablePackSafeResourceKey):

    def __init__(self, *, description='The sound to play.', **kwargs):
        super().__init__(*(None,), resource_types=(sims4.resources.Types.PROPX,), **kwargs)

    @property
    def validate_pack_safe(self):
        return False
