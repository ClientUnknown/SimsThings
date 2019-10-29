import collectionsimport randomimport weakreffrom element_utils import CleanupType, build_element, build_critical_section, build_critical_section_with_finally, build_delayed_elementfrom interactions import ParticipantType, ParticipantTypeSingleSim, ParticipantTypeSingle, ParticipantTypeSavedActorfrom interactions.utils.destruction_liability import DeleteObjectLiability, DELETE_OBJECT_LIABILITYfrom interactions.utils.success_chance import SuccessChancefrom objects import VisibilityStatefrom objects.client_object_mixin import ClientObjectMixinfrom objects.slots import RuntimeSlotfrom sims.sim_dialogs import SimPersonalityAssignmentDialogfrom sims4.tuning.tunable import HasTunableFactory, TunableVariant, TunableTuple, TunableEnumEntry, Tunable, TunableReference, TunableRealSecond, OptionalTunable, TunableRange, TunableSimMinute, AutoFactoryInit, TunableSetfrom singletons import EMPTY_SETfrom tag import Tagfrom ui.ui_dialog import PhoneRingTypefrom ui.ui_dialog_generic import TEXT_INPUT_FIRST_NAME, TEXT_INPUT_LAST_NAMEfrom ui.ui_dialog_rename import RenameDialogElementimport build_buyimport clockimport elementsimport objectsimport placementimport servicesimport sims4.logimport sims4.resourceslogger = sims4.log.Logger('Interaction_Elements')
class XevtTriggeredElement(elements.ParentElement, HasTunableFactory, AutoFactoryInit):
    AT_BEGINNING = 'at_beginning'
    AT_END = 'at_end'
    ON_XEVT = 'on_xevt'
    TIMING_DESCRIPTION = '\n        Determines the exact timing of the behavior, either at the beginning\n        of an interaction, the end, or when an xevt occurs in an animation\n        played as part of the interaction.\n        '
    FakeTiming = collections.namedtuple('FakeTiming', ('timing', 'offset_time', 'criticality', 'xevt_id'))
    LOCKED_AT_BEGINNING = FakeTiming(AT_BEGINNING, None, None, None)
    LOCKED_AT_END = FakeTiming(AT_END, None, None, None)
    LOCKED_ON_XEVT = FakeTiming(ON_XEVT, None, None, None)
    FACTORY_TUNABLES = {'timing': TunableVariant(description=TIMING_DESCRIPTION, default=AT_END, at_beginning=TunableTuple(description="\n                The behavior should occur at the very beginning of the\n                interaction.  It will not be tightly synchronized visually with\n                animation.  This isn't a very common use case and would most\n                likely be used in an immediate interaction or to change hidden\n                state that is used for bookkeeping rather than visual\n                appearance.\n                ", offset_time=OptionalTunable(description='\n                    If enabled, the interaction will wait this amount of time\n                    after the beginning before running the element.\n                    \n                    Only use this if absolutely necessary. Better alternatives\n                    include using xevts, time based conditional action with\n                    loot ops, and using outcomes.\n                    ', tunable=TunableSimMinute(description='The interaction will wait this amount of time after the beginning before running the element', default=2), deprecated=True), locked_args={'timing': AT_BEGINNING, 'criticality': CleanupType.NotCritical, 'xevt_id': None}), at_end=TunableTuple(description='\n                The behavior should occur at the end of the interaction.  It\n                will not be tightly synchronized visually with animation.  An\n                example might be an object that gets dirty every time a Sim uses\n                it (so using a commodity change is overkill) but no precise\n                synchronization with animation is desired, as might be the case\n                with vomiting in the toilet.\n                ', locked_args={'timing': AT_END, 'xevt_id': None, 'offset_time': None}, criticality=TunableEnumEntry(CleanupType, CleanupType.OnCancel)), on_xevt=TunableTuple(description="\n                The behavior should occur synchronized visually with an xevt in\n                an animation played as part of the interaction.  If for some\n                reason such an event doesn't occur, the behavior will occur at\n                the end of the interaction.  This is by far the most common use\n                case, as when a Sim flushes a toilet and the water level should\n                change when the actual flush animation and effects fire.\n                ", locked_args={'timing': ON_XEVT, 'offset_time': None}, criticality=TunableEnumEntry(CleanupType, CleanupType.OnCancel), xevt_id=Tunable(int, 100))), 'success_chance': SuccessChance.TunableFactory(description='\n            The percentage chance that this action will be applied.\n            ')}

    def __init__(self, interaction, *, timing, sequence=(), **kwargs):
        super().__init__(timing=None, **kwargs)
        self.interaction = interaction
        self.sequence = sequence
        self.timing = timing.timing
        self.criticality = timing.criticality
        self.xevt_id = timing.xevt_id
        self.result = None
        self.triggered = False
        self.offset_time = timing.offset_time
        self._XevtTriggeredElement__event_handler_handle = None
        success_chance = self.success_chance.get_chance(interaction.get_resolver())
        self._should_do_behavior = random.random() <= success_chance

    def _register_event_handler(self, element):
        self._XevtTriggeredElement__event_handler_handle = self.interaction.animation_context.register_event_handler(self._behavior_event_handler, handler_id=self.xevt_id)

    def _release_event_handler(self, element):
        self._XevtTriggeredElement__event_handler_handle.release()
        self._XevtTriggeredElement__event_handler_handle = None

    def _behavior_element(self, timeline):
        if not self.triggered:
            self.triggered = True
            if self._should_do_behavior:
                self.result = self._do_behavior()
            else:
                self.result = None
        return self.result

    def _behavior_event_handler(self, *_, **__):
        if not self.triggered:
            self.triggered = True
            if self._should_do_behavior:
                self.result = self._do_behavior()
            else:
                self.result = None

    def _run(self, timeline):
        if self.timing == self.AT_BEGINNING:
            if self.offset_time is None:
                sequence = [self._behavior_element, self.sequence]
            else:
                sequence = build_delayed_element(self.sequence, clock.interval_in_sim_minutes(self.offset_time), self._behavior_element, soft_sleep=True)
        elif self.timing == self.AT_END:
            sequence = [self.sequence, self._behavior_element]
        elif self.timing == self.ON_XEVT:
            sequence = [build_critical_section(self._register_event_handler, self.sequence, self._release_event_handler), self._behavior_element]
        child_element = build_element(sequence, critical=self.criticality)
        child_element = self._build_outer_elements(child_element)
        return timeline.run_child(child_element)

    def _build_outer_elements(self, sequence):
        return sequence

    def _do_behavior(self):
        raise NotImplementedError

    @classmethod
    def validate_tuning_interaction(cls, interaction, basic_extra):
        if basic_extra._tuned_values.timing.timing != XevtTriggeredElement.ON_XEVT:
            return
        if interaction.one_shot and interaction.basic_content.animation_ref is None:
            logger.error('The interaction ({}) has a tuned basic extra ({}) that occurs on an xevt but has no animation content.', interaction, basic_extra.factory, owner='shipark')
        elif interaction.staging:
            staging_content = interaction.basic_content.content.content_set._tuned_values
            if staging_content.affordance_links is None and staging_content.phase_tuning is None and interaction.basic_content.animation_ref is None:
                if interaction.provided_posture_type is None:
                    logger.error('The interaction ({}) has a tuned basic extra ({}) that occurs on an xevt tuned on a staging interaction without any staging content.', interaction, basic_extra.factory, owner='shipark')
                elif interaction.provided_posture_type._animation_data is None:
                    logger.error('The posture-providing interaction ({}) has a tuned basic extra ({}) that occurs on an xevt but has no animation content in the posture.', interaction, basic_extra.factory, owner='shipark')
        elif interaction.looping and interaction.basic_content.animation_ref is None:
            logger.error('The interaction ({}) has a tuned basic extra ({}) that occurs on an xevt but has no animation content.', interaction, basic_extra.factory, owner='shipark')

    @classmethod
    def validate_tuning_outcome(cls, outcome, basic_extra, interaction_name):
        if outcome.animation_ref is None and outcome.response is None and outcome.social_animation is None:
            logger.error('The interaction ({}) has an outcome with a tuned basic extra ({}) that occurs on an xevt, but has no animation content.', interaction_name, basic_extra, owner='shipark')

