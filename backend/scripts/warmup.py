# backend/scripts/warmup.py
import asyncio
import httpx
import logging
import os
import sys

# Add parent directory to path so we can import app modules if needed
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BASE_URL = "http://localhost:8000/api"

# All the endpoints we want to warm up
ENDPOINTS = [
    # Home endpoints
    "/home/overview?year=2024",
    "/home/industry-distribution?year=2024&limit=8",
    "/home/top-jobs?year=2024&limit=8",
    "/home/employment-trends?year_from=2019&year_to=2024&limit=3",
    
    # Industry endpoints
    "/industries/?year=2024",
    "/industries/metrics/2024",
    "/industries/top?year=2024&limit=10&by=employment",
    "/industries/top?year=2024&limit=10&by=salary",
    "/industries/top-trends?year_from=2019&year_to=2024&limit=10",
    "/industries/composition?year=2024&limit=6",
    "/industries/composition-top-occupations?year=2024&industries_limit=6&top_n_occ=3",
    
    # Jobs endpoints
    "/jobs/metrics/2024",
    "/jobs/groups/2024",
    "/jobs/top?year=2024&limit=10&by=employment",
    "/jobs/top?year=2024&limit=10&by=salary",
    "/jobs/top-trends?year_from=2011&year_to=2024&limit=10&sort_by=employment",
    "/jobs/top-trends?year_from=2011&year_to=2024&limit=10&sort_by=salary",
    "/jobs/top-salary-trends?year_from=2011&year_to=2024&limit=10&sort_by=employment",
    "/jobs/top-salary-trends?year_from=2011&year_to=2024&limit=10&sort_by=salary",
    "/jobs/top-combined?year=2024&limit=10&by=employment",
    "/jobs/top-combined?year=2024&limit=10&by=salary",
    "/jobs/composition/2024",
    "/jobs/salary-distribution/2024",
    
    # Forecast endpoints
    # "/forecast/?year=2025",
    # "/forecast/industries?limit=6&forecast_years=4",
    # "/forecast/jobs?limit=8&forecast_years=4",
    
    # Salary & Employment endpoints
    "/salary-employment/metrics?year=2024",
    "/salary-employment/industries/bar?year=2024&limit=15",
    "/salary-employment/industries?year=2024&page=1&page_size=10",
    "/salary-employment/jobs?year=2024&page=1&page_size=10",
    "/salary-employment/jobs/top-cross-industry?year=2024&limit=10",
    
    # Occupations endpoints
    "/occupations/metrics/2024?limit=100",
    "/occupations/industry/000000/metrics/2024?limit=100",
    
    # Job Detail endpoints (for top jobs)
    "/job-detail/15-1252",  # Software Developers
    "/job-detail/29-1141",  # Registered Nurses
    "/job-detail/13-2011",  # Accountants
    "/job-detail/15-1252/skills?limit=20",
    "/job-detail/15-1252/technology-skills",
    "/job-detail/15-1252/abilities?limit=10",
    "/job-detail/15-1252/knowledge?limit=10",
    
    # Skills endpoints (for top skills)
    "/skills/python",
    "/skills/javascript",
    "/skills/sql",
]

# Also warm up specific industry and job detail pages for top items
INDUSTRY_NAICS = [
    "000000",  # Cross-industry
    "541511",  # Custom Computer Programming Services
    "621111",  # Offices of Physicians
]

JOB_OCC_CODES = [
    "15-1252",  # Software Developers
    "29-1141",  # Registered Nurses
    "13-2011",  # Accountants
]

async def warmup():
    logger.info("🔥 Starting cache warmup...")
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        # Warm up main endpoints
        for endpoint in ENDPOINTS:
            url = f"{BASE_URL}{endpoint}"
            try:
                logger.info(f"Fetching {url}")
                response = await client.get(url)
                if response.status_code == 200:
                    logger.info(f"✅ Success: {endpoint}")
                else:
                    logger.warning(f"⚠️  Failed ({response.status_code}): {endpoint}")
            except Exception as e:
                logger.error(f"❌ Error: {endpoint} - {str(e)}")
        
        # Warm up individual industry pages
        for naics in INDUSTRY_NAICS:
            endpoints = [
                f"/industries/{naics}/metrics?year=2024",
                f"/industries/{naics}/jobs?year=2024&limit=10",
                f"/industries/{naics}/top-jobs?year=2024&limit=6",
                f"/industries/{naics}/summary?year_from=2019&year_to=2024",
            ]
            for endpoint in endpoints:
                url = f"{BASE_URL}{endpoint}"
                try:
                    logger.info(f"Fetching {url}")
                    response = await client.get(url)
                    if response.status_code == 200:
                        logger.info(f"✅ Success: {endpoint}")
                except Exception as e:
                    logger.error(f"❌ Error: {endpoint} - {str(e)}")
        
        # Warm up individual job pages
        for occ_code in JOB_OCC_CODES:
            endpoints = [
                f"/jobs/{occ_code}/metrics?year=2024",
                f"/jobs/{occ_code}/summary?year_from=2019&year_to=2024",
                f"/job-detail/{occ_code}",
            ]
            for endpoint in endpoints:
                url = f"{BASE_URL}{endpoint}"
                try:
                    logger.info(f"Fetching {url}")
                    response = await client.get(url)
                    if response.status_code == 200:
                        logger.info(f"✅ Success: {endpoint}")
                except Exception as e:
                    logger.error(f"❌ Error: {endpoint} - {str(e)}")
    
    logger.info("✅ Cache warmup complete!")

if __name__ == "__main__":
    asyncio.run(warmup())