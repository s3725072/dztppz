from fastapi import FastAPI, HTTPException, Depends #импортируем важную библиотеку которая по сути отвечает за сам api есть несколько библиотек 
# но мы выбрали fastapi импортируем модули отвечающие за ошибки в самом api и зависимость
from fastapi.responses import Response #модуль отвечающий за сами запросы к api
from fastapi.staticfiles import StaticFiles  #модуль для работы со статическими файлами такими как векторные тайлы
from sqlalchemy import create_engine, Column, Integer, String, Boolean, DateTime, func, text, LargeBinary #импортируем библиотеку для взаимодействия с sql-таблицами а также модули позволяющие работы с тд из sql
from sqlalchemy.ext.declarative import declarative_base #данная библиотека имеет несколько модулей этот модуль отвечает за наследование моделей и их определение
from sqlalchemy.orm import sessionmaker, Session #этот модуль отвечает за создание новых обьектов сессии для работы с бд
from sqlalchemy.exc import SQLAlchemyError #обработчик ошибок при взаимодействии между api и бд
from pydantic import BaseModel, validator  # импортируем библиотеку для проверки данных и управления настройками в Python
from typing import List, Dict, Any, Optional #импортируем то инструмент для аннотаций типов — явного указания типов данных для переменных, аргументов функций или возвращаемых значений
from botocore.exceptions import ClientError #импортируем обработку ошибок при взаимодействии с клиентской стороной
import datetime #библиотека для отслеживания даты и времени
import json #библиотека для взаимодействия с даннами типа json
import uuid #библиотека для генерации uuid специального представления данных
import gzip # сжатие гео файлов и их обработка и их дальнейшая обработка в нашем api
import boto3 #библиотека для взаимодействия с aws(Amazon Web Service)
import uvicorn #библиотека с помощью которой мы запускаем наше приложение
# URL подключения к БД стилей (метаданные стилей: название, описание, ссылка на S3)
STYLES_DATABASE_URL = "postgresql://user:password@localhost/styles_db"
# URL подключения к БД с векторными тайлами (геоданные для отрисовки карты)
TILES_DATABASE_URL = "postgresql://postgres:admin@localhost:5432/postgres"
# Настройки MinIO/S3 для хранения JSON стилей карт
S3_ENDPOINT = "http://localhost:9000"  # Локальный MinIO сервер
S3_BUCKET = "map-styles"  # Bucket для хранения JSON-файлов стилей
S3_ACCESS_KEY = "minioadmin" #ключ для доступа к базе
S3_SECRET_KEY = "minioadmin" #секретный ключ для доступа к базе

TILES_STORAGE_TYPE = "database" #указание в каком тп мы будем хранить тайлы
S3_TILES_BUCKET = "vector-tiles" #Bucket для хранения векторных тайлов (если используется S3)

# подключения к базам данных
styles_engine = create_engine(STYLES_DATABASE_URL)
StylesSessionLocal = sessionmaker(bind=styles_engine)
StylesBase = declarative_base()
# Подключение к векторным тайлам
tiles_engine = create_engine(TILES_DATABASE_URL)
TilesSessionLocal = sessionmaker(bind=tiles_engine)
TilesBase = declarative_base()

s3_client = boto3.client(   
    's3', #мы указываем что мы работаем с S3
    endpoint_url=S3_ENDPOINT, #URL-сервиса S3
    aws_access_key_id=S3_ACCESS_KEY, #ID-ключ доступа S3
    aws_secret_access_key=S3_SECRET_KEY #секретный ключ доступа AWS
)  #Это создает взаимодействие с сервисом хранения объектов (S3), используя библиотеку boto3

# Таблица для хранения метаданных стилей карт
class Style(StylesBase):
    tablename = "styles"  #имя карты таблицы
    id = Column(Integer, primary_key=True, index=True) #id-таблицы здесь мы задаем primary key=True потому что мы производим уникальную идентификацию нашего id
    name = Column(String(255), nullable=False) #название стилей
    description = Column(String(1000)) #описание стиля
    s3_key = Column(String(512), nullable=False, unique=True) #ключ для взаимодействия с aws и данной таблицей
    is_default = Column(Boolean, default=False) #ставим не дефолт чтобы гарантировать что значения поля можно изменять 
    version = Column(String(10), default="1.0") #версия таблицы
    created_at = Column(DateTime, default=func.now()) #отслека создания таблицы с sql стороны
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now()) #отслежка добавления новых данных с sql стороны

