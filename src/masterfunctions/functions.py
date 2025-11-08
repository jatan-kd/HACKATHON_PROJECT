import os
from urllib import response
from langchain_groq import ChatGroq
import requests
import csv
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
from langchain_core.messages import HumanMessage, AIMessage
from langchain_core.runnables.config import RunnableConfig
from src.api_utilities.historical import UnifiedDataFetcher
from src.api_utilities.jira_cur import JiraDataFetcher
from src.api_utilities.knowledge_base import KnowledgeBaseFetcher
from src import constants
import time
from typing import List
import json
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from src.utilities.schemas import AgentStep
from src.utilities.state import AgentHistory

class MasterFunctions:
    jira_orchestrator = None
    prompt_cache = {"jira":{}}

    def __init__(self,llm,**kwargs) -> None:
        self.llm = llm
        self.members = ["GROOMING_AGENT", "KNOWLEDGE_AGENT", "JIRA_AGENT", "HISTORICAL_AGENT", "SUMMARIZATION_AGENT", "TEST_CASE_AGENT"]
        
    def _load_prompt(self, prompt_file: str) -> str:
        """
        Helper function to load and cache the prompt content from a file.
        Cache duration is in seconds.
        """
        file_path = os.path.join(constants.DIRECTORY_PATH,prompt_file)
        with open(file_path, 'r') as file:
            prompt_content = file.read()

        return prompt_content
    
    def agent_supervisor(self, state: AgentHistory):
        """
        Supervises the agents' flow by deciding which agent to call next, based on the query and history.
        It uses a dedicated supervisor prompt template to receive instructions from the LLM.
        """
        print("------GROOMING SUPERVISOR------")

        query = state.userQuery  
        curr_agent = state.current_agent  
        # category = state.category  # (Commented out: optional category field)

        # Load the supervisor's prompt file for the given mode.
        supervisor_agent_system_prompt = self._load_prompt("grooming_agent_prompt.txt")
        supervisor_agent_prompt = ChatPromptTemplate.from_messages([
            ("system", supervisor_agent_system_prompt),
            ("user", "query:{query}")
        ])

        # Extend the LLM to provide structured output (AgentStep) and run the chain.
        llm_with_out = self.llm.with_structured_output(AgentStep)
        chain = supervisor_agent_prompt | llm_with_out

        response = chain.invoke({"current_agent": curr_agent, "query": query})

        # If the LLM indicates to end the chain, return terminal messages.
        if response.agent == "END":
            print("Execution flow completed:", response.execution_flow)
            return {
                "messages": [
                    HumanMessage(content=query),
                    AIMessage(content=response.execution_flow)
                ],
                "current_agent": "END"
            }

        
        return {
            "messages": [
                HumanMessage(content=query),
                AIMessage(content=response.execution_flow)
            ],
            "current_agent": response.agent
        }
        
    def jira_agent(self, state: AgentHistory):
        """
        Handles JIRA queries by fetching JIRA details and invoking the LLM.
        """
        print("------JIRA AGENT------")

        query = state.userQuery
        curr_jira = state.current_Jira_data
        curr_agent = state.current_agent

        jira_server = os.getenv("JIRA_SERVER")
        jira_username = os.getenv("JIRA_USERNAME")
        jira_token = os.getenv("JIRA_API_TOKEN")
        jira_fetcher = JiraDataFetcher(jira_server, jira_username, jira_token)

        # Fetch JIRA details
        curr_jira = jira_fetcher.prepare_for_agent(query)
        print("Fetched JIRA Details:", curr_jira)
        if not curr_jira:
            response_text = "No JIRA data available for processing."
        else:
            response_text = json.dumps(curr_jira)

        # Prepare prompt for LLM
        jira_agent_system_prompt = self._load_prompt("jira_agent_system.txt")
            # Pass the JSON as plain text, not as a template variable
        jira_agent_prompt = ChatPromptTemplate.from_messages([
                ("system", jira_agent_system_prompt),
                ("user", "current_agent: {current_agent}, curr_jira: {curr_jira}")
            ])

        # Extend the LLM to provide structured output (AgentStep) and run the chain.
        llm_with_out = self.llm.with_structured_output(AgentStep)
        chain = jira_agent_prompt | llm_with_out

            # Only pass current_agent and query (not curr_jira)
        response = chain.invoke({"current_agent": curr_agent, "curr_jira": response_text})
        
        # Otherwise, return the agent's instruction and continue.
        summary = response.execution_flow
        keywords = self.summarize_resolution(summary)
        result_json = {
            "summary": summary,
            "keywords": keywords
        }
        
        # Save updated state for next agent
        state.keywords = keywords
        state.current_Jira_data = summary
        
        ################# HISTORICAL AGENT INVOCATION #################
        historicalData = self.historical_agent(state)
        print("HISTORICAL DATA FROM HISTORICAL AGENT:", historicalData)
        state.historical_data = historicalData.get("historical_data", "")
        ################# HISTORICAL AGENT INVOCATION END #################
        
         ################# KNOWLEDGE AGENT INVOCATION #################
        knowledgeData = self.knowledge_agent(state)
        print("KNOWLEDGE DATA FROM KNOWLEDGE AGENT:", knowledgeData)
        state.knowledge_data = knowledgeData.get("knowledge_base", "")
        ################# KNOWLEDGE AGENT INVOCATION END #################

        result_json = {
            "summary": summary,
            "keywords": keywords,
            "historical_data": state.historical_data,
            "knowledge_base": knowledgeData.get("knowledge_base", "")
        }
        
        ################# SUMMARIZATION AGENT INVOCATION #################
        summarizationData = self.summarization_agent(result_json)
        print("SUMMARIZATION DATA FROM SUMMARIZATION AGENT:", summarizationData)
        state.summarization_data = summarizationData.get("summarized_data", "")
        ################# SUMMARIZATION AGENT INVOCATION END #################
        if response.agent == "END":
            print("Execution flow completed:", response.execution_flow)
            return {
                "messages": [
                    HumanMessage(content=query),
                    AIMessage(content=json.dumps(summarizationData, indent=2))
                ],
                "current_agent": "END",
                "state": state  # Return updated state
            }

        # Otherwise, return the agent's instruction and continue.
        return {
            "messages": [
                HumanMessage(content=query),
                AIMessage(content=json.dumps(summarizationData, indent=2))
            ],
            "current_agent": response.agent,
            "state": state  # Return updated state
        }
    
    def knowledge_agent(self, state: AgentHistory):
        print("------KNOWLEDGE AGENT------")
        curr_agent = state.current_agent
        url = "https://smartbygep.atlassian.net/wiki/spaces/~712020fb23db945f4b48a78712d6e43ffb656e/pages/5049483275/Invoice+Basic+Flow"

        print("STATE IN KNOWLEDGE AGENT",state)

        confluence_server = os.getenv("CONFLUENCE_SERVER")
        jira_username = os.getenv("JIRA_USERNAME")

        jira_token = os.getenv("JIRA_API_TOKEN")

        knowledge_fetcher = KnowledgeBaseFetcher(jira_username, jira_token)

        # Fetch JIRA details
        curr_jira = knowledge_fetcher.fetch_confluence_page(url)
        print("Fetched UNIFIED Details:", curr_jira)
            
        from langchain_groq import ChatGroq

        llm2 = ChatGroq(
    model=os.environ["LLAMA_MODEL"],
    groq_api_key=os.environ["LLAMA_BASE_KEY"],
    temperature=0.7
        )        # Prepare prompt for LLM

        prompt = f"Extract Summary for  the following data {curr_jira}. Return a Proper Summary for the Flow in Breif. DO NOT TRY TO MISS ANY INFORMATION FROM THE INPUT"
        response = llm2.invoke(prompt)
        # If response is an AIMessage, extract its content
        if hasattr(response, "content"):
            content = response.content
        else:
            content = str(response)

        response1 = {
            "knowledge_base": content
        }
        return response1
    
    def historical_agent(self, state: AgentHistory):
        print("------HISTORICAL AGENT------")

        query = state.userQuery
        curr_jira = state.current_Jira_data
        keywords = state.keywords
        curr_agent = state.current_agent
        
        print("STATE IN HISTORICAL AGENT",state)
        print("KEYWORDS IN HISTORICAL AGENT:", keywords)

        jira_server = os.getenv("JIRA_SERVER")
        jira_username = os.getenv("JIRA_USERNAME")
        confluence_server = os.getenv("CONFLUENCE_SERVER")
        jira_token = os.getenv("JIRA_API_TOKEN")
        jiraUnified_fetcher = UnifiedDataFetcher(jira_server, confluence_server, jira_username, jira_token)

        # Fetch JIRA details
        curr_jira = jiraUnified_fetcher.search_jira(keywords)
        print("Fetched UNIFIED Details:", curr_jira)
        if not curr_jira:
            response_text = "No JIRA data available for processing."
        else:
            response_text = json.dumps(curr_jira)
            
        from langchain_groq import ChatGroq

        llm2 = ChatGroq(
    model=os.environ["LLAMA_MODEL"],
    groq_api_key=os.environ["LLAMA_BASE_KEY"],
    temperature=0.7
        )        # Prepare prompt for LLM
        prompt = f"Extract Historical Summarized Data for  the following data {curr_jira}. Return a Proper Summary for the Flow in Brief. DO NOT TRY TO MISS ANY INFORMATION FROM THE INPUT"
            # Only pass current_agent and query (not curr_jira)
        response = llm2.invoke(prompt)
        
        response1 = {
            "historical_data": response.content
        }

        # Otherwise, return the agent's instruction and continue.
        return response1

    def summarization_agent(self, input:dict[str, any]):
        print("------SUMMARIZATION AGENT------")

        curr_jira = input["summary"]
        historical = input["historical_data"]
        knowledge_base = input["knowledge_base"]
                    
        from langchain_groq import ChatGroq

        llm2 = ChatGroq(
    model=os.environ["LLAMA_MODEL"],
    groq_api_key=os.environ["LLAMA_BASE_KEY"],
    temperature=0.7
        )
        prompt = f"You are an expert SUMMARIZER analyst and product workflow specialist. You will analyze a JIRA ticket using the following mandatory inputs: 1) Summarized JIRA Data: {curr_jira} (this is the main reference and must not be ignored), 2) Current JIRA Raw Payload: {curr_jira}, 3) Historical insights and knowledge base for similar past tickets and system workflow {historical}. Your response must include: 1) Ticket Summary: Provide a crisp but complete summary including all key functional and technical details. 2) Workflow Analysis {knowledge_base}: Explain where this ticket fits in the overall system workflow and correlate any relevant historical patterns if applicable. 3) Impacted Areas: List affected components such as frontend modules, backend services, databases, APIs, third-party systems, business logic, automations, or contracts. 4) Risks and Side Effects: Mention possible failures like data issues, performance degradation, security risks, or regression areas. 5) Suggested Validation Strategy: Provide exactly 2 textual test cases (no code) in this format — Test Case 1: Objective, Preconditions, Steps, Expected Result. Test Case 2: Objective, Preconditions, Steps, Expected Result. Rules: Do not skip any detail from the input, do not hallucinate unknown facts, use historical data only when relevant, keep it structured, and provide practical engineer-focused insights. Now generate the analysis."

        # Prepare prompt for LLM
            # Only pass current_agent and query (not curr_jira)
        response = llm2.invoke(prompt)
        
        response1 = {
            "summarized_data": response.content
        }

        return response1
    
    def test_case_agent(self, state: AgentHistory):
        pass
    
    def summarize_resolution(self, resolution_text: str) -> str:
        """Summarizes the combined resolutions using the LLM."""
        prompt = f"Extract KeyWords the following summary into one best possible resolution:\n{resolution_text}\n JUST return Keywords comma separated:"
        response = self.llm.invoke(prompt)
        print("KEYWORDS", response)
        summary = response.content.strip()
        # Split the comma-separated string into an array
        keywords = [kw.strip() for kw in summary.split(",") if kw.strip()]
        print("KEYWORDS -------------", keywords)

        return keywords