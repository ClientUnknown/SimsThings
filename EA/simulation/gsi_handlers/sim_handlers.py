import itertools
def bool_to_str(value):
    if value:
        return 'X'
    return ''

def _get_sim_instance_by_id(sim_id):
    sim_info_manager = services.sim_info_manager()
    if sim_info_manager is not None:
        for sim_info in sim_info_manager.objects:
            if sim_id == sim_info.sim_id:
                return sim_info.get_sim_instance(allow_hidden_flags=ALL_HIDDEN_REASONS)

def _get_sim_info_by_id(sim_id):
    sim_info_manager = services.sim_info_manager()
    sim_info = None
    if sim_info_manager is not None:
        sim_info = sim_info_manager.get(sim_id)
    return sim_info

@GsiHandler('static_commodity_view', static_commodity)
def generate_sim_static_commodity_view_data(sim_id:int=None):
    stat_data = []
    cur_sim_info = _get_sim_info_by_id(sim_id)
    if cur_sim_info.static_commodity_tracker is not None:
        for stat in list(cur_sim_info.static_commodity_tracker):
            stat_data.append({'name': type(stat).__name__})
    return stat_data

    sub_schema.add_field('buff', label='Buff Name')
    sub_schema.add_field('modifier_value', label='Modifier Value', type=GsiFieldVisualizers.INT)
@GsiHandler('skill_view', skill_schema)
def generate_sim_skill_view_data(sim_id:int=None):
    skill_data = []
    cur_sim_info = _get_sim_info_by_id(sim_id)
    if cur_sim_info is not None:
        for stat in cur_sim_info.all_skills():
            skill_level = stat.get_user_value()
            effective_skill_level = cur_sim_info.get_effective_skill_level(stat)
            entry = {'simId': str(sim_id), 'skill_guid': str(stat.guid64), 'skill_name': type(stat).__name__, 'skill_value': stat.get_value(), 'skill_level': skill_level, 'skill_effective_level': effective_skill_level}
            entry['effective_modifiers'] = []
            if effective_skill_level != skill_level:
                for (buff_type, modifier) in cur_sim_info.effective_skill_modified_buff_gen(stat):
                    buff_entry = {'buff': buff_type.__class__.__name__, 'modifier_value': modifier}
                    entry['effective_modifiers'].append(buff_entry)
            skill_data.append(entry)
    return skill_data

    sub_schema.add_field('modifier', label='Modifier')
    sub_schema.add_field('modifier_value', label='Modifier Value')
    sub_schema.add_field('callback_info', label='Callback Info')
@GsiHandler('commodity_data_view', commodity_data_schema)
def generate_sim_commodity_data_view_data(sim_id:int=None):
    cur_sim_info = _get_sim_info_by_id(sim_id)
    if cur_sim_info is None:
        return []

    def add_modifier_entry(modifier_entries, modifier_name, modifier_value):
        modifier_entries.append({'modifier': modifier_name, 'modifier_value': modifier_value})

    stat_data = []
    commodity_tracker = cur_sim_info.commodity_tracker
    if commodity_tracker is None:
        return stat_data
    for stat in list(commodity_tracker):
        entry = {'stat_guid': str(stat.guid64), 'stat_name': stat.stat_type.__name__, 'stat_value': stat.get_value(), 'decay_rate': stat.get_decay_rate(), 'change_rate': stat.get_change_rate(), 'decay_enabled': 'x' if stat.decay_enabled else '', 'time_till_callback': str(stat._alarm_handle.get_remaining_time()) if stat._alarm_handle is not None else '', 'active_callback': str(stat._active_callback) if stat._active_callback is not None else '', 'delayed_decay_timer': str(stat.get_time_till_decay_starts())}
        if isinstance(stat, statistics.commodity.Commodity):
            if stat._buff_handle is not None:
                buff_type = cur_sim_info.get_buff_type(stat._buff_handle)
                if buff_type is not None:
                    entry['state_buff'] = buff_type.__name__
                else:
                    stat_in_tracker = stat in commodity_tracker
                    entry['state_buff'] = 'Buff Handle: {} and cannot find buff, Stat in Tracker: {}'.format(stat._buff_handle, stat_in_tracker)
            if stat._distress_buff_handle is not None:
                buff_type = cur_sim_info.get_buff_type(stat._distress_buff_handle)
                entry['distress_buff'] = buff_type.__name__
        elif stat._skill_level_buff is not None:
            buff_type = cur_sim_info.get_buff_type(stat._skill_level_buff)
            if buff_type is not None:
                entry['state_buff'] = buff_type.__name__
        modifier_entries = []
        add_modifier_entry(modifier_entries, 'persisted', 'x' if stat.persisted else '')
        add_modifier_entry(modifier_entries, 'remove_on_covergence', 'x' if stat.remove_on_convergence else '')
        add_modifier_entry(modifier_entries, 'min_value', stat.min_value)
        add_modifier_entry(modifier_entries, 'max_value', stat.max_value)
        add_modifier_entry(modifier_entries, 'statistic_modifier', stat._statistic_modifier)
        add_modifier_entry(modifier_entries, 'statistic_multiplier_increase', stat._statistic_multiplier_increase)
        add_modifier_entry(modifier_entries, 'statistic_multiplier_decrease', stat._statistic_multiplier_decrease)
        add_modifier_entry(modifier_entries, 'decay_rate_multiplier', stat._decay_rate_modifier)
        entry['modifiers'] = modifier_entries
        callback_infos = []
        for callback_listener in stat._statistic_callback_listeners:
            callback_infos.append({'callback_info': str(callback_listener)})
        entry['track_listeners'] = callback_infos
        stat_data.append(entry)
    return stat_data

