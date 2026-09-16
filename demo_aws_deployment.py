#!/usr/bin/env python3
"""
Demo AWS Deployment Script - Simulates S3 and Redshift deployment
This demonstrates how the deployment would work with proper AWS credentials.
"""

import os
import sys
import asyncio
import logging
import json
from datetime import date, datetime
from pathlib import Path

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger(__name__)


class MockS3Client:
    """Mock S3 client for demonstration purposes."""
    
    def __init__(self, bucket_name):
        self.bucket_name = bucket_name
        self.objects = {}
    
    def put_object(self, Bucket, Key, Body, ContentType=None):
        """Simulate S3 put_object."""
        self.objects[Key] = {
            'Body': Body,
            'ContentType': ContentType,
            'Size': len(Body) if isinstance(Body, (str, bytes)) else 0
        }
        logger.info("📤 [MOCK S3] Uploaded: s3://%s/%s (%d bytes)", Bucket, Key, 
                   len(Body) if isinstance(Body, (str, bytes)) else 0)
        return {'ETag': 'mock-etag'}
    
    def list_objects_v2(self, Bucket, Prefix=''):
        """Simulate S3 list_objects_v2."""
        matching_keys = [key for key in self.objects.keys() if key.startswith(Prefix)]
        return {
            'Contents': [
                {'Key': key, 'Size': obj['Size']} 
                for key, obj in self.objects.items() 
                if key in matching_keys
            ]
        }


def simulate_s3_deployment():
    """Simulate deploying data to S3."""
    logger.info("🚀 [DEMO] Starting S3 Deployment Simulation...")
    
    # Create mock S3 client
    bucket_name = "ecommerce-raw-data-demo"
    s3_client = MockS3Client(bucket_name)
    
    # Simulate uploading the local data files to S3
    local_data_dir = Path("local_data/raw")
    total_files = 0
    total_size = 0
    
    for entity_dir in local_data_dir.iterdir():
        if entity_dir.is_dir():
            entity = entity_dir.name
            for date_dir in entity_dir.iterdir():
                if date_dir.is_dir() and date_dir.name.startswith('ingestion_date='):
                    for json_file in date_dir.glob('*.json'):
                        # Read the local file
                        content = json_file.read_text()
                        
                        # Create S3 key
                        s3_key = f"raw/{entity}/{date_dir.name}/{json_file.name}"
                        
                        # Upload to mock S3
                        s3_client.put_object(
                            Bucket=bucket_name,
                            Key=s3_key,
                            Body=content.encode('utf-8'),
                            ContentType='application/json'
                        )
                        
                        total_files += 1
                        total_size += len(content)
    
    logger.info("✅ [DEMO] S3 deployment complete:")
    logger.info("   📁 Files uploaded: %d", total_files)
    logger.info("   📊 Total size: %d bytes", total_size)
    logger.info("   🪣 Bucket: s3://%s", bucket_name)
    
    return s3_client


def simulate_redshift_deployment(s3_client):
    """Simulate Redshift deployment."""
    logger.info("🏗️  [DEMO] Starting Redshift Deployment Simulation...")
    
    # Simulate DDL creation
    tables = ['customers', 'orders', 'products']
    
    for table in tables:
        # Count records that would be loaded
        s3_objects = s3_client.list_objects_v2(
            Bucket="ecommerce-raw-data-demo", 
            Prefix=f"raw/{table}/"
        )
        
        total_records = 0
        for obj in s3_objects.get('Contents', []):
            # Simulate counting records in JSON file
            json_content = s3_client.objects[obj['Key']]['Body'].decode('utf-8')
            records = json_content.strip().split('\n')
            total_records += len(records)
        
        logger.info("📊 [MOCK REDSHIFT] Table raw.%s: %d records loaded", table, total_records)
    
    logger.info("✅ [DEMO] Redshift deployment complete")


