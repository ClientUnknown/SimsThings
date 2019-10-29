from collections import Counter, namedtupleimport itertoolsfrom gsi_handlers.sim_info_culling_handler import CullingArchive, CullingCensusfrom objects import ALL_HIDDEN_REASONSfrom performance.performance_commands import get_sim_info_creation_sourcesfrom sims.genealogy_tracker import genealogy_cachingfrom sims.household import Householdfrom sims.sim_info_lod import SimInfoLODLevelfrom sims4.math import MAX_INT32from sims4.tuning.tunable import TunableRange, TunableTuple, TunablePercent, TunableMapping, TunableEnumEntry, OptionalTunablefrom story_progression import StoryProgressionFlagsfrom story_progression.story_progression_action import _StoryProgressionActionfrom story_progression.story_progression_enums import CullingReasonsfrom tunable_time import TunableTimeOfDayfrom uid import UniqueIdGeneratorimport gsi_handlersimport servicesimport sims4.logimport telemetry_helperlogger = sims4.log.Logger('SimInfoCulling', default_owner='manus')TELEMETRY_GROUP_STORY_PROGRESSION = 'STRY'TELEMETRY_HOOK_CULL_SIMINFO_BEFORE = 'CSBE'TELEMETRY_HOOK_CULL_SIMINFO_BEFORE2 = 'CSBT'TELEMETRY_HOOK_CULL_SIMINFO_AFTER = 'CSAF'TELEMETRY_CREATION_SOURCE_HOOK_COUNT = 10TELEMETRY_CREATION_SOURCE_BUFFER_LENGTH = 100with sims4.reload.protected(globals()):
    telemetry_id_generator = UniqueIdGenerator()writer = sims4.telemetry.TelemetryWriter(TELEMETRY_GROUP_STORY_PROGRESSION)SimInfoCullingScoreInfo = namedtuple('SimInfoCullingScoreInfo', ('score', 'rel_score', 'inst_score', 'importance_score'))DEFAULT_CULLING_INFO = SimInfoCullingScoreInfo(0, 0, 0, 1.0)
