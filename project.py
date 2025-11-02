from fastapi import FastAPI, HTTPException, Depends
from fastapi.responses import Response
from fastapi.staticfiles import StaticFiles
from sqlalchemy import create_engine, Column, Integer, String, Boolean, DateTime, func, text, LargeBinary,Table
# from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session,declarative_base #не знаю импортировал по новому но еррор сохранился(  
from sqlalchemy.exc import SQLAlchemyError
from pydantic import BaseModel, validator
from typing import List, Dict, Any, Optional
import datetime
import json
import uuid
import gzip
import boto3
from botocore.exceptions import ClientError
import uvicorn  

STYLES_DATABASE_URL = "postgresql://user:password@localhost/styles_db"
TILES_DATABASE_URL = "postgresql://postgres:admin@localhost:5432/postgres"
S3_ENDPOINT = "http://localhost:9000"
S3_BUCKET = "map-styles"
S3_ACCESS_KEY = "minioadmin"
S3_SECRET_KEY = "minioadmin"
TILES_STORAGE_TYPE = "database"
S3_TILES_BUCKET = "vector-tiles"
#подключения к базам данных
# S3_STYLE="styles" # подумал по логике с  VectorTile, не помогло

StylesBase = declarative_base()
styles_engine = create_engine(STYLES_DATABASE_URL)
StylesSessionLocal = sessionmaker(bind=styles_engine)
# Vector Tiles API
tiles_engine = create_engine(TILES_DATABASE_URL)
TilesSessionLocal = sessionmaker(bind=tiles_engine)
TilesBase = declarative_base() 

s3_client = boto3.client(
    's3',
    endpoint_url=S3_ENDPOINT,
    aws_access_key_id=S3_ACCESS_KEY,
    aws_secret_access_key=S3_SECRET_KEY
)

# МОДЕЛИ БД (Styles)
class Style(StylesBase): #ошибка потому что не может определить имя таблицы, вследствие скорее всего того что нету таблицы, 
  #так как там ошибка если переводить на русский кокрас про это. Я сделал обработчик данной ошибки 
    __tablename__ = "styles"
   # __abstract__=True # это самое логичное решение, но оно не помогло, его я взял из: https://github.com/sqlalchemy/sqlalchemy/discussions/8699  
    # __tablename__ = Table('Styles', meta, autoload=True, autoload_with=styles_engine) #этот вариант я нашел на сайте: https://www.devasking.com/issue/how-to-define-a-table-without-primary-key-with-sqlalchemy
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255),  nullable=False)
    description = Column(String(1000))
    s3_key = Column(String(512), nullable=False, unique=True)
    
    is_default = Column(Boolean, default=False)
    version = Column(String(10), default="1.0")
    
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())


# styles_engine = create_engine(STYLES_DATABASE_URL)
# StylesSessionLocal = sessionmaker(bind=styles_engine)
# заглядывал сюда но там про версию pydantic  https://github.com/fastapi/sqlmodel/pull/1602 

class VectorTile(TilesBase): # страновато для меня не фронтендера, но здесь все работает
    __tablename__ = "vector_tiles"

    zoom = Column(Integer, primary_key=True)
    x = Column(Integer, primary_key=True)
    y = Column(Integer, primary_key=True)
    # Бинарные данные тайла в формате Mapbox Vector Tile (протобуф)
    tile_data = Column(LargeBinary, nullable=False)
    created_at = Column(DateTime, default=func.now())  # Когда тайл был создан

    # Где хранится тайл: "database", "s3" или "hybrid"
    storage_type = Column(String(20), default="database")

    # Путь к тайлу в S3 (если используется S3 или hybrid режим)
    s3_key = Column(String(512), nullable=True)

# Создаем таблицы в БД, если они не существуют

#пока что это единственное решение которое я откапал:
class TableNotFoundError(Exception):
    pass
try:
    StylesBase.metadata.create_all(bind=styles_engine)
except SQLAlchemyError as e:
    raise TableNotFoundError(f"Failed to create or access the 'styles' table: {e}")


print("Style.__tablename__ =", getattr(Style, '__tablename__', 'NOT FOUND'))
print("Style class:", Style)

StylesBase.metadata.create_all(bind=styles_engine)
TilesBase.metadata.create_all(bind=tiles_engine)
# Модель источника данных для карты (векторные тайлы)
class SourceStyle(BaseModel):
    type: str
    url: Optional[str] = None
    tiles: Optional[List[str]] = None
    minzoom: Optional[int] = 0
    maxzoom: Optional[int] = 28

