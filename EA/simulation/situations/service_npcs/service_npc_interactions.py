from event_testing.results import TestResultfrom interactions.base.picker_interaction import PickerSuperInteractionfrom interactions.utils.tunable_icon import TunableIconAllPacksfrom sims4.localization import TunableLocalizedStringFactory, TunableLocalizedString, LocalizationHelperTuningfrom sims4.resources import CompoundTypesfrom sims4.tuning.tunable import TunableReference, TunableList, TunableTuple, TunableResourceKey, OptionalTunable, TunablePackSafeResourceKey, TunableVariant, Tunablefrom sims4.tuning.tunable_base import GroupNamesfrom sims4.utils import flexmethodfrom situations.service_npcs.service_npc_tuning import ServiceNpcHireableimport event_testingimport servicesimport sims4.resourcesimport ui
class PickServiceNpcSuperInteraction(PickerSuperInteraction):
    INSTANCE_TUNABLES = {'service_npcs': TunableList(description='\n            A list of the service npcs that will show up in the dialog picker\n            ', tunable=TunableTuple(description='\n                Tuple of service npcs data about those NPCs being pickable.\n                ', service_npc=TunableReference(description='\n                    The service npcs that will show up in the picker.\n                    ', manager=services.get_instance_manager(sims4.resources.Types.SERVICE_NPC), class_restrictions=(ServiceNpcHireable,), pack_safe=True), already_hired_tooltip=TunableLocalizedStringFactory(description='\n                    Tooltip that displays if the service has already been\n                    hired.\n                    '), tests=event_testing.tests.TunableGlobalTestSet(description='\n                    A set of tests that determine if this service npc will show up\n                    as available or greyed out in the picker.\n                    ')), tuning_group=GroupNames.PICKERTUNING), 'non_service_npcs': TunableList(description="\n            A List of non service NPCs that can be hired using the\n            'Hire A Service' UI.\n            ", tunable=TunableTuple(description="\n                The Data needed to display the non service NPC in the \n                'Hire A Service' UI.\n                ", icon=TunableIconAllPacks(description="\n                    The icon to be displayed in 'Hire a Service' UI\n                    ", tuning_group=GroupNames.UI), name=TunableLocalizedStringFactory(description="\n                    The name to be displayed for this NPC in the 'Hire a Service'\n                    UI.\n                    "), cost_string=TunableVariant(description='\n                    When enabled, the tuned string will be shown as the cost\n                    of hiring this NPC.\n                    ', cost_amount=Tunable(description='\n                        ', tunable_type=int, default=0), no_cost_string=TunableLocalizedStringFactory(description="\n                        The description to be used for this NPC in the \n                        if there isn't a cost associated with it\n                        "), locked_args={'disabled': None}, default='disabled'), hire_interaction=TunableReference(description='\n                    The affordance to push the sim making the call when hiring this\n                    service npc from a picker dialog from the phone.\n                    ', manager=services.affordance_manager(), pack_safe=True), tests=event_testing.tests.TunableGlobalTestSet(description='\n                    A set of global tests that are always run before other tests. All\n                    tests must pass in order for the interaction to run.\n                    '), free_service_traits=TunableList(description='\n                    If any Sim in the household has one of these traits, the \n                    non service npc will be free.\n                    ', tunable=TunableReference(manager=services.trait_manager(), pack_safe=True), unique_entries=True))), 'display_price_flat_rate': TunableLocalizedStringFactory(description='\n            Formatting for cost of the service if it has just a one time flat fee.\n            Parameters: 0 is flat rate cost of the service\n            ', tuning_group=GroupNames.PICKERTUNING), 'display_price_hourly_cost': TunableLocalizedStringFactory(description='\n            Formatting for cost of the service if it is purely hourly\n            Parameters: 0 is hourly cost of the service\n            ', tuning_group=GroupNames.PICKERTUNING), 'display_price_fee_and_hourly_cost': TunableLocalizedStringFactory(description='\n            Formatting for cost of the service if it has an upfront cost AND an\n            hourly cost\n            Parameters: 0 is upfront cost of service. 1 is hourly cost of service\n            ', tuning_group=GroupNames.PICKERTUNING), 'display_price_free': TunableLocalizedString(description='\n            Description text if the service has zero upfront cost and zero hourly cost.\n            ', tuning_group=GroupNames.PICKERTUNING)}

    def _run_interaction_gen(self, timeline):
        self._show_picker_dialog(self.sim, target_sim=self.sim)
        return True

    class _ServiceNpcRecurringPair:

        def __init__(self, service_npc_type, recurring):
            self.service_npc_type = service_npc_type
            self.recurring = recurring
            self.__name__ = '{} recurring: {}'.format(self.service_npc_type, self.recurring)

    @flexmethod
    def picker_rows_gen(cls, inst, target, context, **kwargs):
        inst_or_cls = cls if inst is None else inst
        service_npc_data_tuples = [service_npc_data for service_npc_data in inst_or_cls.service_npcs]
        for service_npc_data in service_npc_data_tuples:
            service_npc_type = service_npc_data.service_npc
            household = context.sim.household
            service_record = household.get_service_npc_record(service_npc_type.guid64, add_if_no_record=False)
            is_enabled = service_record is None or not service_record.hired
            if not is_enabled:
                tooltip = service_npc_data.already_hired_tooltip
            else:
                tooltip = None
            allows_recurring = service_npc_type._recurring is not None
            display_name = service_npc_type.display_name if not allows_recurring else service_npc_type._recurring.one_time_name
            tag = PickServiceNpcSuperInteraction._ServiceNpcRecurringPair(service_npc_type, recurring=False)
            if any(sim.trait_tracker.has_any_trait(service_npc_type.free_service_traits) for sim in household.sim_info_gen()):
                display_description = inst_or_cls.display_price_free
            elif not service_npc_type.cost_up_front > 0 or service_npc_type.cost_hourly > 0:
                display_description = inst_or_cls.display_price_fee_and_hourly_cost(service_npc_type.cost_up_front, service_npc_type.cost_hourly)
            elif service_npc_type.cost_up_front > 0:
                display_description = inst_or_cls.display_price_flat_rate(service_npc_type.cost_up_front)
            elif service_npc_type.cost_hourly > 0:
                display_description = inst_or_cls.display_price_hourly_cost(service_npc_type.cost_hourly)
            else:
                display_description = inst_or_cls.display_price_free
            resolver = inst_or_cls.get_resolver(target, context, inst_or_cls, search_for_tooltip=True)
            result = service_npc_data.tests.run_tests(resolver, search_for_tooltip=True)
            is_enabled = result == TestResult.TRUE
            tooltip = result.tooltip
            if not is_enabled or is_enabled or tooltip is None:
                pass
            else:
                row = ui.ui_dialog_picker.ObjectPickerRow(is_enable=is_enabled, name=display_name, icon=service_npc_type.icon, row_description=display_description, tag=tag, row_tooltip=tooltip)
                yield row
                if allows_recurring:
                    tag = PickServiceNpcSuperInteraction._ServiceNpcRecurringPair(service_npc_type, recurring=True)
                    row = ui.ui_dialog_picker.ObjectPickerRow(is_enable=is_enabled, name=service_npc_type._recurring.recurring_name, icon=service_npc_type.icon, row_description=display_description, tag=tag)
                    yield row
        for entry in cls.non_service_npcs:
            if any(sim.trait_tracker.has_any_trait(entry.free_service_traits) for sim in household.sim_info_gen()):
                cost_string = inst_or_cls.display_price_free
            else:
                cost_string = inst_or_cls._get_cost_string(entry)
            resolver = inst_or_cls.get_resolver(target, context, inst_or_cls, search_for_tooltip=True)
            result = entry.tests.run_tests(resolver, search_for_tooltip=True)
            if result or result.tooltip is None:
                pass
            else:
                row = ui.ui_dialog_picker.ObjectPickerRow(is_enable=result == TestResult.TRUE, name=entry.name(), icon=entry.icon, row_description=cost_string, tag=entry, row_tooltip=result.tooltip)
                yield row

    @flexmethod
    def _get_cost_string(cls, inst, entry):
        cost_string = entry.cost_string
        if cost_string is None:
            return
        if isinstance(cost_string, int):
            return LocalizationHelperTuning.get_for_money(cost_string)
        return cost_string()

    def on_choice_selected(self, choice_tag, **kwargs):
        tag = choice_tag
        if tag is not None:
            if isinstance(tag, PickServiceNpcSuperInteraction._ServiceNpcRecurringPair):
                tag.service_npc_type.on_chosen_from_service_picker(self, recurring=tag.recurring)
            elif tag.hire_interaction is not None:
                push_affordance = self.generate_continuation_affordance(tag.hire_interaction)
                for aop in push_affordance.potential_interactions(self.sim, self.context):
                    aop.test_and_execute(self.context)
