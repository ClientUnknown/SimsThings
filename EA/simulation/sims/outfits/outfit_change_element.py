from element_utils import build_critical_section, build_critical_section_with_finally, maybefrom elements import ParentElementfrom event_testing.tests import TunableTestSetfrom interactions import ParticipantTypefrom sims.outfits.outfit_change import TunableOutfitChangefrom sims.outfits.outfit_enums import OutfitChangeReason, OutfitCategoryfrom sims.outfits.outfit_generator import TunableOutfitGeneratorSnippetfrom sims4.tuning.tunable import HasTunableFactory, AutoFactoryInit, TunableEnumFlags, OptionalTunable, TunableTuple, Tunable, TunableEnumEntry, TunableVariant, HasTunableSingletonFactory
class XevtOutfitChangeForReason(HasTunableSingletonFactory, AutoFactoryInit):
    FACTORY_TUNABLES = {'reason': TunableEnumEntry(description="\n            Outfit to change into. Tuning 'Invalid' will keep the Sim in their\n            current outfit.\n            ", tunable_type=OutfitChangeReason, default=OutfitChangeReason.Invalid)}

    def get_xevt_outfit(self, sim_info, interaction):
        return sim_info.get_outfit_for_clothing_change(interaction, self.reason)

    def generate_xevt_outfit(self, sim_info):
        pass

class XevtOutfitChangeForTags(HasTunableSingletonFactory, AutoFactoryInit):
    FACTORY_TUNABLES = {'outfit_category': TunableEnumEntry(description='\n            The outfit category to use to generate an outfit and change into.\n            ', tunable_type=OutfitCategory, default=OutfitCategory.EVERYDAY, invalid_enums=(OutfitCategory.CURRENT_OUTFIT,)), 'generator': TunableOutfitGeneratorSnippet()}

    def get_xevt_outfit(self, *args):
        return (self.outfit_category, 0)

    def generate_xevt_outfit(self, sim_info):
        self.generator(sim_info, self.outfit_category)

class ChangeOutfitElement(ParentElement, HasTunableFactory, AutoFactoryInit):
    FACTORY_TUNABLES = {'subject': TunableEnumFlags(description='\n            The participant of who will change their outfit.\n            ', enum_type=ParticipantType, default=ParticipantType.Actor), 'outfit_change': TunableOutfitChange(description='\n            The change that you want to occur.\n            '), 'outfit_change_exit_test': TunableTestSet(description="\n            This test must pass in order for the exit change to be applied\n            successfully. Note: unlike the regular Outfit Change tunables, this\n            test is evaluated when the change executes, not when it is built. It\n            can therefore take into account any changes that happened during the\n            element's enclosed sequence.\n            "), 'xevt_outfit_change': OptionalTunable(description='\n            If enabled, outfit change will change on xevt.\n            ', tunable=TunableTuple(xevt_id=Tunable(description='\n                    Xevt id to trigger outfit change on.\n                    ', tunable_type=int, default=100), outfit_change=TunableVariant(description='\n                    The type of outfit to change into.\n                    ', for_reason=XevtOutfitChangeForReason.TunableFactory(), for_tags=XevtOutfitChangeForTags.TunableFactory(), default='for_reason')))}

    def __init__(self, interaction, *args, sequence=(), **kwargs):
        super().__init__(*args, **kwargs)
        self.interaction = interaction
        self.sequence = sequence
        subject = self.interaction.get_participant(self.subject)
        self.outfits = subject.get_outfits()
        self.sim_info = self.outfits.get_sim_info()
        self.entry_outfit = self.outfit_change.get_on_entry_outfit(interaction, sim_info=self.sim_info)
        if self.entry_outfit is not None:
            self.sim_info.add_preload_outfit(self.entry_outfit)
        if self.xevt_outfit_change is None:
            self.xevt_outfit = None
        else:
            if self.entry_outfit is not None:
                self.sim_info.set_previous_outfit(None)
            self.xevt_outfit = self.xevt_outfit_change.outfit_change.get_xevt_outfit(self.sim_info, interaction)
            self.sim_info.add_preload_outfit(self.xevt_outfit)
        self._xevt_handle = None
        if self.outfit_change.has_exit_change(interaction, sim_info=self.sim_info) and (self.entry_outfit is not None or self.xevt_outfit is not None):
            self.sim_info.set_previous_outfit(None)
        self.exit_outfit = self.outfit_change.get_on_exit_outfit(interaction, sim_info=self.sim_info)
        if self.exit_outfit is not None:
            self.sim_info.add_preload_outfit(self.exit_outfit)

    def _run_xevt_outfit_change(self):
        self.xevt_outfit_change.outfit_change.generate_xevt_outfit(self.sim_info)
        self.sim_info.set_current_outfit(self.xevt_outfit)

    def _run(self, timeline):
        sequence = self.sequence
        if self.entry_outfit is not None:
            sequence = build_critical_section(self.outfit_change.get_on_entry_change(self.interaction, sim_info=self.sim_info), sequence)
        if self.exit_outfit is not None:
            resolver = self.interaction.get_resolver()

            def on_oufit_change_exit(_):
                if self.sim_info._current_outfit != self.exit_outfit and self.outfit_change_exit_test.run_tests(resolver):
                    self.sim_info.set_current_outfit(self.exit_outfit)

            sequence = build_critical_section_with_finally(build_critical_section(sequence, maybe(lambda : self.outfit_change_exit_test.run_tests(resolver), self.outfit_change.get_on_exit_change(self.interaction, sim_info=self.sim_info))), on_oufit_change_exit)
        if self.xevt_outfit is not None:

            def register_xevt(_):
                self._xevt_handle = self.interaction.animation_context.register_event_handler(lambda _: self._run_xevt_outfit_change(), handler_id=self.xevt_outfit_change.xevt_id)

            def release_xevt(_):
                self._xevt_handle.release()
                self._xevt_handle = None

            sequence = build_critical_section(register_xevt, sequence, release_xevt)
        return timeline.run_child(sequence)
