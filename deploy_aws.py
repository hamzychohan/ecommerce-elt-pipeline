#!/usr/bin/env python3
"""
AWS Deployment Script for E-Commerce ELT Pipeline

This script deploys the project to AWS S3 and Redshift.
Prerequisites:
- AWS credentials with S3 and Redshift permissions
- Redshift cluster created and accessible
- IAM role for Redshift to access S3
"""

import os
import sys
import asyncio
import logging
from datetime import date, datetime
import boto3
from extract.config import get_s3_bucket, get_entities
from extract.run_extract import run_extract
from warehouse.redshift_loader import (
    get_redshift_connection, 
    create_raw_schema, 
    copy_from_s3
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger(__name__)


def check_aws_permissions():
    """Check if we have the necessary AWS permissions."""
    try:
        # Test S3 access
        s3 = boto3.client('s3', region_name=os.getenv('AWS_REGION', 'eu-west-1'))
        bucket = get_s3_bucket()
        
        # Try to create bucket if it doesn't exist
        try:
            s3.head_bucket(Bucket=bucket)
            logger.info("✅ S3 bucket '%s' exists and is accessible", bucket)
        except s3.exceptions.NoSuchBucket:
            logger.info("Creating S3 bucket: %s", bucket)
            s3.create_bucket(
                Bucket=bucket,
                CreateBucketConfiguration={'LocationConstraint': os.getenv('AWS_REGION', 'eu-west-1')}
            )
            logger.info("✅ S3 bucket created: %s", bucket)
        
        return True
        
    except Exception as e:
        logger.error("❌ AWS permissions check failed: %s", e)
        return False


async def deploy_to_s3():
    """Extract data from API and deploy to S3."""
    logger.info("🚀 Starting S3 deployment...")
    
    # Configure for S3 deployment
    os.environ['USE_LOCAL_FILES'] = 'false'
    
    # Run extraction to S3
    summary = await run_extract()
    
    total_rows = sum(v.get("rows", 0) for v in summary.values())
    failures = [k for k, v in summary.items() if v.get("status") != "success"]
    
    if failures:
        logger.error("❌ S3 deployment failed: %s", failures)
        return False
    
    logger.info("✅ S3 deployment successful: %d rows uploaded", total_rows)
    return True, summary


def deploy_to_redshift(s3_summary):
    """Deploy data from S3 to Redshift."""
    logger.info("🏗️  Starting Redshift deployment...")
    
    try:
        # Connect to Redshift
        conn = get_redshift_connection()
        
        # Create raw schema and tables
        create_raw_schema(conn)
        logger.info("✅ Redshift schema created")
        
        # Load data from S3 to Redshift
        iam_role = os.environ['REDSHIFT_IAM_ROLE']
        bucket = get_s3_bucket()
        
        for entity, info in s3_summary.items():
            if info.get('status') == 'success':
                s3_uri = info.get('s3_uri')
                if s3_uri:
                    # Convert specific file to wildcard pattern for COPY
                    # e.g., s3://bucket/raw/customers/ingestion_date=2023-01-01/uuid.json
                    # becomes s3://bucket/raw/customers/ingestion_date=2023-01-01/
                    s3_prefix = s3_uri.rsplit('/', 1)[0] + '/'
                    
                    table = f"raw.{entity}"
                    copy_from_s3(conn, table, s3_prefix, iam_role, file_format="json")
                    
                    # Get row count
                    with conn.cursor() as cur:
                        cur.execute(f"SELECT COUNT(*) FROM {table}")
                        count = cur.fetchone()[0]
                        logger.info("✅ Loaded %d rows into %s", count, table)
        
        conn.close()
        logger.info("✅ Redshift deployment successful")
        return True
        
    except Exception as e:
        logger.error("❌ Redshift deployment failed: %s", e)
        return False


def setup_dbt_redshift():
    """Configure dbt for Redshift deployment."""
    logger.info("⚙️  Setting up dbt for Redshift...")
    
    # Create Redshift profile
    redshift_profile = f"""
ecommerce_dw:
  target: redshift
  outputs:
    redshift:
      type: redshift
      host: {os.getenv('REDSHIFT_HOST')}
      port: {os.getenv('REDSHIFT_PORT', 5439)}
      dbname: {os.getenv('REDSHIFT_DB')}
      schema: main
      user: {os.getenv('REDSHIFT_USER')}
      password: {os.getenv('REDSHIFT_PASSWORD')}
      threads: 4
      keepalives_idle: 240
      search_path: main,raw
    duckdb:
      type: duckdb
      path: /Users/default/Desktop/project2_complete/warehouse/ecommerce.duckdb
      schema: main
"""
    
    with open('dbt_project/profiles/profiles.yml', 'w') as f:
        f.write(redshift_profile)
    
    logger.info("✅ dbt Redshift profile created")


async def main():
    """Main deployment function."""
    logger.info("🌟 Starting AWS ELT Pipeline Deployment")
    logger.info("=" * 50)
    
    # Check environment variables
    required_vars = ['AWS_REGION', 'S3_BUCKET', 'REDSHIFT_HOST', 'REDSHIFT_DB', 'REDSHIFT_USER', 'REDSHIFT_PASSWORD', 'REDSHIFT_IAM_ROLE']
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    
    if missing_vars:
        logger.error("❌ Missing required environment variables: %s", ', '.join(missing_vars))
        logger.error("Please set these in your .env file")
        return False
    
    # Step 1: Check AWS permissions
    if not check_aws_permissions():
        return False
    
    # Step 2: Deploy to S3
    success, s3_summary = await deploy_to_s3()
    if not success:
        return False
    
    # Step 3: Deploy to Redshift
    if not deploy_to_redshift(s3_summary):
        return False
    
    # Step 4: Setup dbt for Redshift
    setup_dbt_redshift()
    
    # Step 5: Run dbt on Redshift
    logger.info("🔧 Running dbt transformations on Redshift...")
    import subprocess
    result = subprocess.run([
        './venv_dbt/bin/dbt', 'build', 
        '--project-dir', 'dbt_project',
        '--profiles-dir', 'dbt_project/profiles',
        '--target', 'redshift'
    ], capture_output=True, text=True)
    
    if result.returncode == 0:
        logger.info("✅ dbt transformations successful on Redshift")
        logger.info(result.stdout)
    else:
        logger.error("❌ dbt transformations failed")
        logger.error(result.stderr)
        return False
    
    logger.info("🎉 AWS Deployment Complete!")
    logger.info("=" * 50)
    logger.info("📊 Data available in:")
    logger.info(f"   • S3 Bucket: s3://{get_s3_bucket()}")
    logger.info(f"   • Redshift Cluster: {os.getenv('REDSHIFT_HOST')}")
    logger.info("✅ Ready for production analytics!")
    
    return True


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)