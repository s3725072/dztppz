from fastapi import FastAPI, HTTPException, Request, Query, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from pydantic import BaseModel
from typing import Optional, Any
import httpx
import datetime
import logging
import asyncio
import math

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# URL сервисов за шлюзом
MAPS_API_URL       = "http://localhost:8000"
NAVIGATION_API_URL = "http://localhost:8001"
PLACES_API_URL     = "http://localhost:8002"
AREA_API_URL       = "http://localhost:8003"

# Таймауты
DEFAULT_TIMEOUT = 30.0
HEALTH_TIMEOUT = 5.0

app = FastAPI(
    title="API Gateway",
    description="Шлюз",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

http_client = httpx.AsyncClient(timeout=DEFAULT_TIMEOUT)


# Вспомогательные функции

async def proxy_request(
    base_url: str,
    path: str,
    method: str,
    body: Any = None,
    params: dict = None,
    headers: dict = None
):
    #Общий прокси-вызов к нижестоящему сервису.
    url = f"{base_url}{path}"
    clean_headers = {k: v for k, v in (headers or {}).items()
                     if k.lower() not in ("host", "content-length")}
    try:
        response = await http_client.request(
            method=method,
            url=url,
            json=body,
            params=params,
            headers=clean_headers
        )
        return response
    except httpx.ConnectError:
        raise HTTPException(status_code=503, detail=f"Сервис недоступен: {base_url}")
    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail=f"Таймаут сервиса: {base_url}")
    except httpx.HTTPError as e:
        raise HTTPException(status_code=502, detail=f"Ошибка шлюза: {str(e)}")


def make_response(upstream_response: httpx.Response) -> Response:
    #Преобразует ответ httpx в FastAPI Response.
    return Response(
        content=upstream_response.content,
        status_code=upstream_response.status_code,
        media_type=upstream_response.headers.get("content-type", "application/json")
    )

# Модели для агрегированных эндпоинтов

class LocationData(BaseModel):
    latitude: float
    longitude: float
    accuracy: float
    altitude: Optional[float] = None
    speed: Optional[float] = None
    timestamp: str  # ISO 8601


class RouteRequest(BaseModel):
    start_lat: float
    start_lon: float
    end_lat: float
    end_lon: float
    routing_type: str = "fastest"
    style_id: int = 1

# Корень

@app.get("/", tags=["Gateway"])
async def root():
    return {
        "service": "API Gateway",
        "version": "1.0.0",
        "routes": {
            "/maps/*":                    "Maps API",
            "/navigation/*":              "Navigation API",
            "/places/*":                  "Moscow Places API",
            "/area/*":                    "Area Selection API",
            "/location":                  "Сохранение GPS в Navigation API",
            "/location/history":          "История GPS из Navigation API",
            "/location/latest":           "Последняя позиция из Navigation API",
            "/location/stats":            "Статистика GPS из Navigation API",
            "/route-map":                 "Маршрут + стиль карты",
            "/route-from-current":        "Маршрут от текущей позиции до места",
            "/places-with-route":         "Место + маршрут до него",
            "/places-in-area":            "Места внутри выделенной области",
            "/navigate-in-area":          "Область + места + маршрут до ближайшего",
            "/health":                    "Статус всех сервисов"
        }
    }


# Агрегированный эндпоинт: маршрут от текущей позиции до места

class RouteFromCurrentRequest(BaseModel):
    end_lat: float
    end_lon: float
    routing_type: str = "fastest"
    style_id: int = 1


