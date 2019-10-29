import randomfrom protocolbuffers import Consts_pb2from crafting.crafting_interactions import DebugCreateCraftableInteractionfrom crafting.crafting_process import RecipeTestResultfrom crafting.crafting_tunable import CraftingTuningfrom date_and_time import create_time_spanfrom distributor.shared_messages import IconInfoDatafrom objects import ALL_HIDDEN_REASONSfrom scheduler import WeeklySchedulefrom sims.bills_enums import AdditionalBillSourcefrom sims4.localization import TunableLocalizedStringfrom sims4.resources import CompoundTypesfrom sims4.tuning.instances import HashedTunedInstanceMetaclassfrom sims4.tuning.tunable import TunableRange, Tunable, TunableEnumEntry, TunableReference, OptionalTunable, TunableSimMinute, TunableTuple, TunableList, TunableResourceKey, TunableIntervalfrom sims4.tuning.tunable_base import GroupNamesfrom sims4.utils import classpropertyfrom situations.service_npcs.modify_lot_items_tuning import ModifyAllLotItemsfrom tunable_time import TunableTimeOfDayfrom ui.ui_dialog_notification import TunableUiDialogNotificationSnippetfrom ui.ui_dialog_picker import RecipePickerRow, UiRecipePickerimport servicesimport sims4.loglogger = sims4.log.Logger('ServiceNpc')
class ServiceNpc(metaclass=HashedTunedInstanceMetaclass, manager=services.get_instance_manager(sims4.resources.Types.SERVICE_NPC)):
    INSTANCE_SUBCLASSES_ONLY = True
    INSTANCE_TUNABLES = {'display_name': TunableLocalizedString(description='\n            Display name for this Service NPC type', tuning_group=GroupNames.UI), 'situation': TunableReference(description='\n            The situation to start when the service has been requested.', manager=services.get_instance_manager(sims4.resources.Types.SITUATION)), 'work_hours': WeeklySchedule.TunableFactory(), 'request_offset': TunableSimMinute(description='\n            The minimum time between a service request and the Sim spawning on\n            the lot.\n            ', default=10), 'fake_perform_job': ModifyAllLotItems.TunableFactory(), '_min_duration_left_for_arrival_on_lot': TunableSimMinute(description='\n            When determining whether to fake perform a service, if the player\n            sim arrived onto the lot WHILE the service would be actively \n            running, if the service would have less than this amount of minutes \n            left to be on the lot, we pretend the service already came. \n            otherwise, the service npc will show up immediately.\n            \n            EX: maid works from 1:00pm to 5:00pm. If the player gets home at\n            4 pm, the maid would only be able to work 1 hour until she has\n            to go home. So if this tuned value is more than 60 minutes, the \n            maid will not show up, and we pretend she was already there. If \n            this tuned value is say 30 mins, we will not fake perform cleaning \n            and the maid will be already on the lot when the player spawns in.\n            ', default=0, minimum=0), '_work_duration_min_max': TunableInterval(description='\n            If we decide to arrive on the lot, the amount of time the service\n            npc stays on the lot will be clamped to be within this interval.\n            Not to be confused with _min_duration_left_for_arrival_on_lot, \n            which is used to determine if the service npc arrives AT ALL.\n            \n            EX: mailman has _min_duration_left_for_arrival_on_lot set to 0\n            This means that if mailman hours are 1:00-4:00pm everyday, if\n            the random timer chooses for the mailman to arrive at 4:00, the \n            mailman will still arrive.\n            \n            However, to determine how long the mailman will stay on the lot, we \n            will use this interval.\n            ', tunable_type=TunableSimMinute, default_lower=60, default_upper=240, minimum=0), 'full_time_npc': Tunable(description='\n            NPC should be considered a full time NPC.  This will make the \n            NPC situation have no timeout and the Sim will not leave.\n            ', tunable_type=bool, default=False), 'exclusive_to_household': Tunable(description='\n            If enabled, service NPC will be exclusive to the first household\n            that hires the service.  This means, when another household \n            request a service NPC, the same Sim will not be considered for\n            that other household.\n            e.g. Butler should not be the same Sim when hired in multiple\n            played households.\n            ', tunable_type=bool, default=False), 'additional_culling_immunity': OptionalTunable(description="\n            In enabled, this unit less number will be a boost the Sim's\n            importance when the culling system scores this Sim. Higher the\n            number, lower the probability this Sim being culled.\n            \n            Performance WARNING: Remember that NPCs like Butlers can be hired\n            by many households via rotational gameplay. This number has to\n            balance the desire to keep this Sim around as well as supporting\n            multiple player families this service.\n            ", tunable=TunableRange(tunable_type=int, default=10, minimum=0))}

    @classmethod
    def auto_schedule_on_client_connect(cls):
        raise NotImplementedError

    @classmethod
    def try_charge_for_service(cls, household, cost):
        raise NotImplementedError

    @classmethod
    def get_cost(cls, time_worked_in_hours):
        raise NotImplementedError

    @classmethod
    def fake_perform(cls, household):
        fake_performer = cls.fake_perform_job()
        return fake_performer.modify_objects()

    @classmethod
    def min_duration_left_for_arrival_on_lot(cls):
        return create_time_span(minutes=cls._min_duration_left_for_arrival_on_lot)

    @classmethod
    def on_chosen_from_service_picker(cls, picker_interaction, recurring=False):
        if cls.hire_interaction is not None:
            push_affordance = picker_interaction.generate_continuation_affordance(cls.hire_interaction)
            for aop in push_affordance.potential_interactions(picker_interaction.sim, picker_interaction.context, service_npc_recurring_request=recurring):
                aop.test_and_execute(picker_interaction.context)

    @classmethod
    def min_work_duration(cls):
        return cls._work_duration_min_max.lower_bound

    @classmethod
    def max_work_duration(cls):
        return cls._work_duration_min_max.upper_bound

    @classmethod
    def on_service_sim_entered_situation(cls, service_sim, situation):
        return True

    @classmethod
    def get_default_user_specified_data_id(cls):
        pass

