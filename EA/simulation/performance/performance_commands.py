from _collections import defaultdictfrom collections import Counter, namedtuplefrom itertools import combinationsfrom numbers import Numberimport collectionsfrom adaptive_clock_speed import AdaptiveClockSpeedfrom clock import ClockSpeedMultiplierType, ClockSpeedModefrom gsi_handlers.performance_handlers import generate_statisticsfrom indexed_manager import object_load_timesfrom interactions.utils.death import DeathTypefrom objects.components.types import STATE_COMPONENTfrom relationships.relationship_enums import RelationshipBitCullingPrevention, RelationshipDecayMetricKeys, RelationshipDirectionfrom server_commands.autonomy_commands import show_queue, autonomy_distance_estimates_enable, autonomy_distance_estimates_dumpfrom server_commands.cache_commands import cache_statusfrom sims.household_telemetry import HouseholdRegionTelemetryDatafrom sims.occult.occult_enums import OccultTypefrom sims.sim_info_lod import SimInfoLODLevelfrom sims4.commands import CommandTypefrom sims4.profiler_utils import create_custom_named_profiler_functionfrom sims4.tuning.tunable import Tunablefrom sims4.utils import create_csvfrom singletons import UNSETfrom story_progression.story_progression_action_relationship_culling import StoryProgressionRelationshipCullingimport autonomy.autonomy_utilimport enumimport event_testingimport indexed_managerimport performance.performance_constants as constsimport servicesimport sims4.commandsPOINTS_PER_INTERACTION = -0.00513POINTS_PER_AUTONOMOUS_INTERACTION = 0.007287POINTS_PER_PROVIDED_POSTURE_INTERACTION = 0.079084POINTS_PER_CLIENT_STATE_TUNING = 0.02182POINTS_PER_CLIENT_STATE_CHANGE_TUNING = -0.01336POINTS_PER_OBJECT_PART = -0.04883POINTS_PER_STATISTIC = 0POINTS_PER_COMMODITY = 0CLIENT_STATE_OPS_TO_IGNORE = ['autonomy_modifiers']RelationshipMetrics = namedtuple('RelationshipMetrics', ('rels', 'rels_active', 'rels_played', 'rels_unplayed', 'rel_bits_one_way', 'rel_bits_bi', 'rel_tracks'))
@sims4.commands.Command('performance.log_alarms')
def log_alarms(enabled:bool=True, check_cooldown:bool=True, _connection=None):
    services.current_zone().alarm_service._log = enabled
    return True

@sims4.commands.Command('performance.log_object_statistics', command_type=CommandType.Automation)
def log_object_statistics(outputFile=None, _connection=None):
    result = generate_statistics()
    if outputFile is not None:
        cheat_output = sims4.commands.FileOutput(outputFile, _connection)
    else:
        cheat_output = sims4.commands.CheatOutput(_connection)
    automation_output = sims4.commands.AutomationOutput(_connection)
    automation_output('PerfLogObjStats; Status:Begin')
    for (name, value) in result:
        sims4.commands.output('{:40} : {:5}'.format(name, value), _connection)
        eval_value = eval(value)
        if isinstance(eval_value, Number):
            automation_output('PerfLogObjStats; Status:Data, Name:{}, Value:{}'.format(name, value))
            cheat_output('{} : {}'.format(name, value))
        elif isinstance(eval_value, (list, tuple)):
            automation_output('PerfLogObjStats; Status:ListBegin, Name:{}'.format(name))
            cheat_output('Name : {}'.format(name))
            for obj_freq in eval_value:
                object_name = obj_freq.get('name')
                frequency = obj_freq.get('frequency')
                automation_output('PerfLogObjStats; Status:ListData, Name:{}, Frequency:{}'.format(object_name, frequency))
                cheat_output('{} : {}'.format(object_name, frequency))
            automation_output('PerfLogObjStats; Status:ListEnd, Name:{}'.format(name))
        cheat_output('\n')
    automation_output('PerfLogObjStats; Status:End')

@sims4.commands.Command('performance.log_object_statistics_summary', command_type=CommandType.Automation)
def log_object_statistics_summary(_connection=None):
    result = generate_statistics()
    (nodes, edges) = services.current_zone().posture_graph_service.get_nodes_and_edges()
    result.append((consts.POSTURE_GRAPH_NODES, nodes))
    result.append((consts.POSTURE_GRAPH_EDGES, edges))
    output = sims4.commands.CheatOutput(_connection)
    f = '{:50} : {:5} : {:5}'
    output(f.format('Metric', 'Value', 'Budget'))
    ignore = set([x for x in consts.OBJECT_CLASSIFICATIONS])
    ignore.add(consts.TICKS_PER_SECOND)
    ignore.add(consts.COUNT_PROPS)
    ignore.add(consts.COUNT_OBJECTS_PROPS)
    for (name, value) in result:
        if name in ignore:
            pass
        else:
            budget = consts.BUDGETS.get(name, '')
            output(f.format(name, value, budget))
    output('\nDetailed info in GSI: Performance Metrics panel, |performance.log_object_statistics, |performance.posture_graph_summary, RedDwarf: World Coverage Report')

@sims4.commands.Command('performance.add_automation_profiling_marker', command_type=CommandType.Automation)
def add_automation_profiling_marker(message:str='Unspecified', _connection=None):
    name_f = create_custom_named_profiler_function(message)
    return name_f(lambda : None)

class SortStyle(enum.Int, export=False):
    ALL = 0
    AVERAGE_TIME = 1
    TOTAL_TIME = 2
    COUNT = 3

