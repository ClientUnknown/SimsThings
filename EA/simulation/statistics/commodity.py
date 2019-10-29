import contextlibimport itertoolsimport operatorimport randomimport weakreffrom protocolbuffers import Commodities_pb2, Localization_pb2, SimObjectAttributes_pb2 as protocols, UI_pb2 as ui_protosfrom alarms import cancel_alarm, add_alarmfrom buffs.tunable import BuffReference, TunableBuffReferencefrom clock import interval_in_sim_minutesfrom event_testing import test_eventsfrom interactions.context import QueueInsertStrategyfrom interactions.utils.tunable_icon import TunableIconAllPacksfrom objects import HiddenReasonFlagfrom sims4.localization import TunableLocalizedStringfrom sims4.math import Threshold, EPSILONfrom sims4.tuning.geometric import TunableVector2from sims4.tuning.instances import HashedTunedInstanceMetaclassfrom sims4.tuning.tunable import Tunable, TunableList, TunableTuple, OptionalTunable, TunableReference, TunableResourceKey, TunableThreshold, HasTunableReference, TunableSingletonFactory, TunableSet, TunableSimMinute, TunableRange, TunableEnumEntry, TunableColor, TunableInterval, TunableVariant, TunableMappingfrom sims4.tuning.tunable_base import ExportModesfrom sims4.utils import classproperty, constpropertyfrom singletons import DEFAULTfrom statistics.commodity_messages import send_sim_commodity_progress_update_message, send_sim_alert_update_messagefrom statistics.continuous_statistic_tuning import TunedContinuousStatisticfrom statistics.statistic_categories import StatisticCategoryfrom statistics.statistic_enums import CommodityTrackerSimulationLevelfrom statistics.tunable import TunableStatAsmParamimport clockimport date_and_timeimport enumimport event_testing.resolverimport interactions.contextimport interactions.priorityimport servicesimport sims4.logimport sims4.resourcesimport telemetry_helperlogger = sims4.log.Logger('Commodities')TELEMETRY_GROUP_COMMODITIES = 'COMO'TELEMETRY_HOOK_STATE_UP = 'UPPP'TELEMETRY_HOOK_STATE_DOWN = 'DOWN'writer = sims4.telemetry.TelemetryWriter(TELEMETRY_GROUP_COMMODITIES)
class CommodityTimePassageFixupType(enum.Int):
    DO_NOT_FIXUP = 0
    FIXUP_USING_AUTOSATISFY_CURVE = 1
    FIXUP_USING_TIME_ELAPSED = 2

class MotiveFillColorLevel(enum.Int):
    NO_FILL = 0
    FAILURE = 1
    DISTRESS = 2
    FINE = 3

class MotiveUIStyle(enum.Int):
    DEFAULT = 0
    LONG = 1
    ORB = 2

class SkewerAlertType(enum.Int):
    NONE = 0
    PET_DISTRESS = 1

class CommodityState:
    __slots__ = ('_value', '_buff', '_buff_overrides', '_icon', '_icon_overrides', '_fill_level', '_buff_add_threshold', '_data_description', '_data_description_overrides', '_fill_color', '_background_color', '_tooltip_icon_list', '_tooltip_icon_list_overrides', 'loot_list_on_enter', 'apply_loot_on_load', '_ui_container_animation_increasing', '_ui_container_animation_decreasing')

    def __init__(self, value=0, buff=None, buff_overrides=None, icon=None, icon_overrides=None, fill_level=None, buff_add_threshold=None, data_description=None, data_description_overrides=None, fill_color=None, background_color=None, tooltip_icon_list=None, tooltip_icon_list_overrides=None, loot_list_on_enter=None, apply_loot_on_load=False, ui_container_animation_increasing='', ui_container_animation_decreasing=''):
        self._value = value
        self._buff = buff
        self._buff_overrides = buff_overrides
        self._icon = icon
        self._icon_overrides = icon_overrides
        self._fill_level = None
        self._buff_add_threshold = buff_add_threshold
        self._data_description = data_description
        self._data_description_overrides = data_description_overrides
        self._fill_color = fill_color
        self._background_color = background_color
        self._tooltip_icon_list = tooltip_icon_list
        self._tooltip_icon_list_overrides = tooltip_icon_list_overrides
        self.loot_list_on_enter = loot_list_on_enter
        self.apply_loot_on_load = apply_loot_on_load
        self._ui_container_animation_increasing = ui_container_animation_increasing
        self._ui_container_animation_decreasing = ui_container_animation_decreasing

    @property
    def fill_level(self):
        return self._fill_level

    @property
    def value(self):
        return self._value

    @property
    def buff(self):
        return self._buff

    @property
    def buff_overrides(self):
        return self._buff_overrides

    @property
    def icon(self):
        return self._icon

    @property
    def icon_overrides(self):
        return self._icon_overrides

    @property
    def data_description(self):
        return self._data_description

    @property
    def data_description_overrides(self):
        return self._data_description_overrides

    @property
    def buff_add_threshold(self):
        return self._buff_add_threshold

    def __repr__(self):
        return 'CommodityState: lower_value:{}, buff:{}'.format(self._value, self._buff.buff_type)

