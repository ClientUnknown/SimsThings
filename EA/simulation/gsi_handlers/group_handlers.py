from gsi_handlers.gameplay_archiver import GameplayArchiverfrom sims4.gsi.dispatcher import GsiHandlerfrom sims4.gsi.schema import GsiGridSchema, GsiFieldVisualizersimport servicesgroup_schema = GsiGridSchema(label='Social Groups')group_schema.add_field('type', label='Group Type', width=1, unique_field=True)group_schema.add_field('count', label='Count', type=GsiFieldVisualizers.INT, width=0.5)group_schema.add_field('anchor', label='Anchor', width=1)group_schema.add_field('shutting_down', label='Shutting Down', width=0.4)with group_schema.add_has_many('group_members', GsiGridSchema, label='Members') as sub_schema:
    sub_schema.add_field('sim_id', label='Sim ID', width=0.35)
    sub_schema.add_field('sim_name', label='Sim Name', width=0.4)
    sub_schema.add_field('registered_si', label='Registered SIs')
    sub_schema.add_field('social_context', label='Social Context')with group_schema.add_has_many('states', GsiGridSchema, label='States') as sub_schema:
    sub_schema.add_field('state', label='State', width=1)
    sub_schema.add_field('value', label='Value', width=1)with group_schema.add_has_many('constraints', GsiGridSchema, label='Constraint Info') as sub_schema:
    sub_schema.add_field('constraint_description', label='Key', width=1)
    sub_schema.add_field('constraint_data', label='Value', width=1)with group_schema.add_view_cheat('debugvis.socials.start', label='DebugVisStart', refresh_view=False) as cheat:
    cheat.add_token_param('sim_id')with group_schema.add_view_cheat('debugvis.socials.stop', label='DebugVisStop', refresh_view=False) as cheat:
    cheat.add_token_param('sim_id')with group_schema.add_view_cheat('sims.focus_camera_on_sim', label='Focus On Selected Sim', refresh_view=False) as cheat:
    cheat.add_token_param('sim_id')
@GsiHandler('social_groups', group_schema)
def generate_group_data():
    group_data = []
    for group in services.social_group_manager().values():
        entry = {'type': repr(group), 'count': len(group), 'shutting_down': 'x' if group.has_been_shutdown else '', 'anchor': str(getattr(group, '_anchor', None))}
        state_info = []
        entry['states'] = state_info
        if group.state_component is not None:
            for (state, value) in group.state_component.items():
                state_entry = {'state': str(state), 'value': str(value)}
                state_info.append(state_entry)
        members_info = []
        entry['group_members'] = members_info
        for sim in group:
            interactions = group._si_registry.get(sim)
            group_members_entry = {'sim_id': str(sim.id), 'sim_name': sim.full_name, 'registered_si': str(interactions), 'social_context': str(sim.get_social_context())}
            members_info.append(group_members_entry)
        constraint_info = []
        constraint_info.append({'constraint_description': 'Constraint', 'constraint_data': str(group._constraint)})
        geometry = [str(constraint.geometry) for constraint in group._constraint]
        constraint_info.append({'constraint_description': 'Constraint Geometry', 'constraint_data': ','.join(geometry)})
        entry['constraints'] = constraint_info
        group_data.append(entry)
    return group_data
group_log_schema = GsiGridSchema(label='Social Groups Log')group_log_schema.add_field('id', label='ID', width=1, unique_field=True)group_log_schema.add_field('type', label='Group Type', width=1)group_log_schema.add_field('count', label='Count', type=GsiFieldVisualizers.INT, width=0.5)group_log_schema.add_field('add/remove', label='Add/Remove', width=0.4)group_log_schema.add_field('shut_down', label='Shutdown', width=0.4)with group_log_schema.add_has_many('group_members', GsiGridSchema, label='Members') as sub_schema:
    sub_schema.add_field('sim_id', label='Sim ID', width=0.35)
    sub_schema.add_field('sim_name', label='Sim Name', width=0.4)
    sub_schema.add_field('registered_si', label='Registered SIs')
    sub_schema.add_field('social_context', label='Social Context')group_log_archiver = GameplayArchiver('group_log', group_log_schema, enable_archive_by_default=True)
def archive_group_message(group, add, shutdown):
    entry = {'id': group.id, 'type': repr(group), 'count': len(group), 'add/remove': add, 'shut_down': 'x' if shutdown else ''}
    members_info = []
    entry['group_members'] = members_info
    for sim in group:
        interactions = group._si_registry.get(sim)
        group_members_entry = {'sim_id': str(sim.id), 'sim_name': sim.full_name, 'registered_si': str(interactions), 'social_context': str(sim.get_social_context())}
        members_info.append(group_members_entry)
    group_log_archiver.archive(data=entry)
