from _collections import defaultdictimport itertoolsimport randomfrom filters.demographics_filter_term_mixin import DemographicsFilterTermMixinfrom sims.sim_spawner_enums import SimNameTypefrom sims4.service_manager import Serviceimport servicesimport sims4.logimport world.streetlogger = sims4.log.Logger('StreetDemographics', default_owner='tingyul')
class DemographicsService(Service):

    def world_meets_townie_population_cap(self, world_id):
        street = world.street.get_street_instance_from_world_id(world_id)
        target_population = street.townie_demographics.target_population if street is not None else None
        if target_population is None:
            return True
        else:
            townie_population = sum(len(household) for household in services.household_manager().values() if household.home_zone_id == 0 and household.get_home_world_id() == world_id)
            if townie_population >= target_population:
                return True
        return False

    def choose_world_and_conform_filter(self, sim_creator, filter_terms, allow_all_worlds):
        demographics_terms = [filter_term for filter_term in filter_terms if isinstance(filter_term, DemographicsFilterTermMixin)]
        whitelists = []
        blacklists = []
        for term in demographics_terms:
            (whitelist, blacklist) = term.get_valid_world_ids()
            if whitelist is not None:
                whitelists.append(whitelist)
            if blacklist is not None:
                blacklists.append(blacklist)
        world_ids = set()
        if allow_all_worlds:
            world_ids.update(services.get_persistence_service().get_world_ids())
        elif whitelists:
            world_ids.update(whitelists.pop())
        world_ids.intersection_update(*whitelists)
        world_ids.difference_update(*blacklists)
        world_id = self._choose_world_from_candidates(world_ids)
        if world_id is None:
            return (None, SimNameType.DEFAULT)
        feature = self._get_filter_feature_for_world_id(world_id)
        if feature is not None:
            if feature.sim_creator_tags is not None:
                sim_creator.tag_set.update(feature.sim_creator_tags.tags)
            filter_terms.extend(feature.filter_terms)
            return (world_id, feature.sim_name_type)
        return (world_id, SimNameType.DEFAULT)

    def _choose_world_from_candidates(self, candidate_world_ids):
        if not candidate_world_ids:
            return
        population_counts = defaultdict(int)
        for household in services.household_manager().values():
            if household.home_zone_id != 0:
                pass
            else:
                population_counts[household.get_home_world_id()] += len(household)
        target_counts = {}
        for world_id in candidate_world_ids:
            street = world.street.get_street_instance_from_world_id(world_id)
            if street is None or street.townie_demographics.target_population is None:
                target_counts[world_id] = 0
            else:
                target_counts[world_id] = street.townie_demographics.target_population
        worlds_that_met_target = []
        worlds_below_target = []
        for world_id in candidate_world_ids:
            if population_counts[world_id] < target_counts[world_id]:
                worlds_below_target.append(world_id)
            else:
                worlds_that_met_target.append(world_id)
        if worlds_that_met_target and (len(worlds_that_met_target) == len(candidate_world_ids) or random.randint(0, 1) == 0):
            worlds_that_met_target.sort(key=lambda world_id: population_counts[world_id] - target_counts[world_id])
            return worlds_that_met_target[0]
        weighted_candidates = tuple((target_counts[world_id] - population_counts[world_id], world_id) for world_id in worlds_below_target)
        world_id = sims4.random.weighted_random_item(weighted_candidates)
        return world_id

    def _get_filter_feature_for_world_id(self, world_id):
        street = world.street.get_street_instance_from_world_id(world_id)
        if street is None:
            return
        features = [(f.weight, f) for f in street.townie_demographics.filter_features]
        feature = sims4.random.weighted_random_item(features)
        return feature
