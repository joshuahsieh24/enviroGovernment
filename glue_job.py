import sys
from awsglue.transforms import *
from awsglue.utils import getResolvedOptions
from pyspark.context import SparkContext
from awsglue.context import GlueContext
from awsglue.job import Job
from pyspark.sql import DataFrame
from pyspark.sql.functions import *
from pyspark.sql.types import *
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Get job parameters
args = getResolvedOptions(sys.argv, ['JOB_NAME', 'INPUT_PATH', 'OUTPUT_PATH', 'DATABASE_NAME', 'TABLE_NAME'])

# Initialize Glue context
sc = SparkContext()
glueContext = GlueContext(sc)
spark = glueContext.spark_session
job = Job(glueContext)
job.init(args['JOB_NAME'], args)

def create_esg_schema():
    """Define schema for ESG utility bill data"""
    return StructType([
        StructField("utility_company", StringType(), True),
        StructField("account_number", StringType(), True),
        StructField("billing_period_start", DateType(), True),
        StructField("billing_period_end", DateType(), True),
        StructField("electricity_consumption_kwh", DoubleType(), True),
        StructField("gas_consumption_therms", DoubleType(), True),
        StructField("water_consumption_gallons", DoubleType(), True),
        StructField("electricity_cost_usd", DoubleType(), True),
        StructField("gas_cost_usd", DoubleType(), True),
        StructField("water_cost_usd", DoubleType(), True),
        StructField("renewable_energy_percentage", DoubleType(), True),
        StructField("carbon_emissions_kg_co2", DoubleType(), True),
        StructField("facility_id", StringType(), True),
        StructField("facility_name", StringType(), True),
        StructField("facility_type", StringType(), True),
        StructField("square_footage", DoubleType(), True),
        StructField("processing_date", TimestampType(), True),
        StructField("data_source", StringType(), True)
    ])

def clean_and_transform_data(df: DataFrame) -> DataFrame:
    """Clean and transform utility bill data"""
    logger.info("Starting data cleaning and transformation")
    
    # Add processing metadata
    df_with_metadata = df.withColumn("processing_date", current_timestamp()) \
                        .withColumn("data_source", lit("utility_bill_csv"))
    
    # Clean and validate numeric fields
    numeric_columns = [
        "electricity_consumption_kwh", "gas_consumption_therms", "water_consumption_gallons",
        "electricity_cost_usd", "gas_cost_usd", "water_cost_usd",
        "renewable_energy_percentage", "carbon_emissions_kg_co2", "square_footage"
    ]
    
    for col_name in numeric_columns:
        if col_name in df_with_metadata.columns:
            df_with_metadata = df_with_metadata.withColumn(
                col_name, 
                when(col(col_name) < 0, None).otherwise(col(col_name))
            )
    
    # Validate percentage fields (0-100)
    df_with_metadata = df_with_metadata.withColumn(
        "renewable_energy_percentage",
        when(
            (col("renewable_energy_percentage") >= 0) & (col("renewable_energy_percentage") <= 100),
            col("renewable_energy_percentage")
        ).otherwise(None)
    )
    
    # Calculate derived ESG metrics
    df_with_metrics = df_with_metadata \
        .withColumn("total_energy_cost_usd", 
                   coalesce(col("electricity_cost_usd"), lit(0)) + 
                   coalesce(col("gas_cost_usd"), lit(0))) \
        .withColumn("energy_intensity_kwh_per_sqft",
                   when(col("square_footage") > 0,
                        col("electricity_consumption_kwh") / col("square_footage"))
                   .otherwise(None)) \
        .withColumn("carbon_intensity_kg_per_kwh",
                   when(col("electricity_consumption_kwh") > 0,
                        col("carbon_emissions_kg_co2") / col("electricity_consumption_kwh"))
                   .otherwise(None)) \
        .withColumn("renewable_energy_kwh",
                   when(col("renewable_energy_percentage").isNotNull(),
                        col("electricity_consumption_kwh") * col("renewable_energy_percentage") / 100)
                   .otherwise(None))
    
    # Add ESG categorization
    df_final = df_with_metrics \
        .withColumn("esg_category_e1_climate", lit(True)) \
        .withColumn("esg_category_e2_pollution", 
                   when(col("carbon_emissions_kg_co2") > 0, True).otherwise(False)) \
        .withColumn("esg_category_e3_water", 
                   when(col("water_consumption_gallons") > 0, True).otherwise(False)) \
        .withColumn("esg_category_e5_resources", lit(True))
    
    logger.info(f"Transformed {df_final.count()} records")
    return df_final

def validate_data_quality(df: DataFrame) -> dict:
    """Perform data quality checks"""
    logger.info("Performing data quality validation")
    
    total_records = df.count()
    
    # Check for required fields
    required_fields = ["utility_company", "billing_period_start", "billing_period_end"]
    missing_required = {}
    
    for field in required_fields:
        if field in df.columns:
            null_count = df.filter(col(field).isNull()).count()
            missing_required[field] = {
                "null_count": null_count,
                "null_percentage": (null_count / total_records) * 100 if total_records > 0 else 0
            }
    
    # Check for data anomalies
    anomalies = {}
    
    # Negative consumption values
    negative_electricity = df.filter(col("electricity_consumption_kwh") < 0).count()
    negative_gas = df.filter(col("gas_consumption_therms") < 0).count()
    negative_water = df.filter(col("water_consumption_gallons") < 0).count()
    
    anomalies["negative_values"] = {
        "electricity": negative_electricity,
        "gas": negative_gas,
        "water": negative_water
    }
    
    # Unrealistic values
    high_electricity = df.filter(col("electricity_consumption_kwh") > 1000000).count()  # > 1M kWh
    high_renewable = df.filter(col("renewable_energy_percentage") > 100).count()
    
    anomalies["unrealistic_values"] = {
        "high_electricity_consumption": high_electricity,
        "invalid_renewable_percentage": high_renewable
    }
    
    quality_report = {
        "total_records": total_records,
        "missing_required_fields": missing_required,
        "anomalies": anomalies,
        "overall_quality_score": calculate_quality_score(missing_required, anomalies, total_records)
    }
    
    logger.info(f"Data quality report: {quality_report}")# ESG Insight Hub - Complete Repository

## README.md

```markdown
# ESG Insight Hub

A serverless platform that ingests raw sustainability evidence, maps it to CSRD/ESRS metrics, identifies gaps/expiring artifacts, drafts narrative text, and alerts stakeholders.

## 🏗️ Architecture (FREE TIER)