@sims4.commands.Command('performance.test_profile.dump', command_type=CommandType.Automation)
def dump_tests_profile(sort:SortStyle=SortStyle.ALL, _connection=None):
    output = sims4.commands.CheatOutput(_connection)
    if event_testing.resolver.test_profile is None:
        output('Test profiling is currently disabled. Use |performance.test_profile.enable')
        return
    if len(event_testing.resolver.test_profile) == 0:
        output('Test profiling is currently enabled but has no records.')
        return

    def get_sort_style(metric):
        if sort == SortStyle.AVERAGE_TIME:
            return metric.get_average_time()
        if sort == SortStyle.TOTAL_TIME:
            return metric.get_total_time()
        elif sort == SortStyle.COUNT:
            return metric.count

    TIME_MULTIPLIER = 1000

    def test_callback(file):
        file.write('Test,Count,AverageTime(ms),TotalTime(ms),Resolver,Key,Count,AverageTime(ms),TotalTime(ms)\n')
        for (test_name, test_metrics) in sorted(event_testing.resolver.test_profile.items(), key=lambda t: get_sort_style(t[1].metrics), reverse=True):
            file.write('{},{},{},{},,,,,\n'.format(test_name, test_metrics.metrics.count, test_metrics.metrics.get_average_time()*TIME_MULTIPLIER, test_metrics.metrics.get_total_time()*TIME_MULTIPLIER))
            for resolver in sorted(test_metrics.resolvers.keys()):
                data = test_metrics.resolvers[resolver]
                for (key, metrics) in sorted(data.items(), key=lambda t: get_sort_style(t[1]), reverse=True):
                    if metrics.get_average_time() > 0:
                        file.write(',,,,{},{},{},{},{}\n'.format(resolver, key, metrics.count, metrics.get_average_time()*TIME_MULTIPLIER, metrics.get_total_time()*TIME_MULTIPLIER))

    def create_test_view(sort_style):
        if sort_style != SortStyle.ALL:
            filename = 'test_profile_' + str(sort_style).replace('.', '_')
            create_csv(filename, callback=test_callback, connection=_connection)

    interactions = defaultdict(list)

    def interaction_callback(file):
        file.write('Interaction,TotalTime(ms),Test,Count,AverageTime(ms),AverageResolveTime(ms),TotalTime(ms)\n')
        for (iname, tests) in sorted(interactions.items(), reverse=True, key=lambda t: sum(m.get_total_time(include_test_set=False) for (_, m) in t[1])):
            file.write('{},{},,,,,\n'.format(iname, sum(m.get_total_time(include_test_set=False) for (_, m) in tests)*TIME_MULTIPLIER))
            for (test, met) in sorted(tests, reverse=True, key=lambda t: (not t[1].is_test_set, t[1].get_total_time())):
                file.write(',,{},{},{},{},{}\n'.format(test, met.count, met.get_average_time()*TIME_MULTIPLIER, met.resolve_time*TIME_MULTIPLIER/met.count, met.get_total_time()*TIME_MULTIPLIER))

    def create_interaction_view():
        for (tname, tmetrics) in event_testing.resolver.test_profile.items():
            interaction_resolver = tmetrics.resolvers.get('InteractionResolver')
            if interaction_resolver is None:
                pass
            else:
                for (interaction, metrics) in interaction_resolver.items():
                    interactions[interaction].append((tname, metrics))
        filename = 'test_profile_interactions'
        create_csv(filename, callback=interaction_callback, connection=_connection)

    sim_resolvers = defaultdict(list)

    def sim_resolver_callback(file):
        file.write('ResolverInfo,TotalTime(ms),Test,Count,AverageTime(ms),TotalTime(ms)\n')
        for (rname, tests) in sorted(sim_resolvers.items(), reverse=True, key=lambda t: sum(m.get_total_time(include_test_set=False) for (_, m) in t[1])):
            file.write('{},{},,,,\n'.format(rname, sum(m.get_total_time(include_test_set=False) for (_, m) in tests)*TIME_MULTIPLIER))
            for (test, met) in sorted(tests, reverse=True, key=lambda t: (not t[1].is_test_set, t[1].get_total_time())):
                file.write(',,{},{},{},{}\n'.format(test, met.count, met.get_average_time()*TIME_MULTIPLIER, met.get_total_time()*TIME_MULTIPLIER))

    def create_sim_resolver_view():
        for (tname, tmetrics) in event_testing.resolver.test_profile.items():
            datum_prefix = 'SingleSimResolver:'
            sim_resolver = tmetrics.resolvers.get('SingleSimResolver')
            if sim_resolver is None:
                datum_prefix = 'DoubleSimResolver:'
                sim_resolver = tmetrics.resolvers.get('DoubleSimResolver')
            if sim_resolver is None:
                pass
            else:
                for (resolver_datum, metrics) in sim_resolver.items():
                    sim_resolvers[datum_prefix + resolver_datum].append((tname, metrics))
        filename = 'test_profile_sim_resolvers'
        create_csv(filename, callback=sim_resolver_callback, connection=_connection)

    if sort == SortStyle.ALL:
        for sort in SortStyle.values:
            create_test_view(sort)
    else:
        create_test_view(sort)
    create_interaction_view()
    create_sim_resolver_view()