class ServiceNpcHireable(ServiceNpc):
    INSTANCE_TUNABLES = {'icon': TunableResourceKey(description="\n        The icon to be displayed in 'Hire a Service' UI\n        ", resource_types=CompoundTypes.IMAGE, default=None, tuning_group=GroupNames.UI), 'cost_up_front': TunableRange(description='\n            The up front cost of this NPC per service session (AKA per day)\n            in simoleons. This is always charged for the service if the\n            service shows up.', tunable_type=int, default=0, minimum=0), 'cost_hourly': TunableRange(description='\n            The cost per hour of this NPC service. This is in addition to the\n            cost up front. EX: if you have a service with 50 upfront cost and\n            then 25 cost per hour. If the npc works for 1 hour, the total cost\n            is 50 + 25 = 75 simoleons.', tunable_type=int, default=50, minimum=0), 'free_service_traits': TunableList(description='\n            If any Sim in the household has one of these traits, the service\n            will be free.\n            ', tunable=TunableReference(manager=services.trait_manager(), pack_safe=True)), 'bill_source': TunableEnumEntry(description='\n            The bill_source tied to this NPC Service. The cost for the service\n            NPC will be applied to that bill_source in total cost of bills.\n            Delinquency tests are grouped by bill_source.', tunable_type=AdditionalBillSource, default=AdditionalBillSource.Miscellaneous), '_recurring': OptionalTunable(description='\n            If enabled, when hiring this NPC, you can specify for them to be\n            regularly scheduled and come every day or hire them one time.', tunable=TunableTuple(one_time_name=TunableLocalizedString(description='\n                    Display name for this Service NPC type when recurring is false.\n                    Ex: for Maid, non recurring name is: One Time Maid', tuning_group=GroupNames.UI), recurring_name=TunableLocalizedString(description='\n                    Display name for this Service NPC type when recurring is true. \n                    Ex: for Maid, recurring maid is: Scheduled Maid', tuning_group=GroupNames.UI))), '_fake_perform_minutes_per_object': TunableSimMinute(description="\n            If we're pretending this service npc went to your lot, and the fake\n            perform tuning is run on the lot, this is the number of minutes we\n            pretend it takes for the maid to clean each object.\n            ", default=10, minimum=0), '_fake_perform_notification': OptionalTunable(description='\n            The notification to display when you return to your lot if this\n            service NPC visited your lot while you were away. The two arguments\n            available are the money charged directly to your household funds\n            (in argument 0), the money billed to your household (in argument\n            1), and the total cost (in argument 2). So, you can use {0.Money},\n            etc. in the notification.\n            ', tunable=TunableUiDialogNotificationSnippet()), 'hire_interaction': TunableReference(description='\n            The affordance to push the sim making the call when hiring this\n            service npc from a picker dialog from the phone.\n            ', manager=services.affordance_manager()), 'bill_time_of_day': OptionalTunable(description="\n            If enabled, service NPC will charge at a specified tunable time.\n            Otherwise service NPC will charge by default whenever the situation\n            ends (full time service NPC's should be collecting this way).\n            ", tunable=TunableTuple(description='\n                Time of day and failure to pay notification when the active\n                household fails to pay for the service.\n                Delinquent NPC quit notification will trigger whenever\n                the NPC quits after bills go delinquent.\n                Notification arguments available are money charged directly to \n                your household funds (in argument 0), the money billed to your \n                household (in argument 1), and the total cost (in argument 2).\n                ', time_of_day=TunableTimeOfDay(description='\n                    Time of day for butler to collect bills.\n                    ', default_hour=12), fail_to_pay_notification=TunableUiDialogNotificationSnippet(), delinquent_npc_quit_notification=TunableUiDialogNotificationSnippet()), enabled_name='specify_bill_time', disabled_name='use_situation_end_as_bill')}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    @classmethod
    def try_charge_for_service(cls, household, cost):
        for sim in household.sim_info_gen():
            if sim.trait_tracker.has_any_trait(cls.free_service_traits):
                cost = 0
                break
        if cost > household.funds.money:
            billed_amount = cost - household.funds.money
            paid_amount = household.funds.money
        else:
            billed_amount = 0
            paid_amount = cost
        first_instanced_sim = next(household.instanced_sims_gen(allow_hidden_flags=ALL_HIDDEN_REASONS), None)
        if not household.funds.try_remove(paid_amount, reason=Consts_pb2.TELEMETRY_INTERACTION_COST, sim=first_instanced_sim):
            billed_amount += paid_amount
            household.bills_manager.add_additional_bill_cost(cls.bill_source, billed_amount)
            return (0, billed_amount)
        if billed_amount > 0:
            household.bills_manager.add_additional_bill_cost(cls.bill_source, billed_amount)
        return (paid_amount, billed_amount)

    @classmethod
    def get_cost(cls, time_worked_in_hours, include_up_front_cost=True):
        cost = int(time_worked_in_hours*cls.cost_hourly)
        if include_up_front_cost:
            cost += cls.cost_up_front
        return cost

    @classmethod
    def auto_schedule_on_client_connect(cls):
        return False

    @classmethod
    def fake_perform(cls, household):
        num_modified = super().fake_perform(household)
        minutes_taken = num_modified*cls._fake_perform_minutes_per_object
        time_taken = create_time_span(minutes=minutes_taken)
        total_cost = cls.get_cost(time_taken.in_hours())
        if total_cost > 0:
            (paid_amount, billed_amount) = cls.try_charge_for_service(household, total_cost)
        else:
            (paid_amount, billed_amount) = (0, 0)
        if cls._fake_perform_notification is not None:
            cls.display_payment_notification(household, paid_amount, billed_amount, cls._fake_perform_notification)
        return num_modified

    @classmethod
    def display_payment_notification(cls, household, paid_amount, billed_amount, notification):
        household_sim = next(household.instanced_sims_gen(allow_hidden_flags=ALL_HIDDEN_REASONS), None)
        if household_sim is not None:
            dialog = notification(household_sim)
            if dialog is not None:
                dialog.show_dialog(additional_tokens=(paid_amount, billed_amount, paid_amount + billed_amount))

