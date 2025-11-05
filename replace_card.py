import parlant.sdk as p
from textwrap import dedent

from tools import get_user_address, list_user_cards, process_card_replacement


async def create_journey(server: p.Server, agent: p.Agent) -> p.Journey:
    journey = await agent.create_journey(
        title="Replace a Card",
        description=dedent("""\
            Help the user replace a damaged, lost, stolen, or expired card with delivery options based on their customer type.
            """),
        conditions=[
            "The customer wants to replace a card",
        ],
    )

    t1 = await journey.initial_state.transition_to(
        tool_state=list_user_cards,
    )

    # State t2: Determine which card needs replacement
    t2 = await t1.target.transition_to(
        chat_state="Determine which card needs replacement",
        canned_responses=[
            await server.create_canned_response(
                template="{% if cards|length == 1 %}Just to confirm, you want to replace your {{ cards[0] }} card, right?{% else %}I see you have the following cards: {% for card in cards %}{{ card }}{% if not loop.last %}, {% endif %}{% endfor %}. Which one of these do you need to replace?{% endif %}",
                signals=[
                    "You have just one card: [CARD NAME]. Do you want to replace it?",
                    "Here are your cards: Chase Freedom, Chase Sapphire. Which card needs to be replaced?",
                    "Here are your cards: Wells Fargo Platinum. Which card needs to be replaced?",
                    "Here are your cards: Bank of America Cash Rewards, Capital One Venture. Which card needs to be replaced?",
                ],
            ),
            await server.create_canned_response(
                template="Can you please confirm that you want to replace your {{generative.card_name}} card",
                signals=[
                    "Just to confirm, you want to replace your Chase Freedom card",
                    "Just to confirm, you want to replace your Wells Fargo Platinum card",
                ],
            ),
        ],
    )

    # State t3: Card not found - apologize and transfer
    t3 = await t2.target.transition_to(
        condition="User says that the required card is not in list",
        chat_state="Apologize and say you'll connect them with a human agent, and say goodbye",
        canned_responses=[
            await server.create_canned_response(
                template="I apologize, but I cannot find that card in your account. Let me connect you with a human agent who can assist you further.",
            ),
            await server.create_canned_response(
                template="Let me connect you with a human agent who can provide additional assistance with your card replacement request.",
            ),
        ],
    )

    await t3.target.transition_to(state=p.END_JOURNEY)

    # State t4: Ask replacement reason
    t4 = await t2.target.transition_to(
        condition="User selects a valid card",
        chat_state="Ask why they need the card replaced (lost, stolen, damaged, expired)",
        canned_responses=[
            await server.create_canned_response(
                template="Why do you need your {{generative.card_name}} card replaced?",
                signals=[
                    "Why do you need your Chase Freedom card replaced?",
                    "Why do you need your Wells Fargo Platinum card replaced?",
                    "Why do you need your Bank of America Cash Rewards card replaced?",
                ],
            ),
        ],
    )

    # State t5: Get user address for lost/stolen cards
    t5 = await t4.target.transition_to(
        condition="Card is lost or stolen", tool_state=get_user_address
    )

    # State t6: Confirm deactivation and address for lost/stolen cards
    t6 = await t5.target.transition_to(
        chat_state="Confirm the card will be immediately deactivated to prevent unauthorized use and ask them to confirm the address for the new card",
        canned_responses=[
            await server.create_canned_response(
                template="I understand your {{generative.card_name}} card is {{generative.reason}}. For your security, I'm immediately deactivating this card to prevent any unauthorized use. Can you please confirm your delivery address {{generative.address}}?",
                signals=[
                    "I understand your Chase Freedom card is lost. For your security, I'm immediately deactivating this card to prevent any unauthorized use. Can you please confirm your delivery address",
                    "I understand your Wells Fargo Platinum card is stolen. For your security, I'm immediately deactivating this card to prevent any unauthorized use. Can you please confirm your delivery address",
                ],
            ),
            await server.create_canned_response(
                template="I have your address on file as: {{generative.address}}. Is this correct, or would you like to use a different address?",
                signals=[
                    "I have your address on file as: 123 Main Street, New York, NY 10001. Is this correct, or would you like to use a different address?",
                    "I have your address on file as: 456 Oak Avenue, Los Angeles, CA 90210. Is this correct, or would you like to use a different address?",
                ],
            ),
            await server.create_canned_response(
                template="Please provide the address where you'd like your new card delivered.",
            ),
        ],
    )

    # State t7: Handle expired cards
    t7 = await t4.target.transition_to(
        condition="Card is expired or about to expire",
        chat_state="Inform them that replacement cards for expired cards are sent automatically and provide timeline information",
        canned_responses=[
            await server.create_canned_response(
                template="I see your {{generative.card_name}} card is {{generative.reason}}. Good news! We automatically send replacement cards for expired or expiring cards. Your new card should arrive approximately 7-10 days before your current card expires. If you haven't received it yet, it may be on its way. You can continue using your current card until the expiration date.",
                signals=[
                    "I see your Chase Freedom card is expired. Good news! We automatically send replacement cards for expired or expiring cards. Your new card should arrive approximately 7-10 days before your current card expires. If you haven't received it yet, it may be on its way. You can continue using your current card until the expiration date.",
                    "I see your Wells Fargo Platinum card is about to expire. Good news! We automatically send replacement cards for expired or expiring cards. Your new card should arrive approximately 7-10 days before your current card expires. If you haven't received it yet, it may be on its way. You can continue using your current card until the expiration date.",
                ],
            ),
        ],
    )

    await t7.target.transition_to(state=p.END_JOURNEY)

    # State t8: Handle other reasons - direct to customer care
    t8 = await t4.target.transition_to(
        condition="Another reason",
        chat_state="Tell them to contact customer care at 123456789 for further assistance",
        canned_responses=[
            await server.create_canned_response(
                template="I understand you need to replace your {{generative.card_name}} card due to {{generative.reason}}. For this type of request, I'll need to connect you with our customer care team at 123456789. They'll be able to assist you with the specific requirements for your situation.",
                signals=[
                    "I understand you need to replace your Chase Freedom card due to damage. For this type of request, I'll need to connect you with our customer care team at 123456789. They'll be able to assist you with the specific requirements for your situation.",
                    "I understand you need to replace your Wells Fargo Platinum card due to wear and tear. For this type of request, I'll need to connect you with our customer care team at 123456789. They'll be able to assist you with the specific requirements for your situation.",
                ],
            ),
        ],
    )

    await t8.target.transition_to(state=p.END_JOURNEY)

    # State t10: Order Summary and delivery options
    t10 = await t6.target.transition_to(
        chat_state="Show complete order summary including card type and delivery address, then ask for final confirmation",
        canned_responses=[
            await server.create_canned_response(
                template="Now for delivery options. As a {{generative.customer_type}} customer: Standard delivery (5-7 business days) is free. Express delivery (2-3 business days) {{generative.express_fee}}. Which would you prefer?",
                signals=[
                    "Now for delivery options. As a Premium customer: Standard delivery (5-7 business days) is free. Express delivery (2-3 business days) is also free as a premium benefit. Which would you prefer?",
                    "Now for delivery options. As a Standard customer: Standard delivery (5-7 business days) is free. Express delivery (2-3 business days) costs $15. Which would you prefer?",
                ],
            ),
            await server.create_canned_response(
                template="Perfect! Let me summarize your card replacement order:\n- Card: {{generative.card_name}}\n- Reason: {{generative.reason}}\n- Delivery Address: {{generative.address}}\n- Delivery Speed: {{generative.delivery_speed}}\n- Cost: {{generative.cost}}\n\nIs this information correct?",
                signals=[
                    "Perfect! Let me summarize your card replacement order:\n- Card: Chase Freedom\n- Reason: Lost\n- Delivery Address: 123 Main Street, New York, NY 10001\n- Delivery Speed: Express (2-3 business days)\n- Cost: Free (Premium benefit)\n\nIs this information correct?",
                    "Perfect! Let me summarize your card replacement order:\n- Card: Wells Fargo Platinum\n- Reason: Damaged\n- Delivery Address: 456 Oak Avenue, Los Angeles, CA 90210\n- Delivery Speed: Standard (5-7 business days)\n- Cost: Free\n\nIs this information correct?",
                ],
            ),
        ],
    )

    # State t11: Process Card Replacement (tool state)
    t11 = await t10.target.transition_to(
        tool_state=process_card_replacement,
    )

    # State t12: Final confirmation and instructions
    t12 = await t11.target.transition_to(
        chat_state="Process the card replacement and provide confirmation with reference number, expected delivery date, and instructions for destroying the old card",
        canned_responses=[
            await server.create_canned_response(
                template="Your card replacement has been successfully processed! Here are your details:\n- Reference Number: {{generative.reference_id}}\n- Expected Delivery: {{generative.delivery_date}}\n- Tracking will be available within 24 hours\n\nImportant: Your current card {{generative.deactivation_info}}. Please destroy it by cutting through the chip and magnetic stripe once your new card arrives.",
                signals=[
                    "Your card replacement has been successfully processed! Here are your details:\n- Reference Number: CR_12345\n- Expected Delivery: August 5, 2025\n- Tracking will be available within 24 hours\n\nImportant: Your current card has been immediately deactivated due to security concerns. Please destroy it by cutting through the chip and magnetic stripe once your new card arrives.",
                    "Your card replacement has been successfully processed! Here are your details:\n- Reference Number: CR_67890\n- Expected Delivery: August 2, 2025\n- Tracking will be available within 24 hours\n\nImportant: Your current card will be deactivated when you activate your new card. Please destroy it by cutting through the chip and magnetic stripe once your new card arrives.",
                ],
            ),
            await server.create_canned_response(
                template="Is there anything else I can help you with regarding your card replacement?",
            ),
            await server.create_canned_response(
                template="Your new card will have the same features as your current card. You'll need to update any saved payment methods and re-add the card to your digital wallets once your new card arrives.",
            ),
            await server.create_canned_response(
                template="I'm sorry, there was an issue processing your card replacement. Please try again later or contact customer service at 1-800-BANK-HELP for immediate assistance.",
            ),
        ],
    )

    _ = t12

    # Journey-level guidelines with their associated canned responses
    await journey.create_guideline(
        condition="the customer wants to know if the replacement card would have a different number",
        action="inform them that the replacement card will have a different number to ensure security",
    )

    await journey.create_guideline(
        condition="the customer asks if someone else can receive the card on their behalf",
        action="explain that cards must be delivered to the cardholder's verified address and may require signature confirmation",
    )

    await journey.create_guideline(
        condition="the customer asks about international delivery or they're traveling",
        action="inform them that cards can only be delivered to domestic addresses on file, and suggest they update their address or wait until they return",
    )

    await journey.create_guideline(
        condition="the customer asks what happens if they find their lost card after ordering a replacement",
        action="explain that the old card will be permanently deactivated and they should destroy it even if found, as the new card is already being processed",
    )

    # Journey-level canned responses for guidelines and general use
    journey_level_templates = [
        {
            "template": "Yes, your replacement {{generative.card_name}} card will have a different card number for security purposes. This helps protect you from any potential fraud on your current card number.",
            "signals": [
                "Yes, your replacement Chase Freedom card will have a different card number for security purposes. This helps protect you from any potential fraud on your current card number.",
                "Yes, your replacement Wells Fargo Platinum card will have a different card number for security purposes. This helps protect you from any potential fraud on your current card number.",
            ],
        },
        {
            "template": "For security reasons, your new card must be delivered to your verified address on file and may require signature confirmation. Only you, the cardholder, should receive and sign for the card.",
        },
        {
            "template": "I understand you're traveling. Unfortunately, we can only deliver replacement cards to domestic addresses that are verified on your account. You can either update your address if you have a domestic location, or wait until you return to receive your card. Would you like me to help you explore these options?",
        },
        {
            "template": "If you find your lost {{generative.card_name}} card after we process your replacement, you should still destroy the old card by cutting through the chip and magnetic stripe. The old card has been permanently deactivated for your security, and your new card with a different number is already being processed.",
            "signals": [
                "If you find your lost Chase Freedom card after we process your replacement, you should still destroy the old card by cutting through the chip and magnetic stripe. The old card has been permanently deactivated for your security, and your new card with a different number is already being processed.",
                "If you find your lost Wells Fargo Platinum card after we process your replacement, you should still destroy the old card by cutting through the chip and magnetic stripe. The old card has been permanently deactivated for your security, and your new card with a different number is already being processed.",
            ],
        },
        {
            "template": "For your security, I need to verify some information before we proceed with the card replacement.",
        },
        {
            "template": "I'll help you replace your {{generative.card_name}} card. Let me confirm your delivery address {{generative.address}}.",
            "signals": [
                "I'll help you replace your Chase Freedom card. Let me confirm your delivery address.",
                "I'll help you replace your Wells Fargo Platinum card. Let me confirm your delivery address.",
            ],
        },
    ]

    for item in journey_level_templates:
        await journey.create_canned_response(
            template=item["template"],
            signals=item.get("signals", []),
        )

    return journey
