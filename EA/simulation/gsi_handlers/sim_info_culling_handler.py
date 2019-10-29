from collections import namedtuplefrom gsi_handlers.gameplay_archiver import GameplayArchiverfrom sims.sim_info_lod import SimInfoLODLevelfrom sims4.gsi.schema import GsiGridSchema, GsiFieldVisualizersimport servicesCullingCensus = namedtuple('CullingCensus', ('player_households', 'player_sims', 'households', 'sims', 'lod_counts'))sim_info_culling_archive_schema = GsiGridSchema(label='SimInfo Culling Archive', sim_specific=False)sim_info_culling_archive_schema.add_field('game_time', label='Game/Sim Time', type=GsiFieldVisualizers.TIME, width=1)sim_info_culling_archive_schema.add_field('reason', label='Reason', width=2)sim_info_culling_archive_schema.add_field('player_households', label='#PlayerHouseholds', width=1)sim_info_culling_archive_schema.add_field('player_sims', label='#PlayerSimInfos', width=1)sim_info_culling_archive_schema.add_field('households', label='#Households', width=1)sim_info_culling_archive_schema.add_field('sims', label='#SimInfos', width=1)sim_info_culling_archive_schema.add_field('full', label='#FullLod', width=1)sim_info_culling_archive_schema.add_field('base', label='#BaseLod', width=1)sim_info_culling_archive_schema.add_field('minimum', label='#MinimumLod', width=1)with sim_info_culling_archive_schema.add_has_many('sim_infos_schema', GsiGridSchema, label='Sim Infos') as sub_schema:
    sub_schema.add_field('name', label='Name')
    sub_schema.add_field('score', label='Score', type=GsiFieldVisualizers.INT)
    sub_schema.add_field('info', label='Info')
    sub_schema.add_field('action', label='Action')
    sub_schema.add_field('rel_score', label='Relationship Score')
    sub_schema.add_field('inst_score', label='Instantiation Score')
    sub_schema.add_field('importance_score', label='Importance Score')with sim_info_culling_archive_schema.add_has_many('households_schema', GsiGridSchema, label='Households') as sub_schema:
    sub_schema.add_field('name', label='Name (ID)')
    sub_schema.add_field('score', label='Score', type=GsiFieldVisualizers.INT)
    sub_schema.add_field('info', label='Info')
    sub_schema.add_field('action', label='Action')archiver = GameplayArchiver('sim_info_culling', sim_info_culling_archive_schema, add_to_archive_enable_functions=True, enable_archive_by_default=True)
def is_archive_enabled():
    return archiver.enabled

class CullingArchive:

    def __init__(self, reason):
        self.reason = reason
        self.census_before = None
        self.census_after = None
        self.household_id_to_names = {}
        self.household_cullabilities = {}
        self.household_actions = {}
        self.sim_id_to_names = {}
        self.sim_info_cullabilities = {}
        self.sim_info_actions = {}

    def add_household_cullability(self, household, score=-1, info=''):
        if household.id not in self.household_id_to_names:
            self.household_id_to_names[household.id] = '{} ({})'.format(household.name, household.id)
        self.household_cullabilities[household.id] = (score, info)

    def add_household_action(self, household, action=''):
        if household.id not in self.household_id_to_names:
            self.household_id_to_names[household.id] = '{} ({})'.format(household.name, household.id)
        self.household_actions[household.id] = action

    def add_sim_info_cullability(self, sim_info, score=-1, info='', rel_score=None, inst_score=None, importance_score=None):
        if sim_info.id not in self.sim_id_to_names:
            self.sim_id_to_names[sim_info.id] = sim_info.full_name
        self.sim_info_cullabilities[sim_info.id] = (score, info, rel_score, inst_score, importance_score)

    def add_sim_info_action(self, sim_info, action=''):
        if sim_info.id not in self.sim_id_to_names:
            self.sim_id_to_names[sim_info.id] = sim_info.full_name
        self.sim_info_actions[sim_info.id] = action

    def apply(self):
        data = {'game_time': str(services.time_service().sim_now), 'reason': self.reason, 'player_households': '{} -> {}'.format(self.census_before.player_households, self.census_after.player_households), 'player_sims': '{} -> {}'.format(self.census_before.player_sims, self.census_after.player_sims), 'households': '{} -> {}'.format(self.census_before.households, self.census_after.households), 'sims': '{} -> {}'.format(self.census_before.sims, self.census_after.sims), 'full': '{} -> {}'.format(self.census_before.lod_counts[SimInfoLODLevel.FULL], self.census_after.lod_counts[SimInfoLODLevel.FULL]), 'base': '{} -> {}'.format(self.census_before.lod_counts[SimInfoLODLevel.BASE], self.census_after.lod_counts[SimInfoLODLevel.BASE]), 'minimum': '{} -> {}'.format(self.census_before.lod_counts[SimInfoLODLevel.MINIMUM], self.census_after.lod_counts[SimInfoLODLevel.MINIMUM])}
        data['sim_infos_schema'] = []
        for (sim_id, name) in self.sim_id_to_names.items():
            (score, info, rel_score, inst_score, importance_score) = self.sim_info_cullabilities.get(sim_id, (-1, ''))
            entry = {'name': name, 'score': score, 'info': info, 'action': self.sim_info_actions.get(sim_id, ''), 'rel_score': rel_score, 'inst_score': inst_score, 'importance_score': importance_score}
            data['sim_infos_schema'].append(entry)
        data['households_schema'] = []
        for (household_id, name) in self.household_id_to_names.items():
            (score, info) = self.household_cullabilities.get(household_id, (-1, 'error: unknown'))
            entry = {'name': name, 'score': score, 'info': info, 'action': self.household_actions.get(household_id, '')}
            data['households_schema'].append(entry)
        archiver.archive(data)
