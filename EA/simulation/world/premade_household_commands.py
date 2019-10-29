from distributor.system import Distributorfrom filters.sim_template import SimTemplateTypefrom server_commands.argument_helpers import TunableInstanceParamfrom sims.sim_info import save_active_household_command_start, save_active_household_command_stopimport persistence_moduleimport servicesimport sims4.commands
@sims4.commands.Command('premade_household.create')
def create_premade_household_from_template(template:TunableInstanceParam(sims4.resources.Types.SIM_TEMPLATE), _connection=None):
    template.create_household(0, None, creation_source='from premade_household.create command')
    return True

@sims4.commands.Command('premade_household.generate')
def generate(template:TunableInstanceParam(sims4.resources.Types.SIM_TEMPLATE), _connection=None):
    output = sims4.commands.Output(_connection)
    if template.template_type != SimTemplateType.PREMADE_HOUSEHOLD:
        output('{} has invalid template type. Expected PREMADE_HOUSEHOLD, got {}'.format(template, template.template_type))
        return
    try:
        distributor = Distributor.instance()
        distributor.enabled = False
        household = template.create_premade_household()
        if household is None:
            output('Failed to create household from template {}'.format(template))
            return
        save_active_household_command_start()
        save_slot_data_msg = services.get_persistence_service().get_save_slot_proto_buff()
        save_slot_data_msg.slot_id = 0
        save_slot_data_msg.active_household_id = household.id
        sims4.core_services.service_manager.save_all_services(None, save_slot_data=save_slot_data_msg)
        save_game_buffer = services.get_persistence_service().get_save_game_data_proto()
        persistence_module.run_persistence_operation(persistence_module.PersistenceOpType.kPersistenceOpSaveHousehold, save_game_buffer, 0, None)
    except Exception as e:
        output('Exception thrown while executing command premade_household.generate.\n{}'.format(e))
        output('No household file generated. Please address all the exceptions.')
        raise
    finally:
        save_active_household_command_stop()
        distributor.enabled = True
    output('Exported active household to T:\\InGame\\Households\\{}.household'.format(household.name))
    for sim_info in tuple(household):
        sim_info.remove_permanently()

@sims4.commands.Command('premade_household.generate_all')
def generate_all(_connection=None):
    for template in services.get_instance_manager(sims4.resources.Types.SIM_TEMPLATE).types.values():
        if template.template_type != SimTemplateType.PREMADE_HOUSEHOLD:
            pass
        else:
            generate(template, _connection=_connection)

@sims4.commands.Command('premade_household.list_premade_household_ids')
def list_reference_ids(separator:str=' ', _connection=None):
    output = sims4.commands.Output(_connection)
    household_manager = services.household_manager()
    for household in household_manager._objects.values():
        if household.premade_household_id > 0:
            output('{}{}{}'.format(household.premade_household_id, separator, household.name))
