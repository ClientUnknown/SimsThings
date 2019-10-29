from event_testing.resolver import SingleSimResolverfrom event_testing.test_events import TestEventfrom open_street_director.festival_situations import BaseGenericFestivalSituationfrom sims4.tuning.instances import lock_instance_tunablesfrom sims4.tuning.tunable import TunableEnumEntry, TunableSet, TunableReference, TunableSimMinute, HasTunableFactory, TunablePackSafeReference, OptionalTunable, TunableIntervalfrom situations.bouncer.bouncer_types import BouncerExclusivityCategoryfrom situations.situation_complex import SituationState, CommonSituationState, SituationComplexCommon, SituationStateData, TunableSituationJobAndRoleStatefrom situations.situation_types import SituationCreationUIOptionfrom tag import Tagfrom ui.ui_dialog_notification import TunableUiDialogNotificationSnippetimport servicesimport sims4.resourcesLAMP_CONTEST_SCORE_DELTA = 'lamp_current_score_delta'LAMP_CONTEST_TNS_ALARM = 'Lamp_TNS_Alarm'
class LampContestVictoryState(CommonSituationState):
    FACTORY_TUNABLES = {'firework_tags': TunableSet(TunableEnumEntry(Tag, Tag.INVALID), description='\n                Tags that determine which fireworks to fire\n                '), 'firework_state': TunablePackSafeReference(description='\n            State value to apply to objects with the tuned tag to ignite the\n            fireworks.\n            ', manager=services.get_instance_manager(sims4.resources.Types.OBJECT_STATE), class_restrictions=('ObjectStateValue',))}

    def __init__(self, *args, firework_tags=None, firework_state=None, **kwargs):
        super().__init__(*args, **kwargs)
        self._firework_tags = firework_tags
        self._firework_state = firework_state

    def on_activate(self, reader=None):
        super().on_activate(reader)
        state_value = self._firework_state
        if state_value is not None:
            state = state_value.state
            for firework in services.object_manager().get_objects_with_tags_gen(*self._firework_tags):
                state_component = firework.state_component
                if state_component is not None:
                    state_component.set_state(state, state_value)

class LightWinVictoryState(LampContestVictoryState):
    pass

class DarkWinVictoryState(LampContestVictoryState):
    pass

class TieVictoryState(LampContestVictoryState):
    pass