@GsiHandler('autonomy_timer_view', autonomy_timer_schema)
def generate_autonomy_timer_view_data(sim_id:int=None):
    autonomy_timer_data = []
    sim = None
    sim_info_manager = services.sim_info_manager()
    if sim_info_manager is None:
        return autonomy_timer_data
    for sim_info in services.sim_info_manager().objects:
        if sim_id == sim_info.sim_id:
            sim = sim_info.get_sim_instance()
            break
    if sim is not None:
        for timer in sim.debug_get_autonomy_timers_gen():
            entry = {'timer_name': timer[0], 'timer_value': timer[1]}
            autonomy_timer_data.append(entry)
    return autonomy_timer_data

@GsiHandler('sim_infos_toolbar', sim_info_toolbar_schema)
def generate_sim_info_toolbar_data(*args, zone_id:int=None, **kwargs):
    sim_info_data = []
    sim_info_manager = services.sim_info_manager()
    if sim_info_manager is None:
        return sim_info_data
    selectable_sims = []
    instanced_sims = []
    uninstanced_sims = []
    for sim_info in list(sim_info_manager.objects):
        if sim_info.first_name or not sim_info.last_name:
            full_name = sim_info.full_name
        else:
            full_name = sim_info.first_name + ' ' + sim_info.last_name
        cur_data_entry = {'simId': str(hex(sim_info.sim_id)), 'fullName': full_name, 'selectable': sim_info.is_selectable, 'isInstanced': sim_info.is_instanced()}
        if cur_data_entry['selectable']:
            selectable_sims.append(cur_data_entry)
        elif cur_data_entry['isInstanced']:
            instanced_sims.append(cur_data_entry)
        else:
            uninstanced_sims.append(cur_data_entry)
    selectable_sims = sorted(selectable_sims, key=lambda data: data['fullName'])
    instanced_sims = sorted(instanced_sims, key=lambda data: data['fullName'])
    uninstanced_sims = sorted(uninstanced_sims, key=lambda data: data['fullName'])
    return list(itertools.chain(selectable_sims, instanced_sims, uninstanced_sims))

    cheat.add_token_param('simId')
    cheat.add_token_param('simId')
    cheat.add_token_param('simId')
    cheat.add_token_param('simId')
    sub_schema.add_field('aging_field_name', label='Property')
    sub_schema.add_field('aging_field_value', label='Value')
    sub_schema.add_field('pregnancy_field_name', label='Property')
    sub_schema.add_field('pregnancy_field_value', label='Value')
    sub_schema.add_field('occult_type', label='Occult Type')
    sub_schema.add_field('occult_is_available', label='Is Available', width=0.5)
    sub_schema.add_field('occult_is_current', label='Is Current', width=0.5)
    sub_schema.add_field('occult_facial_attributes', label='Facial Attributes')
    sub_schema.add_field('occult_physique', label='Physique')
    sub_schema.add_field('occult_skin_tone', label='Skin Tone')
    sub_schema.add_field('occult_voice_actor', label='Voice Actor')
    sub_schema.add_field('occult_voice_pitch', label='Voice Pitch')
    sub_schema.add_field('occult_voice_effect', label='Voice Effect')
    sub_schema.add_field('occult_plumbbob_override', label='Plumbbob Override')
    sub_schema.add_field('occult_outfit_categories', label='Occult Outfits')
    sub_schema.add_field('occult_current_outfit', label='Current Occult Outfit')
    sub_schema.add_field('outfit_category', label='Category')
    sub_schema.add_field('outfit_index', label='Index')
    sub_schema.add_field('outfit_id', label='ID')
    sub_schema.add_field('outfit_flags', label='Flags')
    sub_schema.add_field('outfit_extra_info', label='Extra Info')
    sub_schema.add_field('part_ids', label='Parts', width=3)
    sub_schema.add_field('tracker', label='Tracker')
    sub_schema.add_field('exists', label='Exists')
