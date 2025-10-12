from fastapi import FastAPI,HTTPException,Depends
from fastapi.responses import Response
from fastapi.staticfiles import StaticFiles
from sqlalchemy import create_engine,Column,Integer,String,Boolean,DateTime,func,text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker,Session
from sqlalchemy.types import BINARY
from sqlalchemy.exc import SQLAlchemyError
from pydantic import BaseModel,validator
from typing import List,Dict,Any,Optional
import datetime
import json
import uuid
import gzip
import boto3
import uvicorn

STYLES_DATABASE_URL = "postgresql://user:password@localhost/styles_db"
TILES_DATABASE_URL = "postgresql://postgres:admin@localhost:5432/postgres"
S3_ENDPOINT = "http://localhost:9000"
S3_BUCKET = "map-styles"
S3_ACCESS_KEY = "minioadmin"
S3_SECRET_KEY = "minioadmin"

styles_engine = create_engine(STYLES_DATABASE_URL)
StylesSessionLocal = sessionmaker(bind=styles_engine)
StylesBase = declarative_base()

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

# ===== МОДЕЛИ БД (Styles) =====
class Style(StylesBase):
    tablename = "styles"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    description = Column(String(1000))
    s3_key = Column(String(512), nullable=False, unique=True)
    is_default = Column(Boolean, default=False)
    version = Column(String(10), default="1.0")
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

StylesBase.metadata.create_all(bind=styles_engine)

class VectorTile(TilesBase):
    tablename = "vector_tiles"

    zoom = Column(Integer, primary_key=True)
    x = Column(Integer, primary_key=True)
    y = Column(Integer, primary_key=True)
    tile_data = Column(Binary, nullable=False)

TilesBase.metadata.create_all(bind=tiles_engine)

class SourceStyle(BaseModel):
    type: str
    url: Optional[str] = None
    tiles: Optional[List[str]] = None
    minzoom: Optional[int] = 0
    maxzoom: Optional[int] = 28

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

    @validator('version')
    def validate_version(cls, v):
        if v not in [7, 8]:
            raise ValueError('Version must be 7 or 8')
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

def get_tiles_db():
    db = TilesSessionLocal()
    try:
        yield db
    finally:
        db.close()

# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ

def get_style_from_s3(s3_key: str) -> Dict:
    response = s3_client.get_object(Bucket=S3_BUCKET, Key=s3_key)
    style_content = response['Body'].read().decode('utf-8')
    return json.loads(style_content)

def save_style_to_s3(style_data: Dict) -> str:
    s3_key = f"styles/{uuid.uuid4()}.json"
    s3_client.put_object(
        Bucket=S3_BUCKET,
        Key=s3_key,
        Body=json.dumps(style_data, indent=2),
        ContentType='application/json'
    )
    return s3_key


# ===== STYLES API ENDPOINTS =====

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
    """Получить список всех стилей"""
    styles = db.query(Style).all()
    total = db.query(Style).count()
    return StyleListResponse(items=styles, total=total)

@app.get("/styles/{style_id}", response_model=StyleResponse)
def get_style(style_id: int, db: Session = Depends(get_styles_db)):
    """Получить стиль по ID"""
    db_style = db.query(Style).filter(Style.id == style_id).first()
    if not db_style:
        raise HTTPException(status_code=404, detail="Style not found")

    style_data = get_style_from_s3(db_style.s3_key)

    return StyleResponse(
        id=db_style.id,
        name=db_style.name,
        description=db_style.description,
        style_data=MapglStyle(**style_data),
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

    s3_client.delete_object(Bucket=S3_BUCKET, Key=db_style.s3_key)

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
        "modules": ["Styles API", "Vector Tiles API"]
    }
@app.get('/tiles/{z}/{x}/{y}.mvt')
def get_tiles(z: int, x: int, y: int, db: Session = Depends(get_tiles_db)):
    """Получить vector tile"""
    cached_tile = db.query(VectorTile).filter_by(zoom=z, x=x, y=y).first()
    if cached_tile:
        tile_data = cached_tile.tile_data
    else:
        sql = sql_template.format(z=z, x=x, y=y)
        result = db.execute(text(sql)).scalar()
        tile_data = bytes(result) if result is not None else b''
        new_tile = VectorTile(zoom=z, x=x, y=y, tile_data=tile_data)
        
    try:    
        db.add(new_tile)
      
    except SQLAlchemyError as e:
        return f"Ошибка при добавлении тайлов: {str(e)}"
    
    try: 
        db.commit()
    except SQLAlchemyError as e:
        raise HTTPException(status_code=500, detail=f"Внутренняя ошибка коммита: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=403,detail=f"Ошибка при коммите к базе данных: {str(e)}")
   

    try:
        compressed_data = gzip.compress(tile_data,compresslevel=5)  
    except (MemoryError, OSError) as e:
        print(f"Сжатие не удалось: {str(e)}")
   
    
    return Response(
        content=compressed_data,
        media_type='application/vnd.mapbox-vector-tile',
        headers={'Content-Encoding': 'gzip'}
    )


    if name == 'main':
        uvicorn.run(app, host='0.0.0.0', port=8000)




