from _sims4_collections import frozendictimport itertoolsimport weakreffrom animation import AnimationContextfrom animation.animation_constants import AUTO_EXIT_REF_TAGfrom element_utils import build_critical_section, build_critical_section_with_finally, build_element, must_runfrom routing import PathPlanContextfrom sims.sim_info_types import Species, SpeciesExtendedfrom sims4.callback_utils import protected_callbackfrom sims4.utils import setdefault_callablefrom singletons import UNSETimport animationimport animation.arbimport gsi_handlers.interaction_archive_handlersimport native.animationimport routingimport servicesimport sims4.logimport sims4.resources_unhash_bone_name_cache = {}logger = sims4.log.Logger('Animation')dump_logger = sims4.log.LoggerClass('Animation')
class AsmAutoExitInfo:

    def __init__(self):
        self.clear()

    def clear(self):
        if hasattr(self, 'asm') and self.asm is not None:
            animation_context = self.asm[2]
            animation_context.release_ref(AUTO_EXIT_REF_TAG)
        self.asm = None
        self.apply_carry_interaction_mask = 0
        self.locked = False

class _FakePostureState:

    def __init__(self, *_, **__):
        self._body = None

    def get_carry_state(self, *_, **__):
        return (False, False)

    def get_carry_track(self, *_, **__):
        pass

    def get_carry_posture(self, *_, **__):
        pass

    @property
    def surface_target(self):
        pass

    @property
    def body(self, *_, **__):
        return self._body

    @body.setter
    def body(self, value):
        self._body = value
FAKE_POSTURE_STATE = _FakePostureState()
class StubActor:
    additional_interaction_constraints = None
    age = UNSET
    is_valid_posture_graph_object = False
    party = None

    def __init__(self, guid, template=None, debug_name=None, parent=None, species=None):
        self.id = guid
        self.template = template
        if species is not None:
            self._species = species
        elif template is not None:
            self._species = template.species
        else:
            self._species = Species.HUMAN
        self.debug_name = debug_name
        self.parent = parent
        self.asm_auto_exit = AsmAutoExitInfo()
        self.routing_context = PathPlanContext()
        zone_id = services.current_zone_id()
        routing_surface = routing.SurfaceIdentifier(zone_id or 0, 0, routing.SurfaceType.SURFACETYPE_WORLD)
        self.routing_location = routing.Location(sims4.math.Vector3.ZERO(), sims4.math.Quaternion.IDENTITY(), routing_surface)

    def __repr__(self):
        return 'StubActor({})'.format(self.debug_name or self.id)

    def ref(self, callback=None):
        return weakref.ref(self, protected_callback(callback))

    def resolve(self, cls):
        return self

    def is_in_inventory(self):
        return False

    def is_in_sim_inventory(self, sim=None):
        return False

    @property
    def LineOfSight(self):
        if self.template is not None:
            return self.template.lineofsight_component

    @property
    def parts(self):
        if self.template is not None:
            return self.template.parts

    @property
    def is_part(self):
        if self.template is not None:
            return self.template.is_part
        return False

    @property
    def part_suffix(self):
        if self.template is not None:
            return self.template.part_suffix

    def is_mirrored(self, *args, **kwargs):
        if self.template is not None:
            return self.template.is_mirrored(*args, **kwargs)
        return False

    @property
    def location(self):
        zone_id = services.current_zone_id()
        routing_surface = routing.SurfaceIdentifier(zone_id or 0, 0, routing.SurfaceType.SURFACETYPE_WORLD)
        return sims4.math.Location(sims4.math.Transform(), routing_surface)

    @property
    def transform(self):
        return self.location.transform

    @property
    def position(self):
        return self.transform.translation

    @property
    def orientation(self):
        return self.transform.orientation

    @property
    def forward(self):
        return self.orientation.transform_vector(sims4.math.Vector3.Z_AXIS())

    @property
    def routing_surface(self):
        return self.location.routing_surface

    @property
    def intended_transform(self):
        return self.transform

    @property
    def intended_position(self):
        return self.position

    @property
    def intended_forward(self):
        return self.forward

    @property
    def intended_routing_surface(self):
        return self.routing_surface

    @property
    def is_sim(self):
        if self.template is not None:
            return self.template.is_sim
        return False

    @property
    def rig(self):
        if self.template is not None:
            return self.template.rig

    @property
    def species(self):
        return self._species

    @property
    def extended_species(self):
        return SpeciesExtended(self._species)

    @property
    def age(self):
        return UNSET

    def get_anim_overrides(self, target_name):
        if self.template is not None:
            return self.template.get_anim_overrides(target_name)
        return AnimationOverrides()

    def get_param_overrides(self, target_name, only_for_keys=None):
        if self.template is not None:
            return self.template.get_param_overrides(target_name, only_for_keys)

    @property
    def custom_posture_target_name(self):
        if self.template is not None:
            return self.template.custom_posture_target_name

    @property
    def route_target(self):
        import interactions.utils.routing
        return (interactions.utils.routing.RouteTargetType.OBJECT, self)

    @property
    def posture_state(self):
        if self.template is not None:
            return self.template.posture_state
        return FAKE_POSTURE_STATE

    @property
    def posture(self):
        return self.posture_state.body

    @posture.setter
    def posture(self, value):
        self.posture_state.body = value

    def get_social_group_constraint(self, si):
        import interactions.constraints
        return interactions.constraints.Anywhere()

    def filter_supported_postures(self, postures, *args, **kwargs):
        if self.template is not None:
            return self.template.filter_supported_postures(postures, *args, **kwargs)
        return postures

    @property
    def definition(self):
        if self.template is not None:
            return self.template.definition

    def set_mood_asm_parameter(self, *args, **kwargs):
        pass

    def set_trait_asm_parameters(self, *args, **kwargs):
        pass

    def get_additional_scoring_for_surface(self, surface):
        return 0

    def get_carry_transition_constraint(self, sim, position, routing_surface):
        import objects.components.carryable_component
        import interactions.constraints
        constraints = objects.components.carryable_component.CarryableComponent.DEFAULT_GEOMETRIC_TRANSITION_CONSTRAINT
        constraints = constraints.constraint_non_mobile
        final_constraint = interactions.constraints.Anywhere()
        for constraint in constraints:
            final_constraint = final_constraint.intersect(constraint.create_constraint(None, None, target_position=position, routing_surface=routing_surface))
            if not final_constraint.valid:
                return final_constraint
        return final_constraint

    def get_routing_context(self):
        return self.routing_context

