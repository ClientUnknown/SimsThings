from distributor.ops import GenericProtocolBufferOpfrom distributor.shared_messages import add_object_message, IconInfoDatafrom distributor.system import Distributorfrom event_testing import test_eventsfrom event_testing.resolver import SingleSimResolverfrom interactions import ParticipantTypefrom interactions.utils.tunable_icon import TunableIconfrom interactions.utils.tunable_provided_affordances import TunableProvidedAffordancesfrom objects.mixins import ProvidedAffordanceDatafrom protocolbuffers import Commodities_pb2from protocolbuffers import SimObjectAttributes_pb2 as protocolsfrom protocolbuffers.Consts_pb2 import MSG_SIM_SKILL_UPDATEfrom protocolbuffers.DistributorOps_pb2 import Operationfrom rewards.reward_enums import RewardDestinationfrom sims.sim_info_types import Agefrom sims.sim_info_utils import apply_super_affordance_commodity_flags, remove_super_affordance_commodity_flagsfrom sims4.localization import TunableLocalizedStringfrom sims4.math import Thresholdfrom sims4.tuning.dynamic_enum import DynamicEnumfrom sims4.tuning.geometric import TunableVector2, TunableCurvefrom sims4.tuning.instances import HashedTunedInstanceMetaclassfrom sims4.tuning.tunable import Tunable, TunableList, TunableEnumEntry, TunableMapping, TunableSet, TunableTuple, OptionalTunable, TunableInterval, TunableReference, TunableRange, HasTunableReference, TunablePackSafeReferencefrom sims4.tuning.tunable_base import ExportModes, GroupNamesfrom sims4.utils import classproperty, flexmethod, constpropertyfrom singletons import DEFAULTfrom statistics.base_statistic import StatisticChangeDirectionfrom statistics.progressive_statistic_callback_mixin import ProgressiveStatisticCallbackMixinfrom statistics.tunable import TunableStatAsmParamfrom tag import TunableTagfrom ui.ui_dialog import UiDialogResponsefrom ui.ui_dialog_notification import UiDialogNotificationimport cachesimport collectionsimport distributorimport enumimport gsi_handlers.sim_handlers_logimport operatorimport rewards.reward_tuningimport servicesimport sims4.logimport statistics.continuous_statistic_tuningimport tagimport telemetry_helperimport ui.screen_slamlogger = sims4.log.Logger('Skills')TELEMETRY_GROUP_SKILLS = 'SKIL'TELEMETRY_HOOK_SKILL_LEVEL_UP = 'SKLU'TELEMETRY_HOOK_SKILL_INTERACTION = 'SKIA'TELEMETRY_HOOK_SKILL_INTERACTION_FIRST_TIME = 'SKIF'TELEMETRY_FIELD_SKILL_ID = 'skid'TELEMETRY_FIELD_SKILL_LEVEL = 'sklv'TELEMETRY_FIELD_SKILL_AFFORDANCE = 'skaf'TELEMETRY_FIELD_SKILL_AFFORDANCE_SUCCESS = 'safs'TELEMETRY_FIELD_SKILL_AFFORDANCE_VALUE_ADD = 'safv'TELEMETRY_INTERACTION_NOT_AVAILABLE = 'not_available'skill_telemetry_writer = sims4.telemetry.TelemetryWriter(TELEMETRY_GROUP_SKILLS)MAX_SKILL_LEVEL = 20
class SkillLevelType(enum.Int):
    MAJOR = 0
    MINOR = 1
    CHILD = 2
    TEEN = 3
    VAMPIRE_LORE = 4
    TODDLER = 5
    POTTY = 6

class SkillEffectiveness(DynamicEnum):
    STANDARD = 0

class TunableSkillMultiplier(TunableTuple):

    def __init__(self, **kwargs):
        super().__init__(affordance_list=TunableList(description='\n                List of affordances this multiplier will effect.\n                ', tunable=TunableReference(manager=services.affordance_manager(), reload_dependent=True)), curve=TunableCurve(description='\n                Tunable curve where the X-axis defines the skill level, and\n                the Y-axis defines the associated multiplier.\n                ', x_axis_name='Skill Level', y_axis_name='Multiplier'), use_effective_skill=Tunable(description='\n                If checked, this modifier will look at the current\n                effective skill value.  If unchecked, this modifier will\n                look at the actual skill value.\n                ', tunable_type=bool, needs_tuning=True, default=True), **kwargs)

