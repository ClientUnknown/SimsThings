from server_commands.argument_helpers import TunableInstanceParamfrom sims.sim_info_types import Age, Genderfrom sims.sim_spawner import SimSpawner, SimCreatorimport servicesimport sims4.commands
@sims4.commands.Command('pets.toggle_selectable_pets', command_type=sims4.commands.CommandType.Automation)
def toggle_selectable_pets(_connection=None):
    selectable_sims = services.client_manager().get_first_client().selectable_sims
    selectable_sims.can_select_pets = not selectable_sims.can_select_pets
    if selectable_sims.can_select_pets:
        sims4.commands.cheat_output('Pets are selectable!!!', _connection)
    else:
        sims4.commands.cheat_output('Pets are not selectable...good luck', _connection)

@sims4.commands.Command('pets.create_pet_with_breed', command_type=sims4.commands.CommandType.DebugOnly)
def create_pet_with_breed(breed:TunableInstanceParam(sims4.resources.Types.BREED), gender:Gender=Gender.FEMALE, age:Age=Age.ADULT, x:float=0, y:float=0, z:float=0, _connection=None):
    if age not in (Age.CHILD, Age.ADULT, Age.ELDER):
        sims4.commands.output('Invalid age for pet: {}'.format(age), _connection)
        return
    client = services.client_manager().get(_connection)
    position = sims4.math.Vector3(x, y, z) if x and y and z else None
    sims4.commands.output('Creating pet with breed: {}'.format(breed.__name__), _connection)
    sim_creator = SimCreator(age=age, gender=gender, species=breed.breed_species, additional_tags=(breed.breed_tag,))
    SimSpawner.create_sims((sim_creator,), household=None, tgt_client=client, generate_deterministic_sim=True, sim_position=position, account=client.account, creation_source='cheat: pets.create_pet_with_breed')

@sims4.commands.Command('pets.return_pet', command_type=sims4.commands.CommandType.DebugOnly)
def return_pet(household_id:int, _connection=None):
    household = services.household_manager().get(household_id)
    if household is not None and household.missing_pet_tracker.missing_pet_info is not None:
        household.missing_pet_tracker.cancel_run_away_interaction()

@sims4.commands.Command('pets.post_alert', command_type=sims4.commands.CommandType.DebugOnly)
def post_alert(household_id:int, _connection=None):
    household = services.household_manager().get(household_id)
    if household is not None and household.missing_pet_tracker.missing_pet_info is not None:
        household.missing_pet_tracker.post_alert()
