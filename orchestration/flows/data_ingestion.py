"""
Data ingestion flows for various external sources
"""

import asyncio
import json
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
import httpx
import pandas as pd
import duckdb
from prefect import flow, task, get_run_logger
from prefect.artifacts import create_table_artifact
from prefect.blocks.system import Secret

from tasks.connectors import (
    fetch_nyc_311_data,
    fetch_epa_air_quality,
    fetch_census_data,
    fetch_who_health_data,
    fetch_climate_data,
    process_pdf_documents
)
from tasks.data_quality import validate_data_quality, run_quality_checks
from tasks.storage import store_in_lakehouse, update_knowledge_graph
from tasks.notifications import send_completion_notification


@flow(name="NYC 311 Data Ingestion", log_prints=True)
async def ingest_nyc_311_data(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    limit: int = 10000
) -> Dict[str, Any]:
    """
    Ingest NYC 311 service request data
    """
    logger = get_run_logger()
    logger.info(f"Starting NYC 311 data ingestion")
    
    # Set default date range if not provided
    if not end_date:
        end_date = datetime.now().strftime('%Y-%m-%d')
    if not start_date:
        start_date = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
    
    try:
        # Fetch data from NYC Open Data API
        raw_data = await fetch_nyc_311_data(start_date, end_date, limit)
        logger.info(f"Fetched {len(raw_data)} records from NYC 311 API")
        
        # Validate data quality
        quality_report = await validate_data_quality(
            data=raw_data,
            dataset_name="nyc_311",
            expected_schema={
                "unique_key": "string",
                "created_date": "datetime",
                "complaint_type": "string",
                "descriptor": "string",
                "location_type": "string",
                "incident_zip": "string",
                "city": "string",
                "borough": "string",
                "latitude": "float",
                "longitude": "float"
            }
        )
        
        if not quality_report["passed"]:
            logger.warning(f"Data quality issues found: {quality_report['issues']}")
        
        # Store in lakehouse
        storage_result = await store_in_lakehouse(
            data=raw_data,
            table_name="nyc_311_requests",
            partition_by=["created_date"],
            update_mode="append"
        )
        
        # Update knowledge graph with new entities
        if storage_result["success"]:
            kg_result = await update_knowledge_graph(
                data=raw_data,
                entity_type="ServiceRequest",
                relations=["LOCATED_IN", "BELONGS_TO_CATEGORY"]
            )
        
        # Create artifacts for monitoring
        await create_table_artifact(
            key="nyc-311-ingestion-summary",
            table=pd.DataFrame([{
                "Records Fetched": len(raw_data),
                "Quality Score": quality_report.get("score", 0),
                "Storage Status": storage_result["status"],
                "Processed At": datetime.now().isoformat()
            }])
        )
        
        result = {
            "source": "NYC 311",
            "records_processed": len(raw_data),
            "quality_score": quality_report.get("score", 0),
            "storage_status": storage_result["status"],
            "timestamp": datetime.now().isoformat()
        }
        
        # Send notification
        await send_completion_notification(
            flow_name="NYC 311 Data Ingestion",
            result=result,
            success=True
        )
        
        return result
        
    except Exception as e:
        logger.error(f"NYC 311 ingestion failed: {str(e)}")
        await send_completion_notification(
            flow_name="NYC 311 Data Ingestion",
            result={"error": str(e)},
            success=False
        )
        raise


@flow(name="EPA Air Quality Ingestion", log_prints=True)
async def ingest_epa_air_quality(
    states: List[str] = None,
    pollutants: List[str] = None
) -> Dict[str, Any]:
    """
    Ingest EPA air quality data
    """
    logger = get_run_logger()
    logger.info("Starting EPA air quality data ingestion")
    
    # Default parameters
    if not states:
        states = ["NY", "CA", "TX", "FL", "IL"]  # Major states
    if not pollutants:
        pollutants = ["88101", "44201", "42401", "42101"]  # PM2.5, Ozone, SO2, CO
    
    try:
        all_data = []
        
        # Fetch data for each state and pollutant combination
        for state in states:
            for pollutant in pollutants:
                data = await fetch_epa_air_quality(
                    state=state,
                    pollutant=pollutant,
                    begin_date=datetime.now() - timedelta(days=7),
                    end_date=datetime.now()
                )
                all_data.extend(data)
        
        logger.info(f"Fetched {len(all_data)} air quality measurements")
        
        # Validate data quality
        quality_report = await validate_data_quality(
            data=all_data,
            dataset_name="epa_air_quality",
            expected_schema={
                "state_code": "string",
                "county_code": "string",
                "site_num": "string",
                "parameter_code": "string",
                "poc": "int",
                "latitude": "float",
                "longitude": "float",
                "datum": "string",
                "parameter_name": "string",
                "sample_duration": "string",
                "pollutant_standard": "string",
                "date_local": "date",
                "units_of_measure": "string",
                "event_type": "string",
                "observation_count": "int",
                "observation_percent": "float",
                "arithmetic_mean": "float",
                "first_max_value": "float",
                "first_max_hour": "int",
                "aqi": "int"
            }
        )
        
        # Store in lakehouse
        storage_result = await store_in_lakehouse(
            data=all_data,
            table_name="epa_air_quality",
            partition_by=["date_local", "state_code"],
            update_mode="upsert",
            primary_keys=["state_code", "county_code", "site_num", "parameter_code", "date_local"]
        )
        
        # Update knowledge graph
        if storage_result["success"]:
            kg_result = await update_knowledge_graph(
                data=all_data,
                entity_type="AirQualityMeasurement",
                relations=["MEASURED_AT", "MEASURES_POLLUTANT"]
            )
        
        result = {
            "source": "EPA Air Quality",
            "records_processed": len(all_data),
            "states_covered": len(states),
            "pollutants_tracked": len(pollutants),
            "quality_score": quality_report.get("score", 0),
            "storage_status": storage_result["status"],
            "timestamp": datetime.now().isoformat()
        }
        
        await send_completion_notification(
            flow_name="EPA Air Quality Ingestion",
            result=result,
            success=True
        )
        
        return result
        
    except Exception as e:
        logger.error(f"EPA air quality ingestion failed: {str(e)}")
        await send_completion_notification(
            flow_name="EPA Air Quality Ingestion",
            result={"error": str(e)},
            success=False
        )
        raise