class AnimationOverrides:
    __slots__ = ('animation_context', 'sounds', 'props', 'balloons', 'vfx', 'manifests', 'prop_state_values', 'reactionlet', 'balloon_target_override', 'required_slots', 'params', 'alternative_props')

    def __init__(self, overrides=None, params=frozendict(), vfx=frozendict(), sounds=frozendict(), props=frozendict(), prop_state_values=frozendict(), manifests=frozendict(), required_slots=None, balloons=None, reactionlet=None, animation_context=None, alternative_props=None):
        if overrides is None:
            self.params = frozendict(params)
            self.vfx = frozendict(vfx)
            self.sounds = frozendict(sounds)
            self.props = frozendict(props)
            self.prop_state_values = frozendict(prop_state_values)
            self.manifests = frozendict(manifests)
            self.required_slots = required_slots or ()
            self.balloons = balloons or ()
            self.reactionlet = reactionlet or None
            self.animation_context = animation_context or None
            self.balloon_target_override = None
            self.alternative_props = alternative_props or {}
        else:
            self.params = frozendict(params, overrides.params)
            self.vfx = frozendict(vfx, overrides.vfx)
            self.sounds = frozendict(sounds, overrides.sounds)
            self.props = frozendict(props, overrides.props)
            self.prop_state_values = frozendict(prop_state_values, overrides.prop_state_values)
            self.manifests = frozendict(manifests, overrides.manifests)
            self.required_slots = overrides.required_slots or (required_slots or ())
            self.balloons = overrides.balloons or (balloons or ())
            self.reactionlet = overrides.reactionlet or (reactionlet or None)
            self.animation_context = overrides.animation_context or (animation_context or None)
            self.balloon_target_override = overrides.balloon_target_override or None
            self.alternative_props = overrides.alternative_props or {}

    def __call__(self, overrides=None, **kwargs):
        if overrides or not kwargs:
            return self
        if kwargs:
            overrides = AnimationOverrides(overrides=overrides, **kwargs)
        return AnimationOverrides(overrides=overrides, params=self.params, vfx=self.vfx, sounds=self.sounds, props=self.props, prop_state_values=self.prop_state_values, manifests=self.manifests, required_slots=self.required_slots, balloons=self.balloons, reactionlet=self.reactionlet, animation_context=self.animation_context, alternative_props=self.alternative_props)

    def __repr__(self):
        items = []
        for name in ('params', 'vfx', 'sounds', 'props', 'manifests', 'required_slots', 'balloons', 'reactionlet', 'animation_context'):
            value = getattr(self, name)
            if value:
                items.append('{}={}'.format(name, value))
        return '{}({})'.format(type(self).__name__, ', '.join(items))

    def __bool__(self):
        if self.params or (self.vfx or (self.sounds or (self.props or (self.prop_state_values or (self.manifests or (self.required_slots or (self.balloons or self.reactionlet))))))) or self.animation_context:
            return True
        return False

    def __eq__(self, other):
        if self is other:
            return True
        if type(self) != type(other):
            return False
        elif self.params != other.params or (self.vfx != other.vfx or (self.sounds != other.sounds or (self.props != other.props or (self.prop_state_values != other.prop_state_values or (self.manifests != other.manifests or (self.required_slots != other.required_slots or (self.balloons != other.balloons or (self.reactionlet != other.reactionlet or (self.animation_context != other.animation_context or self.balloon_target_override != other.balloon_target_override))))))))) or self.alternative_props != other.alternative_props:
            return False
        return True

    def override_asm(self, asm, actor=None, suffix=None):
        if asm is not None:
            if self.params:
                for (param_name, param_value) in self.params.items():
                    if isinstance(param_name, tuple):
                        (param_name, actor_name) = param_name
                    else:
                        actor_name = None
                    if actor_name is not None and asm.set_actor_parameter(actor_name, actor, param_name, param_value, suffix):
                        pass
                    else:
                        asm.set_parameter(param_name, param_value)
            if self.props:
                for (prop_name, definition) in self.props.items():
                    alt_prop_def = self.alternative_props.get(prop_name, None)
                    asm.set_prop_override(prop_name, definition, alternative_def=alt_prop_def)
            if self.prop_state_values:
                for (prop_name, state_values) in self.prop_state_values.items():
                    asm.store_prop_state_values(prop_name, state_values)
            if self.vfx:
                for (vfx_actor_name, vfx_override_name) in self.vfx.items():
                    asm.set_vfx_override(vfx_actor_name, vfx_override_name)
            if self.sounds:
                for (name, key) in self.sounds.items():
                    sound_id = key.instance if key is not UNSET else None
                    asm.set_sound_override(name, sound_id)
            if self.animation_context:
                asm.context = AnimationContext()

