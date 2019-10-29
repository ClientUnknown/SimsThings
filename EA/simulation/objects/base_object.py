import weakreffrom distributor.shared_messages import EMPTY_ICON_INFO_DATA, IconInfoDatafrom element_utils import build_elementfrom interactions.interaction_finisher import FinishingTypefrom objects.components import ComponentContainer, forward_to_components, call_component_funcfrom objects.components.types import CARRYABLE_COMPONENTfrom objects.gallery_tuning import ContentSourcefrom objects.object_enums import ResetReasonfrom services.reset_and_delete_service import ResetRecordfrom sims4.callback_utils import protected_callbackfrom sims4.collections import frozendictfrom sims4.repr_utils import standard_repr, standard_brief_id_reprfrom sims4.utils import constpropertyimport build_buyimport cachesimport elementsimport objects.componentsimport objects.systemimport servicesimport sims4.logimport sims4.mathlogger = sims4.log.Logger('Objects')logger_reset = sims4.log.Logger('Reset')
class BaseObject(ComponentContainer):

    def __init__(self, definition, tuned_native_components=frozendict(), **kwargs):
        super().__init__()
        self.id = 0
        self.manager = None
        self.definition = definition
        self._visible_to_client = False
        self._interaction_refs = None
        self._parts = None
        self.content_source = ContentSource.DEFAULT
        self.wall_or_fence_placement = self._has_placement_flag(build_buy.PlacementFlags.WALL_GRAPH_PLACEMENT)
        if definition is not None:
            services.definition_manager().register_definition(definition.id, self)
            for component_id in definition.components:
                comp = objects.components.native_component_id_to_class[component_id]
                if not comp.has_server_component():
                    pass
                else:
                    factory = getattr(tuned_native_components, comp.CNAME, None) or comp.create_component
                    self.add_component(factory(self))

    def __repr__(self):
        guid = getattr(self, 'id', None)
        if guid is not None:
            return standard_repr(self, standard_brief_id_repr(guid))
        return standard_repr(self)

    def __str__(self):
        guid = getattr(self, 'id', None)
        if guid is not None:
            return '{}:{}'.format(self.__class__.__name__, standard_brief_id_repr(guid))
        return '{}'.format(self.__class__.__name__)

    @property
    def visible_to_client(self):
        return self._visible_to_client

    @visible_to_client.setter
    def visible_to_client(self, value):
        self._visible_to_client = value

    @classmethod
    def get_class_for_obj_state(cls, obj_state):
        if cls._object_state_remaps and obj_state < len(cls._object_state_remaps):
            definition = cls._object_state_remaps[obj_state]
            if definition is not None:
                return definition.cls
        return cls

    @property
    def is_downloaded(self):
        return self.content_source == ContentSource.GALLERY or self.content_source == ContentSource.LIBRARY

    @property
    def is_from_gallery(self):
        return self.content_source == ContentSource.GALLERY

    @constproperty
    def is_sim():
        return False

    @constproperty
    def is_terrain():
        return False

    @constproperty
    def is_prop():
        return False

    @property
    def valid_for_distribution(self):
        return self.visible_to_client

    @property
    def zone_id(self):
        if self.manager is None:
            logger.error('Attempting to retrieve a zone id from an object: {} that is not in a manager.', self)
            return
        return self.manager.zone_id

    @property
    def object_manager_for_create(self):
        return services.object_manager()

    @property
    def ceiling_placement(self):
        return self._has_placement_flag(build_buy.PlacementFlags.CEILING)

    @property
    def interaction_refs(self):
        if self._interaction_refs is None:
            return tuple()
        else:
            return self._interaction_refs

    def _has_placement_flag(self, placement_flag):
        placement_flags = build_buy.get_object_placement_flags(self.definition.id)
        if placement_flags & placement_flag:
            return True
        return False

    def ref(self, callback=None):
        return weakref.ref(self, protected_callback(callback))

    def resolve(self, type_or_tuple):
        if isinstance(self, type_or_tuple):
            return self

    def resolve_retarget(self, new_target):
        return new_target

    def reset_reason(self):
        return services.get_reset_and_delete_service().get_reset_reason(self)

    @property
    def can_reset(self):
        return True

    def reset(self, reset_reason, source=None, cause=None):
        services.get_reset_and_delete_service().trigger_reset(self, reset_reason, source, cause)

    def on_reset_notification(self, reset_reason):
        pass

    def on_reset_get_elements_to_hard_stop(self, reset_reason):
        return []

    def on_reset_get_interdependent_reset_records(self, reset_reason, reset_records):
        self.on_reset_component_get_interdependent_reset_records(reset_reason, reset_records)
        if self._interaction_refs is None:
            return
        for interaction in tuple(self._interaction_refs):
            sim = None
            if reset_reason != ResetReason.BEING_DESTROYED:
                sim = interaction.sim
                transition_controller = sim.queue.transition_controller if sim is not None else None
                if transition_controller is not None and transition_controller.will_derail_if_given_object_is_reset(self):
                    pass
                elif interaction.should_reset_based_on_pipeline_progress:
                    self.remove_interaction_reference(interaction)
                    sim = sim or interaction.sim
                    if sim is None:
                        pass
                    else:
                        reset_records.append(ResetRecord(sim, ResetReason.RESET_EXPECTED, self, 'Actor in interaction targeting source. {}, {}'.format(interaction, interaction.pipeline_progress)))
            elif interaction.should_reset_based_on_pipeline_progress:
                self.remove_interaction_reference(interaction)
                sim = sim or interaction.sim
                if sim is None:
                    pass
                else:
                    reset_records.append(ResetRecord(sim, ResetReason.RESET_EXPECTED, self, 'Actor in interaction targeting source. {}, {}'.format(interaction, interaction.pipeline_progress)))

    @forward_to_components
    def on_reset_component_get_interdependent_reset_records(self, reset_reason, reset_records):
        pass

    def on_reset_early_detachment(self, reset_reason):
        if self._interaction_refs is None:
            return
        orig_list = list(self._interaction_refs)
        for interaction in list(orig_list):
            if not interaction.should_reset_based_on_pipeline_progress:
                self.remove_interaction_reference(interaction)
                interaction.cancel(FinishingType.OBJECT_CHANGED, cancel_reason_msg='object destroyed', ignore_must_run=True)

    def on_reset_send_op(self, reset_reason):
        pass

    def on_reset_internal_state(self, reset_reason):
        self.component_reset(reset_reason)

    def on_reset_destroy(self, **kwargs):
        self.manager.remove(self, **kwargs)

    def on_reset_restart(self):
        self.post_component_reset()
        return True

    @forward_to_components
    def component_reset(self, reset_reason):
        pass

    @forward_to_components
    def post_component_reset(self):
        pass

    def destroy(self, source=None, cause=None, **kwargs):
        services.get_reset_and_delete_service().trigger_destroy(self, source=source, cause=cause, **kwargs)

    def schedule_destroy_asap(self, post_delete_func=None, source=None, cause=None, **kwargs):

        def call_destroy(timeline):
            if services.reset_and_delete_service.can_be_destroyed(self):
                self.destroy(source=source, cause=cause, **kwargs)

        element = elements.CallbackElement(elements.FunctionElement(call_destroy), complete_callback=post_delete_func, hard_stop_callback=post_delete_func, teardown_callback=None)
        services.time_service().sim_timeline.schedule_asap(element)

    def schedule_reset_asap(self, reset_reason=ResetReason.RESET_EXPECTED, source=None, cause=None):

        def call_reset(timeline):
            self.reset(reset_reason, source=source, cause=cause)

        element = build_element(call_reset)
        services.time_service().sim_timeline.schedule_asap(element)

    def remove_from_client(self, **kwargs):
        return objects.system.remove_object_from_client(self, **kwargs)

    @property
    def is_valid_posture_graph_object(self):
        carryable_component = self.get_component(CARRYABLE_COMPONENT)
        if carryable_component is not None and not carryable_component.is_valid_posture_graph_object:
            return False
        elif self._location.transform == sims4.math.Transform.IDENTITY() and self.parent is None:
            return False
        return True

    @property
    def add_to_posture_graph_if_parented(self):
        return False

    @property
    def icon(self):
        if self.definition is not None:
            return self.definition.icon

    def get_icon_info_data(self):
        if self.manager is not None:
            return IconInfoData(obj_instance=self)
        return EMPTY_ICON_INFO_DATA

    @property
    def icon_info(self):
        if self.manager is not None:
            return (self.definition.id, self.manager.id)
        return (None, None)

    @property
    def manager_id(self):
        if self.manager is not None:
            return self.manager.id
        return 0

    @forward_to_components
    def pre_add(self, manager, obj_id):
        pass

    @forward_to_components
    def on_add(self):
        pass

    @forward_to_components
    def on_client_connect(self, client):
        pass

    @forward_to_components
    def on_add_to_client(self):
        pass

    @forward_to_components
    def on_remove_from_client(self):
        pass

    @forward_to_components
    def on_placed_in_slot(self, slot_owner):
        pass

    @forward_to_components
    def on_removed_from_slot(self, slot_owner):
        pass

    @forward_to_components
    def on_before_added_to_inventory(self):
        pass

    @forward_to_components
    def on_added_to_inventory(self):
        pass

    @forward_to_components
    def on_before_removed_from_inventory(self):
        pass

    @forward_to_components
    def on_removed_from_inventory(self):
        pass

    @forward_to_components
    def on_object_added_to_inventory(self, obj):
        pass

    @forward_to_components
    def on_object_removed_from_inventory(self, obj):
        pass

    @forward_to_components
    def on_object_stack_id_updated(self, obj, old_obj_id, old_stack_count):
        pass

    @forward_to_components
    def on_remove(self):
        pass

    @forward_to_components
    def post_remove(self):
        component_class_names = set(component.CNAME for component in self.components)
        for component_definition in objects.components.component_definition_set:
            if component_definition.class_attr in component_class_names:
                self.remove_component(component_definition)
        if self.parts is not None:
            for part in self.parts:
                part.on_proxied_object_removed()
            self.parts.clear()

    def add_component(self, component):
        if super().add_component(component) and self.id:
            call_component_func(component, 'pre_add', self.object_manager_for_create)
            call_component_func(component, 'on_add')

    def remove_component(self, component_definition):
        component = super().remove_component(component_definition)
        if component is not None and self.id:
            call_component_func(component, 'on_remove_from_client')
            call_component_func(component, 'on_remove')
            call_component_func(component, 'post_remove')
        return component

    @property
    def parts(self):
        return self._parts

    def get_part_by_index(self, subroot_index):
        if self._parts is None:
            return
        for part in self._parts:
            if part.subroot_index == subroot_index:
                return part

    def get_part_by_part_group_index(self, part_group_index):
        if self._parts is None:
            return
        for part in self._parts:
            if part.part_group_index == part_group_index:
                return part

    @constproperty
    def is_part():
        return False

    @property
    def _anim_overrides_internal(self):
        pass

    @caches.cached
    def get_anim_overrides(self, actor_name):
        anim_overrides = self._anim_overrides_internal
        if anim_overrides is None:
            return
        elif actor_name is not None and anim_overrides.params:
            return anim_overrides(params={(key, actor_name): value for (key, value) in anim_overrides.params.items()})
        return anim_overrides

    def get_param_overrides(self, actor_name, only_for_keys=None):
        anim_overrides = self._anim_overrides_internal
        if anim_overrides is None:
            return
        if actor_name is not None and anim_overrides.params:
            return {(key, actor_name): value for (key, value) in anim_overrides.params.items() if only_for_keys is None or key in only_for_keys}
        return anim_overrides.params

    def children_recursive_gen(self, include_self=False):
        if include_self:
            yield self

    def get_all_children_recursive_gen(self):
        pass

    def parenting_hierarchy_gen(self):
        yield self

    def add_interaction_reference(self, interaction):
        if self._interaction_refs is None:
            self._interaction_refs = set()
        self._interaction_refs.add(interaction)

    def remove_interaction_reference(self, interaction):
        if self._interaction_refs is not None:
            if interaction in self._interaction_refs:
                self._interaction_refs.remove(interaction)
            if not self._interaction_refs:
                self._interaction_refs = None

    def cancel_interactions_running_on_object(self, finishing_type, cancel_reason_msg):
        if self._interaction_refs is None:
            return
        for interaction in tuple(self._interaction_refs):
            if interaction not in self._interaction_refs:
                pass
            else:
                interaction.cancel(finishing_type, cancel_reason_msg=cancel_reason_msg)
