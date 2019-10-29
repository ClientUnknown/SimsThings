from aspirations.aspiration_types import AspriationTypefrom sims4.tuning.instance_manager import InstanceManagerimport sims4.loglogger = sims4.log.Logger('Aspirations')
class AspirationInstanceManager(InstanceManager):

    def all_whim_sets_gen(self):
        for aspiration in self.types.values():
            if aspiration.aspiration_type == AspriationType.WHIM_SET:
                yield aspiration
