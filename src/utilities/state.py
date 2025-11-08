from pydantic import BaseModel, Field
from typing import Optional
from langchain_core.messages import SystemMessage


def reduce_list(left: list | None, right: list | None) -> list:
    if not left:
        left = []
    if not right:
        right = []

    if len(right)>0:
        if right[0] == SystemMessage(content="DELETE"):
            return []
        if right[0] == SystemMessage(content="APPEND"):
            return right[1:]
    return left + right

class AgentHistory(BaseModel):
    """
    The input schema for the Jira Agent
    """
    userQuery: str = Field(description="The user query, typically the ticket ID or PLI")
    conv_id: str = Field(description="The conversation id for the interaction")
    thread_id: Optional[str] = Field(description="The thread identifier", default=None)  # Added field
    ticket_attributes: Optional[dict] = Field(description="Attributes and comments of the Jira ticket", default=None)
    current_agent: str = Field(description="The current agent in the conversation", default="NONE")
    historical_data: Optional[str] = Field(description="Historical data related to the ticket", default=None)
    current_Jira_data: Optional[dict] = Field(description="Current Jira ticket data", default=None)
    knowledge_data: Optional[str] = Field(description="Knowledge base data relevant to the ticket", default=None)
    summarization_data: Optional[str] = Field(description="Summarization data for the ticket", default=None)
    test_case_data: Optional[str] = Field(description="Test case data related to the ticket", default=None)
    messages: list = Field(default_factory=list)
    keywords: Optional[list] = Field(description="Extracted keywords from the ticket", default=None)
