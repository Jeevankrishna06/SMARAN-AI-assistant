import os
from dotenv import load_dotenv

def init_env():
    """Centrally initializes environment variables from .env or .env/.env"""
    base_dir = os.path.dirname(os.path.abspath(__file__))
    
    # 1. Try nested .env/.env file
    nested_env = os.path.join(base_dir, ".env", ".env")
    if os.path.isfile(nested_env):
        load_dotenv(nested_env, override=False)
        
    # 2. Try root .env file if it's a file
    root_env = os.path.join(base_dir, ".env")
    if os.path.isfile(root_env):
        load_dotenv(root_env, override=False)
        
    # 3. Fallback standard load_dotenv
    load_dotenv(override=False)

init_env()