# Таблица для хранения векторных тайлов
class VectorTile(TilesBase):
    tablename = "vector_tiles"
    # Составной первичный ключ из трех координат тайла
    zoom = Column(Integer, primary_key=True)
    x = Column(Integer, primary_key=True)
    y = Column(Integer, primary_key=True)
    # Бинарные данные тайла в формате Mapbox Vector Tile
    tile_data = Column(LargeBinary, nullable=False)
    created_at = Column(DateTime, default=func.now())  # Когда тайл был создан
    # Где хранится тайл: "database", "s3"
    storage_type = Column(String(20), default="database")
    # Путь к тайлу в S3, если используется S3
    s3_key = Column(String(512), nullable=True)

# Модель источника данных для карты (векторные тайлы)
class SourceStyle(BaseModel):
    type: str #тип тайла
    url: Optional[str] = None #url тайла
    tiles: Optional[List[str]] = None #название тайла
    minzoom: Optional[int] = 0 #установка минимального приближения при взаимодействии с картой
    maxzoom: Optional[int] = 28 #максимального отдаления

# Модель слоя карты (что и как рисовать на карте)
class LayerStyle(BaseModel):
    id: str # id-слоя
    type: str #тип слоя
    source: str #источник откуда слой
    paint: Dict[str, Any]  #определяет визуальные характеристики слоя мы задаем тд словарь т.к. это напободие CSS в сайтах мы задаем стилистические характеристики наших стилей
    layout: Optional[Dict[str, Any]] = None #управляет расположением текстовых и графических элементов: почему дикт? Пример: layout = { 'text-field:{name}, 'text-font:['OpenSans']
   
#Полная спецификация стиля карты
class MapglStyle(BaseModel):
    version: int = 8 #задаем версию
    sources: Dict[str, SourceStyle] #источники откуда импортируются все 
    layers: List[LayerStyle] #список всех загруженных в api тайлов
    sprite: Optional[str] = None #отвечает за изображения на карте например фото Китайской Стены
    glyphs: Optional[str] = None #отвечает за надписи на карте например подпись: Great Chinece Wall

    # Валидатор проверяет версию спецификации так как MapBox Style Spec не версии спецификации ниже 7 уже не поддерживаются поддерживаются только версии 7 и 8 
    @validator('version') 
    def validate_version(cls, v):
        if v not in [7, 8]:
            raise ValueError('Версия может быть 7 или 8')
        return v
    # Валидатор проверяет количество слоев
    @validator('layers')
    def validate_layers(cls, v):
        if len(v) == 0:
            raise ValueError('Нужен слой-как минимум')
        return v

# модель для создание нового стиля
class StyleCreate(BaseModel):
    name: str #название нового стиля
    description: Optional[str] = None #описание нового стиля
    style_data: MapglStyle # опозначаем что это тип данных mapgl
    is_default: bool = False #что бы мы могли изменять данные

# Модель для возврата полного стиля (метаданные из БД + JSON из S3)
class StyleResponse(BaseModel):
    id: int #Id стиля
    name: str #название стиля
    description: Optional[str] #описания стиля
    style_data: MapglStyle #подтвержаем что это mapgl тд
    is_default: bool #модно/нельзя изменять
    version: str #версия
    created_at: datetime.datetime #отслежка когда был создан
    updated_at: datetime.datetime #отслежка когда были обновлены данные
    class Config:
        from_attributes = True #ставим возможность смены атрибутов при создании модели Pydantic

# Модель для возврата метаданных стиля
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

# Модель для списка стилей
class StyleListResponse(BaseModel):
    items: List[StyleMetadataResponse]
    total: int

app = FastAPI(title="Maps API", version="1.0.0") #начала работы с самими api
try:
    app.mount("/static", StaticFiles(directory="static"), name="static") #обработка ошибки взаимодействия со статистическими файлами через app.mount 
except Exception:
    pass
# Для стилей БД
def get_styles_db():
    db = StylesSessionLocal() #получение сессии взаимодействия с бд стилей
    try:
        yield db 
    finally:
        db.close()

# Для БД тайлов
def get_tiles_db():
    db = TilesSessionLocal() 
    try:
        yield db #предоставляет работу с этой таблицей если к ней есть доступ
    finally:
        db.close() #делаем так чтобы бд закрылась после прекращения работы с ней

# Получние метаданных bucket
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
            print(f"Error creating bucket {bucket_name}: {e}") #если букет не существует выводим ошибку на стороне доступа клиента

