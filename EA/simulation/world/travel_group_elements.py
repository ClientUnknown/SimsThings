from interactions import ParticipantTypeActorTargetSim, ParticipantTypefrom interactions.utils.interaction_elements import XevtTriggeredElementfrom sims4.tuning.tunable import TunableEnumEntryimport servicesimport sims4.logimport telemetry_helperTELEMETRY_GROUP_TRAVEL_GROUPS = 'TGRP'TELEMETRY_HOOK_TRAVEL_GROUP_ADD = 'TGAD'TELEMETRY_HOOK_TRAVEL_GROUP_REMOVE = 'TGRM'TELEMETRY_TRAVEL_GROUP_ID = 'tgid'TELEMETRY_TRAVEL_GROUP_ZONE_ID = 'tgzo'TELEMETRY_TRAVEL_GROUP_SIZE = 'tgsz'TELEMETRY_TRAVEL_GROUP_DURATION = 'tgdu'travel_group_telemetry_writer = sims4.telemetry.TelemetryWriter(TELEMETRY_GROUP_TRAVEL_GROUPS)logger = sims4.log.Logger('Travel_Group_Elements', default_owner='rmccord')
class TravelGroupAdd(XevtTriggeredElement):
    FACTORY_TUNABLES = {'travel_group_participant': TunableEnumEntry(description='\n            A participant that belongs to the travel group we care about.\n            ', tunable_type=ParticipantType, default=ParticipantType.Actor), 'target_to_add': TunableEnumEntry(description='\n            The participant we want to add to the travel group.\n            ', tunable_type=ParticipantType, default=ParticipantType.TargetSim)}

    def _do_behavior(self, *args, **kwargs):
        actors = self.interaction.get_participants(self.travel_group_participant)
        targets = self.interaction.get_participants(self.target_to_add)
        if not (actors and targets):
            logger.error('TravelGroupAdd could not acquire participants.')
            return

        def get_first_travel_group(participants):
            travel_group = None
            for participant in participants:
                travel_group = participant.travel_group
                if travel_group is not None:
                    break
            return travel_group

        travel_group = get_first_travel_group(actors)
        if travel_group is None:
            logger.error('Participant {} does not belong to a travel group.', actors)
            return
        target_travel_group = get_first_travel_group(targets)
        if target_travel_group is not None:
            logger.error('Target {} already belongs to a travel group.', targets)
            return
        for target in targets:
            target_sim_info = services.sim_info_manager().get(target.sim_id)
            if not travel_group.can_add_to_travel_group(target_sim_info):
                logger.error('Cannot add Target {} to Travel Group {}.', target, travel_group)
                return
            travel_group.add_sim_info(target_sim_info)
        with telemetry_helper.begin_hook(travel_group_telemetry_writer, TELEMETRY_HOOK_TRAVEL_GROUP_ADD, sim_info=target_sim_info) as hook:
            hook.write_int(TELEMETRY_TRAVEL_GROUP_ID, travel_group.id)
            hook.write_int(TELEMETRY_TRAVEL_GROUP_ZONE_ID, travel_group.zone_id)
            hook.write_int(TELEMETRY_TRAVEL_GROUP_SIZE, len(travel_group))
            hook.write_int(TELEMETRY_TRAVEL_GROUP_DURATION, int(travel_group.duration_time_span.in_minutes()))

class TravelGroupRemove(XevtTriggeredElement):
    FACTORY_TUNABLES = {'participant_to_remove': TunableEnumEntry(description='\n            The participant we want to remove from their travel group.\n            ', tunable_type=ParticipantType, default=ParticipantType.Actor)}

    def _do_behavior(self, *args, **kwargs):
        resolver = self.interaction.get_resolver()
        participant = resolver.get_participant(self.participant_to_remove)
        if participant is not None:
            travel_group = participant.travel_group
            if travel_group is not None:
                if any(sim_info.can_live_alone for sim_info in travel_group if sim_info is not participant):
                    travel_group.remove_sim_info(participant)
                else:
                    travel_group.end_vacation()
                with telemetry_helper.begin_hook(travel_group_telemetry_writer, TELEMETRY_HOOK_TRAVEL_GROUP_REMOVE, sim_info=participant) as hook:
                    hook.write_int(TELEMETRY_TRAVEL_GROUP_ID, travel_group.id)
                    hook.write_int(TELEMETRY_TRAVEL_GROUP_ZONE_ID, travel_group.zone_id)
                    hook.write_int(TELEMETRY_TRAVEL_GROUP_SIZE, len(travel_group))
                    hook.write_int(TELEMETRY_TRAVEL_GROUP_DURATION, int(travel_group.duration_time_span.in_minutes()))

class TravelGroupExtend(XevtTriggeredElement):
    FACTORY_TUNABLES = {'participant': TunableEnumEntry(description='\n            A participant that belongs to the travel group we care about.\n            ', tunable_type=ParticipantTypeActorTargetSim, default=ParticipantTypeActorTargetSim.Actor)}

    def _do_behavior(self, *args, **kwargs):
        participant = self.interaction.get_participant(self.participant)
        if participant is not None:
            travel_group = participant.travel_group
            if travel_group is None:
                logger.error('Participant {} does not belong to a travel group.', participant)
                return
            travel_group.show_extend_vacation_dialog()

class TravelGroupEnd(XevtTriggeredElement):
    FACTORY_TUNABLES = {'participant': TunableEnumEntry(description='\n            A participant that belongs to the travel group we care about.\n            ', tunable_type=ParticipantTypeActorTargetSim, default=ParticipantTypeActorTargetSim.Actor)}

    def _do_behavior(self, *args, **kwargs):
        participant = self.interaction.get_participant(self.participant)
        if participant is not None:
            travel_group = participant.travel_group
            if travel_group is None:
                logger.error('Participant {} does not belong to a travel group.', participant)
                return
            travel_group.end_vacation()
