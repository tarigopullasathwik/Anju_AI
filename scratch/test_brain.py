import sys
import os
from dotenv import load_dotenv

# Resolve paths
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Load dotenv to simulate real application boot
env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env")
load_dotenv(dotenv_path=env_path)

from brain.brain import process_query

def test_brain_fallback():
    print("Testing Brain logic fallback under Quota Exhausted status...")
    try:
        # A query that requires hitting the Gemini API
        query = "Can you design a high-frequency trading algorithm or explain quantum physics?"
        print(f"Query: '{query}'")
        response = process_query(query)
        print("\nSUCCESS: Brain processed query cleanly without crashing!")
        print(f"Response: {response}")
    except Exception as e:
        print(f"\nFATAL CRASH: {e}")

if __name__ == "__main__":
    test_brain_fallback()
