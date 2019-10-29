from business.business_enums import BusinessType, BusinessEmployeeTypefrom interactions import ParticipantTypeLot, ParticipantTypeSingleSimfrom interactions.utils.interaction_elements import XevtTriggeredElementfrom sims4.tuning.tunable import TunableEnumEntry, HasTunableSingletonFactory, AutoFactoryInit, TunableVariantimport servicesimport sims4.loglogger = sims4.log.Logger('Business', default_owner='trevor')
class BusinessBuyLot(XevtTriggeredElement):
    FACTORY_TUNABLES = {'business_type': TunableEnumEntry(description='\n            The type of business to create for the lot.\n            ', tunable_type=BusinessType, default=BusinessType.INVALID, invalid_enums=(BusinessType.INVALID,)), 'lot_participant': TunableEnumEntry(description='\n            The lot to purchase. This is likely the Picked Zone ID from the map\n            view picker screen.\n            ', tunable_type=ParticipantTypeLot, default=ParticipantTypeLot.PickedZoneId)}

    def _do_behavior(self):
        zone_id = self.interaction.get_participant(self.lot_participant)
        if self.lot_participant == ParticipantTypeLot.Lot:
            zone_id = zone_id.id
        actor_household = self.interaction.sim.household
        business_service = services.business_service()
        business_service.make_owner(actor_household.id, self.business_type, zone_id)

class _BusinessEmployeeActionHire(HasTunableSingletonFactory, AutoFactoryInit):
    FACTORY_TUNABLES = {'employee_type': TunableEnumEntry(description='\n            The type of employee this sim should be hired as.\n            ', tunable_type=BusinessEmployeeType, default=BusinessEmployeeType.INVALID, invalid_enums=(BusinessEmployeeType.INVALID,))}

    def do_action(self, business_manager, employee_sim_info):
        business_manager.add_employee(employee_sim_info, self.employee_type)

class _BusinessEmployeeActionFire(HasTunableSingletonFactory, AutoFactoryInit):

    def do_action(self, business_manager, employee_sim_info):
        business_manager.remove_employee(employee_sim_info)

class BusinessEmployeeAction(XevtTriggeredElement):
    FACTORY_TUNABLES = {'employee': TunableEnumEntry(description='\n            The sim participant to hire/fire.\n            ', tunable_type=ParticipantTypeSingleSim, default=ParticipantTypeSingleSim.PickedSim), 'action': TunableVariant(description='\n            The action (hire or fire) to apply to the chosen employee.\n            ', hire=_BusinessEmployeeActionHire.TunableFactory(), fire=_BusinessEmployeeActionFire.TunableFactory(), default='hire')}

    def _do_behavior(self):
        employee_sim_info = self.interaction.get_participant(self.employee)
        if employee_sim_info is None:
            logger.error('Got a None Sim trying to run the BusinessEmployeeAction element. {}, action: {}', self.interaction, self.action)
            return
        employee_sim_info = getattr(employee_sim_info, 'sim_info', employee_sim_info)
        business_manager = services.business_service().get_business_manager_for_zone()
        if business_manager is None:
            logger.error('Got a None Business Manager trying to run a BusinessEmployeeAction element. {}, action: {}', self.interaction, self.action)
            return
        self.action.do_action(business_manager, employee_sim_info)
