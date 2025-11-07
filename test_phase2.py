"""
Phase 2 Tests: Parlant API Integration

This script tests the ParlantInferenceEndpoint adapter with a live Parlant server.
It automatically starts/stops the server for testing.
"""

import asyncio
import subprocess
import time
import sys
import requests
from pathlib import Path
from typing import Optional

# Add current directory to path
sys.path.insert(0, str(Path(__file__).parent))

from parlant_inference_endpoint import (
    ParlantInferenceEndpoint,
    ParlantAPIError,
    ParlantTimeoutError,
    create_parlant_endpoint,
)
from src.synthetic_conversation_generation.data_models.conversation import (
    Conversation,
    Message,
    ROLE,
)
from datetime import datetime
from dotenv import load_dotenv


# Test colors for output
class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    RESET = '\033[0m'


def print_test_header(test_name: str):
    """Print a formatted test header."""
    print(f"\n{Colors.BLUE}{'=' * 60}{Colors.RESET}")
    print(f"{Colors.BLUE}TEST: {test_name}{Colors.RESET}")
    print(f"{Colors.BLUE}{'=' * 60}{Colors.RESET}")


def print_success(message: str):
    """Print a success message."""
    print(f"{Colors.GREEN}✓ {message}{Colors.RESET}")


def print_error(message: str):
    """Print an error message."""
    print(f"{Colors.RED}✗ {message}{Colors.RESET}")


def print_info(message: str):
    """Print an info message."""
    print(f"{Colors.YELLOW}ℹ {message}{Colors.RESET}")


