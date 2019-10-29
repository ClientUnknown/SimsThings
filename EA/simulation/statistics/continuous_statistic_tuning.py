import operatorfrom sims4.math import Thresholdfrom sims4.tuning.tunable import Tunable, OptionalTunable, TunableReference, TunableEnumEntry, TunableList, TunableTuple, TunableInterval, TunableSimMinutefrom sims4.tuning.tunable_base import GroupNamesfrom singletons import UNSETfrom statistics.base_statistic import GalleryLoadBehaviorfrom tag import Tagfrom ui.ui_dialog_notification import TunableUiDialogNotificationSnippetimport servicesimport sims4.tuning.tunableimport sims4.utilsimport statistics.continuous_statisticimport statistics.tunablelogger = sims4.log.Logger('ContinuousStatisticTuning', default_owner='msantander')
class _DecayOverrideNode:

    def __init__(self, lower_bound, upper_bound, decay_override, initial_delay_override=UNSET, final_delay_override=UNSET):
        self.lower_bound = lower_bound
        self.upper_bound = upper_bound
        self.decay_override = decay_override
        self.initial_delay_override = initial_delay_override
        self.final_delay_override = final_delay_override

    def __repr__(self):
        return '_DecayOverrideNode: {} from {} to {}'.format(self.decay_override, self.lower_bound, self.upper_bound)