@sims4.commands.Command('performance.test_profile.dump_resolver', command_type=CommandType.Automation)
def dump_test_resolver_profiles(_connection=None):
    TIME_MULTIPLIER = 1000

    def average_time(time, count):
        if time == 0 or count == 0:
            return 0
        return time*TIME_MULTIPLIER/count

    resolver_types = set()
    for (test_name, test_metrics) in event_testing.resolver.test_profile.items():
        resolver_types |= test_metrics.resolvers.keys()
    resolver_types = list(resolver_types)
    resolver_types.sort()

    def callback(file):
        file.write('Test,Count,AvgTime,ResolveTime,TestTime,{}\n'.format(','.join('{}Count,{}'.format(x, x) for x in resolver_types)))
        for (test_name, test_metrics) in event_testing.resolver.test_profile.items():
            metrics = test_metrics.metrics
            file.write('{},{},{},{},{}'.format(test_name, metrics.count, average_time(metrics.get_total_time(), metrics.count), average_time(metrics.resolve_time, metrics.count), average_time(metrics.test_time, metrics.count)))
            for resolver_type in resolver_types:
                sub_metrics = test_metrics.resolvers.get(resolver_type)
                if sub_metrics is None:
                    file.write(',,')
                else:
                    count = sum(m.count for m in sub_metrics.values())
                    resolve_time = sum(m.resolve_time for m in sub_metrics.values())
                    file.write(',{},{}'.format(count, average_time(resolve_time, count)))
            file.write('\n')

    filename = 'test_resolver_profile'
    create_csv(filename, callback=callback, connection=_connection)

@sims4.commands.Command('performance.test_profile.enable', command_type=CommandType.Automation)
def enable_test_profile(_connection=None):
    event_testing.resolver.test_profile = dict()
    output = sims4.commands.CheatOutput(_connection)
    output('Test profiling enabled. Dump the profile any time using performance.test_profile.dump')

@sims4.commands.Command('performance.test_profile.disable', command_type=CommandType.Automation)
def disable_test_profile(_connection=None):
    event_testing.resolver.test_profile = None
    output = sims4.commands.CheatOutput(_connection)
    output('Test profiling disabled.')

@sims4.commands.Command('performance.test_profile.clear', command_type=CommandType.Automation)
def clear_tests_profile(_connection=None):
    if event_testing.resolver.test_profile is not None:
        event_testing.resolver.test_profile.clear()
    output = sims4.commands.CheatOutput(_connection)
    output('Test profile metrics have been cleared.')

@sims4.commands.Command('performance.print_player_household_metrics', command_type=CommandType.Automation)
def player_household_metrics(_connection=None):
    output = sims4.commands.CheatOutput(_connection)
    (active_sim_count, player_sim_count, played_sim_count) = (0, 0, 0)
    (active_household_count, player_household_count, played_household_count) = (0, 0, 0)
    households = services.household_manager().get_all()
    for household in households:
        if household.is_active_household:
            active_household_count += 1
            active_sim_count += len(household)
        if household.is_player_household:
            player_household_count += 1
            player_sim_count += len(household)
        if household.is_played_household:
            played_household_count += 1
            played_sim_count += len(household)
    for (name, value) in (('#sim_infos', len(services.sim_info_manager())), ('#active sim_infos', active_sim_count), ('#player sim_infos', player_sim_count), ('#played sim_infos', played_sim_count), ('#households', len(households)), ('#active households', active_household_count), ('#player households', player_household_count), ('#played households', played_household_count)):
        output('{:50} : {}'.format(name, value))
    return True

def get_relationship_decay_metrics(output=None):
    total_relationships = 0
    metrics = defaultdict(Counter)
    for (x, y) in combinations(services.sim_info_manager().values(), 2):
        x_y = x.relationship_tracker.relationship_decay_metrics(y.id)
        y_x = y.relationship_tracker.relationship_decay_metrics(x.id)
        decay_metrics = x_y if x_y is not None else y_x
        if decay_metrics is not None:
            active_counter = None
            total_relationships += 1
            if not (x.is_npc and y.is_npc):
                active_counter = metrics['active']
            elif x.is_played_sim or y.is_played_sim:
                active_counter = metrics['played']
            else:
                active_counter = metrics['unplayed']
            if active_counter is None:
                pass
            else:
                active_counter += decay_metrics
                active_counter[RelationshipDecayMetricKeys.RELS] += 1
                long_term_tracks_decaying = decay_metrics[RelationshipDecayMetricKeys.LONG_TERM_TRACKS_DECAYING]
                if long_term_tracks_decaying > 0:
                    active_counter[RelationshipDecayMetricKeys.RELS_WITH_DECAY] += 1
    return (total_relationships, metrics)

