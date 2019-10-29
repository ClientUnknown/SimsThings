from _math import Vector3, Quaternion, Transformfrom _resourceman import Keyimport collectionsfrom native.animation.arb import NativeArb, BoundaryConditionInfoimport api_configimport sims4logger = sims4.log.Logger('Animation(Native)')try:
    from _animation import AsmBase
    from _animation import _ASM_ACTORTYPE_INVALID as ASM_ACTORTYPE_INVALID
    from _animation import _ASM_ACTORTYPE_OBJECT as ASM_ACTORTYPE_OBJECT
    from _animation import _ASM_ACTORTYPE_SIM as ASM_ACTORTYPE_SIM
    from _animation import _ASM_ACTORTYPE_PROP as ASM_ACTORTYPE_PROP
    from _animation import _ASM_REQUESTRESULT_SUCCESS as ASM_REQUESTRESULT_SUCCESS
    from _animation import _ASM_REQUESTRESULT_TARGET_STATE_NOT_FOUND as ASM_REQUESTRESULT_TARGET_STATE_NOT_FOUND
    from _animation import _ASM_REQUESTRESULT_TARGET_JUMPED_TO_TARGET_STATE as ASM_REQUESTRESULT_TARGET_JUMPED_TO_TARGET_STATE
except:
    ASM_REQUESTRESULT_SUCCESS = 0
    ASM_REQUESTRESULT_TARGET_STATE_NOT_FOUND = 1
    ASM_REQUESTRESULT_TARGET_JUMPED_TO_TARGET_STATE = 2

    class AsmBase:

        def __init__(self, key):
            pass

        def _request(self, to_state, arb, request_id=0, interrupt=False):
            return ASM_REQUESTRESULT_TARGET_STATE_NOT_FOUND

        def _traverse(self, from_state, to_state, arb, request_id=0, from_boundary_conditions=False):
            return False

        def _set_actor(self, actor_name, actor_id, suffix):
            return False

        def _clear_actor(self, actor_name):
            return False

        def _add_virtual_actor(self, actor_name, actor_id, suffix):
            return False

        def _remove_virtual_actor(self, actor_name, actor_id, suffix):
            return False

        def _set_parameter(self, parameter_name, value):
            return False

        def _set_actor_parameter(self, actor_name, actor_id, parameter_name, value):
            return False

        def _set_single_actor_parameter_if_possible(self, actor_name, parameter_name, value):
            return False

        def _add_actor_instance_namespace_override(self, actor_name, actor_id, actor_suffix, namespace, target_id, target_suffix):
            return False

        def _enter(self):
            return False

        def _exit(self, arb, request_id=0):
            return ASM_REQUESTRESULT_TARGET_STATE_NOT_FOUND

        def _schedule_exit_content(self, arb):
            pass

        def _set_current_state(self, state_name):
            return False

        def _get_supported_postures_for_actor(self, actor_name):
            return False

        def _get_resource_key_for_actor(self, actor_name):
            return False

        def _get_props_in_traversal(self, from_state, to_state):
            return False

        def _get_actor_definition(self, actor_name):
            pass

