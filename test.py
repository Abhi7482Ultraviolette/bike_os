# Add this at the bottom of custom_aws_client.py
if __name__ == "__main__":
    # Initialize the AWS client
    aws_client = AWSClient()

    # Test retrieving logs for a specific IMEI
    imei = "860548049205591"
    logs = aws_client.get_available_logs(imei)
    print(f"Available logs: {logs}")

    # Test downloading a log file (replace 'log_filename' with an actual file name from the logs list)
    if logs:
        log_file = aws_client.download_log_file(imei, logs[0])
        if log_file:
            print("Log file downloaded successfully!")