@sims4.commands.Command('performance.relationship_decay_metrics')
def print_relationship_decay_metrics(long_version:bool=False, _connection=None):
    output = sims4.commands.CheatOutput(_connection)
    (total_tracks, metrics) = get_relationship_decay_metrics(output=output)
    output('TOTAL_RELS = {:10}'.format(total_tracks))
    for (status, metric) in metrics.items():
        long_term_tracks = metric[RelationshipDecayMetricKeys.LONG_TERM_TRACKS]
        short_term_tracks = metric[RelationshipDecayMetricKeys.LONG_TERM_TRACKS]
        long_term_tracks_decaying = metric[RelationshipDecayMetricKeys.LONG_TERM_TRACKS_DECAYING]
        short_term_tracks_decaying = metric[RelationshipDecayMetricKeys.SHORT_TERM_TRACKS_DECAYING]
        long_term_tracks_decaying_at_convergence = metric[RelationshipDecayMetricKeys.LONG_TERM_TRACKS_AT_CONVERGENCE]
        short_term_tracks_decaying_at_convergence = metric[RelationshipDecayMetricKeys.SHORT_TERM_TRACKS_AT_CONVERGENCE]
        if not long_version:
            output('{:30} : {:5} : #decaying:{:4}: #tracks:{:4} : #tracks_decaying:{:4} : #tracks_at_convergence:{:4}'.format(str(status), metric[RelationshipDecayMetricKeys.RELS], metric[RelationshipDecayMetricKeys.RELS_WITH_DECAY], long_term_tracks + short_term_tracks, long_term_tracks_decaying + short_term_tracks_decaying, long_term_tracks_decaying_at_convergence + short_term_tracks_decaying_at_convergence))
        else:
            output('{:30} : {:5} : #decaying:{:4}: #tracks:{:4} : #tracks_decaying:{:4} : #tracks_at_convergence:{:4}: #long_term:{:4} : #long_term_decaying:{:4} : #long_term_at_convergence:{:4}: #short_term:{:4} : #short_term_decaying:{:4} : #short_term_at_convergence:{:4}'.format(str(status), metric[RelationshipDecayMetricKeys.RELS], metric[RelationshipDecayMetricKeys.RELS_WITH_DECAY], long_term_tracks + short_term_tracks, long_term_tracks_decaying + short_term_tracks_decaying, long_term_tracks_decaying_at_convergence + short_term_tracks_decaying_at_convergence, long_term_tracks, long_term_tracks_decaying, long_term_tracks_decaying_at_convergence, short_term_tracks, short_term_tracks_decaying, short_term_tracks_decaying_at_convergence))
    return metrics

@sims4.commands.Command('performance.relationship_object_per_sim')
def dump_relationship_object_information_per_sim(_connection=None):

    def callback(file):
        entries = []
        active_rel_objs = 0
        playable_rel_objs = 0
        unplayed_rel_obj = 0
        one_way_rel_obj = 0
        for x in services.sim_info_manager().values():
            total_rels = 0
            household_rels = 0
            rels_can_be_culled = 0
            rels_decaying = 0
            rels_target_unplayable = 0
            family_rels = 0
            rels_with_no_long_term_tracks = 0
            rels_target_playable = 0
            rels_target_active = 0
            for relationship in x.relationship_tracker:
                total_rels += 1
                decay_information = x.relationship_tracker.relationship_decay_metrics(relationship.get_other_sim_id(x.sim_id))
                if decay_information is not None:
                    (decay_enabled, _, possible_tracks_decaying, _) = decay_information
                    if decay_enabled:
                        rels_decaying += 1
                    elif possible_tracks_decaying == 0:
                        rels_with_no_long_term_tracks += 1
                target_sim_info = relationship.get_other_sim_info(x.sim_id)
                if target_sim_info is not None:
                    if target_sim_info.household_id == x.household_id:
                        household_rels += 1
                    elif any(bit.relationship_culling_prevention == RelationshipBitCullingPrevention.PLAYED_AND_UNPLAYED for bit in relationship._bits.values()):
                        family_rels += 1
                    else:
                        rels_can_be_culled += 1
                    if not target_sim_info.is_npc:
                        rels_target_active += 1
                    elif target_sim_info.is_played_sim:
                        rels_target_playable += 1
                    else:
                        rels_target_unplayable += 1
                    if not (x.is_npc and target_sim_info.is_npc):
                        active_rel_objs += 1
                    elif x.is_played_sim or target_sim_info.is_played_sim:
                        playable_rel_objs += 1
                    else:
                        unplayed_rel_obj += 1
                else:
                    one_way_rel_obj += 1
            entries.append('a{},{},{},{},{},{},{},{},{},{},{},{},{}\n'.format(x.id, x.first_name, x.last_name, total_rels, rels_can_be_culled, household_rels, family_rels, rels_target_active, rels_target_playable, rels_target_unplayable, rels_decaying, rels_with_no_long_term_tracks))
        total_rel_objects = active_rel_objs + playable_rel_objs + unplayed_rel_obj + one_way_rel_obj
        file.write('Metrics\n')
        file.write('#relationship python objs:,{}\n'.format(total_rel_objects))
        file.write('#relationships one way objects:,{}\n'.format(one_way_rel_obj))
        file.write('#relationships active objects:,{}\n'.format(active_rel_objs))
        file.write('#relationships played objects:,{}\n'.format(playable_rel_objs))
        file.write('#relationships unplayed objects:,{}\n\n'.format(unplayed_rel_obj))
        file.write('SimID,FirstName,LastName,Played,RelationshipObjects,#Cullable,HouseholdConnected,BitPreventingCulling,WithActive,WithPlayable,WithUnplayayble,#Decaying,#NoLongTermTracks\n')
        for row_entry in entries:
            file.write(row_entry)

    create_csv('relationship_objects_per_sim', callback=callback, connection=_connection)

def get_relationship_metrics(output=None):
    rels = 0
    rels_active = 0
    rels_played = 0
    rels_unplayed = 0
    rel_bits_one_way = 0
    rel_bits_bi = 0
    rel_tracks = 0
    rel_service = services.relationship_service()
    for relationship in rel_service:
        x = relationship.find_sim_info_a()
        x_id = x.sim_id
        y = relationship.find_sim_info_b()
        y_id = y.sim_id
        x_bits = set(relationship.get_bits(x_id))
        y_bits = set(relationship.get_bits(y_id))
        rel_bits_bi += sum(1 for bit in x_bits if bit.directionality == RelationshipDirection.BIDIRECTIONAL)
        rel_bits_one_way += sum(1 for bit in x_bits if bit.directionality == RelationshipDirection.UNIDIRECTIONAL) + sum(1 for bit in y_bits if bit.directionality == RelationshipDirection.UNIDIRECTIONAL)
        rel_tracks += len(relationship.relationship_track_tracker)
        rels += 1
        if not (x.is_npc and y.is_npc):
            rels_active += 1
        elif x.is_played_sim or y.is_played_sim:
            rels_played += 1
        else:
            rels_unplayed += 1
    return RelationshipMetrics(rels, rels_active, rels_played, rels_unplayed, rel_bits_one_way, rel_bits_bi, rel_tracks)

