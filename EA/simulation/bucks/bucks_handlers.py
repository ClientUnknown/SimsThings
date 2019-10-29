from bucks.bucks_enums import BucksType
    bucks_perks.add_filter(str(bucks_type))
    cheat.add_token_param('name')
    cheat.add_static_param(True)
    cheat.add_token_param('bucks_type_value')
    cheat.add_token_param('sim_id')
@GsiHandler('bucks_perks', bucks_perks)
def generate_bucks_perks_view(sim_id:int=None, filter=None):
    filter_list = parse_filter_to_list(filter)
    bucks_perks_data = []
    perks_instance_manager = services.get_instance_manager(sims4.resources.Types.BUCKS_PERK)
    previous_bucks_type = None
    for perk in perks_instance_manager.types.values():
        if perk.associated_bucks_type != previous_bucks_type:
            perk_specific_bucks_tracker = BucksUtils.get_tracker_for_bucks_type(perk.associated_bucks_type, sim_id)
            previous_bucks_type = perk.associated_bucks_type
        if 'Unlocked Only' in filter_list:
            if not perk_specific_bucks_tracker is None:
                if not perk_specific_bucks_tracker.is_perk_unlocked(perk):
                    pass
                elif len(filter_list) > 1 and str(perk.associated_bucks_type) not in filter_list:
                    pass
                else:
                    bucks_perks_data.append({'sim_id': str(sim_id), 'name': perk.__name__, 'bucks_type': str(perk.associated_bucks_type), 'bucks_type_value': int(perk.associated_bucks_type), 'bucks_tracker_name': str(perk_specific_bucks_tracker), 'is_unlocked': perk_specific_bucks_tracker.is_perk_unlocked(perk) if perk_specific_bucks_tracker is not None else False})
        elif str(perk.associated_bucks_type) not in filter_list:
            pass
        else:
            bucks_perks_data.append({'sim_id': str(sim_id), 'name': perk.__name__, 'bucks_type': str(perk.associated_bucks_type), 'bucks_type_value': int(perk.associated_bucks_type), 'bucks_tracker_name': str(perk_specific_bucks_tracker), 'is_unlocked': perk_specific_bucks_tracker.is_perk_unlocked(perk) if perk_specific_bucks_tracker is not None else False})
        bucks_perks_data.append({'sim_id': str(sim_id), 'name': perk.__name__, 'bucks_type': str(perk.associated_bucks_type), 'bucks_type_value': int(perk.associated_bucks_type), 'bucks_tracker_name': str(perk_specific_bucks_tracker), 'is_unlocked': perk_specific_bucks_tracker.is_perk_unlocked(perk) if filter_list is not None and perk_specific_bucks_tracker is not None else False})
    return bucks_perks_data