class TunableCommodityState(TunableSingletonFactory):
    FACTORY_TYPE = CommodityState

    def __init__(self, **kwargs):
        super().__init__(value=Tunable(description='\n                                lower bound value of the commodity state\n                                ', tunable_type=int, default=0, export_modes=ExportModes.All), buff=TunableBuffReference(description='\n                            Buff that will get added to sim when commodity is at\n                            this current state.\n                            ', reload_dependent=True, allow_none=True), buff_overrides=TunableMapping(description='\n                            A mapping of traits to TunableBuffReferences, used to\n                            override the buff field\n                            ', key_type=TunableReference(description='\n                                The trait.\n                                ', manager=services.get_instance_manager(sims4.resources.Types.TRAIT), pack_safe=True), value_type=TunableBuffReference(description='\n                                Buff that will get added to sim when commodity is at\n                                this current state.\n                                ', reload_dependent=True, pack_safe=True)), buff_add_threshold=OptionalTunable(TunableThreshold(description='\n                            When enabled, buff will not be added unless threshold\n                            has been met. Value for threshold must be within this\n                            commodity state.\n                            ')), icon=TunableResourceKey(description='\n                            Icon that is displayed for the current state of this\n                            commodity.\n                            ', allow_none=True, resource_types=sims4.resources.CompoundTypes.IMAGE, export_modes=ExportModes.All), icon_overrides=TunableMapping(description='\n                            A mapping of traits to TunableResourceKeys, used to\n                            override the icon field\n                            ', key_type=TunableReference(description='\n                                The trait.\n                                ', manager=services.get_instance_manager(sims4.resources.Types.TRAIT), pack_safe=True), value_type=TunableIconAllPacks(description='\n                                Icon that is displayed for the current state of this\n                                commodity.\n                                '), tuple_name='IconOverrideMapping', export_modes=ExportModes.ClientBinary), fill_level=TunableEnumEntry(description='\n                            By default we use ui_visible_distress_threshold to indicate\n                            when a motive needs attention in the sim info tray. When this is tuned,\n                            a state can override that by selecting DISTRESS or worse.\n                            ', tunable_type=MotiveFillColorLevel, default=MotiveFillColorLevel.NO_FILL, export_modes=ExportModes.All), data_description=TunableLocalizedString(description='\n                            Localized description of the current commodity state.\n                            ', allow_none=True, export_modes=ExportModes.All), data_description_overrides=TunableMapping(description='\n                            A mapping of Traits to TunableLocalizedString, used to\n                            override the data_description field. If a sim has more\n                            than one of the tuned traits, the first trait found in\n                            the mapping is used.\n                            ', key_type=TunableReference(description='\n                                The trait.\n                                ', manager=services.get_instance_manager(sims4.resources.Types.TRAIT), pack_safe=True), value_type=TunableLocalizedString(description='\n                                Localized description of this commodity state.\n                                ', allow_none=True), tuple_name='DataDescriptionOverridesMappingTuple', allow_none=True, export_modes=ExportModes.ClientBinary), fill_color=TunableColor.TunableColorRGBA(description='\n                            Fill color for motive bar\n                            ', export_modes=(ExportModes.ClientBinary,)), background_color=TunableColor.TunableColorRGBA(description='\n                            Background color for motive bar\n                            ', export_modes=(ExportModes.ClientBinary,)), tooltip_icon_list=TunableList(description='\n                            A list of icons to show in the tooltip of this\n                            commodity state.\n                            ', tunable=TunableResourceKey(description='\n                                Icon that is displayed what types of objects help\n                                solve this motive.\n                                ', resource_types=sims4.resources.CompoundTypes.IMAGE), export_modes=(ExportModes.ClientBinary,)), tooltip_icon_list_overrides=TunableMapping(description='\n                            A mapping of Traits to a list of Icons, used to\n                            override the tooltip_icon_list field. If a sim has\n                            more than one of the tuned traits, the first trait\n                            found in the mapping is used.\n                            ', key_type=TunableReference(description='\n                                The trait.\n                                ', manager=services.get_instance_manager(sims4.resources.Types.TRAIT), pack_safe=True), value_type=TunableList(description='\n                                A list of icons to show in the tooltip of this\n                                commodity state.\n                                ', tunable=TunableIconAllPacks(description='\n                                    Icon that is displayed what types of objects\n                                    help solve this motive.\n                                    '), unique_entries=True), tuple_name='TooltipIconListOverridesMappingTuple', export_modes=(ExportModes.ClientBinary,)), loot_list_on_enter=TunableList(description='\n                            List of loots that will be applied when commodity\n                            value enters this state. \n                            Note: This will not work if the commodity exists on\n                            both Sims AND Objects because the participant \n                            types in the loot will not match the resolvers \n                            passed in.\n                            ', tunable=TunableReference(services.get_instance_manager(sims4.resources.Types.ACTION), pack_safe=True)), apply_loot_on_load=Tunable(description='\n                            If true and the commodity is currently in this state, \n                            loot_list_on_enter will be reapplied.\n                            ', tunable_type=bool, default=False), ui_container_animation_increasing=OptionalTunable(description='\n                            If enabled, when this commodity enters this state from a lower one,\n                            it plays the tuned animation.\n                            ', tunable=Tunable(description='\n                                When the commodity enters this state from a lower one, play the animation\n                                with this label on the commodity container.\n                                ', tunable_type=str, default=''), export_modes=(ExportModes.ClientBinary,)), ui_container_animation_decreasing=OptionalTunable(description='\n                            If enabled, when this commodity enters this state from a higher one,\n                            it plays the tuned animation.\n                            ', tunable=Tunable(description='\n                                When the commodity enters this state from a higher one, play the animation\n                                with this label on the commodity container.\n                                ', tunable_type=str, default=''), export_modes=(ExportModes.ClientBinary,)), **kwargs)

class TunableCommodityDistress(TunableTuple):

    def __init__(self, **kwargs):
        super().__init__(description='\n            The behaviors that show that the commodity is in distress.\n            ', threshold_value=Tunable(description='\n                Threshold for below which the Sim is in commodity distress.\n                ', tunable_type=int, default=-80), buff=TunableBuffReference(description='\n                Buff that gets added to the Sim when they are in the commodity\n                distress state.\n                ', allow_none=True), distress_interactions=TunableList(description='\n                A list of interactions to be pushed on the sim when the commodity\n                reaches distress.\n                ', tunable=TunableReference(description='\n                    The interaction to be pushed on the sim when the\n                    commodity reaches Distress.\n                    ', manager=services.get_instance_manager(sims4.resources.Types.INTERACTION), pack_safe=True)), priority=Tunable(description='\n                The relative priority of the override interaction being run over\n                others.\n                ', tunable_type=int, default=0), skewer_alert=OptionalTunable(description="\n                If enabled, distress will cause an alert to appear on the Sim's\n                skewer portrait.\n                ", tunable=TunableEnumEntry(description='\n                    The alert we want to show on the skewer when this Sim is in\n                    distress. When distress ends, we will revert back to\n                    AlertType of NONE.\n                    ', tunable_type=SkewerAlertType, default=SkewerAlertType.PET_DISTRESS, invalid_enums=SkewerAlertType.NONE)), **kwargs)

class TunableCommodityFailure(TunableTuple):

    def __init__(self, **kwargs):
        super().__init__(description='\n            The behaviors for the commodity failing.\n            ', threshold=TunableThreshold(description='\n                Threshold for which the sim experiences motive failure.\n                ', value=Tunable(description='\n                    The value of the threshold that the commodity is compared\n                    against.\n                    ', tunable_type=int, default=-100)), failure_interactions=TunableList(description="\n                 A list of interactions to be pushed when the Sim's\n                 commodity fails. Only the first one whose test passes will\n                 run.\n                 ", tunable=TunableReference(description='\n                     The interaction to be pushed on the sim when the\n                     commodity fails.\n                     ', manager=services.get_instance_manager(sims4.resources.Types.INTERACTION), pack_safe=True)), repeat_interval=OptionalTunable(description='\n                If enabled, then the commodity failure interactions are executed\n                at this interval, even if they have failed before.\n                ', tunable=TunableSimMinute(description='\n                    The interval at which the commodity failure interactions are\n                    executed.\n                    ', default=12)), skewer_alert=OptionalTunable(description="\n                If enabled, distress will cause an alert to appear on the Sim's\n                skewer portrait.\n                ", tunable=TunableEnumEntry(description='\n                    The alert we want to show on the skewer when this Sim is in\n                    distress. When distress ends, we will revert back to\n                    AlertType of NONE.\n                    ', tunable_type=SkewerAlertType, default=SkewerAlertType.PET_DISTRESS, invalid_enums=SkewerAlertType.NONE)), **kwargs)

class TunableArrowData(TunableTuple):

    def __init__(self, **kwargs):
        super().__init__(positive_single_arrow=Tunable(float, 1, description='If the change rate for commodity is between this value and less than second arrow value, a single arrow will show up during commodity change.'), positive_double_arrow=Tunable(float, 20, description='If the change rate for commodity is between this value and less than triple arrow value, a double arrow will show up during commodity change.'), positive_triple_arrow=Tunable(float, 30, description='If the change rate for commodity is above this value then triple arrows will show up during commodity change.'), negative_single_arrow=Tunable(float, -1, description='If the change rate for commodity is between this value and less than second arrow value, a single arrow will show up during commodity change.'), negative_double_arrow=Tunable(float, -20, description='If the change rate for commodity is between this value and less than triple arrow value, a double arrow will show up during commodity change.'), negative_triple_arrow=Tunable(float, -30, description='If the change rate for commodity is above this value then triple arrows will show up during commodity change.'), **kwargs)

class CommodityBestValueTuningMethod(enum.Int):
    USE_MAX_VALUE_TUNING = 0
    USE_MIN_VALUE_TUNING = 1

