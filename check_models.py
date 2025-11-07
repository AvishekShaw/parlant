"""
Quick script to check which Claude models are accessible with the current API key.
"""

import os
from anthropic import Anthropic
from dotenv import load_dotenv

load_dotenv()

client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

# List of common Claude model IDs to test
model_ids_to_test = [
    "claude-3-5-sonnet-20241022",
    "claude-3-5-sonnet-20240620",
    "claude-3-5-sonnet-latest",
    "claude-3-sonnet-20240229",
    "claude-3-opus-20240229",
    "claude-3-haiku-20240307",
    "claude-3-5-haiku-20241022",
]

print("Testing Claude model access...\n")

for model_id in model_ids_to_test:
    try:
        response = client.messages.create(
            model=model_id,
            max_tokens=10,
            messages=[{"role": "user", "content": "Hi"}]
        )
        print(f"✓ {model_id}: ACCESSIBLE")
        print(f"  Response: {response.content[0].text}\n")
    except Exception as e:
        error_msg = str(e)
        if "404" in error_msg or "not_found" in error_msg:
            print(f"✗ {model_id}: NOT FOUND (404)")
        elif "401" in error_msg or "authentication" in error_msg.lower():
            print(f"✗ {model_id}: AUTH ERROR")
        elif "permission" in error_msg.lower():
            print(f"✗ {model_id}: PERMISSION DENIED")
        else:
            print(f"✗ {model_id}: ERROR - {error_msg[:100]}")
        print()

print("\n" + "="*60)
print("Recommendation: Use the first ACCESSIBLE model for the pipeline")