@GsiHandler('sim_infos', sim_info_schema)
def generate_sim_info_data(*args, zone_id:int=None, **kwargs):
    sim_info_data = []
    sim_info_manager = services.sim_info_manager()
    if sim_info_manager is None:
        return sim_info_data
    for sim_info in list(sim_info_manager.objects):
        species = sim_info.species
        extended_species = sim_info.extended_species
        if species == extended_species:
            species_str = format_enum_name(species)
        else:
            species_str = '{} ({})'.format(format_enum_name(species), format_enum_name(extended_species))
        entry = {'simId': str(hex(sim_info.sim_id)), 'firstName': sim_info.first_name, 'lastName': sim_info.last_name, 'fullName': sim_info.full_name, 'gender': format_enum_name(sim_info.gender), 'age': format_enum_name(sim_info.age), 'species': species_str, 'lod': format_enum_name(sim_info.lod), 'selectable': sim_info.is_selectable, 'zone_id': sim_info.zone_id}
        sim = sim_info.get_sim_instance(allow_hidden_flags=ALL_HIDDEN_REASONS)
        aging_info = []
        entry['aging'] = aging_info
        entry['aging'].append({'aging_field_name': 'Can Age', 'aging_field_value': str(sim_info.can_age_up())})
        entry['aging'].append({'aging_field_name': 'Can Die', 'aging_field_value': str(not sim_info.is_death_disabled())})
        entry['aging'].append({'aging_field_name': 'Progress', 'aging_field_value': '{}, {:.2%}'.format(sim_info.age_progress, sim_info.age_progress/sim_info.get_age_transition_data(sim_info.age).get_age_duration(sim_info))})
        entry['aging'].append({'aging_field_name': 'Time to Notification', 'aging_field_value': str(sim_info._almost_can_age_handle.get_remaining_time()) if sim_info._almost_can_age_handle is not None else '-'})
        entry['aging'].append({'aging_field_name': 'Time to Availability', 'aging_field_value': str(sim_info._can_age_handle.get_remaining_time()) if sim_info._can_age_handle is not None else '-'})
        entry['aging'].append({'aging_field_name': 'Time to Auto-Age', 'aging_field_value': str(sim_info._auto_age_handle.get_remaining_time()) if sim_info._auto_age_handle is not None else '-'})
        occult_info = []
        entry['occult'] = occult_info
        for occult_type in OccultType:
            occult_sim_info = sim_info.occult_tracker.get_occult_sim_info(occult_type)
            occult_outfit_categories = ''
            if occult_sim_info is not None:
                for outfit_entry in list(occult_sim_info.get_all_outfit_entries()):
                    occult_outfit_categories = occult_outfit_categories + str(outfit_entry[0]) + ' '
            occult_entry = {'occult_type': str(occult_type), 'occult_is_available': 'X' if sim_info.occult_tracker.has_occult_type(occult_type) else '', 'occult_is_current': 'X' if sim_info.current_occult_types == occult_type else '', 'occult_facial_attributes': str(occult_sim_info.facial_attributes)[:32] if occult_sim_info is not None else '', 'occult_physique': str(occult_sim_info.physique) if occult_sim_info is not None else '', 'occult_skin_tone': str(occult_sim_info.skin_tone) if occult_sim_info is not None else '', 'occult_voice_actor': str(occult_sim_info.voice_actor) if occult_sim_info is not None else '', 'occult_voice_pitch': str(occult_sim_info.voice_pitch) if occult_sim_info is not None else '', 'occult_voice_effect': str(occult_sim_info.voice_effect) if occult_sim_info is not None else '', 'occult_plumbbob_override': str(sim_info.plumbbob_override) if sim_info.current_occult_types == occult_type else '', 'occult_outfit_categories': occult_outfit_categories, 'occult_current_outfit': str(occult_sim_info.get_current_outfit()) if occult_sim_info is not None else ''}
            occult_info.append(occult_entry)
        entry['outfits'] = []
        current_outfit = sim_info.get_current_outfit()
        previous_outfit = sim_info.get_previous_outfit()
        if current_outfit:
            entry['current_outfit_category'] = format_enum_name(OutfitCategory(current_outfit[0]))
            entry['current_outfit_index'] = str(current_outfit[1])
        all_outfit_entries = list(sim_info.get_all_outfit_entries())
        for outfit_entry in all_outfit_entries:
            outfit_data = sim_info.get_outfit(*outfit_entry)
            entry['outfits'].append({'outfit_category': str(outfit_entry[0]), 'outfit_index': str(outfit_entry[1]), 'outfit_id': str(outfit_data.outfit_id), 'outfit_flags': str(outfit_data.outfit_flags), 'outfit_extra_info': 'Current Outfit' if outfit_entry == current_outfit else 'Previous Outfit' if outfit_entry == previous_outfit else '', 'part_ids': ', '.join(str(part_id) for part_id in outfit_data.part_ids)})
        if current_outfit not in all_outfit_entries:
            entry['outfits'].append({'outfit_category': str(current_outfit[0]), 'outfit_index': str(current_outfit[1]), 'outfit_id': '<INVALID OUTFIT>', 'outfit_extra_info': 'Current Outfit'})
        if previous_outfit not in all_outfit_entries:
            entry['outfits'].append({'outfit_category': str(current_outfit[0]), 'outfit_index': str(current_outfit[1]), 'outfit_id': '<INVALID OUTFIT>', 'outfit_extra_info': 'Previous Outfit'})
        entry['pregnancy'] = []
        entry['pregnancy'].append({'pregnancy_field_name': 'Is Pregnant', 'pregnancy_field_value': str(sim_info.is_pregnant)})
        if sim_info.is_pregnant:
            pregnancy_tracker = sim_info.pregnancy_tracker
            pregnancy_commodity = sim_info.get_statistic(pregnancy_tracker.PREGNANCY_COMMODITY_MAP.get(sim_info.species), add=False)
            entry['pregnancy'].append({'pregnancy_field_name': 'Progress', 'pregnancy_field_value': '<None>' if pregnancy_commodity is None else '{:.2%}'.format(pregnancy_commodity.get_value()/pregnancy_commodity.max_value)})
            entry['pregnancy'].append({'pregnancy_field_name': 'Parents', 'pregnancy_field_value': ', '.join('<None>' if p is None else p.full_name for p in pregnancy_tracker.get_parents())})
            entry['pregnancy'].append({'pregnancy_field_name': 'Seed', 'pregnancy_field_value': str(pregnancy_tracker._seed)})
            entry['pregnancy'].append({'pregnancy_field_name': 'Origin', 'pregnancy_field_value': str(pregnancy_tracker._origin)})
        household_id = sim_info.household_id
        if household_id is None:
            entry['householdId'] = 'None'
            entry['householdFunds'] = '0'
            entry['home_zone_id'] = ''
            entry['home_world_id'] = ''
        else:
            entry['householdId'] = str(hex(household_id))
            sim_info_household = sim_info.household
            if sim_info_household:
                entry['householdFunds'] = str(sim_info_household.funds.money)
                entry['home_zone_id'] = str(hex(sim_info_household.home_zone_id))
                entry['home_world_id'] = str(hex(sim_info_household.get_home_world_id()))
            else:
                entry['householdFunds'] = 'Pending'
                entry['home_zone_id'] = ''
                entry['home_world_id'] = ''
        sim = sim_info.get_sim_instance()
        if sim is not None:
            entry['active_mood'] = str(sim.get_mood().__name__)
            entry['on_active_lot'] = str(sim.is_on_active_lot())
        if sim is not None and sim.voice_pitch_override is not None:
            entry['voice_pitch'] = sim.voice_pitch_override
        else:
            entry['voice_pitch'] = sim_info.voice_pitch
        current_away_action = sim_info.away_action_tracker.current_away_action if sim_info.away_action_tracker is not None else None
        if current_away_action is not None:
            entry['away_action'] = str(current_away_action)
        entry['creation_source'] = format_enum_name(sim_info.creation_source)
        entry['trackers'] = []
        for tracker_attr in SimInfo.SIM_INFO_TRACKERS:
            entry['trackers'].append({'tracker': tracker_attr, 'exists': bool_to_str(getattr(sim_info, tracker_attr, None) != None)})
        sim_info_data.append(entry)
    sort_key_fn = lambda data: (data['selectable'] != True, data['firstName'])
    sim_info_data = sorted(sim_info_data, key=sort_key_fn)
    return sim_info_data

    sub_schema.add_field('liabilityType', label='Liability Type')
    sub_schema.add_field('name', label='Name', width=3)
    sub_schema.add_field('action', label='Interaction Action', width=2)
    sub_schema.add_field('satisfied', label='Satisfied', width=1)
    sub_schema.add_field('satisfied_conditions', label='Satisfied Conditions', width=4)
    sub_schema.add_field('unsatisfied_conditions', label='Unsatisfied Conditions', width=4)
    sub_schema.add_field('loot', label='Loot', width=4)
    sub_schema.add_field('progress_bar', label='Progress Bar Tracking', width=4)
    sub_schema.add_field('name', label='Name')
    sub_schema.add_field('result', label='Result')
    sub_schema.add_field('key', label='Key')
    sub_schema.add_field('value', label='Value')
