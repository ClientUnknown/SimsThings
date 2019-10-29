from event_testing.results import TestResultfrom event_testing.test_events import cached_testfrom interactions import ParticipantTypefrom objects.object_tests import ObjectTypeFactory, ObjectTagFactoryfrom objects.slots import SlotType, RuntimeSlotfrom sims4.tuning.tunable import HasTunableSingletonFactory, AutoFactoryInit, TunableEnumEntry, TunableVariant, Tunable, TunableTuple, TunableSingletonFactory, TunableList, OptionalTunableimport event_testing.test_baseimport sims4.logimport singletonslogger = sims4.log.Logger('Tests')
class SlotTest(HasTunableSingletonFactory, AutoFactoryInit, event_testing.test_base.BaseTest):
    TEST_EMPTY_SLOT = 1
    TEST_USED_SLOT = 2
    FACTORY_TUNABLES = {'description': 'Verify slot status.  This test will only apply for single entity participants', 'participant': TunableEnumEntry(description='\n            The subject of this situation data test.', tunable_type=ParticipantType, default=ParticipantType.Object), 'child_slot': TunableVariant(description=' \n            The slot on the participant to be tested. \n            ', by_name=Tunable(description=' \n                The exact name of a slot on the participant to be tested.\n                ', tunable_type=str, default='_ctnm_'), by_reference=SlotType.TunableReference(description=' \n                A particular slot type to be tested.\n                '), default='by_reference'), 'slot_test_type': TunableVariant(description='\n            Type of slot test to run on target subject.\n            ', has_empty_slot=TunableTuple(description="\n                Verify the slot exists on the participant and it's unoccupied\n                ", check_all_slots=Tunable(description='\n                    Check this if you want to check that all the slots of the \n                    subject are empty.\n                    ', tunable_type=bool, default=False), locked_args={'test_type': TEST_EMPTY_SLOT}), has_used_slot=TunableTuple(description='\n                Verify if any slot of the child slot type is currently occupied\n                ', check_all_slots=Tunable(description='\n                    Check this if you want to check that all the slots of the \n                    subject are used.\n                    ', tunable_type=bool, default=False), object_type=OptionalTunable(description='\n                    If enabled one of the children in the used slot must be of\n                    a certain kind of object. This test can be done by \n                    definition id or object tags.\n                    ', tunable=TunableVariant(description='\n                        If set to definition id then at least one of the child\n                        objects must pass the definition test specified.\n                        \n                        If set to object tags then at least one of the child\n                        objects must pass the object tag test specified. \n                        ', definition_id=ObjectTypeFactory.TunableFactory(), object_tags=ObjectTagFactory.TunableFactory())), locked_args={'test_type': TEST_USED_SLOT}), default='has_empty_slot'), 'slot_count_required': Tunable(description='\n            Minimum number of slots that must pass test \n            only valid for reference slots And not if all are required to pass\n            ', tunable_type=int, default=1), 'check_part_owner': Tunable(description='\n            If enabled and target of tests is a part, the test will be run\n            on the part owner instead.\n            ', tunable_type=bool, default=False)}

    def get_expected_args(self):
        return {'test_targets': self.participant}

    @cached_test
    def __call__(self, test_targets=()):
        for target in test_targets:
            if target.is_sim:
                pass
            else:
                if target.is_part:
                    target = target.part_owner
                valid_count = 0
                if self.check_part_owner and self.slot_test_type.test_type == self.TEST_EMPTY_SLOT:
                    if isinstance(self.child_slot, str):
                        runtime_slot = RuntimeSlot(target, sims4.hash_util.hash32(self.child_slot), singletons.EMPTY_SET)
                        if runtime_slot.empty:
                            return TestResult.TRUE
                    elif self.slot_test_type.check_all_slots:
                        if all(runtime_slot.empty for runtime_slot in target.get_runtime_slots_gen(slot_types={self.child_slot}, bone_name_hash=None)):
                            return TestResult.TRUE
                    else:
                        for runtime_slot in target.get_runtime_slots_gen(slot_types={self.child_slot}, bone_name_hash=None):
                            if runtime_slot.empty:
                                valid_count += 1
                                if valid_count >= self.slot_count_required:
                                    return TestResult.TRUE
                elif self.slot_test_type.test_type == self.TEST_USED_SLOT:
                    if isinstance(self.child_slot, str):
                        runtime_slot = RuntimeSlot(target, sims4.hash_util.hash32(self.child_slot), singletons.EMPTY_SET)
                        if not runtime_slot.empty:
                            if self.slot_test_type.object_type is not None:
                                for child in runtime_slot.children:
                                    if self.slot_test_type.object_type(child):
                                        break
                                return TestResult(False, 'None of the children objects were of the specified type. {} children={}', self.slot_test.object_type, runtime_slot.children)
                            return TestResult.TRUE
                            if self.slot_test_type.check_all_slots:
                                if all(not runtime_slot.empty for runtime_slot in target.get_runtime_slots_gen(slot_types={self.child_slot}, bone_name_hash=None)):
                                    return TestResult.TRUE
                                    for runtime_slot in target.get_runtime_slots_gen(slot_types={self.child_slot}, bone_name_hash=None):
                                        if self.slot_test_type.object_type is not None:
                                            for child in runtime_slot.children:
                                                if self.slot_test_type.object_type(child):
                                                    break
                                            return TestResult(False, 'None of the children objects were of the specified type. {} children={}', self.slot_test_type.object_type, runtime_slot.children)
                                        valid_count += 1
                                        if runtime_slot.empty or valid_count >= self.slot_count_required:
                                            return TestResult.TRUE
                            else:
                                for runtime_slot in target.get_runtime_slots_gen(slot_types={self.child_slot}, bone_name_hash=None):
                                    if self.slot_test_type.object_type is not None:
                                        for child in runtime_slot.children:
                                            if self.slot_test_type.object_type(child):
                                                break
                                        return TestResult(False, 'None of the children objects were of the specified type. {} children={}', self.slot_test_type.object_type, runtime_slot.children)
                                    valid_count += 1
                                    if runtime_slot.empty or valid_count >= self.slot_count_required:
                                        return TestResult.TRUE
                    elif self.slot_test_type.check_all_slots:
                        if all(not runtime_slot.empty for runtime_slot in target.get_runtime_slots_gen(slot_types={self.child_slot}, bone_name_hash=None)):
                            return TestResult.TRUE
                            for runtime_slot in target.get_runtime_slots_gen(slot_types={self.child_slot}, bone_name_hash=None):
                                if self.slot_test_type.object_type is not None:
                                    for child in runtime_slot.children:
                                        if self.slot_test_type.object_type(child):
                                            break
                                    return TestResult(False, 'None of the children objects were of the specified type. {} children={}', self.slot_test_type.object_type, runtime_slot.children)
                                valid_count += 1
                                if runtime_slot.empty or valid_count >= self.slot_count_required:
                                    return TestResult.TRUE
                    else:
                        for runtime_slot in target.get_runtime_slots_gen(slot_types={self.child_slot}, bone_name_hash=None):
                            if self.slot_test_type.object_type is not None:
                                for child in runtime_slot.children:
                                    if self.slot_test_type.object_type(child):
                                        break
                                return TestResult(False, 'None of the children objects were of the specified type. {} children={}', self.slot_test_type.object_type, runtime_slot.children)
                            valid_count += 1
                            if runtime_slot.empty or valid_count >= self.slot_count_required:
                                return TestResult.TRUE
        return TestResult(False, "SlotTest: participant doesn't meet slot availability requirements", tooltip=self.tooltip)
