from protocolbuffers import WeatherSeasons_pb2from sims4.gsi.dispatcher import GsiHandlerfrom sims4.gsi.schema import GsiGridSchemaimport servicesweather_data_schema = GsiGridSchema(label='Weather Data')weather_data_schema.add_field('title', label='Title')weather_data_schema.add_field('value', label='Value')
@GsiHandler('weather_data_view', weather_data_schema)
def generate_weather_data_view_data():
    weather_service = services.weather_service()
    weather_data = []
    if weather_service is not None:
        entry = {'title': 'Current Forecast', 'value': str(weather_service._forecasts[0])}
        weather_data.append(entry)
        entry = {'title': 'Current Event', 'value': str(weather_service._current_event)}
        weather_data.append(entry)
        entry = {'title': 'Current WeatherTypes', 'value': str(weather_service._current_weather_types)}
        weather_data.append(entry)
        for key in weather_service._trans_info:
            entry = {'title': 'Element: {}'.format(str(WeatherSeasons_pb2._SEASONWEATHERINTERPOLATIONMESSAGE_SEASONWEATHERINTERPOLATEDTYPE.values_by_number[key].name)), 'value': str(weather_service.get_weather_element_value(key))}
            weather_data.append(entry)
    return weather_data