def clip_event_type_name(event_type):
    for (name, val) in vars(animation.ClipEventType).items():
        if val == event_type:
            return name
    return 'Unknown({})'.format(event_type)

def create_run_animation(arb):
    if arb.empty:
        return

    def run_animation(_):
        arb_accumulator = services.current_zone().arb_accumulator_service
        arb_accumulator.add_arb(arb)

    return build_element(run_animation)

def flush_all_animations(timeline):
    arb_accumulator = services.current_zone().arb_accumulator_service
    yield from arb_accumulator.flush(timeline)

def flush_all_animations_instantly(timeline):
    arb_accumulator = services.current_zone().arb_accumulator_service
    yield from arb_accumulator.flush(timeline, animate_instantly=True)

def get_actors_for_arb_sequence(*arb_sequence):
    all_actors = set()
    om = services.object_manager()
    if om:
        for arb in arb_sequence:
            if isinstance(arb, list):
                arbs = arb
            else:
                arbs = (arb,)
            for sub_arb in arbs:
                for actor_id in sub_arb._actors():
                    actor = om.get(actor_id)
                    if actor is None:
                        pass
                    else:
                        all_actors.add(actor)
    return all_actors

def disable_asm_auto_exit(sim, sequence):
    was_locked = None

    def lock(_):
        nonlocal was_locked
        was_locked = sim.asm_auto_exit.locked
        sim.asm_auto_exit.locked = True

    def unlock(_):
        sim.asm_auto_exit.locked = was_locked

    return build_critical_section(lock, sequence, unlock)

def unhash_bone_name(bone_name_hash:int, try_appending_subroot=True) -> str:
    if bone_name_hash not in _unhash_bone_name_cache:
        for rig_key in sims4.resources.list(type=sims4.resources.Types.RIG):
            try:
                bone_name = native.animation.get_joint_name_for_hash_from_rig(rig_key, bone_name_hash)
            except KeyError:
                pass
            break
        bone_name = None
        if try_appending_subroot:
            bone_name_hash_with_subroot = sims4.hash_util.hash32('1', initial_hash=bone_name_hash)
            bone_name_with_subroot = unhash_bone_name(bone_name_hash_with_subroot, False)
            if bone_name_with_subroot is not None:
                bone_name = bone_name_with_subroot[:-1]
        _unhash_bone_name_cache[bone_name_hash] = bone_name
    return _unhash_bone_name_cache[bone_name_hash]

