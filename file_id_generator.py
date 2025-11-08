from pymongo import MongoClient
import json

def store_payload_in_mongodb(payloadData):
    try:
        # --- Fixed MongoDB connection details ---
        mongo_uri = (
            "mongodb+srv://devleodocteamrw:N3EeQi7d3KoHpvLg@dev-leo-tenant.yjm1a.mongodb.net/"
            "Techathon-Bacardi?ssl=true&authSource=admin&retryWrites=true&"
            "readPreference=primary&w=majority&wtimeoutMS=5000&readConcernLevel=majority&"
            "retryReads=true&appName=docteamrw"
        )
        database_name = "Techathon-Bacardi"
        collection_name = "jirastorysummarizerdata"

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
