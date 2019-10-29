from event_testing import test_basefrom event_testing.results import TestResultfrom event_testing.test_events import cached_testfrom interactions import ParticipantType, ParticipantTypeResponsefrom restaurants.restaurant_order import OrderStatusfrom restaurants.restaurant_tuning import get_restaurant_zone_directorfrom sims.outfits.outfit_enums import OutfitCategoryfrom sims4.tuning.tunable import HasTunableSingletonFactory, AutoFactoryInit, OptionalTunable, Tunable, TunableEnumEntry, TunableEnumWithFilter, TunableList, TunableReference, TunableThresholdfrom tag import Tagimport enumimport services
class RestaurantTest(HasTunableSingletonFactory, AutoFactoryInit, test_base.BaseTest):
    FACTORY_TUNABLES = {'subject': TunableEnumEntry(description='\n            The participant to run the tests against.\n            ', tunable_type=ParticipantType, default=ParticipantType.Actor), 'claimed_table_status': OptionalTunable(description='\n            Test for whether or not a Sim/Sims Dining Group has already claimed\n            a table, or alternatively whether or not a specific table has been\n            claimed.\n            \n            If enabled and the subject is a Sim this test will return True if \n            that Sim or the dining group they are in have already claimed a \n            table.\n            \n            If enabled and the subject is an object this test will return True \n            if the subject is a table that has been claimed. If anything other \n            than a table is passed then this test will return False.\n            ', tunable=Tunable(description="\n                If this is set to true then the test will return True if the\n                Sim/Sims Group has claimed a table or if the Table has already \n                been claimed. Otherwise it will return False.\n                \n                If this is set to False then the test will return True if the\n                Sim/Sims Group has not claimed a table yet or the Table hasn't \n                already claimed a table. Otherwise this test will return False.\n                ", tunable_type=bool, default=True)), 'waiting_for_food': OptionalTunable(description='\n            Test for whether or not the Sim specified by the subject and their\n            group currently has an order being worked on.\n            ', tunable=Tunable(description="\n                If set to True then this test will return True if the group \n                associated with the subject is currently waiting on an order \n                (This means they have a GroupOrder in status Taken or later).\n                \n                If False then this test will return True if the group associated\n                with the subject doesn't have an order with a statu > Taken.\n                \n                (Note: When the order has been delivered there is no more group\n                order to have a status.\n                ", tunable_type=bool, default=True))}

    def get_expected_args(self):
        return {'subjects': self.subject}

    def __call__(self, subjects=()):
        zone_director = get_restaurant_zone_director()
        if zone_director is None:
            return TestResult(False, 'Not currently on a restaurant lot.', tooltip=self.tooltip)
        for subject in subjects:
            if self.claimed_table_status is not None:
                if subject.is_sim:
                    result = zone_director.has_claimed_table(subject)
                else:
                    result = zone_director.table_has_been_claimed(subject.id)
                if not result == self.claimed_table_status:
                    return TestResult(False, "Sim, Group, or Table {} doesn't have the correct claimed status for the test. Test For Claimed = {}, Claimed Status = {}", subject, self.claimed_table_status, result, tooltip=self.tooltip)
            if self.waiting_for_food is not None:
                if not subject.is_sim:
                    return TestResult(False, 'Trying to get the group order of {} which is not a Sim. Tuning is bad.', subject)
                has_group_order = zone_director.has_group_order(subject.id)
                if not has_group_order:
                    if self.waiting_for_food:
                        return TestResult(False, 'Sim {} does not have a group order and therefore cannot be waiting for an order', subject)
                        group_order = zone_director.get_group_order(subject.id)
                        if self.waiting_for_food != group_order.order_status >= OrderStatus.ORDER_TAKEN and group_order.order_status < OrderStatus.ORDER_DELIVERED:
                            return TestResult(False, 'The subject is failing the waiting for order check. Sim: {}, Waiting For Order: {}', subject, self.waiting_for_food)
                else:
                    group_order = zone_director.get_group_order(subject.id)
                    if self.waiting_for_food != group_order.order_status >= OrderStatus.ORDER_TAKEN and group_order.order_status < OrderStatus.ORDER_DELIVERED:
                        return TestResult(False, 'The subject is failing the waiting for order check. Sim: {}, Waiting For Order: {}', subject, self.waiting_for_food)
        return TestResult.TRUE

class DiningSpotTestType(enum.Int):
    IS_CLAIMED = 0
    CLAIMED_BY_GROUP = 1
    CLAIMED_BY_SIM = 2

