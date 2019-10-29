from interactions.utils.interaction_elements import XevtTriggeredElementfrom sims4.tuning.tunable import HasTunableFactory, AutoFactoryInit, OptionalTunable, TunableEnumEntryfrom ui.notebook_tuning import NotebookCategoriesimport sims4.loglogger = sims4.log.Logger('Notebook')
class NotebookDisplayElement(XevtTriggeredElement, HasTunableFactory, AutoFactoryInit):
    FACTORY_TUNABLES = {'initial_selected_category': OptionalTunable(description='\n            If enabled, this tuned category will be opened/selected initially \n            in the notebook. Otherwise, as default, leftmost category will be \n            selected.\n            ', tunable=TunableEnumEntry(description='\n                Initial notebook categories.\n                ', tunable_type=NotebookCategories, default=NotebookCategories.INVALID, invalid_enums=(NotebookCategories.INVALID,), pack_safe=True))}

    def _do_behavior(self):
        if self.interaction.sim.sim_info.notebook_tracker is None:
            logger.error("Trying to display a notebook on {} but that Sim doesn't have a notebook tracker. LOD issue?", self.interaction.sim)
            return False
        self.interaction.sim.sim_info.notebook_tracker.generate_notebook_information(initial_selected_category=self.initial_selected_category)
        return True
