from interactions.base.multi_picker_interaction import MultiPickerInteractionimport sims4.loglogger = sims4.log.Logger('Dialog', default_owner='rfleig')TEXT_INPUT_BRAND_NAME = 'brand_name'
class LifestyleBrandMultiPickerInteraction(MultiPickerInteraction):

    def _create_dialog(self, owner, **kwargs):
        dialog = super()._create_dialog(owner, **kwargs)
        dialog.add_text_listener(self._on_text_input)
        dialog.existing_text = self._existing_text()
        return dialog

    def _existing_text(self):
        sim = self.sim
        lifestyle_brand_tracker = sim.sim_info.lifestyle_brand_tracker
        if lifestyle_brand_tracker is None:
            logger.error("Sim {} doesn't have a Lifestyle Brand Tracker, how is this possible?", sim)
            return (None, None)
        return (TEXT_INPUT_BRAND_NAME, lifestyle_brand_tracker.brand_name)

    def _on_text_input(self, dialog, text_input_name, text_input):
        sim = self.sim
        lifestyle_brand_tracker = sim.sim_info.lifestyle_brand_tracker
        if lifestyle_brand_tracker is None:
            logger.error("Sim {} doesn't have a Lifestyle Brand Tracker, how is this possible?", sim)
            return
        lifestyle_brand_tracker.brand_name = text_input
