from bisect import bisect_rightimport collectionsimport operatorfrom sims4.math import Thresholdfrom sims4.tuning.tunable import TunableList, TunableTuple, TunableReference, Tunable, TunableFactoryimport servicesimport sims4.logimport sims4.resourceslogger = sims4.log.Logger('Relationship', default_owner='msantander')TrackMean = collections.namedtuple('TrackMean', ['track', 'mean'])STATIC_REL_TEST_VALUES = range(-100, 100, 10)
class BaseRelationshipTrackData:

    def build_track_data(self):
        raise NotImplementedError

    def get_track_instance_data(self, track):
        raise NotImplementedError

    def bit_track_node_gen(self):
        yield None

    def get_track_mean_list_for_bit(self, bit):
        return []

    @staticmethod
    def find_add_value_score_index(track_list, score, track_data):
        i = bisect_right(track_list, score)
        if score >= 0:
            if i:
                return i - 1
        elif i != len(track_list):
            return i
        logger.error('No bit_set add value has a valid value for track score {} for track {}', score, track_data, owner='camilogarcia')
        return -1

class BaseRelationshipTrackInstanceData:
    __slots__ = '_track'

    def __init__(self, track):
        self._track = track

    def __repr__(self):
        return '{}'.format(self._track)

    def setup_callbacks(self):
        raise NotImplementedError

    def get_active_bit(self):
        raise NotImplementedError

    def get_active_bit_by_value(self):
        raise NotImplementedError

    def request_full_update(self):
        raise NotImplementedError

    @property
    def _track_data(self):
        return self._track.bit_data

    @property
    def bit_data_set(self):
        return self._track.bit_data.bit_data_set

    def _apply_bit_change(self, bit_to_remove, bit_to_add):
        notify_client = False
        relationship = self._track.tracker.rel_data.relationship
        if bit_to_remove is not None:
            relationship.remove_bit(relationship.sim_id_a, relationship.sim_id_b, bit_to_remove, notify_client=False)
            notify_client = True
        if bit_to_add is not None:
            relationship.add_relationship_bit(relationship.sim_id_a, relationship.sim_id_b, bit_to_add, notify_client=False)
            notify_client = True
        if notify_client and not relationship.suppress_client_updates:
            if relationship._is_object_rel:
                relationship.send_object_relationship_info()
            else:
                relationship.send_relationship_info()

    @staticmethod
    def _setup_callback_listeners_for_track(bit_set_index, bit_set_list, track, track_update_add_callback, track_update_remove_callback):
        if bit_set_index < 0:
            return (None, None)
        if bit_set_index >= len(bit_set_list):
            logger.error('BitSetIndex: {}: is out of bounds of bit set list for track:{} cannot setup callbacks: {}: {}', bit_set_index, track, track_update_add_callback, track_update_remove_callback)
            return (None, None)
        node = bit_set_list[bit_set_index]
        alarm_op = operator.lt if node.remove_value >= 0 else operator.ge
        threshold = Threshold(node.remove_value, alarm_op)
        remove_callback_listener_data = track.tracker.create_and_add_listener(track.stat_type, threshold, track_update_remove_callback)
        add_callback_listener_data = None
        next_node_index = bit_set_index + 1 if node.remove_value >= 0 else bit_set_index - 1
        if next_node_index < len(bit_set_list):
            next_node = bit_set_list[next_node_index]
            alarm_op = operator.ge if next_node.add_value >= 0 else operator.lt
            threshold = Threshold(next_node.add_value, alarm_op)
            add_callback_listener_data = track.tracker.create_and_add_listener(track.stat_type, threshold, track_update_add_callback)
        return (add_callback_listener_data, remove_callback_listener_data)

class BitTrackNode:
    __slots__ = ('bit', 'add_value', 'remove_value', 'track_interval_average')

    def __init__(self, bit, add_value, remove_value):
        self.bit = bit
        self.add_value = add_value
        self.remove_value = remove_value
        self.track_interval_average = None
        if self.bit:
            self.bit.is_track_bit = True

    def __repr__(self):
        return '<Bit:{}[{}-{}]>'.format(self.bit, self.add_value, self.remove_value)

