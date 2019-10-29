from _weakrefset import WeakSetimport itertoolsimport randomfrom event_testing.resolver import SingleSimResolverfrom objects import ALL_HIDDEN_REASONSfrom sims.sim_info_lod import SimInfoLODLevelfrom sims4 import mathfrom sims4.random import weighted_random_indexfrom sims4.tuning.tunable import AutoFactoryInit, HasTunableSingletonFactory, OptionalTunable, TunableIntervalfrom story_progression.story_progression_action import _StoryProgressionFilterActionfrom tunable_multiplier import TunableMultiplierimport gsi_handlersimport services
class CareerStoryProgressionParameters(HasTunableSingletonFactory, AutoFactoryInit):
    FACTORY_TUNABLES = {'joining': OptionalTunable(description='\n            If enabled, Sims will be able to join this career via Story\n            Progression.\n            ', tunable=TunableMultiplier.TunableFactory(description='\n                The weight of a particular Sim joining this career versus all\n                other eligible Sims doing the same. A weight of zero prevents\n                the Sim from joining the career.\n                ')), 'retiring': OptionalTunable(description="\n            If enabled, Sims will be able to retire from this career via Story\n            Progression. This does not override the 'can_quit' flag on the\n            career tuning.\n            \n            Story Progression will attempt to have Sims retire before having\n            Sims quit.\n            ", tunable=TunableMultiplier.TunableFactory(description='\n                The weight of a particular Sim retiring from this career versus\n                all other eligible Sims doing the same. A weight of zero\n                prevents the Sim from retiring from the career.\n                ')), 'quitting': OptionalTunable(description="\n            If enabled, Sims will be able to quit this career via Story\n            Progression. This does not override the 'can_quit' flag on the\n            career tuning.\n            ", tunable=TunableMultiplier.TunableFactory(description='\n                The weight of a particular Sim quitting this career versus all\n                other eligible Sims doing the same. A weight of zero prevents\n                the Sim from quitting the career.\n                '))}

class StoryProgressionActionCareer(_StoryProgressionFilterAction):
    FACTORY_TUNABLES = {'employment_rate': TunableInterval(description='\n            The ideal employment rates. If the rate of employed Sims fall\n            outside this interval, Sims will be hired/fired as necessary.\n            ', tunable_type=float, default_lower=0.6, default_upper=0.9, minimum=0, maximum=1)}

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._employed = WeakSet()
        self._unemployed = WeakSet()
        self._workforce_count = 0

    def _allow_instanced_sims(self):
        return True

    def _is_valid_candidate(self, sim_info):
        if not sim_info.is_npc:
            return False
        if sim_info.lod == SimInfoLODLevel.MINIMUM:
            return False
        if sim_info.is_instanced(allow_hidden_flags=ALL_HIDDEN_REASONS):
            return False
        elif sim_info.career_tracker.currently_during_work_hours:
            return False
        return True

    def _apply_action(self, sim_info):
        if sim_info.career_tracker.has_quittable_career():
            self._employed.add(sim_info)
        elif not sim_info.career_tracker.has_work_career():
            self._unemployed.add(sim_info)
        self._workforce_count += 1

    def _post_apply_action(self):
        lower_bound = math.floor(self._workforce_count*self.employment_rate.lower_bound)
        upper_bound = math.ceil(self._workforce_count*self.employment_rate.upper_bound)
        num_employed = len(self._employed)
        if num_employed < lower_bound:
            self._try_employ_sim()
        elif num_employed > upper_bound:
            self._try_unemploy_sim()
        self._employed.clear()
        self._unemployed.clear()
        self._workforce_count = 0

    def _get_ideal_candidate_for_employment(self):

        def _get_weight(candidate, career):
            if not career.is_valid_career(sim_info=candidate):
                return 0
            if candidate.career_tracker.has_career_by_uid(career.guid64):
                return 0
            return career.career_story_progression.joining.get_multiplier(SingleSimResolver(candidate))

        career_service = services.get_career_service()
        weights = [(_get_weight(candidate, career), candidate, career) for (candidate, career) in itertools.product((candidate for candidate in self._unemployed if self._is_valid_candidate(candidate)), (career for career in career_service.get_career_list() if career.career_story_progression.joining is not None))]
        if not weights:
            return
        selected_candidate_index = weighted_random_index(weights)
        if selected_candidate_index is None:
            return
        selected_candidate = weights[selected_candidate_index]
        return (selected_candidate[1], selected_candidate[2])

    def _get_ideal_candidate_for_unemployment(self, get_unemployment_multiplier):

        def _get_weight(candidate, career):
            subaction_multiplier = get_unemployment_multiplier(career)
            return subaction_multiplier.get_multiplier(SingleSimResolver(candidate))

        weights = list(itertools.chain.from_iterable(((_get_weight(candidate, career), candidate, career) for career in candidate.career_tracker if career.can_quit and get_unemployment_multiplier(career) is not None) for candidate in self._employed if self._is_valid_candidate(candidate)))
        if not weights:
            return
        selected_candidate_index = weighted_random_index(weights)
        if selected_candidate_index is None:
            return
        selected_candidate = weights[selected_candidate_index]
        return (selected_candidate[1], selected_candidate[2])

    def _try_employ_sim(self):
        selected_candidate = self._get_ideal_candidate_for_employment()
        if selected_candidate is None:
            return False
        (sim_info, career_type) = selected_candidate
        max_user_level = career_type.get_max_user_level()
        user_level = random.randint(1, max_user_level)
        if gsi_handlers.story_progression_handlers.story_progression_archiver.enabled:
            gsi_handlers.story_progression_handlers.archive_story_progression(self, 'Add Career to {}: {} ({}/{})', sim_info, career_type, user_level, max_user_level)
        sim_info.career_tracker.add_career(career_type(sim_info), user_level_override=user_level, give_skipped_rewards=False)
        return True

    def _try_retire_sim(self):
        selected_candidate = self._get_ideal_candidate_for_unemployment(lambda career: career.career_story_progression.retiring)
        if selected_candidate is None:
            return False
        (sim_info, career_type) = selected_candidate
        if gsi_handlers.story_progression_handlers.story_progression_archiver.enabled:
            gsi_handlers.story_progression_handlers.archive_story_progression(self, 'Retiring {} from {}', sim_info, career_type)
        sim_info.career_tracker.retire_career(career_type.guid64)
        return True

    def _try_quit_sim(self):
        selected_candidate = self._get_ideal_candidate_for_unemployment(lambda career: career.career_story_progression.quitting)
        if selected_candidate is None:
            return False
        (sim_info, career_type) = selected_candidate
        if gsi_handlers.story_progression_handlers.story_progression_archiver.enabled:
            gsi_handlers.story_progression_handlers.archive_story_progression(self, 'Having {} quit from {}', sim_info, career_type)
        sim_info.career_tracker.quit_quittable_careers()
        return True

    def _try_unemploy_sim(self):
        if self._try_retire_sim():
            return True
        elif self._try_quit_sim():
            return True
        return False
