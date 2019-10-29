from interactions import ParticipantTypefrom interactions.interaction_finisher import FinishingTypefrom interactions.utils.interaction_elements import XevtTriggeredElementfrom sims4.tuning.tunable import HasTunableFactory, TunableEnumEntry, Tunable, TunableVariant, TunableTupleimport build_buyimport servicesimport sims4.loglogger = sims4.log.Logger('SendToInventory', default_owner='stjulien')
class SendToInventory(XevtTriggeredElement, HasTunableFactory):
    PARTICIPANT_INVENTORY = 'inventory_participant'
    HOUSEHOLD_INVENTORY = 'inventory_household'
    MAILBOX_INVENTORY = 'inventory_mailbox'
    FACTORY_TUNABLES = {'participant': TunableEnumEntry(description='\n            The participant of the interaction who will be sent to the specified\n            inventory.\n            ', tunable_type=ParticipantType, default=ParticipantType.Object), 'inventory': TunableVariant(description='\n            The inventory location we want to send the participant to. \n            ', participant_inventory=TunableTuple(description="\n                Send the object to a participant's inventory. If the inventory\n                participant is a Sim, we will set the owner of the participant\n                to the Sim's household.\n                ", participant=TunableEnumEntry(description='\n                    The participant whose inventory we want to use.\n                    ', tunable_type=ParticipantType, default=ParticipantType.Actor), fallback_to_household=Tunable(description='\n                    If enabled and the object fails to add to the participant\n                    inventory, we will fallback to the owning household\n                    inventory.\n                    ', tunable_type=bool, default=False), locked_args={'inventory_type': PARTICIPANT_INVENTORY}), household_inventory=TunableTuple(description='\n                Send the object to the household inventory of its owner.\n                ', locked_args={'inventory_type': HOUSEHOLD_INVENTORY}), mailbox_inventory=TunableTuple(description='\n                Send the object to the hidden inventory of the owners home lot, to be later delivered to the mailbox.\n                ', locked_args={'inventory_type': MAILBOX_INVENTORY}), default='participant_inventory')}

    def _do_behavior(self):
        sim = self.interaction.sim
        target = self.interaction.get_participant(self.participant)
        if target is None:
            return False
        should_fallback = False
        inventory_participant = sim
        if target.is_in_inventory():
            inventory = target.get_inventory()
            inventory.try_remove_object_by_id(target.id)
        if self.inventory.inventory_type == SendToInventory.PARTICIPANT_INVENTORY:
            inventory_participant = self.interaction.get_participant(self.inventory.participant)
            if inventory_participant.is_sim:
                target.set_household_owner_id(inventory_participant.household_id)
            inventory_component = inventory_participant.inventory_component
            if not inventory_component.player_try_add_object(target):
                should_fallback = self.inventory.fallback_to_household
            else:
                for interaction in tuple(target.interaction_refs):
                    if not interaction.running:
                        if interaction.is_finishing:
                            pass
                        elif inventory_participant.is_sim:
                            if not interaction.allow_from_sim_inventory:
                                interaction.cancel(FinishingType.OBJECT_CHANGED, cancel_reason_msg='Object moved to inventory')
                                if not interaction.allow_from_object_inventory:
                                    interaction.cancel(FinishingType.OBJECT_CHANGED, cancel_reason_msg='Object moved to inventory')
                        elif not interaction.allow_from_object_inventory:
                            interaction.cancel(FinishingType.OBJECT_CHANGED, cancel_reason_msg='Object moved to inventory')
        if self.inventory.inventory_type == SendToInventory.MAILBOX_INVENTORY:
            if not inventory_participant.is_sim:
                logger.error('Trying to add an item [{}] to a mailbox but the participant [{}] is not a sim', target.definition, inventory_participant)
                return False
            target.set_household_owner_id(inventory_participant.household_id)
            zone = services.get_zone(inventory_participant.household.home_zone_id)
            if zone is None:
                logger.error('Trying to add an item [{}] to a mailbox but the provided sim [{}] has no home zone.', target.definition, inventory_participant)
                return False
            lot_hidden_inventory = zone.lot.get_hidden_inventory()
            if lot_hidden_inventory is None:
                logger.error("Trying to add an item [{}] to the lot's hidden inventory but the provided sim [{}] has no hidden inventory for their lot.", target.definition, inventory_participant)
                return False
            lot_hidden_inventory.system_add_object(target)
            for interaction in tuple(target.interaction_refs):
                if not interaction.running:
                    if interaction.is_finishing:
                        pass
                    else:
                        interaction.cancel(FinishingType.OBJECT_CHANGED, cancel_reason_msg='Object moved to inventory')
        elif self.inventory.inventory_type == SendToInventory.HOUSEHOLD_INVENTORY or should_fallback:

            def on_reservation_change(*_, **__):
                if not target.in_use:
                    target.unregister_on_use_list_changed(on_reservation_change)
                    build_buy.move_object_to_household_inventory(target)

            if target is self.interaction.target:
                self.interaction.set_target(None)
            if inventory_participant is not None and inventory_participant.is_sim:
                target.set_household_owner_id(inventory_participant.household_id)
            target.remove_from_client(fade_duration=target.FADE_DURATION)
            if target.in_use:
                target.register_on_use_list_changed(on_reservation_change)
            else:
                build_buy.move_object_to_household_inventory(target)
