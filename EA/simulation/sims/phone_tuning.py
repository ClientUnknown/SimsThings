from event_testing.tests import TunableTestVariantfrom interactions.utils.tunable_icon import TunableIconfrom sims4.localization import TunableLocalizedStringFactoryfrom sims4.tuning.tunable import Tunable, TunableTuple, TunableList, TunableReferencefrom sims4.tuning.tunable_base import ExportModesimport servicesimport sims4.resources
class PhoneTuning:
    DISABLE_PHONE_TESTS = TunableList(description='\n        List of tests and tooltip that when passed will disable opening the\n        phone.\n        ', tunable=TunableTuple(description='\n            Test that should pass for the phone to be disabled and its tooltip\n            to display to the player when he clicks on the phone.\n            ', test=TunableTestVariant(), tooltip=TunableLocalizedStringFactory()))

    class TunablePhoneColorTuple(TunableTuple):

        def __init__(self, *args, **kwargs):
            super().__init__(*args, bg_image=TunableIcon(description='\n                Image resource to display as UI phone panel background.\n                '), icon=TunableIcon(description='\n                Icon to display for phone color selector swatch.\n                '), phone_trait=TunableReference(description='\n                Trait associated with cell phone color.\n                ', allow_none=True, manager=services.get_instance_manager(sims4.resources.Types.TRAIT)), **kwargs)

    PHONE_COLOR_VARIATION_TUNING = TunableList(description='\n        A list of all of the different colors you can set the cell phone cover to be.\n        ', tunable=TunablePhoneColorTuple(), export_modes=(ExportModes.ClientBinary,))
