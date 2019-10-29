from sims4.gsi.dispatcher import GsiHandlerfrom sims4.gsi.schema import GsiGridSchema, GsiFieldVisualizersimport servicessim_spawner_service_queue_schema = GsiGridSchema(label='Sim Spawner Service/Queue')sim_spawner_service_queue_schema.add_field('sim', label='Sim', type=GsiFieldVisualizers.STRING)sim_spawner_service_queue_schema.add_field('reason', label='Reason', type=GsiFieldVisualizers.STRING, width=1)sim_spawner_service_queue_schema.add_field('priority', label='Priority', type=GsiFieldVisualizers.STRING)sim_spawner_service_queue_schema.add_field('position', label='Position', type=GsiFieldVisualizers.STRING)
@GsiHandler('sim_spawner_service_queue', sim_spawner_service_queue_schema)
def generate_sim_spawner_service_queue(zone_id:int=None):
    sim_spawner_service = services.sim_spawner_service()
    queue = sim_spawner_service.get_queue_for_gsi()
    return queue
sim_spawner_service_global_schema = GsiGridSchema(label='Sim Spawner Service/Global')sim_spawner_service_global_schema.add_field('npcs_here', label='NPCs Here', type=GsiFieldVisualizers.INT, width=1)sim_spawner_service_global_schema.add_field('npcs_leaving', label='NPCs Leaving', type=GsiFieldVisualizers.INT, width=1)sim_spawner_service_global_schema.add_field('npc_soft_cap', label='NPC Soft Cap', type=GsiFieldVisualizers.INT, width=1)sim_spawner_service_global_schema.add_field('npc_cap_modifier', label='NPC Cap Modifier', type=GsiFieldVisualizers.FLOAT, width=1)
@GsiHandler('sim_spawner_service_global', sim_spawner_service_global_schema)
def generate_sim_spawner_service_global(zone_id:int=None):
    sim_spawner_service = services.sim_spawner_service()
    data = {'npcs_here': sim_spawner_service.number_of_npcs_instantiated, 'npcs_leaving': sim_spawner_service.number_of_npcs_leaving, 'npc_soft_cap': sim_spawner_service.npc_soft_cap, 'npc_cap_modifier': sim_spawner_service._npc_cap_modifier}
    return data
