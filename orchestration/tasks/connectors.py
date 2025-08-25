"""
Data connector tasks for various external APIs and sources
"""

import asyncio
import json
import re
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
import httpx
import pandas as pd
from prefect import task, get_run_logger
from prefect.blocks.system import Secret
import pdfplumber
import spacy
from bs4 import BeautifulSoup


@task(retries=3, retry_delay_seconds=60)
async def fetch_nyc_311_data(
    start_date: str,
    end_date: str,
    limit: int = 10000
) -> List[Dict[str, Any]]:
    """
    Fetch NYC 311 service request data from NYC Open Data API
    """
    logger = get_run_logger()
    
    # NYC Open Data API endpoint for 311 requests
    base_url = "https://data.cityofnewyork.us/resource/erm2-nwe9.json"
    
    params = {
        "$limit": limit,
        "$where": f"created_date between '{start_date}T00:00:00' and '{end_date}T23:59:59'",
        "$order": "created_date DESC"
    }
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(base_url, params=params)
            response.raise_for_status()
            
            data = response.json()
            logger.info(f"Successfully fetched {len(data)} records from NYC 311 API")
            
            # Clean and standardize data
            cleaned_data = []
            for record in data:
                cleaned_record = {
                    "unique_key": record.get("unique_key"),
                    "created_date": record.get("created_date"),
                    "closed_date": record.get("closed_date"),
                    "agency": record.get("agency"),
                    "agency_name": record.get("agency_name"),
                    "complaint_type": record.get("complaint_type"),
                    "descriptor": record.get("descriptor"),
                    "location_type": record.get("location_type"),
                    "incident_zip": record.get("incident_zip"),
                    "incident_address": record.get("incident_address"),
                    "street_name": record.get("street_name"),
                    "cross_street_1": record.get("cross_street_1"),
                    "cross_street_2": record.get("cross_street_2"),
                    "intersection_street_1": record.get("intersection_street_1"),
                    "intersection_street_2": record.get("intersection_street_2"),
                    "address_type": record.get("address_type"),
                    "city": record.get("city"),
                    "landmark": record.get("landmark"),
                    "facility_type": record.get("facility_type"),
                    "status": record.get("status"),
                    "due_date": record.get("due_date"),
                    "resolution_description": record.get("resolution_description"),
                    "resolution_action_updated_date": record.get("resolution_action_updated_date"),
                    "community_board": record.get("community_board"),
                    "bbl": record.get("bbl"),
                    "borough": record.get("borough"),
                    "x_coordinate_state_plane": record.get("x_coordinate_state_plane"),
                    "y_coordinate_state_plane": record.get("y_coordinate_state_plane"),
                    "open_data_channel_type": record.get("open_data_channel_type"),
                    "park_facility_name": record.get("park_facility_name"),
                    "park_borough": record.get("park_borough"),
                    "vehicle_type": record.get("vehicle_type"),
                    "taxi_company_borough": record.get("taxi_company_borough"),
                    "taxi_pick_up_location": record.get("taxi_pick_up_location"),
                    "bridge_highway_name": record.get("bridge_highway_name"),
                    "bridge_highway_direction": record.get("bridge_highway_direction"),
                    "road_ramp": record.get("road_ramp"),
                    "bridge_highway_segment": record.get("bridge_highway_segment"),
                    "latitude": float(record["latitude"]) if record.get("latitude") else None,
                    "longitude": float(record["longitude"]) if record.get("longitude") else None,
                    "location": record.get("location"),
                    "source": "NYC_311",
                    "ingested_at": datetime.now().isoformat()
                }
                cleaned_data.append(cleaned_record)
            
            return cleaned_data
            
    except httpx.HTTPError as e:
        logger.error(f"HTTP error fetching NYC 311 data: {str(e)}")
        raise
    except Exception as e:
        logger.error(f"Error fetching NYC 311 data: {str(e)}")
        raise


