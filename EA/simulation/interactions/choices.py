import collectionsimport weakreffrom event_testing.resolver import SingleSimResolverfrom event_testing.results import TestResult, EnqueueResultfrom sims4.localization import LocalizationHelperTuningfrom singletons import DEFAULTfrom uid import unique_idimport gsi_handlers.sim_handlers_logimport sims4.log__all__ = ['ChoiceMenu']_normal_logger = sims4.log.Logger('Interactions')logger = _normal_loggerwith sims4.reload.protected(globals()):
    _show_interaction_failure_reason = False
def toggle_show_interaction_failure_reason(enable=False):
    global _show_interaction_failure_reason
    _show_interaction_failure_reason = enable if enable is not None else not _show_interaction_failure_reason

class MenuItem:
    __slots__ = ('aop', 'result', 'context', 'category_key', 'deprecated', 'target_invalid')

    def __init__(self, aop, context, result, category_key):
        self.aop = aop
        self.context = context
        self.result = result
        self.category_key = category_key
        self.deprecated = False
        self.target_invalid = False

    def __repr__(self):
        return str(self.aop)

@unique_id('revision')
class ChoiceMenu:

    def __init__(self, sim):
        self.menu_items = collections.OrderedDict()
        if sim is not None:

            def remove_sim(k, selfref=weakref.ref(self)):
                self = selfref()
                if self is not None:
                    self.clear()

            self.simref = sim.ref(remove_sim)
        else:
            self.simref = None
        self.objects = weakref.WeakKeyDictionary()

        def remove(k, selfref=weakref.ref(self)):
            self = selfref()
            if self is not None:
                id_list = self.objects.data.get(k)
                del self.objects.data[k]
                if id_list:
                    for choice_id in id_list:
                        self.menu_items[choice_id].deprecated = True
                        self.menu_items[choice_id].target_invalid = True

        self.objects._remove = remove

    def add_potential_aops(self, target, context, potential_aops):
        scoring_gsi_handler = {} if gsi_handlers.sim_handlers_log.pie_menu_generation_archiver.enabled else None
        for aop in potential_aops:
            si_content_score = aop.affordance.get_content_score(context.sim, SingleSimResolver(context.sim), [aop], scoring_gsi_handler, **aop.interaction_parameters)
            aop.content_score = si_content_score
            result = self.add_aop(aop, context, user_pick_target=target)
            if result or not result.tooltip:
                pass
            else:
                if result:
                    result = DEFAULT
                potentials = aop.affordance.potential_pie_menu_sub_interactions_gen(aop.target, context, scoring_gsi_handler, **aop.interaction_parameters)
                for (mixer_aop, mixer_aop_result) in potentials:
                    if result is not DEFAULT:
                        mixer_aop_result = result
                    self.add_aop(mixer_aop, context, result_override=mixer_aop_result, do_test=False)
        if gsi_handlers.sim_handlers_log.pie_menu_generation_archiver.enabled:
            gsi_handlers.sim_handlers_log.archive_pie_menu_option(context.sim, target, scoring_gsi_handler)

    def __len__(self):
        return len(self.menu_items)

    def __iter__(self):
        return iter(self.menu_items.items())

    def invalidate_choices_based_on_target(self, target):
        id_list = self.objects.get(target)
        if id_list is not None:
            del self.objects[target]
            for choice_id in id_list:
                menu_item = self.menu_items[choice_id]
                menu_item.deprecated = True
                menu_item.target_invalid = True

    @staticmethod
    def is_valid_aop(aop, context, user_pick_target=None, result_override=DEFAULT, do_test=True):
        test_result = None
        result = TestResult.TRUE
        if result_override is not DEFAULT:
            result = result_override
        elif do_test:
            if user_pick_target is not None and user_pick_target.check_affordance_for_suppression(context.sim, aop, user_directed=True):
                result = TestResult(False, '{} failed, aop is being suppressed.', aop)
            else:
                result = aop.test(context)
                if gsi_handlers.sim_handlers_log.pie_menu_generation_archiver.enabled:
                    test_result = str(result)
            if not result:
                logger.info('Test Failure: {}: {}', aop, result.reason)
            if not result:
                if _show_interaction_failure_reason:
                    result = TestResult(result.result, tooltip=lambda *_, reason=result.reason, **__: LocalizationHelperTuning.get_name_value_pair('Failure', reason))
                elif not result.tooltip:
                    result = TestResult(False, '{} failed and has no tooltip', aop)
        if gsi_handlers.sim_handlers_log.pie_menu_generation_archiver.enabled:
            gsi_handlers.sim_handlers_log.log_aop_result(context.sim, aop, result, test_result)
        return result

    def add_aop(self, aop, context, user_pick_target=None, result_override=DEFAULT, do_test=True):
        result = ChoiceMenu.is_valid_aop(aop, context, user_pick_target=user_pick_target, result_override=result_override, do_test=do_test)
        if aop.affordance.allow_user_directed is False:
            if _show_interaction_failure_reason:
                if result:
                    failure_result = TestResult(False, tooltip=lambda *_, **__: LocalizationHelperTuning.get_name_value_pair('Failure', 'Not allowed user-directed'))
                else:
                    failure_result = result
                self._add_menu_item(aop, context, failure_result)
            return result
        if result or not result.tooltip:
            return result
        self._add_menu_item(aop, context, result)
        return result

    def _add_menu_item(self, aop, context, result):
        category = aop.affordance.get_pie_menu_category(**aop.interaction_parameters)
        category_key = None if category is None else category.guid64
        self.menu_items[aop.aop_id] = MenuItem(aop, context, result, category_key)
        if aop.target is not None:
            id_list = self.objects.get(aop.target)
            if id_list is None:
                id_list = []
                self.objects[aop.target] = id_list
            id_list.append(aop.aop_id)

    def select(self, choice_id):
        selection = self.menu_items.get(choice_id)
        context = selection.context
        if context.sim is not None and (selection.aop.affordance.immediate or context.sim.queue.visible_len() >= context.sim.queue.max_interactions):
            return EnqueueResult.NONE
        if selection is not None:
            if selection.result and not selection.target_invalid:
                return selection.aop.test_and_execute(context)
            logger.warn('Attempt to select invalid interaction from a ChoiceMenu')
        return EnqueueResult.NONE

    def clear(self):
        self.menu_items.clear()
        self.objects = None
        self.context = None
        self.simref = None
