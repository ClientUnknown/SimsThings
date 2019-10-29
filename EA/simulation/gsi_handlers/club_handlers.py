from clubs.club_enums import ClubHangoutSettingfrom sims4.gsi.dispatcher import GsiHandlerfrom sims4.gsi.schema import GsiGridSchema, GsiFieldVisualizersimport servicesimport sims4.resourcesclub_schema = GsiGridSchema(label='Club Info')club_schema.add_field('name', label='Name', type=GsiFieldVisualizers.STRING)club_schema.add_field('club_id', label='Club ID', type=GsiFieldVisualizers.STRING, unique_field=True)club_schema.add_field('hangout', label='Hangout Location', type=GsiFieldVisualizers.STRING)club_schema.add_field('associated_color', label='Associated Color', type=GsiFieldVisualizers.STRING)club_schema.add_field('uniform_male_child', label='Male Child Uniform', type=GsiFieldVisualizers.STRING)club_schema.add_field('uniform_female_child', label='Female Child Uniform', type=GsiFieldVisualizers.STRING)club_schema.add_field('uniform_male_adult', label='Male Adult Uniform', type=GsiFieldVisualizers.STRING)club_schema.add_field('uniform_female_adult', label='Female Child Uniform', type=GsiFieldVisualizers.STRING)
def generate_all_club_seeds():
    instance_manager = services.get_instance_manager(sims4.resources.Types.CLUB_SEED)
    if instance_manager.all_instances_loaded:
        return [cls.__name__ for cls in instance_manager.types.values()]
    return []

def add_club(manager):
    with club_schema.add_view_cheat('clubs.create_club_from_seed', label='Create Club') as cheat:
        cheat.add_token_param('club_seed', dynamic_token_fn=generate_all_club_seeds)
services.get_instance_manager(sims4.resources.Types.CLUB_SEED).add_on_load_complete(add_club)with club_schema.add_view_cheat('clubs.remove_club_by_id', label='Remove Club') as cheat:
    cheat.add_token_param('club_id')with club_schema.add_view_cheat('clubs.remove_sim_from_club_by_id', label='Remove Sim From Club') as cheat:
    cheat.add_token_param('sim_id')
    cheat.add_token_param('club_id')with club_schema.add_view_cheat('clubs.end_gathering_by_club_id', label='End Club Gathering') as cheat:
    cheat.add_token_param('club_id')with club_schema.add_view_cheat('clubs.start_gathering_by_club_id', label='Start Gathering') as cheat:
    cheat.add_token_param('club_id')with club_schema.add_view_cheat('clubs.refresh_safe_seed_data_for_club', label='Refresh Safe Data') as cheat:
    cheat.add_token_param('club_id')
def get_buck_amounts():
    return (1, 10, 100, 1000)
with club_schema.add_view_cheat('bucks.update_bucks_by_amount', label='Add Club Bucks') as cheat:
    cheat.add_static_param('ClubBucks')
    cheat.add_token_param('amount', dynamic_token_fn=get_buck_amounts)
    cheat.add_token_param('club_id')with club_schema.add_has_many('club_members', GsiGridSchema, label='Club Members') as sub_schema:
    sub_schema.add_field('sim_id', label='Sim ID', width=0.35)
    sub_schema.add_field('sim_name', label='Sim Name', width=0.4)
    sub_schema.add_field('is_leader', label='Is Leader')with club_schema.add_has_many('club_recent_members', GsiGridSchema, label='Recent Members') as sub_schema:
    sub_schema.add_field('sim_id', label='Sim ID', width=0.35)
    sub_schema.add_field('sim_name', label='Sim Name', width=0.4)with club_schema.add_has_many('club_rules', GsiGridSchema, label='Club Rules') as sub_schema:
    sub_schema.add_field('rule', label='Rule')with club_schema.add_has_many('membership_criteria', GsiGridSchema, label='Membership Criteria') as sub_schema:
    sub_schema.add_field('criteria', label='Criteria')
@GsiHandler('club_info', club_schema)
def generate_club_info_data():
    club_service = services.get_club_service()
    if club_service is None:
        return
    sim_info_manager = services.sim_info_manager()
    club_info = []
    for club in club_service.clubs:
        if club.hangout_setting == ClubHangoutSetting.HANGOUT_VENUE:
            club_hangout_str = 'Venue: {}'.format(str(club.hangout_venue))
        elif club.hangout_setting == ClubHangoutSetting.HANGOUT_LOT:
            club_hangout_str = 'Zone: {}'.format(club.hangout_zone_id)
        else:
            club_hangout_str = 'None'
        entry = {'name': str(club), 'club_id': str(club.club_id), 'hangout': club_hangout_str, 'associated_color': str(club.associated_color) if club.associated_color else 'None', 'uniform_male_child': str(bool(club.uniform_male_child)), 'uniform_female_child': str(bool(club.uniform_female_child)), 'uniform_male_adult': str(bool(club.uniform_male_adult)), 'uniform_female_adult': str(bool(club.uniform_female_adult))}
        members_info = []
        entry['club_members'] = members_info
        for sim in club.members:
            group_members_entry = {'sim_id': str(sim.id), 'sim_name': sim.full_name, 'is_leader': str(sim is club.leader)}
            members_info.append(group_members_entry)
        entry['club_recent_members'] = [{'sim_id': str(sim_id), 'sim_name': str(sim_info_manager.get(sim_id))} for sim_id in club._recent_member_ids]
        rules_info = []
        entry['club_rules'] = rules_info
        if club.rules:
            for rule in club.rules:
                rules_entry = {'rule': str(rule)}
                rules_info.append(rules_entry)
        criteria_info = []
        entry['membership_criteria'] = criteria_info
        if club.membership_criteria:
            for criteria in club.membership_criteria:
                criteria_entry = {'criteria': str(criteria)}
                criteria_info.append(criteria_entry)
        club_info.append(entry)
    return club_info
