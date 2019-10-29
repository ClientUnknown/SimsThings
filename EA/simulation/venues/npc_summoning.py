from sims4.tuning.tunable import HasTunableSingletonFactory, AutoFactoryInitfrom situations import situation_guest_listfrom situations.situation import Situationfrom situations.situation_guest_list import SituationGuestListfrom situations.situation_job import SituationJobimport distributor.opsimport servicesimport sims4.loglogger = sims4.log.Logger('NPCSummoning')
class CreateAndAddToSituation(HasTunableSingletonFactory, AutoFactoryInit):

    @staticmethod
    def _verify_tunable_callback(instance_class, tunable_name, source, value):
        if value.situation_job is not None:
            jobs = value.situation_to_create.get_tuned_jobs()
            if value.situation_job not in jobs:
                logger.error('CreateAndAddToSituation {} references a job {} that is not tuned in the situation {}.', source, value.situation_job, value.situation_to_create, owner='manus')
        elif value.situation_to_create.default_job() is None:
            logger.error('CreateAndAddToSituation {} references a situation {} \n                without referencing a job and the situation does not have a default job.\n                Either tune a default job on the situation or tune a job reference\n                here.', source, value.situation_to_create, owner='sscholl')

    FACTORY_TUNABLES = {'description': 'Create a new situation of this type and add the NPC to its tuned job.', 'situation_to_create': Situation.TunableReference(pack_safe=True), 'situation_job': SituationJob.TunableReference(description="\n            The situation job to assign the sim to. If set to None\n            the sim will be assigned to the situation's default job.\n            ", allow_none=True, pack_safe=True), 'verify_tunable_callback': _verify_tunable_callback}

    def __call__(self, all_sim_infos, purpose=None, host_sim_info=None):
        host_sim_id = host_sim_info.sim_id if host_sim_info is not None else 0
        situation_job = self.situation_job if self.situation_job is not None else self.situation_to_create.default_job()

        def _create_situation(sim_infos):
            guest_list = SituationGuestList(invite_only=True, host_sim_id=host_sim_id)
            for sim_info in sim_infos:
                guest_info = situation_guest_list.SituationGuestInfo.construct_from_purpose(sim_info.sim_id, situation_job, situation_guest_list.SituationInvitationPurpose.INVITED)
                guest_list.add_guest_info(guest_info)
            services.get_zone_situation_manager().create_situation(self.situation_to_create, guest_list=guest_list, user_facing=False)

        if self.situation_to_create.supports_multiple_sims:
            _create_situation(all_sim_infos)
        else:
            for one_sim_info in all_sim_infos:
                _create_situation((one_sim_info,))

class AddToBackgroundSituation(HasTunableSingletonFactory, AutoFactoryInit):

    def __call__(self, sim_infos, purpose=None, host_sim_info=None):
        venue_type = services.get_current_venue()
        if venue_type is None or venue_type.active_background_event_id is None:
            return
        situation = services.get_zone_situation_manager().get(venue_type.active_background_event_id)
        if situation is not None:
            for sim_info in sim_infos:
                situation.invite_sim_to_job(sim_info)

class NotfifyZoneDirector(HasTunableSingletonFactory, AutoFactoryInit):

    def __call__(self, sim_infos, purpose=None, host_sim_info=None):
        zone_director = services.venue_service().get_zone_director()
        for sim_info in sim_infos:
            zone_director.handle_sim_summon_request(sim_info, purpose)

class ResidentialLotArrivalBehavior(HasTunableSingletonFactory, AutoFactoryInit):
    FACTORY_TUNABLES = {'description': '\n            NPC behavior on a residential lot. The behavior is different depending \n            on the lot belonging to the player versus NPC. Greeted behavior can \n            modify behavior as well.\n            ', 'player_sim_lot': CreateAndAddToSituation.TunableFactory(), 'npc_lot_greeted': CreateAndAddToSituation.TunableFactory(), 'npc_lot_ungreeted': CreateAndAddToSituation.TunableFactory()}

    def __call__(self, sim_infos, purpose=None, host_sim_info=None):
        npc_infos = []
        selectable_and_resident_infos = []
        for sim_info in sim_infos:
            if sim_info.is_npc and not sim_info.lives_here:
                npc_infos.append(sim_info)
            else:
                selectable_and_resident_infos.append(sim_info)
        if npc_infos:
            is_active_household_residence = False
            active_household = services.active_household()
            if active_household is not None:
                is_active_household_residence = active_household.considers_current_zone_its_residence()
            if is_active_household_residence:
                if self.player_sim_lot is not None:
                    self.player_sim_lot(npc_infos, host_sim_info)
            elif services.get_zone_situation_manager().is_player_greeted():
                if self.npc_lot_greeted is not None:
                    self.npc_lot_greeted(npc_infos, host_sim_info)
            elif self.npc_lot_ungreeted is not None:
                self.npc_lot_ungreeted(npc_infos, host_sim_info)
        for sim_info in selectable_and_resident_infos:
            if sim_info.get_sim_instance() is None:
                op = distributor.ops.TravelBringToZone([sim_info.sim_id, 0, services.current_zone().id, 0])
                distributor.system.Distributor.instance().add_op_with_no_owner(op)
