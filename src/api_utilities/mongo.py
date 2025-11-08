import os
import json
import logging
from typing import Optional
import requests
from requests.auth import HTTPBasicAuth
from pymongo import MongoClient
from bson import ObjectId

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


class PushError(Exception):
    """Custom exception for push failures."""
    pass


class MongoToJiraPusher:
    """Fetch a document from MongoDB and post its summary to Jira."""

    def __init__(
        self,
        mongo_conn_string: Optional[str] = None,
        db_name: str = "Techathon-Bacardi",
        collection_name: str = "jirastorysummarizerdata",
        jira_base_url: Optional[str] = None,
        jira_user: Optional[str] = None,
        jira_token: Optional[str] = None,
    ):
        # Resolve Mongo connection
        self.mongo_conn_string =  os.environ.get("MONGO_CONN_STRING") 
        
        self.db_name = db_name
        self.collection_name = collection_name

        # Resolve Jira credentials
        self.jira_base_url = (
            jira_base_url
            or os.environ.get("JIRA_BASE_URL")
            or os.environ.get("JIRA_SERVER")
            or "https://smartbygep.atlassian.net"
        )
        self.jira_user = os.environ.get("JIRA_USERNAME") 
        self.jira_token = os.environ.get("JIRA_API_TOKEN") 
        self.jira_auth = (self.jira_user, self.jira_token)

        # Setup Mongo client
        self.client = MongoClient(self.mongo_conn_string)
        self.db = self.client[self.db_name]
        self.collection = self.db[self.collection_name]

    # ----------------------------------------------------------
    # Jira Posting Helper
    # ----------------------------------------------------------
    def _post_jira_comment_adf(self, issue_key: str, body_text: str) -> dict:
        """Post body_text as a Jira comment using Atlassian Document Format."""
        comment_url = f"{self.jira_base_url.rstrip('/')}/rest/api/3/issue/{issue_key}/comment"
        payload = {
            "body": {
                "type": "doc",
                "version": 1,
                "content": [
                    {"type": "paragraph", "content": [{"type": "text", "text": body_text}]}
                ],
            }
        }
        headers = {"Content-Type": "application/json"}

        try:
            resp = requests.post(
                comment_url,
                json=payload,
                auth=HTTPBasicAuth(*self.jira_auth),
                headers=headers,
                timeout=30,
            )
        except Exception as e:
            raise PushError(f"Failed to POST to Jira: {e}") from e

        if not (200 <= resp.status_code < 300):
            raise PushError(f"Jira API returned {resp.status_code}: {resp.text}")

        try:
            return resp.json()
        except Exception:
            return {"status_code": resp.status_code, "text": resp.text}

    # ----------------------------------------------------------
    # Core Logic
    # ----------------------------------------------------------
    def push_summary_by_fileid(self, file_id: str) -> dict:
        """Fetch a MongoDB document by file_id and post its summary to Jira."""
        # Try ObjectId lookup
        doc = None
        try:
            oid = ObjectId(file_id)
            doc = self.collection.find_one({"_id": oid})
        except Exception:
            doc = None


        if not doc:
            raise PushError(f"No document found for file id '{file_id}'")

        issue_key = doc.get("jiraId")
        if not issue_key:
            raise PushError("Document does not contain 'jiraId' field")

        summary = doc.get("summarized_data")
        if not summary:
            raise PushError("Document does not contain 'summary' field")

        logger.info("Posting summary for Mongo file '%s' to Jira issue %s", file_id, issue_key)
        try:
            resp = self._post_jira_comment_adf(issue_key, summary)
            logger.info("Successfully posted comment to %s", issue_key)
            return resp
        except PushError:
            raise
        except Exception as e:
            raise PushError(f"Unexpected error: {e}") from e

 