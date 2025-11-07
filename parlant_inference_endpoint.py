"""
Parlant API adapter for synthetic conversation generation.

This module provides a bridge between the generic conversation generator
and the Parlant API, allowing LLM-simulated users to interact with
Parlant agents through REST endpoints.
"""

import time
import requests
from datetime import datetime
from typing import Dict, Any, Optional
from dataclasses import dataclass

# Import from synthetic conversation generation
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent / "src"))
from synthetic_conversation_generation.data_models.conversation import Conversation, Message, ROLE


class ParlantAPIError(Exception):
    """Raised when Parlant API returns an error."""
    pass


class ParlantTimeoutError(Exception):
    """Raised when polling for response times out."""
    pass


@dataclass
class ParlantInferenceEndpoint:
    """
    Adapter for Parlant API that manages stateful conversations.

    This class implements the same interface as InferenceEndpoint but works
    with Parlant's session-based API. Each instance manages one conversation
    (session) with multiple turns.

    Design Notes:
    - Session lifecycle = Conversation lifecycle
    - Session created on first message, reused for subsequent turns
    - Supports dispute_transaction journey (extensible to lock_card, replace_card)
    """

    base_url: str
    agent_id: str
    customer_id: str
    timeout: int = 120  # Polling timeout in seconds (agent may need time for retries)
    poll_interval: float = 2.0  # Poll every 2 seconds

    # Session state (managed internally)
    session_id: Optional[str] = None
    last_event_offset: int = -1

    def get_assistant_message(
        self,
        conversation: Conversation,
        system_prompt: Optional[str] = None
    ) -> Message:
        """
        Send customer message and wait for agent response.

        This is the main interface method called by ConversationGenerator.

        Args:
            conversation: Current conversation history
            system_prompt: Ignored (agent description set at agent creation)

        Returns:
            Message object with agent's response

        Raises:
            ParlantAPIError: If API request fails
            ParlantTimeoutError: If polling times out
        """
        # Ensure session exists (create on first call)
        if self.session_id is None:
            self._create_session()

        # Get the last customer message (most recent in conversation)
        if not conversation.messages:
            raise ValueError("Conversation has no messages")

        last_message = conversation.messages[-1]
        # Check if last message is from user (handle both enum and string comparison)
        if hasattr(last_message.role, 'name'):
            is_user_message = last_message.role.name == 'user'
        else:
            is_user_message = str(last_message.role).lower() == 'user'

        if not is_user_message:
            raise ValueError(f"Last message must be from user, got: {last_message.role}")

        # Send customer message to Parlant
        event_offset = self._send_customer_message(last_message.content)

        # Poll for agent response
        agent_message_content = self._poll_for_agent_response(after_offset=event_offset)

        # Create and return Message object
        return Message(
            role=ROLE.assistant,
            content=agent_message_content,
            timestamp=datetime.now(),
            message_id=len(conversation.messages)
        )

    def _create_session(self) -> None:
        """
        Create a new Parlant session.

        Sets self.session_id and initializes event offset tracking.

        Raises:
            ParlantAPIError: If session creation fails
        """
        url = f"{self.base_url}/sessions"
        payload = {
            "agent_id": self.agent_id,
            "customer_id": self.customer_id,
            "mode": "auto"  # Auto-respond mode
        }

        try:
            response = requests.post(url, json=payload, timeout=60)  # Increased from 30s
            response.raise_for_status()
            session_data = response.json()
            self.session_id = session_data["id"]
            self.last_event_offset = -1

        except requests.exceptions.RequestException as e:
            raise ParlantAPIError(f"Failed to create session: {e}")

    def _send_customer_message(self, content: str) -> int:
        """
        Send a customer message event to the session.

        Args:
            content: Message content from the customer

        Returns:
            Event offset of the created event

        Raises:
            ParlantAPIError: If message sending fails
        """
        if not self.session_id:
            raise ValueError("Session not created yet")

        url = f"{self.base_url}/sessions/{self.session_id}/events"
        payload = {
            "source": "customer",
            "kind": "message",
            "message": content  # Message content as string, not nested object
        }

        try:
            response = requests.post(url, json=payload, timeout=60)  # Increased from 30s
            response.raise_for_status()
            event_data = response.json()
            return event_data["offset"]

        except requests.exceptions.RequestException as e:
            raise ParlantAPIError(f"Failed to send customer message: {e}")

    def _poll_for_agent_response(self, after_offset: int) -> str:
        """
        Poll for agent response events.

        Continuously polls the events endpoint until:
        1. An AI agent message is found, OR
        2. Timeout is reached

        Args:
            after_offset: Only fetch events after this offset

        Returns:
            Agent's message content

        Raises:
            ParlantTimeoutError: If no response within timeout
            ParlantAPIError: If API request fails
        """
        if not self.session_id:
            raise ValueError("Session not created yet")

        start_time = time.time()
        current_offset = after_offset

        while True:
            # Check timeout
            elapsed = time.time() - start_time
            if elapsed > self.timeout:
                raise ParlantTimeoutError(
                    f"No agent response received within {self.timeout} seconds"
                )

            # Fetch events after current offset
            url = f"{self.base_url}/sessions/{self.session_id}/events"
            params = {"offset": current_offset + 1}

            try:
                response = requests.get(url, params=params, timeout=10)
                response.raise_for_status()
                events = response.json()

            except requests.exceptions.RequestException as e:
                raise ParlantAPIError(f"Failed to fetch events: {e}")

            # Process events
            for event in events:
                # Update offset tracking
                if event["offset"] > self.last_event_offset:
                    self.last_event_offset = event["offset"]
                    current_offset = event["offset"]

                # Look for AI agent message
                if (event.get("kind") == "message" and
                    event.get("source") == "ai_agent"):

                    # Message content can be in data.message (as string) or data.message.content
                    message_data = event.get("data", {}).get("message")
                    if isinstance(message_data, str):
                        return message_data
                    elif isinstance(message_data, dict):
                        message_content = message_data.get("content")
                        if message_content:
                            return message_content

            # No message found yet, wait before next poll
            time.sleep(self.poll_interval)

    def close_session(self) -> None:
        """
        Close the current session (optional cleanup).

        Note: Parlant sessions don't need explicit closing, but this method
        is provided for future extensibility and resource cleanup.
        """
        self.session_id = None
        self.last_event_offset = -1


# Factory function for easy instantiation
def create_parlant_endpoint(
    base_url: str = "http://localhost:8800",
    agent_id: str = None,
    customer_id: str = None,
    timeout: int = 120,
) -> ParlantInferenceEndpoint:
    """
    Create a ParlantInferenceEndpoint with common defaults.

    Args:
        base_url: Parlant server URL (default: localhost:8800)
        agent_id: Agent ID to use for conversations
        customer_id: Customer ID to use for conversations
        timeout: Polling timeout in seconds

    Returns:
        Configured ParlantInferenceEndpoint instance
    """
    if not agent_id or not customer_id:
        raise ValueError("agent_id and customer_id are required")

    return ParlantInferenceEndpoint(
        base_url=base_url,
        agent_id=agent_id,
        customer_id=customer_id,
        timeout=timeout,
    )