class StoryProgressionActionMaxPopulation(_StoryProgressionAction):
    FACTORY_TUNABLES = {'sim_info_cap_per_lod': TunableMapping(description="\n            The mapping of SimInfoLODLevel value to an interval of sim info cap\n            integer values.\n            \n            NOTE: The ACTIVE lod can't be tuned here because it's being tracked\n            via the Maximum Size tuning in Household module tuning.\n            ", key_type=TunableEnumEntry(description='\n                The SimInfoLODLevel value.\n                ', tunable_type=SimInfoLODLevel, default=SimInfoLODLevel.FULL, invalid_enums=(SimInfoLODLevel.ACTIVE,)), value_type=TunableRange(description='\n                The number of sim infos allowed to be present before culling\n                is triggered for this SimInfoLODLevel.\n                ', tunable_type=int, default=210, minimum=0)), 'time_of_day': TunableTuple(description='\n            Only run this action when it is between a certain time of day.\n            ', start_time=TunableTimeOfDay(default_hour=2), end_time=TunableTimeOfDay(default_hour=6)), 'culling_buffer_percentage': TunablePercent(description='\n            When sim infos are culled due to the number of sim infos exceeding\n            the cap, this is how much below the cap the number of sim infos\n            will be (as a percentage of the cap) after the culling, roughly.\n            The margin of error is due to the fact that we cull at the household\n            level, so the number of sims culled can be a bit more than this value\n            if the last household culled contains more sims than needed to reach\n            the goal. (i.e. we never cull partial households)\n            ', default=20), 'homeless_played_demotion_time': OptionalTunable(description='\n            If enabled, played Sims that have been homeless for at least this\n            many days will be drops from FULL to BASE_SIMULATABLE lod.\n            ', tunable=TunableRange(tunable_type=int, default=10, minimum=0))}

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._played_family_tree_distances = {}
        self._precull_telemetry_data = Counter()
        self._precull_telemetry_lod_counts_str = ''
        self._telemetry_id = 0
        self._total_sim_cap = Household.MAXIMUM_SIZE
        self._total_sim_cap += sum(self.sim_info_cap_per_lod.values())
        import sims.sim_info_manager
        sims.sim_info_manager.SimInfoManager.SIM_INFO_CAP = self._total_sim_cap
        sims.sim_info_manager.SIM_INFO_CAP_PER_LOD = self.sim_info_cap_per_lod

    def should_process(self, options):
        current_time = services.time_service().sim_now
        if not current_time.time_between_day_times(self.time_of_day.start_time, self.time_of_day.end_time):
            return False
        return True

    def process_action(self, story_progression_flags):
        try:
            self._pre_cull()
            self._process_full()
            self._process_base()
            self._process_minimum()
            self._post_cull(story_progression_flags)
        finally:
            self._cleanup()

    def _get_cap_level(self, sim_info_lod):
        cap_override = services.sim_info_manager().get_sim_info_cap_override_per_lod(sim_info_lod)
        if cap_override is not None:
            return cap_override
        return self.sim_info_cap_per_lod[sim_info_lod]

    def _pre_cull(self):
        self._played_family_tree_distances = self._get_played_family_tree_distances()
        self._telemetry_id = telemetry_id_generator()
        self._precull_telemetry_data['scap'] = self._total_sim_cap
        (player_households, player_sims, households, sims, lod_counts) = self._get_census()
        self._precull_telemetry_data['thob'] = households
        self._precull_telemetry_data['tsib'] = sims
        self._precull_telemetry_data['phob'] = player_households
        self._precull_telemetry_data['psib'] = player_sims
        self._precull_telemetry_lod_counts_str = self._get_lod_counts_str_for_telemetry(lod_counts)
        for sim_info in services.sim_info_manager().get_all():
            sim_info.report_telemetry('pre-culling')
        self._trigger_creation_source_telemetry()

    def _trigger_creation_source_telemetry(self):
        payload = ''
        counter = 0

        def dump_hook():
            hook_name = 'CS{:0>2}'.format(counter)
            with telemetry_helper.begin_hook(writer, hook_name) as hook:
                hook.write_int('clid', self._telemetry_id)
                hook.write_string('crsr', payload)

        sources = get_sim_info_creation_sources()
        for (source, count) in sources.most_common():
            if counter >= TELEMETRY_CREATION_SOURCE_HOOK_COUNT:
                break
            delta = '{}${}'.format(source, count)
            if len(payload) + len(delta) <= TELEMETRY_CREATION_SOURCE_BUFFER_LENGTH:
                payload = '{}+{}'.format(payload, delta)
            else:
                dump_hook()
                payload = delta
                counter += 1
        dump_hook()

    def _process_full(self):
        if gsi_handlers.sim_info_culling_handler.is_archive_enabled():
            gsi_archive = CullingArchive('Full Pass')
            gsi_archive.census_before = self._get_gsi_culling_census()
        else:
            gsi_archive = None
        cap = self._get_cap_level(SimInfoLODLevel.FULL)
        sim_infos = services.sim_info_manager().get_sim_infos_with_lod(SimInfoLODLevel.FULL)
        now = services.time_service().sim_now
        mandatory_drops = set()
        scores = {}
        for sim_info in sim_infos:
            if sim_info.is_instanced(allow_hidden_flags=ALL_HIDDEN_REASONS):
                if gsi_archive is not None:
                    gsi_archive.add_sim_info_cullability(sim_info, info='immune -- instanced')
                    if not sim_info.is_player_sim:
                        if gsi_archive is not None:
                            gsi_archive.add_sim_info_cullability(sim_info, score=0, info='mandatory drop -- non-player')
                        mandatory_drops.add(sim_info)
                    elif sim_info.household.home_zone_id != 0:
                        if gsi_archive is not None:
                            gsi_archive.add_sim_info_cullability(sim_info, info='immune -- player and not homeless')
                            if self.homeless_played_demotion_time is not None:
                                days_homeless = (now - sim_info.household.home_zone_move_in_time).in_days()
                                if days_homeless < self.homeless_played_demotion_time:
                                    if gsi_archive is not None:
                                        gsi_archive.add_sim_info_cullability(sim_info, info='immune -- not homeless long enough')
                                        if gsi_archive is not None:
                                            gsi_archive.add_sim_info_cullability(sim_info, score=days_homeless, info='homeless for too long')
                                        scores[sim_info] = days_homeless
                                else:
                                    if gsi_archive is not None:
                                        gsi_archive.add_sim_info_cullability(sim_info, score=days_homeless, info='homeless for too long')
                                    scores[sim_info] = days_homeless
                                    if gsi_archive is not None:
                                        gsi_archive.add_sim_info_cullability(sim_info, info='immune -- no pressure to drop')
                            elif gsi_archive is not None:
                                gsi_archive.add_sim_info_cullability(sim_info, info='immune -- no pressure to drop')
                    elif self.homeless_played_demotion_time is not None:
                        days_homeless = (now - sim_info.household.home_zone_move_in_time).in_days()
                        if days_homeless < self.homeless_played_demotion_time:
                            if gsi_archive is not None:
                                gsi_archive.add_sim_info_cullability(sim_info, info='immune -- not homeless long enough')
                                if gsi_archive is not None:
                                    gsi_archive.add_sim_info_cullability(sim_info, score=days_homeless, info='homeless for too long')
                                scores[sim_info] = days_homeless
                        else:
                            if gsi_archive is not None:
                                gsi_archive.add_sim_info_cullability(sim_info, score=days_homeless, info='homeless for too long')
                            scores[sim_info] = days_homeless
                            if gsi_archive is not None:
                                gsi_archive.add_sim_info_cullability(sim_info, info='immune -- no pressure to drop')
                    elif gsi_archive is not None:
                        gsi_archive.add_sim_info_cullability(sim_info, info='immune -- no pressure to drop')
            elif not sim_info.is_player_sim:
                if gsi_archive is not None:
                    gsi_archive.add_sim_info_cullability(sim_info, score=0, info='mandatory drop -- non-player')
                mandatory_drops.add(sim_info)
            elif sim_info.household.home_zone_id != 0:
                if gsi_archive is not None:
                    gsi_archive.add_sim_info_cullability(sim_info, info='immune -- player and not homeless')
                    if self.homeless_played_demotion_time is not None:
                        days_homeless = (now - sim_info.household.home_zone_move_in_time).in_days()
                        if days_homeless < self.homeless_played_demotion_time:
                            if gsi_archive is not None:
                                gsi_archive.add_sim_info_cullability(sim_info, info='immune -- not homeless long enough')
                                if gsi_archive is not None:
                                    gsi_archive.add_sim_info_cullability(sim_info, score=days_homeless, info='homeless for too long')
                                scores[sim_info] = days_homeless
                        else:
                            if gsi_archive is not None:
                                gsi_archive.add_sim_info_cullability(sim_info, score=days_homeless, info='homeless for too long')
                            scores[sim_info] = days_homeless
                            if gsi_archive is not None:
                                gsi_archive.add_sim_info_cullability(sim_info, info='immune -- no pressure to drop')
                    elif gsi_archive is not None:
                        gsi_archive.add_sim_info_cullability(sim_info, info='immune -- no pressure to drop')
            elif self.homeless_played_demotion_time is not None:
                days_homeless = (now - sim_info.household.home_zone_move_in_time).in_days()
                if days_homeless < self.homeless_played_demotion_time:
                    if gsi_archive is not None:
                        gsi_archive.add_sim_info_cullability(sim_info, info='immune -- not homeless long enough')
                        if gsi_archive is not None:
                            gsi_archive.add_sim_info_cullability(sim_info, score=days_homeless, info='homeless for too long')
                        scores[sim_info] = days_homeless
                else:
                    if gsi_archive is not None:
                        gsi_archive.add_sim_info_cullability(sim_info, score=days_homeless, info='homeless for too long')
                    scores[sim_info] = days_homeless
                    if gsi_archive is not None:
                        gsi_archive.add_sim_info_cullability(sim_info, info='immune -- no pressure to drop')
            elif gsi_archive is not None:
                gsi_archive.add_sim_info_cullability(sim_info, info='immune -- no pressure to drop')
        num_to_cull = self._get_num_to_cull(len(sim_infos) - len(mandatory_drops), cap)
        sorted_sims = sorted(scores.keys(), key=lambda x: scores[x], reverse=True)
        for sim_info in itertools.chain(mandatory_drops, sorted_sims[:num_to_cull]):
            if sim_info.request_lod(SimInfoLODLevel.BASE):
                if gsi_archive is not None:
                    gsi_archive.add_sim_info_action(sim_info, action='drop to BASE')
            elif gsi_archive is not None:
                gsi_archive.add_sim_info_action(sim_info, action='failed to drop to BASE')
        if gsi_archive is not None:
            gsi_archive.census_after = self._get_gsi_culling_census()
            gsi_archive.apply()

    def _process_base(self):
        culling_service = services.get_culling_service()
        if gsi_handlers.sim_info_culling_handler.is_archive_enabled():
            gsi_archive = CullingArchive('Base Pass')
            gsi_archive.census_before = self._get_gsi_culling_census()
        else:
            gsi_archive = None
        base_cap = self._get_cap_level(SimInfoLODLevel.BASE)
        sim_info_manager = services.sim_info_manager()
        sim_infos = sim_info_manager.get_sim_infos_with_lod(SimInfoLODLevel.BASE)
        households = frozenset(sim_info.household for sim_info in sim_infos)
        num_infos_above_base_lod = sim_info_manager.get_num_sim_infos_with_criteria(lambda sim_info: sim_info.lod > SimInfoLODLevel.BASE)
        full_and_active_cap = self._get_cap_level(SimInfoLODLevel.FULL) + Household.MAXIMUM_SIZE
        cap_overage = num_infos_above_base_lod - full_and_active_cap
        cap = max(base_cap - cap_overage, 0) if cap_overage > 0 else base_cap
        sim_info_immunity_reasons = {}
        sim_info_scores = {}
        for sim_info in sim_infos:
            immunity_reasons = sim_info.get_culling_immunity_reasons()
            if immunity_reasons:
                sim_info_immunity_reasons[sim_info] = immunity_reasons
            else:
                sim_info_scores[sim_info] = culling_service.get_culling_score_for_sim_info(sim_info)
        household_scores = {}
        immune_households = set()
        for household in households:
            if any(sim_info.lod != SimInfoLODLevel.BASE or sim_info in sim_info_immunity_reasons for sim_info in household):
                immune_households.add(household)
            else:
                score = max(sim_info_scores[sim_info].score for sim_info in household)
                household_scores[household] = score
        if gsi_archive is not None:
            for (sim_info, immunity_reasons) in sim_info_immunity_reasons.items():
                gsi_archive.add_sim_info_cullability(sim_info, info='immune: {}'.format(', '.join(reason.gsi_reason for reason in immunity_reasons)))
            for (sim_info, score) in sim_info_scores.items():
                gsi_archive.add_sim_info_cullability(sim_info, score=score.score, rel_score=score.rel_score, inst_score=score.inst_score, importance_score=score.importance_score)

            def get_sim_cullability(sim_info):
                if sim_info.lod > SimInfoLODLevel.BASE:
                    return 'LOD is not BASE'
                if sim_info in sim_info_immunity_reasons:
                    return ', '.join(reason.gsi_reason for reason in sim_info_immunity_reasons[sim_info])
                elif sim_info in sim_info_scores:
                    return str(sim_info_scores[sim_info].score)
                return ''

            for household in immune_households:
                member_cullabilities = ', '.join('{} ({})'.format(sim_info.full_name, get_sim_cullability(sim_info)) for sim_info in household)
                gsi_archive.add_household_cullability(household, info='immune: {}'.format(member_cullabilities))
            for (household, score) in household_scores.items():
                member_cullabilities = ', '.join('{} ({})'.format(sim_info.full_name, get_sim_cullability(sim_info)) for sim_info in household)
                gsi_archive.add_household_cullability(household, score=score, info=member_cullabilities)
        self._precull_telemetry_data['imho'] = len(immune_households)
        self._precull_telemetry_data['imsi'] = len(sim_info_immunity_reasons)
        self._precull_telemetry_data['imsc'] = sum(len(h) for h in immune_households)
        self._precull_telemetry_data.update(reason.telemetry_hook for reason in itertools.chain.from_iterable(sim_info_immunity_reasons.values()))
        for reason in CullingReasons.ALL_CULLING_REASONS:
            if reason not in self._precull_telemetry_data:
                self._precull_telemetry_data[reason.telemetry_hook] = 0
        culling_service = services.get_culling_service()
        sorted_households = sorted(household_scores, key=household_scores.get)
        num_to_cull = self._get_num_to_cull(len(sim_infos), cap)
        while sorted_households and num_to_cull > 0:
            household = sorted_households.pop(0)
            num_to_cull -= len(household)
            culling_service.cull_household(household, is_important_fn=self._has_player_sim_in_family_tree, gsi_archive=gsi_archive)
        for sim_info in sim_info_manager.get_all():
            if sim_info.household is None:
                logger.error('Found sim info {} without household during sim culling.', sim_info)
        if gsi_archive is not None:
            gsi_archive.census_after = self._get_gsi_culling_census()
            gsi_archive.apply()

    def _process_minimum(self):
        if gsi_handlers.sim_info_culling_handler.is_archive_enabled():
            gsi_archive = CullingArchive('Minimum Pass')
            gsi_archive.census_before = self._get_gsi_culling_census()
        else:
            gsi_archive = None
        cap = self._get_cap_level(SimInfoLODLevel.MINIMUM)
        sim_info_manager = services.sim_info_manager()
        min_lod_sim_infos = sim_info_manager.get_sim_infos_with_lod(SimInfoLODLevel.MINIMUM)
        num_min_lod_sim_infos = len(min_lod_sim_infos)
        sorted_sim_infos = sorted(min_lod_sim_infos, key=lambda x: self._played_family_tree_distances[x.id], reverse=True)
        if gsi_archive is not None:
            for sim_info in min_lod_sim_infos:
                gsi_archive.add_sim_info_cullability(sim_info, score=self._played_family_tree_distances[sim_info.id])
        num_to_cull = self._get_num_to_cull(num_min_lod_sim_infos, cap)
        for sim_info in sorted_sim_infos[:num_to_cull]:
            if gsi_archive is not None:
                gsi_archive.add_sim_info_action(sim_info, action='cull')
            sim_info.remove_permanently()
        if gsi_archive is not None:
            gsi_archive.census_after = self._get_gsi_culling_census()
            gsi_archive.apply()

    def _post_cull(self, story_progression_flags):
        with telemetry_helper.begin_hook(writer, TELEMETRY_HOOK_CULL_SIMINFO_BEFORE) as hook:
            hook.write_int('clid', self._telemetry_id)
            hook.write_string('rson', self._get_trigger_reason(story_progression_flags))
            for (key, value) in self._precull_telemetry_data.items():
                hook.write_int(key, value)
        with telemetry_helper.begin_hook(writer, TELEMETRY_HOOK_CULL_SIMINFO_BEFORE2) as hook:
            hook.write_int('clid', self._telemetry_id)
            hook.write_string('lodb', self._precull_telemetry_lod_counts_str)
        (player_households, player_sims, households, sims, lod_counts) = self._get_census()
        with telemetry_helper.begin_hook(writer, TELEMETRY_HOOK_CULL_SIMINFO_AFTER) as hook:
            hook.write_int('clid', self._telemetry_id)
            hook.write_string('rson', self._get_trigger_reason(story_progression_flags))
            hook.write_int('scap', self._total_sim_cap)
            hook.write_int('thoa', households)
            hook.write_int('tsia', sims)
            hook.write_string('loda', self._get_lod_counts_str_for_telemetry(lod_counts))
            hook.write_int('phoa', player_households)
            hook.write_int('psia', player_sims)

    def _cleanup(self):
        self._played_family_tree_distances.clear()
        self._precull_telemetry_data.clear()

    def _get_played_family_tree_distances(self):
        with genealogy_caching():
            sim_info_manager = services.sim_info_manager()
            played_sim_infos = frozenset(sim_info for sim_info in sim_info_manager.get_all() if sim_info.is_player_sim)

            def get_sim_ids_with_played_spouses():
                return set(sim_info.spouse_sim_id for sim_info in played_sim_infos if sim_info.spouse_sim_id is not None and sim_info.spouse_sim_id in sim_info_manager)

            def get_sim_ids_with_played_siblings():
                sim_ids_with_played_siblings = set()
                visited_ids = set()
                for sim_info in played_sim_infos:
                    if sim_info.id in visited_ids:
                        pass
                    else:
                        siblings = set(sim_info.genealogy.get_siblings_sim_infos_gen())
                        siblings.add(sim_info)
                        visited_ids.update(sibling.id for sibling in siblings)
                        played_siblings = set(sibling for sibling in siblings if sibling.is_player_sim)
                        if len(played_siblings) == 1:
                            sim_ids_with_played_siblings.update(sibling.id for sibling in siblings if sibling not in played_siblings)
                        elif len(played_siblings) > 1:
                            sim_ids_with_played_siblings.update(sibling.id for sibling in siblings)
                return sim_ids_with_played_siblings

            def get_played_relative_distances(up=False):
                distances = {}
                step = 0
                next_crawl_set = set(played_sim_infos)
                while next_crawl_set:
                    step += 1
                    crawl_set = next_crawl_set
                    next_crawl_set = set()

                    def relatives_gen(sim_info):
                        if up:
                            yield from sim_info.genealogy.get_child_sim_infos_gen()
                        else:
                            yield from sim_info.genealogy.get_parent_sim_infos_gen()

                    for relative in itertools.chain.from_iterable(relatives_gen(sim_info) for sim_info in crawl_set):
                        if relative.id in distances:
                            pass
                        else:
                            distances[relative.id] = step
                            if relative not in played_sim_infos:
                                next_crawl_set.add(relative)
                return distances

            zero_distance_sim_ids = get_sim_ids_with_played_spouses() | get_sim_ids_with_played_siblings()
            ancestor_map = get_played_relative_distances(up=True)
            descendant_map = get_played_relative_distances(up=False)

            def get_score(sim_info):
                sim_id = sim_info.id
                if sim_id in zero_distance_sim_ids:
                    return 0
                return min(ancestor_map.get(sim_id, MAX_INT32), descendant_map.get(sim_id, MAX_INT32))

            distances = {sim_info.id: get_score(sim_info) for sim_info in sim_info_manager.get_all()}
            return distances

    def _has_player_sim_in_family_tree(self, sim_info):
        if sim_info.id not in self._played_family_tree_distances:
            logger.error('Getting played family tree distance for an unknown Sim Info {}', sim_info)
            return False
        return self._played_family_tree_distances[sim_info.id] < MAX_INT32

    def _get_distance_to_nearest_player_sim_in_family_tree(self, sim_info):
        if sim_info.id not in self._played_family_tree_distances:
            logger.error('Getting played family tree distance for an unknown Sim Info {}', sim_info)
            return MAX_INT32
        return self._played_family_tree_distances[sim_info.id]

    def _get_num_to_cull(self, pop_count, pop_cap):
        if pop_cap < 0:
            logger.error('Invalid pop_cap provided to _get_num_to_cull: {}', pop_cap)
        if pop_count > pop_cap:
            target_pop = pop_cap*(1 - self.culling_buffer_percentage)
            return int(pop_count - target_pop)
        return 0

    def _get_census(self):
        player_households = sum(1 for household in services.household_manager().get_all() if household.is_player_household)
        player_sims = sum(1 for sim_info in services.sim_info_manager().get_all() if sim_info.is_player_sim)
        households = len(services.household_manager())
        sims = len(services.sim_info_manager())
        lod_counts = {lod: services.sim_info_manager().get_num_sim_infos_with_lod(lod) for lod in SimInfoLODLevel}
        return (player_households, player_sims, households, sims, lod_counts)

    def _get_lod_counts_str_for_telemetry(self, lod_counts):
        return '+'.join('{}~{}'.format(lod.name, num) for (lod, num) in lod_counts.items())

    def _get_gsi_culling_census(self):
        (player_households, player_sims, households, sims, lod_counts) = self._get_census()
        return CullingCensus(player_households, player_sims, households, sims, lod_counts)

    @classmethod
    def _get_trigger_reason(cls, flags):
        reason = 'REGULAR_PROGRESSION'
        if flags & StoryProgressionFlags.SIM_INFO_FIREMETER != 0:
            reason = 'FIREMETER'
        return reason