@sims4.commands.Command('performance.relationship_status', command_type=CommandType.Automation)
def relationship_status(_connection=None):
    output = sims4.commands.CheatOutput(_connection)
    metrics = get_relationship_metrics(output=output)
    dump = []
    dump.append(('#relationships', metrics.rels))
    dump.append(('#relationships active sims', metrics.rels_active))
    dump.append(('#relationships played sims', metrics.rels_played))
    dump.append(('#relationships unplayed sims', metrics.rels_unplayed))
    dump.append(('#relationships rel bits one-way', metrics.rel_bits_one_way))
    dump.append(('#relationships rel bits bi-directional', metrics.rel_bits_bi))
    dump.append(('#relationships rel tracks', metrics.rel_tracks))
    for (name, value) in dump:
        output('{:40} : {}'.format(name, value))
    return dump

def get_sim_info_creation_sources():
    counter = Counter()
    for sim_info in services.sim_info_manager().values():
        counter[str(sim_info.creation_source)] += 1
    return counter

@sims4.commands.Command('performance.print_sim_info_creation_sources', command_type=CommandType.Automation)
def print_sim_info_creation_sources(_connection=None):
    counter = get_sim_info_creation_sources()
    output = sims4.commands.CheatOutput(_connection)
    automation_output = sims4.commands.AutomationOutput(_connection)
    output('Total sim_infos: {}'.format(sum(counter.values())))
    output('--------------------')
    automation_output('SimInfoPerformance; Status:Begin, TotalSimInfos:{}'.format(sum(counter.values())))
    for (source, count) in counter.most_common():
        automation_source = source
        if source == '':
            source = 'Unknown - Is empty string'
            automation_source = 'Unknown'
        output('{:100} : {}'.format(source, count))
        if ': ' in automation_source:
            automation_source = automation_source.replace(': ', '(') + ')'
        automation_output('SimInfoPerformance; Status:Data, Source:{}, Count:{}'.format(automation_source, count))
    automation_output('SimInfoPerformance; Status:End')
    return counter

@sims4.commands.Command('performance.print_census_report', command_type=CommandType.Automation)
def print_census_report(_connection=None):
    age = Counter()
    gender = Counter()
    ghost = Counter()
    occult = Counter()
    lod = Counter()
    sim_types = Counter()
    household_types = Counter()
    output = sims4.commands.CheatOutput(_connection)
    for sim_info in services.sim_info_manager().values():
        age[sim_info.age] += 1
        gender[sim_info.gender] += 1
        if sim_info.is_ghost:
            death_type = sim_info.death_tracker._death_type
            if death_type is not None:
                ghost[DeathType(death_type)] += 1
            else:
                output('{} is a ghost with no death_type.'.format(sim_info))
        for ot in OccultType:
            if sim_info.occult_types & ot:
                occult[ot] += 1
        lod[sim_info.lod] += 1
    for household in services.household_manager().values():
        if household.is_active_household:
            household_types['active'] += 1
            sim_types['active'] += len(household)
        elif household.is_player_household:
            household_types['player'] += 1
            sim_types['player'] += len(household)
        else:
            household_types['unplayed'] += 1
            sim_types['unplayed'] += len(household)
    formatting = '{:14} : {:^10} : {}'
    output(formatting.format('Classification', 'Total', 'Histogram'))

    def _print(classification, counter):
        output(formatting.format(classification, sum(counter.values()), counter.most_common()))

    result = []
    result.append(('Households', household_types))
    result.append(('Sims', sim_types))
    result.append(('LOD', lod))
    result.append(('Age', age))
    result.append(('Gender', gender))
    result.append(('Occult', occult))
    result.append(('Ghost', ghost))
    for (name, counter) in result:
        _print(name, counter)
    return result

@sims4.commands.Command('performance.clock_status', command_type=CommandType.Automation)
def clock_status(_connection=None):
    stats = []
    game_clock = services.game_clock_service()
    clock_speed = ClockSpeedMode(game_clock.clock_speed)
    (deviance, threshold, current_duration, duration) = AdaptiveClockSpeed.get_debugging_metrics()
    output = sims4.commands.CheatOutput(_connection)
    stats.append(('Clock Speed', clock_speed, '(Current player-facing clock speed)'))
    stats.append(('Speed Multiplier Type', ClockSpeedMultiplierType(game_clock.clock_speed_multiplier_type), '(Decides the speed 2/3/SS3 multipliers for adaptive speed)'))
    stats.append(('Clock Speed Multiplier', game_clock.current_clock_speed_scale(), '(Current Speed scaled with appropriate speed settings)'))
    stats.append(('Simulation Deviance', '{:>7} / {:<7}'.format(deviance, threshold), '(Simulation clock deviance from time service clock / Tuning Threshold [units: ticks])'))
    stats.append(('Deviance Duration', '{:>7} / {:<7}'.format(str(current_duration), duration), '(Current duration in multiplier phase / Tuning Duration [units: ticks])'))
    for (name, value, description) in stats:
        output('{:25} {!s:40} {}'.format(name, value, description))
    sims4.commands.automation_output('Performance; ClockSpeed:{}'.format(clock_speed), _connection)

