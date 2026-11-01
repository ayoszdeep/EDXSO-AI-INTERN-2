"""
Crawler Scheduler.
Runs automatic periodic scholarship crawls using APScheduler.
"""
import logging
from apscheduler.schedulers.blocking import BlockingScheduler
from crawler.pipeline import ScholarshipCrawlerPipeline

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


def scheduled_crawl_job():
    logger.info("Starting scheduled scholarship intelligence crawl...")
    pipeline = ScholarshipCrawlerPipeline()
    try:
        results = pipeline.run_crawler(use_search=False, verbose=True)
        logger.info(f"Scheduled crawl finished successfully: {results}")
    except Exception as e:
        logger.error(f"Error during scheduled crawl job: {e}", exc_info=True)


def start_scheduler(interval_hours: int = 24):
    scheduler = BlockingScheduler()
    scheduler.add_job(
        scheduled_crawl_job,
        trigger="interval",
        hours=interval_hours,
        id="daily_scholarship_crawl",
        max_instances=1,
        coalesce=True,
    )
    logger.info(f"Scholarship Intelligence Scheduler started. Interval: {interval_hours} hours. Press Ctrl+C to exit.")
    try:
        # Run immediately once on startup, then continue on interval
        scheduled_crawl_job()
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        logger.info("Scheduler stopped by user.")


if __name__ == "__main__":
    start_scheduler()