class TunedContinuousStatistic(statistics.continuous_statistic.ContinuousStatistic):
    INSTANCE_SUBCLASSES_ONLY = True
    INSTANCE_TUNABLES = {'decay_rate': sims4.tuning.tunable.TunableRange(description='\n            The decay rate for this stat (per sim minute).\n            ', tunable_type=float, default=0.001, minimum=0.0, tuning_group=GroupNames.CORE), '_decay_rate_overrides': TunableList(description='\n            A list of decay rate overrides.  Whenever the value of the stat\n            falls into this range, the decay rate is overridden with the value\n            specified. This overrides the base decay, so all decay modifiers\n            will still apply. The ranges are inclusive on the lower bound and\n            exclusive on the upper bound.  Overlapping values are not allowed\n            and will behave in an undefined manner.\n            ', tunable=TunableTuple(description='\n                The interval/decay_override pair.\n                ', interval=TunableInterval(description='\n                    The range at which this override will apply.  It is inclusive\n                    on the lower bound and exclusive on the upper bound.\n                    ', tunable_type=float, default_lower=-100, default_upper=100), decay_override=Tunable(description='\n                    The value that the base decay will be overridden with.\n                    ', tunable_type=float, default=0.0)), tuning_group=GroupNames.CORE), 'delayed_decay_rate': OptionalTunable(description="\n            When enabled contains the tuning for delayed decay. Delayed decay\n            is decay that happens if the value of the commodity hasn't changed\n            in some time.\n            ", tunable=TunableTuple(description='\n                All of the tuning for delayed decay rate.\n                ', initial_delay=TunableSimMinute(description='\n                    Time, in sim minutes, before the warning that a decay will\n                    start will be shown.\n                    ', default=30, minimum=0), final_delay=TunableSimMinute(description='\n                    Tim, in sim minutes, after the warning is shown that the\n                    decay will actually begin.\n                    ', default=30, minimum=0), delayed_decay_rate=sims4.tuning.tunable.TunableRange(description='\n                    The decay rate for this stat that starts after a delayed\n                    amount of time where the value of the skill does not change.\n                    ', tunable_type=float, default=0.001, minimum=0.0), decay_warning=OptionalTunable(description='\n                    If enabled, the notification to show to warn the user that\n                    a specific statistic is about to start decaying.\n                    ', tunable=TunableUiDialogNotificationSnippet(), enabled_by_default=True), decay_rate_overrides=TunableList(description='\n                    A list of decay rate overrides.  Whenever the value of the \n                    stat falls into this range, the decay rate is overridden \n                    with the value specified. This overrides the base decay, \n                    so all decay modifiers will still apply. The ranges are \n                    inclusive on the lower bound and exclusive on the upper \n                    bound.  Overlapping values are not allowed and will behave \n                    in an undefined manner.\n                    ', tunable=TunableTuple(description='\n                        The interval/decay_override pair.\n                        ', interval=TunableInterval(description='\n                            The range at which this override will apply.  It is \n                            inclusive on the lower bound and exclusive on the \n                            upper bound.\n                            ', tunable_type=float, default_lower=-100, default_upper=100), decay_override=Tunable(description='\n                            The value that the base decay will be overridden with.\n                            ', tunable_type=float, default=0.0), initial_delay_override=TunableSimMinute(description='\n                            The override for how long, in Sim Minutes, the \n                            initial delay is before the warning is given about \n                            decay starting.\n                            ', default=30, minimum=0), final_delay_override=TunableSimMinute(description='\n                            The override for how long, in Sim Minutes, the \n                            final delay is before the actual decay begins, \n                            after displaying the warning.\n                            ', default=30, minimum=0))), npc_decay=Tunable(description="\n                    By default decay doesn't happen for NPC sims. If enabled\n                    this will turn on decay of this statistic for NPC sims.\n                    ", tunable_type=bool, default=False)), tuning_group=GroupNames.CORE), '_default_convergence_value': Tunable(description='\n            The value toward which the stat decays.\n            ', tunable_type=float, default=0.0, tuning_group=GroupNames.CORE), 'stat_asm_param': statistics.tunable.TunableStatAsmParam.TunableFactory(tuning_group=GroupNames.SPECIAL_CASES), 'min_value_tuning': Tunable(description='\n            The minimum value for this stat.\n            ', tunable_type=float, default=-100, tuning_group=GroupNames.CORE), 'max_value_tuning': Tunable(description='\n            The maximum value for this stat.\n            ', tunable_type=float, default=100, tuning_group=GroupNames.CORE), 'initial_value': Tunable(description='\n            The initial value for this stat.\n            ', tunable_type=float, default=0.0, tuning_group=GroupNames.CORE), 'persisted_tuning': Tunable(description="\n            Whether this statistic will persist when saving a Sim or an object.\n            For example, a Sims's SI score statistic should never persist.\n            ", tunable_type=bool, default=True, tuning_group=GroupNames.SPECIAL_CASES), 'communicable_by_interaction_tag': OptionalTunable(description='\n            List of Tag and loot pairs that will trigger if either the actor or\n            target of an interaction has this statistic to give the first loot\n            whose tag matches any tag on the interaction.\n            \n            So you could do one loot for high risk socials, (tagged as such) a\n            different loot for low risk socials (tagged as such) a third loot\n            for high risk object interactions (licking bowl, maybe?), and\n            fourth loot for low risk object interaction\n            "generically using an object".\n            ', tunable=TunableList(tunable=TunableTuple(tag=TunableEnumEntry(description='\n                        Tag on interaction required to apply this loot.\n                        ', tunable_type=Tag, default=Tag.INVALID), loot=TunableReference(description='\n                        The loot to give.\n                        ', manager=services.get_instance_manager(sims4.resources.Types.ACTION), class_restrictions=('LootActions',)))), tuning_group=GroupNames.SPECIAL_CASES), 'gallery_load_behavior': TunableEnumEntry(description="\n            When owner of commodity is loaded from the gallery, tune this to\n            determine if commodity should be loaded or not.\n            \n            DONT_LOAD = Don't load statistic when owner is coming from gallery\n            \n            LOAD_ONLY_FOR_OBJECT = Load only if statistic is being added to an\n            object.  If this statistic is tuned as a linked stat to a state,\n            make sure the state is also marked as gallery persisted. i.e.\n            Statistics like fish_freshness or gardening_groth. Switching on\n            this bit has performance implications when downloading a lot from\n            the gallery. Please discuss with a GPE when setting this tunable.\n    \n            LOAD_ONLY_FOR_SIM = Load only if statistic is being added to a sim.\n            LOAD_FOR_ALL = Always load commodity.  This has the same\n            ramifications as LOAD_ONLY_FOR_OBJECT if owner is an object.\n            ", tunable_type=GalleryLoadBehavior, default=GalleryLoadBehavior.LOAD_ONLY_FOR_SIM, tuning_group=GroupNames.SPECIAL_CASES)}

    @classmethod
    def _verify_tuning_callback(cls):
        if cls._decay_rate_overrides and cls.delayed_decay_rate is not None:
            logger.error('A Continous Statistic ({}) has tuned decay overrides \n            and tuned delayed decay rates. This is not supported. The override \n            will always be used and the delayed decay rate will never work. \n            Please choose one or the other or see a GPE if you really need this\n            to work for some reason. rfleig ', cls)

    def __init__(self, tracker, initial_value):
        super().__init__(tracker, initial_value)
        self._decay_override_calllback_handles = None
        if not self._tracker.suppress_callback_setup_during_load:
            self._create_new_override_callbacks()

    @sims4.utils.classproperty
    def max_value(cls):
        return cls.max_value_tuning

    @sims4.utils.classproperty
    def min_value(cls):
        return cls.min_value_tuning

    @sims4.utils.classproperty
    def best_value(cls):
        return cls.max_value

    def get_asm_param(self):
        return self.stat_asm_param.get_asm_param(self)

    @sims4.utils.classproperty
    def persisted(cls):
        return cls.persisted_tuning

    @sims4.utils.classproperty
    def persists_across_gallery_for_state(cls):
        if cls.gallery_load_behavior == GalleryLoadBehavior.LOAD_FOR_ALL or cls.gallery_load_behavior == GalleryLoadBehavior.LOAD_ONLY_FOR_OBJECT:
            return True
        return False

    @classmethod
    def _tuning_loaded_callback(cls):
        cls._decay_override_list = cls._initialize_decay_override_list(cls._decay_rate_overrides, cls.decay_rate)
        if cls.delayed_decay_rate:
            cls._delayed_decay_override_list = cls._initialize_decay_override_list(cls.delayed_decay_rate.decay_rate_overrides, cls.delayed_decay_rate.delayed_decay_rate, delay=True)

    @classmethod
    def _initialize_decay_override_list(cls, override_tuning, default_decay, delay=False):
        if not override_tuning:
            return ()
        if delay:
            decay_override_list = [_DecayOverrideNode(override_data.interval.lower_bound, override_data.interval.upper_bound, override_data.decay_override, override_data.initial_delay_override, override_data.final_delay_override) for override_data in override_tuning]
        else:
            decay_override_list = [_DecayOverrideNode(override_data.interval.lower_bound, override_data.interval.upper_bound, override_data.decay_override) for override_data in override_tuning]
        decay_override_list.sort(key=lambda node: node.lower_bound)
        final_decay_override_list = []
        last_lower_bound = cls.max_value + 1
        for node in reversed(decay_override_list):
            if last_lower_bound > node.upper_bound:
                default_node = _DecayOverrideNode(node.upper_bound, last_lower_bound, default_decay)
                final_decay_override_list.insert(0, default_node)
            elif last_lower_bound < node.upper_bound:
                logger.error('Tuning error: two nodes are overlapping in continuous statistic decay overrides: {}', cls)
                node.upper_bound = last_lower_bound
            final_decay_override_list.insert(0, node)
            last_lower_bound = node.lower_bound
        if final_decay_override_list and final_decay_override_list[0].lower_bound > cls.min_value:
            default_node = _DecayOverrideNode(cls.min_value, final_decay_override_list[0].lower_bound, default_decay)
            final_decay_override_list.insert(0, default_node)
        return tuple(final_decay_override_list)

    def fixup_callbacks_during_load(self):
        super().fixup_callbacks_during_load()
        self._remove_decay_override_callbacks()
        self._create_new_override_callbacks()

    def _add_decay_override_callbacks(self, override_data, callback):
        if not override_data:
            return
        self._decay_override_calllback_handles = []
        value = self.get_value()
        for override in override_data:
            if value >= override.lower_bound and value < override.upper_bound:
                threshold = Threshold(override.lower_bound, operator.lt)
                self._decay_override_calllback_handles.append(self.create_and_add_callback_listener(threshold, callback))
                threshold = Threshold(override.upper_bound, operator.ge)
                self._decay_override_calllback_handles.append(self.create_and_add_callback_listener(threshold, callback))
                break

    def _remove_decay_override_callbacks(self):
        if not self._decay_override_calllback_handles:
            return
        for callback_listener in self._decay_override_calllback_handles:
            self.remove_callback_listener(callback_listener)
        self._decay_override_calllback_handles.clear()

    def _on_decay_rate_override_changed(self, _):
        value = self.get_value()
        self._remove_decay_override_callbacks()
        for override in self._decay_override_list:
            if value >= override.lower_bound and value < override.upper_bound:
                self._decay_rate_override = override.decay_override
                self._create_new_override_callbacks()
                return
        logger.error('No node found for stat value of {} on {}', value, self)

    def _on_delayed_decay_rate_override_changed(self, _):
        value = self.get_value()
        self._remove_decay_override_callbacks()
        for override in self._delayed_decay_override_list:
            if value >= override.lower_bound and value < override.upper_bound:
                self._delayed_decay_rate_override = override.decay_override
                self._initial_delay_override = override.initial_delay_override
                self._final_delay_override = override.final_delay_override
                self._create_new_override_callbacks()
                return
        logger.error('No node found for stat value of {} on {}', value, self)

    def _create_new_override_callbacks(self):
        if self._decay_rate_overrides:
            self._add_decay_override_callbacks(self._decay_override_list, self._on_decay_rate_override_changed)
        if self.delayed_decay_rate is not None and self.delayed_decay_rate.decay_rate_overrides:
            self._add_decay_override_callbacks(self._delayed_decay_override_list, self._on_delayed_decay_rate_override_changed)
        self._update_callback_listeners(resort_list=False)