@GsiHandler('interaction_state_view', interaction_state_view_schema)
def generate_interaction_view_data(sim_id:int=None):
    sim_interaction_info = []
    cur_sim = _get_sim_instance_by_id(sim_id)
    if cur_sim is not None:
        for bucket in list(cur_sim.queue._buckets):
            for interaction in bucket:
                sim_interaction_info.append(create_state_info_entry(interaction, type(bucket).__name__))
        for interaction in list(cur_sim.si_state):
            sim_interaction_info.append(create_state_info_entry(interaction, 'SI_State'))
    return sim_interaction_info

def create_state_info_entry(interaction, interaction_pos):
    if hasattr(interaction, 'name_override'):
        interaction_name = interaction.name_override
    else:
        interaction_name = type(interaction).__name__
    target = interaction.target
    entry = {'interactionId': interaction.id, 'interactionName': interaction_name, 'target': str(target), 'target_id': str(target.id) if target is not None else '', 'interactionPos': interaction_pos, 'group_id': interaction.group_id, 'running': bool_to_str(interaction.running), 'priority': interaction.priority.name, 'isSuper': bool_to_str(interaction.is_super), 'isFinishing': bool_to_str(interaction.is_finishing), 'allowAuto': bool_to_str(interaction.allow_autonomous), 'allowUser': bool_to_str(interaction.allow_user_directed), 'visible': bool_to_str(interaction.visible), 'is_guaranteed': bool_to_str(interaction.is_guaranteed()), 'icon': str(interaction.get_icon_info())}
    if interaction.liabilities:
        entry['liabilities'] = []
        for liability in interaction.liabilities:
            entry['liabilities'].append({'liabilityType': liability.gsi_text()})
    if interaction._conditional_action_manager is not None:
        entry['conditional_actions'] = []
        for group in interaction._conditional_action_manager:
            group_entry = {}
            group_entry['name'] = str(group.conditional_action)
            group_entry['loot'] = str(group.conditional_action.loot_actions)
            group_entry['action'] = str(group.conditional_action.interaction_action)
            group_entry['satisfied'] = group.satisfied
            group_entry['satisfied_conditions'] = ',\n'.join(str(c) for c in group if c.satisfied)
            group_entry['unsatisfied_conditions'] = ',\n'.join(str(c) for c in group if not c.satisfied)
            if not interaction.progress_bar_enabled.bar_enabled:
                group_entry['progress_bar'] = 'Progress bar not enabled.'
            elif interaction.progress_bar_enabled.force_listen_statistic:
                forced_stat = interaction.progress_bar_enabled.force_listen_statistic
                group_entry['progress_bar'] = 'Being forced to listen to stat {}'.format(forced_stat.statistic)
                subject = interaction.get_participant(forced_stat.subject)
                tracker = subject.get_tracker(forced_stat.statistic)
                if tracker:
                    target_value = forced_stat.target_value.value
                    current_value = tracker.get_user_value(forced_stat.statistic)
                    group_entry['progress_bar'] += '\nCurrent Value: {}'.format(current_value)
                    group_entry['progress_bar'] += '\nTarget Value: {}'.format(target_value)
            elif group.progress_bar_info:
                group_entry['progress_bar'] = group.progress_bar_info
            entry['conditional_actions'].append(group_entry)
    entry['interaction_parameters'] = [{'key': str(key), 'value': str(value)} for (key, value) in interaction.interaction_parameters.items()]
    runner = None
    if runner is not None:
        entry['running_elements'] = []

        def append_element(element_result, depth=0):
            try:
                for sub_element in iter(element_result.element):
                    if hasattr(sub_element, '_debug_run_list'):
                        for sub_element_result in sub_element._debug_run_list:
                            append_element(sub_element_result, depth=depth + 1)
                    else:
                        name = '+'*depth + str(sub_element)
                        entry['running_elements'].append({'name': name, 'result': 'Pending'})
            except TypeError:
                name = '+'*depth + str(element_result.element)
                entry['running_elements'].append({'name': name, 'result': str(element_result.result)})

        if hasattr(runner, '_debug_run_list'):
            for element_result in runner._debug_run_list:
                append_element(element_result)
    return entry

    sub_schema.add_field('cache_key', label='Cache Key')
    sub_schema.add_field('asm', label='ASM')
