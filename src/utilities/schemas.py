from pydantic import BaseModel as PydanticBaseModel, Field
from typing import Literal, Dict

class AgentStep(PydanticBaseModel):
    """
    AgentStep
    A Pydantic model representing the step of an agent in the execution flow.
    Attributes:
y        agent (Literal["AGENT_1","AGENT_2", "HIL"]):
            The agent selected for execution.
        execution_flow (str):
            Reason for selecting the current agent.
    """

    agent:Literal["KNOWLEDGE_AGENT","JIRA_AGENT", "HISTORICAL_AGENT","SUMMARIZATION_AGENT","TEST_CASE_AGENT"] = Field(description="The agent selected for Execution")
    execution_flow:str = Field(description="Reason for selecting the current agent")
