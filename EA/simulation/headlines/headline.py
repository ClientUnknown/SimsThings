from distributor.ops import DisplayHeadlinefrom distributor.system import Distributorfrom interactions.utils.tunable_icon import TunableIconfrom objects import ALL_HIDDEN_REASONS_EXCEPT_UNINITIALIZEDfrom sims4.localization import TunableLocalizedStringfrom sims4.tuning.instances import HashedTunedInstanceMetaclassfrom sims4.tuning.tunable import OptionalTunable, TunableTuple, Tunable, TunableEnumEntry, HasTunableReference, TunableMappingfrom sims4.tuning.tunable_base import ExportModesimport enumimport servicesimport sims4.resources
class FXType(enum.Int):
    NO_EFFECT = 0
    INCREASE = 1
    DECREASE = 2

class HeadlineUpdateData(TunableTuple):

    def __init__(self, description='A grouping of headline update data.', **kwargs):
        super().__init__(description=description, icon=TunableIcon(description='\n                The icon that we will use for this update.\n                '), minimum_value=Tunable(description='\n                The minimum value that this update level will be used.\n                ', tunable_type=float, default=0.0), maximum_value=Tunable(description='\n                The maximum value that this update level will be used.\n                ', tunable_type=float, default=1.0), fx=TunableEnumEntry(description='\n                The fx on the flash timeline that should be used.\n                ', tunable_type=FXType, default=FXType.NO_EFFECT), **kwargs)

class Headline(HasTunableReference, metaclass=HashedTunedInstanceMetaclass, manager=services.get_instance_manager(sims4.resources.Types.HEADLINE)):
    INSTANCE_TUNABLES = {'text': OptionalTunable(description='\n            If enabled then this headline will have text displayed along the\n            icon.\n            ', tunable=TunableLocalizedString(description='\n                The text to display along the icon on this headline.\n                '), export_modes=ExportModes.All, export_class_name='HeadlineTextOptionalTunable'), 'levels': TunableMapping(description='\n            Different Headline update levels.\n            ', key_type=Tunable(description='\n                The level key.\n                ', tunable_type=int, default=1), value_type=HeadlineUpdateData(description='\n                Level data.\n                '), tuple_name='HeadlineLevelMapping', export_modes=ExportModes.All), 'priority': Tunable(description='\n            The display priority of this headline so that if multiple headlines\n            are triggered at the same time, this value will be used to\n            determine which one has priority of another.  Lower values indicate\n            a higher priority.\n            ', tunable_type=int, default=0, export_modes=ExportModes.All), 'show_during_sim_info_creation': Tunable(description='\n            If true, this headline will be shown on sims when they are first \n            created. One case in which this will occur is if a SimFilter had to\n            create a new sim for a situation. If false, will not show the\n            headline.\n            ', tunable_type=bool, default=True)}

    @classmethod
    def send_headline_message(cls, sim_info, value, icon_modifier=None):
        if cls.show_during_sim_info_creation or not sim_info.get_sim_instance(allow_hidden_flags=ALL_HIDDEN_REASONS_EXCEPT_UNINITIALIZED):
            return
        headline_op = DisplayHeadline(sim_info, cls, value, icon_modifier)
        Distributor.instance().add_op(sim_info, headline_op)