class LampContestFestivalSituationState(SituationState, HasTunableFactory):
    FACTORY_TUNABLES = {'light_tags': TunableSet(TunableEnumEntry(Tag, Tag.INVALID), description='\n                light team scores points when a sim with light job completes an\n                interaction with one of these tags.\n                '), 'dark_tags': TunableSet(TunableEnumEntry(Tag, Tag.INVALID), description='\n                dark team scores points when a sim with dark completes an \n                interaction with one of these tags.\n                '), 'light_sim_job_and_default_role_state': TunableSituationJobAndRoleState(description='\n            The Situation Job and role state to put light Sims in. \n            '), 'dark_sim_job_and_default_role_state': TunableSituationJobAndRoleState(description='\n            The Situation Job and role state to put Dark Sims in.\n            '), 'light_ahead_notification': TunableUiDialogNotificationSnippet(description='\n            The notification that will periodically appear when light is ahead.\n            Argument is the score delta.\n            '), 'dark_ahead_notification': TunableUiDialogNotificationSnippet(description='\n            The notification that will periodically appear when dark is ahead.\n            Argument is the score delta.\n            '), 'tie_notification': TunableUiDialogNotificationSnippet(description='\n            The notification that will periodically appear when tied.\n            '), 'notification_interval': TunableSimMinute(description='\n            The interval between score update notifications\n            ', default=60, minimum=1), 'score_range': OptionalTunable(description='\n            If enabled, range that the score should stay between\n            ', tunable=TunableInterval(tunable_type=int, default_lower=-5, default_upper=5))}

    def __init__(self, *args, light_tags=None, dark_tags=None, light_sim_job_and_default_role_state=None, dark_sim_job_and_default_role_state=None, light_ahead_notification=None, dark_ahead_notification=None, tie_notification=None, notification_interval=None, score_range=None, **kwargs):
        super().__init__(*args, **kwargs)
        self._light_tags = light_tags
        self._dark_tags = dark_tags
        self._light_sim_job_and_default_role_state = light_sim_job_and_default_role_state
        self._dark_sim_job_and_default_role_state = dark_sim_job_and_default_role_state
        self._light_ahead_notification = light_ahead_notification
        self._dark_ahead_notification = dark_ahead_notification
        self._tie_notification = tie_notification
        self._notification_interval = notification_interval
        self.current_score_delta = 0
        self.score_range = score_range

    def on_activate(self, reader=None):
        super().on_activate(reader)
        self._set_job_role_state()
        if reader is not None:
            self.current_score_delta = reader.read_int64(LAMP_CONTEST_SCORE_DELTA, 0)
        self._create_or_load_alarm(LAMP_CONTEST_TNS_ALARM, self._notification_interval, lambda _: self._score_tns(), reader=reader)
        for tag in self._light_tags:
            self._test_event_register(TestEvent.InteractionComplete, tag)
        for tag in self._dark_tags:
            self._test_event_register(TestEvent.InteractionComplete, tag)

    def save(self, writer):
        super().save(writer)
        writer.write_int64(LAMP_CONTEST_SCORE_DELTA, self.current_score_delta)

    def handle_event(self, sim_info, event, resolver):
        interaction = resolver.interaction
        if sim_info is interaction.sim.sim_info:
            if self.owner.sim_has_job(interaction.sim, self._light_sim_job_and_default_role_state.job):
                self.current_score_delta += 1
            if self.owner.sim_has_job(interaction.sim, self._dark_sim_job_and_default_role_state.job):
                self.current_score_delta -= 1
            if self._light_tags & interaction.get_category_tags() and self._dark_tags & interaction.get_category_tags() and self.score_range is not None:
                self.current_score_delta = sims4.math.clamp(self.score_range.lower_bound, self.current_score_delta, self.score_range.upper_bound)

    def _score_tns(self):
        self._create_or_load_alarm(LAMP_CONTEST_TNS_ALARM, self._notification_interval, lambda _: self._score_tns())
        for sim in self.owner.all_sims_in_situation_gen():
            if sim.sim_info.is_selectable:
                delta = self.current_score_delta
                if delta > 0:
                    update_notification = self._light_ahead_notification(services.active_sim_info())
                    update_notification.show_dialog(additional_tokens=(delta,))
                    return
                if delta < 0:
                    update_notification = self._dark_ahead_notification(services.active_sim_info())
                    update_notification.show_dialog(additional_tokens=(-delta,))
                    return
                update_notification = self._tie_notification(services.active_sim_info())
                update_notification.show_dialog()
                return

    def _set_job_role_state(self):
        self.owner._set_job_role_state(self._light_sim_job_and_default_role_state.job, self._light_sim_job_and_default_role_state.role_state)
        self.owner._set_job_role_state(self._dark_sim_job_and_default_role_state.job, self._dark_sim_job_and_default_role_state.role_state)

