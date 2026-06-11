import requests
from typing import Optional, List, Dict
from datetime import datetime

class MapsAPIClient:
    #Клиент для взаимодействия с Maps API
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.session = requests.Session()

    def get_styles(self) -> Optional[List[Dict]]:
        #Получить список всех стилей карт
        try:
            response = self.session.get(f"{self.base_url}/styles")
            response.raise_for_status()
            return response.json().get('items', [])
        except requests.RequestException as e:
            print(f"Ошибка получения стилей: {e}")
            return None

    def get_style(self, style_id: int) -> Optional[Dict]:
        #Получить конкретный стиль по ID
        try:
            response = self.session.get(f"{self.base_url}/styles/{style_id}")
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            print(f"Ошибка получения стиля {style_id}: {e}")
            return None

    def get_tile_url(self, z: int, x: int, y: int) -> str:
        #Получить URL векторного тайла
        return f"{self.base_url}/tiles/{z}/{x}/{y}.mvt"

    def get_map_with_route(
            self,
            start_lat: float,
            start_lon: float,
            end_lat: float,
            end_lon: float,
            routing_type: str = "fastest",
            style_id: int = 1
    ) -> Optional[Dict]:
        #Получить карту с маршрутом
        try:
            params = {
                "start_lat": start_lat,
                "start_lon": start_lon,
                "end_lat": end_lat,
                "end_lon": end_lon,
                "routing_type": routing_type,
                "style_id": style_id
            }
            response = self.session.get(
                f"{self.base_url}/map-with-route",
                params=params
            )
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            print(f"Ошибка получения маршрута: {e}")
            return None

    def save_location(
            self,
            latitude: float,
            longitude: float,
            accuracy: float,
            altitude: Optional[float] = None,
            speed: Optional[float] = None
    ) -> Optional[Dict]:
        #Сохранить GPS координаты
        try:
            data = {
                "latitude": latitude,
                "longitude": longitude,
                "accuracy": accuracy,
                "altitude": altitude,
                "speed": speed,
                "timestamp": datetime.now().isoformat()
            }
            response = self.session.post(
                f"{self.base_url}/location",
                json=data
            )
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            print(f"Ошибка сохранения локации: {e}")
            return None

    def get_location_history(
            self,
            limit: int = 100,
            offset: int = 0
    ) -> Optional[List[Dict]]:
        #Получить историю локаций
        try:
            params = {"limit": limit, "offset": offset}
            response = self.session.get(
                f"{self.base_url}/location/history",
                params=params
            )
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            print(f"Ошибка получения истории: {e}")
            return None

    def health_check(self) -> Optional[Dict]:
        #Проверить состояние API
        try:
            response = self.session.get(f"{self.base_url}/health")
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            print(f"API недоступен: {e}")
            return None

    def close(self):
        #Закрыть сессию
        self.session.close()