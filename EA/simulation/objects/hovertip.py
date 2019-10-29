from sims4.tuning import tunable_basefrom sims4.tuning.tunable import TunableList, TunableTuple, Tunable, TunableEnumEntry, TunableReferencefrom sims4.tuning.tunable_base import FilterTagimport enumimport servicesimport sims4
class HovertipStyle(enum.Int):
    HOVER_TIP_DISABLED = 0
    HOVER_TIP_DEFAULT = 1
    HOVER_TIP_CONSUMABLE_CRAFTABLE = 2
    HOVER_TIP_GARDENING = 3
    HOVER_TIP_COLLECTION = 4
    HOVER_TIP_CUSTOM_OBJECT = 5
    HOVER_TIP_ICON_TITLE_DESCRIPTION = 6
    HOVER_TIP_OBJECT_RELATIONSHIP = 7

class TooltipFields(enum.Int):
    recipe_name = 0
    recipe_description = 1
    percentage_left = 3
    style_name = 4
    quality_description = 5
    header = 6
    subtext = 7
    crafted_by_text = 8
    rarity_text = 9
    simoleon_text = 10
    relic_description = 22
    season_text = 23
    spoiled_time_text = 24
    rel_override_id = 25

class TooltipFieldsComplete(TooltipFields, export=False):
    quality = 11
    servings = 12
    spoiled_time = 13
    simoleon_value = 14
    main_icon = 15
    sub_icons = 16
    inscription = 17
    crafter_sim_id = 18
    custom_name = 19
    custom_description = 20
    stolen_from_text = 21

class TooltipFieldConcatenationType(enum.Int):
    CONCATENATE_BEFORE = 0
    CONCATENATE_AFTER = 1

class TunableHovertipTuple(TunableTuple):

    def __init__(self, **kwargs):
        super().__init__(hovertip_style=TunableEnumEntry(description='\n                Style of the hovertip that will apply this restriction.\n                ', tunable_type=HovertipStyle, default=HovertipStyle.HOVER_TIP_DEFAULT), skill=TunableReference(manager=services.get_instance_manager(sims4.resources.Types.STATISTIC), description='\n                What skill (Reference) to test for\n                '), skill_points=Tunable(description='\n                Skill points to test for.  If the skill_point is tuned to 0, no \n                skill test will be run, it will just test that the Sim\n                has the skill.\n                ', tunable_type=int, default=0), field_name=Tunable(description='\n                This field refers to the field name of the protobuff which should\n                only be showed on a tooltip if the skill requirements are met.\n                ', tunable_type=str, default=''), index=Tunable(description='\n                Index of field_name to hide.\n                If field name to hide is a list.  Passing an index will cause\n                the hovertip to hide this index value out of that list.\n                e.g.  Gardening icons will always send 4 icons which some \n                are only visible depending ont he skill level.\n                ', tunable_type=int, default=0))

class HovertipTuning:
    HOVERTIP_RESTRICTIONS = TunableList(description='\n        List of skill dependencies for tooltip fields.  This will show the \n        tagged fields only if the selected sim matches the skill requirement\n        tuned. \n        e.g.  Only sims with gardening level 2 can see all the sub_icon data\n        of a plant.\n        PS: This tunable is on expert mode since on field_name refers to \n        field names on a protobuff, this should only be tuned by a GPE or with \n        a GPE help.  \n        ', tunable=TunableHovertipTuple(), tuning_filter=FilterTag.EXPERT_MODE, export_modes=tunable_base.ExportModes.All)
