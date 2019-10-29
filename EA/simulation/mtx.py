from sims4.common import Packimport servicesimport sims4.callback_utilsimport sims4.utilstry:
    import _zone
except ImportError:

    class _zone:

        @staticmethod
        def has_entitlement(guid):
            return True

        @staticmethod
        def is_displayable(guid):
            pass

        @staticmethod
        def show_mtx_lock_icon(guid):
            pass
has_entitlement = _zone.has_entitlementis_displayable = _zone.is_displayableshow_mtx_lock_icon = _zone.show_mtx_lock_icon
def register_entitlement_unlock_callback(guid, fn):
    raise RuntimeError('[bhill] This function is believed to be dead code as of 8/6/2014. If you see this exception, remove it because the code is not dead.')
    handlers = services.current_zone().entitlement_unlock_handlers
    call_list = handlers.get(guid)
    if call_list is None:
        call_list = sims4.callback_utils.RemovableCallableList()
        handlers[guid] = call_list
    call_list.append(fn)

@sims4.utils.exception_protected
def c_api_entitlement_unlocked(zone_id, account_id, guid):
    raise RuntimeError('[bhill] This function is believed to be dead code as of 8/6/2014. If you see this exception, remove it because the code is not dead.')
    handlers = services.get_zone(zone_id).entitlement_unlock_handlers
    call_list = handlers.get(guid)
    if call_list and call_list(account_id, guid):
        handlers.pop(guid)

@sims4.utils.exception_protected
def c_api_entitlement_purchase_failed(zone_id, account_id, guid, failure_reason):
    pass