@flow(name="Policy Document Ingestion", log_prints=True)
async def ingest_policy_documents(
    document_urls: List[str],
    source_name: str = "Policy Repository"
) -> Dict[str, Any]:
    """
    Ingest and process policy documents (PDFs, etc.)
    """
    logger = get_run_logger()
    logger.info(f"Starting policy document ingestion for {len(document_urls)} documents")
    
    try:
        processed_docs = []
        
        # Process each document
        for url in document_urls:
            try:
                doc_data = await process_pdf_documents(
                    urls=[url],
                    extract_metadata=True,
                    chunk_size=1000,
                    overlap=100
                )
                processed_docs.extend(doc_data)
                logger.info(f"Processed document: {url}")
            except Exception as e:
                logger.warning(f"Failed to process document {url}: {str(e)}")
                continue
        
        logger.info(f"Successfully processed {len(processed_docs)} document chunks")
        
        # Validate processed documents
        quality_report = await validate_data_quality(
            data=processed_docs,
            dataset_name="policy_documents",
            expected_schema={
                "document_id": "string",
                "chunk_id": "string",
                "title": "string",
                "content": "string",
                "source_url": "string",
                "page_number": "int",
                "language": "string",
                "metadata": "object"
            }
        )
        
        # Store in lakehouse
        storage_result = await store_in_lakehouse(
            data=processed_docs,
            table_name="policy_documents",
            partition_by=["source", "language"],
            update_mode="append"
        )
        
        # Update knowledge graph with document entities
        if storage_result["success"]:
            kg_result = await update_knowledge_graph(
                data=processed_docs,
                entity_type="PolicyDocument",
                relations=["CONTAINS", "REFERENCES", "RELATES_TO"]
            )
        
        result = {
            "source": source_name,
            "documents_requested": len(document_urls),
            "chunks_processed": len(processed_docs),
            "quality_score": quality_report.get("score", 0),
            "storage_status": storage_result["status"],
            "timestamp": datetime.now().isoformat()
        }
        
        await send_completion_notification(
            flow_name="Policy Document Ingestion",
            result=result,
            success=True
        )
        
        return result
        
    except Exception as e:
        logger.error(f"Policy document ingestion failed: {str(e)}")
        await send_completion_notification(
            flow_name="Policy Document Ingestion",
            result={"error": str(e)},
            success=False
        )
        raise


@flow(name="Daily Data Ingestion Pipeline", log_prints=True)
async def daily_ingestion_pipeline():
    """
    Orchestrates daily ingestion from all sources
    """
    logger = get_run_logger()
    logger.info("Starting daily data ingestion pipeline")
    
    results = {}
    
    try:
        # Run ingestion flows in parallel for better performance
        ingestion_tasks = [
            ingest_nyc_311_data(),
            ingest_epa_air_quality(),
            # Add other source ingestions here
        ]
        
        # Execute all ingestion flows
        ingestion_results = await asyncio.gather(*ingestion_tasks, return_exceptions=True)
        
        # Process results
        for i, result in enumerate(ingestion_results):
            source_name = ["NYC_311", "EPA_Air_Quality"][i]
            if isinstance(result, Exception):
                logger.error(f"{source_name} ingestion failed: {str(result)}")
                results[source_name] = {"status": "failed", "error": str(result)}
            else:
                logger.info(f"{source_name} ingestion completed successfully")
                results[source_name] = {"status": "success", "data": result}
        
        # Run quality checks across all data
        overall_quality = await run_quality_checks(
            datasets=["nyc_311_requests", "epa_air_quality"],
            run_profiling=True
        )
        
        # Generate summary report
        summary = {
            "pipeline_run_id": f"daily_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            "execution_date": datetime.now().isoformat(),
            "sources_processed": len([r for r in results.values() if r["status"] == "success"]),
            "sources_failed": len([r for r in results.values() if r["status"] == "failed"]),
            "overall_quality_score": overall_quality.get("average_score", 0),
            "individual_results": results
        }
        
        # Create summary artifact
        await create_table_artifact(
            key="daily-ingestion-summary",
            table=pd.DataFrame([{
                "Run Date": datetime.now().strftime('%Y-%m-%d'),
                "Sources Processed": summary["sources_processed"],
                "Sources Failed": summary["sources_failed"],
                "Overall Quality": f"{summary['overall_quality_score']:.2f}%",
                "Status": "Success" if summary["sources_failed"] == 0 else "Partial"
            }])
        )
        
        # Send summary notification
        await send_completion_notification(
            flow_name="Daily Data Ingestion Pipeline",
            result=summary,
            success=summary["sources_failed"] == 0
        )
        
        return summary
        
    except Exception as e:
        logger.error(f"Daily ingestion pipeline failed: {str(e)}")
        await send_completion_notification(
            flow_name="Daily Data Ingestion Pipeline",
            result={"error": str(e)},
            success=False
        )
        raise


if __name__ == "__main__":
    # For testing individual flows
    import asyncio
    
    # Test NYC 311 ingestion
    result = asyncio.run(ingest_nyc_311_data(limit=100))
    print(f"NYC 311 ingestion result: {result}")