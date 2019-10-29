from careers.career_enums import GigResultfrom careers.career_gig import Gigfrom sims4.localization import TunableLocalizedStringFactoryfrom sims4.tuning.instances import lock_instance_tunablesfrom sims4.tuning.tunable import OptionalTunable, Tunable, TunablePercent, TunableTuplefrom ui.ui_dialog_picker import OddJobPickerRowimport randomimport sims.sim_info_testsimport sims4import statistics.skill_testsfrom date_and_time import TimeSpanlogger = sims4.log.Logger('RabbitholeGig', default_owner='madang')
class RabbitholeGig(Gig):
    INSTANCE_TUNABLES = {'negative_mood_tuning': TunableTuple(description='\n            Tuning for the negative mood test.  If the Sim has the any of the \n            negative mood buffs (the Buff test passes), the failure chance \n            tunable will be used to determine whether or not to apply the \n            FAILURE outcome.\n            ', negative_mood_test=sims.sim_info_tests.BuffTest.TunableFactory(), failure_chance=TunablePercent(description='\n                Chance of a FAILURE outcome if the negative mood test passes.\n                ', default=0.0)), 'recommended_skill_tuning': OptionalTunable(description="\n            Tuning for the (optional) recommended skill.  If the Sim has this\n            skill, the outcome will depend on the Sim's skill level relative \n            to the recommended skill level.\n            ", tunable=TunableTuple(recommended_skill_test=statistics.skill_tests.SkillRangeTest.TunableFactory(description='\n                    The recommended skill test for this gig.  For Home \n                    Assignment gigs, the skill range min and max should be the \n                    same.\n                    '), great_success_chance_multiplier=Tunable(description='\n                    The multiplier for determining the chance the Sim will\n                    receive the GREAT_SUCCESS outcome.\n                    ', tunable_type=float, default=0.0), failure_chance_multiplier=Tunable(description='\n                    The multiplier for determining the chance the Sim will\n                    receive the FAILURE outcome.\n                    ', tunable_type=float, default=0.0), critical_failure_skill_level_delta=Tunable(description='\n                    The difference in skill levels lower than the recommended\n                    skill level for a Sim to qualify for a CRITICAL FAILURE \n                    outcome.\n                    ', tunable_type=int, default=0))), 'gig_picker_localization_format': TunableLocalizedStringFactory(description='\n            String used to format the description in the gig picker. Currently\n            has tokens for name, payout, gig time, tip title, and tip text.\n            ')}

    @classmethod
    def _verify_tuning_callback(cls):
        if not cls.tip:
            logger.error('No tip tuned for Rabbithole Gig {}. Rabbithole Gigs must have a tip.', cls)

    def _determine_gig_outcome(self):
        if not self.has_attended_gig():
            self._gig_result = GigResult.CRITICAL_FAILURE
            return
        if self._gig_result == GigResult.CANCELED:
            self._gig_result = GigResult.FAILURE
            return
        resolver = self.get_resolver_for_gig()
        if resolver(self.negative_mood_tuning.negative_mood_test) and random.random() <= self.negative_mood_tuning.failure_chance:
            self._gig_result = GigResult.FAILURE
            return
        if self.recommended_skill_tuning:
            skill = self._owner.get_statistic(self.recommended_skill_tuning.recommended_skill_test.skill, add=False)
            sim_skill_level = 0
            if skill:
                sim_skill_level = skill.get_user_value()
            recommended_level = self.recommended_skill_tuning.recommended_skill_test.skill_range_max
            if sim_skill_level > recommended_level:
                chance = (sim_skill_level - recommended_level)*self.recommended_skill_tuning.great_success_chance_multiplier
                if random.random() <= chance:
                    self._gig_result = GigResult.GREAT_SUCCESS
                else:
                    self._gig_result = GigResult.SUCCESS
            elif sim_skill_level == recommended_level:
                self._gig_result = GigResult.SUCCESS
            else:
                skill_level_difference = recommended_level - sim_skill_level
                if skill_level_difference >= self.recommended_skill_tuning.critical_failure_skill_level_delta:
                    self._gig_result = GigResult.CRITICAL_FAILURE
                else:
                    chance = skill_level_difference*self.recommended_skill_tuning.failure_chance_multiplier
                    if random.random() <= chance:
                        self._gig_result = GigResult.FAILURE
                    else:
                        self._gig_result = GigResult.CRITICAL_FAILURE
        else:
            self._gig_result = GigResult.SUCCESS

    @classmethod
    def create_picker_row(cls, description=None, scheduled_time=None, owner=None, gig_customer=None, enabled=True, **kwargs):
        tip = cls.tip
        duration = TimeSpan.ONE
        finishing_time = None
        if scheduled_time is None:
            logger.error('Rabbit Hole Gig {} : Not a valid scheduled_time.', cls)
            return
        for (start_time, end_time) in cls.gig_time().get_schedule_entries():
            if scheduled_time.day() == start_time.day() and scheduled_time.hour() == start_time.hour() and scheduled_time.minute() == start_time.minute():
                duration = end_time - start_time
                finishing_time = scheduled_time + duration
                break
        if finishing_time == None:
            logger.error('Rabbit Hole Gig {} : No gig start_time found for scheduled_time {} ', cls, scheduled_time)
            return
        pay_rate = cls.gig_pay.lower_bound/duration.in_hours()
        description = cls.gig_picker_localization_format(cls.gig_pay.lower_bound, pay_rate, scheduled_time, finishing_time, tip.tip_title(), tip.tip_text(), gig_customer)
        if enabled or cls.disabled_tooltip is not None:
            row_tooltip = lambda *_: cls.disabled_tooltip(owner)
        elif cls.display_description is None:
            row_tooltip = None
        else:
            row_tooltip = lambda *_: cls.display_description(owner)
        customer_description = cls.odd_job_tuning.customer_description(gig_customer)
        row = OddJobPickerRow(customer_id=gig_customer.id, customer_description=customer_description, tip_title=tip.tip_title(), tip_text=tip.tip_text(), tip_icon=tip.tip_icon, name=cls.display_name(owner), icon=cls.display_icon, row_description=description, row_tooltip=row_tooltip, is_enable=enabled)
        return row
lock_instance_tunables(RabbitholeGig, gig_prep_tasks=None, audio_on_prep_task_completion=None, career_events=None, gig_cast_rel_bit_collection_id=None, gig_cast=None, end_of_gig_dialog=None, payout_stat_data=None)