class ParentObjectElement(XevtTriggeredElement):
    FACTORY_TUNABLES = {'description': "\n        This element parents one participant of an interaction to another in\n        a way that doesn't necessarily depend on animation.  Most parenting\n        should be handled by animation or the posture transition system, so\n        make sure you know why you aren't using one of those systems for\n        your feature before tuning this.\n        \n        Examples include positioning objects that move but aren't carryable by\n        Sims (like the canvas on the easel) or objects that should be positioned\n        as a result of an immediate interaction.\n        ", '_parent_object': TunableEnumEntry(description='\n            The participant of an interaction to which an object will be\n            parented.\n            ', tunable_type=ParticipantType, default=ParticipantType.Object), '_check_part_owner': Tunable(description='\n            If enabled and parent object is a part, the test will be run on\n            the part owner instead.\n            ', tunable_type=bool, default=False), '_parent_slot': TunableVariant(description='\n            The slot on the parent object where the child object should go. This\n            may be either the exact name of a bone on the parent object or a\n            slot type, in which case the first empty slot of the specified type\n            in which the child object fits will be used.\n            ', by_name=Tunable(description="\n                The exact name of a slot on the parent object in which the child\n                object should go.  No placement validation will be done on this\n                slot, as long as it is empty the child will always be placed\n                there.  This should only be used on slots the player isn't\n                allowed to use in build mode, as in the original design for the\n                service slots on the bar, or by GPEs testing out functionality\n                before modelers and designers have settled on slot types and\n                names for a particular design.\n                ", tunable_type=str, default='_ctnm_'), by_reference=TunableReference(description='\n                A particular slot type in which the child object should go.  The\n                first empty slot found on the parent of the specified type in\n                which the child object fits will be used.  If no such slot is\n                found, the parenting will not occur and the interaction will be\n                canceled.\n                ', manager=services.get_instance_manager(sims4.resources.Types.SLOT_TYPE))), '_child_object': TunableEnumEntry(description='\n            The participant of the interaction which will be parented to the\n            parent object.\n            ', tunable_type=ParticipantType, default=ParticipantType.CarriedObject)}

    def __init__(self, interaction, get_child_object_fn=None, ignore_object_placmenent_verification=False, **kwargs):
        super().__init__(interaction, **kwargs)
        _parent_object = kwargs['_parent_object']
        _parent_slot = kwargs['_parent_slot']
        _child_object = kwargs['_child_object']
        self._parent_object = interaction.get_participant(_parent_object)
        self._ignore_object_placmenent_verification = ignore_object_placmenent_verification
        if self._parent_object.is_part:
            self._parent_object = self._parent_object.part_owner
        self.child_participant_type = _child_object
        if self._check_part_owner and get_child_object_fn is None:
            self._child_participant_type = _child_object
        else:
            self._get_child_object = get_child_object_fn
        if isinstance(_parent_slot, str):
            self._slot_type = None
            self._bone_name_hash = sims4.hash_util.hash32(_parent_slot)
        else:
            self._slot_type = _parent_slot
            self._bone_name_hash = None

    def _get_child_object(self):
        return self.interaction.get_participant(self.child_participant_type)

    def _do_behavior(self):
        child_object = self._get_child_object()
        current_child_object_parent_slot = child_object.parent_slot
        if self._slot_type is not None:
            for runtime_slot in self._parent_object.get_runtime_slots_gen(slot_types={self._slot_type}, bone_name_hash=self._bone_name_hash):
                if runtime_slot == current_child_object_parent_slot:
                    return True
                result = runtime_slot.is_valid_for_placement(obj=child_object)
                if self._ignore_object_placmenent_verification or result:
                    runtime_slot.add_child(child_object)
                    return True
                logger.warn("runtime_slot isn't valid for placement: {}", result, owner='nbaker')
            logger.error('The parent object: ({}) does not have the requested slot type: ({}) required for this parenting, or the child ({}) is not valid for this slot type in {}.', self._parent_object, self._slot_type, child_object, self.interaction, owner='nbaker')
            return False
        if self._bone_name_hash is not None:
            if current_child_object_parent_slot is not None and current_child_object_parent_slot.slot_name_hash == self._bone_name_hash:
                return True
            runtime_slot = RuntimeSlot(self._parent_object, self._bone_name_hash, EMPTY_SET)
            if self._ignore_object_placmenent_verification or runtime_slot.empty:
                runtime_slot.add_child(child_object, joint_name_or_hash=self._bone_name_hash)
                return True
            else:
                logger.error('The parent object: ({}) does not have the requested slot type: ({}) required for this parenting, or the child ({}) is not valid for this slot type in {}.  Slot is empty: {}', self._parent_object, self._bone_name_hash, child_object, self.interaction, runtime_slot.empty, owner='nbaker')
                return False

