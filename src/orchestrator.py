import hashlib
import json
import os
import time
from langchain_openai import AzureChatOpenAI
from traitlets import Any
from agents.mastergraph import MasterGraph
from utilities.state import AgentHistory  # Ensure this import exists
from langchain_core.messages import SystemMessage,HumanMessage
import constants
from langgraph.pregel.types import StateSnapshot

class GroomingAgent:
    """
    This class orchestrates the features for the Grooming Agent.
    """
    llm = AzureChatOpenAI(azure_endpoint=os.environ["AZURE_OPENAI_ENDPOINT"],
                api_key=os.environ["OPENAI_API_KEY"], model="gpt-4.1", deployment_name="gpt-4.1", temperature=0.2, max_retries=3, request_timeout=180)
    _invoke_cache = {}

    if not llm:
        raise Exception("LLM is unresponsive")

    def __init__(self):
        """
        Class initializer
        """
        print("-------Creating the graph object-------")
        self.graph_obj = MasterGraph(llm=GroomingAgent.llm)
        print("-------Building the graph-------")
        self.graph = self.graph_obj.build_graph()
        print(MasterGraph(llm=GroomingAgent.llm))

    def set_memory(self, conv_id):
        """
        Sets the conversation ID onto self for the agent state management.
        """
        self.conv_id = conv_id
        self.state_obj = AgentHistory(userQuery="", conv_id=conv_id)
        return "Memory set successfully"
    
    def _hash_json(self, data: Any) -> str:
        """Helper that returns a SHA256 hex digest of the json-serialized input."""
        return hashlib.sha256(
            json.dumps(data, sort_keys=True, default=str).encode("utf-8")
        ).hexdigest()

    def invoke_graph(self, state_obj, config):
        """
        Invokes self.graph and caches the result for subsequent identical calls.
        Uses a time-based cache eviction approach.
        """
        # Generate a cache key by hashing both objects
        state_hash = self._hash_json(state_obj)
        config_hash = self._hash_json(config)
        cache_key = f"{state_hash}-{config_hash}"

        # Evict stale entries older than 10 seconds
        now = time.time()
        remove_keys = []
        for cached_key, (cached_time, _) in self._invoke_cache.items():
            if (now - cached_time) > 10:  # 10 seconds
                remove_keys.append(cached_key)
        for rk in remove_keys:
            del self._invoke_cache[rk]

        # Cache lookup
        if cache_key in self._invoke_cache:
            print("Using cached graph.invoke result.")
            return self._invoke_cache[cache_key][1]

        print("Cache miss; invoking graph.")
        output = self.graph.invoke(state_obj, config)

        self._invoke_cache[cache_key] = (now, output)
        return output
    
    def execute(self, user_input: str, **kwargs):
        """
        Executes the grooming agent's logic.
        """
        try:
            config = {"configurable": {"thread_id": self.conv_id, "llm": self.llm}}
            print("-------Graph built successfully-------")
            output = None

            print("----State object is not a snapshot-------")
            self.state_obj.userQuery = user_input
            self.state_obj.conv_id = self.conv_id

            print(f"Current state is {self.state_obj}")
            output = self.invoke_graph(self.state_obj, config)

            updated_state = self.graph.get_state(config)
            print(f"Updated state is {updated_state}")

            # Extract final response
            if updated_state.next:
                if updated_state.values["messages"][-1].tool_calls:
                    print(updated_state.values["messages"][-1])
                    response_obj = updated_state.values["messages"][-1].tool_calls[0]["args"]['question']
                else:
                    response_obj = updated_state.values["messages"][-1].content
            else:
                if 'messages' in updated_state.values and updated_state.values["messages"]:
                    response_obj = updated_state.values["messages"][-1].content
                elif 'struct_response' in output:
                    response_obj = output["struct_response"]
                    if 'html' in response_obj:
                        response_obj = response_obj["html"]
                    else:
                        response_obj.pop("complete_response", None)
                else:
                    response_obj = output["messages"][-1].content

            print(f"Response from the graph is {response_obj}")

            issuccess = True
            answer = response_obj
            message = response_obj
            resp_comb = (output['current_agent'])
            answer_found = True

        except Exception as e:
            print(f"Error occured while executing the graph. Error - {str(e)}")
            issuccess = False
            answer = e
            message = f"Error - {str(e)}"
            resp_comb = ""
            answer_found = False

        output = self._convert_to_output_format(issuccess, answer, answer_found, resp_comb)
        return issuccess, message, output
    
    def _convert_to_output_format(self, issuccess, answer, answer_found, resp_comb):
        """
        Converts the answer to the right output format

        Parameters:
        ----------
        issuccess: bool
            The success flag

        answer: str
            The generated answer from the llm

        resp_comb: tuple
            Combination of current_agent and docType

        Returns:
        --------
        dict
            The output dict
        """
        output = {}
        response_dict = {}
        if not issuccess:
            output["status"] = 0
            output["conversationId"] = self.conv_id
            output["conversationState"] = "ending"
            output["isConversationEnd"] = True
            output["hasFailed"] = True
            output["statusMessage"] = "Failed to generate the answer"
            output["conversationMessages"] = []

        else:
            if resp_comb[1] == "quickQuote":
                response_dict["responseType"] = 'html_summary' if resp_comb[0] in ['ONE_SHOT_EVENT',"TEMPLATE_MANAGER"] else (
                    "html_question" if resp_comb[0] == "NONE" else "html_text")
            else:
                response_dict['responseType'] = "summaryCard" if 'eventDetails' in answer else (
                    "table" if 'tableData' in answer and answer['tableData'] else "text")
                if response_dict['responseType'] == "summaryCard":
                    answer['eventDetails'] = answer['eventDetails'][0]
            response_dict['responseData'] = answer
            # response_dict['responseData'] = self.render_as_html(answer)

            output["status"] = 1
            output["conversationId"] = self.conv_id
            output["conversationState"] = "ongoing"
            output["message"] = "Answer generated successfully"
            output["conversationMessages"] = [response_dict]
            output['answer_found'] = answer_found

        return output