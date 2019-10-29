from audio.primitive import TunablePlayAudioAllPacksfrom sims4.localization import LocalizationHelperTuning, TunableLocalizedStringFactoryimport servicesimport sims4.logimport sims4.resourceslogger = sims4.log.Logger('Holiday', default_owner='jjacobson')
class CustomHoliday:
    CALENDAR_ALERT_DESCRIPTION = TunableLocalizedStringFactory(description='\n        Description that shows up in the calendar alert.\n        0 - Holiday Name\n        ')
    GENERIC_HOLIDAY_START_AUDIO = TunablePlayAudioAllPacks(description="\n        The holiday sting that we should play when starting this holiday if it\n        doesn't have a specific one set.\n        ")

    def __init__(self, holiday_id, holiday_type):
        self._holiday_id = holiday_id
        self._holiday_type = holiday_type
        self._traditions = None
        self._name = None
        self._localized_custom_name = None
        self._icon = None
        self._time_off_work = None
        self._time_off_school = None
        self._lot_decoration_preset = None

    @property
    def can_be_modified(self):
        return True

    @property
    def holiday_id(self):
        return self._holiday_id

    @property
    def traditions(self):
        if self._traditions is None:
            return self._holiday_type.traditions
        return self._traditions

    @property
    def display_name(self):
        if self._name is None:
            return self._holiday_type.display_name
        if self._localized_custom_name is None:
            self._localized_custom_name = LocalizationHelperTuning.get_raw_text(self._name)
        return self._localized_custom_name

    @property
    def display_icon(self):
        if self._icon is None:
            return self._holiday_type.display_icon
        return self._icon

    @property
    def time_off_work(self):
        if self._time_off_work is None:
            return self._holiday_type.time_off_work
        return self._time_off_work

    @property
    def time_off_school(self):
        if self._time_off_school is None:
            return self._holiday_type.time_off_school
        return self._time_off_school

    @property
    def decoration_preset(self):
        return self._lot_decoration_preset

    @property
    def calendar_alert_description(self):
        if self._holiday_type is not None:
            return self._holiday_type.calendar_alert_description
        return CustomHoliday.CALENDAR_ALERT_DESCRIPTION

    @property
    def audio_sting(self):
        if self._holiday_type is not None:
            return self._holiday_type.audio_sting
        return CustomHoliday.GENERIC_HOLIDAY_START_AUDIO

    def save_holiday(self, msg):
        msg.holiday_type = self._holiday_id
        if self._traditions is not None:
            for tradition in self._traditions:
                msg.traditions.append(tradition.guid64)
        if self._name is not None:
            msg.name = self._name
        if self._icon is not None:
            icon_proto = sims4.resources.get_protobuff_for_key(self._icon)
            msg.icon = icon_proto
        if self._time_off_work is not None:
            msg.time_off_for_work = self._time_off_work
        if self._time_off_school is not None:
            msg.time_off_for_school = self._time_off_school
        if self._lot_decoration_preset is not None:
            msg.lot_decoration_preset = self._lot_decoration_preset.guid64

    def load_holiday(self, msg):
        self._traditions = []
        tradition_manager = services.get_instance_manager(sims4.resources.Types.HOLIDAY_TRADITION)
        for tradition_guid in msg.traditions:
            tradition = tradition_manager.get(tradition_guid)
            if tradition is None:
                pass
            else:
                self.traditions.append(tradition)
        if msg.HasField('name'):
            self._name = msg.name
        else:
            if self._holiday_type is None:
                logger.error('Trying to load holiday {} with no HolidayDefinition and no name set.', self._holiday_id)
            self._name = None
        self._localized_custom_name = None
        if msg.HasField('icon'):
            self._icon = sims4.resources.Key(msg.icon.type, msg.icon.instance, msg.icon.group)
        else:
            if self._holiday_type is None:
                logger.error('Trying to load holiday {} with no HolidayDefinition and no icon set.', self._holiday_id)
            self._icon = None
        if msg.HasField('time_off_for_work'):
            self._time_off_work = msg.time_off_for_work
        else:
            if self._holiday_type is None:
                logger.error('Trying to load holiday {} with no HolidayDefinition and no time off work set.', self._holiday_id)
            self._time_off_work = None
        if msg.HasField('time_off_for_school'):
            self._time_off_school = msg.time_off_for_school
        else:
            if self._holiday_type is None:
                logger.error('Trying to load holiday {} with no HolidayDefinition and no time off school set.', self._holiday_id)
            self._time_off_school = None
        lot_decoration_preset_manager = services.get_instance_manager(sims4.resources.Types.LOT_DECORATION_PRESET)
        self._lot_decoration_preset = lot_decoration_preset_manager.get(msg.lot_decoration_preset)