class Skill(HasTunableReference, ProgressiveStatisticCallbackMixin, statistics.continuous_statistic_tuning.TunedContinuousStatistic, metaclass=HashedTunedInstanceMetaclass, manager=services.get_instance_manager(sims4.resources.Types.STATISTIC)):
    SKILL_LEVEL_LIST = TunableMapping(description='\n        A mapping defining the level boundaries for each skill type.\n        ', key_type=SkillLevelType, value_type=TunableList(description='\n            The level boundaries for skill type, specified as a delta from the\n            previous value.\n            ', tunable=Tunable(tunable_type=int, default=0)), tuple_name='SkillLevelListMappingTuple', export_modes=ExportModes.All)
    SKILL_EFFECTIVENESS_GAIN = TunableMapping(description='\n        Skill gain points based on skill effectiveness.\n        ', key_type=SkillEffectiveness, value_type=TunableCurve())
    DYNAMIC_SKILL_INTERVAL = TunableRange(description='\n        Interval used when dynamic loot is used in a\n        PeriodicStatisticChangeElement.\n        ', tunable_type=float, default=1, minimum=1)
    INSTANCE_TUNABLES = {'stat_name': TunableLocalizedString(description='\n            The name of this skill.\n            ', export_modes=ExportModes.All, tuning_group=GroupNames.UI), 'skill_description': TunableLocalizedString(description="\n            The skill's normal description.\n            ", export_modes=ExportModes.All, tuning_group=GroupNames.UI), 'locked_description': TunableLocalizedString(description="\n            The skill description when it's locked.\n            ", allow_none=True, export_modes=ExportModes.All, tuning_group=GroupNames.UI), 'icon': TunableIcon(description='\n            Icon to be displayed for the Skill.\n            ', export_modes=ExportModes.All, tuning_group=GroupNames.UI), 'tooltip_icon_list': TunableList(description='\n            A list of icons to show in the tooltip of this\n            skill.\n            ', tunable=TunableIcon(description='\n                Icon that is displayed what types of objects help\n                improve this skill.\n                '), export_modes=(ExportModes.ClientBinary,), tuning_group=GroupNames.UI), 'tutorial': TunableReference(description='\n            Tutorial instance for this skill. This will be used to bring up the\n            skill lesson from the first notification for Sim to know this skill.\n            ', manager=services.get_instance_manager(sims4.resources.Types.TUTORIAL), allow_none=True, class_restrictions=('Tutorial',), tuning_group=GroupNames.UI), 'priority': Tunable(description="\n            Skill priority.  Higher priority skills will trump other skills when\n            being displayed on the UI. When a Sim gains multiple skills at the\n            same time, only the highest priority one will display a progress bar\n            over the Sim's head.\n            ", tunable_type=int, default=1, export_modes=ExportModes.All, tuning_group=GroupNames.UI), 'next_level_teaser': TunableList(description='\n            Tooltip which describes what the next level entails.\n            ', tunable=TunableLocalizedString(), export_modes=(ExportModes.ClientBinary,), tuning_group=GroupNames.UI), 'mood_id': TunableReference(description='\n            When this mood is set and active sim matches mood, the UI will\n            display a special effect on the skill bar to represent that this\n            skill is getting a bonus because of the mood.\n            ', manager=services.mood_manager(), allow_none=True, export_modes=ExportModes.All, tuning_group=GroupNames.UI), 'stat_asm_param': TunableStatAsmParam.TunableFactory(tuning_group=GroupNames.ANIMATION), 'hidden': Tunable(description='\n            If checked, this skill will be hidden.\n            ', tunable_type=bool, default=False, export_modes=ExportModes.All, tuning_group=GroupNames.AVAILABILITY), 'update_client_for_npcs': Tunable(description="\n            Whether this skill will send update messages to the client\n            for non-active household sims (NPCs).\n            \n            e.g. A toddler's communication skill determines the VOX they use, so\n            the client needs to know the skill level for all toddlers in order\n            for this work properly.\n            ", tunable_type=bool, default=False, tuning_group=GroupNames.UI), 'is_default': Tunable(description='\n            Whether Sim will default has this skill.\n            ', tunable_type=bool, default=False, tuning_group=GroupNames.AVAILABILITY), 'ages': TunableSet(description='\n            Allowed ages for this skill.\n            ', tunable=TunableEnumEntry(tunable_type=Age, default=Age.ADULT, export_modes=ExportModes.All), tuning_group=GroupNames.AVAILABILITY), 'ad_data': TunableList(description='\n            A list of Vector2 points that define the desire curve for this\n            commodity.\n            ', tunable=TunableVector2(description='\n                Point on a Curve\n                ', default=sims4.math.Vector2(0, 0)), tuning_group=GroupNames.AUTONOMY), 'weight': Tunable(description="\n            The weight of the Skill with regards to autonomy.  It's ignored for\n            the purposes of sorting stats, but it's applied when scoring the\n            actual statistic operation for the SI.\n            ", tunable_type=float, default=0.5, tuning_group=GroupNames.AUTONOMY), 'statistic_multipliers': TunableMapping(description='\n            Multipliers this skill applies to other statistics based on its\n            value.\n            ', key_type=TunableReference(description='\n                The statistic this multiplier will be applied to.\n                ', manager=services.statistic_manager(), reload_dependent=True), value_type=TunableTuple(curve=TunableCurve(description='\n                    Tunable curve where the X-axis defines the skill level, and\n                    the Y-axis defines the associated multiplier.\n                    ', x_axis_name='Skill Level', y_axis_name='Multiplier'), direction=TunableEnumEntry(description="\n                    Direction where the multiplier should work on the\n                    statistic.  For example, a tuned decrease for an object's\n                    brokenness rate will not also increase the time it takes to\n                    repair it.\n                    ", tunable_type=StatisticChangeDirection, default=StatisticChangeDirection.INCREASE), use_effective_skill=Tunable(description='\n                    If checked, this modifier will look at the current\n                    effective skill value.  If unchecked, this modifier will\n                    look at the actual skill value.\n                    ', tunable_type=bool, needs_tuning=True, default=True)), tuning_group=GroupNames.MULTIPLIERS), 'success_chance_multipliers': TunableList(description='\n            Multipliers this skill applies to the success chance of\n            affordances.\n            ', tunable=TunableSkillMultiplier(), tuning_group=GroupNames.MULTIPLIERS), 'monetary_payout_multipliers': TunableList(description='\n            Multipliers this skill applies to the monetary payout amount of\n            affordances.\n            ', tunable=TunableSkillMultiplier(), tuning_group=GroupNames.MULTIPLIERS), 'tags': TunableList(description='\n            The associated categories of the skill\n            ', tunable=TunableEnumEntry(tunable_type=tag.Tag, default=tag.Tag.INVALID, pack_safe=True), tuning_group=GroupNames.CORE), 'skill_level_type': TunableEnumEntry(description='\n            Skill level list to use.\n            ', tunable_type=SkillLevelType, default=SkillLevelType.MAJOR, export_modes=ExportModes.All, tuning_group=GroupNames.CORE), 'level_data': TunableMapping(description='\n            Level-specific information, such as notifications to be displayed to\n            level up.\n            ', key_type=int, value_type=TunableTuple(level_up_notification=UiDialogNotification.TunableFactory(description='\n                    The notification to display when the Sim obtains this level.\n                    The text will be provided two tokens: the Sim owning the\n                    skill and a number representing the 1-based skill level\n                    ', locked_args={'text_tokens': DEFAULT, 'icon': None, 'primary_icon_response': UiDialogResponse(text=None, ui_request=UiDialogResponse.UiDialogUiRequest.SHOW_SKILL_PANEL), 'secondary_icon': None}), level_up_screen_slam=OptionalTunable(description='\n                    Screen slam to show when reaches this skill level.\n                    Localization Tokens: Sim - {0.SimFirstName}, Skill Name - \n                    {1.String}, Skill Number - {2.Number}\n                    ', tunable=ui.screen_slam.TunableScreenSlamSnippet()), skill_level_buff=OptionalTunable(tunable=TunableReference(description='\n                        The buff to place on a Sim when they reach this specific\n                        level of skill.\n                        ', manager=services.buff_manager())), rewards=TunableList(description='\n                    A reward to give for achieving this level.\n                    ', tunable=rewards.reward_tuning.TunableSpecificReward(pack_safe=True)), loot=TunableList(description='\n                    A loot to apply for achieving this level.\n                    ', tunable=TunableReference(manager=services.get_instance_manager(sims4.resources.Types.ACTION), class_restrictions=('LootActions',))), super_affordances=TunableSet(description='\n                    Super affordances this adds to the Sim.\n                    ', tunable=TunableReference(description='\n                        A super affordance added to this Sim.\n                        ', manager=services.get_instance_manager(sims4.resources.Types.INTERACTION), class_restrictions=('SuperInteraction',), pack_safe=True)), target_super_affordances=TunableProvidedAffordances(description='\n                    Super affordances this adds to the target.\n                    ', locked_args={'target': ParticipantType.Object, 'carry_target': ParticipantType.Invalid, 'is_linked': False, 'unlink_if_running': False}), actor_mixers=TunableMapping(description='\n                    Mixers this adds to an associated actor object. (When targeting\n                    something else.)\n                    ', key_type=TunableReference(description='\n                        The super affordance these mixers are associated with.\n                        ', manager=services.get_instance_manager(sims4.resources.Types.INTERACTION), class_restrictions=('SuperInteraction',), pack_safe=True), value_type=TunableSet(description='\n                        Set of mixer affordances associated with the super affordance.\n                        ', tunable=TunableReference(description='\n                            Linked mixer affordance.\n                            ', manager=services.get_instance_manager(sims4.resources.Types.INTERACTION), category='asm', class_restrictions=('MixerInteraction',), pack_safe=True)))), tuning_group=GroupNames.CORE), 'age_up_skill_transition_data': OptionalTunable(description='\n            Data used to modify the value of a new skill based on the level\n            of this skill.\n            \n            e.g. Toddler Communication skill transfers into Child Social skill.\n            ', tunable=TunableTuple(new_skill=TunablePackSafeReference(description='\n                    The new skill.\n                    ', manager=services.get_instance_manager(sims4.resources.Types.STATISTIC)), skill_data=TunableMapping(description="\n                    A mapping between this skill's levels and the\n                    new skill's internal value.\n                    \n                    The keys are user facing skill levels.\n                    \n                    The values are the internal statistic value, not the user\n                    facing skill level.\n                    ", key_type=Tunable(description="\n                        This skill's level.\n                        \n                        This is the actual user facing skill level.\n                        ", tunable_type=int, default=0), value_type=Tunable(description='\n                        The new skill\'s value.\n                        \n                        This is the internal statistic\n                        value, not the user facing skill level."\n                        ', tunable_type=int, default=0))), tuning_group=GroupNames.SPECIAL_CASES), 'skill_unlocks_on_max': TunableList(description='\n            A list of skills that become unlocked when this skill is maxed.\n            ', tunable=TunableReference(description='\n                A skill to unlock.\n                ', manager=services.get_instance_manager(sims4.resources.Types.STATISTIC), class_restrictions=('Skill',), pack_safe=True), tuning_group=GroupNames.SPECIAL_CASES), 'trend_tag': OptionalTunable(description='\n            If enabled, we associate this skill with a particular trend via tag\n            which you can find in trend_tuning.\n            ', tunable=TunableTag(description='\n                The trend tag we associate with this skill\n                ', filter_prefixes=('func_trend',)))}
    REMOVE_INSTANCE_TUNABLES = ('min_value_tuning', 'max_value_tuning', 'decay_rate', '_default_convergence_value')

    def __init__(self, tracker):
        self._skill_level_buff = None
        super().__init__(tracker, self.initial_value)
        self._delta_enabled = True
        self._max_level_update_sent = False

    @classmethod
    def _tuning_loaded_callback(cls):
        super()._tuning_loaded_callback()
        level_list = cls.get_level_list()
        cls.max_level = len(level_list)
        cls.min_value_tuning = 0
        cls.max_value_tuning = sum(level_list)
        cls._default_convergence_value = cls.min_value_tuning
        cls._build_utility_curve_from_tuning_data(cls.ad_data)
        for stat in cls.statistic_multipliers:
            multiplier = cls.statistic_multipliers[stat]
            curve = multiplier.curve
            direction = multiplier.direction
            use_effective_skill = multiplier.use_effective_skill
            stat.add_skill_based_statistic_multiplier(cls, curve, direction, use_effective_skill)
        for multiplier in cls.success_chance_multipliers:
            curve = multiplier.curve
            use_effective_skill = multiplier.use_effective_skill
            for affordance in multiplier.affordance_list:
                affordance.add_skill_multiplier(affordance.success_chance_multipliers, cls, curve, use_effective_skill)
        for multiplier in cls.monetary_payout_multipliers:
            curve = multiplier.curve
            use_effective_skill = multiplier.use_effective_skill
            for affordance in multiplier.affordance_list:
                affordance.add_skill_multiplier(affordance.monetary_payout_multipliers, cls, curve, use_effective_skill)

    @classmethod
    def _verify_tuning_callback(cls):
        success_multiplier_affordances = []
        for multiplier in cls.success_chance_multipliers:
            success_multiplier_affordances.extend(multiplier.affordance_list)
        if len(success_multiplier_affordances) != len(set(success_multiplier_affordances)):
            logger.error("The same affordance has been tuned more than once under {}'s success multipliers, and they will overwrite each other. Please fix in tuning.", cls, owner='tastle')
        monetary_payout_multiplier_affordances = []
        for multiplier in cls.monetary_payout_multipliers:
            monetary_payout_multiplier_affordances.extend(multiplier.affordance_list)
        if len(monetary_payout_multiplier_affordances) != len(set(monetary_payout_multiplier_affordances)):
            logger.error("The same affordance has been tuned more than once under {}'s monetary payout multipliers, and they will overwrite each other. Please fix in tuning.", cls, owner='tastle')

    @classproperty
    def skill_type(cls):
        return cls

    @constproperty
    def is_skill():
        return True

    @classproperty
    def autonomy_weight(cls):
        return cls.weight

    @constproperty
    def remove_on_convergence():
        return False

    @classproperty
    def valid_for_stat_testing(cls):
        return True

    @classmethod
    def can_add(cls, owner, force_add=False, **kwargs):
        if force_add:
            return True
        if owner.age not in cls.ages:
            return False
        return super().can_add(owner, **kwargs)

    @classmethod
    def convert_to_user_value(cls, value):
        level_list = cls.get_level_list()
        if not level_list:
            return 0
        current_value = value
        for (level, level_threshold) in enumerate(level_list):
            current_value -= level_threshold
            if current_value < 0:
                return level
        return level + 1

    @classmethod
    def convert_from_user_value(cls, user_value):
        (level_min, _) = cls._get_level_bounds(user_value)
        return level_min

    @classmethod
    def create_skill_update_msg(cls, sim_id, stat_value):
        skill_msg = Commodities_pb2.Skill_Update()
        skill_msg.skill_id = cls.guid64
        skill_msg.curr_points = int(stat_value)
        skill_msg.sim_id = sim_id
        return skill_msg

    @classmethod
    def get_level_list(cls):
        return cls.SKILL_LEVEL_LIST.get(cls.skill_level_type)

    @classmethod
    def get_skill_effectiveness_points_gain(cls, effectiveness_level, level):
        skill_gain_curve = cls.SKILL_EFFECTIVENESS_GAIN.get(effectiveness_level)
        if skill_gain_curve is not None:
            return skill_gain_curve.get(level)
        logger.error('{} does not exist in SKILL_EFFECTIVENESS_GAIN mapping', effectiveness_level)
        return 0

    def _get_level_data_for_skill_level(self, skill_level):
        level_data = self.level_data.get(skill_level)
        if level_data is None:
            logger.debug('No level data found for skill [{}] at level [{}].', self, skill_level)
        return level_data

    @property
    def is_initial_value(self):
        return self.initial_value == self.get_value()

    def should_send_update(self, sim_info, stat_value):
        if sim_info.is_npc and not self.update_client_for_npcs:
            return False
        if Skill.convert_to_user_value(stat_value) == 0:
            return False
        if self.reached_max_level:
            if self._max_level_update_sent:
                return False
            self._max_level_update_sent = True
        return True

    def on_initial_startup(self):
        super().on_initial_startup()
        skill_level = self.get_user_value()
        self._update_skill_level_buff(skill_level)

    def on_add(self):
        super().on_add()
        self._tracker.owner.add_modifiers_for_skill(self)
        level_data = self._get_level_data_for_skill_level(self.get_user_value())
        if level_data is not None:
            provided_affordances = []
            for provided_affordance in level_data.target_super_affordances:
                provided_affordance_data = ProvidedAffordanceData(provided_affordance.affordance, provided_affordance.object_filter, provided_affordance.allow_self)
                provided_affordances.append(provided_affordance_data)
            self._tracker.add_to_affordance_caches(level_data.super_affordances, provided_affordances)
            self._tracker.add_to_actor_mixer_cache(level_data.actor_mixers)
            sim = self._tracker._owner.get_sim_instance()
            apply_super_affordance_commodity_flags(sim, self, level_data.super_affordances)

    def on_remove(self, on_destroy=False):
        super().on_remove(on_destroy=on_destroy)
        self._destory_callback_handle()
        if not on_destroy:
            self._send_skill_delete_message()
        if self._skill_level_buff is not None:
            self._tracker.owner.remove_buff(self._skill_level_buff)
            self._skill_level_buff = None
        if not on_destroy:
            self._tracker.update_affordance_caches()
        sim = self._tracker._owner.get_sim_instance()
        remove_super_affordance_commodity_flags(sim, self)

    def on_zone_load(self):
        self._max_level_update_sent = False

    def _apply_multipliers_to_continuous_statistics(self):
        for stat in self.statistic_multipliers:
            if stat.continuous:
                owner_stat = self.tracker.get_statistic(stat)
                if owner_stat is not None:
                    owner_stat._recalculate_modified_decay_rate()

    @classproperty
    def default_value(cls):
        return cls.initial_value

    @flexmethod
    @caches.cached
    def get_user_value(cls, inst):
        inst_or_cls = inst if inst is not None else cls
        return super(__class__, inst_or_cls).get_user_value()

    def _clear_user_value_cache(self):
        self.get_user_value.func.cache.clear()

    def set_value(self, value, *args, from_load=False, interaction=None, **kwargs):
        old_value = self.get_value()
        super().set_value(value, *args, **kwargs)
        if not caches.skip_cache:
            self._clear_user_value_cache()
        if from_load:
            return
        event_manager = services.get_event_manager()
        sim_info = self._tracker._owner
        new_value = self.get_value()
        new_level = self.convert_to_user_value(value)
        if old_value == self.initial_value or old_value != new_value:
            event_manager.process_event(test_events.TestEvent.SkillValueChange, sim_info=sim_info, skill=self, statistic=self.stat_type, custom_keys=(self.stat_type,))
        old_level = self.convert_to_user_value(old_value)
        if old_level < new_level or old_value == self.initial_value:
            self._apply_multipliers_to_continuous_statistics()
            event_manager.process_event(test_events.TestEvent.SkillLevelChange, sim_info=sim_info, skill=self, new_level=new_level, custom_keys=(self.stat_type,))

    def add_value(self, add_amount, interaction=None, **kwargs):
        old_value = self.get_value()
        if old_value == self.initial_value:
            telemhook = TELEMETRY_HOOK_SKILL_INTERACTION_FIRST_TIME
        else:
            telemhook = TELEMETRY_HOOK_SKILL_INTERACTION
        super().add_value(add_amount, interaction=interaction)
        if not caches.skip_cache:
            self._clear_user_value_cache()
        if interaction is not None:
            interaction_name = interaction.affordance.__name__
        else:
            interaction_name = TELEMETRY_INTERACTION_NOT_AVAILABLE
        self.on_skill_updated(telemhook, old_value, self.get_value(), interaction_name)

    def _update_value(self):
        old_value = self._value
        if gsi_handlers.sim_handlers_log.skill_change_archiver.enabled:
            last_update = self._last_update
        time_delta = super()._update_value()
        if not caches.skip_cache:
            self._clear_user_value_cache()
        new_value = self._value
        if old_value < new_value:
            event_manager = services.get_event_manager()
            sim_info = self._tracker._owner if self._tracker is not None else None
            if old_value == self.initial_value:
                telemhook = TELEMETRY_HOOK_SKILL_INTERACTION_FIRST_TIME
                self.on_skill_updated(telemhook, old_value, new_value, TELEMETRY_INTERACTION_NOT_AVAILABLE)
            event_manager.process_event(test_events.TestEvent.SkillValueChange, sim_info=sim_info, skill=self, statistic=self.stat_type, custom_keys=(self.stat_type,))
            old_level = self.convert_to_user_value(old_value)
            new_level = self.convert_to_user_value(new_value)
            if gsi_handlers.sim_handlers_log.skill_change_archiver.enabled and self.tracker.owner.is_sim:
                gsi_handlers.sim_handlers_log.archive_skill_change(self.tracker.owner, self, time_delta, old_value, new_value, new_level, last_update)
            if old_level < new_level or old_value == self.initial_value:
                if self._tracker is not None:
                    self._tracker.notify_watchers(self.stat_type, self._value, self._value)
                event_manager.process_event(test_events.TestEvent.SkillLevelChange, sim_info=sim_info, skill=self, new_level=new_level, custom_keys=(self.stat_type,))

    def _on_statistic_modifier_changed(self, notify_watcher=True):
        super()._on_statistic_modifier_changed(notify_watcher=notify_watcher)
        if not self.reached_max_level:
            return
        event_manager = services.get_event_manager()
        sim_info = self._tracker._owner if self._tracker is not None else None
        event_manager.process_event(test_events.TestEvent.SkillValueChange, sim_info=sim_info, skill=self, statistic=self.stat_type, custom_keys=(self.stat_type,))

    def on_skill_updated(self, telemhook, old_value, new_value, affordance_name):
        owner_sim_info = self._tracker._owner
        if owner_sim_info.is_selectable:
            with telemetry_helper.begin_hook(skill_telemetry_writer, telemhook, sim_info=owner_sim_info) as hook:
                hook.write_guid(TELEMETRY_FIELD_SKILL_ID, self.guid64)
                hook.write_string(TELEMETRY_FIELD_SKILL_AFFORDANCE, affordance_name)
                hook.write_bool(TELEMETRY_FIELD_SKILL_AFFORDANCE_SUCCESS, True)
                hook.write_int(TELEMETRY_FIELD_SKILL_AFFORDANCE_VALUE_ADD, new_value - old_value)
        if old_value == self.initial_value:
            skill_level = self.convert_to_user_value(old_value)
            self._handle_skill_up(skill_level)

    def _send_skill_delete_message(self):
        if self.tracker.owner.is_npc:
            return
        skill_msg = Commodities_pb2.SkillDelete()
        skill_msg.skill_id = self.guid64
        op = GenericProtocolBufferOp(Operation.SIM_SKILL_DELETE, skill_msg)
        Distributor.instance().add_op(self.tracker.owner, op)

    @staticmethod
    def _callback_handler(stat_inst):
        new_level = stat_inst.get_user_value()
        old_level = new_level - 1
        stat_inst.on_skill_level_up(old_level, new_level)
        stat_inst.refresh_threshold_callback()

    def _handle_skill_up(self, skill_level):
        self._show_level_notification(skill_level)
        self._update_skill_level_buff(skill_level)
        self._try_give_skill_up_payout(skill_level)
        self._tracker.update_affordance_caches()
        sim = self._tracker._owner.get_sim_instance()
        remove_super_affordance_commodity_flags(sim, self)
        super_affordances = tuple(self._tracker.get_cached_super_affordances_gen())
        apply_super_affordance_commodity_flags(sim, self, super_affordances)

    def _recalculate_modified_decay_rate(self):
        pass

    def refresh_level_up_callback(self):
        self._destory_callback_handle()

        def _on_level_up_callback(stat_inst):
            new_level = stat_inst.get_user_value()
            old_level = new_level - 1
            stat_inst.on_skill_level_up(old_level, new_level)
            stat_inst.refresh_level_up_callback()

        self._callback_handle = self.create_and_add_callback_listener(Threshold(self._get_next_level_bound(), operator.ge), _on_level_up_callback)

    def on_skill_level_up(self, old_level, new_level):
        tracker = self.tracker
        sim_info = tracker._owner
        if self.reached_max_level:
            for skill in self.skill_unlocks_on_max:
                skill_instance = tracker.add_statistic(skill, force_add=True)
                skill_instance.set_value(skill.initial_value)
        with telemetry_helper.begin_hook(skill_telemetry_writer, TELEMETRY_HOOK_SKILL_LEVEL_UP, sim_info=sim_info) as hook:
            hook.write_guid(TELEMETRY_FIELD_SKILL_ID, self.guid64)
            hook.write_int(TELEMETRY_FIELD_SKILL_LEVEL, new_level)
        self._handle_skill_up(new_level)
        services.get_event_manager().process_event(test_events.TestEvent.SkillValueChange, sim_info=sim_info, statistic=self.stat_type, custom_keys=(self.stat_type,))

    def _show_level_notification(self, skill_level, ignore_npc_check=False):
        sim_info = self._tracker._owner
        if not (ignore_npc_check or sim_info.is_npc):
            if skill_level == 1:
                tutorial_service = services.get_tutorial_service()
                if tutorial_service is not None and tutorial_service.is_tutorial_running():
                    return
            level_data = self._get_level_data_for_skill_level(skill_level)
            if level_data is not None:
                tutorial_id = None
                if skill_level == 1:
                    tutorial_id = self.tutorial.guid64
                notification = level_data.level_up_notification(sim_info, resolver=SingleSimResolver(sim_info))
                notification.show_dialog(icon_override=IconInfoData(icon_resource=self.icon), secondary_icon_override=IconInfoData(obj_instance=sim_info), additional_tokens=(skill_level,), tutorial_id=tutorial_id)
                if self.tutorial is not None and level_data.level_up_screen_slam is not None:
                    level_data.level_up_screen_slam.send_screen_slam_message(sim_info, sim_info, self.stat_name, skill_level)

    def _update_skill_level_buff(self, skill_level):
        level_data = self._get_level_data_for_skill_level(skill_level)
        new_buff = level_data.skill_level_buff if level_data is not None else None
        if self._skill_level_buff is not None:
            self._tracker.owner.remove_buff(self._skill_level_buff)
            self._skill_level_buff = None
        if new_buff is not None:
            self._skill_level_buff = self._tracker.owner.add_buff(new_buff)

    def _try_give_skill_up_payout(self, skill_level):
        level_data = self._get_level_data_for_skill_level(skill_level)
        if level_data is None:
            return
        if level_data.rewards:
            for reward in level_data.rewards:
                reward().open_reward(self._tracker.owner, reward_destination=RewardDestination.SIM)
        if level_data.loot:
            resolver = SingleSimResolver(self._tracker.owner)
            for loot in level_data.loot:
                loot.apply_to_resolver(resolver)

    def force_show_level_notification(self, skill_level):
        self._show_level_notification(skill_level, ignore_npc_check=True)

    @classmethod
    def send_commodity_update_message(cls, sim_info, old_value, new_value):
        stat_instance = sim_info.get_statistic(cls.stat_type, add=False)
        if stat_instance is None or not stat_instance.should_send_update(sim_info, new_value):
            return
        msg = cls.create_skill_update_msg(sim_info.id, new_value)
        add_object_message(sim_info, MSG_SIM_SKILL_UPDATE, msg, False)
        change_rate = stat_instance.get_change_rate()
        hide_progress_bar = False
        if sim_info.is_npc or sim_info.is_skill_bar_suppressed():
            hide_progress_bar = True
        op = distributor.ops.SkillProgressUpdate(cls.guid64, change_rate, new_value, hide_progress_bar)
        distributor.ops.record(sim_info, op)

    def save_statistic(self, commodities, skills, ranked_stats, tracker):
        current_value = self.get_saved_value()
        if current_value == self.initial_value:
            return
        message = protocols.Skill()
        message.name_hash = self.guid64
        message.value = current_value
        if self._time_of_last_value_change:
            message.time_of_last_value_change = self._time_of_last_value_change.absolute_ticks()
        skills.append(message)

    def unlocks_skills_on_max(self):
        return True

    def can_decay(self):
        return False

    def get_skill_provided_affordances(self):
        level_data = self._get_level_data_for_skill_level(self.get_user_value())
        if level_data is None:
            return ((), ())
        return (level_data.super_affordances, level_data.target_super_affordances)

    def get_skill_provided_actor_mixers(self):
        level_data = self._get_level_data_for_skill_level(self.get_user_value())
        if level_data is None:
            return
        return level_data.actor_mixers

    def get_actor_mixers(self, super_interaction):
        level_data = self._get_level_data_for_skill_level(self.get_user_value())
        if level_data is None:
            return []
        mixers = level_data.actor_mixers.get(super_interaction, tuple()) if level_data is not None else []
        return mixers
_SkillLootData = collections.namedtuple('_SkillLootData', ['level_range', 'stat', 'effectiveness'])EMPTY_SKILL_LOOT_DATA = _SkillLootData(None, None, None)
class TunableSkillLootData(TunableTuple):

    def __init__(self, **kwargs):
        super().__init__(level_range=OptionalTunable(TunableInterval(description="\n                            Interval is used to clamp the sim's user facing\n                            skill level to determine how many point to give. If\n                            disabled, level passed to the dynamic skill loot\n                            will always be the current user facing skill level\n                            of sim. \n                            Example: if sim is level 7 in fitness but\n                            interaction skill level is only for 1 to 5 give the\n                            dynamic skill amount as if sim is level 5.\n                            ", tunable_type=int, default_lower=0, default_upper=1, minimum=0)), stat=TunablePackSafeReference(description='\n                             The statistic we are operating on.\n                             ', manager=services.get_instance_manager(sims4.resources.Types.STATISTIC), allow_none=True, class_restrictions=Skill), effectiveness=TunableEnumEntry(description='\n                             Enum to determine which curve to use when giving\n                             points to sim.\n                             ', tunable_type=SkillEffectiveness, needs_tuning=True, default=None), **kwargs)
