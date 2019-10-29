from gsi_handlers.gameplay_archiver import GameplayArchiver
    sub_schema.add_field('appearance_modifier', label='Appearance Modifier', width=2)
    sub_schema.add_field('is_permanent', label='Is Permanent', width=2)
    sub_schema.add_field('chosen_modifier', label='Chosen Modifier', width=2)
def add_appearance_modifier_data(sim_info, appearance_modifiers, priority, apply_to_all_outfits, source, chosen_modifier):
    entry = {}
    entry['sim_id'] = sim_info.id
    entry['request_type'] = 'Add Appearance Modifier'
    entry['source'] = str(source)
    entry['priority'] = str(priority)
    entry['apply_to_all_outfits'] = apply_to_all_outfits
    modifiers = []
    for item in appearance_modifiers:
        modifiers.append({'appearance_modifier': str(item.modifier), 'is_permanent': item.modifier.is_permanent_modification, 'chosen_modifier': str(chosen_modifier is item.modifier)})
    entry['Breakdown'] = modifiers
    archiver.archive(data=entry, object_id=sim_info.id)

def remove_appearance_modifier_data(sim_info, appearance_modifiers, source):
    entry = {}
    entry['sim_id'] = sim_info.id
    entry['request_type'] = 'Remove All Appearance Modifiers'
    entry['source'] = str(source)
    modifiers = []
    for modifier in appearance_modifiers:
        modifiers.append({'appearance_modifier': str(modifier)})
    entry['Breakdown'] = modifiers
    archiver.archive(data=entry, object_id=sim_info.id)
