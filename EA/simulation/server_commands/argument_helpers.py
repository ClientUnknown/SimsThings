import operatorfrom singletons import DEFAULTimport servicesimport sims4.commandsimport sims4.loglogger = sims4.log.Logger('Commands')
class RequiredTargetParam(sims4.commands.CustomParam):

    def __init__(self, target_id:int):
        self._target_id = int(target_id, base=0)

    @property
    def target_id(self):
        return self._target_id

    def get_target(self, manager=DEFAULT):
        manager = services.object_manager() if manager is DEFAULT else manager
        target = manager.get(self._target_id)
        if target is None:
            logger.error('Could not find the target id {} for a RequiredTargetParam in the object manager.', self._target_id)
        return target

class OptionalTargetParam(sims4.commands.CustomParam):
    TARGET_ID_ACTIVE_LOT = -1

    def __init__(self, target_id:int=None):
        if not target_id:
            self._target_id = None
        else:
            self._target_id = int(target_id, base=0)

    @property
    def target_id(self):
        return self._target_id

    def _get_target(self, _connection):
        if self._target_id is None:
            tgt_client = services.client_manager().get(_connection)
            if tgt_client is not None:
                return tgt_client.active_sim
            return
        if self._target_id == self.TARGET_ID_ACTIVE_LOT:
            return services.active_lot()
        return services.object_manager().get(self._target_id)

class OptionalSimInfoParam(OptionalTargetParam):

    def _get_target(self, _connection):
        if self._target_id is None:
            client = services.client_manager().get(_connection)
            if client is not None:
                return client.active_sim_info
            return
        return services.sim_info_manager().get(self._target_id)

class OptionalHouseholdParam(OptionalTargetParam):

    def _get_target(self, _connection):
        if self._target_id is None:
            return services.active_household()
        return services.household_manager().get(self._target_id)

def get_optional_target(opt_target:OptionalTargetParam=None, _connection=None, target_type=OptionalTargetParam, notify_failure=True):
    opt_target = opt_target if opt_target is not None else target_type()
    target = opt_target._get_target(_connection)
    if target is None and notify_failure:
        sims4.commands.output('Could not find target for specified ID: {}.'.format(opt_target._target_id), _connection)
    return target

def get_tunable_instance(resource_type, name_string_or_id, exact_match=False):
    manager = services.get_instance_manager(resource_type)
    cls = manager.get(name_string_or_id)
    if cls is not None:
        return cls
    search_string = str(name_string_or_id).lower()
    matches = []
    for cls in manager.types.values():
        if exact_match:
            if search_string == cls.__name__.lower():
                return cls
                if search_string == cls.__name__.lower():
                    return cls
                if search_string in cls.__name__.lower():
                    matches.append(cls)
        else:
            if search_string == cls.__name__.lower():
                return cls
            if search_string in cls.__name__.lower():
                matches.append(cls)
    if not matches:
        raise ValueError("No names matched '{}'.".format(search_string))
    if len(matches) > 1:
        matches.sort(key=operator.attrgetter('__name__'))
        raise ValueError("Multiple names matched '{}': {}".format(search_string, ', '.join(m.__name__ for m in matches)))
    return matches[0]

def TunableInstanceParam(resource_type, exact_match=False):

    def _factory(name_substring_or_id):
        return get_tunable_instance(resource_type, name_substring_or_id, exact_match=exact_match)

    return _factory