class TunableRelationshipBitSet(TunableList):

    @staticmethod
    def _verify_tunable_callback(source, *_, bit, remove_value, add_value, **__):
        if add_value >= 0:
            if remove_value > add_value:
                logger.error('Tunable {} has a tuned remove value higher than its positive add value for bit {}', source, bit, owner='camilogarcia')
        elif remove_value < add_value:
            logger.error('Tunable {} has a tuned remove value lower than its negative add value for bit {}', source, bit, owner='camilogarcia')

    def __init__(self, **kwargs):
        super().__init__(TunableTuple(verify_tunable_callback=TunableRelationshipBitSet._verify_tunable_callback, bit=TunableReference(services.get_instance_manager(sims4.resources.Types.RELATIONSHIP_BIT), description='Reference to bit in set'), remove_value=Tunable(description='\n                Track score value for the bit to be removed.\n                Since by default all relationships will converge at 0 we \n                must tune depending on the side of the zero we are in.\n                For values greater than 0, this must be less than add value.\n                For values less than 0, this must be greater than add value. \n                \n                For example, on the friendship track:\n                GOOD_FRIENDS (value>0) has a remove value of 55.\n                As soon as the track value goes below 55 the bit good friends\n                will be removed, and the next lowest bit will be added.\n                \n                DISLIKED (value<0) has a remove_value of -15.\n                As soon as the track value goes over -15 the bit disliked will \n                be removed and the next highest bit will be added.\n                \n                TUNING MIDDLE VALUES (Ranges approach 0)\n                When tuning a value that goes past 0 (a bit from 10 to -10) it\n                is recommended we tune a positive Bit (10 to 0) and a negative \n                bit (-10 to 0).  This way, we can guarantee the rules will \n                consider correct positive and negative directions.\n                ', tunable_type=float, default=-100), add_value=Tunable(description='\n                Track score value for the bit to be added.\n                Since by default all relationships will converge at 0 we \n                must tune depending on the side of the zero we are in.\n                For values greater than 0, this must be greater than remove \n                value.\n                For values less than 0 this must be less than remove value. \n                \n                Example: For the friendship track:\n                GOOD_FRIENDS (value>0) has an add value of 60\n                As soon as the track value goes >= 60 the bit good friends\n                will be added and the previous active track bit will be removed.\n                \n                DISLIKED (value<0) has an add_value of -20\n                As soon as the track value goes <= -20 the bit disliked will \n                be added and the previous active track bid will be removed.\n                \n                TUNING MIDDLE VALUES (Ranges approach 0)\n                When tuning a value that goes past 0 (a bit from 10 to -10) it\n                is recommended we tune a positive Bit (10 to 0) and a negative \n                bit (-10 to 0).  This way, we can guarantee the rules will \n                consider correct positive and negative directions.\n                ', tunable_type=float, default=100), description='Data for this bit in the track'), **kwargs)

