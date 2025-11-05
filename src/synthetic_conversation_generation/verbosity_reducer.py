"""
Verbosity Reducer - Post-process generated messages to reduce verbose patterns
"""

import re
import logging
from typing import Optional

logger = logging.getLogger(__name__)


class VerbosityReducer:
    """Remove overly verbose patterns from generated text to make messages more chat-like"""

    def __init__(self):
        pass

    def reduce_user_verbosity(self, text: str, max_words: int = 75) -> str:
        """
        Make user messages more chat-like by removing verbose patterns.

        Args:
            text: The user message to process
            max_words: Maximum word count (default 75, ~3 sentences)

        Returns:
            Cleaned up message text
        """
        original_text = text

        # 1. Remove formal introductions
        text = re.sub(r'^Hi there,?\s+I\'m [A-Za-z\s]+\.\s*', 'hey ', text, flags=re.IGNORECASE)
        text = re.sub(r'^Hello,?\s+my name is [A-Za-z\s]+\.\s*', 'hi ', text, flags=re.IGNORECASE)
        text = re.sub(r'^Greetings,?\s+', 'hi ', text, flags=re.IGNORECASE)

        # 2. Remove meta-commentary about message length
        text = re.sub(r'Sorry for the long message[,\.]?\s*', '', text, flags=re.IGNORECASE)
        text = re.sub(r'I know this is a lot[,\.]?\s*', '', text, flags=re.IGNORECASE)
        text = re.sub(r'Bear with me[,\.]?\s*', '', text, flags=re.IGNORECASE)

        # 3. Simplify overly polite/formal phrases
        text = text.replace("I would appreciate it if you could", "can you")
        text = text.replace("I would be grateful if", "can you")
        text = text.replace("I was wondering if you could", "can you")
        text = text.replace("I was wondering if", "can")
        text = text.replace("Could you please", "can you")
        text = text.replace("Would you mind", "can you")
        text = text.replace("I could use some hand-holding", "need help")
        text = text.replace("I could really use some help", "need help")
        text = text.replace("I would like to", "want to")
        text = text.replace("I need to", "i need to")

        # 4. Remove numbered list markers (1), 2), etc.)
        # Convert numbered lists to separate concerns
        if re.search(r'\n\d+[\.\)]\s+', text):
            logger.warning("User message contains numbered list - should be split into multiple messages")
            # Remove the numbers but keep the content
            text = re.sub(r'\n\d+[\.\)]\s+', '. ', text)

        # 5. Remove excessive background/context setting
        text = re.sub(r"A few things about me:.*?(?=\n\n|\Z)", "", text, flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r"Some context:.*?(?=\n\n|\Z)", "", text, flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r"For context:.*?(?=\n\n|\Z)", "", text, flags=re.DOTALL | re.IGNORECASE)

        # 6. Check word count and warn if too long
        word_count = len(text.split())
        if word_count > max_words:
            logger.warning(f"User message still too long after cleanup ({word_count} words). Original: {len(original_text.split())} words")
            # Truncate to first 2-3 sentences
            sentences = re.split(r'[.!?]+', text)
            text = '. '.join(sentences[:3]).strip()
            if text and not text.endswith(('.', '!', '?')):
                text += '?'  # Add question mark if it seems like a question

        # 7. Clean up extra whitespace
        text = re.sub(r'\n\n+', '\n\n', text)  # Max 2 newlines
        text = re.sub(r'  +', ' ', text)  # No double spaces
        text = text.strip()

        return text

    def reduce_assistant_verbosity(self, text: str, max_words: int = 120) -> str:
        """
        Make assistant messages more chat-like by removing verbose patterns.
        Aligns with Parlant ARQ agent style: concise, human-like, avoid overly polite language.

        Args:
            text: The assistant message to process
            max_words: Maximum word count (default 120, ~3-5 sentences)

        Returns:
            Cleaned up message text
        """
        original_text = text

        # 1. Remove markdown headers
        text = re.sub(r'###\s+', '', text)
        text = re.sub(r'##\s+', '', text)
        text = re.sub(r'#\s+', '', text)

        # 2. Remove bold markdown
        text = re.sub(r'\*\*([^*]+)\*\*', r'\1', text)

        # 3. Remove italic markdown
        text = re.sub(r'\*([^*]+)\*', r'\1', text)

        # 4. Simplify numbered lists to simple line breaks
        # "1. **Step one**: Do this" → "Do this"
        text = re.sub(r'\d+\.\s+\*\*[^*:]+\*\*:\s+', '', text)
        text = re.sub(r'\d+\.\s+\*\*[^*]+\*\*\s+', '', text)
        text = re.sub(r'\d+[\.\)]\s+', '', text)

        # 5. Remove bullet points
        text = re.sub(r'\n\s*[-•]\s+', '\n', text)

        # 6. Remove overly empathetic/verbose openings (Parlant principle: avoid being overly polite)
        text = re.sub(r'^I understand that [^.!?]+[.!?]\s*', '', text, flags=re.IGNORECASE)
        text = re.sub(r"^I'm sorry you're experiencing [^.!?]+[.!?]\s*", '', text, flags=re.IGNORECASE)
        text = re.sub(r"^I'm sorry to hear [^.!?]+[.!?]\s*", '', text, flags=re.IGNORECASE)
        text = re.sub(r"^I apologize for [^.!?]+[.!?]\s*", '', text, flags=re.IGNORECASE)
        text = re.sub(r"^Don't worry[,—]\s*", '', text, flags=re.IGNORECASE)
        text = re.sub(r'^Thank you for (your )?patience[.!,]\s*', '', text, flags=re.IGNORECASE)
        text = re.sub(r"^I appreciate (your )?patience[.!,]\s*", '', text, flags=re.IGNORECASE)

        # 7. Remove overly structured section headers
        text = re.sub(r'\n\n[A-Z][^:\n]{1,50}:\n', '\n\n', text)

        # 8. Simplify overly formal language (Parlant principle: be concise, human-like)
        text = text.replace("I'd be happy to help you with", "I can help with")
        text = text.replace("I'd be glad to assist you with", "I can help with")
        text = text.replace("I'll be happy to help you with", "I can help with")
        text = text.replace("I'll be happy to help", "I can help")
        text = text.replace("Let me assist you with", "Let me help with")
        text = text.replace("I would be happy to", "I can")
        text = text.replace("I would be glad to", "I can")
        text = text.replace("Absolutely! I'd be happy to", "Sure! I can")
        text = text.replace("Absolutely! I can certainly", "Sure! I can")
        text = text.replace("I can certainly help", "I can help")
        text = text.replace("I'd love to help", "I can help")

        # 9. Remove verbose transition phrases
        text = re.sub(r"Let me help you with that\.\s*", "", text, flags=re.IGNORECASE)
        text = re.sub(r"Let me take care of that for you\.\s*", "", text, flags=re.IGNORECASE)
        text = re.sub(r"I'm here to help\.\s*", "", text, flags=re.IGNORECASE)

        # 10. Simplify overly elaborate explanations
        text = text.replace("In order to", "To")
        text = text.replace("in order to", "to")
        text = text.replace("For the purpose of", "To")
        text = text.replace("for the purpose of", "to")

        # 11. Remove premature "anything else?" - Parlant principle: Resolution-aware message ending
        # Only remove if it appears to be premature (detected by short message or mid-conversation)
        if len(text.split()) < 80:  # Short message likely mid-conversation
            text = re.sub(r'\s*Is there anything else I can (help|assist) (you with|with)\??\s*$', '', text, flags=re.IGNORECASE)
            text = re.sub(r'\s*Can I help (you )?with anything else\??\s*$', '', text, flags=re.IGNORECASE)
            text = re.sub(r'\s*Anything else I can do for you\??\s*$', '', text, flags=re.IGNORECASE)

        # 12. Check word count and truncate if needed
        word_count = len(text.split())
        if word_count > max_words:
            logger.warning(f"Assistant message too long after cleanup ({word_count} words). Original: {len(original_text.split())} words")
            # Keep first ~120 words (roughly 3-5 sentences)
            words = text.split()
            text = ' '.join(words[:max_words])
            # Try to end at a sentence boundary
            last_period = text.rfind('.')
            last_question = text.rfind('?')
            last_exclaim = text.rfind('!')
            last_punct = max(last_period, last_question, last_exclaim)
            if last_punct > max_words * 0.7:  # If we're at least 70% through
                text = text[:last_punct + 1]

        # 13. Clean up extra whitespace
        text = re.sub(r'\n\n\n+', '\n\n', text)  # Max 2 newlines
        text = re.sub(r'  +', ' ', text)  # No double spaces
        text = text.strip()

        return text

    def check_message_quality(self, text: str, role: str = "user") -> dict:
        """
        Check quality metrics for a message.

        Args:
            text: Message text
            role: "user" or "assistant"

        Returns:
            Dictionary with quality metrics and warnings
        """
        word_count = len(text.split())
        sentence_count = len([s for s in re.split(r'[.!?]+', text) if s.strip()])
        has_markdown_headers = bool(re.search(r'###?\s+', text))
        has_numbered_list = bool(re.search(r'\n\d+[\.\)]\s+', text))
        has_bold = bool(re.search(r'\*\*[^*]+\*\*', text))

        warnings = []

        if role == "user":
            if word_count > 75:
                warnings.append(f"Too long: {word_count} words (target: <75)")
            if sentence_count > 4:
                warnings.append(f"Too many sentences: {sentence_count} (target: 1-3)")
            if has_numbered_list:
                warnings.append("Contains numbered list (should split into multiple messages)")
        else:  # assistant
            if word_count > 120:
                warnings.append(f"Too long: {word_count} words (target: <120, aligns with Parlant ARQ style)")
            if sentence_count > 6:
                warnings.append(f"Too many sentences: {sentence_count} (target: 3-5 sentences)")
            if has_markdown_headers:
                warnings.append("Contains markdown headers (should use plain text)")
            if has_numbered_list:
                warnings.append("Contains numbered list (should use simple line breaks)")
            if has_bold:
                warnings.append("Contains bold markdown (should use plain text)")

        return {
            "word_count": word_count,
            "sentence_count": sentence_count,
            "has_markdown_headers": has_markdown_headers,
            "has_numbered_list": has_numbered_list,
            "has_bold": has_bold,
            "warnings": warnings,
            "is_acceptable": len(warnings) == 0
        }
