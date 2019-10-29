from sims4.service_manager import Serviceimport sims4.loglogger = sims4.log.Logger('Photography', default_owner='shipark')
class PhotographyService(Service):

    def __init__(self):
        self._loots = []

    def add_loot_for_next_photo_taken(self, loot):
        self._loots.append(loot)

    def apply_loot_for_photo(self, siminfo):
        for photoloot in self._loots:
            photoloot.apply_loot(siminfo)

    def get_loots_for_photo(self):
        return self._loots

    def cleanup(self):
        self._loots = []

    def stop(self):
        self.cleanup()
