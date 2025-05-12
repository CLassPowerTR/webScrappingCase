import asyncio
import httpx
from typing import List, Dict, Any
import logging
from tenacity import retry, stop_after_attempt, wait_exponential
from ..models.campground import Campground
from ..database.database import SessionLocal
from ..database.models import Campground as CampgroundDB
from logging.handlers import RotatingFileHandler
from concurrent.futures import ThreadPoolExecutor
from geopy.geocoders import Nominatim
from geopy.extra.rate_limiter import RateLimiter
import requests

log_formatter = logging.Formatter('%(asctime)s [%(levelname)s] %(message)s')
log_file = "scraper.log"
file_handler = RotatingFileHandler(log_file, maxBytes=2*1024*1024, backupCount=5)
file_handler.setFormatter(log_formatter)
file_handler.setLevel(logging.INFO)

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
if not logger.hasHandlers():
    logger.addHandler(file_handler)

API_URL = "https://thedyrt.com/api/v3/campgrounds/search"

GRID_BOXES = [
    {"neLat": 42.1, "neLng": 35.0, "swLat": 39.0, "swLng": 25.9},
    {"neLat": 42.1, "neLng": 44.8, "swLat": 39.0, "swLng": 35.0},
    {"neLat": 39.0, "neLng": 35.0, "swLat": 35.8, "swLng": 25.9},
    {"neLat": 39.0, "neLng": 44.8, "swLat": 35.8, "swLng": 35.0},
]

reverse_cache = {}
geolocator = Nominatim(user_agent="campground_scraper")
reverse = RateLimiter(geolocator.reverse, min_delay_seconds=1)

