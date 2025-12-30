import os

# Configure logging
from utils.logger import Logger
# Set up logging to track application behavior
logger = Logger(__name__)

# Define the timestamp format for logging
timestamp_format = "%Y-%m-%d %H:%M:%S"

def get_config_creator(env, env_name_dev: str, env_name_pro: str, default_env: str = "DEV"):
    """Retrieve configuration value based on the environment."""
    if env is None:
        env = str(os.environ.get("ENV", default_env)).strip().upper()
    value = None

    if "DEV" in env:
        value = os.getenv(env_name_dev)
        logger.warning(f"{env_name_dev} is set as default in environment variables. Please choose 'PRO' if in production.")
    elif "PRO" in env:
        value = os.getenv(env_name_pro)
    else:
        logger.error(f"Could not find the {env} environment variable.")
        raise ValueError(f"Could not find the {env} environment variable.")

    if value is None:
        logger.warning(f"{env_name_dev if 'DEV' in env else env_name_pro} not found in environment variables.")
    
    return value

def get_openai_api_key(env=None):
    """Retrieve the OpenAI API key."""
    return get_config_creator(env, "OPENAI_API_KEY_DEV", "OPENAI_API_KEY_PRO")

def get_db_name(env=None):
    """Retrieve the database name."""
    return get_config_creator(env, "DB_NAME_DEV", "DB_NAME_PRO")

def get_db_username(env=None):
    """Retrieve the database username."""
    return get_config_creator(env, "POSTGRE_USERNAME_DEV", "POSTGRE_USERNAME_PRO")

def get_db_password(env=None):
    """Retrieve the database password."""
    return get_config_creator(env, "POSTGRE_PASSWORD_DEV", "POSTGRE_PASSWORD_PRO")

def get_db_host(env=None):
    """Retrieve the database host."""
    return get_config_creator(env, "DB_HOST_DEV", "DB_HOST_PRO")

def get_db_port(env=None):
    """Retrieve the database port."""
    return get_config_creator(env, "DB_PORT_DEV", "DB_PORT_PRO")

def get_table_name(env_key: str):
    """Retrieve the table name from environment variables."""
    env_key = env_key.upper()
    if env_key in os.environ:
        return os.environ[env_key]
    else:
        logger.warning(f"{env_key} not found in environment variables. Default value {env_key.lower()} will be used.")
        return env_key.lower()

def get_schema_name(env=None):
    """Retrieve the database schema name."""
    return get_config_creator(env, "DB_SCHEMA_DEV", "DB_SCHEMA_PRO")

def get_ollama_url(env=None):
    """Retrieve the Ollama service URL."""
    return get_config_creator(env, "OLLAMA_URL", "OLLAMA_URL")