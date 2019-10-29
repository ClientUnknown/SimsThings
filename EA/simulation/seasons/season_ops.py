from _sims4_collections import frozendictfrom protocolbuffers import DistributorOps_pb2, UI_pb2, WeatherSeasons_pb2from distributor.ops import Opfrom distributor.rollback import ProtocolBufferRollbackfrom seasons.seasons_enums import SeasonTypeimport date_and_timeSTART_SEASON_VALUES = frozendict({SeasonType.SPRING: 2.5, SeasonType.WINTER: 1.5, SeasonType.FALL: 0.5, SeasonType.SUMMER: 3.5})MAX_SEASON_INTERPOLATE_VALUE = 4.0
class SeasonInterpolationOp(Op):

    def __init__(self, season_type, season_content, mid_season_op=False):
        super().__init__()
        self.op = WeatherSeasons_pb2.SeasonWeatherInterpolations()
        with ProtocolBufferRollback(self.op.season_weather_interlops) as season_interlop:
            season_interlop.message_type = WeatherSeasons_pb2.SeasonWeatherInterpolationMessage.SEASON
            if mid_season_op:
                season_interlop.start_value = season_type.value
                season_interlop.end_value = season_type.value + 1
                start_time = season_content.midpoint_time
                season_interlop.start_time = int(start_time/date_and_time.REAL_MILLISECONDS_PER_SIM_SECOND)
                season_interlop.end_time = int((start_time + season_content.length)/date_and_time.REAL_MILLISECONDS_PER_SIM_SECOND)
            else:
                start_value = START_SEASON_VALUES[season_type]
                season_interlop.start_value = start_value
                season_interlop.end_value = start_value + 1
                season_interlop.start_time = int(season_content.start_time/date_and_time.REAL_MILLISECONDS_PER_SIM_SECOND)
                season_interlop.end_time = int(season_content.end_time/date_and_time.REAL_MILLISECONDS_PER_SIM_SECOND)

    @property
    def content(self):
        if self.op.season_weather_interlops:
            return str(self.op.season_weather_interlops[0])
        return ''

    def write(self, msg):
        msg.type = DistributorOps_pb2.Operation.SEASON_WEATHER_INTERPOLATIONS
        msg.data = self.op.SerializeToString()

class CrossSeasonInterpolationOp(Op):

    def __init__(self, start_season, percent_into_start_season, start_time, end_season, percent_into_end_season, end_time):
        super().__init__()
        self.op = WeatherSeasons_pb2.SeasonWeatherInterpolations()
        with ProtocolBufferRollback(self.op.season_weather_interlops) as season_interlop:
            season_interlop.message_type = WeatherSeasons_pb2.SeasonWeatherInterpolationMessage.SEASON
            start_value = START_SEASON_VALUES[start_season] + percent_into_start_season
            end_value = START_SEASON_VALUES[end_season] + percent_into_end_season
            if end_value < start_value:
                end_value = end_value + MAX_SEASON_INTERPOLATE_VALUE
            season_interlop.start_value = start_value
            season_interlop.end_value = end_value
            season_interlop.start_time = int(start_time/date_and_time.REAL_MILLISECONDS_PER_SIM_SECOND)
            season_interlop.end_time = int(end_time/date_and_time.REAL_MILLISECONDS_PER_SIM_SECOND)
        self._is_over_half = end_value - start_value > MAX_SEASON_INTERPOLATE_VALUE/2.0

    @property
    def is_over_half(self):
        return self._is_over_half

    def write(self, msg):
        msg.type = DistributorOps_pb2.Operation.SEASON_WEATHER_INTERPOLATIONS
        msg.data = self.op.SerializeToString()

class SeasonUpdateOp(Op):

    def __init__(self, season_type, season_content):
        super().__init__()
        self.op = UI_pb2.SeasonUpdate()
        self.op.season_type = season_type.value
        self.op.season_guid = season_content.guid64
        self.op.season_start_time = season_content.start_time

    @property
    def content(self):
        return str(self.op)

    def write(self, msg):
        msg.type = DistributorOps_pb2.Operation.SEASON_UPDATE
        msg.data = self.op.SerializeToString()

class SeasonParameterUpdateOp(Op):

    def __init__(self, parameter, start_value, start_time, end_value, end_time):
        super().__init__()
        self.op = WeatherSeasons_pb2.SeasonWeatherInterpolations()
        with ProtocolBufferRollback(self.op.season_weather_interlops) as season_interlop:
            season_interlop.message_type = parameter
            season_interlop.start_value = start_value
            season_interlop.start_time = int(start_time/date_and_time.REAL_MILLISECONDS_PER_SIM_SECOND)
            season_interlop.end_value = end_value
            season_interlop.end_time = int(end_time/date_and_time.REAL_MILLISECONDS_PER_SIM_SECOND)

    @property
    def content(self):
        if self.op.season_weather_interlops:
            return str(self.op.season_weather_interlops[0])
        return ''

    def write(self, msg):
        msg.type = DistributorOps_pb2.Operation.SEASON_WEATHER_INTERPOLATIONS
        msg.data = self.op.SerializeToString()
