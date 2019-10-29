from _collections import defaultdictfrom collections import Counterfrom protocolbuffers import Consts_pb2from event_testing.resolver import SingleActorAndObjectResolverfrom event_testing.tests import TunableTestSetfrom scheduler import WeeklySchedulefrom sims4.localization import LocalizationHelperTuning, TunableLocalizedStringFactoryfrom sims4.tuning.dynamic_enum import DynamicEnumLockedfrom sims4.tuning.tunable import TunableEnumEntry, TunableVariant, TunablePercent, TunableSet, TunableRange, Tunable, TunableMapping, TunableTuplefrom ui.ui_dialog_notification import UiDialogNotificationimport enumimport servicesimport sims4.commandsimport tag
class RebateItem(DynamicEnumLocked, partitioned=True):
    INVALID = 0

class RebateCategoryEnum(enum.Int):
    GAMEPLAY_OBJECT = 0
    BUILD_BUY = 1

class RebateCategory(TunableTuple):

    def __init__(self, **kwargs):
        super().__init__(rebate_category_enum=TunableEnumEntry(description='\n            The category this item falls under, which determines 1. how to handle\n            registered tests and 2. whether to apply a rebate item to an object.\n            ', tunable_type=RebateCategoryEnum, default=RebateCategoryEnum.BUILD_BUY), cyclical=Tunable(description="\n            If checked, the object  will get re-added to rebates after the\n            next Rebate Cycle.\n            \n            This is useful when we want to give a rebate regularly and only\n            when an object passes certain tests, e.g. 'give a weekly rebate to \n            sims that have mature coconut plants.'\n            ", tunable_type=bool, default=False), **kwargs)

class RebateData(TunableTuple):

    def __init__(self, **kwargs):
        super().__init__(valid_objects=TunableVariant(description='\n            The items to which the rebate will be applied.\n            ', by_tag=TunableSet(description='\n                The rebate will only be applied to objects purchased with the\n                tags in this list.\n                ', tunable=TunableEnumEntry(tunable_type=tag.Tag, default=tag.Tag.INVALID, invalid_enums=(tag.Tag.INVALID,))), locked_args={'all_purchases': None}, default='all_purchases'), rebate_payout_type=TunableVariant(percentage=TunablePercent(description='\n                The percentage of the catalog price that the player will get\n                back in the rebate.\n                ', default=10), per_item=TunableRange(description='\n                The amount per valid object the player will get back in the\n                rebate\n                ', tunable_type=int, default=1, minimum=1)), notification_text=TunableLocalizedStringFactory(description='\n            A string representing the line item on the notification\n            explaining why Sims with this trait received a rebate.\n            \n            This string is provided one token: the percentage discount\n            obtained due to having this trait.\n            \n            e.g.:\n             {0.Number}% off for purchasing Art and leveraging Critical\n             Connections.\n            '), tests_set=TunableTestSet(description='\n            If these tests pass, then the object is scheduled for the next \n            scheduled rebate event.\n            '), rebate_category=TunableVariant(description='\n            Specify a rebate category for this rebate item.\n            \n            GAMEPLAY_OBJECT: A GAMEPLAY_OBJECT category rebate item has the option\n            of either being a one-time rebate or a cyclical rebate. If tests are\n            tuned, the object has two opportunities to get added to rebates\n            before the next scheduled rebate event: once on add and its tests\n            pass, the next when its tests pass.\n            \n            BUILD_BUY: A BUILD_BUY category rebate item will give a one-time rebate\n            of all the valid objects purchased through build-buy.\n            ', buildbuy=RebateCategory(locked_args={'rebate_category_enum': RebateCategoryEnum.BUILD_BUY, 'cyclical': False}), gameplay_object=RebateCategory(locked_args={'rebate_category_enum': RebateCategoryEnum.GAMEPLAY_OBJECT}), default='buildbuy'))