@sims4.commands.Command('performance.status', command_type=CommandType.Automation)
def status(_connection=None):
    output = sims4.commands.CheatOutput(_connection)
    output('==Clock==')
    clock_status(_connection=_connection)
    output('==AutonomyQueue==')
    show_queue(_connection=_connection)
    output('==ACC&BCC==')
    cache_status(_connection=_connection)

@sims4.commands.Command('performance.trigger_sim_info_firemeter', command_type=CommandType.Automation)
def trigger_sim_info_firemeter(_connection=None):
    output = sims4.commands.CheatOutput(_connection)
    sim_info_manager = services.sim_info_manager()
    lod_counts = {lod: sim_info_manager.get_num_sim_infos_with_lod(lod) for lod in SimInfoLODLevel}
    sim_info_manager.trigger_firemeter()
    output('LOD counts Before/After firemeter:')
    for lod in SimInfoLODLevel:
        new_count = sim_info_manager.get_num_sim_infos_with_lod(lod)
        output('{}: {} -> {}'.format(lod.name, lod_counts[lod], new_count))

@sims4.commands.Command('performance.trigger_npc_relationship_culling', command_type=CommandType.Automation)
def trigger_npc_relationship_culling(_connection=None):
    output = sims4.commands.CheatOutput(_connection)
    output('Before relationship culling')
    relationship_status(_connection=_connection)
    StoryProgressionRelationshipCulling.trigger_npc_relationship_culling()
    output('After relationship culling')
    relationship_status(_connection=_connection)

@sims4.commands.Command('performance.posture_graph_summary', command_type=CommandType.Automation)
def posture_graph_summary(outputFile=None, _connection=None):
    if outputFile is not None:
        output = sims4.commands.FileOutput(outputFile, _connection)
    else:
        output = sims4.commands.CheatOutput(_connection)
    services.current_zone().posture_graph_service.print_summary(output)
    sims4.commands.automation_output('PostureGraphSummary; Status:End', _connection)

@sims4.commands.Command('performance.sub_autonomy_tracking_start', 'autonomy.sub_autonomy_tracking_start', command_type=sims4.commands.CommandType.Automation)
def record_autonomy_ping_data(_connection=None):
    autonomy.autonomy_util.record_autonomy_ping_data(services.time_service().sim_now)

@sims4.commands.Command('performance.sub_autonomy_tracking_print', 'autonomy.sub_autonomy_tracking_print', command_type=sims4.commands.CommandType.Automation)
def print_sub_autonomy_output(_connection=None):
    output = sims4.commands.CheatOutput(_connection)
    autonomy.autonomy_util.print_sub_autonomy_ping_data(services.time_service().sim_now, output)

@sims4.commands.Command('performance.sub_autonomy_tracking_stop', 'autonomy.sub_autonomy_tracking_stop', command_type=sims4.commands.CommandType.Automation)
def stop_recording_autonomy_ping_data(_connection=None):
    autonomy.autonomy_util.stop_sub_autonomy_ping_data()

@sims4.commands.Command('performance.autonomy_profile.enable', command_type=CommandType.Automation)
def enable_autonomy_profiling_data(_connection=None):
    autonomy.autonomy_util.record_autonomy_profiling_data()
    output = sims4.commands.CheatOutput(_connection)
    output('Autonomy profiling enabled. Dump the profile any time using performance.autonomy_profile.dump')

@sims4.commands.Command('performance.autonomy_profile.disable', command_type=CommandType.Automation)
def disable_autonomy_profiling_data(_connection=None):
    autonomy.autonomy_util.g_autonomy_profile_data = None
    output = sims4.commands.CheatOutput(_connection)
    output('Autonomy profiling disabled.')

@sims4.commands.Command('performance.autonomy_profile.clear', command_type=CommandType.Automation)
def autonomy_autonomy_profiling_data_clear(_connection=None):
    if autonomy.autonomy_util.g_autonomy_profile_data is not None:
        autonomy.autonomy_util.g_autonomy_profile_data.reset_profiling_data()
    output = sims4.commands.CheatOutput(_connection)
    output('Autonomy profile metrics have been cleared.')

@sims4.commands.Command('performance.autonomy_profile.dump', command_type=CommandType.Automation)
def dump_autonomy_profiling_data(_connection=None):
    output = sims4.commands.CheatOutput(_connection)
    if autonomy.autonomy_util.g_autonomy_profile_data is None:
        output('Autonomy profiling is currently disabled. Use |performance.autonomy_profile.enable')
        return
    if not autonomy.autonomy_util.g_autonomy_profile_data.autonomy_requests:
        output('Autonomy profiling is currently enabled but has no records.')
        return

    def callback(file):
        autonomy.autonomy_util.g_autonomy_profile_data.write_profiling_data_to_file(file)

    filename = 'autonomy_profile'
    create_csv(filename, callback=callback, connection=_connection)

@sims4.commands.Command('performance.send_household_region_telemetry', command_type=CommandType.Automation)
def send_region_sim_info_telemetry(_connection=None):
    HouseholdRegionTelemetryData.send_household_region_telemetry()