class SimpleRelationshipTrackData(BaseRelationshipTrackData):

    def __init__(self, bit_data):
        super().__init__()
        self.bit_set_list = []
        self.bit_set_list_add_values = []
        self.bit_data_set = set()
        self._raw_bit_data = bit_data

    def build_track_data(self):
        if not self._raw_bit_data:
            return
        for (i, bit_set) in enumerate(self._raw_bit_data):
            bit_track = BitTrackNode(bit_set.bit, bit_set.add_value, bit_set.remove_value)
            if i < len(self._raw_bit_data) - 1:
                next_bit = self._raw_bit_data[i + 1]
                bit_track.track_interval_average = (next_bit.add_value + bit_set.add_value)*0.5
            else:
                bit_track.track_interval_average = (bit_set.add_value + bit_track.bit.triggered_track.max_value)*0.5
            self.bit_set_list.append(bit_track)
        self.bit_set_list.sort(key=lambda node: node.add_value)
        self.bit_set_list_add_values = [bit_set_item.add_value for bit_set_item in self.bit_set_list]
        self.bit_data_set = set([bit_set_item.bit for bit_set_item in self.bit_set_list])

    def get_track_instance_data(self, track):
        return SimpleRelationshipTrackInstanceData(track)

    def bit_track_node_gen(self):
        for bit_data in self.bit_set_list:
            yield bit_data

    def get_track_mean_list_for_bit(self, bit):
        for bit_track_node in self.bit_set_list:
            if bit_track_node.bit is bit:
                return [TrackMean(bit.triggered_track, bit_track_node.track_interval_average)]
        logger.error('Unable to find Bit: {} in 1D RelationshipTrack {}', self, owner='manus')
        return []

class TunableRelationshipBitData(TunableFactory):
    FACTORY_TYPE = SimpleRelationshipTrackData

    def __init__(self, **kwargs):
        super().__init__(verify_tunable_callback=TunableRelationshipBitData._verify_tunable_callback, bit_data=TunableRelationshipBitSet(), **kwargs)

    @staticmethod
    def _verify_tunable_callback(source, *_, bit_data, **__):
        TunableRelationshipBitData.verify_bit_data_gaps(bit_data, source)

    @staticmethod
    def verify_bit_data_gaps(tuning_data, source):
        add_values = []
        for bit in tuning_data:
            add_values.append(bit.add_value)
        add_values.sort()
        for test_value in STATIC_REL_TEST_VALUES:
            result_index = BaseRelationshipTrackData.find_add_value_score_index(add_values, test_value, source)
            if result_index == -1:
                logger.error('No bit_set add value has a valid value for track test score {} for track {}', test_value, source, owner='camilogarcia')