@GsiHandler('posture_state_view', posture_state_view_schema)
def generate_sim_info_view_data(sim_id:int=None):
    sim_posture_info = []
    cur_sim = _get_sim_instance_by_id(sim_id)
    if cur_sim is not None:
        if cur_sim.posture_state is not None:
            for posture_aspect in cur_sim.posture_state.aspects:
                owning_interaction_strs = [str(owning_interaction) for owning_interaction in posture_aspect.owning_interactions]
                cur_posture_info = {'postureType': type(posture_aspect).name, 'postureName': str(posture_aspect), 'postureTarget': str(posture_aspect.target), 'postureSpec': str(cur_sim.posture_state.spec), 'sourceInteraction': str(posture_aspect.source_interaction), 'owningInteraction': ' '.join(owning_interaction_strs), 'asm_registry': posture_aspect.get_asm_registry_text()}
                sim_posture_info.append(cur_posture_info)
        else:
            cur_posture_info = {'postureType': '---', 'postureName': 'Sim Posture State is None'}
            sim_posture_info.append(cur_posture_info)
    return sim_posture_info

@GsiHandler('ui_manager_view', ui_manager_schema)
def generate_sim_ui_manager_view_data(sim_id:int=None):

    def _visual_type_to_string(visual_type):
        if visual_type == 0:
            return 'Simple'
        if visual_type == 1:
            return 'Parent'
        if visual_type == 2:
            return 'Mixer'
        elif visual_type == 3:
            return 'Posture'
        return 'Undefined'

    ui_data = []
    cur_sim = _get_sim_instance_by_id(sim_id)
    if cur_sim is not None:
        for int_info in cur_sim.ui_manager.get_interactions_gen():
            entry = {'interaction_id': int_info.interaction_id, 'insert_after_id': int_info.insert_after_id, 'target': str(int_info.target), 'canceled': int_info.canceled, 'ui_state': str(int_info.ui_state), 'to_be_canceled': str(int_info.interactions_to_be_canceled), 'super_id': int_info.super_id, 'associated_skill': str(int_info.associated_skill), 'visual_type': _visual_type_to_string(int_info.ui_visual_type), 'priority': str(int_info.priority)}
            ui_data.append(entry)
    return ui_data

    cheat.add_token_param('topic_type')
    cheat.add_token_param('sim_id')
    cheat.add_token_param('target_id')
    cheat.add_token_param('topic_type')
    cheat.add_token_param('sim_id')
@GsiHandler('sim_social_group_view', sim_topics_schema)
def generate_sim_topics_view_data(sim_id:int=None):
    topics_view_data = []
    cur_sim = _get_sim_instance_by_id(sim_id)
    if cur_sim is not None:
        for topic in cur_sim.get_topics_gen():
            topic_target = topic.target
            target_id = topic_target.id if topic_target is not None else ''
            topics_view_data.append({'sim_id': str(sim_id), 'topic_type': topic.__class__.__name__, 'current_relevancy': str(topic.current_relevancy), 'target': str(topic_target), 'target_id': str(target_id), 'is_valid': topic.is_valid})
    return topics_view_data

    sub_schema.add_field('statistic', label='Stat')
    sub_schema.add_field('tuned_threshold', label='Desired Threshold')
    sub_schema.add_field('callback_threshold', label='Callback Threshold')