@app.post("/route-from-current", tags=["Aggregated"])
async def route_from_current(data: RouteFromCurrentRequest):
    #Берёт последнюю GPS-позицию из Navigation API, строит маршрут до указанной точки и загружает стиль карты.

    route_task = http_client.post(
        f"{NAVIGATION_API_URL}/api/v1/route/from-current",
        params={"routing_type": data.routing_type},
        json={"lat": data.end_lat, "lon": data.end_lon}
    )
    style_task = http_client.get(f"{MAPS_API_URL}/styles/{data.style_id}")

    route_result, style_result = await asyncio.gather(
        route_task, style_task, return_exceptions=True
    )

    if isinstance(route_result, Exception):
        raise HTTPException(status_code=503, detail=f"Navigation API недоступен: {route_result}")
    if route_result.status_code == 404:
        raise HTTPException(status_code=404,
                            detail="Нет сохранённой GPS-позиции. Сначала отправьте локацию.")
    if not route_result.is_success:
        raise HTTPException(status_code=route_result.status_code, detail="Ошибка построения маршрута")

    route_data = route_result.json()
    style_data = None
    if not isinstance(style_result, Exception) and style_result.is_success:
        style_data = style_result.json()

    return {
        "route":     route_data,
        "map_style": style_data,
        "tiles_url": f"{MAPS_API_URL}/tiles/{{z}}/{{x}}/{{y}}.mvt",
        "summary": {
            "distance_meters":  route_data.get("distance", 0),
            "duration_seconds": route_data.get("duration", 0),
            "steps_count":      len(route_data.get("steps", []))
        }
    }


# Агрегированный эндпоинт: область + места + маршрут до ближайшего

class NavigateInAreaRequest(BaseModel):
    center_lat: float
    center_lon: float
    size: str = "medium"
    shape: str = "circle"
    category: Optional[str] = None
    routing_type: str = "fastest"
    style_id: int = 1


@app.post("/navigate-in-area", tags=["Aggregated"])
async def navigate_in_area(data: NavigateInAreaRequest):
    #Выделяет область, находит достопримечательности в ней, троит маршрут от текущей позиции до ближайшей из них.

    # 1. Получаем область и последнюю позицию параллельно
    area_task     = http_client.post(
        f"{AREA_API_URL}/area/select",
        json={"center": {"lat": data.center_lat, "lon": data.center_lon},
              "size": data.size, "shape": data.shape}
    )
    location_task = http_client.get(f"{NAVIGATION_API_URL}/location/latest")
    style_task    = http_client.get(f"{MAPS_API_URL}/styles/{data.style_id}")

    area_result, location_result, style_result = await asyncio.gather(
        area_task, location_task, style_task, return_exceptions=True
    )

    if isinstance(area_result, Exception) or not area_result.is_success:
        raise HTTPException(status_code=503, detail="Area API недоступен")

    area = area_result.json()
    radius_km = (area["circle"]["radius_meters"] / 1000
                 if data.shape == "circle" and area.get("circle")
                 else round(math.sqrt(
                     ((area["bounding_box"]["max_lat"] - area["bounding_box"]["min_lat"]) / 2) ** 2 +
                     ((area["bounding_box"]["max_lon"] - area["bounding_box"]["min_lon"]) / 2) ** 2
                 ) * 111, 2))

    # 2. Ищем места в области
    places_result = await http_client.get(
        f"{PLACES_API_URL}/api/places/search/nearby",
        params={"lat": data.center_lat, "lon": data.center_lon, "radius": radius_km}
    )
    places = []
    if places_result.is_success:
        places = places_result.json().get("result", {}).get("items", [])
        if data.category:
            places = [p for p in places
                      if data.category.lower() in (p.get("category") or "").lower()]

    # 3. Строим маршрут от текущей позиции до ближайшего места (если есть позиция и места)
    route_data = None
    nearest_place = None

    current_lat = current_lon = None
    if not isinstance(location_result, Exception) and location_result.is_success:
        loc = location_result.json()
        current_lat = loc.get("latitude")
        current_lon = loc.get("longitude")

    if current_lat and current_lon and places:
        nearest_place = min(
            places,
            key=lambda p: math.sqrt(
                (p["lat"] - current_lat) ** 2 + (p["lon"] - current_lon) ** 2
            )
        )
        route_result = await http_client.post(
            f"{NAVIGATION_API_URL}/api/v1/route",
            json={
                "start": {"lat": current_lat, "lon": current_lon},
                "end":   {"lat": nearest_place["lat"], "lon": nearest_place["lon"]},
                "routing_type": data.routing_type
            }
        )
        if route_result.is_success:
            route_data = route_result.json()

    style_data = None
    if not isinstance(style_result, Exception) and style_result.is_success:
        style_data = style_result.json()

    return {
        "area":          area,
        "places":        places,
        "total_places":  len(places),
        "nearest_place": nearest_place,
        "route":         route_data,
        "current_position": {"lat": current_lat, "lon": current_lon}
                             if current_lat else None,
        "map_style":     style_data,
        "tiles_url":     f"{MAPS_API_URL}/tiles/{{z}}/{{x}}/{{y}}.mvt"
    }

