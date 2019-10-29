from collections import Counterfrom objects import ALL_HIDDEN_REASONSfrom server_commands.argument_helpers import OptionalSimInfoParam, get_optional_targetfrom sims.sim_info_lod import SimInfoLODLevelfrom sims.sim_info_types import Gender, Agefrom sims.sim_spawner import SimCreator, SimSpawnerfrom sims4.commands import CommandTypefrom story_progression.story_progression_enums import CullingReasonsimport randomimport servicesimport sims.sim_infoimport sims4.commands
@sims4.commands.Command('sim_info.lod.request_sim_info_lod', command_type=sims4.commands.CommandType.Automation)
def request_sim_info_lod(sim_lod_level:SimInfoLODLevel, opt_sim:OptionalSimInfoParam=None, _connection=None):
    output = sims4.commands.Output(_connection)
    automation_output = sims4.commands.AutomationOutput(_connection)
    sim_info = get_optional_target(opt_sim, target_type=OptionalSimInfoParam, _connection=_connection)
    if sim_info is None:
        output('Invalid SimInfo for RequestSimLod.')
        automation_output('RequestSimLod; Status:ParamError')
        return False
    if sim_info.request_lod(sim_lod_level):
        output('Requested LOD was set successfully on Sim Info: {}'.format(sim_info))
        automation_output('RequestSimLod; Status:Success, SimId:{}'.format(sim_info.id))
        return True
    else:
        output('Requested LOD could not be set for Sim Info: {}'.format(sim_info))
        automation_output('RequestSimLod; Status:NoChange, SimId:{}'.format(sim_info.id))
        return False

@sims4.commands.Command('sim_info.lod.increment_sim_info_lod', command_type=sims4.commands.CommandType.Automation)
def increment_sim_info_lod(opt_sim:OptionalSimInfoParam=None, _connection=None):
    output = sims4.commands.CheatOutput(_connection)
    automation_output = sims4.commands.AutomationOutput(_connection)
    sim_info = get_optional_target(opt_sim, target_type=OptionalSimInfoParam, _connection=_connection)
    if sim_info is None:
        output('Invalid SimInfo for IncrementSimLod.')
        automation_output('IncrementSimLod; Status:ParamError')
        return False
    new_lod = SimInfoLODLevel.get_next_lod(sim_info.lod)
    if new_lod is not None and sim_info.request_lod(new_lod):
        output('Incremented LOD on Sim Info: {}'.format(sim_info))
        automation_output('IncrementSimLod; Status:Success, SimId:{}'.format(sim_info.id))
        return True
    output('Could not increment LOD on Sim Info: {}'.format(sim_info))
    automation_output('IncrementSimLod; Status:NoChange, SimId:{}'.format(sim_info.id))
    return False

@sims4.commands.Command('sim_info.lod.decrement_sim_info_lod', command_type=sims4.commands.CommandType.Automation)
def decrement_sim_info_lod(opt_sim:OptionalSimInfoParam=None, _connection=None):
    output = sims4.commands.CheatOutput(_connection)
    automation_output = sims4.commands.AutomationOutput(_connection)
    sim_info = get_optional_target(opt_sim, target_type=OptionalSimInfoParam, _connection=_connection)
    if sim_info is None:
        output('Invalid SimInfo for DecrementSimLod.')
        automation_output('DecrementSimLod; Status:ParamError')
        return False
    new_lod = SimInfoLODLevel.get_previous_lod(sim_info.lod)
    if new_lod is not None and sim_info.request_lod(new_lod):
        output('Decremented LOD on Sim Info: {}'.format(sim_info))
        automation_output('DecrementSimLod; Status:Success, SimId:{}'.format(sim_info.id))
        return True
    output('Could not decrement LOD on Sim Info: {}'.format(sim_info))
    automation_output('DecrementSimLod; Status:NoChange, SimId:{}'.format(sim_info.id))
    return False

@sims4.commands.Command('sim_info.lod.set_sims_to_minimum_lod', command_type=sims4.commands.CommandType.Automation)
def set_sims_to_minimum_lod(quantity:int=10, _connection=None):
    set_sims_to_lod(quantity=quantity, lod=SimInfoLODLevel.MINIMUM, _connection=_connection)

