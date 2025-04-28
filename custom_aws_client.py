import os
import boto3
import logging
import zstandard as zstd
import pandas as pd
import io
import pyarrow.parquet as pq
from botocore.config import Config
from ssl_config import ssl_configured
import numpy as np

class AWSClient:
    def __init__(self, access_key, secret_key, bucket_name="datalogs-processed-timeseries"):
        self.access_key = access_key
        self.secret_key = secret_key
        self.bucket_name = bucket_name
        self.s3 = self._initialize_s3_client()

    def _initialize_s3_client(self):
        try:
            if not ssl_configured:
                logging.warning("SSL not properly configured, using less secure connection")
            
            return boto3.client(
                "s3",
                aws_access_key_id=self.access_key,
                aws_secret_access_key=self.secret_key,
                config=Config(
                    connect_timeout=30,
                    retries={'max_attempts': 3},
                    s3={'addressing_style': 'path'}
                ),
                region_name='ap-south-1'  # Explicitly set your region
            )
        except Exception as e:
            logging.error(f"Failed to initialize S3 client: {str(e)}", exc_info=True)
            raise RuntimeError(f"Failed to initialize S3 client: {str(e)}")

    def get_available_logs(self, imei):
        """Retrieve all .parquet.zst log files for the given IMEI"""
        try:
            base_path = f"vcu/MD-{imei}"
            logging.debug(f"Base path for IMEI {imei}: {base_path}")
            
            response = self.s3.list_objects_v2(
                Bucket=self.bucket_name,
                Prefix=base_path
            )
            
            log_files = []
            for content in response.get('Contents', []):
                if content['Key'].endswith('.parquet.zst'):
                    log_files.append(content['Key'])
            
            logging.debug(f"Found log files: {log_files}")
            return log_files
        except Exception as e:
            logging.error(f"Error retrieving logs for IMEI {imei}: {str(e)}", exc_info=True)
            raise RuntimeError(f"Failed to retrieve logs: {str(e)}")
        
    def download_log_file(self, log_path):
        """Download and return log file content with better validation"""
        try:
            # Log the bucket name and log path for debugging
            logging.debug(f"Attempting to download log file: {log_path} from bucket: {self.bucket_name}")

            # First verify the file exists
            logging.debug(f"Checking if file exists: {log_path}")
            self.s3.head_object(Bucket=self.bucket_name, Key=log_path)
            
            # Then download
            logging.debug(f"Downloading file: {log_path}")
            response = self.s3.get_object(
                Bucket=self.bucket_name,
                Key=log_path
            )
            return response['Body'].read()
        except self.s3.exceptions.NoSuchKey:
            logging.error(f"Log file {log_path} not found in bucket {self.bucket_name}")
            return None
        except Exception as e:
            logging.error(f"Error downloading {log_path}: {str(e)}", exc_info=True)
            return None
        
    def extract_archive(self, archive_data):
        """Handle both actual zstd-compressed files and mislabeled parquet files"""
        try:
            # If archive_data is a StreamingBody (from S3), read it first
            if hasattr(archive_data, 'read'):
                archive_data = archive_data.read()

            # Check if the data starts with Parquet magic bytes (b'PAR1')
            if archive_data.startswith(b'PAR1'):
                # It's actually a raw parquet file - read directly
                parquet_file = io.BytesIO(archive_data)
                return pq.read_table(parquet_file).to_pandas()
            else:
                # Try zstd decompression (for genuinely compressed files)
                dctx = zstd.ZstdDecompressor()
                decompressed_data = dctx.decompress(archive_data)
                parquet_file = io.BytesIO(decompressed_data)
                return pq.read_table(parquet_file).to_pandas()

        except Exception as e:
            logging.error(f"Error processing file: {str(e)}", exc_info=True)
            raise RuntimeError(f"Failed to process file: {str(e)}")