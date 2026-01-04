from uuid import uuid4
import asyncio

async def generate_chat_id() -> tuple:
    """
    Asynchronously generates a unique chat ID and returns an initial greeting message.
    
    Returns:
        tuple: 
            - chat_id (str): A unique identifier for the chat session.
            - result_message (str): An initial message from the AI assistant.
    """
    # Generate a unique chat ID using UUID4
    chat_id = str(uuid4())
    
    # Initial greeting message from the assistant
    result_message = "Hello! How can I assist you today?"
    
    return chat_id, result_message

async def form_result(
    result_message: str,
    chat_id: str,
    data: dict | list,
    payload: dict,
    log_database_interaction,
    error_message: str = None,
) -> dict:
    """
    Forms the result to be returned to the frontend.

    Args:
        result_message (str): The response message.
        chat_id (str): The unique identifier for the chat session.
        data (dict | list): Data to be transferred.
        payload (dict): The interaction payload that includes conversation history.
        log_database_interaction: An instance for logging interactions.
        error_message (str, optional): An optional error message to override the result message.
    
    Returns:
        dict: A structured response to be sent back to the client.
    """
    # Use the provided error message, if any
    if error_message:
        result_message = error_message
        
    # Append the assistant's response to the conversation history
    payload["conversation"].append(
        {
            "role": "assistant",
            "message": str(result_message),
        }
    )
    
    # Log the conversation update asynchronously
    asyncio.create_task(log_database_interaction.update_data(
        id=chat_id,
        column_values={
            "conversation": payload["conversation"],
            "data": data,
        },
    ))

    # Build the response object
    result = {
        "meta": {
            "terms_violated": False,  # You can change this based on your own logic
            "message_number": len(payload["conversation"]) - 1,  # Correctly count messages
            "final_message": False,  # Set this true if it’s the last message
        },
        "message": result_message,
        "data": data,  # Store data without converting to string to maintain its structure
        "id": chat_id,
    }
    return result