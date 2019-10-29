from objects.proxy import ProxyObject
class SimPostureNode(ProxyObject):

    def __str__(self):
        return 'Generic Sim Node ' + str(self._proxied_obj)

    @property
    def sim_proxied(self):
        return self._proxied_obj
