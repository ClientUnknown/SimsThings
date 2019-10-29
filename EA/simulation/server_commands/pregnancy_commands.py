from server_commands.argument_helpers import get_optional_target, OptionalTargetParam, OptionalSimInfoParamfrom sims.aging.aging_tuning import AgingTuningfrom sims.pregnancy.pregnancy_offspring_data import PregnancyOffspringDatafrom sims.pregnancy.pregnancy_tracker import PregnancyTrackerfrom sims.sim_info_types import Genderfrom singletons import DEFAULTimport servicesimport sims4.commands
@sims4.commands.Command('pregnancy.clear')
def pregnancy_clear(sim_id:OptionalTargetParam=None, _connection=None):
    sim = get_optional_target(sim_id, _connection)
    if sim is not None:
        pregnancy_tracker = sim.sim_info.pregnancy_tracker
        pregnancy_tracker.clear_pregnancy()
        return True
    return False

@sims4.commands.Command('pregnancy.seed')
def pregnancy_seed(seed:int, sim_id:OptionalTargetParam=None, _connection=None):
    sim = get_optional_target(sim_id, _connection)
    if sim is not None:
        pregnancy_tracker = sim.sim_info.pregnancy_tracker
        if pregnancy_tracker.is_pregnant:
            pregnancy_tracker._seed = seed
            return True
    return False

@sims4.commands.Command('pregnancy.roll')
def pregnancy_roll(sim_id:OptionalTargetParam=None, *seeds, _connection=None):
    sim = get_optional_target(sim_id, _connection)
    if sim is not None:
        pregnancy_tracker = sim.sim_info.pregnancy_tracker
        if pregnancy_tracker.is_pregnant:
            output = sims4.commands.Output(_connection)
            if not seeds:
                seeds = (pregnancy_tracker._seed,)
            for seed in seeds:
                pregnancy_tracker._seed = seed
                pregnancy_tracker.create_offspring_data()
                output('Pregnancy seed: {}'.format(pregnancy_tracker._seed))
                for offspring_data in pregnancy_tracker.get_offspring_data_gen():
                    output('\tGender {}\n\tGenetics: {}\n\n'.format(offspring_data.gender, offspring_data.genetics))
            return True
    return False

@sims4.commands.Command('qa.pregnancy.is_pregnant', command_type=sims4.commands.CommandType.Automation)
def qa_pregnancy_is_pregnant(opt_sim:OptionalSimInfoParam=None, _connection=None):
    sim_info = get_optional_target(opt_sim, _connection, target_type=OptionalSimInfoParam)
    if sim_info is not None:
        sims4.commands.automation_output('Pregnancy; SimId:{}, IsPregnant:{}'.format(opt_sim.target_id, sim_info.pregnancy_tracker.is_pregnant), _connection)

@sims4.commands.Command('pregnancy.force_offspring_count', command_type=sims4.commands.CommandType.Automation)
def pregnancy_force_offspring_count(opt_sim:OptionalSimInfoParam=None, offspring_count:int=1, _connection=None):
    sim_info = get_optional_target(opt_sim, _connection, target_type=OptionalSimInfoParam)
    if sim_info is not None:
        sim_info.pregnancy_tracker.offspring_count_override = offspring_count

@sims4.commands.Command('pregnancy.roll_trait_genetics')
def pregnancy_roll_traits(parent_sim_a:OptionalSimInfoParam=None, parent_sim_b:OptionalSimInfoParam=None, num_traits:int=DEFAULT, offspring_gender:Gender=Gender.FEMALE, _connection=None):
    output = sims4.commands.Output(_connection)
    parent_a = get_optional_target(parent_sim_a, _connection, target_type=OptionalSimInfoParam)
    parent_b = get_optional_target(parent_sim_b, _connection, target_type=OptionalSimInfoParam)
    if not (parent_a and parent_b):
        output('Invalid parents!')
        return False
    if parent_a.gender is parent_b.gender:
        output('Both parents have same gender.')
        return False
    species = parent_a.species
    aging_data = AgingTuning.get_aging_data(species)
    age = aging_data.get_birth_age()
    if num_traits is DEFAULT:
        num_traits = aging_data.get_personality_trait_count(age)
    offspring_data = PregnancyOffspringData(age, offspring_gender, parent_a.species, parent_sim_a, 1)
    selected_traits = PregnancyTracker.select_traits_for_offspring(offspring_data, parent_a, parent_b, num_traits)
    output('Selected Personality Traits:\n\t{}'.format('\n\t'.join(str(trait) for trait in selected_traits if trait.is_personality_trait)))

@sims4.commands.Command('pregnancy.impregnate_many_npcs')
def pregnancy_impregnate_many_npcs(opt_sim:OptionalSimInfoParam=None, _connection=None):
    output = sims4.commands.Output(_connection)
    sim_info = get_optional_target(opt_sim, _connection, target_type=OptionalSimInfoParam)
    if sim_info is None:
        output('No valid SimInfo specified.')
        return False
    if sim_info.is_teen_or_younger:
        output('Restricted to YAE Sims.')
        return False
    sim_info_manager = services.sim_info_manager()
    for target_sim_info in sim_info_manager.get_all():
        if sim_info.gender == target_sim_info.gender:
            pass
        elif sim_info.species != target_sim_info.species:
            pass
        elif target_sim_info.is_teen_or_younger:
            pass
        else:
            pregnancy_tracker = target_sim_info.pregnancy_tracker
            if pregnancy_tracker is None:
                pass
            else:
                pregnancy_tracker.start_pregnancy(target_sim_info, sim_info)
                output('\tImpregnated {}'.format(target_sim_info))
    return True
