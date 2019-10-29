import itertoolsfrom debugvis import Contextfrom interactions.constraints import RequiredSlotSingle, Anywhere, create_constraint_set, _ConstraintSetfrom postures import PostureEvent, PostureTrackfrom sims4.color import pseudo_random_color, Colorfrom sims4.geometry import RelativeFacingRange, RelativeFacingWithCircleimport contourimport routingimport sims4.colorDONE_POSTURE_EVENTS = {PostureEvent.TRANSITION_FAIL, PostureEvent.TRANSITION_COMPLETE}MULTISURFACE_OFFSET = 0.5
def _draw_constraint(layer, constraint, color, altitude_modifier=0, anywhere_position=None, draw_contours=False):
    if constraint is None:
        return
    if isinstance(constraint, RequiredSlotSingle):
        constraint = constraint._intersect(Anywhere())
    if isinstance(constraint, _ConstraintSet):
        drawn_geometry = []
        for sub_constraint in constraint._constraints:
            if sub_constraint._geometry is not None:
                if sub_constraint._geometry in drawn_geometry:
                    _draw_constraint(layer, sub_constraint.generate_alternate_geometry_constraint(None), color, altitude_modifier)
                else:
                    drawn_geometry.append(sub_constraint._geometry)
                    _draw_constraint(layer, sub_constraint, color, altitude_modifier)
                    altitude_modifier += 0.1
            _draw_constraint(layer, sub_constraint, color, altitude_modifier)
            altitude_modifier += 0.1
        return
    (r, g, b, a) = sims4.color.to_rgba(color)
    semitransparent = sims4.color.from_rgba(r, g, b, a*0.5)
    transparent = sims4.color.from_rgba(r, g, b, a*0.25)
    layer.routing_surface = constraint.routing_surface
    if constraint.geometry is not None:
        if constraint.geometry.polygon is not None:
            drawn_facings = []
            drawn_points = []
            drawn_polys = []
            for poly in constraint.geometry.polygon:
                if poly not in drawn_polys:
                    drawn_polys.append(poly)
                    if constraint.multi_surface:
                        if constraint.routing_surface.type in routing.object_routing_surfaces:
                            layer.add_polygon(poly, color=color, altitude=altitude_modifier + 0.1 - MULTISURFACE_OFFSET)
                        else:
                            layer.add_polygon(poly, color=color, altitude=altitude_modifier + 0.1 + MULTISURFACE_OFFSET)
                    layer.add_polygon(poly, color=color, altitude=altitude_modifier + 0.1)

                def draw_facing(point, color):
                    altitude = altitude_modifier + 0.1
                    (valid, interval) = constraint._geometry.get_orientation_range(point)
                    if valid and interval is not None:
                        if interval.a != interval.b:
                            if interval.angle >= sims4.math.TWO_PI:
                                angles = [(interval.ideal, True)]
                            else:
                                angles = [(interval.a, False), (interval.ideal, True), (interval.b, False)]
                        else:
                            angles = [(interval.a, True)]
                        for (angle, arrowhead) in angles:
                            facings_key = (point, angle, arrowhead)
                            if facings_key not in drawn_facings:
                                drawn_facings.append(facings_key)
                                layer.add_arrow(point, angle, end_arrow=arrowhead, length=0.2, color=color, altitude=altitude)
                    else:
                        point_key = point
                        if point_key not in drawn_points:
                            drawn_points.append(point_key)
                            if constraint.multi_surface:
                                if constraint.routing_surface.type in routing.object_routing_surfaces:
                                    layer.add_point(point, color=color, altitude=altitude - MULTISURFACE_OFFSET)
                                else:
                                    layer.add_point(point, color=color, altitude=altitude + MULTISURFACE_OFFSET)
                            layer.add_point(point, color=color, altitude=altitude)

                if not constraint.geometry.restrictions:
                    pass
                else:
                    for vertex in poly:
                        draw_facing(vertex, color)
                    for i in range(len(poly)):
                        v1 = poly[i]
                        v2 = poly[(i + 1) % len(poly)]
                        draw_facing(v1, transparent)
                        draw_facing(0.5*(v1 + v2), transparent)
            if draw_contours:

                def constraint_cost(point):
                    p3 = sims4.math.Vector3(point.x, 0, point.y)
                    orientation = sims4.math.Quaternion.IDENTITY()
                    if constraint._geometry is not None:
                        (_, quat) = constraint._geometry.get_orientation(p3)
                        if quat is not None:
                            orientation = quat
                        else:
                            orientation = sims4.math.Quaternion.IDENTITY()
                        cost = constraint.constraint_cost(p3, orientation)
                    else:
                        cost = 0
                    return cost

                MARGIN = 1.0
                poly = constraint.geometry.polygon
                pt1 = poly[0][0]
                lb = sims4.math.Vector2(pt1.x, pt1.z)
                ub = sims4.math.Vector2(pt1.x, pt1.z)
                for poly in constraint.geometry.polygon:
                    for vertex in poly:
                        lb.x = min(lb.x, vertex.x - MARGIN)
                        lb.y = min(lb.y, vertex.z - MARGIN)
                        ub.x = max(ub.x, vertex.x + MARGIN)
                        ub.y = max(ub.y, vertex.z + MARGIN)
                bounds = sims4.geometry.QtRect(lb, ub)
                hf = contour.HeightField(constraint_cost, bounds, spacing=0.5)
                isolines = hf.all_isolines()
                if isolines:
                    value_min = isolines[0][0]
                    value_max = isolines[-1][0]
                    for (value, line) in isolines:
                        if value_max == value_min:
                            contour_color = sims4.color.from_rgba(1.0, 1.0, 1.0, 0.5)
                        else:
                            contour_quality = 1 - (value - value_min)/(value_max - value_min)
                            contour_color = sims4.color.red_green_lerp(contour_quality, s=0.3, a=0.5)
                        for i in range(len(line) - 1):
                            v1 = line[i]
                            v2 = line[i + 1]
                            layer.add_segment(sims4.math.Vector3(v1.x, 0, v1.y), sims4.math.Vector3(v2.x, 0, v2.y), color=contour_color, routing_surface=constraint.routing_surface)
                        pt = max(line, key=lambda v: (v.x, v.y))
                        v = sims4.math.Vector3(pt.x, 0, pt.y)
                        layer.add_text_world(v, '{:0.2f}'.format(value), routing_surface=constraint.routing_surface)
        elif constraint.geometry.restrictions:
            for restriction in constraint.geometry.restrictions:
                if isinstance(restriction, RelativeFacingRange):
                    layer.add_point(restriction.target, color=color)
                elif isinstance(restriction, RelativeFacingWithCircle):
                    layer.add_circle(restriction.target, radius=restriction.radius, color=color)
        if isinstance(constraint, RequiredSlotSingle):
            for (routing_transform, reference_joint, _) in itertools.chain(constraint._slots_to_params_entry or (), constraint._slots_to_params_exit or ()):
                if routing_transform is None:
                    universal_constraint = constraint.get_universal_constraint(reference_joint=reference_joint)
                    _draw_constraint(layer, universal_constraint, color=semitransparent, altitude_modifier=altitude_modifier, draw_contours=draw_contours)
                else:
                    layer.add_arrow_for_transform(routing_transform, length=0.1, color=semitransparent, altitude=altitude_modifier)
                    layer.add_segment(routing_transform.translation, constraint.containment_transform.translation, color=transparent, altitude=altitude_modifier)
    elif isinstance(constraint, Anywhere) and anywhere_position is not None:
        layer.add_circle(anywhere_position, radius=0.28, color=transparent, altitude=altitude_modifier)
        layer.add_circle(anywhere_position, radius=0.3, color=semitransparent, altitude=altitude_modifier)

