import os

MAGIC_NUMBERS = {
    b'\x50\x4B\x03\x04': "ZIP Archive",
    b'\x1F\x8B\x08': "GZIP Archive",
    b'\x28\xB5\x2F\xFD': "Zstandard compressed file (ZSTD)",
    b'\x50\x41\x52\x31': "Apache Parquet file",
    b'\x42\x5A\x68': "BZIP2 compressed file",
    b'\x75\x73\x74\x61\x72': "TAR Archive (ustar)",
    b'\x25\x50\x44\x46': "PDF Document",
    b'\x89\x50\x4E\x47': "PNG Image",
    b'\xFF\xD8\xFF': "JPEG Image",
    b'\x52\x61\x72\x21': "RAR Archive",
}

def detect_file_type(file_path):
    if not os.path.exists(file_path):
        return "❌ File does not exist."

    with open(file_path, 'rb') as f:
        header = f.read(10)  # Read first 10 bytes
    
    for magic, description in MAGIC_NUMBERS.items():
        if header.startswith(magic):
            return f"✅ Detected: {description}"
    
    return "⚠️ Unknown file type based on magic bytes."

# Example usage
file_path = r"C:\Users\Abhishek\Documents\bike_os\l5no5BP_.parquet.zst"
result = detect_file_type(file_path)
print(result)
