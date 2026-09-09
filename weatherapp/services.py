from __future__ import annotations

import os
from datetime import datetime
from typing import Any

import requests
from django.conf import settings

OPENWEATHER_BASE_URL = "https://api.openweathermap.org/data/2.5"


AQI_LEVELS = {
    1: {"label": "Good", "description": "Air quality is satisfactory and air pollution poses little or no risk."},
    2: {"label": "Fair", "description": "Air quality is acceptable; some pollutants may slightly affect sensitive groups."},
    3: {"label": "Moderate", "description": "Air quality is moderate; sensitive groups should limit prolonged outdoor exertion."},
    4: {"label": "Poor", "description": "Air quality is poor; reduce time outdoors and avoid strenuous activities."},
    5: {"label": "Very Poor", "description": "Air quality is very poor; health risks are significant for everyone."},
}


def sanitize_city(city: str) -> str:
    return " ".join((city or "").strip().split())


def _get_api_key() -> str:
    api_key = getattr(settings, "OPENWEATHER_API_KEY", "") or os.getenv("OPENWEATHER_API_KEY", "")
    if not api_key:
        raise RuntimeError(
            "OpenWeatherMap API key is not configured. Add OPENWEATHER_API_KEY to your environment."
        )
    return api_key


def _parse_coordinate(value: str, name: str) -> float:
    try:
        coordinate = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"Invalid {name}. Please try again.") from exc

    if name == "latitude" and not -90 <= coordinate <= 90:
        raise ValueError("Latitude must be between -90 and 90.")
    if name == "longitude" and not -180 <= coordinate <= 180:
        raise ValueError("Longitude must be between -180 and 180.")

    return coordinate


