# backend/scripts/warmup.py
import asyncio
import httpx
import logging
import os
import sys
from itertools import product

# Add parent directory to path so we can import app modules if needed
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BASE_URL = "http://localhost:8000/api"

# Years range - CHANGED FROM 2011 TO 2019
YEARS = list(range(2019, 2025))  # 2019 to 2024
FORECAST_YEARS = [2025, 2026, 2027, 2028]

# Common NAICS codes for industry detail pages
INDUSTRY_NAICS = [
    "000000",  # Cross-industry
    "541511",  # Custom Computer Programming Services
    "621111",  # Offices of Physicians
    "000001",  # Cross-industry, private
    "11",      # Agriculture, Forestry, Fishing and Hunting
    "21",      # Mining
    "22",      # Utilities
    "23",      # Construction
    "31-33",   # Manufacturing
    "42",      # Wholesale Trade
    "44-45",   # Retail Trade
    "48-49",   # Transportation and Warehousing
    "51",      # Information
    "52",      # Finance and Insurance
    "53",      # Real Estate
    "54",      # Professional, Scientific, and Technical Services
    "55",      # Management of Companies
    "56",      # Administrative and Support
    "61",      # Educational Services
    "62",      # Health Care and Social Assistance
    "71",      # Arts, Entertainment, and Recreation
    "72",      # Accommodation and Food Services
    "81",      # Other Services
    "92",      # Public Administration
]

# Common OCC codes for job detail pages
JOB_OCC_CODES = [
    "15-1252",  # Software Developers
]

# Common skill IDs for skill detail pages
SKILL_IDS = [
    "python",
    "javascript",
    "sql",
    "java",
]