def print_commodity_census(predicate=lambda x: x, most_common=10, _connection=None):
    counter = collections.Counter()
    initial_counter = collections.Counter()
    for sim_info in services.sim_info_manager().values():
        if sim_info.commodity_tracker is None:
            pass
        else:
            for commodity in sim_info.commodity_tracker:
                if not predicate(commodity):
                    pass
                else:
                    counter[commodity.stat_type] += 1
                    if hasattr(commodity, 'initial_value') and commodity.get_value() == commodity.initial_value:
                        initial_counter[commodity.stat_type] += 1
    dump = []
    num_commodities = sum(counter.values())
    num_commodities_initial = sum(initial_counter.values())
    dump.append(('Total count', num_commodities))
    dump.append(('Initial count', num_commodities_initial))
    dump.append(('Non-initial count', num_commodities - num_commodities_initial))
    output = sims4.commands.CheatOutput(_connection)
    for (name, value) in dump:
        output('{:20} : {}'.format(name, value))
    output('Most common at initial value:')
    for (commodity, num_initial) in initial_counter.most_common(most_common):
        output('{:40} : {}'.format(commodity.__name__, num_initial))

@sims4.commands.Command('performance.analyze.global', command_type=CommandType.Automation)
def analyze_global(_connection=None):
    output = sims4.commands.CheatOutput(_connection)
    output('==Census==')
    print_census_report(_connection=_connection)
    output('==Relationships==')
    relationship_status(_connection=_connection)
    output('==Commodities==')
    commodity_status(_connection=_connection)
    output('==Environment==')
    log_object_statistics_summary(_connection=_connection)
    output('-==Object Score==-')
    score_objects_in_world(verbose=False, _connection=_connection)

@sims4.commands.Command('performance.analyze.runtime.enable', command_type=CommandType.Automation)
def analyze_begin(_connection=None):
    enable_test_profile(_connection=_connection)
    autonomy_distance_estimates_enable(_connection=_connection)

@sims4.commands.Command('performance.analyze.runtime.dump', command_type=CommandType.Automation)
def analyze_dump(_connection=None):
    dump_tests_profile(_connection=_connection)
    dump_test_resolver_profiles(_connection=_connection)
    autonomy_distance_estimates_dump(_connection=_connection)

@sims4.commands.Command('performance.commodity_status', command_type=CommandType.Automation)
def commodity_status(most_common=10, _connection=None):

    def predicate(commodity):
        return not commodity.is_skill

    print_commodity_census(predicate=predicate, most_common=most_common, _connection=_connection)

@sims4.commands.Command('performance.skill_status', command_type=CommandType.Automation)
def skill_status(most_common:int=10, _connection=None):

    def predicate(commodity):
        return commodity.is_skill

    print_commodity_census(predicate=predicate, most_common=most_common, _connection=_connection)

@sims4.commands.Command('performance.score_objects_in_world', command_type=CommandType.Automation)
def score_objects_in_world(verbose:bool=False, _connection=None):
    cheat_output = sims4.commands.Output(_connection)
    object_scores = defaultdict(Counter)
    (on_lot_objects, off_lot_objects) = _score_all_objects(object_scores)
    overall_score = 0
    if verbose:
        cheat_output('Objects On Lot:')
        overall_score += _get_total_object_score(on_lot_objects, object_scores, cheat_output, verbose)
        cheat_output('Objects Off Lot:')
        overall_score += _get_total_object_score(off_lot_objects, object_scores, cheat_output, verbose)
    else:
        on_lot_objects_value = _get_total_object_score(on_lot_objects, object_scores, cheat_output, verbose)
        cheat_output('On Lot Objects Score:  {}'.format(on_lot_objects_value))
        off_lot_objects_value = _get_total_object_score(off_lot_objects, object_scores, cheat_output, verbose)
        cheat_output('Off Lot Objects Score: {}'.format(off_lot_objects_value))
        overall_score = on_lot_objects_value + off_lot_objects_value
    cheat_output('Total Lot Score:       {}'.format(overall_score))
    cheat_output('Number of On Lot Objects :  {}'.format(sum(on_lot_objects.values())))
    cheat_output('Number of Off Lot Objects : {}'.format(sum(off_lot_objects.values())))

def _score_all_objects(object_score_counter):
    on_lot_objects = Counter()
    off_lot_objects = Counter()
    all_objects = list(services.object_manager().objects)
    for obj in all_objects:
        if obj.is_sim:
            pass
        else:
            obj_type = obj.definition
            if obj.is_on_active_lot():
                on_lot_objects[obj_type] += 1
            else:
                off_lot_objects[obj_type] += 1
            if obj_type in object_score_counter:
                pass
            else:
                for super_affordance in obj.super_affordances():
                    object_score_counter[obj_type]['interaction'] += POINTS_PER_INTERACTION
                    if super_affordance.allow_autonomous:
                        object_score_counter[obj_type]['autonomous'] += POINTS_PER_AUTONOMOUS_INTERACTION
                    if super_affordance.provided_posture_type is not None:
                        object_score_counter[obj_type]['provided_posture'] += POINTS_PER_PROVIDED_POSTURE_INTERACTION
                if obj.has_component(STATE_COMPONENT):
                    object_score_counter[obj_type]['state_component'] += 1
                    for (_, client_state_values) in obj.get_component(STATE_COMPONENT)._client_states.items():
                        object_score_counter[obj_type]['state_component'] += 1*POINTS_PER_CLIENT_STATE_TUNING
                        client_change_op_count = _num_client_state_ops_changing_client(client_state_values)
                        object_score_counter[obj_type]['client_change_tuning'] += client_change_op_count*POINTS_PER_CLIENT_STATE_CHANGE_TUNING
                if obj.parts:
                    object_score_counter[obj_type]['parts'] += len(obj.parts)*POINTS_PER_OBJECT_PART
                if obj.statistic_tracker is not None:
                    object_score_counter[obj_type]['statistics'] += len(obj.statistic_tracker)*POINTS_PER_STATISTIC
                if obj.commodity_tracker is not None:
                    object_score_counter[obj_type]['commodities'] += len(obj.commodity_tracker)*POINTS_PER_COMMODITY
    return (on_lot_objects, off_lot_objects)

