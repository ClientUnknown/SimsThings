import weakreffrom server import accountfrom sims.sim_spawner import SimSpawnerfrom sims4.commands import CommandTypefrom sims4.service_manager import Servicefrom sims4.utils import classpropertyimport persistence_error_typesimport servicesimport sims4.loglogger = sims4.log.Logger('AccountService')
class AccountService(Service):

    def __init__(self):
        self._accounts = weakref.WeakValueDictionary()

    @classproperty
    def save_error_code(cls):
        return persistence_error_types.ErrorCodes.SERVICE_SAVE_FAILED_ACCOUNT_SERVICE

    def get_account_by_id(self, account_id, try_load_account=False):
        account = self._accounts.get(account_id, None)
        if try_load_account:
            account = self._load_account_by_id(account_id)
        return account

    def add_account(self, new_account):
        if new_account.id in self._accounts:
            logger.warn('Trying to add Account that is already in the Account Service')
        self._accounts[new_account.id] = new_account

    def check_command_permission(self, client_id, command_type):
        tgt_client = services.client_manager().get(client_id)
        if tgt_client is None:
            return False
        if command_type == CommandType.Cheat:
            cheat_service = services.get_cheat_service()
            return cheat_service.cheats_enabled
        return tgt_client.account.check_command_permission(command_type)

    def on_load_options(self, client):
        client.account.on_load_options()

    def on_all_households_and_sim_infos_loaded(self, client):
        client.account.on_all_households_and_sim_infos_loaded(client)

    def on_client_connect(self, client):
        client.account.on_client_connect(client)

    def on_client_disconnect(self, client):
        client.account.on_client_disconnect(client)

    def _load_account_by_id(self, account_id):
        if account_id == SimSpawner.SYSTEM_ACCOUNT_ID:
            new_account = account.Account(SimSpawner.SYSTEM_ACCOUNT_ID, 'SystemAccount')
            return new_account
        account_proto = services.get_persistence_service().get_account_proto_buff()
        new_account = account.Account(account_proto.nucleus_id, account_proto.persona_name)
        new_account.load_account(account_proto)
        return new_account

    def save(self, **kwargs):
        for account in self._accounts.values():
            account.save_account()
