from balloon.balloon_ops import AddBalloonfrom distributor.shared_messages import create_icon_info_msg, IconInfoDatafrom distributor.system import Distributorimport elements
class BalloonRequest(elements.Element):
    __slots__ = ['_sim_ref', 'icon', 'icon_object', 'overlay', 'balloon_type', 'priority', 'duration', 'delay', 'delay_randomization', 'category_icon', 'view_offset']

    def __init__(self, sim, icon, icon_object, overlay, balloon_type, priority, duration, delay, delay_randomization, category_icon, view_offset=None):
        super().__init__()
        self._sim_ref = sim.ref()
        self.icon = icon
        self.icon_object = icon_object
        self.overlay = overlay
        self.balloon_type = balloon_type
        self.priority = priority
        self.duration = duration
        self.delay = delay
        self.delay_randomization = delay_randomization
        self.category_icon = create_icon_info_msg(IconInfoData(icon_resource=category_icon[0], obj_instance=category_icon[1])) if category_icon is not None else None
        self.view_offset = view_offset

    @property
    def _sim(self):
        if self._sim_ref is not None:
            return self._sim_ref()

    def _run(self, timeline):
        return self.distribute()

    def distribute(self):
        sim = self._sim
        if sim is not None and not sim.is_hidden():
            balloon_op = AddBalloon(self, sim)
            distributor = Distributor.instance()
            distributor.add_op(sim, balloon_op)
            return True
        return False
