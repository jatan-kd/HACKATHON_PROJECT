from langgraph.graph import START, END, StateGraph
from langgraph.checkpoint.memory import MemorySaver
from masterfunctions.functions import MasterFunctions
from utilities.state import AgentHistory
from IPython.display import Image


class MasterGraph:
    def __init__(self, llm, **kwargs) -> None:
        self.master_function_obj = MasterFunctions(llm=llm)
        print("Master Graph Initiated, Master Functions Object Created")

    def build_graph(self):
        workflow = StateGraph(AgentHistory)
        # Adding nodes for each agent in the required order
        workflow.add_node("GROOMING_AGENT", self.master_function_obj.agent_supervisor)
        # workflow.add_node("KNOWLEDGE_AGENT", self.master_function_obj.knowledge_agent)
        workflow.add_node("JIRA_AGENT", self.master_function_obj.jira_agent)
        # workflow.add_node("HISTORICAL_AGENT", self.master_function_obj.historical_agent)
        # workflow.add_node("SUMMARIZATION_AGENT", self.master_function_obj.summarization_agent)
        # workflow.add_node("TEST_CASE_AGENT", self.master_function_obj.test_case_agent)

        # Adding edges to define the flow
        workflow.add_edge(START, "GROOMING_AGENT")
        workflow.add_edge("GROOMING_AGENT", "JIRA_AGENT")
        workflow.add_edge("JIRA_AGENT", END)
        # workflow.add_edge("HISTORICAL_AGENT", "SUMMARIZATION_AGENT")
        # workflow.add_edge("SUMMARIZATION_AGENT", "TEST_CASE_AGENT")
        # workflow.add_edge("TEST_CASE_AGENT", END)

        memory = MemorySaver()
        graph = workflow.compile(checkpointer=memory)
        print("Workflow Graph Nodes:", list(workflow.nodes.keys()))
        print("Workflow Graph Edges:", workflow.edges)
        
        return graph