class Commodity(HasTunableReference, TunedContinuousStatistic, metaclass=HashedTunedInstanceMetaclass, manager=services.get_instance_manager(sims4.resources.Types.STATISTIC)):
    OFF_LOT_SIM_DISABLED = 0
    OFF_LOT_SIM_SELECTABLE = 1
    OFF_LOT_SIM_ALL = 2
    REMOVE_INSTANCE_TUNABLES = ('initial_value',)
    INSTANCE_TUNABLES = {'stat_name': TunableLocalizedString(description='\n                Localized name of this commodity.\n                ', allow_none=True, export_modes=ExportModes.All), 'stat_name_overrides': TunableMapping(description='\n                A mapping of Traits to TunableLocalizedString, used to\n                override the stat name field.\n                ', key_type=TunableReference(description='\n                    The trait.\n                    ', manager=services.get_instance_manager(sims4.resources.Types.TRAIT), pack_safe=True), value_type=TunableLocalizedString(description='\n                    Localized name of this commodity.\n                    ', allow_none=True), tuple_name='StatNameOverrideMapping', export_modes=ExportModes.ClientBinary), 'min_value_tuning': Tunable(description='\n                The minimum value for this stat.\n                ', tunable_type=float, default=-100, export_modes=ExportModes.All), 'max_value_tuning': Tunable(description='\n                The maximum value for this stat.', tunable_type=float, default=100, export_modes=ExportModes.All), 'best_value_tuning': TunableVariant(description='\n            When creating clones or using the cheat to set all motives to\n            their best value, the max_value_tuning may not be the BEST\n            value, so this is a place to specify what the BEST value is\n            for this commodity.', same_as_max_value_tuning=TunableTuple(locked_args={'best_value_tuning_method': CommodityBestValueTuningMethod.USE_MAX_VALUE_TUNING}), same_as_min_value_tuning=TunableTuple(locked_args={'best_value_tuning_method': CommodityBestValueTuningMethod.USE_MIN_VALUE_TUNING}), default='same_as_max_value_tuning'), 'ui_render_style': TunableEnumEntry(description='\n                The render style for this commodity. For example, the powers\n                bar for Vampires have a different render style.\n                ', tunable_type=MotiveUIStyle, default=MotiveUIStyle.DEFAULT, export_modes=ExportModes.All), 'ui_sort_order': TunableRange(description='\n                Order in which the commodity will appear in the motive panel.\n                Commodities sort from lowest to highest.\n                ', tunable_type=int, default=0, minimum=0, export_modes=ExportModes.All), 'ui_visible_distress_threshold': Tunable(description='\n                When current value of commodity goes below this value, commodity\n                will appear in the motive panel tab.\n                ', tunable_type=float, default=0, export_modes=ExportModes.All), 'ad_data': TunableList(description='\n                A list of Vector2 points that define the desire curve for this\n                commodity.\n                ', tunable=TunableVector2(description='\n                    Point on a Curve\n                    ', default=sims4.math.Vector2(0, 0), export_modes=ExportModes.All)), 'auto_satisfy_curve_tuning': TunableList(description='\n                A list of Vector2 points that define the auto-satisfy curve for\n                this commodity.\n                ', tunable=TunableVector2(description='\n                    Point on a Curve\n                    ', default=sims4.math.Vector2(0, 0))), 'auto_satisfy_curve_random_time_offset': TunableSimMinute(description='\n                An amount of time that when auto satisfy curves are being used\n                will modify the time current time being used to plus or minus\n                a random number between this value.\n                ', default=120), 'maximum_auto_satisfy_time': TunableSimMinute(description='\n                The maximum amount of time that the auto satisfy curves will\n                interpolate the values based on the current one before just\n                setting to the maximum value.\n                ', default=1440), 'initial_tuning': TunableTuple(description=' \n                The Initial value for this commodity. Can either be a single\n                value, range, or use auto satisfy curve to determine initial\n                value.  Use auto satisfy curve will take precedence over range\n                value and range value will take precedence over single value\n                range.\n                ', _use_auto_satisfy_curve_as_initial_value=Tunable(description="\n                    If checked, when we first add this commodity to a sim (sims only),\n                    the initial value of the commodity will be set according to\n                    the auto-satisfy curves defined by this commodity's tuning as\n                    opposed to the tuned initial value.    \n                    ", tunable_type=bool, needs_tuning=True, default=False), _use_stat_value_on_init=Tunable(description='\n                    If enabled, we will use the initial tuning to set the\n                    commodity in the place of other systems (like states).\n                    Otherwise, those states or systems will set the initial\n                    value of the statistic (a state linked to this stat for\n                    example, will set the statistic to whatever default tuning\n                    is on the state). \n                    TLDR: If checked, the commodity sets the\n                    state. Otherwise, the state sets up this commodity. \n                    Note:\n                    If unchecked, we error if any initial values are tuned as\n                    they imply that we want to use them.\n                    ', tunable_type=bool, default=False), _value_range=OptionalTunable(description='\n                    If enabled then when we first add this commodity to a Sim the\n                    initial value of the commodity will be set to a random value\n                    within this interval.\n                    ', tunable=TunableInterval(description='\n                        An interval that will be used for the initial value of this\n                        commodity.\n                        ', tunable_type=int, default_lower=0, default_upper=100)), _value=Tunable(description='\n                    The initial value for this stat.', tunable_type=float, default=0.0)), 'weight': Tunable(description="\n                The weight of the Skill with regards to autonomy.  It's ignored \n                for the purposes of sorting stats, but it's applied when scoring \n                the actual statistic operation for the SI.\n                ", tunable_type=float, default=0.5), 'states': TunableList(description="\n                Commodity states based on thresholds.  This should be ordered\n                from lowest to highest value. If the higher the value the worse the\n                commodity gets, check the field 'States Ordered Best To Worst'.\n                ", tunable=TunableCommodityState()), 'commodity_distress': OptionalTunable(TunableCommodityDistress()), 'commodity_failure': OptionalTunable(TunableCommodityFailure()), 'commodity_autosolve_failure_interaction': OptionalTunable(description='\n                If enabled, tune an interaction to be pushed on the Sim when\n                they fail to autosolve a commodity.  This should only be\n                enabled on visible commodites. \n                ', tunable=TunableReference(description='\n                     The interaction to be pushed on the Sim when failing to\n                     autosolve a commodity.\n                     ', manager=services.get_instance_manager(sims4.resources.Types.INTERACTION), class_restrictions='SuperInteraction')), 'remove_on_convergence': Tunable(description='\n                Commodity will be removed when convergence is met only if not\n                a core commodity.\n                ', tunable_type=bool, default=True), 'visible': Tunable(description='\n                Whether or not commodity should be sent to client.\n                ', tunable_type=bool, default=False, export_modes=ExportModes.All), '_add_if_not_in_tracker': Tunable(description="\n                If True, when we try to add or set the commodity, we will add\n                the commodity to the tracker if the tracker doesn't already have\n                it.\n                \n                e.g If a sim uses the toilet and we update bladder when that sim\n                doesn't have the bladder commodity in his/her tracker, we will\n                add the bladder commodity to that sim. \n                \n                Set this to false for the case of NPC behavior commodities like\n                Being a Maid or Being a Burglar.\n                ", tunable_type=bool, default=True), 'initial_as_default': Tunable(description='\n                Setting this to true will cause the default value returned during testing to be the \n                initial value tuned. This happens when a test is run on this commodity on a Sim that\n                does not have the commodity. Leaving this as false will instead return the convergence\n                value.\n                ', tunable_type=bool, default=False), 'instance_if_not_default': Tunable(description="\n                If set, this commodity can be ignored when instantiating if\n                its being initialized to its default value and doesn't decay.\n                The purpose of this is not have some commodities instanced\n                until we actually need to have them decay or modified.\n                i.e. Sim Frozen commodity doens't need to be instantiated on \n                every Sim until the Sim is actually frozen for the first time.\n                ", tunable_type=bool, default=False), 'arrow_data': TunableArrowData(description='\n                Used to determine when positive or negative arrows should show\n                up depending on the delta rate of the commodity.\n                ', export_modes=(ExportModes.ClientBinary,)), '_categories': TunableSet(description='\n                List of categories that this statistic is part of.\n                ', tunable=StatisticCategory), '_off_lot_simulation': TunableVariant(description='\n                If enabled, this commodity will decay off-lot for the chosen\n                Sim type(s).  This does not apply to babies as their\n                commodities are always auto-satisfied.\n                ', locked_args={'selectable_sims': OFF_LOT_SIM_SELECTABLE, 'selectable_sims_and_npcs': OFF_LOT_SIM_ALL, 'disabled': OFF_LOT_SIM_DISABLED}, default='disabled'), '_time_passage_fixup_type': TunableEnumEntry(description="\n            This is for commodities on SIMS only.\n            This option what we do with the commodity when the sim\n            gets instanced after time has elapsed since the last time the sim\n            was spawned.\n            \n            do not fixup: Means the commodity will stay the same value as it was\n                when the sim was last instantiated\n                \n            fixup using autosatisfy curve: The commodity's value will be set\n                based on its autosatisfy curve and the time between when the sim was\n                last saved. Note, this fixup will not occur for active household sims\n                if offlot simulation is enabled for this commodity.\n                \n            fixup using time elapsed: The commodity will decay linearly based on\n                when the sim was last saved. Use this for things like commodities\n                that control buff timers to make sure that the time remaining on\n                a buff remains consistent.\n            ", tunable_type=CommodityTimePassageFixupType, default=CommodityTimePassageFixupType.DO_NOT_FIXUP), 'time_passage_fixup_for_objects': Tunable(description='\n            As a rule, object commodities do not advance while the object is not\n            loaded.  In rare cases, a commodity should be fixed up on a loaded object\n            to reflect the passage of time.  Set this flag in those cases.  May\n            your deity of choice have mercy on your manifestation of being.\n            ', tunable_type=bool, default=False), 'stat_asm_param': TunableStatAsmParam.TunableFactory(locked_args={'use_effective_skill_level': True}), '_states_ordered_best_to_worst': Tunable(description='\n            Check this if you are ordering the states for this commodity from best to worst.\n            ', tunable_type=bool, default=False), '_affects_plumbob_color': Tunable(description="\n            Uncheck this if the state of this commodity should not affect the plumbob color.\n            This is useful if you want a sim's plumbob to stay green even if this commodity\n            state is low.\n            \n            This tuning is only relevant if this commodity is visible, as non-visible\n            commodities don't affect the plumbob anyway.\n            ", tunable_type=bool, default=True)}
    initial_value = 0
    _auto_satisfy_curve = None
    use_autosatisfy_curve = True
    commodity_states = None

    @classmethod
    def _tuning_loaded_callback(cls):
        super()._tuning_loaded_callback()
        cls.initial_value = cls.initial_tuning._value
        cls._build_utility_curve_from_tuning_data(cls.ad_data)
        if cls.auto_satisfy_curve_tuning:
            point_list = [(point.x, point.y) for point in cls.auto_satisfy_curve_tuning]
            cls._auto_satisfy_curve = sims4.math.CircularUtilityCurve(point_list, 0, date_and_time.HOURS_PER_DAY)
        if cls.states:
            state_zero = cls.states[0]
            if state_zero.value < cls.min_value:
                logger.error('Worst state should not be lower than min value of commodity.  Please update tuning')
                cls.commodity_states = cls.states
            elif state_zero.value > cls.min_value:
                state = CommodityState(value=cls.min_value, buff=BuffReference())
                cls.commodity_states = (state,) + cls.states
            else:
                cls.commodity_states = cls.states
            previous_value = cls.max_value
            index = len(cls.commodity_states)
            for state in reversed(cls.commodity_states):
                index -= 1
                if state.value >= previous_value:
                    logger.error('{0} has a lower bound value of state at index:{1} that is higher than the previous state.  Please update tuning', cls, index)
                if state.buff_add_threshold is not None:
                    threshold_value = state.buff_add_threshold.value
                    if threshold_value < state.value or threshold_value > previous_value:
                        logger.error('{0} add buff threshold is out of range for state at index:{1}.  Please update tuning', cls, index)
                previous_value = state.value
                if state.buff is not None and state.buff.buff_type is not None:
                    state.buff.buff_type.add_owning_commodity(cls)

    @classmethod
    def _verify_tuning_callback(cls):
        min_value = cls.min_value
        max_value = cls.max_value
        if cls.initial_tuning._value_range is None:
            initial_value = cls.initial_tuning._value
            if initial_value < min_value:
                logger.error('{} has an initial value of {} which is below the minimum value of {}', cls, initial_value, min_value)
            if initial_value > max_value:
                logger.error('{} has an initial value of {} which is above the maximum value of {}', cls, initial_value, max_value)
        else:
            range_lower = cls.initial_tuning._value_range.lower_bound
            range_upper = cls.initial_tuning._value_range.upper_bound
            if range_lower < min_value:
                logger.error('{} has a value range lower bound of {} which is below the minimum value of {}', cls, range_lower, min_value)
            if range_upper > max_value:
                logger.error('{} has a value range upper bound of {} which is above the maximum value of {}', cls, range_upper, max_value)
        if cls.visible and (cls.ui_visible_distress_threshold < min_value or cls.ui_visible_distress_threshold > max_value):
            logger.error('{} visible distress value {} is outside the min{} / max {} range.  Please update tuning', cls, cls.ui_visible_distress_threshold, cls.min_value, cls.max_value)

    def __init__(self, tracker, core=False):
        self._allow_convergence_callback_to_activate = False
        self._buff_handle = None
        super().__init__(tracker, self.get_initial_value())
        self._core = core
        self._buff_handle = None
        self._buff_threshold_callback = None
        self._current_state_index = None
        self._current_state_ge_callback_data = None
        self._current_state_lt_callback_data = None
        self._distress_buff_handle = None
        self._exit_distress_callback_data = None
        self._distress_callback_data = None
        self._failure_callback_data = None
        self._failure_alarm_handle = None
        self._failure_interaction = None
        self._convergence_callback_data = None
        self._suppress_client_updates = False
        self.force_apply_buff_on_start_up = False
        self.force_buff_reason = None
        if tracker is not None and not tracker.load_in_progress:
            if self.tracker.simulation_level == CommodityTrackerSimulationLevel.REGULAR_SIMULATION:
                activate_convergence_callback = self.default_value != self.get_value()
                self.on_initial_startup(apply_state_enter_loot=True, activate_convergence_callback=activate_convergence_callback)
            else:
                self.start_low_level_simulation()

    @classproperty
    def initial_value_range(cls):
        return cls.initial_tuning._value_range

    @classproperty
    def use_auto_satisfy_curve_as_initial_value(cls):
        return cls.initial_tuning._use_auto_satisfy_curve_as_initial_value

    @classmethod
    def get_initial_value(cls):
        if cls.initial_value_range is None:
            return cls.initial_value
        return random.uniform(cls.initial_value_range.lower_bound, cls.initial_value_range.upper_bound)

    @classproperty
    def use_stat_value_on_initialization(cls):
        return cls.initial_tuning._use_stat_value_on_init

    @property
    def core(self):
        return self._core

    @core.setter
    def core(self, value):
        self._core = value

    @property
    def is_visible(self):
        return self.visible

    def on_add(self):
        if self._buff_handle is None:
            return
        tracker = self.tracker
        if tracker is None or tracker.load_in_progress:
            return
        if tracker.simulation_level == CommodityTrackerSimulationLevel.REGULAR_SIMULATION:
            self._update_buff(self._get_change_rate_without_decay())

    @classmethod
    def added_by_default(cls, min_range=None, max_range=None):
        if not cls.instance_if_not_default:
            return True
        if cls.decay_rate != 0:
            return True
        elif min_range is not None:
            if min_range <= cls.default_value and cls.default_value <= max_range:
                return False
            else:
                return True
        return True
        return False

    @staticmethod
    def create_and_send_sim_alert_update_msg(sim, alert_type):
        alert_msg = ui_protos.SimAlertUpdate()
        alert_msg.sim_id = sim.id
        alert_msg.alert_type = alert_type
        send_sim_alert_update_message(sim, alert_msg)

    def _setup_commodity_states(self, apply_state_enter_loot=False):
        if self.commodity_states:
            self._remove_state_callback()
            current_value = self.get_value()
            new_state_index = self._find_state_index(current_value)
            if self._current_state_index != new_state_index:
                self._set_state(new_state_index, current_value, apply_state_enter_loot=apply_state_enter_loot, send_client_update=False)
            self._add_state_callback()

    def _setup_commodity_distress(self):
        if self.commodity_distress is not None:
            self._distress_callback_data = self.create_callback_listener(Threshold(self.commodity_distress.threshold_value, operator.le), self._enter_distress)
            if self._is_at_commodity_distress():
                sim = self.tracker.owner.get_sim_instance()
                if sim is not None:
                    self._setup_distress_essentials(sim)

    def _setup_commodity_failure(self):
        if self.commodity_failure is not None:
            self._failure_callback_data = self.create_callback_listener(self.commodity_failure.threshold, self._commodity_fail)
            if self._is_at_commodity_failure():
                self._setup_commodity_failure_alarm()

    def _setup_commodity_failure_alarm(self):
        if self.commodity_failure.repeat_interval is None:
            return
        if self._failure_alarm_handle is not None:
            return
        time_span = clock.interval_in_sim_minutes(self.commodity_failure.repeat_interval)
        self._failure_alarm_handle = add_alarm(self, time_span, self._on_commodity_failure_interval, repeating=True)

    def _stop_commodity_failure_alarm(self):
        if self._failure_alarm_handle is not None:
            cancel_alarm(self._failure_alarm_handle)
            self._failure_alarm_handle = None

    def _on_commodity_failure_interval(self, _):
        if not self._is_at_commodity_failure():
            self._stop_commodity_failure_alarm()
            return
        failure_interaction = self._failure_interaction() if self._failure_interaction is not None else None
        if failure_interaction is None:
            self._commodity_fail(self)

    def on_initial_startup(self, apply_state_enter_loot=False, activate_convergence_callback=True):
        self._setup_commodity_distress()
        if self._distress_callback_data is not None:
            self.add_callback_listener(self._distress_callback_data)
        self._setup_commodity_failure()
        if self._failure_callback_data is not None:
            self.add_callback_listener(self._failure_callback_data)
        self._setup_commodity_states(apply_state_enter_loot=apply_state_enter_loot)
        self.decay_enabled = not self.tracker.owner.is_locked(self)
        self._apply_buff_load_reason()
        if self._convergence_callback_data is None:
            self._convergence_callback_data = self.create_callback_listener(Threshold(self.convergence_value, operator.eq), self._remove_self_from_tracker)
            if activate_convergence_callback:
                self.add_callback_listener(self._convergence_callback_data)
                self._allow_convergence_callback_to_activate = False
            else:
                self._allow_convergence_callback_to_activate = True

    @contextlib.contextmanager
    def _suppress_client_updates_context_manager(self, is_rate_change=True):
        if self._suppress_client_updates:
            yield None
        else:
            self._suppress_client_updates = True
            try:
                yield None
            finally:
                self._suppress_client_updates = False
                self.send_commodity_progress_msg(is_rate_change=is_rate_change)

    def _commodity_telemetry(self, hook, desired_state_index):
        if not self.tracker.owner.is_sim:
            return
        with telemetry_helper.begin_hook(writer, hook, sim=self.tracker.get_sim()) as hook:
            guid = getattr(self, 'guid64', None)
            if guid is not None:
                hook.write_guid('stat', self.guid64)
            else:
                logger.info('{} does not have a guid64', self)
            hook.write_int('oldd', self._current_state_index)
            hook.write_int('news', desired_state_index)

    def _update_state_up(self, stat_instance):
        with self._suppress_client_updates_context_manager():
            current_value = self.get_value()
            desired_state_index = self._find_state_index(current_value)
            if desired_state_index == self._current_state_index:
                desired_state_index = self._find_state_index(current_value + EPSILON)
            if desired_state_index != self._current_state_index:
                self._remove_state_callback()
                self._commodity_telemetry(TELEMETRY_HOOK_STATE_UP, desired_state_index)
                while self._current_state_index < desired_state_index:
                    next_index = self._current_state_index + 1
                    self._set_state(next_index, current_value, send_client_update=next_index == desired_state_index)
                self._update_state_callback(desired_state_index)
            else:
                logger.warn('{} update state up was called, but state did not change. current state_index:{}', self, self._current_state_index, owner='msantander')

    def _update_state_down(self, stat_instance):
        with self._suppress_client_updates_context_manager():
            current_value = self.get_value()
            desired_state_index = self._find_state_index(self.get_value())
            if desired_state_index == self._current_state_index:
                desired_state_index = self._find_state_index(current_value - EPSILON)
            if desired_state_index != self._current_state_index:
                self._remove_state_callback()
                self._commodity_telemetry(TELEMETRY_HOOK_STATE_DOWN, desired_state_index)
                while self._current_state_index > desired_state_index:
                    prev_index = self._current_state_index - 1
                    self._set_state(prev_index, current_value, send_client_update=prev_index == desired_state_index)
                self._update_state_callback(desired_state_index)
            else:
                logger.warn('{} update state down was called, but state did not change. current state_index:{}', self, self._current_state_index, owner='msantander')

    def _update_state_callback(self, desired_state_index):
        new_state_index = self._find_state_index(self.get_value())
        if new_state_index > desired_state_index:
            self._update_state_up(self)
        elif new_state_index < desired_state_index:
            self._update_state_down(self)
        else:
            self._add_state_callback()

    def _state_reset_callback(self, stat_instance, time):
        self._update_buff(self._get_change_rate_without_decay())

    def _remove_self_from_tracker(self, _):
        tracker = self._tracker
        if tracker is not None:
            tracker.remove_statistic(self.stat_type)

    def _can_low_level_simulate(self):
        sim = self.tracker.owner
        if sim.is_baby:
            return False
        if self._off_lot_simulation == self.OFF_LOT_SIM_DISABLED:
            return False
        elif self._off_lot_simulation == self.OFF_LOT_SIM_SELECTABLE:
            return sim.is_selectable
        return True

    def start_low_level_simulation(self):
        if self._can_low_level_simulate():
            self.decay_enabled = True
            self._setup_commodity_states()
            self._apply_buff_load_reason()
        else:
            self.decay_enabled = False

    def stop_low_level_simulation(self, on_destroy=False):
        if not on_destroy:
            self.decay_enabled = False
        self._remove_state_callback()

    def stop_regular_simulation(self, on_destroy=False):
        self._remove_state_callback()
        if not on_destroy:
            self.decay_enabled = False
        if self._convergence_callback_data is not None:
            self.remove_callback_listener(self._convergence_callback_data)
            self._convergence_callback_data = None
        if self._distress_callback_data is not None:
            self.remove_callback_listener(self._distress_callback_data)
            self._distress_callback_data = None
        if self.commodity_distress is not None and not on_destroy:
            self._exit_distress(self, True)
        if self._failure_callback_data is not None:
            self.remove_callback_listener(self._failure_callback_data)
            self._failure_callback_data = None
        self._stop_commodity_failure_alarm()

    def _find_state_index(self, current_value):
        index = len(self.commodity_states) - 1
        while index >= 0:
            state = self.commodity_states[index]
            if current_value >= state.value:
                return index
            index -= 1
        return 0

    def _add_state_callback(self):
        next_state_index = self._current_state_index + 1
        if next_state_index < len(self.commodity_states):
            self._current_state_ge_callback_data = self.create_and_add_callback_listener(Threshold(self.commodity_states[next_state_index].value, operator.ge), self._update_state_up, on_callback_alarm_reset=self._state_reset_callback)
        if self.commodity_states[self._current_state_index].value > self.min_value:
            self._current_state_lt_callback_data = self.create_and_add_callback_listener(Threshold(self.commodity_states[self._current_state_index].value, operator.lt), self._update_state_down, on_callback_alarm_reset=self._state_reset_callback)

    def _remove_state_callback(self):
        if self._current_state_ge_callback_data is not None:
            self.remove_callback_listener(self._current_state_ge_callback_data)
            self._current_state_ge_callback_data = None
        if self._current_state_lt_callback_data is not None:
            self.remove_callback_listener(self._current_state_lt_callback_data)
            self._current_state_lt_callback_data = None
        if self._buff_threshold_callback is not None:
            self.remove_callback_listener(self._buff_threshold_callback)
            self._buff_threshold_callback = None

    def _get_next_buff_commodity_decaying_to(self):
        transition_into_buff_id = 0
        if self._current_state_index > 0:
            current_value = self.get_value()
            buff_tunable_ref = None
            if self.convergence_value <= current_value:
                buff_tunable_ref = self.commodity_states[self._current_state_index - 1].buff
            else:
                next_state_index = self._current_state_index + 1
                if next_state_index < len(self.commodity_states):
                    buff_tunable_ref = self.commodity_states[next_state_index].buff
            if buff_tunable_ref is not None:
                buff_type = buff_tunable_ref.buff_type
                if buff_type.visible:
                    transition_into_buff_id = buff_type.guid64
        return transition_into_buff_id

    def _add_buff_from_state(self, commodity_state, apply_buff_loot=True):
        owner = self.tracker.owner
        if owner.is_sim:
            buff_tuning = commodity_state.buff
            if commodity_state.buff_overrides is not None:
                for (trait, buff) in commodity_state.buff_overrides.items():
                    if owner.sim_info.trait_tracker.has_trait(trait):
                        buff_tuning = buff
                        break
            transition_into_buff_id = self._get_next_buff_commodity_decaying_to() if buff_tuning.buff_type.visible else 0
            try:
                self._buff_handle = owner.add_buff(buff_tuning.buff_type, buff_reason=buff_tuning.buff_reason, commodity_guid=self.guid64, change_rate=self._get_change_rate_without_decay(), transition_into_buff_id=transition_into_buff_id, apply_buff_loot=apply_buff_loot)
            except:
                logger.exception('Sim {} failed to add buff {} from state. Commodity:{}, Sim LOD:{}', owner, buff_tuning.buff_type, self, owner.lod)

    def _apply_buff_load_reason(self):
        self.force_apply_buff_on_start_up = False
        if self._buff_handle is not None:
            current_state = self.commodity_states[self._current_state_index]
            self.tracker.owner.set_buff_reason(current_state.buff.buff_type, self.force_buff_reason, use_replacement=True)
            self.force_buff_reason = None

    def _add_buff_callback(self, _):
        current_state = self.commodity_states[self._current_state_index]
        self.remove_callback_listener(self._buff_threshold_callback)
        self._buff_threshold_callback = None
        self._add_buff_from_state(current_state)

    def _set_state(self, new_state_index, current_value, apply_state_enter_loot=False, send_client_update=True):
        new_state = self.commodity_states[new_state_index]
        old_state_index = self._current_state_index
        self._current_state_index = new_state_index
        if self._buff_threshold_callback is not None:
            self.remove_callback_listener(self._buff_threshold_callback)
            self._buff_threshold_callback = None
        if self._buff_handle is not None:
            self.tracker.owner.remove_buff(self._buff_handle)
            self._buff_handle = None
        if new_state.buff.buff_type:
            if new_state.buff_add_threshold is not None and not (self.force_apply_buff_on_start_up or new_state.buff_add_threshold.compare(current_value)):
                self._buff_threshold_callback = self.create_and_add_callback_listener(new_state.buff_add_threshold, self._add_buff_callback)
            else:
                apply_buff_loot = apply_state_enter_loot or old_state_index is not None
                self._add_buff_from_state(new_state, apply_buff_loot=apply_buff_loot)
        if new_state.loot_list_on_enter is not None:
            if self.tracker.owner.is_sim:
                resolver = event_testing.resolver.SingleSimResolver(self.tracker.owner)
            else:
                resolver = event_testing.resolver.SingleObjectResolver(self.tracker.owner)
            for loot_action in new_state.loot_list_on_enter:
                loot_action.apply_to_resolver(resolver)
        if (old_state_index is not None or apply_state_enter_loot or new_state.apply_loot_on_load) and send_client_update:
            self.send_commodity_progress_msg()

    def _enter_distress(self, stat_instance):
        if not self.tracker.owner.is_sim:
            logger.error('Distress for commodity {} is trying to be called on object {}, which is not a sim.  This is not valid.', self, self.tracker.owner, owner='jjacobson')
            return
        sim = self.tracker.owner.get_sim_instance()
        if sim is None:
            return
        self._setup_distress_essentials(sim)
        for si in itertools.chain(sim.si_state, sim.queue):
            if si.prevents_distress(self.stat_type):
                return
        context = interactions.context.InteractionContext(self.tracker.owner.get_sim_instance(), interactions.context.InteractionContext.SOURCE_AUTONOMY, interactions.priority.Priority.High, insert_strategy=QueueInsertStrategy.NEXT, bucket=interactions.context.InteractionBucketType.DEFAULT)
        for distress_affordance in self.commodity_distress.distress_interactions:
            result = sim.push_super_affordance(distress_affordance, None, context)
            if result:
                break

    def _setup_distress_essentials(self, sim):
        if self.commodity_distress.buff.buff_type is not None:
            if self._distress_buff_handle is None:
                self._distress_buff_handle = self.tracker.owner.add_buff(self.commodity_distress.buff.buff_type, self.commodity_distress.buff.buff_reason, commodity_guid=self.guid64)
            else:
                logger.error('Distress Buff Handle is not none when entering Commodity Distress for {}.', self, owner='jjacobson')
        if self._exit_distress_callback_data is None:
            self._exit_distress_callback_data = self.create_and_add_callback_listener(Threshold(self.commodity_distress.threshold_value, operator.gt), self._exit_distress)
        self.tracker.owner.enter_distress(self)
        if self.commodity_distress.skewer_alert is not None:
            self.create_and_send_sim_alert_update_msg(sim, self.commodity_distress.skewer_alert)

    def _is_at_commodity_distress(self):
        return Threshold(self.commodity_distress.threshold_value, operator.le).compare(self.get_value())

    def _exit_distress(self, stat_instance, on_removal=False):
        if self._distress_buff_handle is not None:
            self.tracker.owner.remove_buff(self._distress_buff_handle)
            self._distress_buff_handle = None
        elif self.commodity_distress.buff.buff_type is not None and not on_removal:
            logger.error('Distress Buff Handle is none when exiting Commodity Distress for {}.', self, owner='jjacobson')
        if self._exit_distress_callback_data is not None:
            self.remove_callback_listener(self._exit_distress_callback_data)
            self._exit_distress_callback_data = None
        elif not on_removal:
            logger.error('Exit distress called before exit distress callback has been setup for {}.', self, owner='jjacobson')
        self.tracker.owner.exit_distress(self)

    def _commodity_fail_object(self, stat_instance):
        context = interactions.context.InteractionContext(None, interactions.context.InteractionContext.SOURCE_SCRIPT, interactions.priority.Priority.Critical, bucket=interactions.context.InteractionBucketType.DEFAULT)
        owner = self.tracker.owner
        for failure_interaction in self.commodity_failure.failure_interactions:
            if not (failure_interaction.immediate and failure_interaction.simless):
                logger.error('Trying to use a non-immediate and/or non-simless\n                interaction as a commodity failure on an object. Object\n                commodity failures can only push immediate, simless\n                interactions. - trevor')
                break
            aop = interactions.aop.AffordanceObjectPair(failure_interaction, owner, failure_interaction, None)
            if aop.test_and_execute(context):
                break

    def _is_at_commodity_failure(self):
        if self.commodity_failure is not None:
            return self.commodity_failure.threshold.compare(self.get_value())
        return False

    def _commodity_fail(self, stat_instance):
        owner = self.tracker.owner
        if not owner.is_sim:
            return self._commodity_fail_object(stat_instance)
        sim = owner.get_sim_instance(allow_hidden_flags=HiddenReasonFlag.RABBIT_HOLE)
        in_rabbit_hole = sim is not None and sim.is_hidden()
        if sim is None or in_rabbit_hole:
            if in_rabbit_hole:
                if self.remove_on_convergence:
                    logger.error("The commodity [{}] on Sim [{}] has reached its failure threshold while the Sim is in a Rabbit Hole\n                    interaction. Since the commodity is tuned to be removed on convergence, the failure behavior will not run. If it's\n                    critical that this behavior run, ensure 'Remove On Convergence' is unchecked in the tuning for this commodity\n                    and ensure it gets removed elsewhere.", self, sim, owner='trevor')
                elif self.commodity_failure.repeat_interval is None:
                    logger.debug('The commodity [{}] on Sim [{}] has reached its failure threshold while the Sim is in a Rabbit Hole\n                    interaction. Since this commodity has no Repeat Interval tuned, this failure will not process until the next zone\n                    spin up or save/load. If you need this failure to run more immediately ensure a Repeat Interval is tuned in the\n                    Commodity Failure section of this commodities tuning or find another way to tune around this (i.e. motive_Bladder).', self, sim, owner='trevor')
                self._setup_commodity_failure_alarm()
            return
        context = interactions.context.InteractionContext(sim, interactions.context.InteractionContext.SOURCE_SCRIPT, interactions.priority.Priority.Critical, bucket=interactions.context.InteractionBucketType.DEFAULT)
        for failure_affordance in self.commodity_failure.failure_interactions:
            result = sim.push_super_affordance(failure_affordance, None, context)
            if result:
                self._failure_interaction = weakref.ref(result.interaction)
                break
        self._setup_commodity_failure_alarm()

    def fixup_for_time(self, last_update_time, is_locked, is_baby=False, is_npc=False, decay_enabled=DEFAULT):
        if self.time_passage_fixup_type() == CommodityTimePassageFixupType.FIXUP_USING_TIME_ELAPSED:
            if last_update_time is not None and not is_locked:
                if decay_enabled is DEFAULT:
                    final_decay_enabled = self.decay_enabled
                else:
                    final_decay_enabled = decay_enabled
                self.decay_enabled = True
                self.update_commodity_to_time(last_update_time)
                self.decay_enabled = final_decay_enabled
        elif self.time_passage_fixup_type() == CommodityTimePassageFixupType.FIXUP_USING_AUTOSATISFY_CURVE and (self._off_lot_simulation == self.OFF_LOT_SIM_DISABLED or is_baby or is_npc and self._off_lot_simulation != self.OFF_LOT_SIM_ALL):
            self.set_to_auto_satisfy_value()

    def fixup_on_sim_instantiated(self):
        sim = self.tracker.owner
        time_sim_was_saved = sim.time_sim_was_saved
        is_locked = sim.is_locked(self)
        self.fixup_for_time(time_sim_was_saved, is_locked, self.tracker.owner.is_baby, sim.is_npc)

    def update_commodity_to_time(self, time, update_callbacks=False):
        self._last_update = time
        old_value = self._value
        self._update_value()
        if update_callbacks:
            self._update_callback_listeners(old_value=old_value, new_value=self._value)

    def set_to_auto_satisfy_value(self):
        if self.use_autosatisfy_curve and self._auto_satisfy_curve:
            now = services.time_service().sim_now
            time_sim_was_saved = self.tracker.owner.time_sim_was_saved
            if time_sim_was_saved is None and self.use_auto_satisfy_curve_as_initial_value and time_sim_was_saved == now:
                return False
            random_time_offset = random.uniform(-1*self.auto_satisfy_curve_random_time_offset, self.auto_satisfy_curve_random_time_offset)
            now += interval_in_sim_minutes(random_time_offset)
            current_hour = now.hour() + now.minute()/date_and_time.MINUTES_PER_HOUR
            auto_satisfy_value = self._auto_satisfy_curve.get(current_hour)
            maximum_auto_satisfy_time = interval_in_sim_minutes(self.maximum_auto_satisfy_time)
            if time_sim_was_saved is None or time_sim_was_saved + maximum_auto_satisfy_time <= now:
                self._last_update = services.time_service().sim_now
                self.set_user_value(auto_satisfy_value)
                return True
            if time_sim_was_saved >= now:
                return False
            else:
                interpolation_time = (now - time_sim_was_saved).in_ticks()/maximum_auto_satisfy_time.in_ticks()
                current_value = self.get_user_value()
                new_value = (auto_satisfy_value - current_value)*interpolation_time + current_value
                self._last_update = services.time_service().sim_now
                self.set_user_value(new_value)
                return True
        return False

    def set_to_exact_auto_satisfy_value(self):
        if self.use_autosatisfy_curve and self._auto_satisfy_curve:
            now = services.time_service().sim_now
            current_hour = now.hour() + now.minute()/date_and_time.MINUTES_PER_HOUR
            auto_satisfy_value = self._auto_satisfy_curve.get(current_hour)
            self._last_update = services.time_service().sim_now
            self.set_user_value(auto_satisfy_value)
            return True
        return False

    def on_remove(self, on_destroy=False):
        super().on_remove(on_destroy=on_destroy)
        self.stop_regular_simulation(on_destroy=on_destroy)
        self.stop_low_level_simulation(on_destroy=on_destroy)
        self._stop_commodity_failure_alarm()
        if self._buff_handle is not None:
            self.tracker.owner.remove_buff(self._buff_handle, on_destroy=on_destroy)
            self._buff_handle = None
        if self._distress_buff_handle is not None:
            self.tracker.owner.remove_buff(self._distress_buff_handle, on_destroy=on_destroy)
            self._distress_buff_handle = None

    def _activate_convergence_callback(self):
        if self._allow_convergence_callback_to_activate:
            if self._convergence_callback_data is not None:
                self.add_callback_listener(self._convergence_callback_data)
            self._allow_convergence_callback_to_activate = False

    def set_value(self, value, from_load=False, **kwargs):
        if from_load:
            super().set_value(value, from_load=from_load, **kwargs)
            if self._buff_handle is not None:
                self._get_change_rate_without_decay()
            if self._allow_convergence_callback_to_activate and self._convergence_callback_data is not None:
                self._activate_convergence_callback()
            return
        with self._suppress_client_updates_context_manager(is_rate_change=False):
            change = value - self.get_value()
            self._update_buff(change)
            super().set_value(value, from_load=from_load, **kwargs)
            if self.visible:
                self.send_commodity_progress_msg(is_rate_change=False)
            self._update_buff(self._get_change_rate_without_decay())
            self._activate_convergence_callback()
            self._send_value_update_event()

    def _update_value(self):
        old_value = self._value
        time_delta = super()._update_value()
        if old_value != self._value:
            self._send_value_update_event()
        return time_delta

    def _send_value_update_event(self):
        owner = self._tracker._owner if self._tracker is not None else None
        if owner is not None and owner.is_sim and not owner.is_npc:
            services.get_event_manager().process_event(test_events.TestEvent.StatValueUpdate, sim_info=owner, statistic=self.stat_type, custom_keys=(self.stat_type,))

    def _on_statistic_modifier_changed(self, notify_watcher=True):
        super()._on_statistic_modifier_changed(notify_watcher=notify_watcher)
        self.send_commodity_progress_msg()
        self._update_buff(self._get_change_rate_without_decay())
        self._update_callback_listeners()
        self._activate_convergence_callback()

    def _recalculate_modified_decay_rate(self):
        super()._recalculate_modified_decay_rate()
        if self._decay_rate_modifier > 1:
            self._update_buff(-self._decay_rate_modifier)
        else:
            self._update_buff(0)

    @property
    def buff_handle(self):
        return self._buff_handle

    def _update_buff(self, change_rate):
        if self._buff_handle is not None:
            buff_type = self.tracker.owner.get_buff_type(self._buff_handle)
            transition_into_buff_id = 0
            if buff_type.visible:
                transition_into_buff_id = self._get_next_buff_commodity_decaying_to()
            self.tracker.owner.buff_commodity_changed(self._buff_handle, change_rate=change_rate, transition_into_buff_id=transition_into_buff_id)

    @property
    def state_index(self):
        return self._current_state_index

    def get_state_index(self):
        if self._current_state_index is not None:
            return self._current_state_index
        current_value = self.get_value()
        for (index, state) in enumerate(reversed(self.commodity_states)):
            if current_value >= state.value:
                return len(self.commodity_states) - index - 1

    @classmethod
    def get_state_index_matches_buff_type(cls, buff_type):
        if cls.commodity_states:
            for index in range(len(cls.commodity_states)):
                state = cls.commodity_states[index]
                if state.buff is None:
                    pass
                elif state.buff.buff_type is buff_type:
                    return index

    @classproperty
    def max_value(cls):
        return cls.max_value_tuning

    @classproperty
    def min_value(cls):
        return cls.min_value_tuning

    @classproperty
    def best_value(cls):
        if cls.best_value_tuning.best_value_tuning_method == CommodityBestValueTuningMethod.USE_MAX_VALUE_TUNING:
            return cls.max_value
        if cls.best_value_tuning.best_value_tuning_method == CommodityBestValueTuningMethod.USE_MIN_VALUE_TUNING:
            return cls.min_value
        logger.error('CommodityBestValueTuningMethod not specified when returning the best value for commodity: {}', cls)
        return cls.max_value

    @classproperty
    def autonomy_weight(cls):
        return cls.weight

    @classproperty
    def default_value(cls):
        if not cls.initial_as_default:
            return cls._default_convergence_value
        else:
            return cls.initial_value

    @constproperty
    def is_commodity():
        return True

    @constproperty
    def is_skill():
        return False

    def _clamp(self, value=None):
        if value is None:
            value = self._value
        self._value = sims4.math.clamp(self.min_value_tuning, value, self.max_value_tuning)

    def save_statistic(self, commodities, skills, ranked_statistics, tracker):
        message = protocols.Commodity()
        message.name_hash = self.guid64
        message.value = self.get_saved_value()
        message.apply_buff_on_start_up = self.buff_handle is not None
        if self.buff_handle is not None:
            buff_reason = tracker._owner.get_buff_reason(self.buff_handle)
            if buff_reason is not None:
                message.buff_reason = buff_reason
        elif self.force_buff_reason is not None:
            message.buff_reason = self.force_buff_reason
        if self._time_of_last_value_change:
            message.time_of_last_value_change = self._time_of_last_value_change.absolute_ticks()
        commodities.append(message)

    @classproperty
    def add_if_not_in_tracker(cls):
        return cls._add_if_not_in_tracker

    def needs_fixup_on_load(self):
        return True

    def needs_fixup_on_load_for_objects(self):
        return self.time_passage_fixup_for_objects

    def has_auto_satisfy_value(self):
        return True

    @classmethod
    def load_statistic_data(cls, tracker, data):
        super().load_statistic_data(tracker, data)
        stat = tracker.get_statistic(cls)
        if stat is not None:
            stat.force_apply_buff_on_start_up = data.apply_buff_on_start_up
            if data.buff_reason.hash:
                stat.force_buff_reason = Localization_pb2.LocalizedString()
                stat.force_buff_reason.MergeFrom(data.buff_reason)
            stat.load_time_of_last_value_change(data)

    def time_passage_fixup_type(self):
        return self._time_passage_fixup_type

    @classmethod
    def get_categories(cls):
        return cls._categories

    def get_adjusted_state_index(self):
        if self._states_ordered_best_to_worst:
            return len(self.commodity_states) - 1 - self.state_index
        else:
            return self.state_index

    def send_commodity_progress_msg(self, is_rate_change=True):
        self.create_and_send_commodity_update_msg(is_rate_change=is_rate_change)

    def create_and_send_commodity_update_msg(self, is_rate_change=True, from_add=False):
        if not self.is_visible_commodity():
            return
        commodity_msg = Commodities_pb2.CommodityProgressUpdate()
        self.populate_commodity_update_msg(commodity_msg, is_rate_change=is_rate_change)
        if commodity_msg is not None:
            send_sim_commodity_progress_update_message(self.tracker._owner, commodity_msg)

    def is_visible_commodity(self):
        if self.tracker is None or not self.tracker.owner.is_sim:
            return False
        if not self.visible:
            return False
        if not self.commodity_states:
            return False
        if self.state_index is None:
            return False
        elif self._suppress_client_updates:
            return False
        return True

    def populate_commodity_update_msg(self, commodity_msg, is_rate_change=True):
        commodity_msg.commodity_id = self.guid64
        commodity_msg.current_value = self.get_value()
        commodity_msg.rate_of_change = self.get_change_rate()
        commodity_msg.commodity_state_index = self.state_index
        commodity_msg.is_rate_change = is_rate_change
        commodity_msg.adjusted_state_index = self.get_adjusted_state_index()
        commodity_msg.affects_plumbob_color = self._affects_plumbob_color

    def on_unlock(self, auto_satisfy=True):
        super().on_unlock(auto_satisfy=auto_satisfy)
        if auto_satisfy:
            self.set_to_exact_auto_satisfy_value()

class RuntimeCommodity(Commodity):
    INSTANCE_SUBCLASSES_ONLY = True

    @classmethod
    def generate(cls, name):
        ProxyClass = type(cls)(name, (cls,), {'INSTANCE_SUBCLASSES_ONLY': True})
        ProxyClass.reloadable = False
        key = sims4.resources.get_resource_key(name, ProxyClass.tuning_manager.TYPE)
        ProxyClass.tuning_manager.register_tuned_class(ProxyClass, key)
        return ProxyClass