class DiningSpotTest(HasTunableSingletonFactory, AutoFactoryInit, test_base.BaseTest):
    FACTORY_TUNABLES = {'subject': TunableEnumEntry(description='\n            The participant to run the tests against.\n            ', tunable_type=ParticipantTypeResponse, default=ParticipantTypeResponse.Actor), 'test_type': TunableEnumEntry(description="\n            What type of claim table situation we want to test. The three\n            options are: \n            IS CLAIMED : will pass if the table is claimed by anyone.\n            If negate, it will pass if the table is not claimed. \n            CLAIMED BY GROUP : will pass if the table is claimed by\n            the subject sim's group. If negate it will pass if the table is not\n            claimed by the group.\n            CLAIMED BY SIM : will pass if the seat if assigned to the subject sim.\n            If negate, it will pass if the seat is not assigned to the subject sim\n            ", tunable_type=DiningSpotTestType, default=DiningSpotTestType.IS_CLAIMED), 'negate': Tunable(description='\n            If checked, the test will pass if the table/seat is not claimed.\n            Otherwise the test will pass if the table/seat is claimed by the\n            certain claim type.\n            ', tunable_type=bool, default=False), 'non_spot_seat_always_pass': Tunable(description='\n            If checked, the seat that is not a dining spot, like barstool on\n            bar or a chair not attach to table, will always pass this test.\n            ', tunable_type=bool, default=True)}

    def get_expected_args(self):
        return {'target_list': ParticipantType.Object, 'subjects': self.subject, 'interaction_context': ParticipantType.InteractionContext}

    @cached_test
    def __call__(self, target_list=None, subjects=None, interaction_context=None):
        if target_list is None:
            return TestResult(False, "Target object doesn't exist.", tooltip=self.tooltip)
        zone_director = get_restaurant_zone_director()
        if zone_director is None:
            return TestResult(False, 'Not currently on a restaurant lot.', tooltip=self.tooltip)
        for obj in target_list:
            table = None
            seats = None
            if zone_director.is_dining_table(obj):
                table = obj
                if zone_director.is_picnic_table(obj):
                    if obj.is_part:
                        seats = (obj,)
                    elif interaction_context.pick is not None:
                        parts = obj.get_closest_parts_to_position(interaction_context.pick.location)
                        seats = (parts.pop(),)
                    else:
                        seats = obj.parts
            else:
                if obj.parts:
                    if interaction_context.pick is not None:
                        parts = obj.get_closest_parts_to_position(interaction_context.pick.location)
                        seats = (parts.pop(),)
                    else:
                        seats = obj.parts
                else:
                    seats = (obj,)
                table = zone_director.get_dining_table_by_chair(seats[0])
                if table is None:
                    if self.non_spot_seat_always_pass:
                        return TestResult.TRUE
                    return TestResult(False, 'Test target {} is not dining table or dining seat in the restaurant.'.format(obj), tooltip=self.tooltip)
            if self.test_type == DiningSpotTestType.IS_CLAIMED:
                return self._test_table_claimed(table, zone_director)
            for sim_info in subjects:
                if not sim_info.is_sim:
                    return TestResult(False, '{} is not a sim for subject {}'.format(sim_info, self.subject), tooltip=self.tooltip)
                sim = sim_info.get_sim_instance()
                if sim is None:
                    return TestResult(False, '{} is not instantiated'.format(sim_info), tooltip=self.tooltip)
                if self.test_type == DiningSpotTestType.CLAIMED_BY_GROUP or seats is None:
                    return self._test_table_claimed_by_sim(table, sim, zone_director)
                if self.test_type == DiningSpotTestType.CLAIMED_BY_SIM:
                    if self.non_spot_seat_always_pass and not zone_director.seat_is_dining_spot(seats[0]):
                        return TestResult.TRUE
                    results = [self._test_seat_claimed_by_sim(seat, sim, zone_director) for seat in seats]
                    if any(results):
                        return TestResult.TRUE
                    return results[0]
        return TestResult(False, 'None of the conditions satisfied', tooltip=self.tooltip)

    def _test_table_claimed(self, table, zone_director):
        if zone_director.table_has_been_claimed(table.id):
            if self.negate:
                return TestResult(False, '{} claimed.'.format(table), tooltip=self.tooltip)
            return TestResult.TRUE
        elif self.negate:
            return TestResult.TRUE
        else:
            return TestResult(False, '{} is not claimed.'.format(table), tooltip=self.tooltip)

    def _test_table_claimed_by_sim(self, table, sim, zone_director):
        groups = zone_director.get_dining_groups_by_sim(sim)
        tables = []
        for group in groups:
            tables.extend(zone_director.get_tables_by_group_id(group.id))
        if table.id in tables:
            if self.negate:
                return TestResult(False, '{} claimed by {}.'.format(table, sim), tooltip=self.tooltip)
            return TestResult.TRUE
        elif self.negate:
            return TestResult.TRUE
        else:
            return TestResult(False, '{} is not claimed by {}.'.format(table, sim), tooltip=self.tooltip)

    def _test_seat_claimed_by_sim(self, seat, sim, zone_director):
        if zone_director.seat_claimed_by_sim(sim, seat):
            if self.negate:
                return TestResult(False, '{} claimed by {}.'.format(seat, sim), tooltip=self.tooltip)
            return TestResult.TRUE
        elif self.negate:
            return TestResult.TRUE
        else:
            return TestResult(False, '{} is not claimed by {}.'.format(seat, sim), tooltip=self.tooltip)

