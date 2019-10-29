from sims.sim_info_tests import SimInfoTestimport cachesimport sims.sim_info_types
@caches.cached
def get_disallowed_ages(affordance):
    disallowed_ages = set()
    for test in affordance.test_globals:
        if isinstance(test, SimInfoTest):
            if test.ages is None:
                pass
            else:
                for age in sims.sim_info_types.Age:
                    if age not in test.ages:
                        disallowed_ages.add(age)
    return disallowed_ages
