from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from typing import List, Literal
from enum import Enum
import math
import uvicorn
app = FastAPI(
    title="Area Selection API",
    description="API для выделения областей с разными размерами, как в 2ГИС",
    version="1.0.0"
)


class AreaSize(str, Enum):
    SMALL = "small"
    MEDIUM = "medium"
    LARGE = "large"


class Point(BaseModel):
    lat: float = Field(..., description="Широта", ge=-90, le=90)
    lon: float = Field(..., description="Долгота", ge=-180, le=180)


class AreaRequest(BaseModel):
    center: Point = Field(..., description="Центральная точка области")
    size: AreaSize = Field(..., description="Размер области: small, medium, large")
    shape: Literal["circle", "square"] = Field(
        default="circle",
        description="Форма области: circle или square"
    )


class BoundingBox(BaseModel):
    min_lat: float
    max_lat: float
    min_lon: float
    max_lon: float


class CircleArea(BaseModel):
    center: Point
    radius_meters: float
    radius_degrees: float


class AreaResponse(BaseModel):
    center: Point
    size: AreaSize
    shape: str
    bounding_box: BoundingBox
    circle: CircleArea | None = None
    corners: List[Point] | None = None
    area_km2: float


# Радиусы для разных размеров областей (в метрах)
RADIUS_CONFIG = {
    AreaSize.SMALL: 500,  # 500 метров
    AreaSize.MEDIUM: 2000,  # 2 километра
    AreaSize.LARGE: 10000  # 10 километров
}


def meters_to_degrees_lat(meters: float) -> float:
    #Конвертация метров в градусы широты
    return meters / 111320


def meters_to_degrees_lon(meters: float, latitude: float) -> float:
    #Конвертация метров в градусы долготы с учётом широты
    return meters / (111320 * math.cos(math.radians(latitude)))


def calculate_area_km2(radius_m: float, shape: str) -> float:
    #Вычисление площади в км²
    radius_km = radius_m / 1000
    if shape == "circle":
        return math.pi * radius_km ** 2
    else:  # square
        side = radius_km * 2
        return side ** 2


@app.get("/", tags=["info"])
async def root():
    #Информация об API
    return {
        "message": "Area Selection API",
        "version": "1.0.0",
        "endpoints": {
            "POST /area/select": "Выделить область на карте",
            "GET /area/sizes": "Получить доступные размеры областей"
        }
    }


@app.get("/area/sizes", tags=["area"])
async def get_available_sizes():
    #Получить информацию о доступных размерах областей
    return {
        "sizes": [
            {
                "size": "small",
                "radius_meters": RADIUS_CONFIG[AreaSize.SMALL],
                "description": "Малая область (500м)"
            },
            {
                "size": "medium",
                "radius_meters": RADIUS_CONFIG[AreaSize.MEDIUM],
                "description": "Средняя область (2км)"
            },
            {
                "size": "large",
                "radius_meters": RADIUS_CONFIG[AreaSize.LARGE],
                "description": "Большая область (10км)"
            }
        ]
    }


@app.post("/area/select", response_model=AreaResponse, tags=["area"])
async def select_area(request: AreaRequest):
    #Выделить область на карте
    try:
        radius_meters = RADIUS_CONFIG[request.size]

        # Конвертация радиуса в градусы
        radius_lat = meters_to_degrees_lat(radius_meters)
        radius_lon = meters_to_degrees_lon(radius_meters, request.center.lat)

        # Вычисление bounding box
        bounding_box = BoundingBox(
            min_lat=request.center.lat - radius_lat,
            max_lat=request.center.lat + radius_lat,
            min_lon=request.center.lon - radius_lon,
            max_lon=request.center.lon + radius_lon
        )

        # Вычисление площади
        area_km2 = calculate_area_km2(radius_meters, request.shape)

        response = AreaResponse(
            center=request.center,
            size=request.size,
            shape=request.shape,
            bounding_box=bounding_box,
            area_km2=round(area_km2, 2)
        )

        if request.shape == "circle":
            response.circle = CircleArea(
                center=request.center,
                radius_meters=radius_meters,
                radius_degrees=radius_lat
            )
        else:  # square
            # Вычисление углов квадрата
            response.corners = [
                Point(lat=bounding_box.min_lat, lon=bounding_box.min_lon),  # SW
                Point(lat=bounding_box.min_lat, lon=bounding_box.max_lon),  # SE
                Point(lat=bounding_box.max_lat, lon=bounding_box.max_lon),  # NE
                Point(lat=bounding_box.max_lat, lon=bounding_box.min_lon),  # NW
            ]
        return response

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка при обработке: {str(e)}")


@app.post("/area/check-point", tags=["area"])
async def check_point_in_area(
        area_center: Point,
        area_size: AreaSize,
        check_point: Point,
        shape: Literal["circle", "square"] = "circle"
):
    #Проверить, находится ли точка внутри области
    radius_meters = RADIUS_CONFIG[area_size]

    # Вычисление расстояния между точками (формула гаверсинусов)
    lat1, lon1 = math.radians(area_center.lat), math.radians(area_center.lon)
    lat2, lon2 = math.radians(check_point.lat), math.radians(check_point.lon)

    dlat = lat2 - lat1
    dlon = lon2 - lon1

    a = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    c = 2 * math.asin(math.sqrt(a))
    distance_meters = 6371000 * c  # Радиус Земли в метрах

    if shape == "circle":
        inside = distance_meters <= radius_meters
    else:  # square
        radius_lat = meters_to_degrees_lat(radius_meters)
        radius_lon = meters_to_degrees_lon(radius_meters, area_center.lat)

        inside = (
                abs(check_point.lat - area_center.lat) <= radius_lat and
                abs(check_point.lon - area_center.lon) <= radius_lon
        )

    return {
        "inside": inside,
        "distance_meters": round(distance_meters, 2),
        "area_radius_meters": radius_meters
    }

if __name__ == '__main__':
    uvicorn.run(app, host='0.0.0.0', port=8003)  # запуск api с помощью библиотеки uvicorn