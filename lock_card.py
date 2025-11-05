from textwrap import dedent
import parlant.sdk as p

from tools import list_user_cards, lock_card


async def create_journey(server: p.Server, agent: p.Agent) -> p.Journey:
    journey = await agent.create_journey(
        title="Lock a Card",
        description=dedent("""\
            Help the user lock their card.
            """),
        conditions=[
            "The customer wants to lock their card",
        ],
    )

    t1 = await journey.initial_state.transition_to(
        tool_state=list_user_cards,
    )

    # State t2: Present cards and ask which to lock
    t2 = await t1.target.transition_to(
        chat_state="Present the user with their list of cards and ask which one they want to lock",
        canned_responses=[
            await server.create_canned_response(
                template="Here are your cards: {% for card in cards %}\n- {{card.card_name}}, {{card.card_number}}{% endfor %}.\n\nWhich one would you like to lock?",
                signals=[
                    "Here are your cards:\n- Chase Freedom, **** **** **** 1234\n- Chase Sapphire, **** **** **** 5678\n\nWhich one would you like to lock?",
                    "Here are your cards:\n- Chase Student Card, **** **** **** 9012\n\nWhich one would you like to lock?",
                ],
            ),
            await server.create_canned_response(
                template="I can see you have these cards on your account:\n{% for card in cards %}{{loop.index}}. **{{card.card_name}}** ({{card.card_number}}){% if not loop.last %}\n{% endif %}{% endfor %}\nJust to confirm - you'd like me to lock the {{selected_card.card_name}} card ending in {{selected_card.card_number}}, correct?",
                signals=[
                    "I can see you have these cards on your account:\n1. **Chase Freedom** (**** **** **** 1234)\n2. **Chase Sapphire** (**** **** **** 5678)\nJust to confirm - you'd like me to lock the Chase Sapphire card ending in **** **** **** 5678, correct?",
                    "I can see you have these cards on your account:\n1. **Chase Freedom** (**** **** **** 1234)\n2. **Chase Sapphire** (**** **** **** 5678)\nJust to confirm - you'd like me to lock the Chase Freedom card ending in **** **** **** 1234, correct?",
                    "I can see you have these cards on your account:\n1. **Chase Student Card** (**** **** **** 9012)\nJust to confirm - you'd like me to lock the Chase Student Card card ending in **** **** **** 9012, correct?",
                ],
            ),
            await server.create_canned_response(
                template="Please confirm that you would like to lock your {{selected_card.card_name}} card.",
                signals=[
                    "Please confirm that you would like to lock your Chase Freedom card.",
                    "Please confirm that you would like to lock your Chase Sapphire card.",
                ],
            ),
        ],
    )

    # State t3: Ask for reason
    t3 = await t2.target.transition_to(
        chat_state="Ask for the reason for locking the card (e.g., lost, stolen, temporary lock, etc.)",
        canned_responses=[
            await server.create_canned_response(
                template="Could you please provide the reason for locking the card?",
            ),
        ],
    )

    # State t4: Lock card for lost/stolen (tool state)
    t4 = await t3.target.transition_to(
        condition="The card is lost or stolen",
        tool_state=lock_card,
    )

    # State t5: Confirm lock for lost/stolen and ask about replacement
    t5 = await t4.target.transition_to(
        chat_state="Tell the user that their card has been immediately locked for security reasons. Ask if they would you like to order a replacement card?",
        canned_responses=[
            await server.create_canned_response(
                template="Your {{locked_card.card_name}} card has been immediately locked for your protection. Would you like to order a replacement card?",
                signals=[
                    "Your Chase Freedom card has been immediately locked for your protection. Would you like to order a replacement card?",
                    "Your Chase Sapphire card has been immediately locked for your protection. Would you like to order a replacement card?",
                ],
            ),
        ],
    )

    await t5.target.transition_to(state=p.END_JOURNEY)

    # State t6: Lock card for other reasons (tool state)
    t6 = await t3.target.transition_to(
        condition="Otherwise",
        tool_state=lock_card,
    )

    # State t7: Confirm successful lock for other reasons
    t7 = await t6.target.transition_to(
        chat_state="Confirm whether or not the card has been locked successfully",
        canned_responses=[
            await server.create_canned_response(
                template="Your {{locked_card.card_name}} card has been locked successfully.",
                signals=[
                    "Your Chase Freedom card has been locked successfully.",
                    "Your Chase Sapphire card has been locked successfully.",
                ],
            ),
            await server.create_canned_response(
                template="Your card has been locked successfully. Would you like to continue with the previous request?",
            ),
        ],
    )

    _ = t7

    # Journey-level canned responses for general use
    journey_level_templates = [
        {
            "template": "Please call customer support at 123456789 to report the lost or stolen card.",
        },
    ]

    for item in journey_level_templates:
        await journey.create_canned_response(
            template=item["template"],
            signals=item.get("signals", []),
        )

    return journey