class LampContestFestivalSituation(BaseGenericFestivalSituation):
    INSTANCE_TUNABLES = {'_contest_state': LampContestFestivalSituationState.TunableFactory(description='\n            The first state that the Sims will be put into when this Situation\n            Starts.\n            ', tuning_group=SituationComplexCommon.SITUATION_STATE_GROUP), '_light_win_state': LightWinVictoryState.TunableFactory(description='\n            The state that the Situation will go into when the festival open\n            street director notifies it that the festival is going into\n            cooldown and light wins.\n            ', locked_args={'allow_join_situation': False, 'time_out': None}, tuning_group=SituationComplexCommon.SITUATION_STATE_GROUP), '_dark_win_state': DarkWinVictoryState.TunableFactory(description='\n            The state that the Situation will go into when the festival open\n            street director notifies it that the festival is going into\n            cooldown and dark wins.\n            ', locked_args={'allow_join_situation': False, 'time_out': None}, tuning_group=SituationComplexCommon.SITUATION_STATE_GROUP), '_tie_state': TieVictoryState.TunableFactory(description='\n            The state that the Situation will go into when the festival open\n            street director notifies it that the festival is going into\n            cooldown, and the score is a tie.\n            ', locked_args={'allow_join_situation': False, 'time_out': None}, tuning_group=SituationComplexCommon.SITUATION_STATE_GROUP), '_start_notification': TunableUiDialogNotificationSnippet(description='\n            The notification that will appear at the start of this situation.\n            '), '_light_win_end_notification': TunableUiDialogNotificationSnippet(description='\n            The notification that will appear at the end of this situation if light wins.\n            '), '_dark_win_end_notification': TunableUiDialogNotificationSnippet(description='\n            The notification that will appear at the end of this situation if dark wins.\n            '), '_tie_end_notification': TunableUiDialogNotificationSnippet(description='\n            The notification that will appear at the end of this situation if a tie.\n            '), '_light_win_rewards': TunableReference(description='\n            A reference to a loot that will be applied to winning teams.\n            ', manager=services.get_instance_manager(sims4.resources.Types.ACTION), class_restrictions=('LootActions',)), '_dark_win_rewards': TunableReference(description='\n            A reference to a loot that will be applied to winning teams.\n            ', manager=services.get_instance_manager(sims4.resources.Types.ACTION), class_restrictions=('LootActions',)), '_tie_rewards': TunableReference(description='\n            A reference to a loot that will be applied to tied teams.\n            ', manager=services.get_instance_manager(sims4.resources.Types.ACTION), class_restrictions=('LootActions',))}
    REMOVE_INSTANCE_TUNABLES = ('cooldown_state',)

    @classmethod
    def _states(cls):
        return (SituationStateData(1, LampContestFestivalSituationState, factory=cls._contest_state), SituationStateData(2, LightWinVictoryState, factory=cls._light_win_state), SituationStateData(3, DarkWinVictoryState, factory=cls._dark_win_state), SituationStateData(4, TieVictoryState, factory=cls._tie_state))

    @classmethod
    def _get_tuned_job_and_default_role_state_tuples(cls):
        return [(cls._contest_state._tuned_values.light_sim_job_and_default_role_state.job, cls._contest_state._tuned_values.light_sim_job_and_default_role_state.role_state), (cls._contest_state._tuned_values.dark_sim_job_and_default_role_state.job, cls._contest_state._tuned_values.dark_sim_job_and_default_role_state.role_state)]

    def start_situation(self):
        start_notification = self._start_notification(services.active_sim_info())
        start_notification.show_dialog()
        super().start_situation()
        self._change_state(self._contest_state())

    def put_on_cooldown(self):
        delta = self._cur_state.current_score_delta
        if delta > 0:
            end_notification = self._light_win_end_notification(services.active_sim_info())
            end_notification.show_dialog()
            for sim in self.all_sims_in_situation_gen():
                if sim.sim_info.is_selectable and self.sim_has_job(sim, self._cur_state._light_sim_job_and_default_role_state.job):
                    resolver = SingleSimResolver(sim.sim_info)
                    self._light_win_rewards.apply_to_resolver(resolver)
            self._change_state(self._light_win_state())
        elif delta < 0:
            end_notification = self._dark_win_end_notification(services.active_sim_info())
            end_notification.show_dialog()
            for sim in self.all_sims_in_situation_gen():
                if sim.sim_info.is_selectable and self.sim_has_job(sim, self._cur_state._dark_sim_job_and_default_role_state.job):
                    resolver = SingleSimResolver(sim.sim_info)
                    self._dark_win_rewards.apply_to_resolver(resolver)
            self._change_state(self._dark_win_state())
        else:
            end_notification = self._tie_end_notification(services.active_sim_info())
            end_notification.show_dialog()
            for sim in self.all_sims_in_situation_gen():
                if sim.sim_info.is_selectable:
                    resolver = SingleSimResolver(sim.sim_info)
                    self._tie_rewards.apply_to_resolver(resolver)
            self._change_state(self._tie_state())

    def score(self):
        if self._state_to_uid(self._cur_state) == 1:
            return self._cur_state.current_score_delta
        return 0
lock_instance_tunables(LampContestFestivalSituation, exclusivity=BouncerExclusivityCategory.VENUE_BACKGROUND, creation_ui_option=SituationCreationUIOption.NOT_AVAILABLE, duration=0, _implies_greeted_status=False)