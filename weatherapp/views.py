from django.shortcuts import render
import requests

def home(request):
    weather_data = None

    if request.method == "POST":
        city = request.POST.get('city')

        # Your actual API key
        api_key = "3f978ddd1b3f9501f27a258b376be7e9"
        url = f"https://api.openweathermap.org/data/2.5/weather?q={city}&appid={api_key}&units=metric"

        response = requests.get(url).json()

        if response.get('cod') == 200:
            weather_data = {
                'city': city,
                'temperature': response['main']['temp'],
                'description': response['weather'][0]['description'],
                'humidity': response['main']['humidity'],
                'wind': response['wind']['speed'],
                'icon': response['weather'][0]['icon'],

            }
        else:
            weather_data = {"error": "City not found"}

    return render(request, "weatherapp/weather.html", {'weather': weather_data})

