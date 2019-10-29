from protocolbuffers.Consts_pb2 import MGR_CLIENT, MGR_HOUSEHOLD, MGR_SIM_INFOimport sims4.reloadimport sims4.service_managerwith sims4.reload.protected(globals()):
    service_manager = None
class GameServiceManager(sims4.service_manager.ServiceManager):

    def __init__(self):
        super().__init__()
        self.allow_shutdown = True
        self.client_object_managers = set()

    @property
    def is_traveling(self):
        return not self.allow_shutdown

    def on_all_households_and_sim_infos_loaded(self, client):
        if service_manager.allow_shutdown:
            super().on_all_households_and_sim_infos_loaded(client)

    def load_all_services(self, zone_data=None):
        if service_manager.allow_shutdown:
            super().load_all_services(zone_data=zone_data)

    def save_all_services(self, persistence_service, **kwargs):
        if service_manager.allow_shutdown:
            super().save_all_services(persistence_service, **kwargs)

def start_services(save_slot_data):
    global service_manager
    if service_manager is None:
        service_manager = GameServiceManager()
        from apartments.landlord_service import LandlordService
        from business.business_service import BusinessService
        from call_to_action.call_to_action_service import CallToActionService
        from clock import GameClock
        from clubs.club_service import ClubService
        from event_testing.event_manager_service import EventManagerService
        from server.clientmanager import ClientManager
        from server.config_service import ConfigService
        from services.cheat_service import CheatService
        from services.style_service import StyleService
        from sims.household_utilities.utilities_manager import UtilitiesManager
        from sims.household_manager import HouseholdManager
        from sims.aging.aging_service import AgingService
        from services.relgraph_service import RelgraphService
        from sims.sim_info_manager import SimInfoManager
        from time_service import TimeService
        from tutorials.tutorial_service import TutorialService
        from curfew.curfew_service import CurfewService
        from sickness.sickness_service import SicknessService
        from trends.trend_service import TrendService
        from relationships.relationship_service import RelationshipService
        from sims.hidden_sim_service import HiddenSimService
        from holidays.holiday_service import HolidayService
        from seasons.season_service import SeasonService
        from weather.weather_service import WeatherService
        from services.rabbit_hole_service import RabbitHoleService
        from lot_decoration.lot_decoration_service import LotDecorationService
        from narrative.narrative_service import NarrativeService
        from services.object_lost_and_found_service import ObjectLostAndFoundService
        from global_policies.global_policy_service import GlobalPolicyService
        service_list = [BusinessService(), CallToActionService(), GameClock(), TimeService(), ConfigService(), CheatService(), EventManagerService(), ClientManager(manager_id=MGR_CLIENT), UtilitiesManager(), HouseholdManager(manager_id=MGR_HOUSEHOLD), RelationshipService(), RelgraphService.get_relgraph_service(), AgingService(), SimInfoManager(manager_id=MGR_SIM_INFO), CurfewService(), SicknessService(), HiddenSimService(), HolidayService(), SeasonService(), WeatherService(), NarrativeService(), GlobalPolicyService(), ClubService(), RabbitHoleService(), LotDecorationService(), StyleService(), TutorialService(), TrendService(), ObjectLostAndFoundService(), LandlordService()]
        for service in service_list:
            if service is not None:
                service_manager.register_service(service)
        service_manager.start_services(container=service_manager, save_slot_data=save_slot_data)

def stop_services():
    global service_manager
    if service_manager.allow_shutdown:
        service_manager.stop_services()
        service_manager = None

def disable_shutdown():
    if service_manager is not None:
        service_manager.allow_shutdown = False

def enable_shutdown():
    if service_manager is not None:
        service_manager.allow_shutdown = True

def on_tick():
    pass