class NativeAsm(AsmBase):
    _BASE_ROOT_STRING = 'b__subroot__'

    class ActorDescription(collections.namedtuple('_ActorDescription', ('actor_name', 'actor_name_hash', 'actor_type', 'is_master', 'is_virtual', 'prop_resource_key'))):
        slots = []

    def set_actor(self, name, actor, rig_key=None, suffix=None):
        if actor is not None:
            return self._set_actor(name, actor.id, suffix)
        else:
            return self._clear_actor(name)

    def set_reaction_actor(self, name):
        return self._set_reaction_actor(name)

    def add_virtual_actor(self, name, actor, suffix=None):
        return self._add_virtual_actor(name, actor.id, suffix)

    def remove_virtual_actor(self, name, actor, suffix=None):
        return self._remove_virtual_actor(name, actor.id, suffix)

    def get_actor_name(self):
        return '<unknown>'

    def set_parameter(self, parameter, value):
        return self._set_parameter(parameter, value)

    def set_actor_parameter(self, actor, instance, parameter, value, suffix=None):
        return self._set_actor_parameter(actor, instance.id, parameter, value, suffix)

    def specialize_virtual_actor_relationship(self, actor_name, actor, actor_suffix, namespace, target, target_suffix):
        return self._add_actor_instance_namespace_override(actor_name, actor.id, actor_suffix, namespace, target.id, target_suffix)

    def request(self, state_name, arb_instance, request_id=0, interrupt=False):
        return self._request(state_name, arb_instance, request_id, interrupt)

    def traverse(self, from_state_name, to_state_name, arb_instance, request_id=0, from_boundary_conditions=False):
        return self._traverse(from_state_name, to_state_name, arb_instance, request_id, from_boundary_conditions)

    def set_current_state(self, state_name):
        self._set_current_state(state_name)

    def get_supported_postures_for_actor(self, actor_name):
        postures_actor = self._get_supported_postures_for_actor(actor_name)
        postures_default = self._get_supported_postures_for_actor(None)
        if postures_default is not None:
            if postures_actor is not None:
                combined_postures = set(postures_actor)
                combined_postures.update(postures_default)
                return combined_postures
            else:
                return postures_default
        return postures_actor

    def get_resource_key_for_actor(self, actor_name):
        return self._get_resource_key_for_actor(actor_name)

    def get_props_in_traversal(self, from_state, to_state):
        return self._get_props_in_traversal(from_state, to_state)

    def get_actor_definition(self, actor_name):
        description_args = self._get_actor_definition(actor_name)
        if not description_args:
            return
        return self.ActorDescription(*description_args)

    def enter(self):
        self._enter()

    def exit(self, arb_instance, request_id=0):
        return self._exit(arb_instance, request_id)

    def schedule_exit_content(self, arb_instance):
        return self._schedule_exit_content(arb_instance)

    def set_param_sequence(self, param_dict):
        if param_dict is not None:
            for (key, value) in param_dict.items():
                if isinstance(key, tuple):
                    param = key[0]
                    actor = key[1]
                    if actor is not None:
                        self._set_single_actor_parameter_if_possible(actor, param, value)
                    else:
                        self.set_parameter(param, value)
                        self.set_parameter(key, value)
                else:
                    self.set_parameter(key, value)

    def get_initial_offset(self, actor, to_state_name, from_state_name='entry'):
        arb = NativeArb()
        self.traverse(from_state_name, to_state_name, arb, from_boundary_conditions=True)
        offset = arb.get_initial_offset(actor)
        return Transform(Vector3(*offset[0]), Quaternion(*offset[1]))

    def get_boundary_conditions(self, actor, to_state_name, from_state_name='entry'):
        arb = NativeArb()
        self.traverse(from_state_name, to_state_name, arb, from_boundary_conditions=True)
        return arb.get_boundary_conditions(actor)
Asm = NativeAsm
def get_joint_transform_from_rig(rig_key, joint_name):
    import _animation
    try:
        transform = _animation.get_joint_transform_from_rig(rig_key, joint_name)
    except Exception as exe:
        logger.error('Failed to get transform from rig: {}, {}'.format(rig_key, joint_name))
        raise exe
    return transform

def get_joint_name_for_hash_from_rig(rig_key, joint_name_hash):
    import _animation
    return _animation.get_joint_name_for_hash_from_rig(rig_key, joint_name_hash)

def get_joint_name_for_index_from_rig(rig_key, joint_index):
    import _animation
    return _animation.get_joint_name_for_index_from_rig(rig_key, joint_index)

def get_mirrored_joint_name_hash(rig_key, joint_name):
    import _animation
    return _animation.get_mirrored_joint_name_hash(rig_key, joint_name)

def update_post_condition_arb(post_condition, content):
    import _animation
    return _animation.update_post_condition_arb(post_condition, content)

def enable_native_reaction_event_handling(enabled):
    import _animation
    return _animation.enable_native_reaction_event_handling(enabled)