class SimpleRelationshipTrackInstanceData(BaseRelationshipTrackInstanceData):
    __slots__ = ('_bit_set_index', '_node_change_listeners')

    def __init__(self, track):
        super().__init__(track)
        self._bit_set_index = -1
        self._node_change_listeners = None

    def callback_listeners(self):
        return self._node_change_listeners

    def setup_callbacks(self):
        if self._bit_set_index == -1:
            track_data = self._track_data
            score = self._track.get_value()
            self._bit_set_index = BaseRelationshipTrackData.find_add_value_score_index(track_data.bit_set_list_add_values, score, self)
        self._setup_node_change_listeners()

    def _clear_node_change_listeners(self):
        if self._node_change_listeners:
            for listener_handle in self._node_change_listeners:
                if listener_handle is not None:
                    self._track.tracker.remove_listener(listener_handle)
            self._node_change_listeners = None

    def _setup_node_change_listeners(self):
        self._clear_node_change_listeners()
        self._node_change_listeners = self._setup_callback_listeners_for_track(self._bit_set_index, self._track_data.bit_set_list, self._track, self._track_update_add_bit_callback, self._track_update_remove_bit_callback)

    def _requires_bit_fixup(self, new_node, new_index):
        if self._bit_set_index == -1 or self._bit_set_index == new_index:
            return False
        current_node = self._track_data.bit_set_list[self._bit_set_index]
        requires_fixup = False
        if current_node.bit is not new_node.bit:
            track_value = self._track.get_value()
            if track_value >= 0:
                if new_node.remove_value > track_value or new_node.add_value < track_value:
                    requires_fixup = True
            elif new_node.remove_value < track_value or new_node.add_value > track_value:
                requires_fixup = True
        if requires_fixup:
            relationship = self._track.tracker.rel_data.relationship
            if new_node.bit is not None:
                relationship.remove_bit(relationship.sim_id_a, relationship.sim_id_b, new_node.bit, notify_client=False)
            if current_node.bit is not None:
                relationship.add_relationship_bit(relationship.sim_id_a, relationship.sim_id_b, current_node.bit, notify_client=False)
        return requires_fixup

    def get_active_bit(self):
        if self._bit_set_index < 0:
            return
        bit_track_node = self._track_data.bit_set_list[self._bit_set_index]
        return bit_track_node.bit

    def get_active_bit_by_value(self):
        index = BaseRelationshipTrackData.find_add_value_score_index(self._track_data.bit_set_list_add_values, self._track.get_value(), self)
        if index < 0:
            return
        return self._track_data.bit_set_list[index].bit

    def request_full_update(self):
        return self._full_update()

    def _update(self, remove_callback):
        track_data = self._track_data
        if self._bit_set_index == -1:
            return self._full_update()
        original_node = track_data.bit_set_list[self._bit_set_index]
        self._clear_node_change_listeners()
        current_value = self._track.get_value()
        self._bit_set_index = BaseRelationshipTrackData.find_add_value_score_index(track_data.bit_set_list_add_values, current_value, self)
        current_node = track_data.bit_set_list[self._bit_set_index]
        self._setup_node_change_listeners()
        logger.debug('Updating track {}', self)
        logger.debug('   Score: {}', current_value)
        logger.debug('   Original node: {} - {}', original_node.add_value, original_node.remove_value)
        logger.debug('   Current node:  {} - {}', current_node.add_value, current_node.remove_value)
        logger.debug('   index: {}', self._bit_set_index)
        if current_node == original_node:
            return (None, None)
        new_bit = track_data.bit_set_list[self._bit_set_index].bit
        logger.debug('   Old bit: {}', original_node.bit)
        logger.debug('   New bit: {}', new_bit)
        return (original_node.bit, new_bit)

    def _full_update(self):
        self._clear_node_change_listeners()
        track_data = self._track_data
        score = self._track.get_value()
        old_bit = None
        if self._bit_set_index != -1:
            old_bit = track_data.bit_set_list[self._bit_set_index].bit
        self._bit_set_index = BaseRelationshipTrackData.find_add_value_score_index(track_data.bit_set_list_add_values, score, self)
        self._setup_node_change_listeners()
        new_bit = None
        if self._bit_set_index != -1:
            new_bit = track_data.bit_set_list[self._bit_set_index].bit
        else:
            logger.warn("There's a hole in RelationshipTrack: {}", self._track, owner='jjacobson')
        logger.debug('Updating track (FULL) {}', self._track)
        logger.debug('   Score: {}', score)
        logger.debug('   Current node:  {} - {}', track_data.bit_set_list[self._bit_set_index].add_value, track_data.bit_set_list[self._bit_set_index].remove_value)
        logger.debug('   Old bit: {}', old_bit)
        logger.debug('   New bit: {}', new_bit)
        logger.debug('   index: {}', self._bit_set_index)
        return (old_bit, new_bit)

    def full_load_update(self, relationship):
        if self._bit_set_index != -1:
            current_node = self._track_data.bit_set_list[self._bit_set_index]
            if relationship.has_bit(relationship.sim_id_a, current_node.bit):
                return
        for (i, track_bit) in enumerate(self._track_data.bit_set_list):
            if relationship.has_bit(relationship.sim_id_a, track_bit.bit):
                if not self._requires_bit_fixup(track_bit, i):
                    self._bit_set_index = i
                    self._setup_node_change_listeners()
                return

    def _track_update_add_bit_callback(self, _):
        logger.debug('_track_update_move_up_callback() called')
        (bit_to_remove, bit_to_add) = self._update(False)
        self._apply_bit_change(bit_to_remove, bit_to_add)

    def _track_update_remove_bit_callback(self, _):
        logger.debug('_track_update_move_down_callback() called')
        (bit_to_remove, bit_to_add) = self._update(True)
        self._apply_bit_change(bit_to_remove, bit_to_add)