@GsiHandler('mult_motive_view', multi_motive_view_schema)
def generate_multi_motive_view_data(sim_id:int=None):
    view_data = []
    cur_sim = _get_sim_instance_by_id(sim_id)
    if cur_sim is not None:
        for multi_motive_tracker in cur_sim._multi_motive_buff_trackers:
            buff_to_add = multi_motive_tracker._buff
            entry = {'buff_to_add': str(buff_to_add), 'buff_added': 'x' if cur_sim.has_buff(buff_to_add) else '', 'count': '{}/{}'.format(multi_motive_tracker._motive_count, len(multi_motive_tracker._multi_motive_buff_motives)), 'watcher_add': 'x' if multi_motive_tracker._watcher_handle is not None else '', 'statistics': []}
            for (stat_type, callback_data) in tuple(multi_motive_tracker._commodity_callback.items()):
                threshold = multi_motive_tracker._multi_motive_buff_motives.get(stat_type)
                stat_entry = {'statistic': str(stat_type), 'tuned_threshold': str(threshold), 'callback_threshold': str(callback_data.threshold) if callback_data is not None else 'Stat not available'}
                entry['statistics'].append(stat_entry)
            view_data.append(entry)
    return view_data

    sub_schema.add_field('game_effect_index', label='Index', type=GsiFieldVisualizers.INT, width=0.1)
    sub_schema.add_field('attribute_name', label='Name')
    sub_schema.add_field('attribute_value', label='Value')
    sub_schema.add_field('type', label='Type')
    sub_schema.add_field('reference', label='Reference')
    sub_schema.add_field('score_modifier', label='Score Modifier', type=GsiFieldVisualizers.FLOAT)
    sub_schema.add_field('success_modifier', label='Success Modifier', type=GsiFieldVisualizers.FLOAT)
    sub_schema.add_field('static_commodity_name', label='Name')
    sub_schema.add_field('affordance', label='Affordance')
    sub_schema.add_field('min_lockout_initial', label='Min Time Initial', type=GsiFieldVisualizers.FLOAT)
    sub_schema.add_field('max_lockout_initial', label='Max Time Initial', type=GsiFieldVisualizers.FLOAT)
    sub_schema.add_field('min_lockout', label='Min Time', type=GsiFieldVisualizers.FLOAT)
    sub_schema.add_field('max_lockout', label='Max Time', type=GsiFieldVisualizers.FLOAT)
    sub_schema.add_field('unlock_time', label='Time until unlock')
    sub_schema.add_field('affordance', label='Affordance')
    sub_schema.add_field('commodity_flags', label='Commodity Flags')
    sub_schema.add_field('affordance', label='Affordance')
    sub_schema.add_field('commodity_flags', label='Commodity Flags')
    sub_schema.add_field('modifier', label='Modifier')
    cheat.add_token_param('sim_id')
    cheat.add_token_param('name')
    cheat.add_token_param('sim_id')
def generate_all_buffs():
    instance_manager = services.get_instance_manager(Types.BUFF)
    if instance_manager.all_instances_loaded:
        return [cls.__name__ for cls in instance_manager.types.values()]
    else:
        return []

def add_buff_cheats(manager):
    with sim_buff_schema.add_view_cheat('sims.add_buff', label='Add Buff (Select Grid Entry First)') as cheat:
        cheat.add_token_param('buff_name', dynamic_token_fn=generate_all_buffs)
        cheat.add_token_param('sim_id')

def _buff_super_affordance_output(super_affordances):
    if not super_affordances:
        return []
    affordances_entries = []
    for super_affordance in super_affordances:
        affordances_entries.append({'affordance': super_affordance.__name__, 'commodity_flags': str(super_affordance.commodity_flags) if super_affordance.commodity_flags else ''})
    return affordances_entries

def _buff_target_super_affordance_output(target_super_affordances):
    if not target_super_affordances:
        return []
    affordance_entries = []
    for target_super_affordance in target_super_affordances:
        affordance_entries.append({'affordance': target_super_affordance.affordance.__name__, 'commodity_flags': str(target_super_affordance.affordance.commodity_flags) if target_super_affordance.affordance.commodity_flags else ''})
    return affordance_entries

