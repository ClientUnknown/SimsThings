from _collections import defaultdictfrom collections import namedtuplefrom xml.sax.saxutils import escapeimport gcimport timeimport weakrefimport cachesimport enumimport interactions.constraintsimport servicesimport sims4.loglogger = sims4.log.Logger('ObjectLeakTracker', default_owner='tingyul')GC_PASS_THRESHOLD = 2SIM_HOUR_THRESHOLD = 3OBJECT_REF_DEPTH = 10HUB_OBJECT_THRESHOLD = 10GRAPHML_HEADER = '<?xml version="1.0" encoding="UTF-8"?>\n<graphml xmlns="http://graphml.graphdrawing.org/xmlns">\n<graph id="graph" edgedefault="directed">\n<key id="c" for="node" attr.name="color" attr.type="string">\n<default>black</default>\n</key>\n<key id="l" for="node" attr.name="label" attr.type="string"/>\n<key id="t" for="node" attr.name="type" attr.type="string"/>\n'GRAPHML_NODE_START = '<node id="{}">\n'GRAPHML_NODE_DATA = '<data key="{}">{}</data>\n'GRAPHML_NODE_END = '</node>\n'GRAPHML_EDGE = '<edge source="{}" target="{}"/>\n'GRAPHML_END = '</graph>\n</graphml>\n'
class NodeStatus(enum.Int, export=False):
    INVALID = ...
    PENDING = ...
    LEAKED = ...
    FALSE_POSITIVE = ...
NodeTimeStamp = namedtuple('NodeTimeStamp', ('gc_pass', 'time'))
class Node:
    __slots__ = ('_ref', '_status', '_pid', '_obj_type', '_manager_type', '_old_obj_id', '_time_stamps')

    def __init__(self, obj, manager_type, old_obj_id):
        self._ref = weakref.ref(obj)
        self._status = NodeStatus.INVALID
        self._pid = id(obj)
        self._obj_type = type(obj)
        self._manager_type = manager_type
        self._old_obj_id = old_obj_id
        self._time_stamps = {}

    def __str__(self):
        return 'Node(pid:{:#08x}, obj_type:{}, manager:{}, old_obj_id:{})'.format(self._pid, self._obj_type.__name__, self._manager_type.__name__, self._old_obj_id)

    @property
    def status(self):
        return self._status

    @property
    def pid(self):
        return self._pid

    @property
    def obj_type(self):
        return self._obj_type

    @property
    def manager_type(self):
        return self._manager_type

    @property
    def old_obj_id(self):
        return self._old_obj_id

    @property
    def time_stamps(self):
        return self._time_stamps

    def set_status(self, status, time_stamp):
        self._status = status
        self._time_stamps[self._status] = time_stamp

    def get_object(self):
        return self._ref()

