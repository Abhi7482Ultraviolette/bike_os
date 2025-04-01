import os
import boto3
import py7zr
import io


class AWSClient:
    def __init__(self, access_key, secret_key, bucket_name, custom_ca_bundle=None):
        """
        Initialize the AWS client with credentials and bucket name.
        :param access_key: AWS Access Key ID
        :param secret_key: AWS Secret Access Key
        :param bucket_name: Name of the S3 bucket
        :param custom_ca_bundle: Path to custom CA bundle for SSL verification
        """
        self.access_key = access_key
        self.secret_key = secret_key
        self.bucket_name = bucket_name
        self.custom_ca_bundle = custom_ca_bundle
        self.s3 = self._initialize_s3_client()

    def _initialize_s3_client(self):
        """
        Initialize the S3 client with optional custom CA bundle.
        :return: boto3 S3 client
        """
        try:
            # if self.custom_ca_bundle and os.path.exists(self.custom_ca_bundle):
            #     return boto3.client(
            #         "s3",
            #         aws_access_key_id=self.access_key,
            #         aws_secret_access_key=self.secret_key,
            #         verify=self.custom_ca_bundle
            #     )
            # else:
            # Use certifi's CA bundle by default
            import certifi
            return boto3.client(
                "s3",
                aws_access_key_id=self.access_key,
                aws_secret_access_key=self.secret_key,
                verify=certifi.where()
            )
        except Exception as e:
            raise RuntimeError(f"Failed to initialize S3 client: {e}")

    def get_available_logs(self, imei):
        """
        Retrieve all .7z log files for the given IMEI from the S3 bucket.
        :param imei: The IMEI of the bike
        :return: List of log file paths
        """
        try:
            base_path = f"vehicles/vcu_logs_{imei}"
            all_log_files = []
            # Traverse the directory structure
            date_folders = self.s3.list_objects_v2(Bucket=self.bucket_name, Prefix=base_path).get("Contents", [])
            for date_folder in date_folders:
                date_key = date_folder["Key"]
                day_folders = self.s3.list_objects_v2(Bucket=self.bucket_name, Prefix=date_key).get("Contents", [])
                for day_folder in day_folders:
                    day_key = day_folder["Key"]
                    time_folders = self.s3.list_objects_v2(Bucket=self.bucket_name, Prefix=day_key).get("Contents", [])
                    for time_folder in time_folders:
                        time_key = time_folder["Key"]
                        files = self.s3.list_objects_v2(Bucket=self.bucket_name, Prefix=time_key).get("Contents", [])
                        for file in files:
                            if file["Key"].endswith(".7z"):
                                all_log_files.append(file["Key"])
            return all_log_files
        except Exception as e:
            print(f"Error retrieving logs: {e}")
            return []

    def download_log_file(self, imei, log_path):
        """
        Download a specific log file for the given IMEI.
        :param imei: The IMEI of the bike
        :param log_path: The S3 key of the log file
        :return: BytesIO object containing the downloaded file data
        """
        try:
            response = self.s3.get_object(Bucket=self.bucket_name, Key=log_path)
            return response["Body"].read()
        except Exception as e:
            print(f"Error downloading log file: {e}")
            return None

    def extract_archive(self, archive_data):
        """
        Extract a .7z archive into memory.
        :param archive_data: BytesIO object containing the .7z archive data
        :return: Dictionary of extracted files (file_name: content)
        """
        try:
            with py7zr.SevenZipFile(archive_data, "r") as archive:
                extracted_files = archive.readall()
            return extracted_files
        except Exception as e:
            print(f"Error extracting archive: {e}")
            return {}