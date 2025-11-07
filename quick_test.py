"""
Quick sanity check for Phase 3 implementation.
Tests just the basic imports and persona loading without running full conversations.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).parent / "src"))

print("=" * 60)
print("QUICK PHASE 3 SANITY CHECK")
print("=" * 60)

# Test 1: Imports
print("\n1. Testing imports...")
try:
    from generate_synthetic_conversations import SyntheticConversationPipeline
    from parlant_inference_endpoint import create_parlant_endpoint
    from anthropic import Anthropic
    import os
    from dotenv import load_dotenv
    print("✓ All imports successful")
except Exception as e:
    print(f"✗ Import failed: {e}")
    sys.exit(1)

# Test 2: Load personas
print("\n2. Testing persona loading...")
try:
    import yaml
    with open("data/conversation_characters/financial_personas.yaml", 'r') as f:
        personas = yaml.safe_load(f)['users']
    print(f"✓ Loaded {len(personas)} personas")
    print(f"  - Elder: {sum(1 for p in personas if p['customer_type'] == 'Elder')}")
    print(f"  - Millenial: {sum(1 for p in personas if p['customer_type'] == 'Millenial')}")
    print(f"  - Small Business Owner: {sum(1 for p in personas if p['customer_type'] == 'Small Business Owner')}")
    print(f"  - Foreigner: {sum(1 for p in personas if p['customer_type'] == 'Foreigner')}")
except Exception as e:
    print(f"✗ Persona loading failed: {e}")
    sys.exit(1)

# Test 3: API key
print("\n3. Testing API key...")
try:
    load_dotenv()
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        print("✗ ANTHROPIC_API_KEY not found in .env")
        sys.exit(1)
    print(f"✓ API key found: {api_key[:20]}...")
except Exception as e:
    print(f"✗ API key check failed: {e}")
    sys.exit(1)

# Test 4: Model access
print("\n4. Testing Claude model access...")
try:
    client = Anthropic(api_key=api_key)
    response = client.messages.create(
        model="claude-3-5-haiku-20241022",
        max_tokens=10,
        messages=[{"role": "user", "content": "Hi"}]
    )
    print(f"✓ claude-3-5-haiku-20241022 is accessible")
    print(f"  Response: {response.content[0].text}")
except Exception as e:
    print(f"✗ Model access failed: {e}")
    sys.exit(1)

# Test 5: Pipeline initialization
print("\n5. Testing pipeline initialization...")
try:
    pipeline = SyntheticConversationPipeline(
        personas_path="data/conversation_characters/financial_personas.yaml",
        output_dir="output/quick_test",
        model_id="claude-3-5-haiku-20241022",
        max_conversation_turns=3,
        timeout=120,
    )
    print(f"✓ Pipeline initialized")
    print(f"  - {len(pipeline.personas)} personas loaded")
    print(f"  - Assistant: {pipeline.assistant.name}")
    print(f"  - Model: {pipeline.model_id}")
except Exception as e:
    print(f"✗ Pipeline initialization failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\n" + "=" * 60)
print("✅ ALL QUICK CHECKS PASSED!")
print("="  * 60)
print("\nThe full Phase 3 tests should work now.")
print("Run: .venv/bin/python test_phase3.py")
