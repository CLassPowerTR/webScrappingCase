from sqlalchemy import Column, String, Float, Boolean, Integer, DateTime, ARRAY
from sqlalchemy.dialects.postgresql import ARRAY
from .database import Base

class Campground(Base):
    __tablename__ = "campgrounds"

    id = Column(String, primary_key=True)
    type = Column(String)
    name = Column(String)
    latitude = Column(Float)
    longitude = Column(Float)
    region_name = Column(String)
    administrative_area = Column(String, nullable=True)
    nearest_city_name = Column(String, nullable=True)
    accommodation_type_names = Column(ARRAY(String))
    bookable = Column(Boolean, default=False)
    camper_types = Column(ARRAY(String))
    operator = Column(String, nullable=True)
    photo_url = Column(String, nullable=True)
    photo_urls = Column(ARRAY(String))
    photos_count = Column(Integer, default=0)
    rating = Column(Float, nullable=True)
    reviews_count = Column(Integer, default=0)
    slug = Column(String, nullable=True)
    price_low = Column(Float, nullable=True)
    price_high = Column(Float, nullable=True)
    availability_updated_at = Column(DateTime, nullable=True)
    address = Column(String, nullable=True)
    state = Column(String, nullable=True)
    nearest_city = Column(String, nullable=True)
    elevation = Column(Float, nullable=True)
    tile_id = Column(String, nullable=True) 