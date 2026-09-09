from django.shortcuts import render
import requests
from datetime import datetime

def home(request):
    weather_data = None
    forecast_data = None
    error_message = None
    
    if request.method == "POST":
        city = request.POST.get('city')
        api_key = "3f978ddd1b3f9501f27a258b376be7e9"
        
        if city:
            try:
                current_url = f"https://api.openweathermap.org/data/2.5/weather?q={city}&appid={api_key}&units=metric"
                current_response = requests.get(current_url)
                current_data = current_response.json()
                
                if current_response.status_code == 200:
                    forecast_url = f"https://api.openweathermap.org/data/2.5/forecast?q={city}&appid={api_key}&units=metric"
                    forecast_response = requests.get(forecast_url)
                    forecast_json = forecast_response.json()
                    
                    weather_data = {
                        'city': current_data['name'],
                        'country': current_data['sys']['country'],
                        'temperature': round(current_data['main']['temp']),
                        'description': current_data['weather'][0]['description'],
                        'icon': current_data['weather'][0]['icon'],
                        'humidity': current_data['main']['humidity'],
                        'pressure': current_data['main']['pressure'],
                        'wind_speed': current_data['wind']['speed'],
                        'feels_like': round(current_data['main']['feels_like']),
                        'temp_min': round(current_data['main']['temp_min']),
                        'temp_max': round(current_data['main']['temp_max']),
                        'visibility': current_data.get('visibility', 0) / 1000,
                        'sunrise': datetime.fromtimestamp(current_data['sys']['sunrise']).strftime('%I:%M %p'),
                        'sunset': datetime.fromtimestamp(current_data['sys']['sunset']).strftime('%I:%M %p'),
                    }
                    
                    daily_forecasts = {}
                    hourly_forecasts = []
                    
                    for item in forecast_json['list'][:8]:
                        time = datetime.fromtimestamp(item['dt']).strftime('%H:%M')
                        hourly_forecasts.append({
                            'time': time,
                            'temp': round(item['main']['temp']),
                            'icon': item['weather'][0]['icon'],
                            'description': item['weather'][0]['description']
                        })
                    
                    for item in forecast_json['list']:
                        date = datetime.fromtimestamp(item['dt'])
                        day_key = date.strftime('%Y-%m-%d')
                        
                        if day_key not in daily_forecasts:
                            daily_forecasts[day_key] = {
                                'day': date.strftime('%a'),
                                'date': date.strftime('%b %d'),
                                'temp': round(item['main']['temp']),
                                'temp_min': round(item['main']['temp_min']),
                                'temp_max': round(item['main']['temp_max']),
                                'icon': item['weather'][0]['icon'],
                                'description': item['weather'][0]['description']
                            }
                    
                    forecast_data = {
                        'hourly': hourly_forecasts,
                        'daily': list(daily_forecasts.values())[:7]
                    }
                else:
                    error_message = 'City not found. Please try again.'
                    
            except Exception as e:
                error_message = f'Error fetching weather data: {str(e)}'
        else:
            error_message = 'Please enter a city name.'
    
    context = {
        'weather': weather_data,
        'forecast': forecast_data,
        'error': error_message,
    }
    return render(request, "weatherapp/weather.html", context)