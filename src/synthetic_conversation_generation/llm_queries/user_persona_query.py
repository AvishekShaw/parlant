from dataclasses import asdict
import json
from typing import List, Optional

from synthetic_conversation_generation.data_models.assistant import Assistant
from synthetic_conversation_generation.data_models.character_card import CharacterCard
from synthetic_conversation_generation.llm_queries.llm_query import LLMQuery, ModelProvider

class UserPersonaQuery(LLMQuery):

    def __init__(
        self, 
        model_provider: ModelProvider, 
        model_id: str, 
        assistant: Assistant, 
        previous_personas: List[CharacterCard]
    ):
        super().__init__(model_provider, model_id)
        self.assistant = assistant
        self.previous_personas = previous_personas

    def generate_prompt(self):
        return f"""Create a distinct, realistic, and well-defined user persona that represents someone likely to interact with the AI assistant defined below. You'll later use these personas to drive simulated conversations and evaluate the assistant's performance. Thus, each generated persona should fill a gap left by existing personas.

### Background
These personas will be utilized to generate simulated conversations and evaluate the performance of the AI assistant. Thus, the new persona should be distinct from the previous personas in order to test the assistant's performance across diverse user types, identify potential gaps in the assistant's response capabilities, and ensure comprehensive test coverage across a wide range of potential interactions.

### Target Journeys
The persona MUST have a scenario that aligns with ONE of these specific banking journeys:

1. **Dispute a Transaction**: The user needs to dispute a credit card transaction. Example scenarios include (but are not limited to):
   - Suspect fraud or unauthorized charges
   - Have issues with merchant charges (duplicate, incorrect amount, service not received)
   - Need to navigate the dispute filing process including providing transaction details (date, amount, merchant)
   - May or may not have used the "Report Problem" button in their app
   - Other dispute-related scenarios

2. **Lock a Card**: The user needs to lock their credit/debit card. Example scenarios include (but are not limited to):
   - Card is lost or stolen
   - Temporary security precaution (traveling, suspicious activity)
   - Misplaced card temporarily
   - May need card replacement afterward
   - Other card locking scenarios

3. **Replace a Card**: The user needs to replace a damaged, lost, stolen, or expired card. Example scenarios include (but are not limited to):
   - Have a lost or stolen card requiring immediate deactivation
   - Have a damaged/worn card that's hard to use
   - Have an expired or expiring card
   - Need to confirm delivery address and select delivery speed
   - Have questions about the replacement process
   - Other card replacement scenarios

### Instructions
1. Review the assistant definition, target journeys, and previous user personas.
2. Invent a new persona (name, background, personality, goals, motivations, communication style, etc.) that is likely to seek out the defined assistant.
3. **CRITICAL**: The persona's scenario MUST align with ONE of the three target journeys above. Be specific about which journey and the circumstances (e.g., "John lost his Chase Sapphire card while traveling and needs to lock it immediately and order a replacement").
4. Develop the persona based on filling gaps in the existing persona collection - vary demographics, personality types, technical proficiency, urgency levels, and communication styles.
5. Ensure diversity across:
   - Age groups (students, working professionals, retirees)
   - Technical comfort (tech-savvy vs. needs hand-holding)
   - Emotional states (calm/rational vs. anxious/frustrated vs. rushed)
   - Journey types (distribute across all three journeys)
   - Specific circumstances within each journey

### Assistant Definition
{json.dumps(asdict(self.assistant), indent=4)}

### Previous User Personas
{json.dumps([asdict(persona) for persona in self.previous_personas], indent=4)}
"""
    
    def response_schema(self):
        properties = {
            "name": {
                "type": "string",
                "description": "The user's name"
            },
            "description": {
                "type": "string",
                "description": "An overview of the user's physical and mental traits."
            },
            "personality": {
                "type": "string",
                "description": "A description of the user's personality."
            },
            "scenario": {
                "type": "string",
                "description": "The context and circumstances for why the user is interacting with the assistant."      
            },
            "summary": {
                "type": "string",
                "description": "A concise (~10 words) summary of the user, with the main focus on the user's personality, scenario, and description."
            }
        }

        return {
            "type": "object",
            "properties": properties,
            "required": ["name", "description", "personality", "scenario", "summary"],
            "additionalProperties": False
        }
    
    def parse_response(self, json_response) -> CharacterCard:   
        return CharacterCard(
            name=json_response["name"],
            description=json_response["description"],
            personality=json_response["personality"],
            scenario=json_response["scenario"],
            summary=json_response["summary"]
        )
