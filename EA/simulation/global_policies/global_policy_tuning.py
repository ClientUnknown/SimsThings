from date_and_time import TimeSpanfrom display_snippet_tuning import DisplaySnippetfrom elements import SleepElementfrom event_testing.resolver import SingleSimResolverfrom event_testing.test_events import TestEventfrom global_policies.global_policy_effects import GlobalPolicyEffectVariantsfrom global_policies.global_policy_enums import GlobalPolicyProgressEnum, GlobalPolicyTokenTypefrom interactions.utils.loot import LootActionsfrom sims4.localization import TunableLocalizedStringFactory, LocalizationHelperTuningfrom sims4.tuning.tunable import TunableList, TunableRangeimport servicesimport sims4logger = sims4.log.Logger('Global Policy Tuning', default_owner='shipark')
class GlobalPolicy(DisplaySnippet):
    GLOBAL_POLICY_TOKEN_NON_ACTIVE = TunableLocalizedStringFactory(description='\n        Display string that appears when trying to use a Global Policy Token\n        referencing a non-active Global Policy.\n        ')
    INSTANCE_TUNABLES = {'decay_days': TunableRange(description='\n            The number of days it will take for the global policy to revert to\n            not-complete. Decay begins when the policy is completed.\n            ', tunable_type=int, default=5, minimum=0), 'progress_initial_value': TunableRange(description='\n            The initial value of global policy progress. Progress begins when\n            the policy is first set to in-progress.\n            ', tunable_type=int, default=0, minimum=0), 'progress_max_value': TunableRange(description='\n            The max value of global policy progress. Once the policy progress\n            reaches the max threshold, global policy state becomes complete.\n            ', tunable_type=int, default=100, minimum=1), 'loot_on_decay': TunableList(description='\n            A list of loot actions that will be run when the policy decays.\n            ', tunable=LootActions.TunableReference(description='\n                The loot action will target the active Sim.\n                ')), 'loot_on_complete': TunableList(description='\n            A list of loot actions that will be run when the policy is complete.\n            ', tunable=LootActions.TunableReference(description='\n                The loot action will target the active Sim.\n                ')), 'global_policy_effects': TunableList(description='\n            Actions to apply when the global policy is enacted.\n            ', tunable=GlobalPolicyEffectVariants(description='\n                The action to apply.\n                '))}

    @classmethod
    def _verify_tuning_callback(cls):
        if cls.progress_max_value < cls.progress_initial_value:
            logger.error('Global Policy {} has a max value less than the initial value. This is not allowed.', cls)

    def __init__(self, progress_initial_value=None, **kwargs):
        super().__init__(**kwargs)
        self._progress_state = GlobalPolicyProgressEnum.NOT_STARTED
        self._progress_value = 0
        self.decay_handler = None
        self.end_time_from_load = 0

    @property
    def progress_state(self):
        return self._progress_state

    @property
    def progress_value(self):
        return self._progress_value

    def pre_load(self, global_policy_data):
        self.set_progress_state(GlobalPolicyProgressEnum(global_policy_data.progress_state), from_load=True)
        self.set_progress_value(global_policy_data.progress_value, from_load=True)
        if global_policy_data.decay_days != 0:
            self.end_time_from_load = global_policy_data.decay_days

    def set_progress_state(self, progress_enum, from_load=False):
        old_state = self._progress_state
        self._progress_state = progress_enum
        if old_state != self._progress_state and not from_load:
            services.get_event_manager().process_event(TestEvent.GlobalPolicyProgress, custom_keys=(type(self), self))

    def set_progress_value(self, new_value, from_load=False):
        self._progress_value = new_value
        if not from_load:
            self._process_new_value(new_value)
        return self.progress_state

    def _process_new_value(self, new_value):
        if new_value <= self.progress_initial_value and self.progress_state != GlobalPolicyProgressEnum.NOT_STARTED:
            self.set_progress_state(GlobalPolicyProgressEnum.NOT_STARTED)
            self.decay_handler = None
            for effect in self.global_policy_effects:
                effect.turn_off(self.guid64)
        elif new_value >= self.progress_max_value and self.progress_state != GlobalPolicyProgressEnum.COMPLETE:
            self.set_progress_state(GlobalPolicyProgressEnum.COMPLETE)
            for effect in self.global_policy_effects:
                effect.turn_on(self.guid64)
        elif self.progress_state != GlobalPolicyProgressEnum.IN_PROGRESS:
            self.set_progress_state(GlobalPolicyProgressEnum.IN_PROGRESS)

    def apply_policy_loot_to_active_sim(self, loot_list, resolver=None):
        if resolver is None:
            resolver = SingleSimResolver(services.active_sim_info())
        for loot_action in loot_list:
            loot_action.apply_to_resolver(resolver)

    def decay_policy(self, timeline):
        yield timeline.run_child(SleepElement(TimeSpan.ZERO))
        services.global_policy_service().set_global_policy_progress(self, self.progress_initial_value)
        self.decay_handler = None
        self.apply_policy_loot_to_active_sim(self.loot_on_decay)

    @classmethod
    def get_non_active_display(cls, token_data):
        if token_data.token_property == GlobalPolicyTokenType.NAME:
            return LocalizationHelperTuning.get_raw_text(token_data.global_policy.display_name())
        if token_data.token_property == GlobalPolicyTokenType.PROGRESS:
            return LocalizationHelperTuning.get_raw_text(cls.GLOBAL_POLICY_TOKEN_NON_ACTIVE())
        logger.error('Invalid Global Policy Property {} tuned on the Global Policy token.'.format(token_data.property))

    def get_active_policy_display(self, token_data):
        if token_data.token_property == GlobalPolicyTokenType.NAME:
            return LocalizationHelperTuning.get_raw_text(self.display_name())
        if token_data.token_property == GlobalPolicyTokenType.PROGRESS:
            progress_percentage_str = str(int(round(float(self.progress_value)/float(self.progress_max_value), 2)*100))
            return LocalizationHelperTuning.get_raw_text(progress_percentage_str)
        logger.error('Invalid Global Policy Property {} tuned on the Global Policy token.'.format(token_data.property))
