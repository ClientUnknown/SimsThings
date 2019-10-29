import services
class BusinessSituationMixin:

    def __init__(self, *arg, **kwargs):
        super().__init__(*arg, **kwargs)
        self._business_manager = services.business_service().get_business_manager_for_zone()
        if self._business_manager is not None:
            self._business_manager.on_store_closed.register(self._on_business_closed)

    def _on_business_closed(self):
        for sim in self.all_sims_in_situation_gen():
            if not sim.is_selectable:
                services.get_zone_situation_manager().make_sim_leave(sim)
        self._self_destruct()

    def _destroy(self):
        business_manager = services.business_service().get_business_manager_for_zone()
        if business_manager is not None and self._on_business_closed in business_manager.on_store_closed:
            business_manager.on_store_closed.unregister(self._on_business_closed)
        super()._destroy()
