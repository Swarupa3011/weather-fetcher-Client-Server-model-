import socket
import requests
import json
from datetime import datetime
import threading
import logging
from config import API_KEY

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    filename='weather_server.log'
)

def save_recent(city):
    """Save recently searched cities with proper format handling"""
    try:
        with open('recent.json', 'r') as f:
            recent = json.load(f)
            # Convert old format to new format if needed
            if recent and isinstance(recent[0], str):
                recent = [{"city": c, "timestamp": datetime.now().isoformat()} for c in recent]
    except (FileNotFoundError, json.JSONDecodeError):
        recent = []

    # Remove if already exists (case insensitive)
    recent = [item for item in recent if item['city'].lower() != city.lower()]
    
    # Add new entry
    recent.insert(0, {
        'city': city,
        'timestamp': datetime.now().isoformat()
    })
    
    # Keep only last 5 searches
    recent = recent[:5]

    with open('recent.json', 'w') as f:
        json.dump(recent, f, indent=2)

def get_weather_data(city):
    """Fetch weather data from OpenWeatherMap API"""
    try:
        current_url = f"http://api.openweathermap.org/data/2.5/weather?q={city}&appid={API_KEY}&units=metric"
        forecast_url = f"http://api.openweathermap.org/data/2.5/forecast?q={city}&appid={API_KEY}&units=metric"

        with requests.Session() as session:
            current_res = session.get(current_url, timeout=10)
            forecast_res = session.get(forecast_url, timeout=10)

        if current_res.status_code != 200 or forecast_res.status_code != 200:
            error_msg = current_res.json().get('message', 'Unknown error')
            return {"error": f"City not found: {error_msg}"}

        current = current_res.json()
        forecast = forecast_res.json()

        # Process current weather
        current_weather = {
            "city": current["name"],
            "country": current.get("sys", {}).get("country", ""),
            "temperature": current["main"]["temp"],
            "feels_like": current["main"]["feels_like"],
            "description": current["weather"][0]["description"].title(),
            "humidity": current["main"]["humidity"],
            "wind_speed": current["wind"]["speed"],
            "pressure": current["main"]["pressure"],
            "icon": current["weather"][0]["icon"],
            "sunrise": datetime.fromtimestamp(current["sys"]["sunrise"]).strftime('%H:%M'),
            "sunset": datetime.fromtimestamp(current["sys"]["sunset"]).strftime('%H:%M')
        }

        # Process forecast data
        forecast_data = []
        for i in range(0, 40, 8):  # Every 24 hours (8 * 3-hour steps)
            item = forecast["list"][i]
            forecast_data.append({
                "date": item["dt_txt"].split()[0],
                "day": datetime.strptime(item["dt_txt"].split()[0], '%Y-%m-%d').strftime('%A'),
                "temp": item["main"]["temp"],
                "feels_like": item["main"]["feels_like"],
                "desc": item["weather"][0]["description"].title(),
                "humidity": item["main"]["humidity"],
                "wind_speed": item["wind"]["speed"],
                "icon": item["weather"][0]["icon"]
            })

        save_recent(city)
        return {"current": current_weather, "forecast": forecast_data}

    except requests.exceptions.RequestException as e:
        logging.error(f"API request failed: {str(e)}")
        return {"error": "Failed to connect to weather service"}
    except Exception as e:
        logging.error(f"Unexpected error: {str(e)}")
        return {"error": "An unexpected error occurred"}

def handle_client(client_socket):
    """Handle client connection in a separate thread"""
    try:
        city = client_socket.recv(1024).decode().strip()
        if not city:
            return
            
        logging.info(f"Processing request for: {city}")
        result = get_weather_data(city)
        client_socket.send(json.dumps(result).encode())
    except Exception as e:
        logging.error(f"Client handling error: {str(e)}")
    finally:
        client_socket.close()

def start_server():
    """Start the weather server"""
    host = '127.0.0.1'
    port = 12346
    
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind((host, port))
    server.listen(5)
    
    logging.info(f"Weather server running at {host}:{port}")
    print(f"Server running at {host}:{port}")

    try:
        while True:
            client_socket, addr = server.accept()
            logging.info(f"Connection from {addr}")
            client_thread = threading.Thread(
                target=handle_client,
                args=(client_socket,),
                daemon=True
            )
            client_thread.start()
    except KeyboardInterrupt:
        logging.info("Server shutting down...")
    finally:
        server.close()

if __name__ == "__main__":
    start_server()