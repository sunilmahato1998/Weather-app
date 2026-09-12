from django.shortcuts import render

from .services import (
    fetch_air_quality,
    fetch_weather_for_city,
    fetch_weather_for_coordinates,
    sanitize_city,
)


def home(request):
    weather_data = None
    forecast_data = None
    air_quality = None
    error_message = None

    if request.method == "POST":
        city = request.POST.get("city", "")
        latitude = request.POST.get("lat")
        longitude = request.POST.get("lon")

        try:
            city = sanitize_city(city)

            if latitude and longitude:
                weather_data, forecast_data = fetch_weather_for_coordinates(latitude, longitude)
                air_quality = fetch_air_quality(latitude, longitude)
            elif city:
                weather_data, forecast_data = fetch_weather_for_city(city)
                if weather_data.get("latitude") is not None and weather_data.get("longitude") is not None:
                    air_quality = fetch_air_quality(weather_data["latitude"], weather_data["longitude"])
            else:
                error_message = "Please enter a city name."
        except ValueError as exc:
            error_message = str(exc)
        except RuntimeError as exc:
            error_message = str(exc)
        except Exception:
            error_message = "Something went wrong while loading weather data. Please try again."

    context = {
        "weather": weather_data,
        "forecast": forecast_data,
        "air_quality": air_quality,
        "error": error_message,
    }
    return render(request, "weatherapp/weather.html", context)