# загрузка json стиля из s3
def get_style_from_s3(s3_key: str) -> Dict:
    try:
        # Запрашиваем объект из S3
        response = s3_client.get_object(Bucket=S3_BUCKET, Key=s3_key)
        # Читаем содержимое и декодируем из bytes в строку
        style_content = response['Body'].read().decode('utf-8')
        # Парсим JSON в Python словарь
        return json.loads(style_content)
    except ClientError as e:  
        raise HTTPException(status_code=404, detail=f"Style not found in S3: {str(e)}") #если стиль не был найден выводим ошибку доступа 404 к этому стилю  

# сохранение json стиля в s3
def save_style_to_s3(style_data: Dict) -> str:
    s3_key = f"styles/{uuid.uuid4()}.json" #создаем уникальный ключ для хранения файла стилей в Amazon S3 где "/styles"-директория в s3 для организации файлов, 
#"uuid.uuid4"-генерирует уникальный идентификатор, .json-показывает что файл должен быть сохранен в формате json
    try:
        s3_client.put_object(  #загружаем данные стиля в Amazon S3.
            Bucket=S3_BUCKET, #указываем что букет у нас принадлежит к классу s3
            Key=s3_key, #ключ типа s3
            Body=json.dumps(style_data, indent=2),  # Преобразуем словарь в JSON строку
            ContentType='application/json'  # Указываем MIME-тип
        )
        return s3_key #возращаем уникальный ключ для каждого файла
    except ClientError as e:
        raise HTTPException(status_code=500, detail=f"Error saving to S3: {str(e)}") #если уникальный ключ не сохраняется выводим ошибку на стороне клиента

# сохранение векторного тайла в s3 со сжатием
def save_tile_to_s3(z: int, x: int, y: int, tile_data: bytes) -> str:
    s3_key = f"tiles/{z}/{x}/{y}.mvt" #мы сохраняем тайлы в векторном формате mvt так как это  менее ресурсно затратно
    try:
        # Сжимаем данные с помощью gzip (уровень 5 - баланс скорости и степени сжатия) 
        compressed_data = gzip.compress(tile_data, compresslevel=5)
        s3_client.put_object( #загружаем данные тайлов в Amazon S3
            Bucket=S3_TILES_BUCKET, #все тож самое только с тайлами
            Key=s3_key,
            Body=compressed_data,  # Сохраняем СЖАТЫЕ данные
            ContentType='application/vnd.mapbox-vector-tile',
            ContentEncoding='gzip'  # ВАЖНО: указываем что данные сжаты
        )
        return s3_key #ключ хранения в s3
    except ClientError as e:
        print(f"Error saving tile to S3: {str(e)}")
        return None  #еслми произошла ошибка сохранения выводим ничего 

# загрузка сжатых векторных тайлов из s3
def get_tile_from_s3(s3_key: str) -> bytes:
    try:
        response = s3_client.get_object(Bucket=S3_TILES_BUCKET, Key=s3_key) #загружаем сами данные, находя их по букету S3 и ключу
        # Данные уже сжаты, возвращаем как есть
        return response['Body'].read()
    except ClientError:
        return None #если данные не найдены возвращаем ничего
@app.post("/styles", response_model=StyleMetadataResponse, status_code=201) #определяем продолжения создания новых стилей в api. где "/styles"-базовый путь для работы со стилями, 
# response_model-определяет структуру ответа,201-ый код-так называемый создан, стандартный код статуса все хорошо у вас все добавлено   
# API стиля функции
def create_style(style: StyleCreate , db: Session = Depends(get_styles_db)): #style:StyleCreate-модель данных для создания стиля, db: Session - сессия базы данных через dependency injection-
#встроенную систему в FastAPI, которая позволяет объявлять зависимости, Depends(get_styles_db) - автоматическое получение сессии БД
    if style.is_default:
        db.query(Style).update({Style.is_default: False}) #если стиль-дефолтный, делаем его не дефолтным чтобы можно было изменять данные в бд
    # Сохраняем JSON стиля в S3 и получаем путь
    s3_key = save_style_to_s3(style.style_data.model_dump())
    # Создаем запись в БД с метаданными
    db_style = Style(
        name=style.name,
        description=style.description,
        s3_key=s3_key,
        is_default=style.is_default
    )
    #Сохранение и обновление
    db.add(db_style)  #добавка таблицы стилей
    db.commit() #Сохраняем изменения
    db.refresh(db_style) #Обновляем объект с данными из БД
    return db_style 
