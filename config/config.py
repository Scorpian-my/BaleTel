import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    API_ID = int(os.getenv("API_ID"))
    API_HASH = os.getenv("API_HASH")
    SESSION_NAME = os.getenv("SESSION_NAME")
    
    TOKEN = os.getenv("TOKEN")
    ADMIN_BALE = int(os.getenv("ADMIN_BALE"))
    
    MAIN_ADMIN_ID = ADMIN_BALE
    ADMINS = {MAIN_ADMIN_ID}
    
    ITEMS_PER_PAGE = 10

config = Config()