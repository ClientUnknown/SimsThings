from objects.object_manager import DistributableObjectManagerfrom server.client import Client
class ClientManager(DistributableObjectManager):

    def create_client(self, client_id, account, household_id):
        new_client = Client(client_id, account, household_id)
        self.add(new_client)
        return new_client

    def get_client_by_household(self, household):
        for client in self._objects.values():
            if client.household is household:
                return client

    def get_client_by_household_id(self, household_id):
        for client in self._objects.values():
            if client.household_id == household_id:
                return client

    def get_client_by_account(self, account_id):
        for client in self._objects.values():
            if client.account.id == account_id:
                return client

    def get_first_client(self):
        for client in self._objects.values():
            return client

    def get_first_client_id(self):
        for client in self._objects.values():
            return client.id