# Модель слоя карты (что и как рисовать на карте)
class LayerStyle(BaseModel):
    id: str
    type: str
    source: str
    paint: Dict[str, Any]
    layout: Optional[Dict[str, Any]] = None


class MapglStyle(BaseModel):
    version: int = 8
    sources: Dict[str, SourceStyle]
    layers: List[LayerStyle]
    sprite: Optional[str] = None
    glyphs: Optional[str] = None

    # Валидатор проверяет версию спецификации
    @validator('version')
    def validate_version(cls, v):
        if v not in [7, 8]:
            raise ValueError('Версия может быть 7 или 8')
        return v

    @validator('layers')
    def validate_layers(cls, v):
        if len(v) == 0:
            raise ValueError('At least one layer is required')
        return v


class StyleCreate(BaseModel):
    name: str
    description: Optional[str] = None
    style_data: MapglStyle
    is_default: bool = False

    @validator('name')
    def validate_name(cls, v):
        if not v or len(v) < 3:
            raise ValueError('Name must be at least 3 characters')
        return v


# Модель для возврата полного стиля (с данными из S3)
class StyleResponse(BaseModel):
    id: int
    name: str
    description: Optional[str]
    style_data: MapglStyle
    is_default: bool
    version: str
    created_at: datetime.datetime
    updated_at: datetime.datetime

    class Config:
        from_attributes = True

# Модель для возврата метаданных стиля (без данных из S3, легковесная)
class StyleMetadataResponse(BaseModel):
    id: int
    name: str
    description: Optional[str]
    is_default: bool
    version: str
    created_at: datetime.datetime
    updated_at: datetime.datetime

    class Config:
        from_attributes = True

# Модель для списка стилей (пагинация)
class StyleListResponse(BaseModel):
    items: List[StyleMetadataResponse]
    total: int


app = FastAPI(title="Maps API", version="1.0.0")
try:
    app.mount("/static", StaticFiles(directory="static"), name="static")
except Exception:
    pass


def get_styles_db():
    db = StylesSessionLocal()
    try:
        yield db
    finally:
        db.close()

# Аналогично для БД тайлов
def get_tiles_db():
    db = TilesSessionLocal()
    try:
        yield db
    finally:
        db.close()


# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
def ensure_s3_bucket_exists(bucket_name: str):
    try:
        # Пытаемся получить метаданные bucket
        s3_client.head_bucket(Bucket=bucket_name)
    except ClientError:
        # Bucket не существует, создаем его
        try:
            s3_client.create_bucket(Bucket=bucket_name)
            print(f"Created S3 bucket: {bucket_name}")
        except ClientError as e:
            print(f"Error creating bucket {bucket_name}: {e}")


def get_style_from_s3(s3_key: str) -> Dict:
    try:
        # Запрашиваем объект из S3
        response = s3_client.get_object(Bucket=S3_BUCKET, Key=s3_key)
        # Читаем содержимое и декодируем из bytes в строку
        style_content = response['Body'].read().decode('utf-8')
        # Парсим JSON в Python словарь
        return json.loads(style_content)
    except ClientError as e:
        raise HTTPException(status_code=404, detail=f"Style not found in S3: {str(e)}")


def save_style_to_s3(style_data: Dict) -> str:
    s3_key = f"styles/{uuid.uuid4()}.json"
    try:
        s3_client.put_object(
            Bucket=S3_BUCKET,
            Key=s3_key,
            Body=json.dumps(style_data, indent=2),  # Преобразуем словарь в JSON строку
            ContentType='application/json'  # Указываем MIME-тип
        )
        return s3_key
    except ClientError as e:
        raise HTTPException(status_code=500, detail=f"Error saving to S3: {str(e)}")

def save_tile_to_s3(z: int, x: int, y: int, tile_data: bytes) -> str:
    s3_key = f"tiles/{z}/{x}/{y}.mvt"
    try:
        # СЖИМАЕМ данные с помощью gzip (уровень 5 - баланс скорости и степени сжатия)
        compressed_data = gzip.compress(tile_data, compresslevel=5)

        s3_client.put_object(
            Bucket=S3_TILES_BUCKET,
            Key=s3_key,
            Body=compressed_data,  # Сохраняем СЖАТЫЕ данные
            ContentType='application/vnd.mapbox-vector-tile',
            ContentEncoding='gzip'  # ВАЖНО: указываем что данные сжаты
        )
        return s3_key
    except ClientError as e:
        print(f"Error saving tile to S3: {str(e)}")
        return None