def build_hourly_forecasts(forecast_items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    hourly_forecasts = []
    for item in forecast_items[:8]:
        hourly_forecasts.append(
            {
                "time": datetime.fromtimestamp(item["dt"]).strftime("%H:%M"),
                "temp": round(item["main"]["temp"]),
                "icon": item["weather"][0]["icon"],
                "description": item["weather"][0]["description"],
            }
        )
    return hourly_forecasts


def build_daily_forecasts(forecast_items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[str, dict[str, Any]] = {}

    for item in forecast_items:
        date = datetime.fromtimestamp(item["dt"])
        day_key = date.strftime("%Y-%m-%d")

        if day_key not in grouped:
            grouped[day_key] = {
                "day": date.strftime("%a"),
                "date": date.strftime("%b %d"),
                "raw_date": item["dt"],
                "temp": round(item["main"]["temp"]),
                "temp_min": round(item["main"]["temp_min"]),
                "temp_max": round(item["main"]["temp_max"]),
                "icon": item["weather"][0]["icon"],
                "description": item["weather"][0]["description"],
            }
        else:
            grouped[day_key]["temp_min"] = min(grouped[day_key]["temp_min"], round(item["main"]["temp_min"]))
            grouped[day_key]["temp_max"] = max(grouped[day_key]["temp_max"], round(item["main"]["temp_max"]))

    sorted_days = sorted(grouped.values(), key=lambda entry: entry["raw_date"])
    return sorted_days[:7]


def _build_current_weather(current_data: dict[str, Any]) -> dict[str, Any]:
    coord = current_data.get("coord", {})

    return {
        "city": current_data["name"],
        "country": current_data["sys"]["country"],
        "temperature": round(current_data["main"]["temp"]),
        "description": current_data["weather"][0]["description"],
        "icon": current_data["weather"][0]["icon"],
        "humidity": current_data["main"]["humidity"],
        "pressure": current_data["main"]["pressure"],
        "wind_speed": current_data["wind"]["speed"],
        "feels_like": round(current_data["main"]["feels_like"]),
        "temp_min": round(current_data["main"]["temp_min"]),
        "temp_max": round(current_data["main"]["temp_max"]),
        "visibility": current_data.get("visibility", 0) / 1000,
        "sunrise": datetime.fromtimestamp(current_data["sys"]["sunrise"]).strftime("%I:%M %p"),
        "sunset": datetime.fromtimestamp(current_data["sys"]["sunset"]).strftime("%I:%M %p"),
        "latitude": coord.get("lat"),
        "longitude": coord.get("lon"),
    }


def build_air_quality(air_data: dict[str, Any]) -> dict[str, Any] | None:
    items = air_data.get("list", [])
    if not items:
        return None

    aqi = items[0].get("main", {}).get("aqi", 1)
    components = items[0].get("components", {})
    config = AQI_LEVELS.get(aqi, AQI_LEVELS[1])

    return {
        "aqi": aqi,
        "label": config["label"],
        "description": config["description"],
        "pm2_5": round(components.get("pm2_5", 0)),
        "pm10": round(components.get("pm10", 0)),
        "no2": round(components.get("no2", 0)),
    }


def _fetch_json(url: str, error_message: str) -> dict[str, Any]:
    try:
        response = requests.get(url, timeout=10)
        data = response.json()
    except requests.RequestException as exc:
        raise RuntimeError(error_message) from exc

    if response.status_code != 200:
        message = data.get("message", "Unable to load weather data.") if isinstance(data, dict) else "Unable to load weather data."
        raise ValueError(message)

    return data


def fetch_weather_for_city(city: str) -> tuple[dict[str, Any], dict[str, Any]]:
    clean_city = sanitize_city(city)

    if not clean_city:
        raise ValueError("Please enter a city name.")

    api_key = _get_api_key()

    current_url = f"{OPENWEATHER_BASE_URL}/weather?q={clean_city}&appid={api_key}&units=metric"
    forecast_url = f"{OPENWEATHER_BASE_URL}/forecast?q={clean_city}&appid={api_key}&units=metric"

    current_data = _fetch_json(current_url, "Unable to connect to the weather service right now. Please try again later.")
    forecast_json = _fetch_json(forecast_url, "Unable to fetch the forecast right now. Please try again later.")

    weather_data = _build_current_weather(current_data)
    forecast_data = {
        "hourly": build_hourly_forecasts(forecast_json.get("list", [])),
        "daily": build_daily_forecasts(forecast_json.get("list", [])),
    }

    return weather_data, forecast_data


def fetch_weather_for_coordinates(latitude: float | str, longitude: float | str) -> tuple[dict[str, Any], dict[str, Any]]:
    lat = _parse_coordinate(latitude, "latitude")
    lon = _parse_coordinate(longitude, "longitude")

    api_key = _get_api_key()

    current_url = f"{OPENWEATHER_BASE_URL}/weather?lat={lat}&lon={lon}&appid={api_key}&units=metric"
    forecast_url = f"{OPENWEATHER_BASE_URL}/forecast?lat={lat}&lon={lon}&appid={api_key}&units=metric"

    current_data = _fetch_json(current_url, "Unable to connect to the weather service right now. Please try again later.")
    forecast_json = _fetch_json(forecast_url, "Unable to fetch the forecast right now. Please try again later.")

    weather_data = _build_current_weather(current_data)
    forecast_data = {
        "hourly": build_hourly_forecasts(forecast_json.get("list", [])),
        "daily": build_daily_forecasts(forecast_json.get("list", [])),
    }

    return weather_data, forecast_data


def fetch_air_quality(latitude: float | str, longitude: float | str) -> dict[str, Any] | None:
    lat = _parse_coordinate(latitude, "latitude")
    lon = _parse_coordinate(longitude, "longitude")

    api_key = _get_api_key()
    air_url = f"{OPENWEATHER_BASE_URL}/air_pollution?lat={lat}&lon={lon}&appid={api_key}"

    air_data = _fetch_json(air_url, "Unable to load air quality data right now. Please try again later.")
    return build_air_quality(air_data)