class FadeChildrenElement(elements.ParentElement, HasTunableFactory):
    FACTORY_TUNABLES = {'opacity': TunableRange(description='\n            The target opacity for the children.\n            ', tunable_type=float, default=0, minimum=0, maximum=1), '_parent_object': TunableEnumEntry(description='\n            The participant of an interaction whose children should be hidden.\n            ', tunable_type=ParticipantType, default=ParticipantType.Object), 'fade_duration': OptionalTunable(TunableRealSecond(description='\n                The number of seconds it should take for objects to fade out and\n                in.\n                ', default=0.25), disabled_name='use_default_fade_duration', enabled_name='use_custom_fade_duration'), 'fade_objects_on_ground': Tunable(description='\n            If checked, objects at height zero will fade. By default, objects \n            at ground level (like stools slotted into counters) will not fade.\n            ', tunable_type=bool, default=False)}

    def __init__(self, interaction, *, opacity, _parent_object, fade_duration, fade_objects_on_ground, sequence=()):
        super().__init__()
        self.interaction = interaction
        self.opacity = opacity
        self.parent_object = interaction.get_participant(_parent_object)
        if fade_duration is None:
            self.fade_duration = ClientObjectMixin.FADE_DURATION
        else:
            self.fade_duration = fade_duration
        self.fade_objects_on_ground = fade_objects_on_ground
        self.sequence = sequence
        self.hidden_objects = weakref.WeakKeyDictionary()

    def _run(self, timeline):

        def begin(_):
            for obj in self.parent_object.children_recursive_gen():
                if self.fade_objects_on_ground or obj.position.y == self.parent_object.position.y:
                    pass
                else:
                    opacity = obj.opacity
                    self.hidden_objects[obj] = opacity
                    obj.fade_opacity(self.opacity, self.fade_duration)

        def end(_):
            for (obj, opacity) in self.hidden_objects.items():
                obj.fade_opacity(opacity, self.fade_duration)

        return timeline.run_child(build_critical_section_with_finally(begin, self.sequence, end))