TunableSlotTest = TunableSingletonFactory.create_auto_factory(SlotTest)
class RelatedSlotsTest(HasTunableSingletonFactory, AutoFactoryInit, event_testing.test_base.BaseTest):
    FACTORY_TUNABLES = {'participant': TunableEnumEntry(description='\n            The subject of this slot test.', tunable_type=ParticipantType, default=ParticipantType.Object), 'slot_tests': TunableList(description='\n            A list of slot tests that must all pass on a single part in order\n            for that part to count.\n            ', tunable=TunableTuple(description='\n                A tuple containing all the information for the slot tests.\n                ', slot=SlotType.TunableReference(description=' \n                    A particular slot type to be tested.\n                    '), requires_child=OptionalTunable(description='\n                    If set to has children then there must be a child in the \n                    slot to pass the test.\n                    \n                    If not checked then the slot must be a empty in order to\n                    pass the test.\n                    ', disabled_name='No_Children', enabled_name='Has_Children', tunable=TunableTuple(description='\n                        A tuple holding all of the different tuning for what\n                        matters about the child of a specified slot. For\n                        instance the test for what kind of object you are \n                        looking for in this specific slot type.\n                        ', object_type=OptionalTunable(description='\n                            A test for what type of object at least one of the\n                            children of this slot must be.\n                            ', tunable=TunableVariant(description='\n                                If set to definition id then at least one of the child\n                                objects must pass the definition test specified.\n                                \n                                If set to object tags then at least one of the child\n                                objects must pass the object tag test specified. \n                                ', definition_id=ObjectTypeFactory.TunableFactory(), object_tags=ObjectTagFactory.TunableFactory())))), count_required=Tunable(description='\n                    Minimum number of slots that must pass the test (to either be\n                    empty or have children) before the requirement is met.\n                    ', tunable_type=int, default=1))), 'parts_required': Tunable(description='\n            The number of parts that must pass all of the slot tests in order\n            for this test to return True.\n            ', tunable_type=int, default=1)}

    def get_expected_args(self):
        return {'test_targets': self.participant}

    def test_part(self, part):
        for entry in self.slot_tests:
            valid_count = 0
            for runtime_slot in part.get_runtime_slots_gen(slot_types={entry.slot}, bone_name_hash=None):
                if entry.requires_child is not None and entry.requires_child.object_type is not None:
                    for obj in runtime_slot.children:
                        if entry.requires_child.object_type(obj):
                            valid_count += 1
                else:
                    valid_count += 1
                if entry.requires_child is None == runtime_slot.empty and valid_count >= entry.count_required:
                    break
            return False
        return True

    @cached_test
    def __call__(self, test_targets=None):
        if test_targets is None:
            return TestResult(False, 'RelatedSlotsTest: There are no test targets')
        for target in test_targets:
            if target.is_part:
                if self.test_part(target):
                    if self.parts_required == 1:
                        return TestResult.TRUE
                    return TestResult(False, 'Running a related slot test against an object part {} with a required parts count > 1 ({}). This will always fail.', target, self.parts_required)
                    if target.parts:
                        valid_parts = 0
                        for part in target.parts:
                            if self.test_part(part):
                                valid_parts += 1
                                if valid_parts >= self.parts_required:
                                    return TestResult.TRUE
            elif target.parts:
                valid_parts = 0
                for part in target.parts:
                    if self.test_part(part):
                        valid_parts += 1
                        if valid_parts >= self.parts_required:
                            return TestResult.TRUE
        return TestResult(False, '{} Failed RelatedSlotTest. Not enough parts passed all of the slot tests.', test_targets)
