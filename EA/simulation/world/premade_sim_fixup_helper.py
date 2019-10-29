from _collections import defaultdictfrom sims.pregnancy.pregnancy_tracker import PregnancyTrackerfrom sims.sim_info_base_wrapper import SimInfoBaseWrapperfrom world.premade_sim_relationships import PremadeSimRelationshipsimport servicesimport sims4.resourceslogger = sims4.log.Logger('PremadeSimManager', default_owner='tingyul')
class PremadeSimFixupHelper:

    def __init__(self):
        self._premade_sim_infos = {}

    def fix_up_premade_sims(self):
        for sim_info in services.sim_info_manager().values():
            if not sim_info.premade_sim_template_id:
                pass
            else:
                sim_template = self._get_sim_template_from_id(sim_info.premade_sim_template_id)
                self._premade_sim_infos[sim_template] = sim_info
                sim_info.premade_sim_template_id = 0
        if not self._premade_sim_infos:
            return
        self._apply_household_fixup()
        PremadeSimRelationships.apply_relationships(self._premade_sim_infos)
        self._apply_clubs()
        self._apply_careers()
        self._apply_pregnancy()
        self._apply_occult()
        self._apply_template_data()
        self._apply_aspiration()

    def _get_sim_template_from_id(self, template_id):
        template_manager = services.get_instance_manager(sims4.resources.Types.SIM_TEMPLATE)
        sim_template = template_manager.get(template_id)
        return sim_template

    def _apply_household_fixup(self):
        households = {sim_info.household for sim_info in self._premade_sim_infos.values()}
        sim_info_to_template = {sim_info: template for (template, sim_info) in self._premade_sim_infos.items()}
        for household in households:
            household_templates = {sim_info_to_template[sim_info].household_template for sim_info in household if sim_info in sim_info_to_template}
            if None in household_templates or len(household_templates) != 1:
                logger.error('Premade Household {} has members in different PremadeHouseholdTemplates: {}', household, household_templates)
            else:
                household_template = next(iter(household_templates))
                household_template.apply_fixup_to_household(household, self._premade_sim_infos)

    def _apply_clubs(self):

        class PremadeClubInfo:

            def __init__(self):
                self.leader = None
                self.members = []

        clubs = defaultdict(PremadeClubInfo)
        for (premade_sim_template, sim_info) in self._premade_sim_infos.items():
            for club_info in premade_sim_template.clubs:
                clubs[club_info.seed].members.append(sim_info)
                if club_info.leader:
                    if clubs[club_info.seed].leader is not None:
                        logger.error('Club {} has multiple leaders: {}, {}', club_info.seed, sim_info, clubs[club_info.seed].leader)
                    clubs[club_info.seed].leader = sim_info
        if not clubs:
            return
        club_service = services.get_club_service()
        with club_service.defer_club_distribution():
            for (club_seed, info) in clubs.items():
                club_seed.create_club(leader=info.leader, members=info.members, refresh_cache=False)
        club_service.update_affordance_cache()

    def _apply_careers(self):
        for (premade_sim_template, sim_info) in self._premade_sim_infos.items():
            career_level = premade_sim_template.career_level
            if career_level is not None:
                career_type = career_level.career
                if not career_type.is_valid_career(sim_info=sim_info, from_join=True):
                    pass
                else:
                    career = career_type(sim_info)
                    sim_info.career_tracker.add_career(career, career_level_override=career_level, give_skipped_rewards=False, defer_rewards=True)
                    sim_info.update_school_data()
            sim_info.update_school_data()

    def _apply_pregnancy(self):
        for (premade_sim_template, sim_info) in self._premade_sim_infos.items():
            pregnancy_tuning = premade_sim_template.pregnancy
            if pregnancy_tuning is None:
                pass
            else:
                other_parent = self._premade_sim_infos.get(pregnancy_tuning.other_parent, None)
                if other_parent is None:
                    logger.error('Could not find sim info for other parent {}', pregnancy_tuning.other_parent)
                else:
                    sim_info.pregnancy_tracker.start_pregnancy(sim_info, other_parent, pregnancy_origin=pregnancy_tuning.origin)
                    sim_info.set_stat_value(PregnancyTracker.PREGNANCY_COMMODITY_MAP.get(sim_info.species), pregnancy_tuning.progress*100)

    def _apply_occult(self):
        for (premade_sim_template, sim_info) in self._premade_sim_infos.items():
            occult_tuning = premade_sim_template.occult
            if occult_tuning is None:
                pass
            else:
                sim_info_wrapper = SimInfoBaseWrapper(gender=sim_info.gender, age=sim_info.age, species=sim_info.species, first_name=sim_info.first_name, last_name=sim_info.last_name, breed_name=sim_info.breed_name, full_name_key=sim_info.full_name_key, breed_name_key=sim_info.breed_name_key)
                sim_info_wrapper.load_from_resource(occult_tuning.occult_sim_info)
                sim_info.occult_tracker.add_occult_for_premade_sim(sim_info_wrapper, occult_tuning.occult_type)

    def _apply_template_data(self):
        for (premade_sim_template, sim_info) in self._premade_sim_infos.items():
            premade_sim_template.add_perks(sim_info)
            premade_sim_template.add_rank(sim_info)

    def _apply_aspiration(self):
        for (premade_sim_template, sim_info) in self._premade_sim_infos.items():
            if premade_sim_template.primary_aspiration is not None:
                sim_info.primary_aspiration = premade_sim_template.primary_aspiration