@task(retries=3, retry_delay_seconds=60)
async def fetch_epa_air_quality(
    state: str,
    pollutant: str,
    begin_date: datetime,
    end_date: datetime
) -> List[Dict[str, Any]]:
    """
    Fetch EPA air quality data from Air Quality System (AQS) API
    """
    logger = get_run_logger()
    
    # Note: This requires EPA API key - in production, store in Prefect Secret
    try:
        epa_api_key = await Secret.load("epa-api-key")
        api_key = epa_api_key.get()
    except:
        logger.warning("EPA API key not found, using demo data")
        return _generate_demo_air_quality_data(state, pollutant, begin_date, end_date)
    
    base_url = "https://aqs.epa.gov/data/api/dailyData/byState"
    
    params = {
        "email": "your-email@example.com",  # Required by EPA API
        "key": api_key,
        "param": pollutant,
        "bdate": begin_date.strftime("%Y%m%d"),
        "edate": end_date.strftime("%Y%m%d"),
        "state": state
    }
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(base_url, params=params)
            response.raise_for_status()
            
            data = response.json()
            
            if data.get("Header", [{}])[0].get("status") != "Success":
                logger.warning(f"EPA API returned non-success status: {data}")
                return []
            
            records = data.get("Data", [])
            logger.info(f"Successfully fetched {len(records)} air quality records for {state}/{pollutant}")
            
            # Clean and standardize data
            cleaned_data = []
            for record in records:
                cleaned_record = {
                    "state_code": record.get("state_code"),
                    "county_code": record.get("county_code"),
                    "site_num": record.get("site_num"),
                    "parameter_code": record.get("parameter_code"),
                    "poc": record.get("poc"),
                    "latitude": record.get("latitude"),
                    "longitude": record.get("longitude"),
                    "datum": record.get("datum"),
                    "parameter_name": record.get("parameter_name"),
                    "sample_duration": record.get("sample_duration"),
                    "pollutant_standard": record.get("pollutant_standard"),
                    "date_local": record.get("date_local"),
                    "units_of_measure": record.get("units_of_measure"),
                    "event_type": record.get("event_type"),
                    "observation_count": record.get("observation_count"),
                    "observation_percent": record.get("observation_percent"),
                    "arithmetic_mean": record.get("arithmetic_mean"),
                    "first_max_value": record.get("first_max_value"),
                    "first_max_hour": record.get("first_max_hour"),
                    "aqi": record.get("aqi"),
                    "method_code": record.get("method_code"),
                    "method_name": record.get("method_name"),
                    "local_site_name": record.get("local_site_name"),
                    "address": record.get("address"),
                    "state_name": record.get("state_name"),
                    "county_name": record.get("county_name"),
                    "city_name": record.get("city_name"),
                    "cbsa_name": record.get("cbsa_name"),
                    "date_of_last_change": record.get("date_of_last_change"),
                    "source": "EPA_AQS",
                    "ingested_at": datetime.now().isoformat()
                }
                cleaned_data.append(cleaned_record)
            
            return cleaned_data
            
    except httpx.HTTPError as e:
        logger.error(f"HTTP error fetching EPA data: {str(e)}")
        raise
    except Exception as e:
        logger.error(f"Error fetching EPA data: {str(e)}")
        raise