async def warmup():
    logger.info("🔥 Starting comprehensive cache warmup...")
    logger.info(f"📅 Warming up for years: {YEARS[0]} to {YEARS[-1]}")
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        
        # ==================== HOME ENDPOINTS ====================
        logger.info("\n🏠 Warming up Home endpoints...")
        for year in YEARS:
            endpoints = [
                f"/home/overview?year={year}",
                f"/home/market-ticker?year={year}",
            ]
            for endpoint in endpoints:
                url = f"{BASE_URL}{endpoint}"
                try:
                    response = await client.get(url)
                    if response.status_code == 200:
                        logger.info(f"✅ Home {year}: {endpoint}")
                    else:
                        logger.warning(f"⚠️ Home {year}: {endpoint} - {response.status_code}")
                except Exception as e:
                    logger.error(f"❌ Home {year}: {endpoint} - {str(e)}")

        # ==================== INDUSTRY ENDPOINTS ====================
        logger.info("\n🏭 Warming up Industry endpoints...")
        
        # List industries for each year
        for year in YEARS:
            endpoint = f"/industries/?year={year}"
            url = f"{BASE_URL}{endpoint}"
            try:
                response = await client.get(url)
                if response.status_code == 200:
                    logger.info(f"✅ Industries list {year}")
            except Exception as e:
                logger.error(f"❌ Industries list {year}: {str(e)}")
        
        # Industry metrics for each year
        for year in YEARS:
            endpoint = f"/industries/metrics/{year}"
            url = f"{BASE_URL}{endpoint}"
            try:
                response = await client.get(url)
                if response.status_code == 200:
                    logger.info(f"✅ Industry metrics {year}")
            except Exception as e:
                logger.error(f"❌ Industry metrics {year}: {str(e)}")
        
        # Top industries by employment and salary for each year
        for year, by in product(YEARS, ["employment", "salary"]):
            endpoint = f"/industries/top?year={year}&limit=10&by={by}"
            url = f"{BASE_URL}{endpoint}"
            try:
                response = await client.get(url)
                if response.status_code == 200:
                    logger.info(f"✅ Top industries {year} by {by}")
            except Exception as e:
                logger.error(f"❌ Top industries {year} by {by}: {str(e)}")
        
        # Industry trends for various ranges (using 2019 as base instead of 2011)
        trend_ranges = [
            (2019, 2021),
            (2021, 2024),
            (2019, 2024)
        ]
        for year_from, year_to in trend_ranges:
            endpoint = f"/industries/top-trends?year_from={year_from}&year_to={year_to}&limit=10"
            url = f"{BASE_URL}{endpoint}"
            try:
                response = await client.get(url)
                if response.status_code == 200:
                    logger.info(f"✅ Industry trends {year_from}-{year_to}")
            except Exception as e:
                logger.error(f"❌ Industry trends {year_from}-{year_to}: {str(e)}")
        
        # Industry composition for each year
        for year in YEARS:
            endpoints = [
                f"/industries/composition?year={year}&limit=6",
                f"/industries/composition-top-occupations?year={year}&industries_limit=6&top_n_occ=3",
            ]
            for endpoint in endpoints:
                url = f"{BASE_URL}{endpoint}"
                try:
                    response = await client.get(url)
                    if response.status_code == 200:
                        logger.info(f"✅ Industry composition {year}")
                except Exception as e:
                    logger.error(f"❌ Industry composition {year}: {str(e)}")
        
        # Individual industry pages - REDUCED to just a few key industries
        logger.info("\n🔍 Warming up key individual industry pages...")
        key_industries = ["000000", "541511", "621111", "54", "62"]  # Reduced set
        for naics, year in product(key_industries, YEARS):
            endpoints = [
                f"/industries/{naics}/metrics?year={year}",
                f"/industries/{naics}/top-jobs?year={year}&limit=6",
            ]
            for endpoint in endpoints:
                url = f"{BASE_URL}{endpoint}"
                try:
                    response = await client.get(url)
                    if response.status_code == 200:
                        logger.info(f"✅ Industry {naics} {year}")
                except Exception as e:
                    if response.status_code != 404:
                        logger.error(f"❌ Industry {naics} {year}: {str(e)}")
            
            # Industry summaries for key ranges
            for year_from, year_to in [(2019, 2021), (2021, 2024)]:
                endpoint = f"/industries/{naics}/summary?year_from={year_from}&year_to={year_to}"
                url = f"{BASE_URL}{endpoint}"
                try:
                    response = await client.get(url)
                    if response.status_code == 200:
                        logger.info(f"✅ Industry {naics} summary {year_from}-{year_to}")
                except Exception as e:
                    if response.status_code != 404:
                        logger.error(f"❌ Industry {naics} summary: {str(e)}")

        # ==================== JOBS ENDPOINTS ====================
        logger.info("\n💼 Warming up Jobs endpoints...")
        
        # Jobs list for each year (with reduced limit)
        for year in YEARS:
            endpoint = f"/jobs/?year={year}&limit=50"  # Reduced from 100 to 50
            url = f"{BASE_URL}{endpoint}"
            try:
                response = await client.get(url)
                if response.status_code == 200:
                    logger.info(f"✅ Jobs list {year}")
            except Exception as e:
                logger.error(f"❌ Jobs list {year}: {str(e)}")
        
        # Jobs metrics for each year
        for year in YEARS:
            endpoint = f"/jobs/metrics/{year}"
            url = f"{BASE_URL}{endpoint}"
            try:
                response = await client.get(url)
                if response.status_code == 200:
                    logger.info(f"✅ Jobs metrics {year}")
            except Exception as e:
                logger.error(f"❌ Jobs metrics {year}: {str(e)}")
        
        # Jobs groups for each year
        for year in YEARS:
            endpoint = f"/jobs/groups/{year}"
            url = f"{BASE_URL}{endpoint}"
            try:
                response = await client.get(url)
                if response.status_code == 200:
                    logger.info(f"✅ Jobs groups {year}")
            except Exception as e:
                logger.error(f"❌ Jobs groups {year}: {str(e)}")
        
        # Top jobs by employment and salary for each year
        for year, by in product(YEARS, ["employment", "salary"]):
            endpoint = f"/jobs/top?year={year}&limit=10&by={by}"
            url = f"{BASE_URL}{endpoint}"
            try:
                response = await client.get(url)
                if response.status_code == 200:
                    logger.info(f"✅ Top jobs {year} by {by}")
            except Exception as e:
                logger.error(f"❌ Top jobs {year} by {by}: {str(e)}")
        
        # Job trends for key ranges only
        trend_ranges = [(2019, 2021), (2021, 2024)]
        for year_from, year_to in trend_ranges:
            for sort_by in ["employment", "salary"]:
                endpoint = f"/jobs/top-trends?year_from={year_from}&year_to={year_to}&limit=10&sort_by={sort_by}"
                url = f"{BASE_URL}{endpoint}"
                try:
                    response = await client.get(url)
                    if response.status_code == 200:
                        logger.info(f"✅ Job trends {year_from}-{year_to} by {sort_by}")
                except Exception as e:
                    logger.error(f"❌ Job trends {year_from}-{year_to}: {str(e)}")
        
        # Job salary trends for key ranges only
        for year_from, year_to in trend_ranges:
            for sort_by in ["employment", "salary"]:
                endpoint = f"/jobs/top-salary-trends?year_from={year_from}&year_to={year_to}&limit=10&sort_by={sort_by}"
                url = f"{BASE_URL}{endpoint}"
                try:
                    response = await client.get(url)
                    if response.status_code == 200:
                        logger.info(f"✅ Salary trends {year_from}-{year_to} by {sort_by}")
                except Exception as e:
                    logger.error(f"❌ Salary trends {year_from}-{year_to}: {str(e)}")
        
        # Job composition and salary distribution for each year
        for year in YEARS:
            endpoints = [
                f"/jobs/composition/{year}",
                f"/jobs/salary-distribution/{year}",
            ]
            for endpoint in endpoints:
                url = f"{BASE_URL}{endpoint}"
                try:
                    response = await client.get(url)
                    if response.status_code == 200:
                        logger.info(f"✅ Jobs {year} {endpoint.split('/')[-1]}")
                except Exception as e:
                    logger.error(f"❌ Jobs {year} {endpoint}: {str(e)}")
        
        # Individual job pages - just one job code for speed
        logger.info("\n📋 Warming up individual job pages...")
        for occ_code, year in product(JOB_OCC_CODES, YEARS):
            endpoints = [
                f"/jobs/{occ_code}/metrics?year={year}",
                f"/job-detail/{occ_code}",
            ]
            for endpoint in endpoints:
                url = f"{BASE_URL}{endpoint}"
                try:
                    response = await client.get(url)
                    if response.status_code == 200:
                        logger.info(f"✅ Job {occ_code} {year}")
                except Exception as e:
                    if response.status_code != 404:
                        logger.error(f"❌ Job {occ_code}: {str(e)}")

        # ==================== SKILLS ENDPOINTS ====================
        logger.info("\n🧠 Warming up Skills endpoints...")
        
        # Individual skill pages for each year
        for skill_id, year in product(SKILL_IDS, YEARS):
            endpoint = f"/skills/{skill_id}?year={year}"
            url = f"{BASE_URL}{endpoint}"
            try:
                response = await client.get(url)
                if response.status_code == 200:
                    logger.info(f"✅ Skill {skill_id} {year}")
            except Exception as e:
                if response.status_code != 404:
                    logger.error(f"❌ Skill {skill_id} {year}: {str(e)}")

        # ==================== SEARCH ENDPOINTS ====================
        logger.info("\n🔍 Warming up Search endpoints...")
        search_terms = ["software", "nurse", "manager"]
        for term, year in product(search_terms, YEARS):
            endpoint = f"/search/?q={term}&limit=5&year={year}"
            url = f"{BASE_URL}{endpoint}"
            try:
                response = await client.get(url)
                if response.status_code == 200:
                    logger.info(f"✅ Search {term} {year}")
            except Exception as e:
                logger.error(f"❌ Search {term}: {str(e)}")

        # ==================== SALARY & EMPLOYMENT ENDPOINTS ====================
        logger.info("\n💰 Warming up Salary & Employment endpoints...")
        for year in YEARS:
            endpoints = [
                f"/salary-employment/metrics?year={year}",
                f"/salary-employment/industries/bar?year={year}&limit=15",
                f"/salary-employment/industries?year={year}&page=1&page_size=10",
                f"/salary-employment/jobs?year={year}&page=1&page_size=10",
            ]
            for endpoint in endpoints:
                url = f"{BASE_URL}{endpoint}"
                try:
                    response = await client.get(url)
                    if response.status_code == 200:
                        logger.info(f"✅ Salary {year} {endpoint.split('?')[0]}")
                except Exception as e:
                    logger.error(f"❌ Salary {year}: {str(e)}")
        
        # Timeseries endpoints - just the most recent year
        industries = ["Technology", "Healthcare", "Retail"]
        endpoint = f"/salary-employment/industries/salary-timeseries?names={','.join(industries)}&end_year=2024"
        url = f"{BASE_URL}{endpoint}"
        try:
            response = await client.get(url)
            if response.status_code == 200:
                logger.info(f"✅ Salary timeseries 2024")
        except Exception as e:
            logger.error(f"❌ Salary timeseries: {str(e)}")

        # ==================== FORECAST ENDPOINTS ====================
        logger.info("\n🔮 Warming up Forecast endpoints...")
        for forecast_year in FORECAST_YEARS:
            endpoint = f"/forecast/?year={forecast_year}"
            url = f"{BASE_URL}{endpoint}"
            try:
                response = await client.get(url)
                if response.status_code == 200:
                    logger.info(f"✅ Forecast {forecast_year}")
            except Exception as e:
                logger.error(f"❌ Forecast {forecast_year}: {str(e)}")

        # ==================== OCCUPATIONS ENDPOINTS ====================
        logger.info("\n📊 Warming up Occupations endpoints...")
        for year in YEARS:
            endpoint = f"/occupations/metrics/{year}?limit=50"  # Reduced limit
            url = f"{BASE_URL}{endpoint}"
            try:
                response = await client.get(url)
                if response.status_code == 200:
                    logger.info(f"✅ Occupations metrics {year}")
            except Exception as e:
                logger.error(f"❌ Occupations metrics {year}: {str(e)}")

    logger.info("\n✅ Cache warmup complete for years 2019-2024!")

if __name__ == "__main__":
    asyncio.run(warmup())