@app.get("/styles", response_model=StyleListResponse) #здесь мы используем stylelistresponse-для получения ответа в виде списка

#Получить список всех стилей
def list_styles(db: Session = Depends(get_styles_db)):
    styles = db.query(Style).all() #проходимся по всем данным в бд стилей
    total = db.query(Style).count() #считаем количество
    return StyleListResponse(items=styles, total=total) #прога возвращает все данные и количество

@app.get("/styles/{style_id}", response_model=StyleResponse)
#Получить полный стиль карты по ID (метаданные + JSON из S3)
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
#удаление стиля
def delete_style(style_id: int, db: Session = Depends(get_styles_db)):
    # Находим стиль в БД
    db_style = db.query(Style).filter(Style.id == style_id).first()
    if not db_style: #если нет такой таблицы то само собой ошибка доступа 404
        raise HTTPException(status_code=404, detail="Style not found")
    # Удаляем JSON файл из S3
    try:
        s3_client.delete_object(Bucket=S3_BUCKET, Key=db_style.s3_key) #попытка удаления по букету и ключу
    except ClientError as e:
        print(f"Ошибка:S3 объект не может быть удален: {str(e)}") #если нет то ошибка на стороне клиента
    # Удаляем запись из БД
    db.delete(db_style)
    db.commit() #сохраняем изменения
    return {"message": "Удаление прошло успешно"}
# SQL шаблон для генерации векторного тайла из PostGIS
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
#ST_AsMVT(q, 'lines_tricity', 4096, 'geom') as mvt #Использует таблицу lines_tricity из схемы osm,которая хранит линейные объекты (дороги, границы и т.д.) 
# переводим в формат mvt с помощью as 
#ST_Transform(geom, 3857) - преобразует геометрию из WGS84 в Web Mercator (SRID 3857), что необходимо для совместимости с веб-картами
#ST_TileEnvelope({z}, {x}, {y}) - определяет область тайла; z - уровень масштабирования; x, y - координаты тайла в системе Web Mercator
#4096 - размер тайла в пикселях,0 - размер буфера (отсутствие буфера), true - включает обрезку геометрии
#WHERE geom && ST_Transform(ST_TileEnvelope({z}, {x}, {y}), 4326) -фильтрация данных, где мы фильтруем только геометрии, попадающие в текущий тайл
# в конце мы используем q т.к это обязательное требованиев PostgreSQL до версии 16, по сути это присвоение временного имени подзапросу в FROM


@app.get('/')
# информация о API
def root():
    return {
        "service": "Maps API",
        "version": "1.0.0",
        "modules": ["Styles API", "Vector Tiles API"],
        "tiles_storage": TILES_STORAGE_TYPE
    }

@app.get('/tiles/{z}/{x}/{y}.mvt')
# Генерирует и отдает векторный тайл в формате Mapbox Vector Tile (MVT)
def get_tiles(z: int, x: int, y: int, db: Session = Depends(get_tiles_db)):
    # Подставление координаты тайла в SQL шаблон
    sql = sql_template.format(z=z, x=x, y=y)
    try:
        # Выполняем SQL и получаем бинарные данные MVT
        result = db.execute(text(sql)).scalar()
        tile_data = bytes(result) if result is not None else b'' #проверяем что result не пустой и возвращаем битовые данные
    except SQLAlchemyError as e:
        raise HTTPException(status_code=500, detail=f"Ошибка при генерации тайла: {str(e)}") #если ничего нет то ошибка 
    # Сжимаем данные
    try:
        compressed_data = gzip.compress(tile_data, compresslevel=5)  #здесь мы используем модуль gzip для сжатия геоданных наших тайлов мы сделали 5 так как это золотая середина
    except (MemoryError, OSError) as e: #проверяем что память и ос вывозят данное сжатие для предотвращения вылета ОС 
        raise HTTPException(status_code=500, detail=f"Ошибка сжатия: {str(e)}")
    # Возвращаем сжатый тайл
    return Response( 
        content=compressed_data, #получаем наш сжатый тайл
        media_type='application/vnd.mapbox-vector-tile', #возвращаем мы его в формате mvt- векторных тайлов
        headers={'Content-Encoding': 'gzip'} #показываем что сжимали с помощью gzip
    )
    if name == 'main':
        uvicorn.run(app, host='0.0.0.0', port=8000)  #запуск api с помощью библиотеки uvicorn 