@task(retries=2, retry_delay_seconds=30)
async def fetch_census_data(
    variables: List[str],
    geography: str = "state:*",
    year: int = 2022
) -> List[Dict[str, Any]]:
    """
    Fetch US Census data from Census API
    """
    logger = get_run_logger()
    
    try:
        census_api_key = await Secret.load("census-api-key")
        api_key = census_api_key.get()
    except:
        logger.warning("Census API key not found, using demo data")
        return _generate_demo_census_data(variables, geography, year)
    
    base_url = f"https://api.census.gov/data/{year}/acs/acs5"
    
    params = {
        "get": ",".join(variables + ["NAME"]),
        "for": geography,
        "key": api_key
    }
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(base_url, params=params)
            response.raise_for_status()
            
            data = response.json()
            
            if not data:
                logger.warning("No data returned from Census API")
                return []
            
            # First row contains headers
            headers = data[0]
            records = data[1:]
            
            logger.info(f"Successfully fetched {len(records)} census records")
            
            # Convert to list of dictionaries
            cleaned_data = []
            for record in records:
                cleaned_record = dict(zip(headers, record))
                cleaned_record.update({
                    "year": year,
                    "source": "US_Census",
                    "ingested_at": datetime.now().isoformat()
                })
                cleaned_data.append(cleaned_record)
            
            return cleaned_data
            
    except httpx.HTTPError as e:
        logger.error(f"HTTP error fetching Census data: {str(e)}")
        raise
    except Exception as e:
        logger.error(f"Error fetching Census data: {str(e)}")
        raise


@task(retries=2, retry_delay_seconds=30)
async def fetch_who_health_data(
    indicators: List[str] = None,
    countries: List[str] = None
) -> List[Dict[str, Any]]:
    """
    Fetch WHO health data from WHO API
    """
    logger = get_run_logger()
    
    if not indicators:
        indicators = ["WHS4_100", "WHS4_544", "WHS7_156"]  # Sample health indicators
    
    if not countries:
        countries = ["USA", "CAN", "MEX", "GBR", "DEU", "FRA"]  # Sample countries
    
    base_url = "https://ghoapi.azureedge.net/api"
    
    try:
        all_data = []
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            for indicator in indicators:
                for country in countries:
                    url = f"{base_url}/{indicator}"
                    params = {"$filter": f"SpatialDim eq '{country}'"}
                    
                    try:
                        response = await client.get(url, params=params)
                        response.raise_for_status()
                        
                        data = response.json()
                        values = data.get("value", [])
                        
                        for value in values:
                            cleaned_record = {
                                "indicator_code": indicator,
                                "country_code": value.get("SpatialDim"),
                                "year": value.get("TimeDim"),
                                "value": value.get("NumericValue"),
                                "display_value": value.get("DisplayValue"),
                                "low": value.get("Low"),
                                "high": value.get("High"),
                                "comments": value.get("Comments"),
                                "date": value.get("Date"),
                                "source": "WHO_GHO",
                                "ingested_at": datetime.now().isoformat()
                            }
                            all_data.append(cleaned_record)
                        
                        # Small delay to be respectful to the API
                        await asyncio.sleep(0.1)
                        
                    except httpx.HTTPError as e:
                        logger.warning(f"Failed to fetch WHO data for {indicator}/{country}: {str(e)}")
                        continue
        
        logger.info(f"Successfully fetched {len(all_data)} WHO health records")
        return all_data
        
    except Exception as e:
        logger.error(f"Error fetching WHO data: {str(e)}")
        raise


@task(retries=2, retry_delay_seconds=30)
async def fetch_climate_data(
    parameters: List[str] = None,
    stations: List[str] = None,
    start_date: str = None,
    end_date: str = None
) -> List[Dict[str, Any]]:
    """
    Fetch climate data from NOAA API
    """
    logger = get_run_logger()
    
    try:
        noaa_api_key = await Secret.load("noaa-api-key")
        api_key = noaa_api_key.get()
    except:
        logger.warning("NOAA API key not found, using demo data")
        return _generate_demo_climate_data(parameters, start_date, end_date)
    
    if not parameters:
        parameters = ["TMAX", "TMIN", "PRCP"]  # Temperature max/min, precipitation
    
    if not start_date:
        start_date = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
    if not end_date:
        end_date = datetime.now().strftime("%Y-%m-%d")
    
    base_url = "https://www.ncdc.noaa.gov/cdo-web/api/v2/data"
    
    headers = {"token": api_key}
    params = {
        "datasetid": "GHCND",  # Global Historical Climatology Network Daily
        "datatypeid": ",".join(parameters),
        "startdate": start_date,
        "enddate": end_date,
        "limit": 1000
    }
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(base_url, headers=headers, params=params)
            response.raise_for_status()
            
            data = response.json()
            results = data.get("results", [])
            
            logger.info(f"Successfully fetched {len(results)} climate records")
            
            # Clean and standardize data
            cleaned_data = []
            for record in results:
                cleaned_record = {
                    "station": record.get("station"),
                    "date": record.get("date"),
                    "datatype": record.get("datatype"),
                    "value": record.get("value"),
                    "measurement_flag": record.get("fl_m"),
                    "quality_flag": record.get("fl_q"),
                    "source_flag": record.get("fl_so"),
                    "time_of_observation": record.get("fl_t"),
                    "source": "NOAA_GHCND",
                    "ingested_at": datetime.now().isoformat()
                }
                cleaned_data.append(cleaned_record)
            
            return cleaned_data
            
    except httpx.HTTPError as e:
        logger.error(f"HTTP error fetching NOAA data: {str(e)}")
        raise
    except Exception as e:
        logger.error(f"Error fetching NOAA data: {str(e)}")
        raise