class DyrtScraper:
    def __init__(self):
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    async def fetch_campgrounds(self, client: httpx.AsyncClient, params: dict) -> List[Dict[str, Any]]:
        try:
            response = await client.get(API_URL, params=params)
            response.raise_for_status()
            data = response.json()
            return data.get("data", [])
        except Exception as e:
            logger.error(f"Error fetching campgrounds: {e}")
            raise

    async def process_campground(self, campground_data: Dict[str, Any], db: SessionLocal):
        try:
            campground = Campground(**campground_data)
            db_campground = CampgroundDB(
                id=campground.id,
                type=campground.type,
                name=campground.name,
                latitude=campground.latitude,
                longitude=campground.longitude,
                region_name=campground.region_name,
                administrative_area=campground.administrative_area,
                nearest_city_name=campground.nearest_city_name,
                accommodation_type_names=campground.accommodation_type_names,
                bookable=campground.bookable,
                camper_types=campground.camper_types,
                operator=campground.operator,
                photo_url=str(campground.photo_url) if campground.photo_url else None,
                photo_urls=[str(url) for url in campground.photo_urls],
                photos_count=campground.photos_count,
                rating=campground.rating,
                reviews_count=campground.reviews_count,
                slug=campground.slug,
                price_low=campground.price_low,
                price_high=campground.price_high,
                availability_updated_at=campground.availability_updated_at
            )
            existing = db.query(CampgroundDB).filter(CampgroundDB.id == campground.id).first()
            if existing:
                for key, value in db_campground.__dict__.items():
                    if key != '_sa_instance_state':
                        setattr(existing, key, value)
            else:
                db.add(db_campground)
            db.commit()
        except Exception as e:
            logger.error(f"Error processing campground {campground_data.get('id', 'unknown')}: {e}")
            db.rollback()

    def get_address_info_from_latlon(self, lat, lon):
        key = (round(lat, 5), round(lon, 5))
        if key in reverse_cache:
            return reverse_cache[key]
        try:
            location = reverse(f"{lat}, {lon}", language="en", addressdetails=True)
            address = location.address if location else None
            address_dict = location.raw.get("address", {}) if location else {}
            state = address_dict.get("state")
            city = address_dict.get("city") or address_dict.get("town") or address_dict.get("village")
            elevation = None
            try:
                resp = requests.get(f'https://api.open-elevation.com/api/v1/lookup?locations={lat},{lon}')
                if resp.status_code == 200:
                    elevation = resp.json()["results"][0]["elevation"]
            except Exception as e:
                logger.warning(f"Elevation API error: {e}")
            tile_id = f"{int(lat*100)}_{int(lon*100)}"
            result = {"address": address, "state": state, "nearest_city": city, "elevation": elevation, "tile_id": tile_id}
            reverse_cache[key] = result
            return result
        except Exception as e:
            logger.error(f"Reverse geocoding error for {lat},{lon}: {e}")
            return {"address": None, "state": None, "nearest_city": None, "elevation": None, "tile_id": None}

    async def bulk_upsert_campgrounds(self, campgrounds: list, db: SessionLocal):
        loop = asyncio.get_running_loop()
        db_objects = []

        def validate_and_create(campground_data):
            try:
                campground = Campground(**campground_data)
                info = self.get_address_info_from_latlon(campground.latitude, campground.longitude)
                return CampgroundDB(
                    id=campground.id,
                    type=campground.type,
                    name=campground.name,
                    latitude=campground.latitude,
                    longitude=campground.longitude,
                    region_name=campground.region_name,
                    administrative_area=campground.administrative_area,
                    nearest_city_name=campground.nearest_city_name,
                    accommodation_type_names=campground.accommodation_type_names,
                    bookable=campground.bookable,
                    camper_types=campground.camper_types,
                    operator=campground.operator,
                    photo_url=str(campground.photo_url) if campground.photo_url else None,
                    photo_urls=[str(url) for url in campground.photo_urls],
                    photos_count=campground.photos_count,
                    rating=campground.rating,
                    reviews_count=campground.reviews_count,
                    slug=campground.slug,
                    price_low=campground.price_low,
                    price_high=campground.price_high,
                    availability_updated_at=campground.availability_updated_at,
                    address=info["address"],
                    state=info["state"],
                    nearest_city=info["nearest_city"],
                    elevation=info["elevation"],
                    tile_id=info["tile_id"]
                )
            except Exception as e:
                logger.error(f"Error validating campground {campground_data.get('id', 'unknown')}: {e}")
                return None

        with ThreadPoolExecutor() as executor:
            results = await asyncio.gather(
                *[loop.run_in_executor(executor, validate_and_create, data) for data in campgrounds]
            )
            db_objects = [obj for obj in results if obj is not None]

        for obj in db_objects:
            existing = db.query(CampgroundDB).filter(CampgroundDB.id == obj.id).first()
            if existing:
                for key, value in obj.__dict__.items():
                    if key != '_sa_instance_state':
                        setattr(existing, key, value)
            else:
                db.add(obj)
        db.commit()

    async def scrape_all_campgrounds(self):
        db = SessionLocal()
        async with httpx.AsyncClient(headers=self.headers, timeout=30) as client:
            tasks = []
            for box in GRID_BOXES:
                params = {
                    "neLat": box["neLat"],
                    "neLng": box["neLng"],
                    "swLat": box["swLat"],
                    "swLng": box["swLng"]
                }
                tasks.append(self.fetch_campgrounds(client, params))
            all_campgrounds = []
            results = await asyncio.gather(*tasks, return_exceptions=True)
            for result in results:
                if isinstance(result, Exception):
                    continue
                all_campgrounds.extend(result)
            logger.info(f"Toplam {len(all_campgrounds)} kamp alanı bulundu.")
            await self.bulk_upsert_campgrounds(all_campgrounds, db)
            logger.info(f"Başarıyla {len(all_campgrounds)} kamp alanı kazındı ve veritabanına işlendi.")
        db.close()

def run_scraper():
    scraper = DyrtScraper()
    asyncio.run(scraper.scrape_all_campgrounds()) 