class DressCodeTest(HasTunableSingletonFactory, AutoFactoryInit, test_base.BaseTest):
    FACTORY_TUNABLES = {'sim_subject': TunableEnumEntry(description='\n            The participant sim to run the tests against.\n            ', tunable_type=ParticipantTypeResponse, default=ParticipantTypeResponse.Actor), 'outfit_to_test': OptionalTunable(description='\n            What outfit category to test against.\n            ', tunable=TunableEnumEntry(tunable_type=OutfitCategory, default=OutfitCategory.EVERYDAY), disabled_name='use_zone_outfit_category', enabled_name='use_literal'), 'pass_when_match': Tunable(description='\n            If checked, the test will pass the sim dresses same with the outfit\n            to test against. False then test pass only when sim is dressing\n            differently.\n            ', tunable_type=bool, default=True)}

    def get_expected_args(self):
        return {'sim_infos': self.sim_subject}

    @cached_test
    def __call__(self, sim_infos=None):
        outfit_to_test = self.outfit_to_test
        if outfit_to_test is None:
            zone_director = get_restaurant_zone_director()
            if zone_director is None:
                return TestResult(False, "Want to test against zone director's dress code but zone director doesn't exist.", tooltip=self.tooltip)
            outfit_to_test = zone_director.get_zone_dress_code()
        if outfit_to_test is None:
            return TestResult.TRUE
        for sim_info in sim_infos:
            if not sim_info.is_sim:
                return TestResult(False, '{} is not a sim for subject {}'.format(sim_info, self.sim_subject), tooltip=self.tooltip)
            sim_current_outfit_category = sim_info.get_current_outfit()[0]
            if self.pass_when_match and sim_current_outfit_category != outfit_to_test:
                return TestResult(False, "Dresscode {}, {} is wearing {}, they don't match".format(outfit_to_test, sim_info, sim_current_outfit_category), tooltip=self.tooltip)
            if self.pass_when_match or sim_current_outfit_category == outfit_to_test:
                return TestResult(False, '{} is wearing {} that matches the dresscode'.format(sim_info, sim_current_outfit_category), tooltip=self.tooltip)
        return TestResult.TRUE

class RestaurantPaymentTest(HasTunableSingletonFactory, AutoFactoryInit, test_base.BaseTest):
    FACTORY_TUNABLES = {'sim_subject': TunableEnumEntry(description='\n            The participant to run the tests against.\n            ', tunable_type=ParticipantTypeResponse, default=ParticipantTypeResponse.Actor), 'negate': Tunable(description="\n            If checked, the test will pass if the dining group doesn't have bill.\n            If not, it will pass if the dining group has bill.\n            ", tunable_type=bool, default=False)}

    def get_expected_args(self):
        return {'sim_infos': self.sim_subject}

    @cached_test
    def __call__(self, sim_infos=None):
        zone_director = get_restaurant_zone_director()
        if zone_director is None:
            return TestResult(False, "Want to test restaurant payment but zone director doesn't exist.", tooltip=self.tooltip)
        for sim_info in sim_infos:
            if not sim_info.is_sim:
                return TestResult(False, '{} is not a sim for subject {}'.format(sim_info, self.sim_subject), tooltip=self.tooltip)
            sim_instance = sim_info.get_sim_instance()
            dining_groups = zone_director.get_dining_groups_by_sim(sim_instance)
            has_bill = False
            for dining_group in dining_groups:
                if dining_group.meal_cost != 0:
                    has_bill = True
                    if not self.negate:
                        return TestResult.TRUE
            if has_bill and self.negate:
                return TestResult(False, "{}'s group has bill need to pay".format(sim_info), tooltip=self.tooltip)
            if has_bill or not self.negate:
                return TestResult(False, "{}'s group doesn't have bill to pay".format(sim_info), tooltip=self.tooltip)
        return TestResult.TRUE

class RestaurantCourseItemCountTest(HasTunableSingletonFactory, AutoFactoryInit, test_base.BaseTest):
    FACTORY_TUNABLES = {'course': TunableEnumWithFilter(description='\n            The course to check for this test.\n            ', tunable_type=Tag, filter_prefixes=['recipe_course'], default=Tag.INVALID, invalid_enums=(Tag.INVALID,), pack_safe=True), 'threshold': TunableThreshold(description='\n            The number of items that should available in this course.\n            '), 'blacklist_recipes': TunableList(description='\n            The items from the course to not include in this test.\n            ', tunable=TunableReference(manager=services.recipe_manager(), class_restrictions=('Recipe',), pack_safe=True))}

    def get_expected_args(self):
        return {}

    def __call__(self):
        zone_director = get_restaurant_zone_director()
        if zone_director is None:
            return TestResult(False, 'Want to test restaurant course item count but not in a restaurant.', tooltip=self.tooltip)
        item_count = len([recipe for recipe in zone_director.get_menu_for_course(self.course) if recipe not in self.blacklist_recipes])
        if not self.threshold.compare(item_count):
            return TestResult(False, 'Only {} items in {}'.format(item_count, self.course), tooltip=self.tooltip)
        return TestResult.TRUE
