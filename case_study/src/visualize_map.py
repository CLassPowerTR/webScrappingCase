import folium
from database.database import SessionLocal
from database.models import Campground

def create_map():
    db = SessionLocal()
    campgrounds = db.query(Campground).all()
    db.close()
    m = folium.Map(location=[39, -98], zoom_start=4)
    for cg in campgrounds:
        popup = f"{cg.name}<br>{cg.address or ''}<br>{cg.state or ''}<br>{cg.nearest_city or ''}<br>Yükseklik: {cg.elevation or ''}"
        folium.Marker(
            [cg.latitude, cg.longitude],
            popup=popup
        ).add_to(m)
    m.save("campgrounds_map.html")

if __name__ == "__main__":
    create_map() 