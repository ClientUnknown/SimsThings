from build_buy import get_object_placement_flags, PlacementFlags, WALL_OBJECT_POSITION_PADDINGfrom native.routing.connectivity import Handlefrom objects.components.state import TunableStateValueReferencefrom plex.plex_enums import PlexBuildingTypefrom primitives import routing_utilsfrom sims4.tuning.tunable import TunableSet, TunableEnumWithFilter, TunableTuple, TunableList, TunableReferenceimport routingimport servicesimport sims4import taglogger = sims4.log.Logger('MailboxOwnerHelper', default_owner='jdimailig')
@sims4.commands.Command('mailboxes.assign')
def assign_mailbox_owners_command():
    helper = MailboxOwnerHelper()
    helper.assign_mailbox_owners()

class ObjectConnectivityHandle(Handle):

    def __init__(self, obj, position):
        super().__init__(routing.Location(position, orientation=obj.orientation, routing_surface=obj.routing_surface), obj.routing_surface)
        self.obj = obj
        self.assigned = False

class MailboxOwnerHelper:
    MAILBOX_TAGS = TunableSet(description='\n        Tags that considered mailboxes.\n        ', tunable=TunableEnumWithFilter(tunable_type=tag.Tag, default=tag.Tag.INVALID, filter_prefixes=('func',)))
    OWNER_STATES = TunableList(description='\n        A list of items and states used for setting ownership states\n        of plex mailboxes.\n        \n        This is contained within a list to protect against pack safe references.\n        ', tunable=TunableTuple(description='\n            A set of states that will be set depending on whether\n            the active household is the owner of a mailbox or not.\n            ', definitions=TunableList(description='\n                Only items with the specified definition(s) will have their states updated.\n                ', tunable=TunableReference(services.definition_manager(), pack_safe=True)), default_state_value=TunableStateValueReference(description='\n                Default state of mailbox, used if not owned by active household.\n                ', pack_safe=True), active_state_value=TunableStateValueReference(description='\n                State to use when owned by active household.\n                ', pack_safe=True)))

    def assign_mailbox_owners(self):
        plex_service = services.get_plex_service()
        door_service = services.get_door_service()
        if not plex_service.is_active_zone_a_plex():
            return
        if plex_service.get_plex_building_type(services.current_zone_id()) == PlexBuildingType.PENTHOUSE_PLEX:
            return
        plex_door_infos = door_service.get_plex_door_infos()
        if not plex_door_infos:
            return
        object_manager = services.object_manager()
        unclaimed_mailboxes = []
        for mailbox in object_manager.get_objects_with_tags_gen(*self.MAILBOX_TAGS):
            mailbox.set_household_owner_id(None)
            unclaimed_mailboxes.append(mailbox)
        mailbox_handles = [self._create_mailbox_handle(mailbox) for mailbox in unclaimed_mailboxes]
        door_handles = self._create_plexdoor_handles(plex_door_infos)
        routes = routing_utils.sorted_estimated_distances_between_multiple_handles(mailbox_handles, door_handles, routing.PathPlanContext())
        for estimated_distance in routes:
            mbox_handle = estimated_distance[0]
            door_handle = estimated_distance[1]
            mailbox = mbox_handle.obj
            door = door_handle.obj
            if mbox_handle.assigned:
                pass
            elif door_handle.assigned:
                pass
            else:
                mapped_household_ids = set()
                household_id = door.household_owner_id
                if household_id != 0 and household_id not in mapped_household_ids:
                    mapped_household_ids.add(household_id)
                self._apply_ownership(mailbox, household_id)
                door_handle.assigned = True
                mbox_handle.assigned = True
                logger.debug('mailbox {} paired with a door {} owned by household {}', mailbox, door, household_id)
                if not [dh for dh in door_handles if not dh.assigned]:
                    break
                if not [mbh for mbh in mailbox_handles if not mbh.assigned]:
                    break

    def _apply_ownership(self, mailbox, household_id):
        mailbox.set_household_owner_id(household_id)
        for tuning in self.OWNER_STATES:
            if mailbox.definition in tuning.definitions:
                owner_state_value = tuning.active_state_value if household_id == services.active_household_id() else tuning.default_state_value
                mailbox.set_state(owner_state_value.state, owner_state_value, immediate=True)

    def _create_plexdoor_handles(self, plex_door_infos):
        handles = []
        object_manager = services.object_manager()
        for plex_door_info in plex_door_infos:
            door = object_manager.get(plex_door_info.door_id)
            (front_position, _) = door.get_door_positions()
            handles.append(ObjectConnectivityHandle(door, front_position))
        return handles

    def _create_mailbox_handle(self, mailbox):
        position = mailbox.position
        if PlacementFlags.EDGE_AGAINST_WALL & get_object_placement_flags(mailbox.definition.id):
            position = mailbox.position + mailbox.forward*WALL_OBJECT_POSITION_PADDING
        return ObjectConnectivityHandle(mailbox, position)
