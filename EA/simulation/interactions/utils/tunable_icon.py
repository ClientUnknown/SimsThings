import randomfrom distributor.shared_messages import IconInfoData, EMPTY_ICON_INFO_DATAfrom interactions import ParticipantType, ParticipantTypeSinglefrom interactions.utils.interaction_liabilities import PRIVACY_LIABILITYfrom sims4.log import LEVEL_ERRORfrom sims4.tuning.tunable import TunableFactory, TunableResourceKey, TunableEnumFlags, TunableVariant, TunablePackSafeResourceKeyimport servicesimport sims4.logimport sims4.resourceslogger = sims4.log.Logger('Icons', default_owner='rmccord')
class TunableIcon(TunableResourceKey):

    def __init__(self, *, description='The icon image to be displayed.', **kwargs):
        super().__init__(*(None,), resource_types=sims4.resources.CompoundTypes.IMAGE, description=description, **kwargs)

class TunableIconAllPacks(TunablePackSafeResourceKey):

    def __init__(self, *, description='The icon image to be displayed.', **kwargs):
        super().__init__(*(None,), resource_types=sims4.resources.CompoundTypes.IMAGE, description=description, **kwargs)

    @property
    def validate_pack_safe(self):
        return False

class TunableIconFactory(TunableFactory):

    @staticmethod
    def factory(_, key, balloon_target_override=None, **kwargs):
        if balloon_target_override is not None:
            return IconInfoData(obj_instance=balloon_target_override)
        return IconInfoData(icon_resource=key)

    FACTORY_TYPE = factory

    def __init__(self, pack_safe=False, **kwargs):
        icon_type = TunableIcon if not pack_safe else TunableIconAllPacks
        super().__init__(key=icon_type(), description='The icon image to be displayed.', **kwargs)

class TunableParticipantTypeIconFactory(TunableFactory):

    @staticmethod
    def factory(resolver, participant_type, balloon_target_override=None, **kwargs):
        if resolver is None:
            logger.callstack('Attempting to use a None resolver in an icon.', level=LEVEL_ERROR, owner='rmccord')
            return EMPTY_ICON_INFO_DATA
        if balloon_target_override is not None:
            return IconInfoData(obj_instance=balloon_target_override)
        icon_targets = resolver.get_participants(participant_type)
        if icon_targets:
            chosen_object = random.choice(icon_targets)
        else:
            chosen_object = None
        return IconInfoData(obj_instance=chosen_object)

    FACTORY_TYPE = factory

    def __init__(self, default_participant_type=None, **kwargs):
        super().__init__(participant_type=TunableEnumFlags(enum_type=ParticipantType, default=default_participant_type or ParticipantType.Actor), description="The Sim who's thumbnail will be used.", **kwargs)

class TunableHolidayIconFactory(TunableFactory):

    @staticmethod
    def factory(resolver, participant_type, balloon_target_override=None, **kwargs):
        if resolver is None:
            logger.callstack('Attempting to use a None resolver in an icon.', level=LEVEL_ERROR, owner='bosee')
            return EMPTY_ICON_INFO_DATA
        if balloon_target_override is not None:
            return IconInfoData(obj_instance=balloon_target_override)
        participant = resolver.get_participant(participant_type)
        if participant is None:
            logger.callstack('Unable to retrieve participant for holiday icon variant.', level=LEVEL_ERROR, owner='bosee')
            return EMPTY_ICON_INFO_DATA
        else:
            holiday_tracker = participant.household.holiday_tracker
            holiday_service = services.holiday_service()
            if holiday_service is not None and holiday_tracker is not None and holiday_tracker.active_holiday_id is not None:
                return IconInfoData(icon_resource=holiday_service.get_holiday_display_icon(holiday_tracker.active_holiday_id))
        return EMPTY_ICON_INFO_DATA

    def __init__(self, default_participant_type=None, **kwargs):
        super().__init__(participant_type=TunableEnumFlags(description="\n                We use this participant's holiday tracker to get the icon.\n                ", enum_type=ParticipantTypeSingle, default=default_participant_type or ParticipantType.Actor), **kwargs)

    FACTORY_TYPE = factory

class TunablePrivacyIconFactory(TunableFactory):

    @staticmethod
    def factory(resolver, balloon_target_override=None, **kwargs):
        if resolver is None:
            logger.callstack('Attempting to use a None resolver in an icon.', level=LEVEL_ERROR, owner='rmccord')
            return EMPTY_ICON_INFO_DATA
        if balloon_target_override is not None:
            return IconInfoData(obj_instance=balloon_target_override)
        else:
            privacy_liability = resolver.get_liability(PRIVACY_LIABILITY)
            if privacy_liability:
                violators = privacy_liability.privacy.violators
                if violators:
                    return IconInfoData(obj_instance=random.choice(list(violators)))
        return EMPTY_ICON_INFO_DATA

    FACTORY_TYPE = factory

    def __init__(self, **kwargs):
        super().__init__(description="\n            Search an interaction's privacy liability to find violating Sims\n            and randomly select one to display an icon of.\n            ", **kwargs)

class TunableLifestyleBrandIconFactory(TunableFactory):

    @staticmethod
    def factory(resolver, participant_type, balloon_target_override=None, **kwargs):
        if resolver is None:
            logger.callstack('Attempting to use a None resolver in an icon.', level=LEVEL_ERROR, owner='rmccord')
            return EMPTY_ICON_INFO_DATA
        if balloon_target_override is not None:
            return IconInfoData(obj_instance=balloon_target_override)
        participant = resolver.get_participant(participant_type)
        if participant is None:
            logger.callstack('Unable to retrieve participant for Lifestyle Brand.', level=LEVEL_ERROR, owner='bosee')
            return EMPTY_ICON_INFO_DATA
        lifestyle_brand_tracker = participant.lifestyle_brand_tracker
        if lifestyle_brand_tracker is None:
            logger.callstack('Unable to find a Lifestyle Brand Tracker for the participant: {}', participant, level=LEVEL_ERROR, owner='rfleig')
            return EMPTY_ICON_INFO_DATA
        lifestyle_brand_icon = lifestyle_brand_tracker.logo
        if lifestyle_brand_icon is None:
            logger.callstack('Unable to find a Lifestyle Brand Logo for the participant: {}', participant, level=LEVEL_ERROR, owner='rfleig')
            return EMPTY_ICON_INFO_DATA
        return IconInfoData(icon_resource=lifestyle_brand_icon)

    FACTORY_TYPE = factory

    def __init__(self, **kwargs):
        super().__init__(participant_type=TunableEnumFlags(description='\n                The Participant who owns the lifestyle brand we want to use.\n                ', enum_type=ParticipantTypeSingle, default=ParticipantType.Actor), **kwargs)

class TunableIconVariant(TunableVariant):

    def __init__(self, default_participant_type=None, icon_pack_safe=False, **kwargs):
        if default_participant_type is not None:
            default = 'participant'
        else:
            default = 'resource_key'
        super().__init__(resource_key=TunableIconFactory(pack_safe=icon_pack_safe), participant=TunableParticipantTypeIconFactory(default_participant_type=default_participant_type), privacy=TunablePrivacyIconFactory(), tradition=TunableHolidayIconFactory(), lifestyle_brand=TunableLifestyleBrandIconFactory(), default=default, **kwargs)