class _RelationshipTrackData2dLinkArrayElement:

    def __init__(self, bit_set, add_value, remove_value):
        self.bit_list_add_values = []
        self.bit_set = self._build_node_data(bit_set)
        self.add_value = add_value
        self.remove_value = remove_value
        self.average_value = None

    def _build_node_data(self, bit_set_nods):
        bit_set_list = []
        if not bit_set_nods:
            return bit_set_list
        bit_set_list = []
        for (i, bit_set) in enumerate(bit_set_nods):
            bit_track = BitTrackNode(bit_set.bit, bit_set.add_value, bit_set.remove_value)
            if i < len(bit_set_nods) - 1:
                next_bit = bit_set_nods[i + 1]
                bit_track.track_interval_average = (next_bit.add_value + bit_set.add_value)*0.5
            else:
                self.average_value = (bit_set.add_value + bit_track.bit.triggered_track.max_value)*0.5
            bit_set_list.append(bit_track)
        bit_set_list.sort(key=lambda node: node.add_value)
        self.bit_list_add_values = [bit_set_item.add_value for bit_set_item in bit_set_list]
        return bit_set_list

class RelationshipTrackData2dLink(BaseRelationshipTrackData):

    def __init__(self, y_axis_track, y_axis_content):
        super().__init__()
        self.bit_set_list = []
        self.bit_set_list_add_values = []
        self.bit_data_set = set()
        self._y_axis_track = y_axis_track
        self._raw_y_axis_content = y_axis_content

    def build_track_data(self):
        if not self._raw_y_axis_content:
            return
        self.bit_set_list = [_RelationshipTrackData2dLinkArrayElement(y_axis_chunk.bit_set, y_axis_chunk.add_value, y_axis_chunk.remove_value) for y_axis_chunk in self._raw_y_axis_content]
        self.bit_set_list.sort(key=lambda node: node.add_value)
        self.bit_set_list_add_values = [bit_set_item.add_value for bit_set_item in self.bit_set_list]
        for bit_set_item in self.bit_set_list:
            self.bit_data_set |= set([bit_set.bit for bit_set in bit_set_item.bit_set])

    def get_track_instance_data(self, track):
        return RelationshipTrackInstanceData2dLink(track)

    def bit_track_node_gen(self):
        for y_content in self.bit_set_list:
            for x_content in y_content.bit_set:
                yield x_content

    def get_track_mean_list_for_bit(self, bit):
        x_track = None
        y_track = self._y_axis_track
        for y_content in self.bit_set_list:
            for x_content in y_content.bit_set:
                if x_content.bit is bit:
                    x_track = x_content.bit.triggered_track
        if not hasattr(y_content, 'average_value'):
            pass
        track_mean_list = [TrackMean(x_track, x_content.average_value), TrackMean(y_track, y_content.average_value)]
        return track_mean_list

    @property
    def y_axis_track(self):
        return self._y_axis_track

class TunableRelationshipTrack2dLink(TunableFactory):
    FACTORY_TYPE = RelationshipTrackData2dLink

    def __init__(self, **kwargs):
        super().__init__(verify_tunable_callback=TunableRelationshipTrack2dLink._verify_tunable_callback, y_axis_track=TunableReference(manager=services.get_instance_manager(sims4.resources.Types.STATISTIC), class_restrictions='RelationshipTrack', description='The bit track to key the Y axis off of.'), y_axis_content=TunableList(TunableTuple(bit_set=TunableRelationshipBitSet(description='The bit set representing the X axis in the matrix for this Y position.'), remove_value=Tunable(float, -100, description='Track score value for the bit to be removed.'), add_value=Tunable(float, 100, description='Track score value for the bit to be added.'), description='A threshold for this node in the matrix along with a bit set.'), description='A list of bit sets and thresholds.  This represents the Y axis of the matrix.'), **kwargs)

    @staticmethod
    def _verify_tunable_callback(source, *_, y_axis_content, **__):
        TunableRelationshipBitData.verify_bit_data_gaps(y_axis_content, source)

