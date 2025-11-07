"""
Phase 3 Tests: End-to-End Synthetic Conversation Generation

This script tests the complete pipeline:
1. Loading financial personas
2. Starting Parlant server
3. Generating conversations via LLM-simulated personas
4. Exporting to Parlant format
5. Validating output quality
"""

import asyncio
import json
import sys
from pathlib import Path
from dotenv import load_dotenv

# Add current directory to path
sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).parent / "src"))

from generate_synthetic_conversations import (
    ParlantServerManager,
    SyntheticConversationPipeline,
    Colors,
)


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


async def test_persona_loading():
    """Test that financial personas can be loaded correctly."""
    print_test_header("Persona Loading Test")

    try:
        import yaml

        personas_path = Path("data/conversation_characters/financial_personas.yaml")
        if not personas_path.exists():
            print_error(f"Personas file not found: {personas_path}")
            return False

        with open(personas_path, 'r') as f:
            data = yaml.safe_load(f)

        personas = data['users']
        print_success(f"Loaded {len(personas)} personas")

        # Check required fields
        required_fields = ['name', 'customer_type', 'description', 'personality', 'scenario', 'dispute_reason', 'summary']
        for idx, persona in enumerate(personas[:3], 1):  # Check first 3
            print_info(f"Checking persona {idx}: {persona['name']}")
            for field in required_fields:
                if field not in persona:
                    print_error(f"Missing field '{field}' in persona {persona['name']}")
                    return False
                print(f"  ✓ {field}: {str(persona[field])[:50]}...")

        # Check customer type distribution
        customer_types = {}
        for persona in personas:
            ct = persona['customer_type']
            customer_types[ct] = customer_types.get(ct, 0) + 1

        print_info("\nCustomer type distribution:")
        for ct, count in sorted(customer_types.items()):
            print(f"  {ct}: {count}")

        expected_types = ['Elder', 'Millenial', 'Small Business Owner', 'Foreigner']
        for ct in expected_types:
            if ct not in customer_types:
                print_error(f"Missing customer type: {ct}")
                return False

        print_success(f"All {len(expected_types)} customer types represented")
        return True

    except Exception as e:
        print_error(f"Persona loading test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_pipeline_initialization():
    """Test that the pipeline can be initialized correctly."""
    print_test_header("Pipeline Initialization Test")

    try:
        load_dotenv()

        # Create pipeline with test output directory
        pipeline = SyntheticConversationPipeline(
            personas_path="data/conversation_characters/financial_personas.yaml",
            output_dir="output/test_phase3",
            model_id="claude-3-5-haiku-20241022",  # Cost-efficient model
            max_conversation_turns=5,  # Short for testing
            timeout=120,
        )

        print_success("Pipeline initialized successfully")
        print_success(f"Loaded {len(pipeline.personas)} personas")
        print_success(f"Assistant: {pipeline.assistant.name}")
        print_success(f"Output directory: {pipeline.output_dir}")

        # Verify assistant description
        assert "Chase" in pipeline.assistant.description, "Assistant should mention Chase"
        print_success("Assistant description validated")

        return True

    except Exception as e:
        print_error(f"Pipeline initialization test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_single_conversation_generation():
    """Test generating a single conversation (pilot test)."""
    print_test_header("Single Conversation Generation Test (Pilot)")

    load_dotenv()

    try:
        # Create pipeline with single persona (first Elder persona)
        import yaml
        with open("data/conversation_characters/financial_personas.yaml", 'r') as f:
            all_personas = yaml.safe_load(f)['users']

        # Find first Elder persona
        elder_persona = next(p for p in all_personas if p['customer_type'] == 'Elder')
        print_info(f"Testing with persona: {elder_persona['name']}")

        # Create temporary personas file with just one persona
        temp_personas_path = Path("output/test_phase3/temp_single_persona.yaml")
        temp_personas_path.parent.mkdir(parents=True, exist_ok=True)
        with open(temp_personas_path, 'w') as f:
            yaml.dump({'users': [elder_persona]}, f)

        # Create pipeline
        pipeline = SyntheticConversationPipeline(
            personas_path=str(temp_personas_path),
            output_dir="output/test_phase3/single_conversation",
            model_id="claude-3-5-haiku-20241022",  # Cost-efficient model
            max_conversation_turns=5,  # Short for testing
            timeout=120,
        )

        # Start server and generate conversation
        with ParlantServerManager() as server:
            print_info("Generating single conversation...")
            conversations = pipeline.generate_all_conversations(server)

            # Validate results
            assert len(conversations) == 1, f"Expected 1 conversation, got {len(conversations)}"
            print_success("Generated 1 conversation")

            conv = conversations[0]
            assert len(conv.messages) > 0, "Conversation should have messages"
            print_success(f"Conversation has {len(conv.messages)} messages")

            # Check message structure
            for msg in conv.messages[:3]:  # Check first 3 messages
                assert hasattr(msg, 'role'), "Message should have role"
                assert hasattr(msg, 'content'), "Message should have content"
                assert len(msg.content) > 0, "Message content should not be empty"
                print(f"  ✓ {msg.role.name}: {msg.content[:80]}...")

            # Export and validate
            pipeline.export_to_parlant_format(conversations)
            pipeline.generate_summary_report(conversations)

            # Check output files exist
            output_dir = Path("output/test_phase3/single_conversation")
            assert (output_dir / "sessions.json").exists(), "sessions.json should exist"
            assert (output_dir / "events.json").exists(), "events.json should exist"
            assert (output_dir / "generation_summary.json").exists(), "summary should exist"
            print_success("All output files created")

            # Validate sessions.json structure
            with open(output_dir / "sessions.json", 'r') as f:
                sessions = json.load(f)
            assert len(sessions) == 1, "Should have 1 session"
            assert "id" in sessions[0], "Session should have id"
            assert "customer_id" in sessions[0], "Session should have customer_id"
            print_success("sessions.json structure validated")

            # Validate events.json structure
            with open(output_dir / "events.json", 'r') as f:
                events = json.load(f)
            assert len(events) > 0, "Should have events"
            assert events[0]["kind"] == "message", "Event should be message"
            assert "source" in events[0], "Event should have source"
            assert "data" in events[0], "Event should have data"
            print_success("events.json structure validated")

        # Cleanup temp file
        temp_personas_path.unlink()

        return True

    except Exception as e:
        print_error(f"Single conversation generation test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_multi_persona_generation():
    """Test generating conversations for multiple personas (2-3)."""
    print_test_header("Multi-Persona Generation Test")

    load_dotenv()

    try:
        # Create pipeline with 3 personas (one from each main type for diversity)
        import yaml
        with open("data/conversation_characters/financial_personas.yaml", 'r') as f:
            all_personas = yaml.safe_load(f)['users']

        # Select 3 personas from different customer types
        selected_personas = []
        for customer_type in ['Elder', 'Millenial', 'Small Business Owner']:
            persona = next(p for p in all_personas if p['customer_type'] == customer_type)
            selected_personas.append(persona)

        print_info(f"Testing with {len(selected_personas)} personas:")
        for p in selected_personas:
            print(f"  - {p['name']} ({p['customer_type']})")

        # Create temporary personas file
        temp_personas_path = Path("output/test_phase3/temp_multi_personas.yaml")
        temp_personas_path.parent.mkdir(parents=True, exist_ok=True)
        with open(temp_personas_path, 'w') as f:
            yaml.dump({'users': selected_personas}, f)

        # Create pipeline
        pipeline = SyntheticConversationPipeline(
            personas_path=str(temp_personas_path),
            output_dir="output/test_phase3/multi_conversation",
            model_id="claude-3-5-haiku-20241022",  # Cost-efficient model
            max_conversation_turns=5,  # Short for testing
            timeout=120,
        )

        # Start server and generate conversations
        with ParlantServerManager() as server:
            print_info("Generating multiple conversations...")
            conversations = pipeline.generate_all_conversations(server)

            # Validate results
            assert len(conversations) == 3, f"Expected 3 conversations, got {len(conversations)}"
            print_success(f"Generated {len(conversations)} conversations")

            # Check each conversation
            for idx, conv in enumerate(conversations, 1):
                print_info(f"Conversation {idx}: {conv.id}")
                assert len(conv.messages) > 0, f"Conversation {idx} should have messages"
                print(f"  ✓ {len(conv.messages)} messages")

            # Export and validate
            pipeline.export_to_parlant_format(conversations)
            pipeline.generate_summary_report(conversations)

            # Check output files
            output_dir = Path("output/test_phase3/multi_conversation")
            with open(output_dir / "sessions.json", 'r') as f:
                sessions = json.load(f)
            assert len(sessions) == 3, "Should have 3 sessions"
            print_success("All 3 sessions exported correctly")

            with open(output_dir / "events.json", 'r') as f:
                events = json.load(f)
            assert len(events) > 0, "Should have events"
            print_success(f"Exported {len(events)} total events")

            # Check summary
            with open(output_dir / "generation_summary.json", 'r') as f:
                summary = json.load(f)
            assert summary["total_conversations"] == 3, "Summary should show 3 conversations"
            assert "customer_type_distribution" in summary, "Summary should have customer type distribution"
            print_success("Summary report validated")

        # Cleanup
        temp_personas_path.unlink()

        return True

    except Exception as e:
        print_error(f"Multi-persona generation test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def run_all_tests():
    """Run all Phase 3 tests."""
    print(f"\n{Colors.BLUE}{'=' * 60}{Colors.RESET}")
    print(f"{Colors.BLUE}PHASE 3 TEST SUITE{Colors.RESET}")
    print(f"{Colors.BLUE}{'=' * 60}{Colors.RESET}")

    results = []

    # Run tests in order
    results.append(("Persona Loading", await test_persona_loading()))
    results.append(("Pipeline Initialization", await test_pipeline_initialization()))
    results.append(("Single Conversation Generation (Pilot)", await test_single_conversation_generation()))
    results.append(("Multi-Persona Generation", await test_multi_persona_generation()))

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
        print(f"\n{Colors.GREEN}🎉 All Phase 3 tests passed! Pipeline is ready for full generation.{Colors.RESET}\n")
        return True
    else:
        print(f"\n{Colors.RED}❌ Some tests failed. Please fix the issues before proceeding.{Colors.RESET}\n")
        return False


if __name__ == "__main__":
    # Run all tests
    success = asyncio.run(run_all_tests())
    sys.exit(0 if success else 1)
