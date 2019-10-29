from gsi_handlers.sim_handlers import _get_sim_info_by_idfrom sims4.gsi.dispatcher import GsiHandlerfrom sims4.gsi.schema import GsiGridSchemafamiliar_schema = GsiGridSchema(label='Familiars', sim_specific=True)familiar_schema.add_field('familiar_name', label='Name')familiar_schema.add_field('familiar_type', label='Type')familiar_schema.add_field('familiar_active', label='Active')
@GsiHandler('familiar_view', familiar_schema)
def generate_sim_skill_view_data(sim_id:int=None):
    familiar_data = []
    cur_sim_info = _get_sim_info_by_id(sim_id)
    if cur_sim_info is not None:
        familiar_tracker = cur_sim_info.familiar_tracker
        if familiar_tracker is not None:
            active_familiar_id = familiar_tracker.active_familiar_id
            for familiar_info in familiar_tracker:
                if active_familiar_id is None:
                    familiar_active = False
                else:
                    familiar_active = familiar_info.uid == active_familiar_id
                entry = {'familiar_name': familiar_info.raw_name, 'familiar_type': str(familiar_info.familiar_type), 'familiar_active': str(familiar_active)}
                familiar_data.append(entry)
    return familiar_data