# История локаций (прокси к Navigation API)

@app.api_route("/maps/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH"],
               tags=["Maps API proxy"])
async def maps_proxy(path: str, request: Request):
    # Проксирует любой запрос в Maps API.
    body = None
    if request.method in ("POST", "PUT", "PATCH"):
        try:
            body = await request.json()
        except Exception:
            body = None

    upstream = await proxy_request(
        base_url=MAPS_API_URL,
        path=f"/{path}",
        method=request.method,
        body=body,
        params=dict(request.query_params),
        headers=dict(request.headers)
    )
    return make_response(upstream)



@app.api_route("/navigation/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH"],
               tags=["Navigation API proxy"])
async def navigation_proxy(path: str, request: Request):
    #Проксирует любой запрос в Navigation API.
    body = None
    if request.method in ("POST", "PUT", "PATCH"):
        try:
            body = await request.json()
        except Exception:
            body = None

    upstream = await proxy_request(
        base_url=NAVIGATION_API_URL,
        path=f"/{path}",
        method=request.method,
        body=body,
        params=dict(request.query_params),
        headers=dict(request.headers)
    )
    return make_response(upstream)


@app.api_route("/places/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH"],
               tags=["Places API proxy"])
async def places_proxy(path: str, request: Request):
    #Проксирует любой запрос в Moscow Places API.
    body = None
    if request.method in ("POST", "PUT", "PATCH"):
        try:
            body = await request.json()
        except Exception:
            body = None

    upstream = await proxy_request(
        base_url=PLACES_API_URL,
        path=f"/api/{path}",
        method=request.method,
        body=body,
        params=dict(request.query_params),
        headers=dict(request.headers)
    )
    return make_response(upstream)


@app.api_route("/area/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH"],
               tags=["Area API proxy"])
async def area_proxy(path: str, request: Request):
    #Проксирует любой запрос в Area API.
    body = None
    if request.method in ("POST", "PUT", "PATCH"):
        try:
            body = await request.json()
        except Exception:
            body = None

    upstream = await proxy_request(
        base_url=AREA_API_URL,
        path=f"/area/{path}",
        method=request.method,
        body=body,
        params=dict(request.query_params),
        headers=dict(request.headers)
    )
    return make_response(upstream)
# Отправляет координаты в оба сервиса параллельно

@app.post("/location", tags=["Navigation"])
async def save_location(location: LocationData):
    #Сохраняет GPS-координаты в Navigation API.
    upstream = await proxy_request(
        base_url=NAVIGATION_API_URL,
        path="/location",
        method="POST",
        body=location.model_dump()
    )
    return make_response(upstream)


# Shortcut-прокси для удобных Navigation-маршрутов

@app.get("/location/latest", tags=["Navigation"])
async def location_latest():
    # Последняя известная позиция пользователя из Navigation API.
    upstream = await proxy_request(
        base_url=NAVIGATION_API_URL, path="/location/latest", method="GET"
    )
    return make_response(upstream)


@app.get("/location/stats", tags=["Navigation"])
async def location_stats():
    #Статистика GPS-точек из Navigation API.
    upstream = await proxy_request(
        base_url=NAVIGATION_API_URL, path="/location/stats", method="GET"
    )
    return make_response(upstream)


@app.delete("/location/history", tags=["Navigation"])
async def clear_location_history():
    # Очистить историю перемещений в Navigation API
    upstream = await proxy_request(
        base_url=NAVIGATION_API_URL, path="/location/history", method="DELETE"
    )
    return make_response(upstream)


# эндпоинт: маршрут и стиль карты

