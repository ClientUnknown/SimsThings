from distributor.ops import SetCallToActionfrom distributor.system import Distributorfrom filters.tunable import TunableSimFilterfrom sims4.localization import TunableLocalizedStringfrom sims4.tuning.instances import HashedTunedInstanceMetaclassfrom sims4.tuning.tunable import HasTunableReference, TunableRange, TunableColor, Tunable, OptionalTunableimport servicesimport sims4.logimport taglogger = sims4.log.Logger('call_to_action', default_owner='nabaker')
class CallToAction(HasTunableReference, metaclass=HashedTunedInstanceMetaclass, manager=services.get_instance_manager(sims4.resources.Types.CALL_TO_ACTION)):
    INSTANCE_TUNABLES = {'_color': TunableColor(description='\n            The color of the call to action.\n            '), '_pulse_frequency': TunableRange(description='\n            The frequency at which the highlight pulses.\n            ', tunable_type=float, default=1.0, minimum=0.1), '_thickness': TunableRange(description='\n            The thickness of the highlight.\n            ', tunable_type=float, default=0.002, minimum=0.001, maximum=0.005), '_tags': tag.TunableTags(description='\n            The set of tags that are used to determine which objects to highlight.\n            '), '_on_active_lot': Tunable(description='\n            Whether or not objects on active lot should be highlighted.\n            ', tunable_type=bool, default=True), '_on_open_street': Tunable(description='\n            Whether or not objects on open street should be highlighted.\n            ', tunable_type=bool, default=True), '_tutorial_text': OptionalTunable(description='\n            Text for a tutorial call to action.  If this is enabled, the\n            CTA will be a tutorial CTA with the specified text.\n            ', tunable=TunableLocalizedString()), '_sim_filter': OptionalTunable(description='\n            Filter to select one or more sims to recieve the CTA.\n            ', tunable=TunableSimFilter.TunablePackSafeReference())}

    def __init__(self):
        super().__init__()
        self._owner = None
        self._sim_ids = []

    def get_sim_filter_gsi_name(self):
        return str(self)

    @property
    def owner(self):
        return self._owner

    def turn_on(self, owner):
        self._owner = owner
        for script_object in services.object_manager().get_objects_with_tags_gen(*self._tags):
            self._turn_on_object(script_object)
        if self._sim_filter is not None:
            constrained_sims = tuple(sim_info.sim_id for sim_info in services.sim_info_manager().instanced_sims_gen())
            filter_result = services.sim_filter_service().submit_filter(sim_filter=self._sim_filter, callback=None, sim_constraints=constrained_sims, allow_yielding=False, gsi_source_fn=self.get_sim_filter_gsi_name)
            object_manager = services.object_manager()
            self._sim_ids = []
            for result in filter_result:
                sim_id = result.sim_info.sim_id
                self._sim_ids.append(sim_id)
                sim = object_manager.get(sim_id)
                self._turn_on_object(sim)

    def turn_off(self):
        if self._owner is not None:
            self._owner.on_cta_ended(self.guid64)
        for script_object in services.object_manager().get_objects_with_tags_gen(*self._tags):
            Distributor.instance().add_op(script_object, SetCallToAction(0, 0, 0, None))
        object_manager = services.object_manager()
        for sim_id in self._sim_ids:
            sim = object_manager.get(sim_id)
            if sim is not None:
                Distributor.instance().add_op(sim, SetCallToAction(0, 0, 0))
        self._sim_ids = []

    def turn_on_object_on_create(self, script_object):
        if script_object.definition.has_build_buy_tag(*self._tags):
            script_object.register_on_location_changed(self._object_location_changed)
        elif script_object.is_sim and self._sim_filter is not None:
            results = services.sim_filter_service().submit_filter(sim_filter=self._sim_filter, callback=None, sim_constraints=(script_object.sim_info.sim_id,), allow_yielding=False, gsi_source_fn=self.get_sim_filter_gsi_name)
            if results:
                script_object.register_on_location_changed(self._object_location_changed)

    def _turn_on_object(self, script_object):
        if script_object.is_on_active_lot():
            if not self._on_active_lot:
                return
        elif not self._on_open_street:
            return
        Distributor.instance().add_op(script_object, SetCallToAction(self._color, self._pulse_frequency, self._thickness, tutorial_text=self._tutorial_text))

    def _object_location_changed(self, script_object, old_loc, new_loc):
        script_object.unregister_on_location_changed(self._object_location_changed)
        self._turn_on_object(script_object)
        if script_object.is_sim:
            self._sim_ids.append(script_object.sim_info.sim_id)
