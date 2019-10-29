from interactions import ParticipantTypefrom reservation.reservation_handler_basic import ReservationHandlerBasic, ReservationHandlerAllParts, ReservationHandlerUnmovableObjectsfrom reservation.reservation_handler_interlocked import ReservationHandlerInterlockedfrom reservation.reservation_handler_multi import ReservationHandlerMultifrom reservation.reservation_handler_nested import ReservationHandlerNestedfrom sims4.tuning.tunable import TunableFactory, TunableEnumFlags, TunableVariant, TunableList, TunableTupleimport sims4.loglogger = sims4.log.Logger('Reserve', default_owner='shouse')DEFAULT_RESERVATION_PARTICIPANT_TYPES = ParticipantType.Object | ParticipantType.CarriedObject | ParticipantType.CraftingObject
class TunableReserveTypeVariant(TunableVariant):

    def __init__(self, *args, **kwargs):
        if 'default' not in kwargs:
            kwargs['default'] = 'basic'
        super().__init__(*args, basic=ReservationHandlerBasic.TunableFactory(), all=ReservationHandlerAllParts.TunableFactory(), multi=ReservationHandlerMulti.TunableFactory(), reserve_and_lock_all_parts=ReservationHandlerAllParts.TunableFactory(), multi_reserve_all_unmovable_parts=ReservationHandlerUnmovableObjects.TunableFactory(), interlocked=ReservationHandlerInterlocked.TunableFactory(), **kwargs)

class TunableReserveObject(TunableFactory, is_fragment=True):
    DEFAULT_DESCRIPTION = "\n        Control which objects are marked as reserved for in use and how. When\n        setting this value, consider these rules:\n         \n        * Sims may never be marked as in use. Do not try to reserve TargetSim,\n        nor you should try to reserve Object if the interaction may run on\n        Sims.\n         \n        * You may not use a 'basic' reservation if you wish to reserve an entire\n        object and that object has parts. In that case, you must use an 'all'\n        reservation.\n        \n         e.g. Sit \n          Sims sit down, and may do so on individual parts of the sofa.\n          Because the interaction targets the part specifically, we use a 'basic'\n          reservation to reserve that and only that part.\n          \n         e.g. Possess\n          Ghosts may possess objects and have them shake. Since they might\n          possess the sofa (in its entirety), we want to use the 'all' reserve\n          type to mark the object, as well as each individual part as reserved\n          for use. This would prevent other Sims from sitting down while the\n          object is being possessed.\n          \n          Note: it is valid to use the 'all' reserve type on any object, not\n          just objects with parts!\n        "

    @staticmethod
    def _factory(sim, interaction, *, reserve_type_for_provided_target, subject_list, reserve_target=None, **kwargs):
        if reserve_target is not None:
            if reserve_type_for_provided_target is not None:
                reserve_type = reserve_type_for_provided_target
            elif subject_list:
                reserve_type = subject_list[0].reserve_type
            else:
                reserve_type = ReservationHandlerBasic
            return reserve_type(sim, reserve_target, reservation_interaction=interaction)
        else:
            handler = ReservationHandlerNested()

            def _process_participants(reserve_type, subject):
                for obj in interaction.get_participants(subject):
                    if not obj is None:
                        if obj.is_sim:
                            pass
                        else:
                            handler.add_handler(reserve_type(sim, obj, reservation_interaction=interaction))

            if subject_list:
                for item in subject_list:
                    _process_participants(item.reserve_type, item.subject)
            else:
                _process_participants(ReservationHandlerBasic, DEFAULT_RESERVATION_PARTICIPANT_TYPES)
            return handler

    FACTORY_TYPE = _factory

    @staticmethod
    def _on_tunable_loaded_callback(cls, fields, source, *, reserve_type_for_provided_target, subject_list, **kwargs):
        if reserve_type_for_provided_target is not None and issubclass(ReservationHandlerMulti, reserve_type_for_provided_target.factory):
            cls._has_multi_reserve = True
            return
        if subject_list:
            cls._has_multi_reserve |= any(issubclass(ReservationHandlerMulti, item.reserve_type.factory) for item in subject_list)

    @staticmethod
    def verify_tunable_callback(instance_class, tunable_name, source, reserve_type_for_provided_target, subject_list):
        if len(subject_list) > 1:
            accum = 0
            for item in subject_list:
                flags = int(item.subject)
                if accum & flags != 0:
                    logger.error('TunableReserveObject: {} has the same subject {} with more than one reserve type.  Each subject can only be referenced once in the list.', source, item)
                accum = accum | flags

    def __init__(self, description=DEFAULT_DESCRIPTION, **kwargs):
        super().__init__(reserve_type_for_provided_target=TunableReserveTypeVariant(description='\n                    When the interaction is provided a target (instead of \n                    discovering them via the ParticipantType), only this is \n                    needed.  If None, it uses the first Subject List \n                    Reserve Type.\n                ', default=None), subject_list=TunableList(description='\n                List of reservation handlers and subject pairs.  An empty list will\n                result in the default basic reservation type for the default \n                participant types.\n                ', tunable=TunableTuple(description='\n                    Select a reservation handler for a set of subjects.\n                    Backward compatibility: Older tuning may have one item where\n                    only the reserve_type is used instead of using the\n                    Reserve Type For Provided Target.\n                    ', reserve_type=TunableReserveTypeVariant(description='\n                        Select the type of reservation\n                        '), subject=TunableEnumFlags(description='\n                        Who or what to reserve.\n                        ', enum_type=ParticipantType, default=DEFAULT_RESERVATION_PARTICIPANT_TYPES))), verify_tunable_callback=TunableReserveObject.verify_tunable_callback, description=description, callback=self._on_tunable_loaded_callback, **kwargs)