@app.post("/route-map", tags=["Aggregated"])
async def get_route_with_map(data: RouteRequest):
    #Строит маршрут через Navigation API и одновременно загружает стиль карты из Maps API.

    route_payload = {
        "start": {"lat": data.start_lat, "lon": data.start_lon},
        "end":   {"lat": data.end_lat,   "lon": data.end_lon},
        "routing_type": data.routing_type
    }

    route_task = http_client.post(
        f"{NAVIGATION_API_URL}/api/v1/route", json=route_payload
    )
    style_task = http_client.get(
        f"{MAPS_API_URL}/styles/{data.style_id}"
    )

    route_result, style_result = await asyncio.gather(
        route_task, style_task, return_exceptions=True
    )
    # Маршрут — обязательный результат
    if isinstance(route_result, Exception):
        raise HTTPException(status_code=503,
                            detail=f"Navigation API недоступен: {route_result}")
    if not route_result.is_success:
        raise HTTPException(status_code=route_result.status_code,
                            detail="Ошибка построения маршрута")

    route_data = route_result.json()

    # Стиль карты — опциональный результат
    style_data = None
    if not isinstance(style_result, Exception) and style_result.is_success:
        style_data = style_result.json()

    return {
        "route": route_data,
        "map_style": style_data,
        "tiles_url": f"{MAPS_API_URL}/tiles/{{z}}/{{x}}/{{y}}.mvt",
        "summary": {
            "distance_meters":  route_data.get("distance", 0),
            "duration_seconds": route_data.get("duration", 0),
            "steps_count":      len(route_data.get("steps", []))
        }
    }

# Moscow Places API + Navigation API

class PlaceRouteRequest(BaseModel):
    place_id: int
    start_lat: float
    start_lon: float
    routing_type: str = "fastest"
    style_id: int = 1


@app.post("/places-with-route", tags=["Aggregated"])
async def get_place_with_route(data: PlaceRouteRequest):
   # Получает информацию о достопримечательности из Places API, строит маршрут через Navigation API и загружает стиль карты из Maps API.

    # Параллельно запрашиваем место и стиль карты
    place_task = http_client.get(f"{PLACES_API_URL}/api/places/{data.place_id}")
    style_task = http_client.get(f"{MAPS_API_URL}/styles/{data.style_id}")

    place_result, style_result = await asyncio.gather(
        place_task, style_task, return_exceptions=True
    )

    # Место — обязательный результат
    if isinstance(place_result, Exception):
        raise HTTPException(status_code=503, detail=f"Places API недоступен: {place_result}")
    if place_result.status_code == 404:
        raise HTTPException(status_code=404, detail=f"Место с ID {data.place_id} не найдено")
    if not place_result.is_success:
        raise HTTPException(status_code=place_result.status_code, detail="Ошибка получения места")

    place_data = place_result.json()
    place = place_data.get("result", {})

    end_lat = place.get("lat")
    end_lon = place.get("lon")
    if end_lat is None or end_lon is None:
        raise HTTPException(status_code=400, detail="У места отсутствуют координаты")

    # Строим маршрут
    route_result = await http_client.post(
        f"{NAVIGATION_API_URL}/api/v1/route",
        json={
            "start": {"lat": data.start_lat, "lon": data.start_lon},
            "end":   {"lat": end_lat,        "lon": end_lon},
            "routing_type": data.routing_type
        }
    )

    if not route_result.is_success:
        raise HTTPException(status_code=503, detail="Не удалось построить маршрут")

    route_data = route_result.json()

    # Стиль карты — опциональный результат
    style_data = None
    if not isinstance(style_result, Exception) and style_result.is_success:
        style_data = style_result.json()

    return {
        "place":    place,
        "route":    route_data,
        "map_style": style_data,
        "tiles_url": f"{MAPS_API_URL}/tiles/{{z}}/{{x}}/{{y}}.mvt",
        "summary": {
            "destination":      place.get("name"),
            "address":          place.get("address"),
            "distance_meters":  route_data.get("distance", 0),
            "duration_seconds": route_data.get("duration", 0),
        }
    }


# Агрегированный эндпоинт: места внутри области