def simulate_dbt_redshift():
    """Simulate running dbt on Redshift."""
    logger.info("🔧 [DEMO] Running dbt transformations on Redshift...")
    
    # These would be the actual dbt models run on Redshift
    models = [
        'stg_customers', 'stg_orders', 'stg_products',
        'int_customer_activity', 'int_customer_orders', 'int_order_lines_enriched',
        'mart_customers', 'mart_orders', 'mart_order_lines', 
        'mart_revenue_daily', 'mart_customer_churn_monthly'
    ]
    
    for model in models:
        logger.info("🔄 [MOCK DBT] Building model: %s", model)
    
    logger.info("✅ [DEMO] All dbt models built successfully on Redshift")


def demonstrate_analytics_queries():
    """Show what analytics queries would look like on Redshift."""
    logger.info("📊 [DEMO] Sample Analytics Queries for Redshift:")
    
    queries = {
        "Daily Revenue": """
            SELECT 
                order_date,
                total_orders,
                gross_revenue_dollars,
                avg_order_value_dollars
            FROM main.mart_revenue_daily 
            ORDER BY order_date DESC 
            LIMIT 10;
        """,
        
        "Top Customers": """
            SELECT 
                customer_id,
                total_orders,
                lifetime_total_dollars,
                avg_order_value_dollars,
                last_active_at
            FROM main.mart_customers 
            ORDER BY lifetime_total_dollars DESC 
            LIMIT 10;
        """,
        
        "Product Category Performance": """
            SELECT 
                product_category_name,
                COUNT(*) as total_order_lines,
                SUM(total_line_dollars) as total_revenue,
                AVG(price_dollars) as avg_price
            FROM main.mart_order_lines 
            GROUP BY product_category_name
            ORDER BY total_revenue DESC;
        """,
        
        "Monthly Churn Analysis": """
            SELECT 
                cohort_month,
                active_customers_prior,
                churned_customers,
                churn_rate,
                (churn_rate * 100)::decimal(5,2) as churn_percentage
            FROM main.mart_customer_churn_monthly 
            ORDER BY cohort_month DESC;
        """
    }
    
    for name, query in queries.items():
        logger.info("🔍 %s:", name)
        for line in query.strip().split('\n'):
            logger.info("     %s", line.strip())
        logger.info("")


async def main():
    """Main demo function."""
    logger.info("🌟 AWS ELT Pipeline Deployment Demo")
    logger.info("=" * 60)
    logger.info("This demonstrates how the pipeline would deploy to AWS")
    logger.info("with proper credentials and permissions.")
    logger.info("=" * 60)
    
    # Step 1: Simulate S3 deployment
    s3_client = simulate_s3_deployment()
    
    # Step 2: Simulate Redshift deployment  
    simulate_redshift_deployment(s3_client)
    
    # Step 3: Simulate dbt transformations
    simulate_dbt_redshift()
    
    # Step 4: Show analytics capabilities
    demonstrate_analytics_queries()
    
    logger.info("🎉 Demo Complete! Here's what would happen with real AWS:")
    logger.info("=" * 60)
    logger.info("📤 Raw Data → S3:")
    logger.info("   • 5,400 records uploaded to partitioned S3 bucket")
    logger.info("   • JSON format with date-based partitioning")
    logger.info("   • Automatic compression and encryption")
    logger.info("")
    logger.info("🏗️  S3 Data → Redshift:")
    logger.info("   • COPY commands load data from S3 to raw tables")
    logger.info("   • Optimized with DISTKEY and SORTKEY")
    logger.info("   • IAM role provides secure S3 access")
    logger.info("")
    logger.info("🔧 dbt Transformations:")
    logger.info("   • 11 models process raw data into analytics tables")
    logger.info("   • Incremental materialization for large tables")
    logger.info("   • Data quality tests ensure accuracy")
    logger.info("")
    logger.info("📊 Analytics Ready:")
    logger.info("   • Revenue metrics by day/month/category")
    logger.info("   • Customer segmentation and lifetime value")
    logger.info("   • Churn analysis and retention metrics")
    logger.info("   • Ready for Tableau, Looker, or PowerBI")
    logger.info("")
    logger.info("🚀 Production Benefits:")
    logger.info("   • Scalable to TBs of data")
    logger.info("   • Sub-second query performance")
    logger.info("   • Automatic backups and HA")
    logger.info("   • Pay-per-use cost model")


if __name__ == "__main__":
    asyncio.run(main())