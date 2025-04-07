from pymongo import MongoClient
from gridfs import GridFSBucket
import os

def upload_file(file_path, database_name, bucket_name=None):
    try:
        # MongoDB Atlas connection string (replace placeholders)
        connection_uri = "mongodb+srv://atlas-sample-dataset-load-67f3c23f76d84f705ee1530a:Brancosoft%401234@stalkre-ai.uuvaicz.mongodb.net/?retryWrites=true&w=majority&appName=stalkre-ai"

        
        # Connect to MongoDB
        client = MongoClient(connection_uri)
        db = client[database_name]
        
        # Initialize GridFS Bucket (optional custom bucket name)
        fs = GridFSBucket(db, bucket_name=bucket_name) if bucket_name else GridFSBucket(db)
        
        # Validate file existence
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")
        
        # Upload the file
        with open(file_path, 'rb') as file_data:
            file_id = fs.upload_from_stream(
                filename=os.path.basename(file_path),
                source=file_data,
                metadata={"contentType": "application/octet-stream"}  # Optional metadata
            )
            print(f"✅ File uploaded successfully! File ID: {file_id}")

    except Exception as e:
        print(f"❌ Error: {str(e)}")
    finally:
        client.close()

# Example usage
if __name__ == "__main__":
    upload_file(
        file_path="./scrape_ecommerce/madeinchina/products.json",  # Replace with your file path
        database_name="stalkre-ai",       # Replace with your database name
        bucket_name="caterpillar_engine_fuel_injectors_v1"         # Optional: Replace or omit
    )