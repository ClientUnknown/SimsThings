from crafting.photography_enums import PhotoStyleTypefrom interactions import ParticipantTypeSingle, ParticipantTypefrom interactions.utils.interaction_elements import XevtTriggeredElementfrom sims4.tuning.tunable import TunableEnumEntryimport sims4logger = sims4.log.Logger('Photography', default_owner='rrodgers')
class SetPhotoFilter(XevtTriggeredElement):
    FACTORY_TUNABLES = {'participant': TunableEnumEntry(description='\n            The participant object that is the photo.\n            ', tunable_type=ParticipantTypeSingle, default=ParticipantType.Object), 'photo_filter': TunableEnumEntry(description='\n            The photo filter that you want this photo to use.\n            ', tunable_type=PhotoStyleType, default=PhotoStyleType.NORMAL)}

    def _do_behavior(self):
        photo_obj = self.interaction.get_participant(self.participant)
        if photo_obj is None:
            logger.error('set_photo_filter basic extra tuned participant does not exist.')
            return False
        canvas_component = photo_obj.canvas_component
        if canvas_component is None:
            logger.error('set_photo_filter basic extra tuned participant does not have a canvas component.')
            return False
        canvas_component.painting_effect = self.photo_filter
        return True
