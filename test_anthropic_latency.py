"""
Test Anthropic API latency to diagnose if API slowness is causing timeouts.

Run this script to check if the Anthropic API is responding quickly:
    .venv/bin/python test_anthropic_latency.py

Expected: <5s per request
If >10s per request: API is likely slow or rate limited
"""

import time
from anthropic import Anthropic
import os
from dotenv import load_dotenv

load_dotenv()

def test_api_latency():
    """Test Anthropic API response times."""
    client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

    print("=" * 70)
    print("ANTHROPIC API LATENCY TEST")
    print("=" * 70)
    print(f"Model: claude-3-5-sonnet-20241022")
    print(f"Testing 3 sequential requests...\n")

    times = []

    for i in range(3):
        try:
            start = time.time()
            response = client.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=1024,
                messages=[{
                    "role": "user",
                    "content": f"Test {i+1}: Please respond with a brief hello message."
                }]
            )
            end = time.time()

            elapsed = end - start
            times.append(elapsed)

            print(f"Request {i+1}:")
            print(f"  Response time: {elapsed:.2f}s")
            print(f"  Input tokens:  {response.usage.input_tokens}")
            print(f"  Output tokens: {response.usage.output_tokens}")
            print(f"  Response:      {response.content[0].text[:60]}...")
            print()

        except Exception as e:
            print(f"Request {i+1} FAILED: {e}")
            print()

    if times:
        avg_time = sum(times) / len(times)
        max_time = max(times)
        min_time = min(times)

        print("=" * 70)
        print("SUMMARY")
        print("=" * 70)
        print(f"Average response time: {avg_time:.2f}s")
        print(f"Min response time:     {min_time:.2f}s")
        print(f"Max response time:     {max_time:.2f}s")
        print()

        # Interpretation
        if avg_time < 5:
            print("✅ RESULT: API is responding quickly")
            print("   The timeout issue is likely NOT due to API slowness.")
            print("   Recommendation: Reduce retry logic in Parlant (see ACTIONS.md Option 2)")
        elif avg_time < 10:
            print("⚠️  RESULT: API is responding moderately slowly")
            print("   The timeout issue may be partially due to API performance.")
            print("   Recommendation: Try increasing timeout to 180s (see ACTIONS.md Option 1)")
        else:
            print("❌ RESULT: API is responding very slowly")
            print("   The timeout issue is likely due to API slowness or rate limiting.")
            print("   Possible causes:")
            print("   - Anthropic API outage or degraded performance")
            print("   - Rate limiting on your API key")
            print("   - Network issues")
            print()
            print("   Recommendation:")
            print("   1. Check https://status.anthropic.com/")
            print("   2. Check your Anthropic account for rate limit warnings")
            print("   3. Try again in 1-2 hours")
            print("   4. If problem persists, consider Option 4 in ACTIONS.md")

    print("=" * 70)

if __name__ == "__main__":
    test_api_latency()