class PlacesInAreaRequest(BaseModel):
    center_lat: float
    center_lon: float
    size: str = "medium"       # small / medium / large
    shape: str = "circle"      # circle / square
    category: Optional[str] = None


@app.post("/places-in-area", tags=["Aggregated"])
async def get_places_in_area(data: PlacesInAreaRequest):
    #Выделяет область через Area API, затем ищет ближайшие достопримечательности из Places API в её радиусе.

    # 1. Получаем параметры области
    area_result = await http_client.post(
        f"{AREA_API_URL}/area/select",
        json={
            "center": {"lat": data.center_lat, "lon": data.center_lon},
            "size":   data.size,
            "shape":  data.shape
        }
    )
    if not area_result.is_success:
        raise HTTPException(status_code=area_result.status_code,
                            detail="Ошибка получения области")

    area = area_result.json()

    # Определяем радиус поиска в км
    if data.shape == "circle" and area.get("circle"):
        radius_km = area["circle"]["radius_meters"] / 1000
    else:
        bb = area["bounding_box"]
        dlat = (bb["max_lat"] - bb["min_lat"]) / 2
        dlon = (bb["max_lon"] - bb["min_lon"]) / 2
        radius_km = round(math.sqrt(dlat**2 + dlon**2) * 111, 2)

    # 2. Ищем места в радиусе
    places_result = await http_client.get(
        f"{PLACES_API_URL}/api/places/search/nearby",
        params={"lat": data.center_lat, "lon": data.center_lon, "radius": radius_km}
    )
    if not places_result.is_success:
        raise HTTPException(status_code=503, detail="Places API недоступен")

    places = places_result.json().get("result", {}).get("items", [])

    # 3. Фильтр по категории (если указан)
    if data.category:
        places = [p for p in places
                  if data.category.lower() in (p.get("category") or "").lower()]

    return {
        "area":    area,
        "places":  places,
        "total":   len(places),
        "search_params": {
            "center":    {"lat": data.center_lat, "lon": data.center_lon},
            "radius_km": radius_km,
            "category":  data.category
        }
    }

@app.get("/location/history", tags=["Aggregated"])
async def location_history(
    limit:  int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0)
):
    #Возвращает историю GPS-точек из Navigation API.
    upstream = await proxy_request(
        base_url=NAVIGATION_API_URL,
        path="/location/history",
        method="GET",
        params={"limit": limit, "offset": offset}
    )
    return make_response(upstream)


# Health-check всех сервисов

@app.get("/health", tags=["Gateway"])
async def health_check():
    #Проверяет доступность всех сервисов.

    async def ping(url: str, path: str = "/health") -> str:
        try:
            r = await http_client.get(f"{url}{path}", timeout=HEALTH_TIMEOUT)
            return "healthy" if r.is_success else f"unhealthy ({r.status_code})"
        except Exception as e:
            return f"unavailable ({e})"

    maps_status, nav_status, places_status, area_status = await asyncio.gather(
        ping(MAPS_API_URL),
        ping(NAVIGATION_API_URL, "/api/v1/health"),
        ping(PLACES_API_URL),
        ping(AREA_API_URL)
    )

    all_ok = all(s == "healthy" for s in [maps_status, nav_status, places_status, area_status])

    return {
        "gateway":        "healthy",
        "overall":        "healthy" if all_ok else "degraded",
        "maps_api":       maps_status,
        "navigation_api": nav_status,
        "places_api":     places_status,
        "area_api":       area_status,
        "timestamp":      datetime.datetime.now().isoformat()
    }

# Жизненный цикл

@app.on_event("startup")
async def startup():
    logger.info("API Gateway запущен")
    logger.info(f"  Maps API        {MAPS_API_URL}")
    logger.info(f"  Navigation API  {NAVIGATION_API_URL}")
    logger.info(f"  Places API      {PLACES_API_URL}")
    logger.info(f"  Area API        {AREA_API_URL}")


@app.on_event("shutdown")
async def shutdown():
    await http_client.aclose()
    logger.info("API Gateway остановлен")


# Точка входа

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)