class RebateManager:
    REBATES = TunableMapping(description='\n        A mapping of all rebate items to rebate data.\n        ', key_type=TunableEnumEntry(tunable_type=RebateItem, default=RebateItem.INVALID), value_type=RebateData())
    REBATE_PAYMENT_SCHEDULE = WeeklySchedule.TunableFactory(description='\n        The schedule when accrued rebates will be paid out.\n        ')
    REBATE_CYCLE = WeeklySchedule.TunableFactory(description='\n        The day of the week at which objects that qualify for cyclical rebates\n        will get tested back in and added to rebate objects.\n        ')
    REBATE_NOTIFICATION = UiDialogNotification.TunableFactory(description="\n        The notification that will show when the player receives their rebate\n        money.\n        \n        The notification's text is provided two tokens:\n         0 - An integer representing the total rebate amount \n         \n         1 - A string. The contents of the string are a bulleted list of the\n         entries specified for each of the traits.\n         \n        e.g.:\n         A rebate check of {0.Money} has been received! Sims in the household\n         were able to save on their recent purchases:\n{1.String}\n        ")

    def __init__(self, household):
        self._household = household
        self._rebates = Counter()
        self._rebate_object_ids = defaultdict(list)
        self._schedule = None
        self._rebate_cycle = None

    def register_tests_for_rebates(self, obj, rebate_item):
        if rebate_item.rebate_category.rebate_category_enum == RebateCategoryEnum.GAMEPLAY_OBJECT:
            obj.register_rebate_tests(rebate_item.tests_set)

    def add_rebate_for_object(self, obj_id, category):
        object_manager = services.object_manager()
        for (rebate_item, rebate_data) in self.REBATES.items():
            if rebate_data.rebate_category.rebate_category_enum != category:
                pass
            else:
                obj = object_manager.get(obj_id)
                if obj is None:
                    return
                valid_objects = rebate_data.valid_objects
                if valid_objects is not None and not obj.has_any_tag(valid_objects):
                    pass
                elif self.run_tests_on_object_and_household_sims(obj, rebate_data.tests_set):
                    self._rebates[rebate_item] += rebate_data.rebate_payout_type if type(rebate_data.rebate_payout_type) is int else obj.catalog_value*rebate_data.rebate_payout_type
                    self._rebate_object_ids[rebate_item] = self._rebate_object_ids[rebate_item] + [obj_id]
                else:
                    self.register_tests_for_rebates(obj, rebate_data)
        if self._rebates:
            self.start_rebate_schedule()

    def add_rebate_for_object_from_cycle(self, scheduler, alarm_data, extra_data):
        obj_id = extra_data.get('obj_id')
        category = extra_data.get('category')
        self.add_rebate_for_object(obj_id, category)

    def add_rebate_cycle(self):
        cyclical_rebate_object_ids = set()
        for (rebate_item, rebate_object_id_list) in self._rebate_object_ids.items():
            rebate_data = self.REBATES.get(rebate_item)
            if not rebate_data.rebate_category.cyclical:
                pass
            else:
                for rebate_object_id in rebate_object_id_list:
                    cyclical_rebate_object_ids.add((rebate_object_id, rebate_data.rebate_category))
        for (cyclical_object_id, rebate_category) in cyclical_rebate_object_ids:
            if self._rebate_cycle is None:
                self._rebate_cycle = self.REBATE_CYCLE(start_callback=self.add_rebate_for_object_from_cycle, extra_data={'obj_id': cyclical_object_id, 'category': rebate_category}, schedule_immediate=False)
            else:
                self._rebate_cycle.merge_schedule(self.REBATE_CYCLE(start_callback=self.add_rebate_for_object_from_cycle, extra_data={'obj_id': cyclical_object_id, 'category': rebate_category}, schedule_immediate=False))

    def run_tests_on_object_and_household_sims(self, obj, test_set):
        result = False
        for sim_info in self._household.sim_info_gen():
            sim_and_object_resolver = SingleActorAndObjectResolver(sim_info, obj, None)
            if test_set.run_tests(sim_and_object_resolver):
                result = True
        return result

    def clear_rebates(self):
        self._rebates.clear()
        self._rebate_object_ids.clear()

    def start_rebate_schedule(self):
        if self._schedule is None:
            self._schedule = self.REBATE_PAYMENT_SCHEDULE(start_callback=self.payout_rebates, schedule_immediate=False)

    def payout_rebates(self, *_):
        if not self._rebates:
            return
        rebate_reasons = []
        for rebate_item_enum in self._rebates.keys():
            rebate_data = self.REBATES.get(rebate_item_enum)
            rebate_reasons.append(rebate_data.notification_text(rebate_data.rebate_payout_type if type(rebate_data.rebate_payout_type) is int else rebate_data.rebate_payout_type*100))
        rebate_reasons_string = LocalizationHelperTuning.get_bulleted_list((None,), rebate_reasons)
        total_rebate_amount = sum(self._rebates.values())
        active_sim_info = services.active_sim_info()
        dialog = self.REBATE_NOTIFICATION(active_sim_info)
        dialog.show_dialog(additional_tokens=(total_rebate_amount, rebate_reasons_string))
        self._household.funds.add(total_rebate_amount, reason=Consts_pb2.TELEMETRY_MONEY_ASPIRATION_REWARD, sim=active_sim_info)
        self.add_rebate_cycle()
        self.clear_rebates()

@sims4.commands.Command('households.rebates.payout')
def payout_rebates(household_id:int=None, _connection=None):
    if household_id is None:
        household = services.active_household()
    else:
        household_manager = services.household_manager()
        household = household_manager.get(household_id)
    if household is None:
        return False
    rebate_manager = household.rebate_manager
    if rebate_manager is None:
        return False
    rebate_manager.payout_rebates()
    return True
