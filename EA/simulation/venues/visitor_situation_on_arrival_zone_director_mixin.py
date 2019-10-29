from sims4.tuning.tunable import OptionalTunable, Tunablefrom singletons import DEFAULTfrom situations.situation import Situationfrom situations.situation_guest_list import SituationGuestList, SituationGuestInfo, SituationInvitationPurposeimport servicesimport sims4logger = sims4.log.Logger('VisitorSituationOnArrivalZone', default_owner='cjiang')
class VisitorSituationOnArrivalZoneDirectorMixin:
    INSTANCE_TUNABLES = {'user_sim_arrival_situation': Situation.TunableReference(description='\n            The situation to place all of the Sims from the users household\n            in when they arrive.\n            '), 'place_all_user_sims_in_same_arrival_situation': Tunable(description='\n            If this is enabled then all user sims will be placed in the same\n            situation instead of each in their own situation.\n            ', tunable_type=bool, default=False), 'place_travel_companion_in_same_arrival_situation': Tunable(description='\n            If this is enabled, the travel companion will put into the same\n            situation with user sims. If this checked,\n            place_all_user_sims_in_same_arrival_situation has to be True as\n            well or there will be unit test error.\n            ', tunable_type=bool, default=False), 'travel_companion_arrival_situation': OptionalTunable(description="\n            If enabled then Sims that aren't controllable that travel with the\n            users Sims will be placed in the tuned situation on arrival. If\n            place_travel_companion_in_same_arrival_situation is checked, this\n            needs to be disable or there will be unit test error.\n            ", tunable=Situation.TunableReference(description="\n                If the user invites NPC's to travel with them to this lot then\n                this is the situation that they will be added to.\n                "))}

    @classmethod
    def _verify_tuning_callback(cls):
        if cls.place_travel_companion_in_same_arrival_situation and not cls.place_all_user_sims_in_same_arrival_situation:
            logger.error("{} set place_travel_companion_in_same_arrival_situation to True but doesn't support place_all_user_sims_in_same_arrival_situation, this is invalid.", cls.__name__)
        if cls.place_travel_companion_in_same_arrival_situation and cls.travel_companion_arrival_situation is not None:
            logger.error('{} set place_travel_companion_in_same_arrival_situation to True but specify travel_companion_arrival_situation, this is invalid', cls.__name__)

    def _sim_info_already_in_arrival_situation(self, sim_info, situation_manager):
        seeds = situation_manager.get_zone_persisted_seeds_during_zone_spin_up()
        for seed in seeds:
            if services.current_zone().time_has_passed_in_world_since_zone_save():
                if seed.allow_time_jump:
                    return True
            return True
        return False

    def create_arrival_situation_for_sim(self, sim_info, situation_type=DEFAULT, during_spin_up=False):
        if situation_type is DEFAULT:
            situation_type = self.user_sim_arrival_situation
        situation_manager = services.get_zone_situation_manager()
        if during_spin_up and self._sim_info_already_in_arrival_situation(sim_info, situation_manager):
            return
        guest_list = SituationGuestList(invite_only=True)
        guest_info = SituationGuestInfo.construct_from_purpose(sim_info.id, situation_type.default_job(), SituationInvitationPurpose.INVITED)
        guest_list.add_guest_info(guest_info)
        self.create_arrival_situation(situation_type, guest_list, situation_manager)

    def create_arrival_situation(self, situation_type, guest_list, situation_manager):
        try:
            creation_source = self.instance_name
        except:
            creation_source = str(self)
        situation_manager.create_situation(situation_type, guest_list=guest_list, user_facing=False, creation_source=creation_source)

    def get_all_sim_arrival_guest_list(self, situation_manager, during_spin_up=False):
        sim_infos = [sim_info for sim_info in self.get_user_controlled_sim_infos()]
        if self.place_travel_companion_in_same_arrival_situation:
            sim_infos.extend(self._traveled_sim_infos)
        guest_list = SituationGuestList(invite_only=True)
        for sim_info in sim_infos:
            if during_spin_up and self._sim_info_already_in_arrival_situation(sim_info, situation_manager):
                pass
            else:
                guest_info = SituationGuestInfo.construct_from_purpose(sim_info.id, self.user_sim_arrival_situation.default_job(), SituationInvitationPurpose.INVITED)
                guest_list.add_guest_info(guest_info)
        return guest_list

    def create_situations_during_zone_spin_up(self):
        super().create_situations_during_zone_spin_up()
        situation_manager = services.get_zone_situation_manager()
        if self.place_all_user_sims_in_same_arrival_situation:
            guest_list = self.get_all_sim_arrival_guest_list(situation_manager, during_spin_up=True)
            self.create_arrival_situation(self.user_sim_arrival_situation, guest_list, situation_manager)
        else:
            for sim_info in self.get_user_controlled_sim_infos():
                self.create_arrival_situation_for_sim(sim_info, during_spin_up=True)
        if self.travel_companion_arrival_situation:
            for sim_info in self._traveled_sim_infos:
                if not sim_info.is_selectable:
                    self.create_arrival_situation_for_sim(sim_info, situation_type=self.travel_companion_arrival_situation, during_spin_up=True)

    def handle_sim_summon_request(self, sim_info, purpose):
        self.create_arrival_situation_for_sim(sim_info)
