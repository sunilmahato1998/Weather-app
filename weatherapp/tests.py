from unittest import mock

from django.test import TestCase

from weatherapp.services import (
    _build_current_weather,
    build_air_quality,
    build_daily_forecasts,
    build_hourly_forecasts,
    sanitize_city,
)


class WeatherServicesTests(TestCase):
    def test_sanitize_city_removes_extra_spaces(self):
        self.assertEqual(sanitize_city("   delhi   city   "), "delhi city")

    def test_sanitize_city_rejects_numeric_input(self):
        with self.assertRaises(ValueError):
            sanitize_city("1234")

    def test_build_hourly_forecasts_limits_to_eight_items(self):
        items = [
            {"dt": 1710000000, "main": {"temp": 28.5}, "weather": [{"icon": "01d", "description": "clear sky"}]},
            {"dt": 1710003600, "main": {"temp": 29.1}, "weather": [{"icon": "02d", "description": "few clouds"}]},
        ]

        result = build_hourly_forecasts(items * 5)
        self.assertEqual(len(result), 8)

    def test_build_daily_forecasts_groups_by_day_and_tracks_min_max(self):
        items = [
            {
                "dt": 1710000000,
                "main": {"temp": 24.0, "temp_min": 18.0, "temp_max": 27.0},
                "weather": [{"icon": "02d", "description": "few clouds"}],
            },
            {
                "dt": 1710003600,
                "main": {"temp": 25.5, "temp_min": 19.0, "temp_max": 29.0},
                "weather": [{"icon": "03d", "description": "scattered clouds"}],
            },
        ]

        result = build_daily_forecasts(items)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["temp_min"], 18)
        self.assertEqual(result[0]["temp_max"], 29)

    def test_build_current_weather_includes_coordinates(self):
        current_data = {
            "name": "Delhi",
            "sys": {"country": "IN", "sunrise": 1710000000, "sunset": 1710003600},
            "main": {"temp": 30, "temp_min": 26, "temp_max": 32, "feels_like": 31, "humidity": 60, "pressure": 1010},
            "weather": [{"icon": "01d", "description": "clear sky"}],
            "wind": {"speed": 3.2},
            "visibility": 10000,
            "coord": {"lat": 28.6139, "lon": 77.2090},
        }

        result = _build_current_weather(current_data)
        self.assertEqual(result["latitude"], 28.6139)
        self.assertEqual(result["longitude"], 77.209)

    def test_build_air_quality_formats_data(self):
        air_data = {
            "list": [{
                "main": {"aqi": 2},
                "components": {"pm2_5": 12.4, "pm10": 20.1, "no2": 17.5},
            }]
        }

        result = build_air_quality(air_data)
        self.assertEqual(result["label"], "Fair")
        self.assertEqual(result["pm2_5"], 12)

    @mock.patch("weatherapp.views.fetch_air_quality")
    @mock.patch("weatherapp.views.fetch_weather_for_coordinates")
    def test_home_uses_coordinates_when_city_is_empty(self, mock_fetch_weather_for_coordinates, mock_fetch_air_quality):
        mock_fetch_weather_for_coordinates.return_value = (
            {
                "city": "Current Location",
                "country": "IN",
                "temperature": 29,
                "description": "clear sky",
                "icon": "01d",
                "humidity": 50,
                "pressure": 1010,
                "wind_speed": 2.1,
                "feels_like": 30,
                "temp_min": 27,
                "temp_max": 32,
                "visibility": 10,
                "sunrise": "06:00 AM",
                "sunset": "06:30 PM",
                "latitude": 12.34,
                "longitude": 56.78,
            },
            {"hourly": [], "daily": []},
        )
        mock_fetch_air_quality.return_value = {
            "aqi": 1,
            "label": "Good",
            "description": "Air quality is satisfactory.",
            "pm2_5": 5,
            "pm10": 10,
            "no2": 12,
        }

        response = self.client.post("/", {"city": "", "lat": "12.34", "lon": "56.78"})

        self.assertEqual(response.status_code, 200)
        self.assertIsNone(response.context["error"])
        mock_fetch_weather_for_coordinates.assert_called_once_with("12.34", "56.78")
        mock_fetch_air_quality.assert_called_once_with("12.34", "56.78")
