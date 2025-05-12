from fastapi import FastAPI, BackgroundTasks
from apscheduler.schedulers.background import BackgroundScheduler
from .database.database import engine, Base
from .scraper.scraper import run_scraper
import logging

# Veritabanı tablolarını oluştur
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Campground Scraper API")
logger = logging.getLogger(__name__)

scheduler = BackgroundScheduler()

@app.on_event("startup")
async def startup_event():
    scheduler.add_job(run_scraper, 'cron', hour=0, minute=0, id='daily_scraper')
    scheduler.start()
    logger.info("APScheduler başlatıldı ve günlük scraping job'u eklendi.")

@app.on_event("shutdown")
def shutdown_event():
    scheduler.shutdown()
    logger.info("APScheduler kapatıldı.")

@app.post("/run-scraper")
async def trigger_scraper(background_tasks: BackgroundTasks):
    background_tasks.add_task(run_scraper)
    return {"status": "started"}

@app.get("/health")
async def health_check():
    return {"status": "healthy"} 