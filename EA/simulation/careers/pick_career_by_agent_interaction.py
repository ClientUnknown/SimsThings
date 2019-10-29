from event_testing.resolver import SingleSimResolverfrom sims4.resources import Typesfrom sims4.tuning.tunable import TunableList, TunableReferencefrom sims4.tuning.tunable_base import GroupNamesfrom traits.trait_tracker import TraitPickerSuperInteractionimport services
class PickCareerByAgentInteraction(TraitPickerSuperInteraction):
    INSTANCE_TUNABLES = {'pickable_careers': TunableList(description='\n            A list of careers whose available agents will be used to populate\n            the picker. When an available agent is selected, the sim actor will\n            be placed in the associated career. A career may have multiple\n            agents, in which case each will appear and each will correspond to\n            that career.\n            ', tunable=TunableReference(manager=services.get_instance_manager(Types.CAREER), pack_safe=True), tuning_group=GroupNames.PICKERTUNING, unique_entries=True)}

    @classmethod
    def _get_agent_traits_for_career_gen(cls, sim_info, career):
        career_history = sim_info.career_tracker.career_history
        (entry_level, _, career_track) = career.get_career_entry_level(career_history, SingleSimResolver(sim_info))
        for agent_trait in career_track.career_levels[entry_level].agents_available:
            yield agent_trait

    @classmethod
    def _trait_selection_gen(cls, target):
        for career in cls.pickable_careers:
            if target.sim_info.career_tracker.has_career_by_uid(career.guid64):
                pass
            else:
                yield from cls._get_agent_traits_for_career_gen(target.sim_info, career)

    def on_choice_selected(self, choice_tag, **kwargs):
        if choice_tag is None:
            return
        sim_info = self.target.sim_info
        for career in self.pickable_careers:
            if choice_tag in self._get_agent_traits_for_career_gen(sim_info, career):
                sim_info.career_tracker.add_career(career(sim_info), post_quit_msg=False)
                super().on_choice_selected(choice_tag, **kwargs)
                return
