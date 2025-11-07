"""
Phase 3: Synthetic Conversation Generation for Parlant

This script orchestrates the generation of synthetic conversations between
LLM-simulated personas and the Parlant Chase Digital Assistant agent.

It handles:
- Loading financial personas from YAML
- Starting/stopping Parlant server
- Creating conversation sessions
- Exporting to Parlant native format (sessions.json + events.json)
"""

import asyncio
import json
import logging
import os
import sys
import time
import yaml
import requests
import subprocess
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime
from dotenv import load_dotenv
from anthropic import Anthropic

# Add paths
sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).parent / "src"))

from parlant_inference_endpoint import (
    ParlantInferenceEndpoint,
    create_parlant_endpoint,
)
from synthetic_conversation_generation.data_models.assistant import Assistant
from synthetic_conversation_generation.data_models.character_card import CharacterCard
from synthetic_conversation_generation.data_models.conversation import Conversation
from synthetic_conversation_generation.conversation_generator import ConversationGenerator
from synthetic_conversation_generation.llm_queries.llm_query import AnthropicModelProvider

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Silence third-party loggers
logging.getLogger('openai').setLevel(logging.WARNING)
logging.getLogger('anthropic').setLevel(logging.WARNING)
logging.getLogger('httpx').setLevel(logging.WARNING)


# ANSI color codes
class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    MAGENTA = '\033[95m'
    CYAN = '\033[96m'
    RESET = '\033[0m'


def print_header(message: str):
    """Print a formatted header."""
    print(f"\n{Colors.BLUE}{'=' * 70}{Colors.RESET}")
    print(f"{Colors.BLUE}{message}{Colors.RESET}")
    print(f"{Colors.BLUE}{'=' * 70}{Colors.RESET}")


def print_success(message: str):
    """Print a success message."""
    print(f"{Colors.GREEN}✓ {message}{Colors.RESET}")


def print_error(message: str):
    """Print an error message."""
    print(f"{Colors.RED}✗ {message}{Colors.RESET}")


def print_info(message: str):
    """Print an info message."""
    print(f"{Colors.YELLOW}ℹ {message}{Colors.RESET}")


def print_progress(message: str):
    """Print a progress message."""
    print(f"{Colors.CYAN}→ {message}{Colors.RESET}")


class ParlantServerManager:
    """
    Manages Parlant server lifecycle for synthetic conversation generation.
    """

    def __init__(self, port: int = 8800, startup_timeout: int = 60):
        self.port = port
        self.startup_timeout = startup_timeout
        self.process: Optional[subprocess.Popen] = None
        self.agent_id: Optional[str] = None
        self.customer_ids: Dict[str, str] = {}

    def start(self) -> bool:
        """Start the Parlant server and wait for readiness."""
        print_info("Starting Parlant server...")

        try:
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
        """Fetch agent and customer IDs from the running server."""
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


