from jira import JIRA
import requests
import json
from bs4 import BeautifulSoup  # for cleaning HTML content

class UnifiedDataFetcher:
    def __init__(self, jira_server, confluence_server, username, api_token):
        self.jira_server = jira_server.rstrip('/')
        self.confluence_server = confluence_server.rstrip('/')
        self.username = username
        self.api_token = api_token

        # Initialize JIRA client (for fetching detailed issue data)
        self.jira = JIRA(
            server=self.jira_server,
            basic_auth=(username, api_token)
        )

        from get_particular_jira import JiraDataFetcher
        self.jira_fetcher = JiraDataFetcher(jira_server, username, api_token)

    # ----------------------------------------
    # JIRA Search (correct payload and endpoint)
    # ----------------------------------------
    def search_jira(self, keywords):
        all_issues = []
        for keyword in keywords:
            try:
                jql_query = f'text ~ "{keyword}" ORDER BY created DESC'
                url = f"{self.jira_server}/rest/api/3/search/jql"

                payload = {
                    "jql": jql_query,
                    "maxResults": 5,
                    "fields": ["summary", "key", "status", "assignee", "created"]
                }

                response = requests.post(
                    url,
                    auth=(self.username, self.api_token),
                    headers={"Content-Type": "application/json"},
                    json=payload
                )

                if response.status_code == 200:
                    data = response.json()
                    issues = data.get("issues", [])
                    for issue in issues:
                        issue_key = issue["key"]
                        issue_details = self.jira_fetcher.get_jira_details(issue_key)
                        if issue_details:
                            all_issues.append(issue_details)
                else:
                    print(f"⚠️ Failed to search JIRA for '{keyword}': {response.status_code} {response.text}")
            except Exception as e:
                print(f"Error searching JIRA for '{keyword}': {str(e)}")

        # only return top 5 overall
        return all_issues[:5]

    # ----------------------------------------
    # Confluence Search (cleaned HTML content)
    # ----------------------------------------
    def search_confluence(self, keywords):
        results = []
        for keyword in keywords:
            try:
                url = f"{self.confluence_server}/rest/api/content/search"
                params = {
                    "cql": f'text ~ "{keyword}" ORDER BY created DESC',
                    "limit": 5,
                    "expand": "body.view,space"
                }

                response = requests.get(
                    url,
                    params=params,
                    auth=(self.username, self.api_token)
                )

                if response.status_code == 200:
                    data = response.json()
                    for item in data.get("results", []):
                        raw_html = item["body"]["view"]["value"]
                        soup = BeautifulSoup(raw_html, "html.parser")
                        clean_text = soup.get_text(separator=" ", strip=True)

                        page_info = {
                            "id": item["id"],
                            "title": item["title"],
                            "url": f"{self.confluence_server}{item['_links']['webui']}",
                            "space": item["space"]["name"] if "space" in item else "",
                            "content": clean_text
                        }
                        results.append(page_info)
                else:
                    print(f"⚠️ Failed to search Confluence for '{keyword}': {response.status_code} {response.text}")
            except Exception as e:
                print(f"Error searching Confluence for '{keyword}': {str(e)}")

        return results[:5]

    # ----------------------------------------
    # Entry Point
    # ----------------------------------------
    def search_from_keywords(self, keywords):
        print(f"🔍 Searching for keywords: {keywords}")
        jira_results = self.search_jira(keywords)
        confluence_results = self.search_confluence(keywords)
        return {
            "jira": jira_results,
            "confluence": confluence_results
        }

if __name__ == "__main__":
    jira_server = "https://your-domain.atlassian.net"
    confluence_server = "https://your-domain.atlassian.net/wiki"
    username = "your_email@domain.com"
    api_token = "your_api_token"

    keywords = ["invoice", "workflow", "approval issue"]

    fetcher = UnifiedDataFetcher(jira_server, confluence_server, username, api_token)
    final_output = fetcher.search_from_keywords(keywords)
    print(json.dumps(final_output, indent=4))