@task(retries=2, retry_delay_seconds=30)
async def process_pdf_documents(
    urls: List[str],
    extract_metadata: bool = True,
    chunk_size: int = 1000,
    overlap: int = 100
) -> List[Dict[str, Any]]:
    """
    Download and process PDF documents, extracting text and metadata
    """
    logger = get_run_logger()
    
    # Load spaCy model for text processing
    try:
        nlp = spacy.load("en_core_web_sm")
    except OSError:
        logger.warning("spaCy model not found, using simple text processing")
        nlp = None
    
    processed_docs = []
    
    async with httpx.AsyncClient(timeout=60.0) as client:
        for url in urls:
            try:
                logger.info(f"Processing PDF from: {url}")
                
                # Download PDF
                response = await client.get(url)
                response.raise_for_status()
                
                # Process PDF with pdfplumber
                with pdfplumber.open(io.BytesIO(response.content)) as pdf:
                    # Extract metadata
                    metadata = {
                        "source_url": url,
                        "total_pages": len(pdf.pages),
                        "pdf_metadata": pdf.metadata or {},
                        "processed_at": datetime.now().isoformat()
                    }
                    
                    # Extract text from each page
                    full_text = ""
                    for page_num, page in enumerate(pdf.pages):
                        page_text = page.extract_text() or ""
                        full_text += page_text + "\n"
                        
                        # Store page-level chunks if text is substantial
                        if len(page_text.strip()) > 100:
                            page_metadata = metadata.copy()
                            page_metadata.update({
                                "page_number": page_num + 1,
                                "chunk_type": "page"
                            })
                            
                            processed_docs.append({
                                "document_id": f"pdf_{hash(url)}"[:16],
                                "chunk_id": f"page_{page_num + 1}",
                                "title": _extract_title_from_text(page_text) or f"Document Page {page_num + 1}",
                                "content": page_text.strip(),
                                "source_url": url,
                                "page_number": page_num + 1,
                                "language": _detect_language(page_text),
                                "metadata": page_metadata,
                                "source": "PDF_Document",
                                "ingested_at": datetime.now().isoformat()
                            })
                    
                    # Create semantic chunks from full text
                    if full_text.strip() and chunk_size > 0:
                        chunks = _create_text_chunks(full_text, chunk_size, overlap)
                        
                        for i, chunk in enumerate(chunks):
                            chunk_metadata = metadata.copy()
                            chunk_metadata.update({
                                "chunk_index": i,
                                "chunk_type": "semantic",
                                "total_chunks": len(chunks)
                            })
                            
                            processed_docs.append({
                                "document_id": f"pdf_{hash(url)}"[:16],
                                "chunk_id": f"chunk_{i}",
                                "title": _extract_title_from_text(chunk) or f"Document Chunk {i + 1}",
                                "content": chunk.strip(),
                                "source_url": url,
                                "page_number": None,  # Spans multiple pages
                                "language": _detect_language(chunk),
                                "metadata": chunk_metadata,
                                "source": "PDF_Document",
                                "ingested_at": datetime.now().isoformat()
                            })
                
                logger.info(f"Successfully processed PDF: {url} ({len(processed_docs)} chunks)")
                
            except Exception as e:
                logger.error(f"Failed to process PDF {url}: {str(e)}")
                continue
    
    return processed_docs


