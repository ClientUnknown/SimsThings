import operatorimport randomfrom sims4.localization import TunableLocalizedStringfrom sims4.tuning.instances import HashedTunedInstanceMetaclassfrom sims4.tuning.tunable import HasTunableReference, Tunable, TunableResourceKey, TunableEnumEntry, TunableTuple, TunableInterval, OptionalTunablefrom sims4.tuning.tunable_base import ExportModesfrom sims4.utils import classproperty, flexmethodfrom statistics.base_statistic import BaseStatistic, GalleryLoadBehaviorfrom statistics.tunable import TunableStatAsmParamimport servicesimport sims4.resources
class Statistic(HasTunableReference, BaseStatistic, metaclass=HashedTunedInstanceMetaclass, manager=services.statistic_manager()):
    INSTANCE_TUNABLES = {'initial_tuning': TunableTuple(description=' \n            The Initial value for this statistic. Can either be a single\n            value, range, or use auto satisfy curve to determine initial\n            value.  Range value will take precedence over single value\n            range.\n            ', _use_stat_value_on_init=Tunable(description='\n                If enabled, we will use the initial tuning to set the\n                statistic in the place of other systems (like states).\n                Otherwise, those states or systems will set the initial\n                value of the statistic (a state linked to this stat for\n                example, will set the statistic to whatever default tuning\n                is on the state). \n                TLDR: If checked, the statistic sets the\n                state. Otherwise, the state sets up this statistic. \n                Note:\n                If unchecked, we error if any initial values are tuned as\n                they imply that we want to use them.\n                ', tunable_type=bool, default=False), _value_range=OptionalTunable(description='\n                If enabled then when we first add this statistic to an object,\n                the initial value of the statistic will be set to a random\n                value within this interval.\n                ', tunable=TunableInterval(description='\n                    An interval that will be used for the initial value of this\n                    statistic.\n                    ', tunable_type=int, default_lower=0, default_upper=100)), _initial_value=Tunable(description='\n                The initial value for this stat.\n                ', tunable_type=int, default=0)), 'stat_asm_param': TunableStatAsmParam.TunableFactory(locked_args={'use_effective_skill_level': True}), 'min_value_tuning': Tunable(description='\n            The minimum value that this statistic can reach.\n            ', tunable_type=int, default=0, export_modes=ExportModes.All), 'max_value_tuning': Tunable(description='\n            The minimum value that this statistic can reach.\n            ', tunable_type=int, default=100, export_modes=ExportModes.All), 'stat_name': TunableLocalizedString(description='\n            Localized name of this statistic.\n            ', allow_none=True, export_modes=ExportModes.All), 'icon': TunableResourceKey(description='\n            Icon to be displayed for the Statistic.\n            ', allow_none=True, resource_types=sims4.resources.CompoundTypes.IMAGE), 'persisted_tuning': Tunable(description="\n            Whether this statistic will persist when saving a Sim or an object.\n            For example, a Sims's SI score statistic should never persist.\n            ", tunable_type=bool, default=True), 'gallery_load_behavior': TunableEnumEntry(description="\n            When owner of commodity is loaded from the gallery, tune this to\n            determine if commodity should be loaded or not.\n            \n            DONT_LOAD = Don't load statistic when owner is coming from gallery\n            \n            LOAD_ONLY_FOR_OBJECT = Load only if statistic is being added to an\n            object.  If this statistic is tuned as a linked stat to a state, make\n            sure the state is also marked as gallery persisted. i.e. Statistics\n            like fish_freshness or gardening_groth. Switching on this bit has\n            performance implications when downloading a lot from the gallery.\n            Please discuss with a GPE when setting this tunable.\n    \n            LOAD_ONLY_FOR_SIM = Load only if statistic is being added to a sim.\n            LOAD_FOR_ALL = Always load commodity.  This has the same ramifications\n            as LOAD_ONLY_FOR_OBJECT if owner is an object.\n            ", tunable_type=GalleryLoadBehavior, default=GalleryLoadBehavior.LOAD_ONLY_FOR_SIM), 'apply_value_to_object_cost': Tunable(description='\n            Whether the value of this statistic should be added to the value of the owner\n            of statistic. Affects the price when sold.\n            ', tunable_type=bool, default=False)}

    def __init__(self, tracker):
        super().__init__(tracker, self.get_initial_value())
        self._static_modifiers = None
        self._update_modified_value()

    def _update_modified_value(self):
        value = self._value
        default_value = self.default_value
        if self._static_modifiers is not None:
            for modifier in self._static_modifiers:
                value = modifier.apply(value, default_value)
        value = self.clamp(value)
        self._modified_value = value

    @classproperty
    def name(cls):
        return cls.__name__

    @classproperty
    def max_value(cls):
        return cls.max_value_tuning

    @classproperty
    def min_value(cls):
        return cls.min_value_tuning

    @classproperty
    def best_value(cls):
        return cls.max_value

    @classproperty
    def persisted(cls):
        return cls.persisted_tuning

    @classproperty
    def persists_across_gallery_for_state(cls):
        if cls.gallery_load_behavior == GalleryLoadBehavior.LOAD_FOR_ALL or cls.gallery_load_behavior == GalleryLoadBehavior.LOAD_ONLY_FOR_OBJECT:
            return True
        return False

    @classproperty
    def use_stat_value_on_initialization(cls):
        return cls.initial_tuning._use_stat_value_on_init

    @classproperty
    def initial_value(cls):
        return cls.initial_tuning._initial_value

    @classproperty
    def initial_value_range(cls):
        return cls.initial_tuning._value_range

    @classmethod
    def get_initial_value(cls):
        if cls.initial_value_range is None:
            return cls.initial_value
        return random.uniform(cls.initial_value_range.lower_bound, cls.initial_value_range.upper_bound)

    @classproperty
    def default_value(cls):
        return cls.initial_value

    def get_asm_param(self):
        return self.stat_asm_param.get_asm_param(self)

    def add_statistic_static_modifier(self, modifier):
        if self._static_modifiers is None:
            self._static_modifiers = []
        self._static_modifiers.append(modifier)
        self._static_modifiers.sort(key=operator.attrgetter('priority'))
        old_value = self._modified_value
        self._update_modified_value()
        if self._modified_value != old_value:
            self._notify_change(old_value)

    def remove_statistic_static_modifier(self, modifier):
        if self._static_modifiers is not None and modifier in self._static_modifiers:
            self._static_modifiers.remove(modifier)
            if not self._static_modifiers:
                self._static_modifiers = None
            old_value = self._modified_value
            self._update_modified_value()
            if self._modified_value != old_value:
                self._notify_change(old_value)

    def set_value(self, value, **kwargs):
        old_value = self._modified_value
        self._value = value
        self._clamp()
        self._update_modified_value()
        self._notify_change(old_value)

    def _add_value(self, amount, **kwargs):
        new_value = self._value + amount
        self.set_value(new_value, **kwargs)

    @flexmethod
    def get_value(cls, inst):
        if inst is not None:
            return inst._modified_value
        else:
            return cls.default_value

    @classproperty
    def valid_for_stat_testing(cls):
        return True
