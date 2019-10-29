import randomfrom build_buy import get_current_venuefrom objects import ALL_HIDDEN_REASONSfrom sims4.localization import TunableLocalizedString, LocalizationHelperTuningfrom sims4.tuning.tunable import AutoFactoryInit, HasTunableFactory, TunableList, TunableReference, TunableVariantimport servicesimport sims4.logimport sims4.resourceslogger = sims4.log.Logger('Careers', default_owner='epanero')
class CareerLocation(HasTunableFactory, AutoFactoryInit):

    def __init__(self, career, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._career = career

    def get_company_name(self):
        pass

    def get_persistable_company_name_data(self):
        pass

    def get_zone_id(self):
        return 0

    def is_valid_career_location(self):
        return True

    def save_career_location(self, career_proto):
        pass

    def load_career_location(self, career_proto):
        pass

    def on_npc_start_work(self):
        sim = self._career.sim_info.get_sim_instance(allow_hidden_flags=ALL_HIDDEN_REASONS)
        if sim is not None:
            career = self._career
            sim_info = career.sim_info
            current_track = career.current_track_tuning
            if current_track.goodbye_notification is not None and sim_info.goodbye_notification is not None:

                class _UiDialogNotificationCareerGoodbye:

                    def __init__(self, *args, **kwargs):
                        self._dialog = current_track.goodbye_notification(*args, **kwargs)

                    def show_dialog(self, *args, **kwargs):
                        self._dialog.show_dialog(*args, additional_tokens=career.get_career_text_tokens(), **kwargs)

                sim_info.try_to_set_goodbye_notification(_UiDialogNotificationCareerGoodbye)
            if sim_info.is_at_home and self._career.push_go_to_work_affordance():
                return
            services.get_zone_situation_manager().make_sim_leave_now_must_run(sim)
            career.attend_work()

class CareerLocationRandomCompany(CareerLocation):

    @staticmethod
    def _verify_tunable_callback(instance_class, tunable_name, source, *, company_names):
        if not company_names:
            logger.error('Career location in {} does not specify any company names.', source)

    FACTORY_TUNABLES = {'company_names': TunableList(description="\n            A list of random company names. A Sim's career is assigned one of\n            these and the selection is preserved.\n            ", tunable=TunableLocalizedString(), minlength=1), 'verify_tunable_callback': _verify_tunable_callback}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._company_name = random.choice(self.company_names)

    def __str__(self):
        return 'Company: 0x{:x}'.format(self._company_name.hash)

    def get_company_name(self):
        return self._company_name

    def get_persistable_company_name_data(self):
        return self._career.guid64

    def save_career_location(self, career_proto):
        career_proto.company_name_hash = self._company_name.hash

    def load_career_location(self, career_proto):
        for company_name in self.company_names:
            if career_proto.company_name_hash == company_name.hash:
                self._company_name = company_name

class _CareerLocationVenue(CareerLocation):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._zone_id = 0

    def __str__(self):
        return 'Venue: {}, zone 0x{:x}'.format(self._get_zone_name(), self.get_zone_id())

    def _get_zone_name(self):
        persistence_service = services.get_persistence_service()
        if persistence_service is not None:
            zone_data = persistence_service.get_zone_proto_buff(self._zone_id)
            if zone_data is not None:
                return zone_data.name
        return ''

    def get_company_name(self):
        return LocalizationHelperTuning.get_raw_text(self._get_zone_name())

    def get_persistable_company_name_data(self):
        self._get_zone_name()

    def is_valid_career_location(self):
        if self._zone_id:
            venue_manager = services.venue_manager()
            try:
                venue_key = get_current_venue(self._zone_id)
            except RuntimeError:
                return False
            venue_type = venue_manager.get(venue_key)
            if venue_type in self.venue_types:
                return True
        return False

    def get_zone_id(self):
        return self._zone_id

    def set_zone_id(self, zone_id):
        self._zone_id = zone_id

    def save_career_location(self, career_proto):
        career_proto.zone_id = self._zone_id

    def load_career_location(self, career_proto):
        self._zone_id = career_proto.zone_id

    def on_npc_start_work(self):
        sim_info = self._career.sim_info
        if sim_info.zone_id == self._zone_id:
            return
        return super().on_npc_start_work()

class CareerLocationVenue(_CareerLocationVenue):
    FACTORY_TUNABLES = {'venue_types': TunableList(description='\n            The set of required venue types to be in this career.\n            ', tunable=TunableReference(description='\n                The required venue type for this career.\n                ', manager=services.get_instance_manager(sims4.resources.Types.VENUE), pack_safe=True))}

    def is_valid_career_location(self):
        if not super().is_valid_career_location():
            return False
        business_manager = services.business_service().get_business_manager_for_zone(self._zone_id)
        if business_manager is None:
            return True
        elif business_manager.is_owner_household_active:
            return business_manager.is_employee(self._career.sim_info)
        return True

class CareerLocationServiceNpc(CareerLocationRandomCompany):

    def on_npc_start_work(self):
        sim = self._career.sim_info.get_sim_instance(allow_hidden_flags=ALL_HIDDEN_REASONS)
        if sim is not None:
            self._career.attend_work()

class TunableCareerLocationVariant(TunableVariant):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, company=CareerLocationRandomCompany.TunableFactory(), venue=CareerLocationVenue.TunableFactory(), service_npc=CareerLocationServiceNpc.TunableFactory(), default='company', **kwargs)
