import randomfrom sims4.localization import TunableLocalizedStringFactoryimport sims4.logimport sims4.telemetryfrom clock import interval_in_sim_daysfrom date_and_time import TimeSpan, create_time_spanfrom distributor.ops import SetAgeProgressfrom distributor.system import Distributorfrom element_utils import build_elementfrom event_testing.resolver import SingleSimResolverfrom event_testing.test_events import TestEventfrom interactions.context import InteractionContextfrom interactions.priority import Priorityfrom interactions.utils.death import DeathTypefrom objects import ALL_HIDDEN_REASONSfrom sims.aging.aging_statistic import AgeProgressContinuousStatisticfrom sims.aging.aging_tuning import AgeSpeeds, AgingTuningfrom sims.baby.baby_aging import baby_age_upfrom sims.sim_info_lod import SimInfoLODLevelfrom sims.sim_info_types import Agefrom statistics.life_skill_statistic import LifeSkillStatisticfrom traits.trait_quirks import add_quirksimport alarmsimport distributor.fieldsimport distributor.opsimport servicesimport telemetry_helperlogger = sims4.log.Logger('Aging')TELEMETRY_CHANGE_AGE = 'AGES'writer_age = sims4.telemetry.TelemetryWriter(TELEMETRY_CHANGE_AGE)
class AgingMixin:
    AGE_PROGRESS_BAR_FACTOR = 100
    FILL_AGE_PROGRESS_BAR_BUFFER = 0.0001

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._age_progress = AgeProgressContinuousStatistic(None, 0.0)
        self._age_progress.decay_enabled = True
        self._auto_aging_enabled = True
        self._age_speed_setting = AgeSpeeds.NORMAL
        self._almost_can_age_handle = None
        self._can_age_handle = None
        self._auto_age_handle = None
        self._age_time = 1
        self._time_alive = TimeSpan.ZERO
        self._last_time_time_alive_updated = None
        self._age_suppression_alarm_handle = None

    @property
    def is_child(self):
        return self.age == Age.CHILD

    @property
    def is_child_or_older(self):
        return self.age >= Age.CHILD

    @property
    def is_child_or_younger(self):
        return self.age <= Age.CHILD

    @property
    def is_teen(self):
        return self.age == Age.TEEN

    @property
    def is_teen_or_older(self):
        return self.age >= Age.TEEN

    @property
    def is_teen_or_younger(self):
        return self.age <= Age.TEEN

    @property
    def is_young_adult(self):
        return self.age == Age.YOUNGADULT

    @property
    def is_young_adult_or_older(self):
        return self.age >= Age.YOUNGADULT

    @property
    def is_adult(self):
        return self.age == Age.ADULT

    @property
    def is_elder(self):
        return self.age == Age.ELDER

    @property
    def is_toddler(self):
        return self.age == Age.TODDLER

    @property
    def is_toddler_or_younger(self):
        return self.age <= Age.TODDLER

    @property
    def age_progress(self):
        return self._age_progress.get_value()

    @age_progress.setter
    def age_progress(self, value):
        self._age_progress.set_value(value)

    @property
    def age_progress_in_days(self):
        (progress, _) = self._age_progress_data
        return progress

    @distributor.fields.Field(op=distributor.ops.SetAgeProgress)
    def _age_progress_data(self):
        tooltip = self._get_aging_disabled_tooltip()
        progress = int(self.age_progress/self._age_time*self.AGE_PROGRESS_BAR_FACTOR)
        return (progress, tooltip)

    resend_age_progress_data = _age_progress_data.get_resend()

    def _get_aging_disabled_tooltip(self):
        for trait in self.trait_tracker.equipped_traits:
            if trait.disable_aging is not None and not trait.can_age_up(self.age):
                if trait.disable_aging.tooltip is not None:
                    return trait.disable_aging.tooltip()
                return

    def get_aging_data(self):
        aging_data = AgingTuning.AGING_DATA[self.species]
        return aging_data

    def get_age_transition_data(self, age):
        aging_data = self.get_aging_data()
        return aging_data.get_age_transition_data(age)

    def get_birth_age(self):
        aging_data = self.get_aging_data()
        return aging_data.get_birth_age()

    def get_next_age(self, age):
        aging_data = self.get_aging_data()
        return aging_data.get_next_age(age)

    def get_previous_age(self, age):
        aging_data = self.get_aging_data()
        return aging_data.get_previous_age(age)

    def _create_fake_total_time_alive(self):
        aging_service = services.get_aging_service()
        age = self.get_birth_age()
        time_alive = TimeSpan.ZERO
        while age < self.age:
            age_transition_data = self.get_age_transition_data(age)
            time_alive += interval_in_sim_days(age_transition_data.get_age_duration(self))
            age = self.get_next_age(age)
        setting_multiplier = aging_service.get_speed_multiple(self._age_speed_setting)
        time_alive /= setting_multiplier
        return time_alive

    def load_time_alive(self, loaded_time):
        if loaded_time is None:
            loaded_time = self._create_fake_total_time_alive()
        self._time_alive = loaded_time
        self._last_time_time_alive_updated = services.time_service().sim_now

    def update_time_alive(self):
        if self._last_time_time_alive_updated is None:
            logger.error('Trying to update time live before initial value has been set.', owner='jjacobson')
            return
        current_time = services.time_service().sim_now
        if current_time < self._last_time_time_alive_updated:
            logger.error('Time alive going backward for {}. time_alive: {}, last time time alive updated: {}, current time: {}', self, self._time_alive, self._last_time_time_alive_updated, current_time, owner='tingyul')
            return
        time_since_last_update = current_time - self._last_time_time_alive_updated
        self._time_alive += time_since_last_update
        self._last_time_time_alive_updated = current_time

    def advance_age_phase(self):
        if self.age == Age.ELDER:
            bonus_days = self._get_bonus_days()
        else:
            bonus_days = 0
        age_transition_data = self.get_age_transition_data(self.age)
        age_time = age_transition_data.get_age_duration(self)
        warn_time = age_time - age_transition_data.age_transition_warning
        auto_age_time = age_time + age_transition_data.age_transition_delay + bonus_days
        age_progress = self._age_progress.get_value()
        if age_progress <= warn_time:
            age_progress = warn_time
        elif age_progress <= age_time:
            age_progress = age_time
        else:
            age_progress = auto_age_time
        self._age_progress.set_value(age_progress - self.FILL_AGE_PROGRESS_BAR_BUFFER)
        self.update_age_callbacks()

    def _set_age_progress(self, new_age_value):
        self._age_progress.set_value(new_age_value)
        self.send_age_progress_bar_update()
        self.resend_age()
        self.update_age_callbacks()

    def decrement_age_progress(self, days):
        delta_age = self._age_progress.get_value() - days
        new_age_value = max(delta_age, 0)
        self._set_age_progress(new_age_value)

    def increment_age_progress(self, days):
        delta_age = self._age_progress.get_value() + days
        new_age_value = min(delta_age, self._age_time)
        self._set_age_progress(new_age_value - self.FILL_AGE_PROGRESS_BAR_BUFFER)

    def reset_age_progress(self):
        self._set_age_progress(self._age_progress.min_value)

    def fill_age_progress(self):
        self._set_age_progress(self._age_time - self.FILL_AGE_PROGRESS_BAR_BUFFER)

    def _days_until_ready_to_age(self):
        aging_service = services.get_aging_service()
        setting_multiplier = aging_service.get_speed_multiple(self._age_speed_setting)
        return (self._age_time - self._age_progress.get_value())/setting_multiplier

    def get_randomized_progress(self, age_progress):
        age_transition_data = self.get_age_transition_data(self.age)
        return age_transition_data.get_randomized_progress(self, age_progress)

    def update_age_callbacks(self):
        age_transition_data = self.get_age_transition_data(self.age)
        if self._is_aging_disabled():
            self._age_time = age_transition_data.get_age_duration(self)
            self._age_progress.decay_enabled = False
            if self._almost_can_age_handle is not None:
                alarms.cancel_alarm(self._almost_can_age_handle)
                self._almost_can_age_handle = None
            if self._can_age_handle is not None:
                alarms.cancel_alarm(self._can_age_handle)
                self._can_age_handle = None
            if self._auto_age_handle is not None:
                alarms.cancel_alarm(self._auto_age_handle)
                self._auto_age_handle = None
            return
        self._update_age_trait(self._base.age)
        self._age_time = age_transition_data.get_age_duration(self)
        self._age_progress.decay_enabled = True
        if self.is_elder:
            bonus_days = self._get_bonus_days()
        else:
            bonus_days = 0
        aging_service = services.get_aging_service()
        setting_multiplier = aging_service.get_speed_multiple(self._age_speed_setting)
        self._age_progress.set_modifier(setting_multiplier)
        age_time = self._days_until_ready_to_age()
        warn_time = age_time - age_transition_data.age_transition_warning/setting_multiplier
        auto_age_time = age_time + (age_transition_data.age_transition_delay + bonus_days)/setting_multiplier
        if self._almost_can_age_handle is not None:
            alarms.cancel_alarm(self._almost_can_age_handle)
        if warn_time >= 0:
            self._almost_can_age_handle = alarms.add_alarm(self, create_time_span(days=warn_time), self.callback_almost_ready_to_age, cross_zone=True)
        if self._can_age_handle is not None:
            alarms.cancel_alarm(self._can_age_handle)
        if age_time >= 0:
            self._can_age_handle = alarms.add_alarm(self, create_time_span(days=age_time), self.callback_ready_to_age, cross_zone=True)
        self._create_auto_age_callback(delay=max(0, auto_age_time))
        self.send_age_progress()

    def send_age_progress(self):
        if self.is_selectable:
            self.send_age_progress_bar_update()

    def _create_auto_age_callback(self, delay=1):
        if self._auto_age_handle is not None:
            alarms.cancel_alarm(self._auto_age_handle)
        time_span_until_age_up = create_time_span(days=delay)
        if time_span_until_age_up.in_ticks() <= 0:
            time_span_until_age_up = create_time_span(minutes=1)
        self._auto_age_handle = alarms.add_alarm(self, time_span_until_age_up, self.callback_auto_age, cross_zone=True)

    def add_bonus_days(self, number_of_days):
        self._additional_bonus_days += number_of_days

    def _get_bonus_days(self):
        aging_data = self.get_aging_data()
        bonus_days = aging_data.get_lifetime_bonus(self)
        bonus_days += self._additional_bonus_days
        return bonus_days

    def _update_age_trait(self, next_age, current_age=None):
        trait_tracker = self.trait_tracker
        if current_age is not None:
            age_transition_data = self.get_age_transition_data(current_age)
            if trait_tracker.has_trait(age_transition_data.age_trait):
                self.remove_trait(age_transition_data.age_trait)
        age_transition_data = self.get_age_transition_data(next_age)
        if not trait_tracker.has_trait(age_transition_data.age_trait):
            self.add_trait(age_transition_data.age_trait)

    def _show_age_notification(self, notification_name):
        if self.is_npc:
            return
        if self._is_aging_disabled():
            return
        age_transition_data = self.get_age_transition_data(self.age)
        notification = getattr(age_transition_data, notification_name)
        if notification is None:
            return
        dialog = notification(self, SingleSimResolver(self))
        dialog.show_dialog(additional_tokens=(self,))

    def callback_ready_to_age(self, *_, **__):
        logger.info('READY TO AGE: {}', self.full_name)
        self._show_age_notification('age_up_available_notification')
        services.get_event_manager().process_event(TestEvent.ReadyToAge, sim_info=self)

    def callback_almost_ready_to_age(self, *_, **__):
        logger.info('ALMOST READY TO AGE: {}', self.full_name)
        self._show_age_notification('age_up_warning_notification')

    def callback_auto_age(self, *_, **__):
        if self._is_aging_disabled():
            self._create_auto_age_callback()
        else:
            self.age_moment()

    def age_moment(self):
        logger.info('AGE UP COMPLETE BY AUTOAGING: {}', self.full_name)
        if self.is_baby:
            self._age_up_baby()
        elif self.is_elder:
            self._age_up_elder()
        else:
            self._age_up_pctya()

    def _age_up_baby(self):
        baby = services.object_manager().get(self.sim_id)
        if baby is not None:
            baby_age_up(self)
        elif self.is_npc:
            self.advance_age()

    def _age_up_pctya(self):
        sim_instance = self.get_sim_instance(allow_hidden_flags=ALL_HIDDEN_REASONS)
        if sim_instance is not None:
            aging_data = self.get_aging_data()
            context = InteractionContext(sim_instance, InteractionContext.SOURCE_SCRIPT, Priority.Critical)
            result = sim_instance.push_super_affordance(aging_data.age_up_interaction, None, context)
            if not result:
                self._create_auto_age_callback()
                return
        elif self.is_npc:
            self.advance_age()

    def _age_up_elder(self):
        aging_data = self.get_aging_data()
        sim_instance = self.get_sim_instance(allow_hidden_flags=ALL_HIDDEN_REASONS)
        if sim_instance is not None:
            context = InteractionContext(sim_instance, InteractionContext.SOURCE_SCRIPT, Priority.Critical)
            if not sim_instance.push_super_affordance(aging_data.old_age_interaction, None, context):
                self._create_auto_age_callback()
        elif self.is_npc:
            household = self.household
            old_age_interaction = aging_data.old_age_interaction
            if old_age_interaction is not None and hasattr(old_age_interaction, 'death_type'):
                death_type = old_age_interaction.death_type
            else:
                death_type = aging_data.old_age_npc_death_type_fallback
            self.death_tracker.set_death_type(death_type, is_off_lot_death=True)
            household.handle_adultless_household()

    def set_aging_speed(self, speed:int):
        if speed is None or speed < 0 or speed > 2:
            logger.warn('Trying to set aging speed on a sim with an invalid speed: {}. Speed can only be 0, 1, or 2.', speed)
        self._age_speed_setting = AgeSpeeds(speed)
        self.update_age_callbacks()

    def set_aging_enabled(self, enabled:bool, update_callbacks=True):
        self._auto_aging_enabled = enabled
        if update_callbacks:
            self.update_age_callbacks()

    def advance_age_progress(self, days:float) -> None:
        self._age_progress.set_value(self._age_progress.get_value() + days)

    def _is_aging_disabled_common(self):
        if self.lod == SimInfoLODLevel.MINIMUM:
            return True
        current_age = self._base.age
        if any(not trait.can_age_up(current_age) for trait in self.trait_tracker):
            return True
        elif self._age_suppression_alarm_handle is not None:
            return True
        return False

    def _is_aging_disabled(self):
        if not self._auto_aging_enabled:
            return True
        if self._is_aging_disabled_common():
            return True
        elif self.is_elder and self.is_death_disabled():
            return True
        return False

    def is_death_disabled(self):
        return any(not trait.can_die for trait in self.trait_tracker)

    def can_age_up(self) -> bool:
        if self.is_elder:
            return False
        elif self._is_aging_disabled_common():
            return False
        return True

    @property
    def time_until_age_up(self):
        return self._age_time - self._age_progress.get_value()

    def update_skills_for_aging(self):
        for skill in self.all_skills():
            if skill.age_up_skill_transition_data is not None and skill.age_up_skill_transition_data.new_skill is not None:
                user_value = skill.get_user_value()
                if user_value > 0:
                    new_skill_value = skill.age_up_skill_transition_data.skill_data[user_value]
                    if skill.age_up_skill_transition_data.new_skill is not None:
                        self.commodity_tracker.set_value(skill.age_up_skill_transition_data.new_skill, new_skill_value)
            if not skill.can_add(self):
                self.remove_statistic(skill.stat_type)

    def change_age(self, new_age, current_age):
        self.age_progress = 0
        self.apply_age(new_age)
        self.appearance_tracker.evaluate_appearance_modifiers()
        self.resend_physical_attributes()
        self._update_age_trait(new_age, current_age)
        self.career_tracker.add_ageup_careers()
        self.career_tracker.remove_invalid_careers()
        self.trait_tracker.remove_invalid_traits()
        if self.aspiration_tracker is not None:
            self.aspiration_tracker.remove_invalid_aspirations()
        self.update_skills_for_aging()
        add_quirks(self)
        sim_instance = self.get_sim_instance(allow_hidden_flags=ALL_HIDDEN_REASONS)
        if sim_instance is not None:
            with telemetry_helper.begin_hook(writer_age, TELEMETRY_CHANGE_AGE, sim=sim_instance) as hook:
                hook.write_enum('agef', current_age)
                hook.write_enum('aget', new_age)
            sim_instance.schedule_element(services.time_service().sim_timeline, build_element(sim_instance._update_face_and_posture_gen))
            sim_instance._update_multi_motive_buff_trackers()
            sim_instance.update_portal_locks()
        self.reset_age_progress()
        if self.is_npc or self.whim_tracker is not None:
            self.whim_tracker.validate_goals()
        client = services.client_manager().get_client_by_household_id(self._household_id)
        if client is None:
            return
        client.selectable_sims.notify_dirty()

    def can_reverse_age(self):
        prev_age = self.get_previous_age(self.age)
        return prev_age is not None and prev_age != Age.BABY

    def reverse_age(self):
        current_age = self.age
        prev_age = self.get_previous_age(current_age)
        self.change_age(prev_age, current_age)

    def advance_age(self):
        current_age = self.age
        next_age = self.get_next_age(current_age)
        self._relationship_tracker.update_bits_on_age_up(current_age)
        self.change_age(next_age, current_age)
        services.get_event_manager().process_event(TestEvent.AgedUp, sim_info=self)
        school_data = self.get_school_data()
        if school_data is not None:
            school_data.update_school_data(self, create_homework=True)
        if self.is_npc:
            if self.is_child or self.is_teen:
                available_aspirations = []
                aspiration_track_manager = services.get_instance_manager(sims4.resources.Types.ASPIRATION_TRACK)
                aspiration_tracker = self.aspiration_tracker
                for aspiration_track in aspiration_track_manager.types.values():
                    track_available = not aspiration_track.is_hidden_unlockable
                    if aspiration_tracker is not None:
                        track_available = aspiration_tracker.is_aspiration_track_visible(aspiration_track)
                    if track_available or track_available:
                        if aspiration_track.is_child_aspiration_track:
                            if self.is_child:
                                available_aspirations.append(aspiration_track)
                                if self.is_teen:
                                    available_aspirations.append(aspiration_track)
                        elif self.is_teen:
                            available_aspirations.append(aspiration_track)
                self.primary_aspiration = random.choice(available_aspirations)
            trait_tracker = self.trait_tracker
            empty_trait_slots = trait_tracker.empty_slot_number
            if empty_trait_slots:
                available_traits = [trait for trait in services.trait_manager().types.values() if trait.is_personality_trait]
                while empty_trait_slots > 0 and available_traits:
                    trait = random.choice(available_traits)
                    available_traits.remove(trait)
                    if not trait_tracker.can_add_trait(trait):
                        pass
                    elif self.add_trait(trait):
                        empty_trait_slots -= 1
        age_transition = self.get_age_transition_data(next_age)
        age_transition.apply_aging_transition_loot(self)
        self._create_additional_statistics()
        life_skills_trait_gained = self._apply_life_skill_traits()
        return life_skills_trait_gained

    def _apply_life_skill_traits(self):
        age = self.age
        stats_to_remove = []
        traits_to_add = []
        for statistic in self.commodity_tracker:
            if not isinstance(statistic, LifeSkillStatistic):
                pass
            else:
                statistic_value = statistic.get_value()
                for range_info in statistic.trait_on_age_up_list:
                    age_up_info = range_info.age_up_info
                    if age_up_info is not None and age_up_info.age_to_apply_trait == age and statistic_value in range_info.life_skill_range:
                        traits_to_add.append(range_info.age_up_info.life_skill_trait)
                if age == statistic.age_to_remove_stat:
                    statistic.create_and_send_life_skill_delete_msg()
                    stats_to_remove.append(statistic.stat_type)
        traits_to_return = []
        for trait in traits_to_add:
            is_successful = self.add_trait(trait)
            if is_successful:
                traits_to_return.append(trait.guid64)
            else:
                logger.error('Failed to add life skill trait when aging up. Check logger info for reason. ')
        for stat_to_remove in stats_to_remove:
            self.commodity_tracker.remove_statistic(stat_to_remove)
        return traits_to_return

    def _suppress_aging_callback(self, _):
        self._age_suppression_alarm_handle = None

    def suppress_aging(self):
        if self._age_suppression_alarm_handle is not None:
            logger.warn("Trying to suppress aging when aging is already suppressed. You probably don't want to do be doing this.", owner='jjacobson')
        self._age_suppression_alarm_handle = alarms.add_alarm(self, create_time_span(minutes=AgingTuning.AGE_SUPPRESSION_ALARM_TIME), self._suppress_aging_callback, cross_zone=True)

    def is_birthday(self):
        return self._days_until_ready_to_age() <= 0
