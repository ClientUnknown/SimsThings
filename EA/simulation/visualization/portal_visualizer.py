from build_buy import register_build_buy_exit_callback, unregister_build_buy_exit_callbackfrom debugvis import Contextfrom sims4 import commandsfrom sims4.color import Colorimport servicesimport sims4.loglogger = sims4.log.Logger('Debugvis')
class PortalVisualizer:

    def __init__(self, layer, portal_obj_id=0, portal_id=0):
        self.layer = layer
        self.portal_obj_id = portal_obj_id
        self.portal_id = portal_id
        self._start()

    def _start(self):
        object_manager = services.object_manager()
        object_manager.register_portal_added_callback(self._draw_portal_obj)
        object_manager.register_portal_removed_callback(self._on_portal_removed)
        register_build_buy_exit_callback(self._draw_all_portals)
        if self.portal_obj_id:
            obj = services.object_manager().get(self.portal_obj_id)
            if obj is not None:
                obj.register_on_location_changed(self._draw_portal_obj)
        self._draw_all_portals()

    def stop(self):
        object_manager = services.object_manager()
        object_manager.unregister_portal_added_callback(self._draw_portal_obj)
        object_manager.unregister_portal_removed_callback(self._on_portal_removed)
        unregister_build_buy_exit_callback(self._draw_all_portals)
        if self.portal_obj_id:
            obj = services.object_manager().get(self.portal_obj_id)
            if obj is not None:
                obj.unregister_on_location_changed(self._draw_portal_obj)

    def _draw_portal_pair(self, portal_instance, portal_id, layer, color_entry, color_exit, height, detail):
        (p_entry, p_exit) = portal_instance.get_portal_locations(portal_id)
        layer.add_arch(p_entry, p_exit, height=height, detail=detail, color_a=color_entry, color_b=color_exit)

    def _draw_portal_obj(self, portal_obj, *args, portal_id=0, **kwargs):
        with Context(self.layer, preserve=True) as layer:
            for portal_instance in portal_obj.get_portal_instances():
                if portal_id and not (portal_id == portal_instance.there or portal_id == portal_instance.back):
                    pass
                else:
                    if portal_instance.there is not None:
                        self._draw_portal_pair(portal_instance, portal_instance.there, layer, Color.CYAN, Color.MAGENTA, 6.0, 6)
                    if portal_instance.back is not None:
                        self._draw_portal_pair(portal_instance, portal_instance.back, layer, Color.GREEN, Color.ORANGE, 4.0, 6)

    def _on_portal_removed(self, portal_obj):
        if self.portal_obj_id and portal_obj.id == self.portal_id:
            full_command = 'debugvis.portals.stop' + ' {}'.format(self.portal_obj_id)
            client_id = services.client_manager().get_first_client_id()
            commands.execute(full_command, client_id)
        else:
            self._draw_all_portals()

    def _draw_all_portals(self, *_, **__):
        object_manager = services.object_manager()
        with Context(self.layer, preserve=True) as context:
            context.layer.clear()
        if self.portal_obj_id:
            portal_obj = object_manager.get(self.portal_obj_id)
            if portal_obj is not None:
                self._draw_portal_obj(portal_obj, portal_id=self.portal_id)
            return
        for obj in object_manager.portal_cache_gen():
            self._draw_portal_obj(obj, portal_id=0)
