import os
from datetime import datetime
from colorist import Color

# Define the timestamp format for logging
timestamp_format = "%Y-%m-%d %H:%M:%S"

def get_config_creator(env, env_name_dev: str, env_name_pro: str, default_env: str = "DEV"):
    """Retrieve configuration value based on the environment."""
    if env is None:
        env = str(os.environ.get("ENV", default_env)).strip().upper()

    date_time = datetime.now().strftime(timestamp_format)
    value = None

    if "DEV" in env:
        value = os.getenv(env_name_dev)
        print(f"{date_time}: {Color.GREEN}{env_name_dev} is set as default{Color.OFF} in environment variables. Please choose 'PRO' if in production.")
    elif "PRO" in env:
        value = os.getenv(env_name_pro)
    else:
        raise ValueError(f"Could not find the {env} environment variable.")

    if value is None:
        msg = f"{date_time}: {Color.YELLOW}{env_name_dev if 'DEV' in env else env_name_pro} not found{Color.OFF} in environment variables."
        print(msg)

    return value

def get_openai_api_key(env=None):
    return get_config_creator(env, "OPENAI_API_KEY_DEV", "OPENAI_API_KEY_PRO")

def get_db_name(env=None):
    return get_config_creator(env, "DB_NAME_DEV", "DB_NAME_PRO")

def get_db_username(env=None):
    return get_config_creator(env, "POSTGRE_USERNAME_DEV", "POSTGRE_USERNAME_PRO")

def get_db_password(env=None):
    return get_config_creator(env, "POSTGRE_PASSWORD_DEV", "POSTGRE_PASSWORD_PRO")

def get_db_host(env=None):
    return get_config_creator(env, "DB_HOST_DEV", "DB_HOST_PRO")

def get_db_port(env=None):
    return get_config_creator(env, "DB_PORT_DEV", "DB_PORT_PRO")

def get_table_name(env_key: str):
    """Retrieve the table name from environment variables."""
    env_key = env_key.upper()
    if env_key in os.environ:
        return os.environ[env_key]
    else:
        date_time = datetime.now().strftime(timestamp_format)
        print(f"{date_time}: {Color.YELLOW}{env_key} not found{Color.OFF} in environment variables. Default value {env_key.lower()} will be used.")
        return env_key.lower()

def get_schema_name(env=None):
    return get_config_creator(env, "DB_SCHEMA_DEV", "DB_SCHEMA_PRO")

def get_ollama_url(env=None):
    return get_config_creator(env, "OLLAMA_URL", "OLLAMA_URL")