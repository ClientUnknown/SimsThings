import itertoolsimport protocolbuffersfrom audio.primitive import TunablePlayAudio, play_tunable_audiofrom interactions.utils.tunable_icon import TunableIconfrom sims4.localization import TunableLocalizedStringFactoryfrom sims4.tuning.tunable import OptionalTunable, Tunable, TunableEnumEntry, AutoFactoryInit, HasTunableSingletonFactory, TunableVariantfrom snippets import define_snippet, SCREEN_SLAMimport distributorimport enum
class ScreenSlamType(enum.Int, export=False):
    LEGACY = 0
    CUSTOM = 1

class ScreenSlamSizeEnum(enum.Int):
    SMALL = 0
    MEDIUM = 1
    LARGE = 2
    EXTRA_LARGE = 3

class ScreenSlamSizeBased(HasTunableSingletonFactory, AutoFactoryInit):
    FACTORY_TUNABLES = {'screen_slam_size': TunableEnumEntry(description='\n            Screen slam size.\n            ', tunable_type=ScreenSlamSizeEnum, default=ScreenSlamSizeEnum.MEDIUM)}

    def populate_screenslam_message(self, msg):
        msg.type = ScreenSlamType.LEGACY
        msg.size = self.screen_slam_size

class ScreenSlamKeyBased(HasTunableSingletonFactory, AutoFactoryInit):
    FACTORY_TUNABLES = {'key': Tunable(description='\n            Key to use for the screenslam. This will be typically tied\n            to what animation will play. Verify with your UI partner\n            what the correct value to use will be.\n        ', tunable_type=str, default='medium')}

    def populate_screenslam_message(self, msg):
        msg.type = ScreenSlamType.CUSTOM
        msg.ui_key = self.key

class ScreenSlamDisplayVariant(TunableVariant):

    def __init__(self, **kwargs):
        super().__init__(size_based=ScreenSlamSizeBased.TunableFactory(), key_based=ScreenSlamKeyBased.TunableFactory(), default='size_based', **kwargs)

class ScreenSlam(HasTunableSingletonFactory, AutoFactoryInit):
    FACTORY_TUNABLES = {'display_type': ScreenSlamDisplayVariant(), 'title': OptionalTunable(description='\n            Title of the screen slam.\n            ', tunable=TunableLocalizedStringFactory()), 'text': OptionalTunable(description='"\n            Text of the screen slam.\n            ', tunable=TunableLocalizedStringFactory()), 'icon': OptionalTunable(description=',\n            Icon to be displayed for the screen Slam.\n            ', tunable=TunableIcon()), 'audio_sting': OptionalTunable(description='\n            A sting to play at the same time as the screen slam.\n            ***Some screen slams may appear to play a sting, but the audio is\n            actually tuned on something else.  Example: On CareerLevel tuning\n            there already is a tunable, Promotion Audio Sting, to trigger a\n            sting, so one is not necessary on the screen slam.  Make sure to\n            avoid having to stings play simultaneously.***\n            ', tunable=TunablePlayAudio()), 'active_sim_only': Tunable(description='\n            If true, the screen slam will be only be shown if the active Sim\n            triggers it.\n            ', tunable_type=bool, default=True)}

    def send_screen_slam_message(self, sim_info, *localization_tokens):
        msg = protocolbuffers.UI_pb2.UiScreenSlam()
        self.display_type.populate_screenslam_message(msg)
        if self.text is not None:
            msg.name = self.text(*(token for token in itertools.chain(localization_tokens)))
        if sim_info is not None:
            msg.sim_id = sim_info.sim_id
        if self.icon is not None:
            msg.icon.group = self.icon.group
            msg.icon.instance = self.icon.instance
            msg.icon.type = self.icon.type
        if self.title is not None:
            msg.title = self.title(*(token for token in itertools.chain(localization_tokens)))
        if self.active_sim_only and sim_info is not None and sim_info.is_selected or not self.active_sim_only:
            distributor.shared_messages.add_message_if_player_controlled_sim(sim_info, protocolbuffers.Consts_pb2.MSG_UI_SCREEN_SLAM, msg, False)
            if self.audio_sting is not None:
                play_tunable_audio(self.audio_sting)
(TunableScreenSlamReference, TunableScreenSlamSnippet) = define_snippet(SCREEN_SLAM, ScreenSlam.TunableFactory())