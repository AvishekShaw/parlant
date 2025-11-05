
from dataclasses import asdict
from datetime import datetime
import json

from synthetic_conversation_generation.data_models.assistant import Assistant
from synthetic_conversation_generation.data_models.conversation import Conversation, Message, ROLE
from synthetic_conversation_generation.data_models.character_card import CharacterCard
from synthetic_conversation_generation.llm_queries.llm_query import LLMQuery, ModelProvider

class UserMessageQuery(LLMQuery):

    def __init__(self, model_provider: ModelProvider, model_id: str, conversation: Conversation, user_persona: CharacterCard, assistant: Assistant):
        super().__init__(model_provider, model_id)
        self.conversation = conversation
        self.user_persona = user_persona
        self.assistant = assistant
        
    def generate_prompt(self):
        return f"""Generate a realistic, SHORT user message (1-3 sentences max, ~50 words) in casual chat style.

### CRITICAL CONSTRAINTS:
- **Maximum length**: 1-3 sentences or ~50 words max (strictly enforce this!)
- **Chat style**: Write like texting/chatting, NOT like email or formal writing
- **One topic per message**: Don't combine multiple questions or requests
- **Casual tone**: Use contractions, informal language, occasional abbreviations
- **Natural imperfections**: Include 1-2 typos, missing punctuation, or lowercase starts

### BAD EXAMPLES (Too verbose - NEVER do this):
❌ "Hi there, I'm Walter Jenkins. I'm brand-new to the Chase app and I could use some hand-holding. I want to do three things, but I get overwhelmed with tech, so maybe we can go one at a time: 1) Set up my Social Security direct deposit into my Chase checking. 2) Enroll in automatic bill pay..."
❌ "Thanks, this helps. Let's do the Social Security part now. I'm on my checking screen and I see my balance and recent transactions. I don't see 'Account details,' though—I do see buttons for 'Pay & transfer,' 'Deposit,' 'More,' and there's a little gear icon. Which one should I tap from here?"

### GOOD EXAMPLES (Chat-like - DO this):
✅ "hey i need help setting up direct deposit for my social security"
✅ "im on the checking screen but dont see account details?"
✅ "ok tapped More. which button do i tap next?"
✅ "wait where do i find the routing number"
✅ "can u help me send money to my grandson"

### RULES FOR REALISTIC CHAT MESSAGES:
1. **Break up long requests**: If user has multiple needs, this message should only ask about ONE thing
2. **Ask directly**: Skip long introductions and background context
3. **Natural flow**: Respond to what assistant just said, don't repeat everything
4. **Imperfect typing**: Include typos (1-3%), missing apostrophes (don't, cant, im), lowercase starts
5. **Abbreviations**: Use "im", "dont", "cant", "u", "ur", "rn", "pls", "thx" when appropriate
6. **Real chat patterns**:
   - Start with "hey", "hi", or jump right to question
   - Use "?" for questions (but not always)
   - Use "ok" or "alright" to acknowledge
   - Express confusion: "wait", "confused", "not sure"
   - Show frustration: "ugh", "this isnt working"

### PERSONA-SPECIFIC PATTERNS:

**For elderly/less tech-savvy users:**
- Shorter sentences but still polite
- Some typos from unfamiliarity
- Questions show uncertainty: "do i tap this?", "where do i find?"
- May over-explain slightly but STILL keep under 3 sentences
- Example: "ok i tapped More like you said. which one do i tap next?"

**For busy/urgent users:**
- Very short: 1 sentence only
- Abbreviations: "acct", "asap", "rn"
- Incomplete sentences: "checking screen. dont see account details"
- All lowercase or ALL CAPS if stressed
- Example: "card declined help" or "NEED TO CHECK BALANCE ASAP"

**For casual/young users:**
- Heavy abbreviations: "u", "ur", "rn", "ngl", "tbh"
- No capitalization
- Lots of "like", "yeah", "ok"
- Example: "yo can u check my balance rn"

### MESSAGE LENGTH EXAMPLES (FOLLOW THESE):
- **1 sentence**: "how do i check my balance"
- **2 sentences**: "hey im trying to set up direct deposit. where do i find my routing number"
- **3 sentences MAX**: "i tapped More like you said. i see Account Services and Direct Deposit Info. which one?"

### CRITICAL: NEVER generate messages longer than 3 sentences or 50 words unless the user persona specifically requires technical detail. If the user has multiple things to ask about, only include ONE in this message.

### User Definition
{json.dumps(asdict(self.user_persona), indent=4)}

### Assistant Definition
{json.dumps(asdict(self.assistant), indent=4)}

### Conversation History
{json.dumps(self.conversation.prompt_format, indent=4)}
"""

    def response_schema(self):
        properties = {}
        properties["user_message"] = {
            "type": "string",
            "description": "The user's next message in the conversation"
        }

        return {
            "type": "object",
            "properties": properties,
            "required": ["user_message"],
            "additionalProperties": False
        }
    
    def parse_response(self, json_response) -> Message:   
        return Message(
            message_id=len(self.conversation.messages),
            role=ROLE.user,
            content=json_response["user_message"],
            timestamp=datetime.now()
        )