def _num_client_state_ops_changing_client(client_state_values):
    count = 0
    for client_state_value in client_state_values:
        count += _get_num_client_changing_ops(client_state_value.new_client_state.ops)
    for target_client_state_value in client_state_values.values():
        count += _get_num_client_changing_ops(target_client_state_value.ops)
    return count

def _get_num_client_changing_ops(ops):
    count = 0
    for (op, value) in ops.items():
        if _client_state_op_has_client_change(op, value):
            count += 1
    return count

def _client_state_op_has_client_change(op, value):
    if op in CLIENT_STATE_OPS_TO_IGNORE:
        return False
    elif value is UNSET or value is None:
        return False
    return True

def _get_total_object_score(counter, scores, output, verbose):
    overall_score = 0
    for obj_type in counter:
        occurrences = counter[obj_type]
        object_data = scores[obj_type]
        object_score = sum(object_data.values())
        overall_score += occurrences*object_score
        if verbose:
            output('\tObject {} appears {} times at a score of {} for a total contribution of ({})'.format(obj_type.__name__, occurrences, object_score, occurrences*object_score))
    if verbose:
        output('Total Score is {}'.format(overall_score))
    return overall_score

@sims4.commands.Command('performance.dump_object_scores', command_type=CommandType.Automation)
def dump_object_scores(_connection=None):
    object_scores = defaultdict(Counter)
    (on_lot_objects, off_lot_objects) = _score_all_objects(object_scores)

    def _score_objects_callback(file):
        file.write('Object,total,On Lot,Off Lot,Interaction,Autonomous,provided posture,state component,client change tuning,parts,stats,commodities\n')
        for object_type in object_scores:
            _dump_object_to_file(object_type, object_scores, on_lot_objects, off_lot_objects, file)

    create_csv('object_scores', _score_objects_callback, _connection)

def _dump_object_to_file(object_type, object_scores, on_lot_objects, off_lot_objects, file):
    object_counter = object_scores[object_type]
    file.write('{},{},{},{},{},{},{},{},{},{},{},{}\n'.format(object_type, sum(object_counter.values()), on_lot_objects[object_type], off_lot_objects[object_type], object_counter['interaction'], object_counter['autonomous'], object_counter['provided_posture'], object_counter['state_component'], object_counter['client_change_tuning'], object_counter['parts'], object_counter['statistics'], object_counter['commodities']))

@sims4.commands.Command('performance.display_object_load_times', command_type=CommandType.Automation)
def display_object_load_times(_connection=None):
    if not indexed_manager.capture_load_times:
        return False
    cheat_output = sims4.commands.Output(_connection)
    for (object_class, object_load_data) in object_load_times.items():
        if not isinstance(object_class, str):
            cheat_output('{}: Object Manager Add Time {} : Component Load Time {} : Number of times added {} : number of times loaded {}'.format(object_class, object_load_data.time_spent_adding, object_load_data.time_spent_loading, object_load_data.adds, object_load_data.loads))
    time_adding = sum([y.time_spent_adding for (x, y) in object_load_times.items() if not isinstance(x, str)])
    time_loading = sum([y.time_spent_loading for (x, y) in object_load_times.items() if not isinstance(x, str)])
    cheat_output('Total time spent adding objects : {}'.format(time_adding))
    cheat_output('Total time spent loading components : {}'.format(time_loading))
    cheat_output('Time spent loading households : {}'.format(object_load_times['household']))
    cheat_output('Time spent building posture graph: {}'.format(object_load_times['posture_graph']))
    cheat_output('Time spent loading into the zone: {}'.format(object_load_times['lot_load']))

@sims4.commands.Command('performance.dump_object_load_times', command_type=CommandType.Automation)
def dump_object_load_times(_connection=None):
    if not indexed_manager.capture_load_times:
        return False

    def _object_load_time_callback(file):
        file.write('Object,AddTime,LoadTime,Adds,Loads\n')
        for (object_class, object_load_data) in object_load_times.items():
            if not isinstance(object_class, str):
                file.write('{},{},{},{},{}\n'.format(object_class, object_load_data.time_spent_adding, object_load_data.time_spent_loading, object_load_data.adds, object_load_data.loads))
        time_adding = sum([y.time_spent_adding for (x, y) in object_load_times.items() if not isinstance(x, str)])
        time_loading = sum([y.time_spent_loading for (x, y) in object_load_times.items() if not isinstance(x, str)])
        file.write(',{},{}\n'.format(time_adding, time_loading))
        file.write('Household,{}\n'.format(object_load_times['household']))
        file.write('Posture Graph,{}\n'.format(object_load_times['posture_graph']))
        file.write('Lot Load,{}\n'.format(object_load_times['lot_load']))

    create_csv('object_load_times', _object_load_time_callback, _connection)

@sims4.commands.Command('performance.toggle_object_load_capture', command_type=CommandType.Automation)
def _toggle_object_load_capture(_connection=None):
    indexed_manager.capture_load_times = not indexed_manager.capture_load_times