# Helper functions for demo data when APIs are unavailable

def _generate_demo_air_quality_data(state: str, pollutant: str, begin_date: datetime, end_date: datetime) -> List[Dict[str, Any]]:
    """Generate demo air quality data for testing"""
    import random
    
    demo_data = []
    current_date = begin_date
    
    while current_date <= end_date:
        demo_data.append({
            "state_code": state,
            "county_code": "001",
            "site_num": "0001",
            "parameter_code": pollutant,
            "date_local": current_date.strftime("%Y-%m-%d"),
            "arithmetic_mean": round(random.uniform(10, 50), 2),
            "aqi": random.randint(20, 100),
            "parameter_name": "Demo Pollutant",
            "units_of_measure": "µg/m³",
            "latitude": round(random.uniform(25, 45), 6),
            "longitude": round(random.uniform(-125, -70), 6),
            "source": "EPA_AQS_DEMO",
            "ingested_at": datetime.now().isoformat()
        })
        current_date += timedelta(days=1)
    
    return demo_data


def _generate_demo_census_data(variables: List[str], geography: str, year: int) -> List[Dict[str, Any]]:
    """Generate demo census data for testing"""
    import random
    
    states = ["Alabama", "Alaska", "Arizona", "Arkansas", "California"]
    demo_data = []
    
    for state in states:
        record = {"NAME": state}
        for var in variables:
            record[var] = random.randint(10000, 1000000)
        record.update({
            "year": year,
            "source": "US_Census_DEMO",
            "ingested_at": datetime.now().isoformat()
        })
        demo_data.append(record)
    
    return demo_data


def _generate_demo_climate_data(parameters: List[str], start_date: str, end_date: str) -> List[Dict[str, Any]]:
    """Generate demo climate data for testing"""
    import random
    
    demo_data = []
    current_date = datetime.strptime(start_date, "%Y-%m-%d") if start_date else datetime.now() - timedelta(days=7)
    end = datetime.strptime(end_date, "%Y-%m-%d") if end_date else datetime.now()
    
    while current_date <= end:
        for param in (parameters or ["TMAX", "TMIN", "PRCP"]):
            demo_data.append({
                "station": "DEMO_STATION_001",
                "date": current_date.strftime("%Y-%m-%d"),
                "datatype": param,
                "value": random.randint(-100, 400) if param in ["TMAX", "TMIN"] else random.randint(0, 100),
                "source": "NOAA_GHCND_DEMO",
                "ingested_at": datetime.now().isoformat()
            })
        current_date += timedelta(days=1)
    
    return demo_data


def _extract_title_from_text(text: str) -> Optional[str]:
    """Extract a potential title from the beginning of text"""
    lines = text.strip().split('\n')
    for line in lines[:5]:  # Check first 5 lines
        line = line.strip()
        if 20 <= len(line) <= 200 and not line.endswith('.'):
            return line
    return None


def _detect_language(text: str) -> str:
    """Simple language detection (fallback to English)"""
    try:
        from langdetect import detect
        return detect(text[:1000])  # Use first 1000 chars for detection
    except:
        return "en"  # Default to English


def _create_text_chunks(text: str, chunk_size: int, overlap: int) -> List[str]:
    """Split text into overlapping chunks"""
    words = text.split()
    chunks = []
    
    for i in range(0, len(words), chunk_size - overlap):
        chunk_words = words[i:i + chunk_size]
        if chunk_words:
            chunks.append(' '.join(chunk_words))
    
    return chunks