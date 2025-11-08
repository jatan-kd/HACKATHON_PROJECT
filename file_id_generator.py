from pymongo import MongoClient
import json
import os

def store_payload_in_mongodb(payloadData):
    try:
        # --- Fixed MongoDB connection details ---
        mongo_uri = os.getenv("MONGO_CONN_STRING")
        database_name = os.getenv("MONGO_DB_NAME")
        collection_name = os.getenv("MONGO_COLLECTION_NAME")
 

        # --- Connect to MongoDB ---
        client = MongoClient(mongo_uri)
        db = client[database_name]
        collection = db[collection_name]

        # --- Insert the payload ---
        result = collection.insert_one(payloadData)
        inserted_id = str(result.inserted_id)

        # --- Prepare response ---
        response = {
            "jiraId": payloadData.get("jiraId", ""),
            "fileId": inserted_id
        }

        print("✅ Insert successful!")
        return json.dumps(response, indent=2)

    except Exception as e:
        return json.dumps({"error": str(e)})
