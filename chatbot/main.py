import asyncio
from datetime import datetime
import os
from dotenv import dotenv_values
from utils.logger import Logger

# Set up logging to track application behavior
logger = Logger(__name__)

# Set up environment configuration and paths
_module_path = os.path.dirname(os.path.abspath(__file__))
env = dotenv_values(os.path.join(_module_path, ".env"))
for key, value in env.items():
    os.environ[key] = value
from contextlib import asynccontextmanager

from utils.ollama_utils import Ollama
from utils.config import get_table_name
from fastapi import FastAPI, HTTPException, Body, Response
from utils.databaseUtils import DatabaseInteraction
from fastapi.middleware.cors import CORSMiddleware
from utils import schemas as chat_schemas
from utils.chatbot_utils import generate_chat_id, form_result

# Constants
HISTORY_LENGTH = 60
MAX_MESSAGE_LENGTH = 1000

# Initialize database interaction for logging
log_database_interaction = DatabaseInteraction(
    table_name=get_table_name("CHATBOT_LOG")
)

# Initialize Ollama API for interacting with AI models
ollama_api = Ollama()

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Setup and teardown routine for the FastAPI application.
    Initializes database tables and loads the AI model on startup.
    Cleans up resources on shutdown.
    """
    # Before startup
    await log_database_interaction.create_tables()
    await ollama_api.load_model()
    yield
    # After shutdown
    await log_database_interaction.dispose()
    await ollama_api.shutdown()

# Create FastAPI app
app = FastAPI(
    title="Chatbot Backend API",
    description="API endpoints for creating and managing chatbot conversations.",
    version="1.0",
    lifespan=lifespan
)

# Add CORS middleware for cross-origin requests
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # Allow requests from any origin
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Endpoint to create a new chat session
@app.get(
    "/chat/new",
    responses=chat_schemas.get_create_chat_response_desc(),
    response_model=chat_schemas.ChatResponse,
)
async def new_chat(response: Response = None):
    """
    Create a new chat session and receive an immediate bot reply.

    Returns:
        A JSON object with metadata about the conversation,
        the bot's initial message, serialized data, and a unique chat ID.

    **Errors**
    - 429: Too Many Requests (rate limiting applied)
    """
    logger.info("Creating a new chat session.")

    chat_id, result_message = await generate_chat_id()
    data = [{
                "timestamp": datetime.now().isoformat(),
                "user_message": "Let's start",
                "final_prompt": "",
                }]
    # Prepare the initial payload for the conversation
    payload = {
        "conversation": [{
            "role": "user",
            "content": [{"type": "input_text", "text": "Let's start"}]
        }]
    }
    
    # Log the interaction in the database
    await log_database_interaction.insert_data(
        column_values={
            "id": chat_id,
            "data": data,
            "conversation": payload["conversation"]
        }
    )
    
    # Generate and return the result
    response_json = await form_result(
        result_message=result_message,
        chat_id=chat_id,
        data=data,
        payload=payload,
        log_database_interaction=log_database_interaction
    )
    
    logger.info(f"Chat session created successfully: {chat_id}")
    return response_json



@app.post(
    "/chat/{chat_id}",
    responses=chat_schemas.get_continue_chat_response_desc(),
    response_model=chat_schemas.ChatResponse,
)
async def continue_chat(
    chat_id: str,
    payload: chat_schemas.ChatContinueRequest = Body(
        ..., description="User's new input, plus any extra context"
    ),
):
    """
    Continue an existing chatbot session by sending a new user message and context.

    Args:
        chat_id (str): Unique identifier of the chat session.
        payload (ChatContinueRequest): JSON body with user's message and context.

    Returns:
        ChatResponse: The formatted response structure.
    
    Raises:
        HTTPException: For various error cases like 400, 404, and 429.
    """
    payload = payload.dict()  # Convert request body to dictionary
    try:
        # Retrieve the chat history from the database
        log_history = await log_database_interaction.get_data(chat_id)
        
        if log_history is None:
            raise HTTPException(
                status_code=404,
                detail="Chat does not exist. No chat with the given ID is known.",
            )
            
        payload["conversation"] = log_history[2]  # Get the conversation history
        prompt_history: dict = log_history[1]  # Get previous prompt history
        message = str(payload.get("message", "")).strip().lower()

        if message:
            message = message.replace("  ", " ")[:1000]  # Clean and limit the message length
            
            # Append user message to the conversation
            payload["conversation"].append({"role": "user", "content": [{"type": "input_text", "text": message}]})
            prompt_history.append({
                "timestamp": datetime.now().isoformat(),
                "user_message": message,
                "final_prompt": f"Prompt-{len(payload['conversation']) - 2}",
            })
        else:
            raise HTTPException(
                status_code=400,
                detail="Missing required field: message",
            )
        
        result_message = "result message"  # Replace with actual logic to get the result
        return await form_result(
            result_message=result_message,
            chat_id=chat_id,
            data=prompt_history,
            payload=payload,
            log_database_interaction=log_database_interaction
        )
    except HTTPException as http_ex:
        # Handle known HTTP exceptions
        raise http_ex  # Reraise the caught HTTPException for FastAPI to handle
    except Exception as e:
        # Handle unexpected exceptions
        return await form_result(
            result_message="I'm sorry, but I'm currently unable to process your request. Please try again later.",
            chat_id=chat_id,
            data={},
            payload=payload,
            log_database_interaction=log_database_interaction,
            error_message=str(e)
        )