class SimLOSVisualizer:

    def __init__(self, sim, layer):
        self._sim_ref = sim.ref()
        self.layer = layer
        self._color = pseudo_random_color(sim.id)
        color2 = pseudo_random_color(-sim.id)
        (r, g, b, a) = sims4.color.to_rgba(color2)
        (gr, gg, gb, ga) = sims4.color.to_rgba(Color.GREY)
        self._color_semitrans = sims4.color.from_rgba((gr + r)/2, (gg + g)/2, (gb + b)/2, (ga + a)/2*0.4)
        self._start()

    @property
    def _sim(self):
        if self._sim_ref is not None:
            return self._sim_ref()

    def _start(self):
        self._sim.on_posture_event.append(self._on_posture_event)
        self._sim.si_state.on_changed.append(self._redraw)
        self._redraw()

    def stop(self):
        if self._on_posture_event in self._sim.on_posture_event:
            self._sim.on_posture_event.remove(self._on_posture_event)
        if self._redraw in self._sim.si_state.on_changed:
            self._sim.si_state.on_changed.remove(self._redraw)

    def _on_posture_event(self, change, dest_state, track, source_posture, dest_posture):
        if self._sim is None or not PostureTrack.is_body(track):
            return
        if change in DONE_POSTURE_EVENTS:
            self._redraw()

    def _redraw(self, _=None):
        los_constraint = self._sim.los_constraint
        with Context(self.layer, routing_surface=los_constraint.routing_surface) as layer:
            _draw_constraint(layer, los_constraint, self._color)
            _draw_constraint(layer, self._sim.get_social_group_constraint(None), self._color_semitrans)