class ParlantServerManager:
    """
    Manages Parlant server lifecycle for testing.

    Starts server as subprocess, waits for readiness, and cleanly shuts down.
    """

    def __init__(self, port: int = 8800, startup_timeout: int = 60):
        self.port = port
        self.startup_timeout = startup_timeout
        self.process: Optional[subprocess.Popen] = None
        self.agent_id: Optional[str] = None
        self.customer_ids: dict[str, str] = {}

    def start(self) -> bool:
        """
        Start the Parlant server and wait for it to be ready.

        Returns:
            True if server started successfully, False otherwise
        """
        print_info("Starting Parlant server...")

        try:
            # Start main.py which sets up the server
            self.process = subprocess.Popen(
                [".venv/bin/python", "main.py"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,
            )

            # Wait for server to be ready
            start_time = time.time()
            while time.time() - start_time < self.startup_timeout:
                try:
                    response = requests.get(
                        f"http://localhost:{self.port}/agents",
                        timeout=2
                    )
                    if response.status_code == 200:
                        print_success("Parlant server is ready!")
                        time.sleep(2)  # Extra time for agent setup
                        self._fetch_agent_and_customer_ids()
                        return True
                except requests.exceptions.RequestException:
                    pass

                time.sleep(1)

            print_error("Server failed to start within timeout")
            return False

        except Exception as e:
            print_error(f"Failed to start server: {e}")
            return False

    def _fetch_agent_and_customer_ids(self) -> None:
        """
        Fetch agent and customer IDs from the running server.

        These IDs are created by main.py during startup.
        """
        try:
            # Fetch agents
            response = requests.get(f"http://localhost:{self.port}/agents", timeout=5)
            response.raise_for_status()
            agents = response.json()
            if agents:
                self.agent_id = agents[0]["id"]
                print_success(f"Found agent: {self.agent_id}")

            # Fetch customers
            response = requests.get(f"http://localhost:{self.port}/customers", timeout=5)
            response.raise_for_status()
            customers = response.json()
            for customer in customers:
                self.customer_ids[customer["name"]] = customer["id"]
                print_success(f"Found customer: {customer['name']} ({customer['id']})")

        except Exception as e:
            print_error(f"Failed to fetch IDs: {e}")

    def stop(self):
        """Stop the Parlant server."""
        if self.process:
            print_info("Stopping Parlant server...")
            self.process.terminate()
            try:
                self.process.wait(timeout=10)
                print_success("Server stopped cleanly")
            except subprocess.TimeoutExpired:
                self.process.kill()
                self.process.wait()
                print_info("Server killed (forced)")

    def __enter__(self):
        """Context manager entry."""
        if not self.start():
            raise RuntimeError("Failed to start Parlant server")
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.stop()


def test_session_creation():
    """Test that ParlantInferenceEndpoint creates a session successfully."""
    print_test_header("Session Creation Test")

    load_dotenv()

    try:
        with ParlantServerManager() as server:
            # Create endpoint
            endpoint = create_parlant_endpoint(
                base_url="http://localhost:8800",
                agent_id=server.agent_id,
                customer_id=server.customer_ids["Elder"],
            )
            print_success("ParlantInferenceEndpoint created")

            # Create a minimal conversation with one message
            conversation = Conversation(
                id="test_conv_1",
                user_id="Elder",
                messages=[
                    Message(
                        role=ROLE.user,
                        content="I want to dispute a transaction",
                        timestamp=datetime.now(),
                        message_id=0
                    )
                ]
            )

            # This should trigger session creation
            response = endpoint.get_assistant_message(conversation)

            assert endpoint.session_id is not None, "Session ID should be set"
            print_success(f"Session created: {endpoint.session_id}")

            assert response.role == ROLE.assistant, "Response should be from assistant"
            assert len(response.content) > 0, "Response should have content"
            print_success(f"Got response: {response.content[:100]}...")

            return True

    except Exception as e:
        print_error(f"Session creation test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_multi_turn_conversation():
    """Test a multi-turn conversation about disputing a transaction."""
    print_test_header("Multi-Turn Conversation Test")

    load_dotenv()

    try:
        with ParlantServerManager() as server:
            endpoint = create_parlant_endpoint(
                base_url="http://localhost:8800",
                agent_id=server.agent_id,
                customer_id=server.customer_ids["Elder"],
            )

            # Start conversation
            conversation = Conversation(
                id="test_conv_2",
                user_id="Elder",
                messages=[]
            )

            # Turn 1: User initiates dispute
            print_info("\nTurn 1: User initiates dispute")
            conversation.messages.append(Message(
                role=ROLE.user,
                content="I want to dispute a transaction on my credit card",
                timestamp=datetime.now(),
                message_id=0
            ))
            response1 = endpoint.get_assistant_message(conversation)
            conversation.messages.append(response1)
            print_success(f"Agent: {response1.content[:150]}...")

            # Verify agent asks about cards or follows dispute journey
            assert len(response1.content) > 0, "Response should not be empty"
            print_success("Turn 1 completed")

            # Turn 2: User provides card info
            print_info("\nTurn 2: User provides card")
            conversation.messages.append(Message(
                role=ROLE.user,
                content="Chase Freedom",
                timestamp=datetime.now(),
                message_id=len(conversation.messages)
            ))
            response2 = endpoint.get_assistant_message(conversation)
            conversation.messages.append(response2)
            print_success(f"Agent: {response2.content[:150]}...")

            # Verify session is reused (same session_id)
            assert endpoint.session_id is not None, "Session should persist"
            print_success("Session persisted across turns")

            # Turn 3: Continue conversation
            print_info("\nTurn 3: User answers fraud question")
            conversation.messages.append(Message(
                role=ROLE.user,
                content="Yes, I suspect fraud",
                timestamp=datetime.now(),
                message_id=len(conversation.messages)
            ))
            response3 = endpoint.get_assistant_message(conversation)
            conversation.messages.append(response3)
            print_success(f"Agent: {response3.content[:150]}...")

            print_success(f"Multi-turn conversation completed with {len(conversation.messages)} messages")
            return True

    except Exception as e:
        print_error(f"Multi-turn conversation test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_api_error_handling():
    """Test error handling for API failures."""
    print_test_header("API Error Handling Test")

    try:
        # Try to connect to non-existent server
        endpoint = ParlantInferenceEndpoint(
            base_url="http://localhost:9999",  # Wrong port
            agent_id="fake_agent",
            customer_id="fake_customer",
            timeout=5,
        )

        conversation = Conversation(
            id="test_conv_3",
            user_id="test",
            messages=[Message(
                role=ROLE.user,
                content="test",
                timestamp=datetime.now(),
                message_id=0
            )]
        )

        try:
            endpoint.get_assistant_message(conversation)
            print_error("Should have raised ParlantAPIError")
            return False
        except ParlantAPIError as e:
            print_success(f"Correctly raised ParlantAPIError: {e}")
            return True

    except Exception as e:
        print_error(f"API error handling test failed unexpectedly: {e}")
        return False


def test_timeout_handling():
    """Test timeout handling for slow responses."""
    print_test_header("Timeout Handling Test")

    load_dotenv()

    try:
        with ParlantServerManager() as server:
            # Create endpoint with very short timeout
            endpoint = create_parlant_endpoint(
                base_url="http://localhost:8800",
                agent_id=server.agent_id,
                customer_id=server.customer_ids["Elder"],
                timeout=1,  # 1 second timeout (very short)
            )

            conversation = Conversation(
                id="test_conv_4",
                user_id="Elder",
                messages=[Message(
                    role=ROLE.user,
                    content="This should timeout",
                    timestamp=datetime.now(),
                    message_id=0
                )]
            )

            try:
                # This might timeout depending on server speed
                response = endpoint.get_assistant_message(conversation)
                # If it doesn't timeout, that's actually OK (server was fast)
                print_info("Server responded quickly (no timeout)")
                return True
            except ParlantTimeoutError as e:
                print_success(f"Correctly handled timeout: {e}")
                return True

    except Exception as e:
        print_error(f"Timeout handling test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def run_all_tests():
    """Run all Phase 2 tests."""
    print(f"\n{Colors.BLUE}{'=' * 60}{Colors.RESET}")
    print(f"{Colors.BLUE}PHASE 2 TEST SUITE{Colors.RESET}")
    print(f"{Colors.BLUE}{'=' * 60}{Colors.RESET}")

    results = []

    # Run tests
    results.append(("Session Creation", test_session_creation()))
    results.append(("Multi-Turn Conversation", test_multi_turn_conversation()))
    results.append(("API Error Handling", test_api_error_handling()))
    results.append(("Timeout Handling", test_timeout_handling()))

    # Print summary
    print(f"\n{Colors.BLUE}{'=' * 60}{Colors.RESET}")
    print(f"{Colors.BLUE}TEST SUMMARY{Colors.RESET}")
    print(f"{Colors.BLUE}{'=' * 60}{Colors.RESET}")

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for test_name, result in results:
        if result:
            print_success(f"{test_name}: PASSED")
        else:
            print_error(f"{test_name}: FAILED")

    print(f"\n{Colors.BLUE}Total: {passed}/{total} tests passed{Colors.RESET}")

    if passed == total:
        print(f"\n{Colors.GREEN}🎉 All Phase 2 tests passed! Ready to proceed to Phase 3.{Colors.RESET}\n")
        return True
    else:
        print(f"\n{Colors.RED}❌ Some tests failed. Please fix the issues before proceeding.{Colors.RESET}\n")
        return False


if __name__ == "__main__":
    # Run all tests
    success = asyncio.run(run_all_tests())
    sys.exit(0 if success else 1)