@sims4.commands.Command('sim_info.lod.set_sims_to_lod', command_type=sims4.commands.CommandType.Automation)
def set_sims_to_lod(quantity:int=10, lod:SimInfoLODLevel=SimInfoLODLevel.MINIMUM, _connection=None):
    output = sims4.commands.CheatOutput(_connection)
    automation_output = sims4.commands.AutomationOutput(_connection)
    sims_left = quantity
    sim_infos = list(services.sim_info_manager().objects)
    random.shuffle(sim_infos)
    for sim_info in sim_infos:
        if not sim_info.lod == lod:
            if not sim_info.is_npc:
                pass
            else:
                household = sim_info.household
                household_sim_infos = household.sim_infos
                if len(household_sim_infos) > sims_left:
                    pass
                else:
                    for household_sim_info in household_sim_infos:
                        if household_sim_info.is_instanced(allow_hidden_flags=ALL_HIDDEN_REASONS) or not (household_sim_info.can_set_to_lod(lod) and household_sim_info.can_change_lod(household_sim_info.lod)):
                            break
                    for household_sim_info in household_sim_infos:
                        if household_sim_info.request_lod(lod):
                            output('Sim set to {} LOD. ID:{} Name: {}'.format(lod, household_sim_info.id, household_sim_info.full_name))
                            sims_left -= 1
                        else:
                            output('Sim NOT set to {} LOD. ID:{} Name: {}'.format(lod, household_sim_info.id, household_sim_info.full_name))
                    if lod == SimInfoLODLevel.MINIMUM:
                        household.set_to_hidden()
                    if sims_left == 0:
                        break
    if sims_left == 0:
        output('All {} sim infos set to {} LOD'.format(quantity, lod))
        automation_output('SetSimsToLod; Status:Success')
    elif sims_left != quantity:
        output('Only {} sim infos set to {} LOD. Requested: {}'.format(quantity - sims_left, lod, quantity))
        automation_output('SetSimsToLod; Status:Success')
    else:
        output('No sim infos set to {} LOD. Requested: {}'.format(lod, quantity))
        automation_output('SetSimsToLod; Status:Failed')

@sims4.commands.Command('sim_info.lod.set_sims_in_household_to_minimum_lod', command_type=sims4.commands.CommandType.Automation)
def set_sims_in_household_to_minimum_lod(household_id:int=None, _connection=None):
    set_sims_in_household_to_lod(household_id=household_id, lod=SimInfoLODLevel.MINIMUM, _connection=_connection)

@sims4.commands.Command('sim_info.lod.set_sims_in_household_to_lod', command_type=sims4.commands.CommandType.Automation)
def set_sims_in_household_to_lod(household_id:int=None, lod:SimInfoLODLevel=SimInfoLODLevel.MINIMUM, _connection=None):
    output = sims4.commands.CheatOutput(_connection)
    automation_output = sims4.commands.AutomationOutput(_connection)
    household = services.household_manager().get(household_id)
    if household is None:
        output('Household not found.')
        automation_output('set_sims_in_household_to_lod; Status:Failed')
        return False
    for sim_info in household.sim_info_gen():
        if sim_info.can_set_to_lod(lod):
            if not sim_info.can_change_lod(sim_info.lod):
                output('Not all sim infos can be set to {} LOD for household: {}'.format(lod, household))
                automation_output('set_sims_in_household_to_lod; Status:Failed')
                return False
        output('Not all sim infos can be set to {} LOD for household: {}'.format(lod, household))
        automation_output('set_sims_in_household_to_lod; Status:Failed')
        return False
    for sim_info in household.sim_info_gen():
        if sim_info.request_lod(lod):
            output('Sim set to {} LOD. ID:{} Name: {}'.format(lod, sim_info.id, sim_info.full_name))
        else:
            output('Sim NOT set to {} LOD. ID:{} Name: {}'.format(lod, sim_info.id, sim_info.full_name))
    if lod == SimInfoLODLevel.MINIMUM:
        household.set_to_hidden()

@sims4.commands.Command('sim_info.lod.create_minimum_lod_sim_infos', command_type=sims4.commands.CommandType.Automation)
def create_minimum_lod_sim_infos(quantity:int=1, _connection=None):
    create_lod_sim_infos(quantity=quantity, lod=SimInfoLODLevel.MINIMUM, _connection=_connection)