# STYLES API ENDPOINTS
def get_tile_from_s3(s3_key: str) -> bytes:
    try:
        response = s3_client.get_object(Bucket=S3_TILES_BUCKET, Key=s3_key)
        # Данные уже сжаты, возвращаем как есть
        return response['Body'].read()
    except ClientError:
        return None
@app.post("/styles", response_model=StyleMetadataResponse, status_code=201)
def create_style(style: StyleCreate, db: Session = Depends(get_styles_db)):
    if style.is_default:
        db.query(Style).update({Style.is_default: False})

        s3_key = save_style_to_s3(style.style_data.model_dump())
        db_style = Style(
        name=style.name,
        description=style.description,
        s3_key=s3_key,
        is_default=style.is_default
    )   
        db.add(db_style)
        db.commit()
        db.refresh(db_style)
        return db_style

@app.get("/styles", response_model=StyleListResponse)
def list_styles(db: Session = Depends(get_styles_db)):
    #Получить список всех стилей
    styles = db.query(Style).all()
    total = db.query(Style).count()
    return StyleListResponse(items=styles, total=total)


@app.get("/styles/{style_id}", response_model=StyleResponse)
def get_style(style_id: int, db: Session = Depends(get_styles_db)):
    # Находим стиль в БД
    db_style = db.query(Style).filter(Style.id == style_id).first()
    if not db_style:
        raise HTTPException(status_code=404, detail="Style not found")

    # Загружаем JSON стиля из S3
    style_data = get_style_from_s3(db_style.s3_key)

    # Возвращаем комбинацию метаданных из БД и данных из S3
    return StyleResponse(
        id=db_style.id,
        name=db_style.name,
        description=db_style.description,
        style_data=MapglStyle(**style_data),  # Валидируем через Pydantic
        is_default=db_style.is_default,
        version=db_style.version,
        created_at=db_style.created_at,
        updated_at=db_style.updated_at
    )
@app.delete("/styles/{style_id}")
def delete_style(style_id: int, db: Session = Depends(get_styles_db)):
    db_style = db.query(Style).filter(Style.id == style_id).first()

    if not db_style:
        raise HTTPException(status_code=404, detail="Style not found")

    try:
        s3_client.delete_object(Bucket=S3_BUCKET, Key=db_style.s3_key)
    except ClientError as e:
        print(f"Warning: Could not delete S3 object: {str(e)}")
    db.delete(db_style)
    db.commit()
    return {"message": "Style deleted successfully"}

sql_template = '''
    SELECT
        ST_AsMVT(q, 'lines_tricity', 4096, 'geom') as mvt
    FROM (
        SELECT
            ST_AsMVTGeom(
                ST_Transform(geom, 3857),
                ST_TileEnvelope({z}, {x}, {y}),
                4096,
                0,
                true
            ) AS geom
        FROM
            osm.lines_tricity
        WHERE
            geom && ST_Transform(ST_TileEnvelope({z}, {x}, {y}), 4326)
    ) q;
'''

@app.get('/')
def root():
    return {
        "service": "Maps API",
        "version": "1.0.0",
        "modules": ["Styles API", "Vector Tiles API"],
        "tiles_storage": TILES_STORAGE_TYPE
    }

@app.get('/tiles/{z}/{x}/{y}.mvt')
def get_tiles(z: int, x: int, y: int, db: Session = Depends(get_tiles_db)):
    #Получить vector tile
    sql = sql_template.format(z=z, x=x, y=y)

    try:
        result = db.execute(text(sql)).scalar()
        tile_data = bytes(result) if result is not None else b''
    except SQLAlchemyError as e:
        raise HTTPException(status_code=500, detail=f"Ошибка при генерации тайла: {str(e)}")

    # Сжимаем данные
    try:
        compressed_data = gzip.compress(tile_data, compresslevel=5)
    except (MemoryError, OSError) as e:
        raise HTTPException(status_code=500, detail=f"Ошибка сжатия: {str(e)}")

    # Возвращаем сжатый тайл
    return Response(
        content=compressed_data,
        media_type='application/vnd.mapbox-vector-tile',
        headers={'Content-Encoding': 'gzip'}
    )
if __name__ == '__main__':
    uvicorn.run(app, host='0.0.0.0', port=8000)







