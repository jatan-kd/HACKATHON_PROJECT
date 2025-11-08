from jira import JIRA
import os
import re
from dotenv import load_dotenv
load_dotenv()
import easyocr
import json

class JiraDataFetcher:
    def __init__(self, jira_server, username, api_token):
        self.jira_server = jira_server.rstrip('/')
        self.username = username
        self.api_token = api_token

        self.jira = JIRA(
            server=jira_server,
            basic_auth=(username, api_token)
        )

        self.reader = easyocr.Reader(['en'], gpu=False)

    def get_jira_details(self, jira_id):
        try:
            issue = self.jira.issue(jira_id, fields="*all")

            # --- Base data ---
            issue_data = {
                'key': issue.key,
                'summary': getattr(issue.fields, 'summary', ''),
                'status': getattr(issue.fields.status, 'name', ''),
                'assignee': getattr(issue.fields.assignee, 'displayName', 'Unassigned'),
                'description': "",
                'comments': [],
                'attachments': []
            }

            # --- Start with main description ---
            full_text = getattr(issue.fields, 'description', '') or ''
            description = self._clean_text(full_text)
            attachments = self._extract_inline_images(full_text)

            # --- Scan all fields dynamically for General tab content ---
            excluded_fields = ["attachment", "comment", "issuelinks", "subtasks", "changelog"]
            for field_name, value in issue.raw['fields'].items():
                if not value or field_name.lower() in excluded_fields:
                    continue
                field_text = self._extract_text_recursive(value)
                if field_text.strip():
                    description += f" {self._clean_text(field_text)}"
                    attachments.extend(self._extract_inline_images(field_text))

            # --- Attachments from main issue ---
            if hasattr(issue.fields, "attachment"):
                for attachment in issue.fields.attachment:
                    full_url = attachment.content
                    if not full_url.startswith("http"):
                        full_url = f"{self.jira_server}{attachment.content}"
                    attachments.append(full_url)

            # --- Comments ---
            if hasattr(issue.fields, "comment") and hasattr(issue.fields.comment, "comments"):
                for comment in issue.fields.comment.comments:
                    clean_comment = self._clean_text(comment.body)
                    comment_data = {
                        'author': getattr(comment.author, 'displayName', 'Unknown'),
                        'body': clean_comment,
                        'created': comment.created
                    }
                    comment_images = self._extract_inline_images(comment.body)
                    attachments.extend(comment_images)
                    issue_data['comments'].append(comment_data)

            # --- Deduplicate attachments ---
            issue_data['attachments'] = list(set(attachments))
            issue_data['description'] = description.strip()

            return issue_data

        except Exception as e:
            print(f"Error fetching JIRA details: {str(e)}")
            return None

    def _extract_text_recursive(self, value):
        """Recursively extract only readable text from field values."""
        if isinstance(value, str):
            return self._remove_links(value)
        elif isinstance(value, dict):
            text = ""
            for key in ["value", "text", "displayName", "name", "summary"]:
                if key in value and value[key]:
                    text += str(value[key]) + " "
            # If nothing found, recurse all items
            if not text.strip():
                for k, v in value.items():
                    text += self._extract_text_recursive(v) + " "
            return text.strip()
        elif isinstance(value, list):
            text = ""
            for item in value:
                text += self._extract_text_recursive(item) + " "
            return text.strip()
        else:
            return ""

    def _remove_links(self, text):
        """Remove URLs, JSON strings, and escape characters from text."""
        if not text:
            return ""
        # Remove URLs
        text = re.sub(r'http[s]?://\S+', '', text)
        # Remove JSON-like objects
        text = re.sub(r'\{.*?\}', '', text)
        # Remove newlines, tabs, multiple spaces
        text = re.sub(r'[\n\r\t]+', ' ', text)
        text = re.sub(r'\s+', ' ', text)
        return text.strip()

    def _clean_text(self, text):
        """Remove inline images and clean text completely."""
        if not text:
            return ""
        # Remove inline images
        text = re.sub(r'!.*?!', '', text)
        # Remove links and clean newlines/spaces
        return self._remove_links(text)

    def _extract_inline_images(self, text):
        """Extract inline image URLs like !image-xyz.png!."""
        if not text:
            return []
        image_filenames = re.findall(r'!(.*?)!', text)
        image_urls = []
        for name in image_filenames:
            filename = name.split('|')[0]
            full_url = f"{self.jira_server}/secure/attachment/{filename}"
            image_urls.append(full_url)
        return image_urls

    def prepare_for_agent(self, jira_id):
        """Fetch details and format into clean JSON."""
        jira_data = self.get_jira_details(jira_id)
        if not jira_data:
            return "No JIRA data available for processing."

        prompt_json = {
        "jira_id": jira_data["key"],
        "summary": jira_data["summary"],
        "status": jira_data["status"],
        "assignee": jira_data["assignee"],
        "details": {
            "description": jira_data["description"],
            "comments": jira_data["comments"],
            "attachments": jira_data["attachments"]
        }
    }

        return json.dumps(prompt_json, indent=4)