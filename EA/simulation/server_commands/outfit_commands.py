import functoolsfrom cas.cas import get_tags_from_outfitfrom objects.components.mannequin_component import MannequinGroupSharingMode, set_mannequin_group_sharing_modefrom server_commands.argument_helpers import OptionalTargetParam, get_optional_target, OptionalSimInfoParam, TunableInstanceParamfrom sims.outfits.outfit_enums import OutfitCategoryfrom sims4.commands import CommandTypefrom tag import Tagimport sims4.commands
@sims4.commands.Command('outfits.generate_outfit')
def generate_outfit(outfit_category:OutfitCategory, outfit_index:int=0, obj_id:OptionalTargetParam=None, outfit_gen:TunableInstanceParam(sims4.resources.Types.SNIPPET)=None, _connection=None):
    obj = get_optional_target(obj_id, _connection)
    if obj is None:
        return False
    outfits = obj.get_outfits()
    if outfits is None:
        return False
    sim_info = outfits.get_sim_info()
    if outfit_gen is not None:
        fn = functools.partial(outfit_gen, sim_info)
    else:
        fn = sim_info.generate_outfit
    fn(outfit_category=outfit_category, outfit_index=outfit_index)
    output = sims4.commands.Output(_connection)
    output('Generated {} outfit {}.'.format(outfit_category, outfit_index))
    return True

@sims4.commands.Command('outfits.switch_outfit')
def switch_outfit(outfit_category:OutfitCategory=0, outfit_index:int=0, obj_id:OptionalTargetParam=None, _connection=None):
    obj = get_optional_target(obj_id, _connection)
    if obj is None:
        return False
    outfits = obj.get_outfits()
    if outfits is None:
        return False
    sim_info = outfits.get_sim_info()
    sim_info.set_current_outfit((outfit_category, outfit_index))
    return True

@sims4.commands.Command('outfits.info')
def show_outfit_info(obj_id:OptionalTargetParam=None, _connection=None):
    obj = get_optional_target(obj_id, _connection)
    if obj is None:
        return False
    outfits = obj.get_outfits()
    if outfits is None:
        return False
    sim_info = outfits.get_sim_info()
    output = sims4.commands.Output(_connection)
    output('Current outfit: {}'.format(sim_info.get_current_outfit()))
    output('Previous outfit: {}'.format(sim_info.get_previous_outfit()))
    for (outfit_category, outfit_list) in outfits.get_all_outfits():
        output('\t{}'.format(OutfitCategory(outfit_category)))
        for (outfit_index, outfit_data) in enumerate(outfit_list):
            output('\t\t{}: {}'.format(outfit_index, ', '.join(str(part) for part in outfit_data.part_ids)))
    output('')
    return True

@sims4.commands.Command('outfits.set_sharing_mode', command_type=CommandType.Live)
def set_outfit_sharing_mode(outfit_sharing_mode:MannequinGroupSharingMode):
    set_mannequin_group_sharing_mode(outfit_sharing_mode)
    return True

@sims4.commands.Command('outfits.remove_outfit')
def remove_outfit(outfit_category:OutfitCategory, outfit_index:int=0, obj_id:OptionalTargetParam=None, _connection=None):
    obj = get_optional_target(obj_id, _connection)
    if obj is None:
        return False
    outfit_tracker = obj.get_outfits()
    if outfit_tracker is None:
        return False
    outfit_tracker.remove_outfit(outfit_category, outfit_index)
    return True

@sims4.commands.Command('outfits.copy_outfit', command_type=CommandType.Live)
def copy_outfit(destination_outfit_category:OutfitCategory, source_outfit_category:OutfitCategory, source_outfit_index:int=0, obj_id:OptionalTargetParam=None, _connection=None):
    obj = get_optional_target(obj_id, _connection)
    if obj is None:
        return False
    outfit_tracker = obj.get_outfits()
    if outfit_tracker is None:
        return False
    if not outfit_tracker.has_outfit((source_outfit_category, source_outfit_index)):
        return False
    outfit_data = outfit_tracker.get_outfit(source_outfit_category, source_outfit_index)
    destination_outfit = outfit_tracker.add_outfit(destination_outfit_category, outfit_data)
    sim_info = outfit_tracker.get_sim_info()
    sim_info.resend_outfits()
    sim_info.set_current_outfit(destination_outfit)
    return True

@sims4.commands.Command('outfits.get_tags')
def print_outfit_tags(opt_sim:OptionalSimInfoParam=None, _connection=None):
    sim_info = get_optional_target(opt_sim, target_type=OptionalSimInfoParam, _connection=_connection)
    (current_outfit_category, current_outfit_index) = sim_info.get_current_outfit()
    tag_values = set().union(*get_tags_from_outfit(sim_info._base, current_outfit_category, current_outfit_index).values())
    output = sims4.commands.Output(_connection)
    tag_names = [Tag(tag_value).name for tag_value in tag_values]
    tag_names.sort()
    for tag in tag_names:
        output(tag)

@sims4.commands.Command('outfits.current_outfit_info', command_type=sims4.commands.CommandType.Automation)
def get_current_outfit_info(opt_sim:OptionalSimInfoParam=None, _connection=None):
    sim_info = get_optional_target(opt_sim, target_type=OptionalSimInfoParam, _connection=_connection)
    if sim_info is None:
        return False
    (outfit_category, outfit_index) = sim_info.get_current_outfit()
    sims4.commands.automation_output('OutfitInfo; OutfitCategory:{}, OutfitIndex:{}'.format(outfit_category, outfit_index), _connection)
    return True
