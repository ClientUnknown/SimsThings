from gsi_handlers.gameplay_archiver import GameplayArchiverfrom sims4.gsi.dispatcher import GsiHandlerfrom sims4.gsi.schema import GsiGridSchemafrom vet.vet_clinic_utils import get_vet_clinic_zone_directorimport servicesvet_clinic_flow_schema = GsiGridSchema(label='Vet/Vet Clinic Flow Log')vet_clinic_flow_schema.add_field('game_time', label='Game Time', width=1)vet_clinic_flow_schema.add_field('sims', label='Sim(s)', width=2)vet_clinic_flow_schema.add_field('source', label='Source', width=1)vet_clinic_flow_schema.add_field('message', label='message', width=4)host_archiver = GameplayArchiver('flowLog', vet_clinic_flow_schema, add_to_archive_enable_functions=True)
def log_vet_flow_entry(sims, source, message):
    archive_data = {'sims': sims, 'source': source, 'message': message}
    host_archiver.archive(data=archive_data)
vet_clinic_customer_schema = GsiGridSchema(label='Vet/Customers')vet_clinic_customer_schema.add_field('situation_id', label='Situation Id', width=1)vet_clinic_customer_schema.add_field('waiting_start_time', label='Wait Start Time', width=1)vet_clinic_customer_schema.add_field('waiting_queue_order', label='Order In Queue', width=1)vet_clinic_customer_schema.add_field('pet', label='Pet', width=1)vet_clinic_customer_schema.add_field('owner', label='Owner', width=1)vet_clinic_customer_schema.add_field('current_state', label='Current State', width=1)vet_clinic_customer_schema.add_field('vet', label='Vet', width=1)with vet_clinic_customer_schema.add_view_cheat('situations.destroy', label='Destroy Situation') as cheat:
    cheat.add_token_param('situation_id')
@GsiHandler('vet_customers', vet_clinic_customer_schema)
def generate_customer_data(zone_id:int=None):
    customer_situations_data = []
    zone_director = get_vet_clinic_zone_director()
    if zone_director is None:
        return customer_situations_data
    waiting_situations_ids = list(zone_director._waiting_situations.keys())
    waiting_situations_ids_list_fixed = tuple(waiting_situations_ids)

    def add_customer_situation_data(customer_situation):
        is_waiting_situation = customer_situation.id in waiting_situations_ids
        order_in_queue = waiting_situations_ids_list_fixed.index(customer_situation.id) if is_waiting_situation else 'Not In Queue'
        customer_situations_data.append({'waiting_start_time': str(customer_situation.wait_start_time), 'waiting_queue_order': str(order_in_queue), 'situation_id': str(customer_situation.id), 'pet': str(customer_situation.get_pet()), 'owner': str(customer_situation.get_pet_owner()), 'current_state': customer_situation.current_state_type.__name__, 'vet': str(customer_situation.get_vet())})
        if is_waiting_situation:
            waiting_situations_ids.remove(customer_situation.id)

    for customer_situation in zone_director.customer_situations_gen():
        add_customer_situation_data(customer_situation)
    if waiting_situations_ids:
        for customer_situation_id in tuple(waiting_situations_ids):
            customer_situation = services.get_zone_situation_manager().get(customer_situation_id)
            if customer_situation is not None:
                add_customer_situation_data(customer_situation)
    return customer_situations_data