@GsiHandler('sim_buffs_view', sim_buff_schema)
def generate_sim_buffs_view_data(sim_id:int=None):
    buffs_view_data = []
    sim_info = _get_sim_info_by_id(sim_id)
    if sim_info is not None:
        buff_component = sim_info.Buffs
        if buff_component is None:
            return buffs_view_data
        sim = sim_info.get_sim_instance()
        now = services.time_service().sim_now
        for buff in buff_component:
            entry = {'sim_id': str(sim_id), 'name': buff.__class__.__name__, 'visible': str(buff.visible), 'success_modifier': buff.success_modifier, 'mood': buff.mood_type.__name__ if buff.mood_type is not None else 'None', 'mood_weight': buff.mood_weight, 'mood_override': buff.mood_override.__name__ if buff.mood_override is not None else 'None', 'exclusive_index': str(buff.exclusive_index)}
            if buff.commodity is not None:
                entry['commodity'] = buff.commodity.__name__
                (absolute_time, rate) = buff.get_timeout_time()
                entry['timeout'] = '{} : Rate({})'.format(str(date_and_time.DateAndTime(absolute_time)), rate)
            else:
                entry['commodity'] = ('None',)
                entry['timeout'] = ''
            static_commodities_added = []
            for static_commodity in buff.static_commodity_to_add:
                static_commodities_added.append({'static_commodity_name': static_commodity.__name__})
            entry['static_commodities'] = static_commodities_added
            entry['autonomy_modifiers'] = []
            entry['reference_modifiers'] = []
            entry['interactions'] = []
            entry['appearance_modifiers'] = []
            if buff.interactions is not None:
                for mixer_affordance in buff.interactions.interaction_items:
                    if mixer_affordance.lock_out_time_initial is not None:
                        min_lockout_initial = mixer_affordance.lock_out_time_initial.lower_bound
                        max_lockout_initial = mixer_affordance.lock_out_time_initial.upper_bound
                    else:
                        min_lockout_initial = 0
                        max_lockout_initial = 0
                    if mixer_affordance.lock_out_time is not None:
                        min_lockout = mixer_affordance.lock_out_time.interval.lower_bound
                        max_lockout = mixer_affordance.lock_out_time.interval.upper_bound
                    else:
                        min_lockout = 0
                        max_lockout = 0
                    if sim is not None and (mixer_affordance.lock_out_time_initial is not None or mixer_affordance.lock_out_time is not None):
                        unlock_time = sim._mixers_locked_out.get(mixer_affordance, None)
                        if unlock_time is not None:
                            unlock_time = str(unlock_time - now)
                        else:
                            unlock_time = 'Currently Unlocked'
                    else:
                        unlock_time = 'Does Not Lock'
                    entry['interactions'].append({'affordance': mixer_affordance.__name__, 'min_lockout_initial': min_lockout_initial, 'max_lockout_initial': max_lockout_initial, 'min_lockout': min_lockout, 'max_lockout': max_lockout, 'unlock_time': unlock_time})
            entry['super_affordances'] = _buff_super_affordance_output(buff.super_affordances)
            entry['target_super_affordances'] = _buff_target_super_affordance_output(buff.target_super_affordances)
            for (index, modifier) in enumerate(buff.game_effect_modifier._game_effect_modifiers):
                if isinstance(modifier, AutonomyModifier):
                    for (attribute_name, attribute_value) in vars(modifier).items():
                        entry['autonomy_modifiers'].append({'game_effect_index': index, 'attribute_name': attribute_name, 'attribute_value': str(attribute_value)})
                else:
                    buff_entry = {'type': str(modifier.modifier_type)}
                    if modifier.modifier_type == GameEffectType.AFFORDANCE_MODIFIER:
                        buff_entry['reference'] = ('{}'.format([reference_name for reference_name in modifier.debug_affordances_gen()]),)
                        buff_entry['score_modifier'] = (modifier._score_bonus,)
                        buff_entry['success_modifier'] = (modifier._success_modifier,)
                    elif modifier.modifier_type == GameEffectType.EFFECTIVE_SKILL_MODIFIER:
                        buff_entry['reference'] = str(modifier.modifier_key)
                        buff_entry['score_modifier'] = (modifier.modifier_value,)
                    entry['reference_modifiers'].append(buff_entry)
            if buff.appearance_modifier:
                for tuned_modifier in buff.appearance_modifier.appearance_modifiers:
                    buff_entry = {'modifier': repr(tuned_modifier)}
                    entry['appearance_modifiers'].append(buff_entry)
            buffs_view_data.append(entry)
    return buffs_view_data

    sub_schema.add_field('name', label='Name')
    sub_schema.add_field('visible', label='Visible')
    sub_schema.add_field('mood', label='Mood')
    sub_schema.add_field('mood_weight', label='Mood Weight', type=GsiFieldVisualizers.INT)
    sub_schema.add_field('name', label='Name')
    cheat.add_token_param('sim_id')
    cheat.add_token_param('trait_name')
    cheat.add_token_param('sim_id')
def generate_all_traits():
    instance_manager = services.get_instance_manager(Types.TRAIT)
    if instance_manager.all_instances_loaded:
        return [cls.__name__ for cls in services.get_instance_manager(Types.TRAIT).types.values()]
    else:
        return []

def add_trait_cheats(manager):
    with sim_trait_schema.add_view_cheat('traits.equip_trait', label='Add Trait') as cheat:
        cheat.add_token_param('trait_name', dynamic_token_fn=generate_all_traits)
        cheat.add_token_param('sim_id')

@GsiHandler('sim_traits_view', sim_trait_schema)
def generate_sim_traits_view_data(sim_id:int=None):
    traits_view_data = []
    sim_info = _get_sim_info_by_id(sim_id)
    if sim_info is not None:
        for trait in sim_info.trait_tracker.equipped_traits:
            entry = {'sim_id': str(sim_id), 'trait_name': trait.__name__, 'trait_type': trait.trait_type.name, 'num_buffs': len(trait.buffs)}
            entry['linked_buffs'] = []
            for buff in trait.buffs:
                buff_type = buff.buff_type
                buff_entry = {'name': buff_type.__name__, 'visible': str(buff_type.visible), 'commodity': buff_type.commodity.__name__ if buff_type.commodity is not None else 'None', 'mood': buff_type.mood_type.__name__ if buff_type.mood_type is not None else 'None', 'mood_weight': buff_type.mood_weight}
                entry['linked_buffs'].append(buff_entry)
            entry['conflict_traits'] = []
            for conflict_trait in trait.conflicting_traits:
                conflict_trait_entry = {'name': conflict_trait.__name__}
                entry['conflict_traits'].append(conflict_trait_entry)
            traits_view_data.append(entry)
    return traits_view_data

