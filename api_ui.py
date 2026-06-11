import requests
import threading


class APIClient:
    def __init__(self, base_url="http://localhost:8080", timeout=10):
        self.base_url = base_url
        self.timeout = timeout

    def health(self):
        try:
            r = requests.get(
                f"{self.base_url}/health",
                timeout=self.timeout
            )
            return r.json()
        except Exception as e:
            print("Health error:", e)
            return None
        
    def get_style(self, style_id: int):
        try:
            r = requests.get(
                f"{self.base_url}/styles/{style_id}",
                timeout=self.timeout
            )
            return r.json()
        except Exception as e:
            print("Style error:", e)
            return None
        
    def get_route(self, start_lat, start_lon, end_lat, end_lon):
        try:
            r = requests.post(
                f"{self.base_url}/route-map",
                json={
                    "start_lat": start_lat,
                    "start_lon": start_lon,
                    "end_lat": end_lat,
                    "end_lon": end_lon,
                    "routing_type": "fastest",
                    "style_id": 1
                },
                timeout=self.timeout
            )
            return r.json()
        except Exception as e:
            print("Route error:", e)
            return None
        

    def save_location(self, lat, lon, accuracy=1.0):
        try:
            r = requests.post(
                f"{self.base_url}/location",
                json={
                    "latitude": lat,
                    "longitude": lon,
                    "accuracy": accuracy,
                    "timestamp": "now"
                },
                timeout=self.timeout
            )
            return r.json()
        except Exception as e:
            print("Location save error:", e)
            return None
        
    def get_latest_location(self):
        try:
            r = requests.get(
                f"{self.base_url}/location/latest",
                timeout=self.timeout
            )
            return r.json()
        except Exception as e:
            print("Latest location error:", e)
            return None
        
    def get_places_in_area(self, lat, lon, size="medium"):
        try:
            r = requests.post(
                f"{self.base_url}/places-in-area",
                json={
                    "center_lat": lat,
                    "center_lon": lon,
                    "size": size,
                    "shape": "circle"
                },
                timeout=self.timeout
            )
            return r.json()
        except Exception as e:
            print("Places error:", e)
            return None
        
    def run_async(self, func, callback):
        def wrapper():
            result = func()
            callback(result)

        threading.Thread(target=wrapper, daemon=True).start()
    