class SimConstraintVisualizer:

    def __init__(self, sim, layer):
        self._sim = sim.ref()
        self.layer = layer
        self._social_groups = []
        self._start()

    @property
    def sim(self):
        if self._sim is not None:
            return self._sim()

    def _start(self):
        self.sim.on_posture_event.append(self._on_posture_event)
        self._on_posture_event(PostureEvent.TRANSITION_COMPLETE, self.sim.posture_state, PostureTrack.BODY, None, self.sim.posture)
        self.sim.si_state.add_watcher(self, self._on_si_state_changed)

    def stop(self):
        if self.sim is not None:
            if self._on_posture_event in self.sim.on_posture_event:
                self.sim.on_posture_event.remove(self._on_posture_event)
            self._unregister_group_callbacks()
            self.sim.si_state.remove_watcher(self)

    def redraw(self, sim, constraint):
        routing_surface = None if isinstance(constraint, _ConstraintSet) else constraint.routing_surface
        color = pseudo_random_color(sim.id)
        (r, g, b, a) = sims4.color.to_rgba(color)
        (gr, gg, gb, ga) = sims4.color.to_rgba(Color.GREY)
        semitransparent = sims4.color.from_rgba((gr + r)/2, (gg + g)/2, (gb + b)/2, (ga + a)/2*0.4)
        transparent = sims4.color.from_rgba((gr + r)/2, (gg + g)/2, (gb + b)/2, (ga + a)/2*0.15)
        if isinstance(constraint, _ConstraintSet):
            for sub_constraint in constraint:
                if sub_constraint.routing_surface is not None:
                    routing_surface = sub_constraint.routing_surface
                    break
        else:
            routing_surface = constraint.routing_surface
        with Context(self.layer, routing_surface=routing_surface) as layer:
            direction_constraint = None
            direction_constraints = []
            for sub_constraint in constraint:
                if sub_constraint._geometry is not None and sub_constraint._geometry.polygon is None and sub_constraint._geometry.restrictions is not None:
                    direction_constraints.append(sub_constraint)
            if direction_constraints:
                direction_constraint = create_constraint_set(direction_constraints)
            for si in sim.si_state:
                participant_type = si.get_participant_type(sim)
                for si_constraint in si.constraint_intersection(participant_type=participant_type):
                    if direction_constraint is not None:
                        si_constraint = direction_constraint.intersect(si_constraint)
                    si_color = transparent
                    si_altitude = 0.01
                    if si.is_guaranteed():
                        si_color = semitransparent
                        si_altitude = 0.02
                    _draw_constraint(layer, si_constraint, si_color, altitude_modifier=si_altitude)
            _draw_constraint(layer, constraint, color, altitude_modifier=0.03, anywhere_position=sim.position, draw_contours=True)

    def _on_posture_event(self, change, dest_state, track, source_posture, dest_posture):
        if not PostureTrack.is_body(track):
            return
        sim = dest_state.sim
        if change == PostureEvent.TRANSITION_START or change in DONE_POSTURE_EVENTS:
            constraint = get_total_constraint(sim)
        else:
            return
        self._register_on_constraint_changed_for_groups()
        if dest_state is not None:
            self._on_rebuild(sim, constraint)

    def _register_on_constraint_changed_for_groups(self):
        self._unregister_group_callbacks()
        sim = self.sim
        if sim is not None:
            self._social_groups.extend(sim.get_groups_for_sim_gen())
            for group in self._social_groups:
                group.on_constraint_changed.append(self._on_constraint_changed)

    def _unregister_group_callbacks(self):
        for group in self._social_groups:
            if self._on_constraint_changed in group.on_constraint_changed:
                group.on_constraint_changed.remove(self._on_constraint_changed)
        del self._social_groups[:]

    def _on_constraint_changed(self):
        sim = self.sim
        constraint = get_total_constraint(sim)
        self._on_rebuild(sim, constraint)

    def _on_rebuild(self, sim, constraint):
        self.redraw(sim, constraint)

    def _on_si_state_changed(self, si_state):
        self._on_constraint_changed()

def get_total_constraint(sim):
    if sim.queue.running is not None and sim.queue.running.is_super and sim.queue.running.transition is not None:
        constraint = sim.queue.running.transition.get_final_constraint(sim)
    else:
        constraint = Anywhere()
    total_constraint = sim.si_state.get_total_constraint(include_inertial_sis=True, existing_constraint=constraint)
    return total_constraint
