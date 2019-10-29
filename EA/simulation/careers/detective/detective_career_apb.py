from careers.career_event_zone_director import CareerEventZoneDirectorProxyfrom careers.detective.detective_career import DetectiveCareerfrom sims4.tuning.tunable_base import GroupNamesfrom situations.bouncer.bouncer_types import BouncerRequestPriority, RequestSpawningOptionfrom situations.situation import Situationfrom situations.situation_guest_list import SituationGuestList, SituationGuestInfofrom situations.situation_job import SituationJobimport servicesimport sims4.telemetryimport telemetry_helperTELEMETRY_GROUP_DETECTIVE = 'DETE'TELEMETRY_HOOK_APB_CALL = 'APBC'TELEMETRY_CLUES_FOUND = 'clue'DECOY_SIM_IDS = 'decoy_sim_ids'detective_apb_telemetry_writer = sims4.telemetry.TelemetryWriter(TELEMETRY_GROUP_DETECTIVE)
class ZoneDirectorApb(CareerEventZoneDirectorProxy):
    INSTANCE_TUNABLES = {'detective_career': DetectiveCareer.TunableReference(description='\n            The career that we want to use to spawn the criminal.\n            ', tuning_group=GroupNames.CAREER), 'apb_situation': Situation.TunableReference(description='\n            The situation controlling the APB. This will manage the criminal Sim\n            as well as all the decoys.\n            ', tuning_group=GroupNames.CAREER), 'apb_neutral_situation': Situation.TunableReference(description='\n            The situation controlling all Sims in the zone, including Sims in\n            the APB situation.\n            ', tuning_group=GroupNames.CAREER), 'apb_situation_job_detective': SituationJob.TunableReference(description='\n            The job that the detective is put into for the duration of the APB.\n            ', tuning_group=GroupNames.CAREER), 'apb_situation_job_decoy': SituationJob.TunableReference(description='\n            The job that the decoys are put into for the duration of the APB.\n            ', tuning_group=GroupNames.CAREER), 'apb_situation_job_criminal': SituationJob.TunableReference(description='\n            The job that the criminal is put into for the duration of the APB.\n            ', tuning_group=GroupNames.CAREER)}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._persisted_decoy_sim_ids = None
        self._apb_situation_id = None

    def create_situations_during_zone_spin_up(self):
        sim_info = self._career_event.sim_info
        career = sim_info.careers.get(self.detective_career.guid64)
        if career is not None:
            situation_manager = services.get_zone_situation_manager()
            situation_manager.create_situation(self.apb_neutral_situation, user_facing=False, creation_source=self.instance_name)
            guest_list = SituationGuestList(invite_only=True, filter_requesting_sim_id=sim_info.sim_id)
            if not career.active_criminal_sim_id:
                career.create_criminal_fixup()
            guest_list.add_guest_info(SituationGuestInfo(career.active_criminal_sim_id, self.apb_situation_job_criminal, RequestSpawningOption.DONT_CARE, BouncerRequestPriority.EVENT_VIP))
            guest_list.add_guest_info(SituationGuestInfo(sim_info.sim_id, self.apb_situation_job_detective, RequestSpawningOption.DONT_CARE, BouncerRequestPriority.EVENT_VIP))
            decoy_sim_ids = career.get_decoy_sim_ids_for_apb(persisted_sim_ids=self._persisted_decoy_sim_ids)
            for decoy in decoy_sim_ids:
                guest_list.add_guest_info(SituationGuestInfo(decoy, self.apb_situation_job_decoy, RequestSpawningOption.DONT_CARE, BouncerRequestPriority.EVENT_VIP))
            self._persisted_decoy_sim_ids = None
            self._apb_situation_id = situation_manager.create_situation(self.apb_situation, guest_list=guest_list, spawn_sims_during_zone_spin_up=True, user_facing=False, creation_source=self.instance_name)
            with telemetry_helper.begin_hook(detective_apb_telemetry_writer, TELEMETRY_HOOK_APB_CALL, sim_info=sim_info) as hook:
                hook.write_int(TELEMETRY_CLUES_FOUND, len(career.get_discovered_clues()))
        return super().create_situations_during_zone_spin_up()

    def _load_custom_zone_director(self, zone_director_proto, reader):
        super()._load_custom_zone_director(zone_director_proto, reader)
        if reader is not None:
            self._persisted_decoy_sim_ids = reader.read_uint64s(DECOY_SIM_IDS, ())

    def _save_custom_zone_director(self, zone_director_proto, writer):
        super()._save_custom_zone_director(zone_director_proto, writer)
        situation_manager = services.get_zone_situation_manager()
        apb_situation = situation_manager.get(self._apb_situation_id)
        if apb_situation is not None:
            sim_ids = (sim.id for sim in apb_situation.all_sims_in_job_gen(self.apb_situation_job_decoy))
            writer.write_uint64s(DECOY_SIM_IDS, sim_ids)
