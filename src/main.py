from fastapi import FastAPI, HTTPException, status, Header, Request, Depends
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse, FileResponse
from langchain_openai import AzureChatOpenAI
import os
from dotenv import load_dotenv
import uvicorn

from api_utilities.fileId_generator import store_payload_in_mongodb
from api_utilities.mongo import MongoToJiraPusher, PushError
load_dotenv()
import json
import time
import threading
from contextlib import asynccontextmanager
import sys
from src import constants
from orchestrator import GroomingAgent
from pydantic import BaseModel
# Time
import pandas as pd
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
from src.masterfunctions.functions import MasterFunctions


grooming_agent = None

agent_creation_lock = threading.RLock()


from pathlib import Path
print("FilePath:", Path(__file__).absolute())
print("Directory Path:", Path().absolute()) 
def create_agent(agent_class, agent_name):
    with agent_creation_lock:
        log_messages = [
            f"----------------Instantiation at {application_start_time}----------------",
            f"----------------Creating Global {agent_name} Instance----------------"
        ]

        for message in log_messages:
            print(message)

        agent = agent_class()
        print(f"----------------Global {agent_name} Instance Created----------------")

        return agent


@asynccontextmanager
async def lifespan(app):
    global grooming_agent
    try:
        grooming_agent = create_agent(GroomingAgent, "GROOMING_AGENT")
    except Exception as e:
        print(f"Global instance creation failed: {e}")
    yield
    
    
app = FastAPI(root_path=f'/GroomingAgent',lifespan=lifespan) 
app.title = "GroomingAgent"

TIME_FORMAT = "%Y-%m-%d %H:%M:%S GMT"
application_start_time = datetime.now()
application_start_time = application_start_time.strftime(TIME_FORMAT)

@app.get("/api/healthcheck")
async def healthcheck():
    """
    HealthCheck endpoint to check if Fast API is running
    """
    message = {
        "status": 200,
        "message": "Application is up and running!",
        # "build_number": constants.BUILD_NUMBER,
        "current_directory": os.getcwd(),
        "current_directory_contents": os.listdir("."),
        "last_working_directory": os.path.dirname(os.getcwd()),
        "last_working_directory_contents": os.listdir(".."),
        "current_time": datetime.now(timezone.utc).strftime(TIME_FORMAT),
        "start_time": application_start_time
    }
    return JSONResponse(status_code=200, content=jsonable_encoder(message))

@app.get("/routes")
def get_routes():
    return [{"path": route.path, "methods": list(route.methods)} for route in app.router.routes]

class MessageRequest(BaseModel):
    conversationId: str
    userInput: str

class MessageResponse(BaseModel):
    status: int
    message: str
    conversationMessages: list

@app.post("/api/v1/GroomingAgent", response_model=MessageResponse)
async def respond_with_message(
    request: Request,
    body: MessageRequest,
):
    
    conv_id = body.conversationId
    user_input = body.userInput
    print(f"Received request with conversation ID: {conv_id}")
    # llm = AzureChatOpenAI(azure_endpoint=os.environ["AZURE_OPENAI_ENDPOINT"],
    #             api_key=os.environ["OPENAI_API_KEY"], model=constants.MODELNames.GPT4O_MODEL_NAME, deployment_name=constants.MODELDeployment.GPT4O_DEPLOYMENT_MODEL, temperature=0.01, max_retries=3, request_timeout=180)
    # grooming_agent = MasterFunctions(llm)
    
    grooming_agent = create_agent(GroomingAgent, "GROOMING_AGENT")

    # **Initialize conv_id before executing**
    grooming_agent.set_memory(conv_id)


    issuccess, message, output = grooming_agent.execute(
            user_input=user_input,
        )

    if message:
        status_code = 200
    else:
        status_code = 500

    message_obj = json.loads(message)
    message_obj["jiraId"] = user_input
    response = {
        "status": status_code,
        "message": message_obj,
    }
    return JSONResponse(content=response, status_code=status_code)

@app.get("/api/v1/PushMongoToJira")
async def push_mongo_summary_to_jira(fileId: str):
    """
    Takes fileId as a query parameter, fetches the Mongo document, and posts its summary to Jira.
    """
    try:
        pusher = MongoToJiraPusher()
        result = pusher.push_summary_by_fileid(fileId)
        return JSONResponse(status_code=200, content={"status": 1, "result": result})
    except PushError as e:
        return JSONResponse(status_code=500, content={"status": 0, "error": str(e)})
    except Exception as e:
        return JSONResponse(status_code=500, content={"status": 0, "error": str(e)})

@app.post("/api/v1/PostToDB")
async def post_to_db(request: Request):
    payload = await request.json()
    result = store_payload_in_mongodb(payload)
    return JSONResponse(content=result)

if __name__ == "__main__":
    #run the app
    uvicorn.run("main:app", host="0.0.0.0", port=4300, log_level="debug")