class SetVisibilityStateElement(XevtTriggeredElement):
    FACTORY_TUNABLES = {'subject': TunableEnumEntry(description='\n            The participant of this interaction that will change the visibility.\n            ', tunable_type=ParticipantType, default=ParticipantType.Actor), 'visibility': Tunable(description='\n            If checked, the subject will become visible. If unchecked, the\n            subject will become invisible.\n            ', tunable_type=bool, default=True), 'fade': Tunable(description='\n            If checked, the subject will fade in or fade out to match the\n            desired visibility.\n            ', tunable_type=bool, default=False)}

    def _do_behavior(self, *args, **kwargs):
        subject = self.interaction.get_participant(self.subject)
        if subject is not None:
            if self.fade:
                if self.visibility:
                    subject.fade_in()
                else:
                    subject.fade_out()
            else:
                subject.visibility = VisibilityState(self.visibility)

class UpdatePhysique(XevtTriggeredElement, HasTunableFactory, AutoFactoryInit):
    FACTORY_TUNABLES = {'description': "\n            Basic extra to trigger a visual update of the specified Sims'\n            physiques.\n            ", 'targets': TunableEnumEntry(description='\n            The targets of this physique update.\n            ', tunable_type=ParticipantType, default=ParticipantType.Actor)}

    def _do_behavior(self):
        targets = self.interaction.get_participants(self.targets)
        for target in targets:
            target.sim_info.update_fitness_state()

