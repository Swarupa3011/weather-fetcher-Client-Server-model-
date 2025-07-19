import socket
import json
import tkinter as tk
from tkinter import ttk, messagebox
from PIL import Image, ImageTk
import io
import requests
from datetime import datetime

class WeatherApp:
    def __init__(self, root):
        self.root = root
        self.root.title("🌦️ Weather Forecast")
        self.root.geometry("800x700")
        self.configure_styles()
        self.create_widgets()
        self.recent_searches = self.load_recent_searches()
        self.update_recent_listbox()

    def configure_styles(self):
        self.style = ttk.Style()
        self.style.configure('TFrame', background='#f0f0f0')
        self.style.configure('TLabel', background='#f0f0f0', font=('Helvetica', 10))
        self.style.configure('Header.TLabel', font=('Helvetica', 14, 'bold'))
        self.style.configure('Temp.TLabel', font=('Helvetica', 24, 'bold'))
        self.style.configure('TButton', font=('Helvetica', 10))

    def create_widgets(self):
        # Main container
        self.main_frame = ttk.Frame(self.root, padding="10")
        self.main_frame.pack(fill=tk.BOTH, expand=True)

        # Search section
        search_frame = ttk.Frame(self.main_frame)
        search_frame.pack(fill=tk.X, pady=5)

        ttk.Label(search_frame, text="Enter City:").pack(side=tk.LEFT, padx=5)
        
        self.city_entry = ttk.Entry(search_frame, width=30, font=('Helvetica', 12))
        self.city_entry.pack(side=tk.LEFT, padx=5, expand=True, fill=tk.X)
        self.city_entry.bind('<Return>', lambda e: self.get_weather())
        
        search_btn = ttk.Button(search_frame, text="Search", command=self.get_weather)
        search_btn.pack(side=tk.LEFT, padx=5)

        # Recent searches
        recent_frame = ttk.LabelFrame(self.main_frame, text="Recent Searches", padding=5)
        recent_frame.pack(fill=tk.X, pady=5)
        
        self.recent_listbox = tk.Listbox(
            recent_frame, 
            height=4, 
            font=('Helvetica', 10),
            selectbackground='#4a90d9',
            selectforeground='white'
        )
        self.recent_listbox.pack(fill=tk.BOTH, expand=True)
        self.recent_listbox.bind('<<ListboxSelect>>', self.on_recent_select)

        # Current weather display
        self.current_frame = ttk.LabelFrame(self.main_frame, text="Current Weather", padding=10)
        self.current_frame.pack(fill=tk.BOTH, expand=True, pady=5)

        # Forecast display
        forecast_frame = ttk.LabelFrame(self.main_frame, text="5-Day Forecast", padding=10)
        forecast_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        
        self.forecast_canvas = tk.Canvas(forecast_frame, background='#f0f0f0')
        self.scrollbar = ttk.Scrollbar(
            forecast_frame, 
            orient="horizontal", 
            command=self.forecast_canvas.xview
        )
        self.forecast_canvas.configure(xscrollcommand=self.scrollbar.set)
        
        self.scrollbar.pack(side=tk.BOTTOM, fill=tk.X)
        self.forecast_canvas.pack(side=tk.TOP, fill=tk.BOTH, expand=True)
        
        self.forecast_inner_frame = ttk.Frame(self.forecast_canvas)
        self.forecast_canvas.create_window((0, 0), window=self.forecast_inner_frame, anchor="nw")
        
        self.forecast_inner_frame.bind(
            "<Configure>",
            lambda e: self.forecast_canvas.configure(
                scrollregion=self.forecast_canvas.bbox("all")
            )
        )

        # Status bar
        self.status_var = tk.StringVar()
        self.status_bar = ttk.Label(
            self.main_frame, 
            textvariable=self.status_var,
            relief=tk.SUNKEN,
            anchor=tk.W
        )
        self.status_bar.pack(fill=tk.X, pady=(5, 0))

    def load_recent_searches(self):
        """Load recent searches with proper error handling"""
        try:
            with open("recent.json", "r") as f:
                data = json.load(f)
                # Handle both old and new formats
                if data and isinstance(data[0], dict):
                    return [item['city'] for item in data]
                elif data and isinstance(data[0], str):
                    return data
                return []
        except (FileNotFoundError, json.JSONDecodeError):
            return []

    def update_recent_listbox(self):
        """Update the recent searches listbox"""
        self.recent_listbox.delete(0, tk.END)
        for city in self.recent_searches:
            self.recent_listbox.insert(tk.END, city)

    def on_recent_select(self, event):
        """Handle selection from recent searches"""
        if self.recent_listbox.curselection():
            selected = self.recent_listbox.get(self.recent_listbox.curselection())
            self.city_entry.delete(0, tk.END)
            self.city_entry.insert(0, selected)
            self.get_weather()

    def get_weather(self):
        """Get weather data from server"""
        city = self.city_entry.get().strip()
        if not city:
            messagebox.showerror("Error", "Please enter a city name")
            return
            
        self.status_var.set(f"Fetching weather for {city}...")
        self.root.update_idletasks()
        
        try:
            with socket.socket() as s:
                s.settimeout(10)
                s.connect(('127.0.0.1', 12346))
                s.send(city.encode())
                data = s.recv(8192).decode()
                
            weather_data = json.loads(data)
            
            if "error" in weather_data:
                messagebox.showerror("Error", weather_data["error"])
                self.status_var.set("Ready")
                return
                
            self.display_current_weather(weather_data["current"])
            self.display_forecast(weather_data["forecast"])
            
            # Update recent searches
            if city not in self.recent_searches:
                self.recent_searches.insert(0, city)
                if len(self.recent_searches) > 5:
                    self.recent_searches.pop()
                self.update_recent_listbox()
                
            self.status_var.set(f"Weather for {weather_data['current']['city']}, {weather_data['current'].get('country', '')}")
            
        except socket.error as e:
            messagebox.showerror("Connection Error", f"Could not connect to server: {str(e)}")
            self.status_var.set("Server connection failed")
        except json.JSONDecodeError:
            messagebox.showerror("Error", "Invalid response from server")
            self.status_var.set("Data error")
        except Exception as e:
            messagebox.showerror("Error", f"An unexpected error occurred: {str(e)}")
            self.status_var.set("Error occurred")

    def display_current_weather(self, current):
        """Display current weather information"""
        for widget in self.current_frame.winfo_children():
            widget.destroy()
        
        main_info_frame = ttk.Frame(self.current_frame)
        main_info_frame.pack(fill=tk.X, pady=5)
        
        # Weather icon
        try:
            icon_url = f"http://openweathermap.org/img/wn/{current['icon']}@4x.png"
            response = requests.get(icon_url, stream=True)
            img_data = response.content
            img = Image.open(io.BytesIO(img_data))
            photo = ImageTk.PhotoImage(img)
            
            icon_label = ttk.Label(main_info_frame, image=photo)
            icon_label.image = photo
            icon_label.pack(side=tk.LEFT, padx=10)
        except:
            pass
        
        # Temperature and description
        temp_frame = ttk.Frame(main_info_frame)
        temp_frame.pack(side=tk.LEFT, fill=tk.Y)
        
        ttk.Label(
            temp_frame, 
            text=f"{current['temperature']}°C", 
            style='Temp.TLabel'
        ).pack(anchor=tk.W)
        
        ttk.Label(
            temp_frame, 
            text=current['description'], 
            font=('Helvetica', 14)
        ).pack(anchor=tk.W)
        
        ttk.Label(
            temp_frame, 
            text=f"Feels like: {current['feels_like']}°C"
        ).pack(anchor=tk.W)
        
        # Additional details
        details_frame = ttk.Frame(main_info_frame)
        details_frame.pack(side=tk.RIGHT, fill=tk.Y, padx=20)
        
        details = [
            f"💧 Humidity: {current['humidity']}%",
            f"🌬️ Wind: {current['wind_speed']} m/s",
            f"📊 Pressure: {current['pressure']} hPa",
            f"🌅 Sunrise: {current['sunrise']}",
            f"🌇 Sunset: {current['sunset']}"
        ]
        
        for detail in details:
            ttk.Label(details_frame, text=detail).pack(anchor=tk.E)

    def display_forecast(self, forecast):
        """Display 5-day forecast"""
        for widget in self.forecast_inner_frame.winfo_children():
            widget.destroy()
        
        for day in forecast:
            card = ttk.Frame(
                self.forecast_inner_frame, 
                relief=tk.RAISED, 
                borderwidth=1, 
                padding=10
            )
            card.pack(side=tk.LEFT, fill=tk.Y, padx=5, pady=5)
            
            ttk.Label(
                card, 
                text=day['day'], 
                font=('Helvetica', 12, 'bold')
            ).pack()
            
            ttk.Label(card, text=day['date']).pack()
            
            try:
                icon_url = f"http://openweathermap.org/img/wn/{day['icon']}@2x.png"
                response = requests.get(icon_url, stream=True)
                img_data = response.content
                img = Image.open(io.BytesIO(img_data))
                img = img.resize((64, 64), Image.LANCZOS)
                photo = ImageTk.PhotoImage(img)
                
                icon_label = ttk.Label(card, image=photo)
                icon_label.image = photo
                icon_label.pack(pady=5)
            except:
                pass
            
            ttk.Label(
                card, 
                text=f"{day['temp']}°C", 
                font=('Helvetica', 14, 'bold')
            ).pack()
            
            ttk.Label(
                card, 
                text=f"Feels like: {day['feels_like']}°C"
            ).pack()
            
            ttk.Label(card, text=day['desc']).pack()
            
            ttk.Label(card, text=f"💧 {day['humidity']}%").pack()
            ttk.Label(card, text=f"🌬️ {day['wind_speed']} m/s").pack()

if __name__ == "__main__":
    root = tk.Tk()
    app = WeatherApp(root)
    root.mainloop()