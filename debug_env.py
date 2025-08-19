import os
from dotenv import load_dotenv

print("--- Starting debug script ---")
env_path = os.path.join(os.getcwd(), '.env')
print(f"Current Directory: {os.getcwd()}")
print(f"Looking for .env file at: {env_path}")

if os.path.exists(env_path):
    print(".env file FOUND.")
    load_dotenv()
    user = os.getenv('POSTGRES_USER')
    print(f"Value of POSTGRES_USER is: '{user}'")
else:
    print(".env file NOT FOUND.")

print("--- Finished debug script ---")
