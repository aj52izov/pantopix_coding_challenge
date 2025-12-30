import ast
from ollama import AsyncClient
from utils.config import get_ollama_url
from utils.logger import Logger

class Ollama:
    def __init__(self, 
                 ollama_host_url: str = get_ollama_url(), 
                 model: str = "gemma3:12b"):
        """Initialize the Ollama client.
        
        Args:
            ollama_host_url (str): The base URL for the Ollama API.
            model (str): The model to use for generating responses.
        """
        self.ollama_client = AsyncClient(host=ollama_host_url, verify=False)
        self.model = model
        self.logger = Logger(__name__)

    async def shutdown(self):
        """Unload the model and clean up resources."""
        await self.unload_model()

    async def load_model(self) -> bool:
        """Load the specified model from the Ollama API.
        
        Args:
            timeout (str | int): Timeout for loading the model.

        Returns:
            bool: True if the model is loaded successfully, False otherwise.
        """
        try:
            result = await self.ollama_client.generate(
                model=self.model,
                keep_alive=-1
            )
            self.logger.info(f"Model {self.model} loaded successfully.")
            return result.get("done", False)
        except Exception as e:
            self.logger.error(f"Error loading model {self.model}: {e}")
            return False

    async def unload_model(self) -> bool:
        """Unload the model from the Ollama API.
        
        Returns:
            bool: True if the model is unloaded successfully, False otherwise.
        """
        try:
            result = await self.ollama_client.generate(
                model=self.model,
                keep_alive=0
            )
            self.logger.info(f"Model {self.model} unloaded successfully.")
            return result.get("done", False)
        except Exception as e:
            self.logger.error(f"Error unloading model {self.model}: {e}")
            return False

    async def generate_response(
        self,
        prompt: str,
        return_json: bool = False,
    ) -> str | dict | None:
        """Generate a response from the model based on the provided prompt.
        
        Args:
            prompt (str): The prompt to send to the model.
            timeout (str | int): Keep-alive timeout for the response.
            return_json (bool): Whether to return the response in JSON format.

        Returns:
            str | dict | None: The generated response or None on error.
        """
        kwargs = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "raw": True,
            "keep_alive": -1
        }
        if return_json:
            kwargs["format"] = "json"

        try:
            result = await self.ollama_client.generate(**kwargs)
            response = result.get("response")
            if return_json and isinstance(response, str):
                response = ast.literal_eval(response)
            return response
        except Exception as e:
            self.logger.error(f"Error generating response for prompt '{prompt}': {e}")
            return None

    async def extract_user_language(self, message: str) -> str:
        """Extract the language from the given message using the model.
        
        Args:
            message (str): The message to analyze for language detection.

        Returns:
            str: The detected language.
        """
        prompt = f"""
            You are an expert in natural language analysis with expertise in recognizing the language of a given text.
            Given the following message, identify the language used.
            Respond ONLY with a JSON object containing a single key "language" 
            and value being the detected language (e.g., "german", "english", etc.).
            Message: '''{message}'''
        """
        
        response = None
        while not response:
            response = await self.generate_response(prompt=prompt, return_json=True)
            if "language" not in response:
                response = None  # Retry if the response format is not correct
        return response