@sims4.commands.Command('sim_info.lod.create_lod_sim_infos', command_type=sims4.commands.CommandType.Automation)
def create_lod_sim_infos(quantity:int=1, lod:SimInfoLODLevel=SimInfoLODLevel.MINIMUM, _connection=None):
    output = sims4.commands.CheatOutput(_connection)
    account = services.client_manager().get(_connection).account
    for _ in range(quantity):
        gender = random.choice(list(Gender))
        age = random.choice([Age.TEEN, Age.YOUNGADULT, Age.ADULT, Age.ELDER])
        first_name = SimSpawner.get_random_first_name(gender)
        last_name = 'CheatFamilyLOD{}'.format(lod)
        sc = SimCreator(gender=gender, age=age, first_name=first_name, last_name=last_name)
        household = services.household_manager().create_household(account)
        (si, _) = SimSpawner.create_sim_infos((sc,), household=household, zone_id=0, creation_source='cheat: LOD SimInfo')
        if not si[0].request_lod(lod):
            output('Failed to request {} lod for {}'.format(lod, si[0]))
        output('Created a SimInfo and requested {} LOD: {}.'.format(lod, si[0]))
    output('Created a total of {} SimInfos at {} LOD'.format(lod, quantity))

@sims4.commands.Command('sim_info.print_lod_count', command_type=sims4.commands.CommandType.Automation)
def print_sim_info_lod_count(_connection=None):
    output = sims4.commands.CheatOutput(_connection)
    sim_info_manager = services.sim_info_manager()
    output('SIM_INFO_CAP: {}'.format(sim_info_manager.SIM_INFO_CAP))
    output('TUNED_CAP_LEVELS: {}'.format(sims.sim_info_manager.SIM_INFO_CAP_PER_LOD))
    override_data = sim_info_manager.get_sim_info_cap_override()
    cap_override_str = str([(k, v) for (k, v) in override_data.items()]) if override_data else 'None'
    output('OVERIDE CAP LEVELS: {}\n'.format(cap_override_str))
    lod_counter = Counter()
    for sim_info in sim_info_manager.values():
        lod_counter[sim_info.lod] += 1
    output(str(lod_counter))

@sims4.commands.Command('sim_info.toggle_lod_name_into_callstack', command_type=CommandType.Automation)
def toggle_lod_name_into_callstack(_connection=None):
    value = sims.sim_info.INJECT_LOD_NAME_IN_CALLSTACK
    value = not value
    sims.sim_info.INJECT_LOD_NAME_IN_CALLSTACK = value
    sims4.commands.output('Inject LOD name is {}'.format(value), _connection)

@sims4.commands.Command('sim_info.reduce_to_num', command_type=sims4.commands.CommandType.Automation)
def set_num_sim_infos(quantity:int, allow_player:bool=False, _connection=None):
    output = sims4.commands.CheatOutput(_connection)
    sim_info_manager = services.sim_info_manager()
    household_manager = services.household_manager()
    all_sim_infos = list(sim_info_manager.objects)
    count = len(all_sim_infos)
    if quantity >= count:
        output('Current count {} < target count {}'.format(count, quantity))
        return True
    num_to_delete = count - quantity
    eligible = []
    for sim_info in all_sim_infos:
        immunity_reasons = set(sim_info.get_culling_immunity_reasons())
        if allow_player:
            immunity_reasons.discard(CullingReasons.PLAYER)
        if not immunity_reasons:
            eligible.append(sim_info)
    if len(eligible) < num_to_delete:
        output('Insufficient eligible Sims; deleting all {}'.format(len(eligible)))
        num_to_delete = len(eligible)
    doomed = random.sample(eligible, num_to_delete)
    for sim_info in doomed:
        household = sim_info.household
        sim_info.remove_permanently()
        if not len(household):
            household_manager.remove(household)
    output('Removed {} Sim infos.  Current count is {}'.format(num_to_delete, len(sim_info_manager.objects)))

@sims4.commands.Command('sim_info.lod.override_cap_level', command_type=sims4.commands.CommandType.Automation)
def set_sim_info_lod_cap(lod:SimInfoLODLevel=SimInfoLODLevel.MINIMUM, cap:int=None, _connection=None):
    output = sims4.commands.CheatOutput(_connection)
    if cap is None:
        output('no cap value set.')
    sim_info_manager = services.sim_info_manager()
    sim_info_manager.set_sim_info_cap_override(lod, cap)
    output('Lod: {} - setting cap level to {}.'.format(lod, cap))

@sims4.commands.Command('sim_info.lod.clear_override_cap_level', command_type=sims4.commands.CommandType.Automation)
def clear_sim_info_lod_cap(lod:SimInfoLODLevel=SimInfoLODLevel.MINIMUM, _connection=None):
    output = sims4.commands.CheatOutput(_connection)
    sim_info_manager = services.sim_info_manager()
    sim_info_manager.clear_sim_info_cap_override_for_lod(lod)
    output('Lod: {} - cleared cap override.  SIM INFO CAP: {}'.format(lod, sim_info_manager.SIM_INFO_CAP))
