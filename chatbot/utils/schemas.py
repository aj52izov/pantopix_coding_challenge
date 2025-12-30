from pydantic import BaseModel, Field
from typing import Optional

# Configure logging
from utils.logger import Logger
# Set up logging to track application behavior
logger = Logger(__name__)

class Meta(BaseModel):
    """
    Metadata about the chat session.
    """
    terms_violated: bool = Field(
        ...,
        description="Indicates if the user violated bot terms/rules."
    )
    message_number: int = Field(
        ...,
        description="Total number of messages sent by the user in this chat session."
    )
    final_message: bool = Field(
        ...,
        description="True if this is the last message of the chat session."
    )

class Data(BaseModel):
    """
    data field structure for chat session. Represents the final prompt used.
    """
    timestamp: str = Field(..., description="ISO formatted timestamp of the message.")
    user_message: str = Field(..., description="The user's message content.")
    final_prompt: str = Field(...,description="The final prompt sent to the bot, if applicable.")
    
class ChatResponse(BaseModel):
    """
    Response structure from the chat bot.
    """
    meta: Meta = Field(..., description="Metadata about current chat status.")
    message: str = Field(..., description="The bot's reply to the user.")
    data: list[Data] = Field(..., description="Data related to the chat session.")
    id: str = Field(..., description="Unique chat session identifier.")

def get_create_chat_response_desc():
    """
    Returns description for the response of creating a chat session.
    """
    logger.info("Generating description for create chat response.")
    return {
        200: {
            "description": "Request was successfully executed.",
            "content": {
                "application/json": {
                    "example": {
                        "meta": {
                            "terms_violated": False,
                            "message_number": 2,
                            "final_message": False
                        },
                        "message": "Hello, how can I help you today?",
                        "data": "serialized-agent-data",
                        "id": "7b46caba-7ecd-42c9-9618-6657f3c301f6"
                    }
                }
            }
        },
        429: {
            "description": "Rate limit exceeded, too many requests.",
            "content": {
                "application/json": {
                    "example": {"detail": "Rate limit exceeded, too many requests."}
                }
            }
        }
    }

class ErrorResponse(BaseModel):
    """
    Structure for handling error messages.
    """
    detail: str

def get_continue_chat_response_desc():
    """
    Returns descriptions for the response of continuing a chat session.
    """
    logger.info("Generating description for continue chat response.")
    return {
        200: {
            "description": "OK",
            "content": {
                "application/json": {
                    "example": {
                        "meta": {
                            "terms_violated": False,
                            "message_number": 3,
                            "final_message": False
                        },
                        "message": "Sure, I can help with that. Do you want more details?",
                        "data": "{}",
                        "id": "7b46caba-7ecd-42c9-9618-6657f3c301f6"
                    }
                }
            }
        },
        400: {
            "description": "Bad request, missing or wrong content.",
            "model": ErrorResponse,
            "content": {
                "application/json": {
                    "example": { "detail": "Missing required field: message" }
                }
            }
        },
        404: {
            "description": "Chat does not exist.",
            "model": ErrorResponse,
            "content": {
                "application/json": {
                    "example": { "detail": "Chat does not exist." }
                }
            }
        },
        429: {
            "description": "Rate limit exceeded, too many requests.",
            "model": ErrorResponse,
            "content": {
                "application/json": {
                    "example": {"detail": "Rate limit exceeded, too many requests."}
                }
            }
        }
    }
    
class ChatContinueRequest(BaseModel):
    """
    Represents a user's request to continue a chat session.
    """
    message: str = Field(..., description='The user\'s message for the chat bot.')