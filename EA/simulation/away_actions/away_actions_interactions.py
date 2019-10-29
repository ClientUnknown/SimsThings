from event_testing.resolver import SingleSimResolverfrom event_testing.results import TestResultfrom event_testing.tests import TunableTestSet, TunableGlobalTestSetfrom interactions.base.immediate_interaction import ImmediateSuperInteractionfrom interactions.base.picker_interaction import SimPickerInteractionfrom objects import ALL_HIDDEN_REASONSfrom sims4.tuning.instances import lock_instance_tunablesfrom sims4.tuning.tunable_base import GroupNamesfrom sims4.utils import flexmethodimport services
def _common_away_action_tests(away_action_sim_info, away_action=None):
    if away_action_sim_info.is_baby:
        return TestResult(False, 'Away actions cannot be applied on babies.')
    if away_action is not None and away_action.available_when_instanced:
        return TestResult.TRUE
    if away_action_sim_info.is_instanced(allow_hidden_flags=ALL_HIDDEN_REASONS):
        return TestResult(False, 'Cannot apply away action on instanced sim.')
    else:
        return TestResult.TRUE

class ApplyAwayActionInteraction(ImmediateSuperInteraction):

    def __init__(self, *args, away_action=None, away_action_sim_info=None, away_action_target=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.away_action = away_action
        self.away_action_sim_info = away_action_sim_info
        self.away_action_target = away_action_target

    @classmethod
    def _test(cls, *args, away_action=None, away_action_sim_info=None, away_action_target=None, **kwargs):
        test_result = super()._test(*args, **kwargs)
        if not test_result:
            return test_result
        away_action_test_result = away_action.test(sim_info=away_action_sim_info, target=away_action_target)
        if not away_action_test_result:
            return away_action_test_result
        return _common_away_action_tests(away_action_sim_info, away_action)

    @flexmethod
    def _get_name(cls, inst, away_action=None, **interaction_parameters):
        if inst is not None:
            return inst.away_action.get_display_name()
        if away_action is not None:
            return away_action.get_display_name()
        return cls._get_name(**interaction_parameters)

    def _run_interaction_gen(self, timeline):
        self.away_action_sim_info.away_action_tracker.create_and_apply_away_action(self.away_action, self.away_action_target)

    @flexmethod
    def get_display_tooltip(cls, inst, away_action=None, **kwargs):
        if inst is not None:
            away_action = inst.away_action
        inst_or_cls = inst if inst is not None else cls
        if away_action is not None:
            return inst_or_cls.create_localized_string(away_action.pie_menu_tooltip, **kwargs)
        return inst_or_cls.get_display_tooltip(**kwargs)
lock_instance_tunables(ApplyAwayActionInteraction, simless=True, tests=TunableTestSet.DEFAULT_LIST)
class AwayActionSimPickerInteraction(SimPickerInteraction):

    def __init__(self, *args, away_action=None, away_action_sim_info=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.away_action = away_action
        self.away_action_sim_info = away_action_sim_info

    @classmethod
    def _test(cls, *args, away_action=None, away_action_sim_info=None, **kwargs):
        test_result = super()._test(*args, away_action=away_action, away_action_sim_info=away_action_sim_info, **kwargs)
        if not test_result:
            return test_result
        away_action_test_result = away_action.test(sim_info=away_action_sim_info, target=None)
        if not away_action_test_result:
            return away_action_test_result
        return _common_away_action_tests(away_action_sim_info, away_action)

    @flexmethod
    def _get_requesting_sim_info_for_picker(cls, inst, context, away_action_sim_info=None, **kwargs):
        if inst is not None:
            return inst.away_action_sim_info
        return away_action_sim_info

    @flexmethod
    def _get_actor_for_picker(cls, inst, *args, **kwargs):
        inst_or_cls = inst if inst is not None else cls
        return inst_or_cls._get_requesting_sim_info_for_picker(*args, **kwargs)

    @flexmethod
    def _get_name(cls, inst, away_action=None, **interaction_parameters):
        if inst is not None:
            return inst.away_action.get_display_name()
        if away_action is not None:
            return away_action.get_display_name()
        return cls._get_name(**interaction_parameters)

    def _run_interaction_gen(self, timeline):
        self._show_picker_dialog(self.away_action_sim_info)
        return True

    def _push_continuations(self, sim_ids, zone_datas=None):
        target_sim_id = next(iter(sim_ids))
        target_sim_info = services.sim_info_manager().get(target_sim_id)
        self.away_action_sim_info.away_action_tracker.create_and_apply_away_action(self.away_action, target_sim_info)
lock_instance_tunables(AwayActionSimPickerInteraction, simless=True, tests=TunableTestSet.DEFAULT_LIST)
class ApplyDefaultAwayActionInteraction(ImmediateSuperInteraction):
    INSTANCE_TUNABLES = {'away_action_sim_info_test': TunableTestSet(description='\n            A set of tests that will be run on the sim info that is trying to\n            run the set default away action interaction.\n            ', tuning_group=GroupNames.CORE)}

    def __init__(self, *args, away_action_sim_info=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.away_action_sim_info = away_action_sim_info

    @classmethod
    def _test(cls, *args, away_action_sim_info=None, **kwargs):
        test_result = super()._test(*args, **kwargs)
        if not test_result:
            return test_result
        if away_action_sim_info is not None and away_action_sim_info.career_tracker.currently_at_work:
            return TestResult(False, 'Sim is at work')
        test_result = _common_away_action_tests(away_action_sim_info)
        if not test_result:
            return test_result
        resolver = SingleSimResolver(away_action_sim_info)
        return cls.away_action_sim_info_test.run_tests(resolver)

    def _run_interaction_gen(self, timeline):
        self.away_action_sim_info.away_action_tracker.reset_to_default_away_action()
lock_instance_tunables(ApplyDefaultAwayActionInteraction, simless=True, tests=TunableTestSet.DEFAULT_LIST)