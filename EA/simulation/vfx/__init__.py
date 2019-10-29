from protocolbuffers import DistributorOps_pb2 as protocolsfrom protocolbuffers.VFX_pb2 import HARD_TRANSITION, SOFT_TRANSITION, VFXStartfrom distributor.ops import StopVFX, SetVFXStatefrom distributor.system import get_current_tag_set, Distributorfrom element_utils import build_critical_section_with_finallyfrom objects.components.state_change import StateChangefrom sims4.repr_utils import standard_angle_reprfrom sims4.tuning.tunable import TunableFactory, Tunable, HasTunableFactory, TunableList, AutoFactoryInit, OptionalTunable, TunableVariantfrom sims4.tuning.tunable_hash import TunableStringHash32from singletons import DEFAULTfrom uid import unique_idimport distributor.opsimport servicesimport sims4.loglogger = sims4.log.Logger('Animation')
@unique_id('actor_id')
class PlayEffect(distributor.ops.ElementDistributionOpMixin, HasTunableFactory, AutoFactoryInit):
    JOINT_NAME_CURRENT_POSITION = 1899928870
    FACTORY_TUNABLES = {'effect_name': Tunable(description='\n            The name of the effect to play.\n            ', tunable_type=str, default=''), 'joint_name': OptionalTunable(description='\n            Specify if the visual effect is attached to a slot and, if so, which\n            slot.\n            ', tunable=TunableStringHash32(description='\n                The name of the slot this effect is attached to.\n                ', default='_FX_'), enabled_by_default=True, enabled_name='Slot', disabled_name='Current_Position', disabled_value=JOINT_NAME_CURRENT_POSITION), 'play_immediate': Tunable(description='\n            If checked, this effect will be triggered immediately, nothing\n            will block.\n\n            ex. VFX will be played immediately while \n            the Sim is routing or animating.\n            ', tunable_type=bool, default=False)}

    def __init__(self, target, effect_name='', joint_name=0, target_actor_id=0, target_joint_name_hash=0, mirror_effect=False, auto_on_effect=False, target_joint_offset=None, play_immediate=False, callback_event_id=None, store_target_position=False, transform_override=None, **kwargs):
        super().__init__(effect_name=effect_name, joint_name=joint_name, play_immediate=play_immediate, immediate=play_immediate, **kwargs)
        self.target = target
        if target is not None:
            if target.inventoryitem_component is not None:
                forward_to_owner_list = target.inventoryitem_component.forward_client_state_change_to_inventory_owner
                if StateChange.VFX in forward_to_owner_list:
                    inventory_owner = target.inventoryitem_component.inventory_owner
                    if inventory_owner is not None:
                        self.target = inventory_owner
            if target.crafting_component is not None:
                effect_name = target.crafting_component.get_recipe_effect_overrides(effect_name)
        self.target_transform = target.transform if target is not None else transform_override
        self.effect_name = effect_name
        self.auto_on_effect = auto_on_effect
        self.target_actor_id = target_actor_id
        self.target_joint_name_hash = target_joint_name_hash
        self.mirror_effect = mirror_effect
        self._stop_type = SOFT_TRANSITION
        self.target_joint_offset = target_joint_offset
        self.immediate = play_immediate
        self.callback_event_id = callback_event_id
        self.store_target_position = store_target_position

    def __repr__(self):
        return standard_angle_repr(self, self.effect_name)

    @property
    def _is_relative_to_transform(self):
        return self.joint_name == self.JOINT_NAME_CURRENT_POSITION

    def _on_target_location_changed(self, *_, **__):
        self.stop(immediate=True)
        self.start()

    def start(self, *_, **__):
        if self.target is None:
            logger.error('Attempting to attach VFX without a target. Perhaps you mean to use start_one_shot()', owner='rmccord')
        if self._is_relative_to_transform:
            self.target.register_on_location_changed(self._on_target_location_changed)
        if not self._is_valid_target():
            return
        if not self.is_attached:
            self.attach(self.target)
            logger.info('VFX {} on {} START'.format(self.effect_name, self.target))

    def start_one_shot(self):
        if self.target is not None and not self.target.is_terrain:
            distributor.ops.record(self.target, self)
        else:
            Distributor.instance().add_op_with_no_owner(self)

    def stop(self, *_, immediate=False, **kwargs):
        if self.target is None or not self.target.valid_for_distribution:
            return
        if self._is_relative_to_transform:
            self.target.unregister_on_location_changed(self._on_target_location_changed)
        if self.is_attached:
            if immediate:
                self._stop_type = HARD_TRANSITION
            else:
                self._stop_type = SOFT_TRANSITION
            self.detach()

    def _is_valid_target(self):
        if not self.target.valid_for_distribution:
            zone = services.current_zone()
            if zone is not None:
                zone_spin_up_service = zone.zone_spin_up_service
                if zone_spin_up_service is None:
                    logger.callstack('zone_spin_up_service was None in PlayEffect._is_valid_target(), for effect/target: {}/{}', self, self.target, owner='johnwilkinson', level=sims4.log.LEVEL_ERROR)
                    return False
                elif not zone_spin_up_service.is_finished:
                    return False
        return True

    def detach(self, *objects):
        super().detach(*objects)
        if services.current_zone().is_zone_shutting_down:
            return
        op = StopVFX(self.target.id, self.actor_id, stop_type=self._stop_type, immediate=self.immediate)
        distributor.ops.record(self.target, op)
        logger.info('VFX {} on {} STOP'.format(self.effect_name, self.target))

    def write(self, msg):
        start_msg = VFXStart()
        if self.target is not None:
            start_msg.object_id = self.target.id
        start_msg.effect_name = self.effect_name
        start_msg.actor_id = self.actor_id
        start_msg.joint_name_hash = self.joint_name
        start_msg.target_actor_id = self.target_actor_id
        start_msg.target_joint_name_hash = self.target_joint_name_hash
        start_msg.mirror_effect = self.mirror_effect
        start_msg.auto_on_effect = self.auto_on_effect
        if self.target_joint_offset is not None:
            start_msg.target_joint_offset.x = self.target_joint_offset.x
            start_msg.target_joint_offset.y = self.target_joint_offset.y
            start_msg.target_joint_offset.z = self.target_joint_offset.z
        if self.callback_event_id is not None:
            start_msg.callback_event_id = self.callback_event_id
        if self._is_relative_to_transform:
            if self.store_target_position or self.target is None:
                transform = self.target_transform
            else:
                transform = self.target.transform
            start_msg.transform.translation.x = transform.translation.x
            start_msg.transform.translation.y = transform.translation.y
            start_msg.transform.translation.z = transform.translation.z
            start_msg.transform.orientation.x = transform.orientation.x
            start_msg.transform.orientation.y = transform.orientation.y
            start_msg.transform.orientation.z = transform.orientation.z
            start_msg.transform.orientation.w = transform.orientation.w
        self.serialize_op(msg, start_msg, protocols.Operation.VFX_START)

class PlayMultipleEffects(HasTunableFactory):
    FACTORY_TUNABLES = {'description': '\n            Play multiple visual effects.\n            ', 'vfx_list': TunableList(description='\n            A list of effects to play\n            ', tunable=PlayEffect.TunableFactory(description='\n                A single effect to play.\n                '))}

    def __init__(self, owner, *args, vfx_list=None, **kwargs):
        self.vfx_list = []
        for vfx_factory in vfx_list:
            self.vfx_list.append(vfx_factory(owner))

    def start_one_shot(self, *args, **kwargs):
        for play_effect in self.vfx_list:
            play_effect.start_one_shot(*args, **kwargs)

    def start(self, *args, **kwargs):
        for play_effect in self.vfx_list:
            play_effect.start(*args, **kwargs)

    def stop(self, *args, **kwargs):
        for play_effect in self.vfx_list:
            play_effect.stop(*args, **kwargs)

class TunablePlayEffectVariant(TunableVariant):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, play_effect=PlayEffect.TunableFactory(), play_multiple_effects=PlayMultipleEffects.TunableFactory(), locked_args={'no_effect': None}, default='no_effect', **kwargs)