class ServiceNpcHireableCrafter(ServiceNpcHireable):
    INSTANCE_TUNABLES = {'recipe_picker_on_hire': TunableTuple(description='\n            The recipe picker dialog that is shown when hiring this service.\n            The dialog will be shown when we request this service using the\n            request service npc basic extra.\n            \n            Ex: when requesting pizza delivery, we can choose the type of\n            pizza.\n            ', picker_dialog=UiRecipePicker.TunableFactory(description='Tuning for what type of picker dialog to show'), recipes=TunableList(description='\n                The recipes to display in the picker dialog\n                ', tunable=TunableReference(description='\n                    Recipe to craft.\n                    ', manager=services.recipe_manager(), pack_safe=True)))}

    @classmethod
    def on_chosen_from_service_picker(cls, picker_interaction, recurring=False):
        sim = picker_interaction.sim
        dialog = cls.recipe_picker_on_hire.picker_dialog(sim, picker_interaction.get_resolver())

        def on_recipe_selected(dialog):
            recipe = dialog.get_single_result_tag()
            if recipe is None or cls.hire_interaction is None:
                return
            push_affordance = picker_interaction.generate_continuation_affordance(cls.hire_interaction)
            for aop in push_affordance.potential_interactions(sim, picker_interaction.context, service_npc_user_specified_data_id=recipe.guid64, service_npc_recurring_request=recurring):
                aop.test_and_execute(picker_interaction.context)

        for recipe in cls.recipe_picker_on_hire.recipes:
            (_, price) = recipe.get_price(is_retail=True)
            description = recipe.recipe_description(sim)
            if recipe.has_final_product_definition:
                recipe_icon = IconInfoData(icon_resource=recipe.icon_override, obj_def_id=recipe.final_product_definition_id, obj_geo_hash=recipe.final_product_geo_hash, obj_material_hash=recipe.final_product_material_hash)
            else:
                recipe_icon = IconInfoData(recipe.icon_override)
            if sim.family_funds.money < price:
                error_list = [CraftingTuning.INSUFFICIENT_FUNDS_TOOLTIP(sim)]
                result = RecipeTestResult(enabled=False, visible=False, errors=error_list)
            else:
                result = True
            row = RecipePickerRow(name=recipe.get_recipe_name(sim), price=price, icon=recipe.icon_override, row_description=description, skill_level=recipe.required_skill_level, is_enable=result, linked_recipe=recipe.base_recipe, display_name=recipe.get_recipe_picker_name(sim), icon_info=recipe_icon, tag=recipe)
            dialog.add_row(row)
        dialog.set_target_sim(sim)
        dialog.show_dialog(on_response=on_recipe_selected)

    @classmethod
    def on_service_sim_entered_situation(cls, service_sim, situation):
        if situation.role_affordance_target is None:
            recipe = services.recipe_manager().get(situation.object_definition_to_craft)
            if recipe is None:
                return False
            craftable = DebugCreateCraftableInteraction.create_craftable(recipe, service_sim, owning_household_id_override=situation.hiring_household.id, place_in_crafter_inventory=True)
            if craftable is None:
                return False
            situation.set_crafted_object_id(craftable.id)
        return True

    @classmethod
    def get_default_user_specified_data_id(cls):
        if cls.recipe_picker_on_hire.recipes:
            return random.choice(cls.recipe_picker_on_hire.recipes).guid64

class ServiceNpcNonRequestable(ServiceNpc):
    INSTANCE_TUNABLES = {'always_scheduled': Tunable(description='\n            If true, this service will automatically be requested whenever a\n            client starts up', tunable_type=bool, default=True)}

    @classmethod
    def auto_schedule_on_client_connect(cls):
        return cls.always_scheduled

    @classmethod
    def try_charge_for_service(cls, household, cost):
        return (0, 0)

    @classmethod
    def get_cost(cls, time_worked_in_hours):
        return 0

    @classproperty
    def bill_time_of_day(cls):
        pass