class UpdateDisplayNumber(XevtTriggeredElement, HasTunableFactory, AutoFactoryInit):
    FACTORY_TUNABLES = {'targets': TunableEnumEntry(description='\n            The targets of this game score update\n            ', tunable_type=ParticipantType, default=ParticipantType.Object)}

    def _do_behavior(self):
        targets = self.interaction.get_participants(self.targets)
        for target in targets:
            target.update_display_number()

class ReplaceObject(XevtTriggeredElement, HasTunableFactory, AutoFactoryInit):
    FACTORY_TUNABLES = {'participant': TunableEnumEntry(description='\n            The participant that is the object that is to be replaced\n            Note: Please do not try to use this on Sims.\n            ', tunable_type=ParticipantTypeSingle, default=ParticipantType.Object), 'tags': TunableSet(description='\n            A set of tags that an object must have in order to be considered a\n            valid replacement.\n            ', tunable=TunableEnumEntry(tunable_type=Tag, default=Tag.INVALID)), 'exclude_tags': TunableSet(description='\n            A set of tags that an object must NOT have in order to be\n            considered a valid replacement.\n            ', tunable=TunableEnumEntry(tunable_type=Tag, default=Tag.INVALID)), 'margin_of_error': Tunable(description='\n            The margin of error in bounding box size when considering a\n            replacement object. The larger the value, the more variety you will\n            see in potential replacement objects, both in larger and smaller\n            objects compared to the original.\n            ', tunable_type=int, default=50), 'number_replacement_attempts': Tunable(description='\n            This is the number of tries to find a replacement object that will\n            be attempted before giving up. The server team recommends this be set\n            to 0, to signify finding all available objects to pick from randomly.\n            However, in the interest of safety, I am making this tunable so that\n            we can easily change this for certain object types where this may \n            cause an issue. Please talk to a GPE if you think you need to change this.\n            ', tunable_type=int, default=0)}

    def _replace_object(self, resolver):
        original_obj = resolver.get_participant(self.participant)
        if original_obj is None or original_obj.is_sim:
            return
        new_obj_def = build_buy.get_replacement_object(services.current_zone_id(), original_obj.id, self.number_replacement_attempts, self.margin_of_error, tags=self.tags, exclude_tags=self.exclude_tags)
        if new_obj_def is not None:
            new_obj = objects.system.create_object(new_obj_def)
            if new_obj is not None:
                household_owner_id = original_obj.household_owner_id
                parent_slot = original_obj.parent_slot
                new_obj.move_to(routing_surface=original_obj.routing_surface, translation=original_obj.position, orientation=original_obj.orientation)
                new_obj.set_household_owner_id(household_owner_id)
                if parent_slot is not None:
                    original_obj.set_parent(None)
                    parent_slot.add_child(new_obj)
                delete_liability = DeleteObjectLiability([original_obj])
                self.interaction.add_liability(DELETE_OBJECT_LIABILITY, delete_liability)
            else:
                logger.warn('Sim Ray could not create an object from the returned definition: {}.', new_obj_def, owner='jwilkinson')
        else:
            logger.warn('Sim Ray server call did not return a replacement object definition. Try adjusting the tuning to use a larger margin of error.', owner='jwilkinson')

    def _do_behavior(self):
        self._replace_object(self.interaction.get_resolver())

