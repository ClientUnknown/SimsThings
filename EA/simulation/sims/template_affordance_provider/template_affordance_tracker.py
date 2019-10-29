from _collections import defaultdictfrom collections import Counterfrom event_testing.test_events import TestEventfrom interactions.aop import AffordanceObjectPairfrom sims.sim_info_tracker import SimInfoTrackerfrom sims4.tuning.tunable import TunableSimMinuteimport clockimport servicesimport sims4.loglogger = sims4.log.Logger('TemplateAffordanceTracker', default_owner='trevor')
class TemplateAffordanceTracker(SimInfoTracker):
    DEFAULT_POST_RUN_DURATION = TunableSimMinute(description='\n        The default number of Sim Minutes for a template affordance to be\n        provided once the once the template provider (interaction, buff, etc.)\n        is done.\n        ', default=30)

    def __init__(self, sim_info):
        self._owner_sim_info = sim_info
        self._affordance_templates = Counter()
        self._timed_affordance_templates = defaultdict(list)

    def on_sim_added(self):
        services.get_event_manager().register_single_event(self, TestEvent.InteractionComplete)

    def on_sim_removed(self):
        services.get_event_manager().unregister_single_event(self, TestEvent.InteractionComplete)

    def handle_event(self, sim_info, event, resolver, **kwargs):
        target_sim = resolver.interaction.target
        if target_sim is None or not target_sim.is_sim:
            return
        if target_sim.sim_info is not self._owner_sim_info:
            return
        template_affordance = resolver.interaction.interaction_parameters.get('template_affordance', None)
        if template_affordance is None:
            return
        if template_affordance in self._affordance_templates:
            del self._affordance_templates[template_affordance]
        self._find_and_remove_from_timed_list(template_affordance)

    def on_affordance_template_start(self, affordance_template):
        if affordance_template is None:
            logger.error('None affordance_template provided. Can not start tracking a None affordance template.')
            return
        self._find_and_remove_from_timed_list(affordance_template)
        self._affordance_templates[affordance_template] += 1

    def _find_and_remove_from_timed_list(self, affordance_template):
        remove_keys = set()
        for (key, affordance_template_list) in self._timed_affordance_templates.items():
            if affordance_template in affordance_template_list:
                affordance_template_list.remove(affordance_template)
                if not affordance_template_list:
                    remove_keys.add(key)
        for key in remove_keys:
            del self._timed_affordance_templates[key]

    def on_affordance_template_stop(self, affordance_template):
        if affordance_template is None:
            logger.error('None affordance_template provided. Can not stop tracking a None affordance template.')
            return
        self._affordance_templates[affordance_template] -= 1
        if self._affordance_templates[affordance_template] == 0:
            del self._affordance_templates[affordance_template]
            post_run_duration = affordance_template.post_run_duration if affordance_template.post_run_duration is not None else self.DEFAULT_POST_RUN_DURATION
            if post_run_duration > 0:
                expiration_time = services.time_service().sim_now + clock.interval_in_sim_minutes(post_run_duration)
                self._timed_affordance_templates[expiration_time].append(affordance_template)

    def _aops_from_template_gen(self, template, target, **kwargs):
        for affordance_template in template.template_affordances:
            affordance_kwargs = kwargs.copy()
            affordance_kwargs.update(affordance_template.get_template_kwargs())
            affordance_kwargs.update({'template_affordance': template})
            affordance = affordance_template.get_template_affordance()
            yield AffordanceObjectPair(affordance, target, affordance, None, **affordance_kwargs)

    def get_template_interactions_gen(self, context, **kwargs):
        if context.pick is None:
            return
        target = context.pick.target
        if target is None:
            return
        for template in self._affordance_templates:
            yield from self._aops_from_template_gen(template, target, **kwargs)
        expired_times = []
        now = services.time_service().sim_now
        for (expiration_time, templates) in self._timed_affordance_templates.items():
            if now > expiration_time:
                expired_times.append(expiration_time)
            else:
                for template in templates:
                    yield from self._aops_from_template_gen(template, target, **kwargs)
        for time in expired_times:
            del self._timed_affordance_templates[time]