def enable_sim_motive_graph_logging(*args, enableLog=False, **kwargs):
    global sim_motive_graph_alarm
    if enableLog and sim_motive_graph_alarm is None:
        sim_motive_graph_alarm = alarms.add_alarm(sim_motive_archiver, TimeSpan(5000), lambda _: archive_sim_motives(), repeating=True)
    else:
        alarms.cancel_alarm(sim_motive_graph_alarm)
        sim_motive_graph_alarm = None

def archive_sim_motives():
    sim_info_manager = services.sim_info_manager()
    if sim_info_manager is None:
        logger.error('Archiving sim motives when the sim_info_manager is absent.')
        return
    all_motives = ['motive_fun', 'motive_social', 'motive_hygiene', 'motive_hunger', 'motive_energy', 'motive_bladder']
    sim_infos = list(sim_info_manager.values())
    for sim_info in sim_infos:
        sim = sim_info.get_sim_instance()
        if sim is not None:
            archive_data = {}
            for motive in all_motives:
                cur_stat = get_tunable_instance(sims4.resources.Types.STATISTIC, motive, exact_match=True)
                tracker = sim.get_tracker(cur_stat)
                cur_value = tracker.get_value(cur_stat) if tracker is not None else 0
                archive_data[motive] = cur_value
            archive_data['sim_id'] = str(sim.sim_id)
            sim_motive_archiver.archive(object_id=sim.id, data=archive_data)

@GsiHandler('sim_vital_view', sim_vital_schema)
def generate_sim_vital_view_data(sim_id:int=None):
    vital_view_data = []
    sim_info = _get_sim_info_by_id(sim_id)
    if sim_info is None:
        return vital_view_data
    buff_component = sim_info.Buffs
    if buff_component is not None:
        for buff in buff_component:
            entry = {'sim_id': str(sim_id), 'name': buff.__class__.__name__, 'type': 'Buff', 'visible': str(buff.visible), 'data': 'visible={}'.format(buff.visible)}
            vital_view_data.append(entry)
    if sim_info.trait_tracker.equipped_traits is not None:
        for trait in sim_info.trait_tracker.equipped_traits:
            entry = {'sim_id': str(sim_id), 'name': trait.__name__, 'type': 'Trait', 'data': 'type={}'.format(trait.trait_type.name)}
            vital_view_data.append(entry)
    if sim_info.statistic_tracker is not None:
        for stat in list(sim_info.statistic_tracker):
            entry = {'simId': str(sim_id), 'name': type(stat).__name__, 'type': 'Statistic', 'data': 'min={}, max={}, current={}'.format(stat.min_value, stat.max_value, stat.get_value())}
            vital_view_data.append(entry)
        for stat in sim_info.all_skills():
            entry = {'simId': str(sim_id), 'name': type(stat).__name__, 'type': 'Skill', 'data': 'min={}, max={}, current={}'.format(stat.min_value, stat.max_value, stat.get_value())}
            vital_view_data.append(entry)
    if sim_info.commodity_tracker is not None:
        for stat in list(sim_info.commodity_tracker):
            entry = {'simId': str(sim_id), 'name': type(stat).__name__, 'type': 'Commodity', 'data': 'min={}, max={}, current={}'.format(stat.min_value, stat.max_value, stat.get_value())}
            vital_view_data.append(entry)
    if sim_info.static_commodity_tracker is not None:
        for stat in list(sim_info.static_commodity_tracker):
            entry = {'name': type(stat).__name__, 'type': 'Static Commodity', 'data': 'ad_data={}'.format(stat.ad_data)}
            vital_view_data.append(entry)
    return vital_view_data

    cheat.add_token_param('name')
    cheat.add_input_param(label='Value', default='100')
    cheat.add_token_param('simId')
    cheat.add_token_param('name')
    cheat.add_token_param('simId')
    cheat.add_token_param('name')
    cheat.add_static_param(1)
    cheat.add_token_param('simId')
@GsiHandler('commodity_and_stat_view', commodity_and_stat_view_schema)
def generate_sim_commodity_and_stat_view_data(sim_id:int=None, filter=None):
    filter_list = parse_filter_to_list(filter)
    if filter_list is not None and FILTER_WORKING_SET in filter_list:
        filter_list.extend(f for f in FILTER_WORKING_SET_FILTERS if f not in filter_list)
    data = []
    cur_sim_info = _get_sim_info_by_id(sim_id)
    if cur_sim_info is not None:
        if cur_sim_info.static_commodity_tracker is not None:
            for statistic in list(cur_sim_info.commodity_tracker):
                if not isinstance(statistic, statistics.commodity.Commodity):
                    pass
                elif filter_list is not None and not any(a_filter.lower() in type(statistic).__name__.lower() for a_filter in filter_list):
                    pass
                else:
                    data.append({'simId': str(sim_id), 'name': type(statistic).__name__, 'value': statistic.get_value(), 'percentFull': statistic.get_value()/statistic.max_value*100 if statistic.max_value != 0 else 0})
        if cur_sim_info.statistic_tracker is not None:
            for stat in list(cur_sim_info.statistic_tracker):
                data.append({'simId': str(sim_id), 'name': type(stat).__name__, 'value': stat.get_value(), 'percentFull': (stat.get_value() - stat.min_value)/(stat.max_value - stat.min_value)*100})
            for stat in cur_sim_info.all_skills():
                data.append({'simId': str(sim_id), 'name': type(stat).__name__, 'value': stat.get_value(), 'percentFull': stat.get_value()/stat.max_value*100})
    return sorted(data, key=lambda entry: entry['name'])