class PutNearElement(XevtTriggeredElement):
    FACTORY_TUNABLES = {'subject': TunableEnumEntry(description='\n            The participant that will get moved.\n            ', tunable_type=ParticipantType, default=ParticipantType.Actor), 'target': TunableEnumEntry(description='\n            The participant that the subject will get moved near.\n            ', tunable_type=ParticipantType, default=ParticipantType.Object), 'fallback_to_spawn_point': Tunable(description='\n            If enabled, a spawn point will be used as a fallback. If disabled,\n            the Subject will stay wherever they are.\n            ', tunable_type=bool, default=True)}

    def _do_behavior(self, *args, **kwargs):
        subject = self.interaction.get_participant(self.subject)
        target = self.interaction.get_participant(self.target)
        if subject is None or target is None:
            logger.error('Trying to run a PutNear basic extra with a None Subject and/or Target. subject:{}, target:{}', subject, target, owner='trevor')
            return
        starting_location = placement.create_starting_location(location=target.location)
        if subject.is_sim:
            fgl_context = placement.create_fgl_context_for_sim(starting_location, subject)
        else:
            fgl_context = placement.create_fgl_context_for_object(starting_location, subject)
        (translation, orientation) = placement.find_good_location(fgl_context)
        surface = target.routing_surface
        if self.fallback_to_spawn_point:
            zone = services.current_zone()
            fallback_point = zone.get_spawn_point(lot_id=zone.lot.lot_id)
            (translation, orientation) = fallback_point.next_spawn_spot()
            surface = fallback_point.routing_surface
        if translation is None and translation is not None:
            subject.move_to(translation=translation, orientation=orientation or subject.orientation, routing_surface=surface, parent=None, joint_name_or_hash=None, slot_hash=0)

class AddToHouseholdElement(XevtTriggeredElement):
    FACTORY_TUNABLES = {'target': TunableEnumEntry(description='\n            Who to add to the active household.\n            ', tunable_type=ParticipantTypeSingleSim, default=ParticipantTypeSingleSim.TargetSim), 'rename_dialog': OptionalTunable(description='\n            If enabled, the dialog that is displayed (and asks for the player \n            to enter a first name and last name) before assigning the Sim to \n            their household.\n            ', tunable=SimPersonalityAssignmentDialog.TunableFactory(text_inputs=(TEXT_INPUT_FIRST_NAME, TEXT_INPUT_LAST_NAME), locked_args={'phone_ring_type': PhoneRingType.NO_RING}))}

    @staticmethod
    def run_behavior(sim_info):
        household_manager = services.household_manager()
        return household_manager.switch_sim_household(sim_info)

    def _do_behavior(self, *args, **kwargs):
        target = self.interaction.get_participant(self.target)
        if target is None:
            logger.error('Trying to run AddToHousehold basic extra with a None target.')
            return False
        return self.run_behavior(target.sim_info)

    def _build_outer_elements(self, sequence):
        if self.rename_dialog is None:
            return sequence
        target = self.interaction.get_participant(self.target)
        if target is None:
            return sequence
        rename_dialog = self.rename_dialog(target, resolver=self.interaction.get_resolver())
        rename_element = RenameDialogElement(rename_dialog, target.sim_info)
        return build_element((rename_element, sequence))

class SaveParticipantElement(XevtTriggeredElement):
    FACTORY_TUNABLES = {'participant': TunableEnumEntry(description='\n            The participant that will be saved as the saved_participant specified.\n            ', tunable_type=ParticipantType, default=ParticipantType.Actor), 'saved_participant': TunableEnumEntry(description='\n            The saved participant slot that participant will be saved as.\n            ', tunable_type=ParticipantTypeSavedActor, default=ParticipantTypeSavedActor.SavedActor1)}

    def _do_behavior(self, *args, **kwargs):
        participant = self.interaction.get_participant(self.participant)
        if participant is None:
            logger.error('Trying to save a participant in SaveParticipantElement that cannot be resolved by get_participant.\n  Interaction: {}\n  Participant:{}', self.interaction, self.participant)
        for (index, flag) in enumerate(list(ParticipantTypeSavedActor)):
            if self.saved_participant == flag:
                break
        self.interaction.set_saved_participant(index, participant)
