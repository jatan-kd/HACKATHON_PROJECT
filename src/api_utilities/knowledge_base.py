"""Fetch and clean a Confluence page given its URL.

Usage (PowerShell):
  pip install requests beautifulsoup4
  python fetch_confluence.py "https://<your-site>.atlassian.net/wiki/spaces/.../pages/5049483275/Invoice+Basic+Flow"

Authentication:
  The script uses HTTP Basic auth with an API token. Provide credentials via env vars:
    - JIRA_API_USER or JIRA_USERNAME
    - JIRA_API_TOKEN or JIRA_TOKEN
  Or pass --user and --token on the CLI.

This writes a cleaned plain-text version of the page to a file named <page-title>_clean.txt
"""
import os
import re
import json
import logging
from typing import Optional

import requests
from requests.auth import HTTPBasicAuth
from bs4 import BeautifulSoup, Tag
import getpass


class KnowledgeBaseFetcher:
    def __init__(self, username: Optional[str] = None, token: Optional[str] = None):
        self.username = username 
        self.token = token 
        if not self.username or not self.token:
            raise Exception("Confluence/Jira credentials not provided via args or environment variables")

    class FetchError(Exception):
        pass

    def _extract_page_id(self, url: str) -> Optional[str]:
        m = re.search(r"/pages/(\d+)", url)
        if m:
            return m.group(1)
        m = re.search(r"[?&]pageId=(\d+)", url)
        if m:
            return m.group(1)
        return None

    def _extract_base_wiki(self, url: str) -> Optional[str]:
        m = re.match(r"(https?://[^/]+/wiki)", url)
        if m:
            return m.group(1)
        m = re.match(r"(https?://[^/]+)", url)
        if m:
            return m.group(1) + "/wiki"
        return None

    def html_to_clean_text(self, html: str) -> str:
        soup = BeautifulSoup(html, "html.parser")
        body = soup
        lines = []

        def walk(node, indent=0):
            if isinstance(node, Tag):
                name = node.name.lower()
                if name in ("h1", "h2", "h3", "h4", "h5", "h6"):
                    level = int(name[1]) if name[1].isdigit() else 1
                    lines.append(("#" * level) + " " + node.get_text(strip=True))
                    lines.append("")
                    return
                if name == "p":
                    txt = node.get_text(strip=True)
                    if txt:
                        lines.append(txt)
                        lines.append("")
                    return
                if name == "ul":
                    for li in node.find_all("li", recursive=False):
                        lines.append(" " * indent + "- " + li.get_text(strip=True))
                    lines.append("")
                    return
                if name == "ol":
                    i = 1
                    for li in node.find_all("li", recursive=False):
                        lines.append(" " * indent + f"{i}. " + li.get_text(strip=True))
                        i += 1
                    lines.append("")
                    return
                if name == "li":
                    lines.append(" " * indent + "- " + node.get_text(strip=True))
                    return
                if name == "table":
                    rows = []
                    for tr in node.find_all("tr"):
                        cols = [c.get_text(strip=True) for c in tr.find_all(["th", "td"])]
                        rows.append(cols)
                    if rows:
                        max_cols = max(len(r) for r in rows)
                        rows = [r + [""] * (max_cols - len(r)) for r in rows]
                        lines.append(" | ".join(rows[0]))
                        lines.append(" | ".join(["---"] * max_cols))
                        for r in rows[1:]:
                            lines.append(" | ".join(r))
                        lines.append("")
                    return
                for child in node.children:
                    walk(child, indent)
            else:
                text = str(node).strip()
                if text:
                    lines.append(text)

        for child in body.children:
            walk(child, 0)

        out_lines = []
        blank = 0
        for l in lines:
            if not l.strip():
                blank += 1
                if blank <= 2:
                    out_lines.append("")
            else:
                blank = 0
                out_lines.append(l)

        return "\n".join(out_lines).strip() + "\n"

    def fetch_confluence_page(self, url: str) -> str:
        page_id = self._extract_page_id(url)
        if not page_id:
            raise self.FetchError("Could not extract page id from URL. Provide a Confluence page URL containing /pages/{id}/ or pageId parameter.")

        base = self._extract_base_wiki(url)
        if not base:
            raise self.FetchError("Could not determine Confluence base URL from provided URL")

        api_url = f"{base}/rest/api/content/{page_id}?expand=body.storage,title"

        try:
            resp = requests.get(api_url, auth=HTTPBasicAuth(self.username, self.token), timeout=30)
        except Exception as e:
            raise self.FetchError(f"Failed to fetch Confluence page: {e}") from e

        if not (200 <= resp.status_code < 300):
            raise self.FetchError(f"Confluence API returned {resp.status_code}: {resp.text}")

        data = resp.json()
        title = data.get("title") or f"page_{page_id}"
        storage = data.get("body", {}).get("storage", {}).get("value")
        if not storage:
            raise self.FetchError("No storage/html content found on the Confluence page")

        clean = self.html_to_clean_text(storage)

        return clean


# if __name__ == "__main__":
#     # Hardcoded Confluence page URL (Invoice Basic Flow)
#     HARDCODED_URL = (
#         "https://smartbygep.atlassian.net/wiki/spaces/~712020fb23db945f4b48a78712d6e43ffb656e/"
#         "pages/5049483275/Invoice+Basic+Flow"
#     )

#     # NOTE: Credentials are hardcoded below per user request. This is insecure
#     # and should NOT be committed to source control. Remove before sharing.
#     JIRA_SERVER = "https://smartbygep.atlassian.net/"
#     username = "ansh.chirawawala@gep.com"
#     token = (
#         "ATATT3xFfGF0J11aWFx0tfJX-oYC5FjIV8jI_NQ8FTXaT74EUGpHtCJiBkijW5tZdNjU6wIkhfCTn2CYykF"
#         "VTrXjHA4CDivsZ0wcfp7nLV_6i1g3nsJhCe8QeM9oqFvOMeuJIOHL42T2GsaUgW3Q3LXAjoZrlX_Z_I7XAK3"
#         "5HLd7FieR2genx0g=A2622883"
#     )

#     try:
#         out_file = fetch_confluence_page(HARDCODED_URL, username=username, token=token)
#         print("Saved cleaned page to", out_file)
#     except Exception as e:
#         print("ERROR:", e)
#         raise