class ObjectLeakTracker:
    __slots__ = ('_gc_pass_count', '_node_buckets', '_disable_reasons', '_enabled')

    def __init__(self):
        self._gc_pass_count = 0
        self._node_buckets = {}
        for status in NodeStatus:
            self._node_buckets[status] = set()
        self._disable_reasons = []
        self._enabled = False

    @property
    def buckets(self):
        return self._node_buckets

    def start_tracking(self):
        logger.debug('start tracking')
        if self._enabled:
            logger.error('Trying to start tracking when we have already started')
            return
        self._enabled = True
        current_zone = services.current_zone()
        if current_zone is not None and current_zone.is_zone_running:
            self.register_gc_callback()

    def register_gc_callback(self):
        logger.debug('register gc callback')
        if not self._enabled:
            logger.error('Trying to register gc callback when not enabled')
            return
        if self._gc_callback in gc.callbacks:
            logger.error('Trying to register gc callback multiple times')
            return
        gc.callbacks.append(self._gc_callback)

    def unregister_gc_callback(self):
        logger.debug('unregister gc callback')
        if not self._enabled:
            logger.error('Trying to register gc callback when not enabled')
            return
        if self._gc_callback not in gc.callbacks:
            logger.error('Trying to unregister gc callback that has not been registered')
            return
        gc.callbacks.remove(self._gc_callback)

    def stop_tracking(self):
        logger.debug('stop tracking')
        if not self._enabled:
            logger.error("Trying to stop tracking when it's not enabled")
            return
        self._enabled = False
        nodes = tuple(node for node in self._node_buckets[NodeStatus.PENDING] if node.get_object() is not None)
        if nodes:
            logger.debug('Leaked {} objects on zone removal.', len(nodes))
            self._report_leaks(nodes)
        for bucket in self._node_buckets.values():
            bucket.clear()

    def track_object(self, obj, manager, obj_id):
        if not self._enabled:
            return
        node = Node(obj, type(manager), obj_id)
        self._move_node_to_status(node, NodeStatus.PENDING)

    def add_disable_reason(self, reason):
        self._disable_reasons.append(reason)

    def remove_disable_reason(self, reason):
        if reason not in self._disable_reasons:
            logger.error('Trying remove disable reason ({}), not added before', reason)
            return
        self._disable_reasons.remove(reason)

    def _get_time_stamp(self):
        time_service = services.time_service()
        if time_service is None or time_service.sim_timeline is None:
            now = None
        else:
            now = time_service.sim_now
        return NodeTimeStamp(self._gc_pass_count, now)

    def _move_node_to_status(self, node, status):
        if node.status != NodeStatus.INVALID:
            self._node_buckets[node.status].remove(node)
        node.set_status(status, self._get_time_stamp())
        self._node_buckets[status].add(node)

    def _gc_callback(self, phase, info):
        generation = info['generation']
        if generation != 2:
            return
        if self._disable_reasons:
            logger.debug('ignoring gc callback due to disable reasons: {}', self._disable_reasons)
            return
        if phase == 'start':
            caches.clear_all_caches(force=True)
            interactions.constraints.RequiredSlot.clear_required_slot_cache()
            return
        self._gc_pass_count += 1
        logger.debug('Gc pass {}', self._gc_pass_count)
        for node in tuple(self._node_buckets[NodeStatus.LEAKED]):
            obj = node.get_object()
            if obj is None:
                self._move_node_to_status(node, NodeStatus.FALSE_POSITIVE)
        leaked_nodes = set()
        now = self._get_time_stamp()
        for node in tuple(self._node_buckets[NodeStatus.PENDING]):
            if node.get_object() is None:
                self._node_buckets[NodeStatus.PENDING].remove(node)
            else:
                node_time = node.time_stamps[NodeStatus.PENDING]
                if now.gc_pass < node_time.gc_pass + GC_PASS_THRESHOLD:
                    pass
                elif node_time.time is not None and now.time is not None and (now.time - node_time.time).in_hours() < SIM_HOUR_THRESHOLD:
                    pass
                else:
                    self._move_node_to_status(node, NodeStatus.LEAKED)
                    leaked_nodes.add(node)
        self._report_leaks(leaked_nodes)

    def _report_leaks(self, nodes):
        if not nodes:
            return
        objects = tuple(node.get_object() for node in nodes)
        self.generate_referrer_graph_for_objects(objects, log_error=True)

    @staticmethod
    def generate_referrer_graph_for_objects(objects, max_depth=None, max_hub_refs=None, log_error=False):
        all_objects = gc.get_objects()
        referrers_map = defaultdict(list)
        for obj in all_objects:
            for referent in gc.get_referents(obj):
                if not referent is all_objects:
                    if referent is objects:
                        pass
                    else:
                        referrers_map[id(referent)].append(obj)
        generic_sim_proxy = None
        posture_graph_service = services.current_zone().posture_graph_service
        if posture_graph_service is not None:
            generic_sim_proxy = posture_graph_service.get_proxied_sim()
        for obj in objects:
            if obj is generic_sim_proxy:
                pass
            else:
                ObjectLeakTracker._generate_referrer_graph(obj, referrers_map, max_depth=max_depth, max_hub_refs=max_hub_refs, log_error=log_error)

    @staticmethod
    def _generate_referrer_graph(root, referrers_map, max_depth=None, max_hub_refs=None, log_error=False):

        def start_graph(f):
            f.write(GRAPHML_HEADER)

        def end_graph(f):
            f.write(GRAPHML_END)

        def write_node(f, node, color):
            f.write(GRAPHML_NODE_START.format(id(node)))
            f.write(GRAPHML_NODE_DATA.format('c', color))
            f.write(GRAPHML_NODE_DATA.format('t', escape(type(node).__name__)))
            try:
                safe_repr = repr(node)
            except:
                safe_repr = 'exc'
            f.write(GRAPHML_NODE_DATA.format('l', escape(safe_repr)))
            f.write(GRAPHML_NODE_END)

        def write_edge(f, source, dest):
            f.write(GRAPHML_EDGE.format(id(source), id(dest)))

        max_depth = OBJECT_REF_DEPTH if max_depth is None else max_depth
        max_hub_refs = HUB_OBJECT_THRESHOLD if max_hub_refs is None else max_hub_refs
        current_time = time.strftime('%Y-%m-%d_%H.%M.%S', time.gmtime())
        file_name = 'ObjectDesc_0x{:08x}-{}-{}.graphml'.format(id(root), type(root).__name__, current_time)
        with open(file_name, 'w') as f:
            start_graph(f)
            visited = {id(root)}
            current_visit = [root]
            next_visit = []
            edges = []
            depth = 0
            while current_visit:
                for obj in current_visit:
                    node_id = id(obj)
                    is_hub = len(referrers_map[node_id]) > max_hub_refs
                    is_root = obj is root
                    if is_root:
                        color = 'green'
                    elif is_hub:
                        color = 'red'
                    else:
                        color = 'black'
                    write_node(f, obj, color)
                    if is_root or not depth >= max_depth:
                        if is_hub:
                            pass
                        else:
                            for referrer in referrers_map[node_id]:
                                referrer_id = id(referrer)
                                edges.append((referrer, obj))
                                if referrer_id not in visited:
                                    next_visit.append(referrer)
                                    visited.add(referrer_id)
                current_visit = next_visit
                next_visit = []
                depth += 1
            for (source, dest) in edges:
                write_edge(f, source, dest)
            end_graph(f)
        if log_error:
            logger.error('Object leaked: {}. See {} for more details.', root, file_name, trigger_callback_on_error_or_exception=False)
