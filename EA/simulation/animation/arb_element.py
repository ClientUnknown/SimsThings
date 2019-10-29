import _mathfrom protocolbuffers import DistributorOps_pb2 as protocolsfrom animation import get_animation_object_by_id, get_event_handler_error_for_missing_object, get_animation_object_for_eventfrom animation.animation_sleep_element import AnimationSleepElementfrom animation.animation_utils import clip_event_type_namefrom distributor.ops import GenericProtocolBufferOpfrom distributor.rollback import ProtocolBufferRollbackfrom distributor.system import Distributorfrom native.animation import get_mirrored_joint_name_hash, get_joint_transform_from_rigfrom sims4.callback_utils import CallableList, consume_exceptionsfrom sims4.math import invert_quaternionfrom sims4.repr_utils import standard_reprimport animationimport distributor.opsimport element_utilsimport elementsimport gsi_handlersimport servicesimport sims4.logwith sims4.reload.protected(globals()):
    _nested_arb_depth = 0
    _nested_arb_detach_callbacks = Nonelogger = sims4.log.Logger('ArbElement')dump_logger = sims4.log.LoggerClass('ArbElement')
class ArbElement(distributor.ops.ElementDistributionOpMixin, elements.SubclassableGeneratorElement):
    _BASE_SUBROOT_STRING = 'b__subroot__'
    _BASE_ROOT_STRING = 'b__root__'

    def __init__(self, arb, *args, event_records=None, master=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.arb = arb
        self.enable_optional_sleep_time = True
        self._attached_actors = []
        self._client_location_captures = set()
        self._default_handlers_registered = False
        self.event_records = event_records
        self._duration_total = None
        self._duration_must_run = None
        self._duration_interrupt = None
        self._duration_repeat = None
        self._objects_to_reset = []
        self.master = master
        self._add_block_tags_for_event_records(event_records)
        for blocker in self.arb.additional_blockers:
            self.add_additional_channel(blocker.manager.id, blocker.id)

    def __repr__(self):
        if self.event_records is not None:
            event_tags = [event_record.tag for event_record in self.event_records]
            return standard_repr(self, tags=event_tags)
        return standard_repr(self)

    def cleanup(self):
        self.arb._handlers = None

    def _teardown(self):
        self.arb = None
        super()._teardown()

    def _actors(self, main_timeline_only=False):
        actors = []
        if self.arb.is_valid():
            om = services.object_manager()
            if om:
                try:
                    actors_iter = self.arb._actors(main_timeline_only)
                except:
                    actors_iter = self.arb._actors()
                for actor_id in actors_iter:
                    actor = om.get(actor_id)
                    if actor is not None:
                        actors.append(actor)
        return actors

    def _get_asms_from_arb_request_info(self):
        return ()

    def _log_event_records(self, log_fn, only_errors):
        log_records = []
        errors_found = False
        for record in self.event_records:
            if record.errors:
                errors_found = True
                for error in record.errors:
                    log_records.append((True, record, error))
            else:
                log_records.append((False, record, None))
        if errors_found:
            log_fn('Errors occurred while handling clip events:')
        if errors_found or not only_errors:
            for (is_error, record, message) in log_records:
                if only_errors and not is_error:
                    pass
                else:
                    event_type = clip_event_type_name(record.event_type)
                    if message:
                        message = ': ' + str(message)
                    log_fn('  {}: {}#{:03}{}'.format(record.clip_name, event_type, record.event_id, message))
            self.arb.log_request_history(log_fn)

    def _add_block_tags_for_event_records(self, event_records):
        if event_records:
            for event in event_records:
                self.block_tag(event.tag)

    def attach(self, *actors, actor_instances=()):
        new_attachments = [a for a in actors if a not in self._attached_actors]
        if new_attachments:
            super().attach(*new_attachments)
            mask = 0
            actor_instances = actor_instances or self.arb._actor_instances()
            for (_, suffix) in actor_instances:
                if suffix is not None:
                    mask |= 1 << int(suffix)
            if not mask:
                mask = 4294967295
            for attachment in new_attachments:
                self.add_additional_channel(attachment.manager.id, attachment.id, mask=mask)
        self._attached_actors.extend(new_attachments)

    def detach(self, *detaching_objects):
        global _nested_arb_detach_callbacks
        if self.master not in detaching_objects:
            for detaching_object in detaching_objects:
                self._attached_actors.remove(detaching_object)
            super().detach(*detaching_objects)
            return
        if _nested_arb_depth > 0:
            if _nested_arb_detach_callbacks is None:
                _nested_arb_detach_callbacks = CallableList()
            super_self = super()
            _nested_arb_detach_callbacks.append(lambda : super_self.detach(*self._attached_actors))
            return True
        if _nested_arb_detach_callbacks is not None:
            cl = _nested_arb_detach_callbacks
            _nested_arb_detach_callbacks = None
            cl()
        super().detach(*self._attached_actors)

    def add_object_to_reset(self, obj):
        self._objects_to_reset.append(obj)

    def execute_and_merge_arb(self, arb, safe_mode):
        if self.event_records is None:
            raise RuntimeError("Attempt to merge an Arb into an ArbElement that hasn't had handle_events() called: {} into {}.".format(arb, self))
        arb_element = ArbElement(arb)
        (event_records, _) = arb_element.handle_events()
        self.event_records.extend(event_records)
        self._additional_channels.update(arb_element._additional_channels)
        self._add_block_tags_for_event_records(event_records)
        self.arb.append(arb, safe_mode)
        arb_element.cleanup()

    def handle_events(self):
        global _nested_arb_depth
        if not self._default_handlers_registered:
            self._register_default_handlers()
            self._default_handlers_registered = True
        sleep = _nested_arb_depth == 0
        _nested_arb_depth += 1
        event_context = consume_exceptions('Animation', 'Exception raised while handling clip events:')
        event_records = self.arb.handle_events(event_context=event_context)
        _nested_arb_depth -= 1
        return (event_records, sleep)

    def distribute(self):
        gen = self._run_gen()
        try:
            next(gen)
            logger.error('ArbElement.distribute attempted to yield.')
        except StopIteration as exc:
            return exc.value

    def _run_gen(self, timeline=None):
        if not self.arb.is_valid():
            return False
        actors = self._actors()
        if actors or not self._objects_to_reset:
            return True
        animation_sleep_element = None
        with distributor.system.Distributor.instance().dependent_block():
            self.attach(*actors)
            if self.event_records is None:
                (self.event_records, sleep) = self.handle_events()
            else:
                sleep = True
            self._log_event_records(dump_logger.error, True)
            for actor in actors:
                actor.update_reference_arb(self.arb)
            if timeline is not None:
                (self._duration_total, self._duration_must_run, self._duration_repeat) = self.arb.get_timing()
                self._duration_interrupt = self._duration_total - self._duration_must_run
                if self._duration_must_run or self._duration_repeat:
                    animation_sleep_element = AnimationSleepElement(self._duration_must_run, self._duration_interrupt, self._duration_repeat, enable_optional_sleep_time=self.enable_optional_sleep_time, arbs=(self.arb,))
            if sleep and gsi_handlers.animation_archive_handlers.archiver.enabled:
                gsi_handlers.animation_archive_handlers.archive_animation_request(self.arb)
        if animation_sleep_element is not None and not services.current_zone().animate_instantly:
            yield from element_utils.run_child(timeline, animation_sleep_element)
        self.detach(*self._attached_actors)
        return True

    def write(self, msg):
        from protocolbuffers import Animation_pb2 as animation_protocols
        msg.type = protocols.Operation.ARB
        if self.event_records is None:
            logger.error('ArbElement is being distributed before it has completed the non-blocking portion of _run().')
            return
        if self.arb.empty and not self._objects_to_reset:
            logger.warn('An empty Arb is being distributed')
            return
        arb_pb = animation_protocols.AnimationRequestBlock()
        arb_pb.arb_data = self.arb._bytes()
        for event in self.event_records:
            netRecord = arb_pb.event_handlers.add()
            netRecord.event_type = event.event_type
            netRecord.event_id = event.event_id
            netRecord.tag = event.tag
        for object_to_reset in self._objects_to_reset:
            with ProtocolBufferRollback(arb_pb.objects_to_reset) as moid_to_reset_msg:
                moid_to_reset_msg.manager_id = object_to_reset.manager.id
                moid_to_reset_msg.object_id = object_to_reset.id
        arb_pb.is_interruptible = self.arb._is_interruptible()
        arb_pb.should_analyze = self.arb._should_analyze()
        self.serialize_op(msg, arb_pb, protocols.Operation.ARB)
        from animation.animation_constants import _log_arb_contents

    def _register_default_handlers(self):
        self.arb.register_event_handler(self._event_handler_snap, animation.ClipEventType.Snap)
        self.arb.register_event_handler(self._event_handler_parent, animation.ClipEventType.Parent)
        self.arb.register_event_handler(self._event_handler_visibility, animation.ClipEventType.Visibility)
        self.arb.register_event_handler(self._event_handler_update_flipbook, animation.ClipEventType.AdvanceFlipBook)
        self.arb.register_event_handler(self._event_handler_client_location_capture, animation.ClipEventType.ClientLocationCapture)
        self.arb.register_event_handler(self._event_handler_client_location_restore, animation.ClipEventType.ClientLocationRestore)

    def _event_handler_client_location_capture(self, event_data):
        asms = list(self._get_asms_from_arb_request_info())
        (early_out, obj) = get_animation_object_for_event(event_data, 'target_actor_id', 'Client-only location target', asms=asms)
        if early_out is not None:
            return
        self._client_location_captures.add(obj)

    def _event_handler_client_location_restore(self, event_data):
        asms = list(self._get_asms_from_arb_request_info())
        (early_out, obj) = get_animation_object_for_event(event_data, 'target_actor_id', 'Client-only location target', asms=asms)
        if early_out is not None:
            return
        obj.resend_location()
        self._client_location_captures.discard(obj)

    def _event_handler_snap(self, event_data):
        asms = list(self._get_asms_from_arb_request_info())
        (early_out, object_to_snap) = get_animation_object_for_event(event_data, 'event_actor_id', 'object to be snapped', asms=asms)
        if early_out is not None:
            return
        snap_actor_namespace = event_data.event_data.get('snap_actor_namespace', None)
        if snap_actor_namespace is None:
            v = event_data.event_data['snap_translation']
            q = event_data.event_data['snap_orientation']
            snap_transform = _math.Transform(v, q)
        else:
            (early_out, snap_reference_object) = get_animation_object_for_event(event_data, 'snap_actor_id', 'snap reference object', asms=asms)
            if early_out is not None:
                return
            v = event_data.event_data['snap_translation']
            q = event_data.event_data['snap_orientation']
            suffix = event_data.event_data['snap_actor_suffix']
            base_transform = snap_reference_object.transform
            if suffix is not None:
                base_joint = self._BASE_SUBROOT_STRING + suffix
                offset = get_joint_transform_from_rig(snap_reference_object.rig, base_joint)
                base_transform = _math.Transform.concatenate(offset, base_transform)
            snap_transform = _math.Transform(v, q)
            snap_transform = _math.Transform.concatenate(snap_transform, base_transform)
        if object_to_snap in self._client_location_captures:
            new_location = object_to_snap.location.clone(transform=snap_transform)
            object_to_snap.resend_location(value=new_location)
        else:
            object_to_snap.transform = snap_transform
            if object_to_snap.is_sim:
                object_to_snap.update_intended_position_on_active_lot()

    def _event_handler_parent(self, event_data):
        asms = self._get_asms_from_arb_request_info()
        (early_out, child_object) = get_animation_object_for_event(event_data, 'parent_child_id', 'child', asms=asms)
        if early_out is not None:
            return
        parent_id = event_data.event_data['parent_parent_id']
        if parent_id is None:
            parent_object = child_object.get_parenting_root()
            child_object.clear_parent(child_object.transform, parent_object.routing_surface)
            return
        parent_object = get_animation_object_by_id(int(parent_id))
        if parent_object is None:
            return get_event_handler_error_for_missing_object('parent', parent_id)
        joint_name_hash = int(event_data.event_data['parent_joint_name_hash'])
        translation = event_data.event_data['parent_translation']
        orientation = event_data.event_data['parent_orientation']
        if orientation is None:
            joint_transform = get_joint_transform_from_rig(parent_object.rig, joint_name_hash)
            joint_orientation = _math.Quaternion.concatenate(parent_object.orientation, joint_transform.orientation)
            joint_orientation = invert_quaternion(joint_orientation)
            orientation = _math.Quaternion.concatenate(joint_orientation, child_object.orientation)
        transform = _math.Transform(translation, orientation)
        self.add_additional_channel(child_object.manager.id, child_object.id)
        try:
            if event_data.event_data['clip_is_mirrored']:
                joint_name_hash = get_mirrored_joint_name_hash(parent_object.rig, joint_name_hash)
            joint_name_or_hash = None
            slot_hash = 0
            joint_name_or_hash = joint_name_hash
            if child_object in self._client_location_captures:
                location = child_object.create_parent_location(parent_object, transform, joint_name_or_hash=joint_name_or_hash, slot_hash=slot_hash)
                child_object.resend_location(value=location)
            else:
                child_object.set_parent(parent_object, transform, joint_name_or_hash=joint_name_or_hash, slot_hash=slot_hash)
        except KeyError:
            logger.exception("\n                ANIMATION: A clip is trying to fire a parent event with bad\n                data. Either the animation actors are mistuned, or a slot\n                that doesn't exist on the rig has been specified in Maya.\n                \n                ASMs: {}\n                \n                 Clip: {}{} (Parent Event ID: {}),\n                 Parenting {} to {},\n                 Slot {} on {},\n                 Offset: {}\n                ", ', '.join(set(asm.name for asm in asms)), event_data.event_data.get('clip_name', 'unknown clip'), ' (mirrored)' if event_data.event_data['clip_is_mirrored'] else '', event_data.event_id, str(child_object), str(parent_object), hex(joint_name_hash), parent_object.rig, str(transform))

    def _event_handler_visibility(self, event_data):
        from objects import VisibilityState
        asms = self._get_asms_from_arb_request_info()
        (early_out, target_object) = get_animation_object_for_event(event_data, 'target_actor_id', 'target', asms=asms, allow_obj=False)
        if early_out is not None:
            (early_out, target_object) = get_animation_object_for_event(event_data, 'target_actor_id', 'target', asms=asms, allow_prop=False)
            if early_out is not None:
                return
        visible = event_data.event_data['visibility_state']
        if visible is not None:
            curr_visibility = target_object.visibility or VisibilityState(True, False, False)
            target_object.visibility = VisibilityState(visible, curr_visibility.inherits, curr_visibility.enable_drop_shadow)

    def _event_handler_update_flipbook(self, event_data):
        asms = list(self._get_asms_from_arb_request_info())
        (early_out, target) = get_animation_object_for_event(event_data, 'event_actor_id', 'object to be snapped', asms=asms)
        if early_out is not None:
            return
        op = GenericProtocolBufferOp(protocols.Operation.UPDATE_FLIPBOOK, protocols.UpdateFlipBook())
        Distributor.instance().add_op(target, op)

    def _debug_test_handlers(self):

        def _event_handler_all(event_data):
            print('Calling _event_handler_all:')
            print(event_data.event_type, event_data.event_id, event_data.event_data)

        self.arb.register_event_handler(_event_handler_all)
        print('--------Testing event handlers--------')
        eventRecords = self.arb.handle_events()
        print('--------------------------------------')
        return eventRecords

def distribute_arb_element(arb, event_records=None, master=None, **kwargs):
    element = ArbElement(arb, event_records=event_records, master=master, **kwargs)
    element.distribute()
    element.cleanup()