class RelationshipTrackInstanceData2dLink(BaseRelationshipTrackInstanceData):
    __slots__ = ('_x_index', '_y_index', '_y_callback_handles', '_x_callback_handles')

    def __init__(self, track):
        super().__init__(track)
        self._x_index = -1
        self._y_index = -1
        self._y_callback_handles = None
        self._x_callback_handles = None

    def callback_listeners(self):
        return (self._y_callback_handles, self._x_callback_handles)

    def setup_callbacks(self):
        self._setup_y_callbacks()
        self._setup_x_callbacks()

    def _setup_y_callbacks(self, set_y_index=True):
        self._clear_y_callbacks()
        if set_y_index:
            self._y_index = self._get_y_axis_index()
        y_track = self._get_y_track()
        self._y_callback_handles = self._setup_callback_listeners_for_track(self._y_index, self._track_data.bit_set_list, y_track, self._y_track_update_add_bit_callback, self._y_track_update_remove_bit_callback)

    def _clear_y_callbacks(self):
        if self._y_callback_handles is not None:
            y_track = self._get_y_track()
            for handle in self._y_callback_handles:
                if handle is not None:
                    y_track.remove_callback_listener(handle)
            self._y_callback_handles = None

    def get_active_bit(self):
        if self._y_index < 0 or self._x_index < 0:
            return
        return self._track_data.bit_set_list[self._y_index].bit_set[self._x_index].bit

    def get_active_bit_by_value(self):
        y_track = self._track.tracker.get_statistic(self._track_data._y_axis_track)
        x_track = self._track
        if y_track is None or x_track is None:
            return
        y_index = BaseRelationshipTrackData.find_add_value_score_index(self._track_data.bit_set_list_add_values, y_track.get_value(), self)
        x_index = BaseRelationshipTrackData.find_add_value_score_index(self._get_x_bit_list_add_values(), x_track.get_value(), self)
        if y_index < 0 or x_index < 0:
            return
        return self._track_data.bit_set_list[y_index].bit_set[x_index].bit

    def request_full_update(self):
        self._full_y_update()
        return self._full_x_update()

    def full_load_update(self, relationship):
        if self._y_index != -1:
            current_bit_set = self._track_data.bit_set_list[self._y_index]
            potential_x_index = BaseRelationshipTrackData.find_add_value_score_index(current_bit_set.bit_list_add_values, self._track.get_value(), self)
            current_node = current_bit_set.bit_set[potential_x_index]
            if relationship.has_bit(relationship.sim_id_a, current_node.bit):
                self._x_index = potential_x_index
                self._setup_y_callbacks(set_y_index=False)
                self._setup_x_callbacks()
                return
        for (i, y_track_bit) in enumerate(self._track_data.bit_set_list):
            for (j, x_track) in enumerate(y_track_bit.bit_set):
                if relationship.has_bit(relationship.sim_id_a, x_track.bit):
                    self._y_index = i
                    self._x_index = j
                    self._setup_y_callbacks(set_y_index=False)
                    self._setup_x_callbacks()
                    return

    def _get_y_track(self):
        return self._track.tracker.get_statistic(self._track_data.y_axis_track, True)

    def _get_y_axis_index(self):
        track_data = self._track_data
        score = self._track.tracker.get_value(track_data.y_axis_track)
        return BaseRelationshipTrackData.find_add_value_score_index(track_data.bit_set_list_add_values, score, self)

    def _get_x_bit_set(self):
        if self._y_index < 0:
            return
        return self._track_data.bit_set_list[self._y_index].bit_set

    def _get_x_bit_list_add_values(self):
        if self._y_index < 0:
            return
        return self._track_data.bit_set_list[self._y_index].bit_list_add_values

    def _setup_x_callbacks(self):
        self._clear_x_callbacks()
        x_bit_set = self._get_x_bit_set()
        if x_bit_set is not None:
            self._x_callback_handles = self._setup_callback_listeners_for_track(self._x_index, x_bit_set, self._track, self._x_track_update_add_bit_callback, self._x_track_update_remove_bit_callback)
        else:
            logger.error('x_bit_set is None for {}', self._track, owner='jjacobson')

    def _clear_x_callbacks(self):
        if self._x_callback_handles is not None:
            for handle in self._x_callback_handles:
                if handle is not None:
                    self._track.remove_callback_listener(handle)
            self._x_callback_handles = None

    def _update_y_track(self, remove_callback):
        y_track = self._get_y_track()
        track_data = self._track_data
        original_bit = self.get_active_bit()
        if self._y_index < 0:
            return self._full_y_update()
        original_node = track_data.bit_set_list[self._y_index]
        self._clear_y_callbacks()
        score = y_track.get_value()
        self._y_index = BaseRelationshipTrackData.find_add_value_score_index(track_data.bit_set_list_add_values, score, self)
        curr_node = track_data.bit_set_list[self._y_index]
        self._setup_y_callbacks()
        if curr_node == original_node:
            return (None, None)
        self._x_index = -1
        (_, new_bit) = self._full_x_update()
        if new_bit == original_bit:
            return (None, None)
        logger.debug('   Old bit: {}', original_bit)
        logger.debug('   New bit: {}', new_bit)
        return (original_bit, new_bit)

    def _full_y_update(self):
        self._clear_y_callbacks()
        track_data = self._track_data
        track = self._get_y_track()
        score = track.get_value()
        old_bit = self.get_active_bit()
        self._y_index = BaseRelationshipTrackData.find_add_value_score_index(track_data.bit_set_list_add_values, score, self)
        self._setup_y_callbacks()
        self._x_index = -1
        (_, new_bit) = self._full_x_update()
        logger.debug('Old bit: {}', old_bit)
        logger.debug('New bit: {}', new_bit)
        return (old_bit, new_bit)

    def _update_x_track(self, remove_callback):
        x_bit_set = self._get_x_bit_set()
        original_bit = self.get_active_bit()
        if self._x_index < 0:
            return self._full_x_update()
        original_node = x_bit_set[self._x_index]
        self._clear_x_callbacks()
        score = self._track.get_value()
        self._x_index = BaseRelationshipTrackData.find_add_value_score_index(self._get_x_bit_list_add_values(), score, self)
        curr_node = x_bit_set[self._x_index]
        self._setup_x_callbacks()
        if curr_node == original_node:
            return (None, None)
        new_bit = x_bit_set[self._x_index].bit
        logger.debug('   Old bit: {}', original_bit)
        logger.debug('   New bit: {}', new_bit)
        return (original_bit, new_bit)

    def _full_x_update(self):
        self._clear_x_callbacks()
        score = self._track.get_value()
        old_bit = self.get_active_bit()
        bit_list_add_values = self._get_x_bit_list_add_values()
        self._x_index = BaseRelationshipTrackData.find_add_value_score_index(bit_list_add_values, score, self._track)
        self._setup_x_callbacks()
        new_bit = None
        if self._x_index >= 0:
            new_bit = self.get_active_bit()
        else:
            logger.warn("There's a hole in RelationshipTrack: {}", self._track, owner='jjacobson')
        return (old_bit, new_bit)

    def _x_track_update_add_bit_callback(self, _):
        (bit_to_remove, bit_to_add) = self._update_x_track(False)
        self._apply_bit_change(bit_to_remove, bit_to_add)

    def _x_track_update_remove_bit_callback(self, _):
        (bit_to_remove, bit_to_add) = self._update_x_track(True)
        self._apply_bit_change(bit_to_remove, bit_to_add)

    def _y_track_update_add_bit_callback(self, _):
        (bit_to_remove, bit_to_add) = self._update_y_track(False)
        self._apply_bit_change(bit_to_remove, bit_to_add)

    def _y_track_update_remove_bit_callback(self, _):
        (bit_to_remove, bit_to_add) = self._update_y_track(True)
        self._apply_bit_change(bit_to_remove, bit_to_add)