class SyntheticConversationPipeline:
    """
    Orchestrates synthetic conversation generation for Parlant.
    """

    def __init__(
        self,
        personas_path: str,
        output_dir: str,
        base_url: str = "http://localhost:8800",
        model_id: str = "claude-3-5-haiku-20241022",  # Default to cost-efficient model
        max_conversation_turns: int = 15,
        timeout: int = 120,
    ):
        self.personas_path = Path(personas_path)
        self.output_dir = Path(output_dir)
        self.base_url = base_url
        self.model_id = model_id
        self.max_conversation_turns = max_conversation_turns
        self.timeout = timeout

        # Create output directory
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Load personas
        self.personas = self._load_personas()
        print_success(f"Loaded {len(self.personas)} financial personas")

        # Create assistant object (Chase Digital Assistant)
        self.assistant = Assistant(
            name="Chase Digital Assistant",
            description="""You're a customer service agent for the Chase bank.

You work directly on the Chase mobile app and help customers with their needs with respect to Chase's offerings, such as credit cards, loans, and other banking services.

When talking about and representing Chase, use "we" and "us" to signify that you're speaking on behalf of the company.

IMPORTANT: Always reply in markdown format with proper paragraph separation.

IMPORTANT: Sometimes a user will provide certain information implicitly, such as saying "that one", while referring to certain details.
In those cases, do your best to infer the information as opposed to tediously asking/seeking confirmation for the specifics explicitly."""
        )

    def _load_personas(self) -> List[Dict]:
        """Load financial personas from YAML file."""
        with open(self.personas_path, 'r') as f:
            data = yaml.safe_load(f)
        return data['users']

    def generate_all_conversations(self, server: ParlantServerManager) -> List[Conversation]:
        """
        Generate conversations for all personas.

        Args:
            server: Running ParlantServerManager instance

        Returns:
            List of generated Conversation objects
        """
        conversations = []

        print_header(f"GENERATING {len(self.personas)} SYNTHETIC CONVERSATIONS")

        for idx, persona_data in enumerate(self.personas, 1):
            print_header(f"Conversation {idx}/{len(self.personas)}: {persona_data['name']}")

            try:
                # Create CharacterCard from persona data
                persona = CharacterCard.from_dict(persona_data)
                print_info(f"Persona: {persona.name} ({persona_data['customer_type']})")
                print_info(f"Scenario: {persona.scenario[:100]}...")

                # Get customer_id based on customer_type
                customer_type = persona_data['customer_type']
                if customer_type not in server.customer_ids:
                    print_error(f"Customer type '{customer_type}' not found in server")
                    continue

                customer_id = server.customer_ids[customer_type]

                # Create ParlantInferenceEndpoint
                endpoint = create_parlant_endpoint(
                    base_url=self.base_url,
                    agent_id=server.agent_id,
                    customer_id=customer_id,
                    timeout=self.timeout,
                )

                # Create Anthropic client
                anthropic_client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

                # Create ConversationGenerator
                generator = ConversationGenerator(
                    model_provider=AnthropicModelProvider(client=anthropic_client),
                    model_id=self.model_id,
                    assistant_endpoint=endpoint,
                    assistant=self.assistant,
                    user_persona=persona,
                    max_conversation_turns=self.max_conversation_turns,
                    conversation_completion_query_model_id="claude-3-5-haiku-20241022",  # Haiku for fast completion checking
                )

                # Generate conversation
                print_progress("Generating conversation...")
                conversation = generator.generate_conversation(
                    conversation_id=f"financial_dispute_{idx}_{persona.name.replace(' ', '_')}"
                )

                # Save individual conversation
                conversation_file = self.output_dir / f"conversation_{idx}_{persona.name.replace(' ', '_')}.json"
                conversation_dict = {
                    "id": conversation.id,
                    "user_id": conversation.user_id,
                    "messages": [
                        {
                            "role": msg.role.name,
                            "content": msg.content,
                            "timestamp": msg.timestamp.isoformat(),
                            "message_id": str(msg.message_id)
                        }
                        for msg in conversation.messages
                    ]
                }
                with open(conversation_file, 'w') as f:
                    json.dump(conversation_dict, f, indent=2)

                print_success(f"Saved conversation to {conversation_file}")
                print_success(f"Generated {len(conversation.messages)} messages")

                conversations.append(conversation)

                # Close session for next conversation
                endpoint.close_session()

            except Exception as e:
                print_error(f"Failed to generate conversation for {persona_data['name']}: {e}")
                import traceback
                traceback.print_exc()
                continue

        return conversations

    def export_to_parlant_format(self, conversations: List[Conversation]):
        """
        Export conversations to Parlant native format.

        This creates sessions.json and events.json files that match
        Parlant's internal data structure.

        Note: This is a simplified export. Full Parlant format would require
        fetching actual session/event data from the API.
        """
        print_header("EXPORTING TO PARLANT NATIVE FORMAT")

        sessions = []
        all_events = []

        for conv in conversations:
            # Create session object
            session = {
                "id": conv.id,
                "agent_id": "chase_digital_assistant",
                "customer_id": conv.user_id,
                "created_at": conv.messages[0].timestamp.isoformat() if conv.messages else datetime.now().isoformat(),
                "updated_at": conv.messages[-1].timestamp.isoformat() if conv.messages else datetime.now().isoformat(),
            }
            sessions.append(session)

            # Create event objects for each message
            for offset, msg in enumerate(conv.messages):
                event = {
                    "session_id": conv.id,
                    "offset": offset,
                    "kind": "message",
                    "source": "customer" if msg.role.name == "user" else "ai_agent",
                    "data": {
                        "message": msg.content
                    },
                    "timestamp": msg.timestamp.isoformat()
                }
                all_events.append(event)

        # Save sessions.json
        sessions_file = self.output_dir / "sessions.json"
        with open(sessions_file, 'w') as f:
            json.dump(sessions, f, indent=2)
        print_success(f"Saved {len(sessions)} sessions to {sessions_file}")

        # Save events.json
        events_file = self.output_dir / "events.json"
        with open(events_file, 'w') as f:
            json.dump(all_events, f, indent=2)
        print_success(f"Saved {len(all_events)} events to {events_file}")

    def generate_summary_report(self, conversations: List[Conversation]):
        """Generate a summary report of all conversations."""
        print_header("GENERATION SUMMARY")

        total_conversations = len(conversations)
        total_messages = sum(len(conv.messages) for conv in conversations)
        avg_messages = total_messages / total_conversations if total_conversations > 0 else 0

        print_success(f"Total conversations generated: {total_conversations}")
        print_success(f"Total messages: {total_messages}")
        print_success(f"Average messages per conversation: {avg_messages:.1f}")

        # Count by customer type
        customer_type_counts = {}
        for conv in conversations:
            # Find matching persona
            for persona_data in self.personas:
                if persona_data['name'] in conv.id:
                    customer_type = persona_data['customer_type']
                    customer_type_counts[customer_type] = customer_type_counts.get(customer_type, 0) + 1
                    break

        print_info("\nConversations by customer type:")
        for customer_type, count in sorted(customer_type_counts.items()):
            print(f"  {customer_type}: {count}")

        # Save summary
        summary_file = self.output_dir / "generation_summary.json"
        summary = {
            "total_conversations": total_conversations,
            "total_messages": total_messages,
            "average_messages_per_conversation": avg_messages,
            "customer_type_distribution": customer_type_counts,
            "generation_timestamp": datetime.now().isoformat(),
            "model_used": self.model_id,
            "max_turns": self.max_conversation_turns,
        }
        with open(summary_file, 'w') as f:
            json.dump(summary, f, indent=2)
        print_success(f"Saved summary report to {summary_file}")


async def main():
    """Main entry point for synthetic conversation generation."""
    load_dotenv()

    print_header("PARLANT SYNTHETIC CONVERSATION GENERATION - PHASE 3")

    # Configuration
    personas_path = "data/conversation_characters/financial_personas.yaml"
    output_dir = "output/synthetic_conversations"

    # Create pipeline
    # Using claude-3-5-haiku-20241022 for cost efficiency
    pipeline = SyntheticConversationPipeline(
        personas_path=personas_path,
        output_dir=output_dir,
        model_id="claude-3-5-haiku-20241022",  # Cost-efficient model
        max_conversation_turns=15,
        timeout=120,
    )

    # Start Parlant server and generate conversations
    try:
        with ParlantServerManager() as server:
            # Generate all conversations
            conversations = pipeline.generate_all_conversations(server)

            # Export to Parlant format
            pipeline.export_to_parlant_format(conversations)

            # Generate summary report
            pipeline.generate_summary_report(conversations)

            print_header("✅ GENERATION COMPLETE!")
            print_success(f"Output saved to {output_dir}/")

    except Exception as e:
        print_error(f"Pipeline failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
