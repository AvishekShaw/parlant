"""
Phase 1 Tests: Setup & Dependencies

This script tests that:
1. Tools can be imported and have correct signatures
2. Mock tools return expected data structures
3. Journey modules can be imported
4. Main.py agent setup completes successfully
"""

import asyncio
import sys
from pathlib import Path
from typing import Dict, Any

# Add current directory to path
sys.path.insert(0, str(Path(__file__).parent))

import parlant.sdk as p
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


def print_warning(message: str):
    """Print a warning message."""
    print(f"{Colors.YELLOW}⚠ {message}{Colors.RESET}")


async def test_tools_import():
    """Test that tools can be imported successfully."""
    print_test_header("Tools Import Test")

    try:
        import tools
        print_success("Tools module imported successfully")

        # Check that all required tools exist
        required_tools = [
            'list_user_cards',
            'fetch_recent_transactions',
            'file_dispute',
            'lock_card',
            'get_user_address',
            'process_card_replacement',
        ]

        for tool_name in required_tools:
            if hasattr(tools, tool_name):
                print_success(f"Tool '{tool_name}' found")
            else:
                print_error(f"Tool '{tool_name}' not found")
                return False

        return True

    except Exception as e:
        print_error(f"Failed to import tools: {e}")
        return False


async def test_journeys_import():
    """Test that journey modules can be imported."""
    print_test_header("Journeys Import Test")

    try:
        from journeys import dispute_transaction, lock_card, replace_card
        print_success("Journey modules imported successfully")

        # Check that each journey has create_journey function
        for journey_name, journey_module in [
            ('dispute_transaction', dispute_transaction),
            ('lock_card', lock_card),
            ('replace_card', replace_card),
        ]:
            if hasattr(journey_module, 'create_journey'):
                print_success(f"Journey '{journey_name}' has create_journey function")
            else:
                print_error(f"Journey '{journey_name}' missing create_journey function")
                return False

        return True

    except Exception as e:
        print_error(f"Failed to import journeys: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_mock_tools_data_structure():
    """Test that mock tools return expected data structures."""
    print_test_header("Mock Tools Data Structure Test")

    try:
        # Import tools
        import tools

        # Create a mock context
        class MockCustomer:
            def __init__(self, name: str):
                self.name = name

        class MockContext:
            def __init__(self, customer_name: str):
                self.customer = MockCustomer(customer_name)

        context = MockContext("Elder")

        # Test list_user_cards
        print("\nTesting list_user_cards...")
        cards_tool_result = await tools.list_user_cards(context)
        assert isinstance(cards_tool_result, p.ToolResult), "list_user_cards should return ToolResult"
        cards_result = cards_tool_result.data
        assert 'cards' in cards_result, "list_user_cards should return 'cards' key"
        assert isinstance(cards_result['cards'], list), "cards should be a list"
        if cards_result['cards']:
            assert 'card_name' in cards_result['cards'][0], "card should have 'card_name'"
            assert 'card_number' in cards_result['cards'][0], "card should have 'card_number'"
        print_success(f"list_user_cards returns correct structure: {len(cards_result['cards'])} cards")

        # Test fetch_recent_transactions
        print("\nTesting fetch_recent_transactions...")
        transactions_tool_result = await tools.fetch_recent_transactions(context, "**** **** **** 1234")
        assert isinstance(transactions_tool_result, p.ToolResult), "fetch_recent_transactions should return ToolResult"
        transactions_result = transactions_tool_result.data
        assert 'transactions' in transactions_result, "fetch_recent_transactions should return 'transactions' key"
        assert isinstance(transactions_result['transactions'], list), "transactions should be a list"
        if transactions_result['transactions']:
            transaction = transactions_result['transactions'][0]
            assert 'date' in transaction, "transaction should have 'date'"
            assert 'merchant_name' in transaction, "transaction should have 'merchant_name'"
            assert 'amount' in transaction, "transaction should have 'amount'"
        print_success(f"fetch_recent_transactions returns correct structure: {len(transactions_result['transactions'])} transactions")

        # Test file_dispute
        print("\nTesting file_dispute...")
        dispute_tool_result = await tools.file_dispute(
            context,
            card_number="**** **** **** 1234",
            date="2024-01-15",
            amount="89.99",
            merchant_name="Amazon.com",
            reason="Did not authorize this purchase"
        )
        assert isinstance(dispute_tool_result, p.ToolResult), "file_dispute should return ToolResult"
        dispute_result = dispute_tool_result.data
        assert 'dispute_id' in dispute_result, "file_dispute should return 'dispute_id'"
        assert 'status' in dispute_result, "file_dispute should return 'status'"
        print_success(f"file_dispute returns correct structure: {dispute_result['dispute_id']}")

        # Test lock_card
        print("\nTesting lock_card...")
        lock_tool_result = await tools.lock_card(
            context,
            card_number="**** **** **** 1234",
            reason="lost"
        )
        assert isinstance(lock_tool_result, p.ToolResult), "lock_card should return ToolResult"
        lock_result = lock_tool_result.data
        assert 'status' in lock_result, "lock_card should return 'status'"
        assert 'locked_card' in lock_result, "lock_card should return 'locked_card'"
        print_success(f"lock_card returns correct structure: status={lock_result['status']}")

        # Test get_user_address
        print("\nTesting get_user_address...")
        address_tool_result = await tools.get_user_address(context)
        assert isinstance(address_tool_result, p.ToolResult), "get_user_address should return ToolResult"
        address_result = address_tool_result.data
        assert 'address' in address_result, "get_user_address should return 'address'"
        print_success(f"get_user_address returns correct structure: {address_result['address']}")

        # Test process_card_replacement
        print("\nTesting process_card_replacement...")
        replacement_tool_result = await tools.process_card_replacement(
            context,
            card_number="**** **** **** 1234",
            reason="lost",
            address="123 Main St, Springfield, IL 62701",
            delivery_speed="express"
        )
        assert isinstance(replacement_tool_result, p.ToolResult), "process_card_replacement should return ToolResult"
        replacement_result = replacement_tool_result.data
        assert 'reference_id' in replacement_result, "process_card_replacement should return 'reference_id'"
        assert 'status' in replacement_result, "process_card_replacement should return 'status'"
        assert 'delivery_date' in replacement_result, "process_card_replacement should return 'delivery_date'"
        print_success(f"process_card_replacement returns correct structure: {replacement_result['reference_id']}")

        return True

    except Exception as e:
        print_error(f"Mock tools data structure test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_agent_setup():
    """Test that agent setup from main.py completes successfully."""
    print_test_header("Agent Setup Test")

    try:
        load_dotenv()
        from textwrap import dedent
        from journeys import dispute_transaction, lock_card, replace_card

        # Create a minimal server instance
        async with p.Server(
            log_level=p.LogLevel.INFO,
            session_store="transient",  # Use transient for testing
            nlp_service=p.NLPServices.anthropic,
        ) as server:
            print_success("Server instance created")

            # Create customers
            await server.create_customer(name="Elder")
            await server.create_customer(name="Millenial")
            print_success("Test customers created")

            # Create agent
            agent = await server.create_agent(
                name="Chase Digital Assistant",
                description=dedent("""\
                    You're a customer service agent for the Chase bank.

                    You work directly on the Chase mobile app and help customers with their needs with respect to Chase's offerings, such as credit cards, loans, and other banking services.

                    When talking about and representing Chase, use "we" and "us" to signify that you're speaking on behalf of the company.

                    IMPORTANT: Always reply in markdown format with proper paragraph separation.

                    IMPORTANT: Sometimes a user will provide certain information implicitly, such as saying "that one", while referring to certain details.
                    In those cases, do your best to infer the information as opposed to tediously asking/seeking confirmation for the specifics explicitly.
                    """),
                composition_mode=p.CompositionMode.STRICT,
            )
            print_success(f"Agent created: {agent.name}")

            # Create one journey (dispute_transaction) for testing
            dispute_journey = await dispute_transaction.create_journey(server, agent)
            print_success(f"Dispute transaction journey created")

            # Add a simple guideline
            await agent.create_guideline(
                condition="user is not in a position to call customer care",
                action="ask if they'd like you to connect them with a human representative through chat",
            )
            print_success("Global guideline added")

            print_success("Agent setup completed successfully!")
            return True

    except Exception as e:
        print_error(f"Agent setup test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def run_all_tests():
    """Run all Phase 1 tests."""
    print(f"\n{Colors.BLUE}{'=' * 60}{Colors.RESET}")
    print(f"{Colors.BLUE}PHASE 1 TEST SUITE{Colors.RESET}")
    print(f"{Colors.BLUE}{'=' * 60}{Colors.RESET}")

    results = []

    # Run tests
    results.append(("Tools Import", await test_tools_import()))
    results.append(("Journeys Import", await test_journeys_import()))
    results.append(("Mock Tools Data Structure", await test_mock_tools_data_structure()))
    results.append(("Agent Setup", await test_agent_setup()))

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
        print(f"\n{Colors.GREEN}🎉 All Phase 1 tests passed! Ready to proceed to Phase 2.{Colors.RESET}\n")
        return True
    else:
        print(f"\n{Colors.RED}❌ Some tests failed. Please fix the issues before proceeding.{Colors.RESET}\n")
        return False


if __name__ == "__main__":
    # Run all tests
    success = asyncio.run(run_all_tests())
    sys.exit(0 if success else 1)
