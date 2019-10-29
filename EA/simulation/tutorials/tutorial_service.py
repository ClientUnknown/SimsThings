from alarms import add_alarmfrom drama_scheduler.drama_node_types import DramaNodeTypefrom event_testing.resolver import SingleSimResolverfrom tutorials.tutorial_tip import TutorialModefrom sims4.service_manager import Servicefrom sims4.tuning.tunable import OptionalTunable, TunableReference, TunableTuplefrom snippets import TunableAffordanceFilterSnippetimport servicesimport sims4.logimport sims4.localizationlogger = sims4.log.Logger('tutorial', default_owner='nabaker')
class TutorialService(Service):
    INTERACTION_DISABLED_TOOLTIP = sims4.localization.TunableLocalizedStringFactory(description='\n        Default Tooltip for disabled interactions.\n        ')
    TUTORIAL_DRAMA_NODE = TunableReference(description='\n        The drama node that controls the tutorial.\n        ', manager=services.get_instance_manager(sims4.resources.Types.DRAMA_NODE), class_restrictions=('TutorialDramaNode',))
    FALLBACK_RESTRICTED_AFFORDANCES = OptionalTunable(description='\n        If enabled, use this affordance restriction if we are in the tutorial \n        mode and somehow no restriction has currently been specified by a \n        tutorial tip.  (There should always be a restriction.)\n        ', tunable=TunableTuple(visible_affordances=TunableAffordanceFilterSnippet(description='\n                The filter of affordances that are visible.\n                '), tooltip=OptionalTunable(description='\n                Tooltip when interaction is disabled by tutorial restrictions\n                If not specified, will use the default in the tutorial service\n                tuning.\n                ', tunable=sims4.localization.TunableLocalizedStringFactory()), enabled_affordances=TunableAffordanceFilterSnippet(description='\n                The filter of visible affordances that are enabled.\n                ')))

    def __init__(self):
        self._visible_affordance_filter = None
        self._enabled_affordance_filter = None
        self._tooltip = None
        self._tutorial_alarms = {}
        self._unselectable_sim_id = None
        self._unselectable_sim_count = 0
        self._tutorial_mode = TutorialMode.STANDARD

    def add_tutorial_alarm(self, tip, callback, time_of_day):
        now = services.game_clock_service().now()
        time_till_satisfy = now.time_till_next_day_time(time_of_day)
        self._tutorial_alarms[tip] = add_alarm(self, time_till_satisfy, callback, cross_zone=True)

    def remove_tutorial_alarm(self, tip):
        del self._tutorial_alarms[tip]

    def is_affordance_visible(self, affordance):
        visible_filter = self._visible_affordance_filter
        if self.FALLBACK_RESTRICTED_AFFORDANCES:
            visible_filter = self.FALLBACK_RESTRICTED_AFFORDANCES.visible_affordances
        return visible_filter is None and self._tutorial_mode == TutorialMode.FTUE and visible_filter is None or visible_filter(affordance)

    def get_disabled_affordance_tooltip(self, affordance):
        enabled_filter = self._enabled_affordance_filter
        disabled_text = self._tooltip
        if enabled_filter is None and self._tutorial_mode == TutorialMode.FTUE:
            enabled_filter = self.FALLBACK_RESTRICTED_AFFORDANCES.enabled_affordances
            disabled_text = self.FALLBACK_RESTRICTED_AFFORDANCES.tooltip
            return
        if enabled_filter is None or enabled_filter(affordance):
            return
        if disabled_text is not None:
            return disabled_text
        return self.INTERACTION_DISABLED_TOOLTIP

    def clear_restricted_affordances(self):
        self._visible_affordance_filter = None
        self._enabled_affordance_filter = None
        self._tooltip = None

    def set_restricted_affordances(self, visible_filter, tooltip, enabled_filter):
        self._visible_affordance_filter = visible_filter
        self._enabled_affordance_filter = enabled_filter
        self._tooltip = tooltip

    def on_all_households_and_sim_infos_loaded(self, client):
        save_slot_data_msg = services.get_persistence_service().get_save_slot_proto_buff()
        if save_slot_data_msg.trigger_tutorial_drama_node:
            save_slot_data_msg.trigger_tutorial_drama_node = False
            drama_scheduler = services.drama_scheduler_service()
            if drama_scheduler is not None:
                resolver = SingleSimResolver(services.active_sim_info())
                drama_scheduler.run_node(self.TUTORIAL_DRAMA_NODE, resolver)
        self._tutorial_mode = save_slot_data_msg.tutorial_mode

    def set_tutorial_mode(self, mode):
        save_slot_data_msg = services.get_persistence_service().get_save_slot_proto_buff()
        save_slot_data_msg.tutorial_mode = mode
        self._tutorial_mode = mode
        if mode != TutorialMode.FTUE:
            drama_scheduler = services.drama_scheduler_service()
            if drama_scheduler is not None:
                drama_nodes = drama_scheduler.get_running_nodes_by_drama_node_type(DramaNodeType.TUTORIAL)
                if drama_nodes:
                    drama_nodes[0].end()

    def is_sim_unselectable(self, sim_info):
        return sim_info.sim_id == self._unselectable_sim_id

    def set_unselectable_sim(self, sim_info):
        if sim_info is None:
            sim_id = None
        else:
            sim_id = sim_info.sim_id
        if sim_id != self._unselectable_sim_id:
            if sim_id is None:
                self._unselectable_sim_count -= 1
                if self._unselectable_sim_count > 0:
                    return
            elif self._unselectable_sim_id is None:
                self._unselectable_sim_count = 1
            else:
                logger.error('Tutorial only supports one unselectable sim at a time.  Attempting to add:{}', sim_info)
                return
            self._unselectable_sim_id = sim_id
            client = services.client_manager().get_first_client()
            if client is not None:
                client.selectable_sims.notify_dirty()
                if sim_id is not None:
                    client.validate_selectable_sim()
        elif sim_id is not None:
            self._unselectable_sim_count += 1

    def is_tutorial_running(self):
        drama_scheduler = services.drama_scheduler_service()
        if drama_scheduler is None or not drama_scheduler.get_running_nodes_by_drama_node_type(DramaNodeType.TUTORIAL):
            return False
        return True
