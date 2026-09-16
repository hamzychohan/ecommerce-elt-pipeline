# AWS Deployment Guide

This guide shows how to deploy the E-Commerce ELT Pipeline to AWS S3 and Redshift.

## Prerequisites

### 1. AWS IAM Permissions

Your AWS user/role needs the following permissions:

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "s3:CreateBucket",
                "s3:DeleteBucket",
                "s3:ListBucket",
                "s3:GetObject",
                "s3:PutObject",
                "s3:DeleteObject"
            ],
            "Resource": [
                "arn:aws:s3:::ecommerce-raw-data-*",
                "arn:aws:s3:::ecommerce-raw-data-*/*"
            ]
        },
        {
            "Effect": "Allow",
            "Action": [
                "redshift:DescribeClusters",
                "redshift:GetClusterCredentials"
            ],
            "Resource": "*"
        }
    ]
}
```

### 2. Redshift Cluster Setup

Create a Redshift cluster with:
- Cluster identifier: `ecommerce-cluster`
- Database name: `ecommerce_dw`
- Master username: `admin`
- Master password: (set securely)
- Node type: `ra3.xlplus` (or `dc2.large` for development)
- Number of nodes: 1 (for development)

### 3. IAM Role for Redshift

Create an IAM role for Redshift to access S3:

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "s3:GetBucketLocation",
                "s3:GetObject",
                "s3:ListBucket"
            ],
            "Resource": [
                "arn:aws:s3:::ecommerce-raw-data-*",
                "arn:aws:s3:::ecommerce-raw-data-*/*"
            ]
        }
    ]
}
```

Attach this role to your Redshift cluster.

## Configuration

### 1. Update .env file

```bash
# AWS Configuration
AWS_REGION=eu-west-1
S3_BUCKET=ecommerce-raw-data-12345  # Use a unique suffix
S3_PREFIX=raw
USE_LOCAL_FILES=false

# Redshift Configuration
REDSHIFT_HOST=ecommerce-cluster.abc123.eu-west-1.redshift.amazonaws.com
REDSHIFT_PORT=5439
REDSHIFT_DB=ecommerce_dw
REDSHIFT_USER=admin
REDSHIFT_PASSWORD=YourSecurePassword
REDSHIFT_IAM_ROLE=arn:aws:iam::123456789012:role/RedshiftS3AccessRole
```

### 2. Install Additional Dependencies

```bash
pip install psycopg2-binary
```

## Deployment Steps

### Option 1: Full Automated Deployment

```bash
# Make the deployment script executable
chmod +x deploy_aws.py

# Run the deployment
PYTHONPATH=. python deploy_aws.py
```

### Option 2: Step-by-Step Deployment

#### Step 1: Deploy Raw Data to S3

```bash
# Configure for S3 deployment
export USE_LOCAL_FILES=false

# Run extraction to S3
PYTHONPATH=. python extract/run_extract.py
```

#### Step 2: Create Redshift Tables

```bash
PYTHONPATH=. python -c "
from warehouse.redshift_loader import get_redshift_connection, create_raw_schema
conn = get_redshift_connection()
create_raw_schema(conn)
print('Redshift tables created')
conn.close()
"
```

#### Step 3: Load Data from S3 to Redshift

```bash
PYTHONPATH=. python -c "
from warehouse.redshift_loader import get_redshift_connection, copy_from_s3
import os

conn = get_redshift_connection()
bucket = os.getenv('S3_BUCKET')
iam_role = os.getenv('REDSHIFT_IAM_ROLE')

# Load each entity
for entity in ['customers', 'orders', 'products']:
    s3_uri = f's3://{bucket}/raw/{entity}/'
    copy_from_s3(conn, f'raw.{entity}', s3_uri, iam_role, 'json')
    print(f'Loaded {entity} from S3 to Redshift')

conn.close()
"
```

#### Step 4: Run dbt on Redshift

```bash
./venv_dbt/bin/dbt build --project-dir dbt_project --profiles-dir dbt_project/profiles --target redshift
```

## Verification

### Check S3 Data

```bash
aws s3 ls s3://your-bucket-name/raw/ --recursive
```

### Check Redshift Tables

```sql
-- Connect to Redshift and run:
SELECT schemaname, tablename, rows 
FROM pg_tables 
JOIN (
    SELECT schemaname, tablename, COUNT(*) as rows
    FROM stv_tbl_perm 
    GROUP BY schemaname, tablename
) t USING (schemaname, tablename)
WHERE schemaname IN ('raw', 'main');
```

### Sample Analytics Query

```sql
-- Daily revenue from Redshift
SELECT 
    order_date,
    total_orders,
    gross_revenue_dollars
FROM main.mart_revenue_daily 
ORDER BY order_date DESC 
LIMIT 10;
```

## Monitoring and Troubleshooting

### S3 Upload Issues

- Check AWS credentials: `aws sts get-caller-identity`
- Verify bucket permissions
- Check bucket region matches AWS_REGION

### Redshift Connection Issues

- Verify cluster endpoint and port
- Check VPC security groups allow inbound connections
- Ensure cluster is in "available" state

### COPY Command Issues

- Check IAM role is attached to cluster
- Verify IAM role has S3 permissions
- Check S3 file format and structure
- Query `stl_load_errors` for COPY failures

### dbt Issues

- Verify Redshift profile configuration
- Check schema and table permissions
- Review dbt logs for specific errors

## Production Considerations

### Security
- Use AWS Secrets Manager for database credentials
- Enable S3 bucket versioning and encryption
- Use VPC endpoints for S3 access
- Enable Redshift audit logging

### Performance  
- Use Redshift DISTKEY and SORTKEY optimally
- Consider columnar compression
- Monitor query performance with query plans
- Use Redshift Spectrum for large datasets

### Cost Optimization
- Use Redshift pause/resume for dev environments
- Consider Reserved Instances for production
- Implement S3 lifecycle policies
- Monitor AWS costs with Cost Explorer

## Architecture Diagram

```
[Mock API] → [Python Extractor] → [S3 Bucket] → [Redshift Cluster] → [BI Tools]
                                      ↓
                                  [dbt Models]
                                      ↓
                               [Analytics Tables]
```

This deployment creates a production-ready ELT pipeline on AWS infrastructure!