def partition_boundary_on_params(boundary_to_params):
    ks_to_vs = {}
    for params in set(itertools.chain(*boundary_to_params.values())):
        for (k, v) in params.items():
            vs = setdefault_callable(ks_to_vs, k, set)
            vs.add(v)

    def get_matching_params_excluding_key(k, v):
        results = []
        for (boundary, param_sets) in boundary_to_params.items():
            valid_params = set()
            for params in param_sets:
                vp = params.get(k, v)
                if vp == v:
                    valid_params.add(sims4.collections.frozendict({kf: vf for (kf, vf) in params.items() if kf != k}))
            results.append((boundary, valid_params))
        return results

    unique_keys = set()
    for (k, vs) in ks_to_vs.items():
        matching_params = None
        for v in vs:
            matching_params_v = get_matching_params_excluding_key(k, v)
            if matching_params is None:
                matching_params = matching_params_v
            elif matching_params != matching_params_v:
                unique_keys.add(k)
                break
    boundary_param_sets = {boundary: unique_keys for boundary in boundary_to_params}
    return boundary_param_sets

def with_event_handlers(animation_context, handler, clip_event_type, sequence=None, tag=None):
    handle = None

    def begin(_):
        nonlocal handle
        handle = animation_context.register_event_handler(handler, clip_event_type, tag=tag)

    def end(_):
        if handle is not None:
            handle.release()

    return build_critical_section(begin, sequence, end)

def get_release_contexts_fn(contexts_to_release, tag):

    def release_contexts(_):
        for context in contexts_to_release:
            context.release_ref(tag)

    return release_contexts

def release_auto_exit(actor):
    contexts_to_release = []
    for other_actor in actor.asm_auto_exit.asm[1]:
        if other_actor.is_sim and other_actor.asm_auto_exit.asm is not None:
            animation_context = other_actor.asm_auto_exit.asm[2]
            contexts_to_release.append(animation_context)
            other_actor.asm_auto_exit.asm = None
    return contexts_to_release

def get_auto_exit(actors, asm=None, interaction=None, required_actors=()):
    arb_exit = None
    contexts_to_release_all = []
    for actor in actors:
        if actor.is_sim and actor.asm_auto_exit.asm is not None:
            asm_to_exit = actor.asm_auto_exit.asm[0]
            if asm_to_exit is asm:
                pass
            elif required_actors:
                asm_actors = set(asm_to_exit.actors_gen())
                if not all(a in asm_actors for a in required_actors):
                    pass
                else:
                    if arb_exit is None:
                        arb_exit = animation.arb.Arb()
                    if gsi_handlers.interaction_archive_handlers.is_archive_enabled(interaction):
                        prev_state = asm_to_exit.current_state
                    try:
                        asm_to_exit.request('exit', arb_exit, debug_context=(interaction, asm))
                    finally:
                        if gsi_handlers.interaction_archive_handlers.is_archive_enabled(interaction):
                            gsi_handlers.interaction_archive_handlers.add_animation_data(interaction, asm_to_exit, prev_state, 'exit', 'arb_exit is empty' if arb_exit.empty else arb_exit.get_contents_as_string())
                    contexts_to_release = release_auto_exit(actor)
                    contexts_to_release_all.extend(contexts_to_release)
            else:
                if arb_exit is None:
                    arb_exit = animation.arb.Arb()
                if gsi_handlers.interaction_archive_handlers.is_archive_enabled(interaction):
                    prev_state = asm_to_exit.current_state
                try:
                    asm_to_exit.request('exit', arb_exit, debug_context=(interaction, asm))
                finally:
                    if gsi_handlers.interaction_archive_handlers.is_archive_enabled(interaction):
                        gsi_handlers.interaction_archive_handlers.add_animation_data(interaction, asm_to_exit, prev_state, 'exit', 'arb_exit is empty' if arb_exit.empty else arb_exit.get_contents_as_string())
                contexts_to_release = release_auto_exit(actor)
                contexts_to_release_all.extend(contexts_to_release)
    release_contexts_fn = get_release_contexts_fn(contexts_to_release_all, AUTO_EXIT_REF_TAG)
    if arb_exit is not None and not arb_exit.empty:
        element = build_critical_section_with_finally(build_critical_section(create_run_animation(arb_exit), flush_all_animations), release_contexts_fn)
        return must_run(element)
    elif contexts_to_release_all:
        return must_run(build_element(release_contexts_fn))

def mark_auto_exit(actors, asm):
    if asm is None:
        return
    contexts_to_release_all = []
    for actor in actors:
        if actor.is_sim and (actor.asm_auto_exit is not None and actor.asm_auto_exit.asm is not None) and actor.asm_auto_exit.asm[0] is asm:
            contexts_to_release = release_auto_exit(actor)
            contexts_to_release_all.extend(contexts_to_release)
    if not contexts_to_release_all:
        return
    return get_release_contexts_fn(contexts_to_release_all, AUTO_EXIT_REF_TAG)
