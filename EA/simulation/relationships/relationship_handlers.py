from sims4.gsi.dispatcher import GsiHandlerfrom sims4.gsi.schema import GsiGridSchema, GsiFieldVisualizersfrom sims4.resources import Typesimport services
def _get_sim_info_by_id(sim_id):
    sim_info_manager = services.sim_info_manager()
    sim_info = None
    if sim_info_manager is not None:
        sim_info = sim_info_manager.get(sim_id)
    return sim_info

def generate_all_rel_bits():
    instance_manager = services.get_instance_manager(Types.RELATIONSHIP_BIT)
    if instance_manager.all_instances_loaded:
        return [cls.__name__ for cls in instance_manager.types.values()]
    else:
        return []
relationship_schema = GsiGridSchema(label='Relationships', sim_specific=True)relationship_schema.add_field('relationship_id', label='Rel ID', hidden=True, unique_field=True)relationship_schema.add_field('sim_name', label='Sim Name')relationship_schema.add_field('depth', label='Depth', type=GsiFieldVisualizers.FLOAT)relationship_schema.add_field('prevailing_stc', label='Prevailing STC')relationship_schema.add_field('sim_id', label='Sim Id', hidden=True)
def add_rel_bit_cheats(manager):
    with relationship_schema.add_view_cheat('relationship.add_bit', label='Add Bit') as cheat:
        cheat.add_token_param('sim_id')
        cheat.add_token_param('target_id')
        cheat.add_token_param('bit_string', dynamic_token_fn=generate_all_rel_bits)
services.get_instance_manager(Types.RELATIONSHIP_BIT).add_on_load_complete(add_rel_bit_cheats)with relationship_schema.add_has_many('tracks', GsiGridSchema, label='Tracks') as sub_schema:
    sub_schema.add_field('type', label='Track')
    sub_schema.add_field('score', label='Score', type=GsiFieldVisualizers.FLOAT)
    sub_schema.add_field('decay', label='Decay', type=GsiFieldVisualizers.FLOAT)
    sub_schema.add_field('bits', label='Bit')with relationship_schema.add_has_many('all_bits', GsiGridSchema, label='All Bits') as sub_schema:
    sub_schema.add_field('raw_bit', label='Bit')with relationship_schema.add_has_many('track_listeners', GsiGridSchema, label='Track Callbacks') as sub_schema:
    sub_schema.add_field('track_name', label='Track')
    sub_schema.add_field('callback_info', label='Callback Info')with relationship_schema.add_has_many('relationship_bit_locks', GsiGridSchema, label='Relationship Bit Locks') as sub_schema:
    sub_schema.add_field('lock', label='Lock')
    sub_schema.add_field('lock_group', label='Lock Group')
    sub_schema.add_field('lock_end_time', label='Lock End Time')
@GsiHandler('relationship_view', relationship_schema)
def generate_relationship_view_data(sim_id:int=None):
    rel_data = []
    sim_info_manager = services.sim_info_manager()
    if sim_info_manager is None:
        return rel_data
    relationship_service = services.relationship_service()
    sim_info = sim_info_manager.get(sim_id)
    for rel in relationship_service.get_all_sim_relationships(sim_id):
        target_sim_info = _get_sim_info_by_id(rel.get_other_sim_id(sim_id))
        entry = {'relationship_id': str(rel.get_other_sim_id(sim_id)), 'depth': rel.get_relationship_depth(sim_id), 'prevailing_stc': str(rel.get_prevailing_short_term_context_track()), 'sim_id': str(sim_info.sim_id)}
        if target_sim_info is not None:
            entry['sim_name'] = target_sim_info.full_name
        entry['tracks'] = []
        callback_info = []
        for track in rel.relationship_track_tracker:
            track_name = track.__class__.__name__
            track_entry = {'type': track_name, 'score': track.get_user_value(), 'decay': track.get_decay_rate()}
            active_bit = track.get_active_bit()
            if active_bit is not None:
                track_entry['bits'] = active_bit.__name__
            for callback_listener in track._statistic_callback_listeners:
                callback_info.append({'track_name': track_name, 'callback_info': str(callback_listener)})
            entry['tracks'].append(track_entry)
        entry['track_listeners'] = callback_info
        entry['all_bits'] = []
        for bit in rel.get_bits(sim_id):
            entry['all_bits'].append({'raw_bit': bit.__name__})
        entry['relationship_bit_locks'] = []
        for rel_lock in rel.get_all_relationship_bit_locks(sim_id):
            entry['relationship_bit_locks'].append({'lock': str(rel_lock), 'lock_group': str(rel_lock.group_id), 'lock_end_time': str(rel_lock.end_time)})
        rel_data.append(entry)
    for rel in relationship_service.get_all_sim_object_relationships(sim_id):
        obj_def = rel.find_member_obj_b()
        entry = {'relationship_id': str(rel.sim_id_b), 'depth': rel.get_relationship_depth(sim_id), 'sim_id': str(sim_info.sim_id)}
        if obj_def is not None:
            name = rel.get_object_rel_name()
            if name is not None:
                entry['sim_name'] = f'{obj_def}: {name}'
            else:
                entry['sim_name'] = str(obj_def)
        entry['tracks'] = []
        callback_info = []
        for track in rel.relationship_track_tracker:
            track_name = track.__class__.__name__
            track_entry = {'type': track_name, 'score': track.get_user_value(), 'decay': track.get_decay_rate()}
            active_bit = track.get_active_bit()
            if active_bit is not None:
                track_entry['bits'] = active_bit.__name__
            for callback_listener in track._statistic_callback_listeners:
                callback_info.append({'track_name': track_name, 'callback_info': str(callback_listener)})
            entry['tracks'].append(track_entry)
        entry['track_listeners'] = callback_info
        entry['all_bits'] = []
        for bit in rel.get_bits(sim_id):
            entry['all_bits'].append({'raw_bit': bit.__name__})
        entry['relationship_bit_locks'] = []
        for rel_lock in rel.get_all_relationship_bit_locks(sim_id):
            entry['relationship_bit_locks'].append({'lock': str(rel_lock), 'lock_group': str(rel_lock.group_id), 'lock_end_time': str(rel_lock.end_time)})
        entry['object_relationship'] = []
        rel_data.append(entry)
    return rel_data
