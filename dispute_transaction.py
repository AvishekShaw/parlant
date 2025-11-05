from textwrap import dedent
import parlant.sdk as p

from tools import fetch_recent_transactions, file_dispute, list_user_cards


async def create_journey(server: p.Server, agent: p.Agent) -> p.Journey:
    journey = await agent.create_journey(
        title="Dispute a Transaction",
        description=dedent("""\
            Help the user dispute a credit card transaction following the complete validation and eligibility flow.
            """),
        conditions=[
            "The customer wants to dispute a transaction",
        ],
    )

    t1 = await journey.initial_state.transition_to(
        tool_state=list_user_cards,
    )

    # State t2: Present cards and ask which card
    t2 = await t1.target.transition_to(
        chat_state="Present the user with their list of credit cards and ask which card the transaction was made from",
        canned_responses=[
            await server.create_canned_response(
                template="Here are your credit cards: {% for card in cards %}\n - {{card.card_name}}, {{card.card_number}}{% endfor %}.\n\nWhich card was the transaction made from?",
                signals=[
                    "Here are your credit cards: Chase Freedom, Chase Sapphire. Which card was the transaction made from?",
                    "Here are your credit cards: Chase Student Card. Which card was the transaction made from?",
                    """\
I can help you dispute that transaction. I see you have two credit cards with us:

1. **Chase Freedom** (**** **** **** 1234)
2. **Chase Sapphire** (**** **** **** 5678)

Which card did the disputed transaction appear on?""",
                ],
            ),
            await server.create_canned_response(
                template="Could you confirm if the transaction was made from this card: {{card_name}} ending in {{card_number}}?",
                signals=[
                    "Could you confirm if the transaction was made from this card: Chase Freedom ending in **** **** **** 1234?",
                    "Could you confirm if the transaction was made from this card: Chase Sapphire ending in **** **** **** 5678?",
                ],
            ),
        ],
    )

    # State t3: Card not found - apologize and offer human agent
    t3 = await t2.target.transition_to(
        condition="User says that the required card is not on the list",
        chat_state="Apologize and ask if they want to connect with a human agent",
        canned_responses=[
            await server.create_canned_response(
                template="I apologize, but I cannot help with this request. Let me connect you with a human agent.",
            ),
        ],
    )

    await t3.target.transition_to(state=p.END_JOURNEY)

    # State t4: Ask if they suspect fraud
    t4 = await t2.target.transition_to(
        condition="User selects one of the cards on the list",
        chat_state="Ask if they suspect the transaction is fraudulent",
        canned_responses=[
            await server.create_canned_response(
                template="Do you suspect fraud with this transaction?",
            ),
            await server.create_canned_response(
                template="No problem, I switched the card.\n\nSo do you suspect this transaction is fraudulent?"
            ),
        ],
    )

    # State t5: Ask about Report Problem button
    t5 = await t4.target.transition_to(
        chat_state="Ask if they have looked at the 'Report Problem' button next to the transaction on their transactions dashboard",
        canned_responses=[
            await server.create_canned_response(
                template="Have you looked at the 'Report Problem' button next to the transaction on your transactions dashboard? It lets you report such issues quickly and easily.",
            ),
            await server.create_canned_response(
                template="It's a button on your transactions dashboard that lets you quickly flag issues with specific transactions. ",
                signals=[
                    "The 'Report Problem' button is a feature on your transactions dashboard that lets you quickly flag issues with specific transactions."
                ],
            ),
        ],
    )

    # Branch: User HAS checked Report Problem button
    _ = await t5.target.transition_to(
        condition="User HAS checked the Report Problem button",
        chat_state="Inform the user about merchant resolution process and provide customer care contact information.",
        canned_responses=[
            await server.create_canned_response(
                template="Here's information about the merchant resolution process [INFORMATION...].\n\nYou can contact customer care at 123456789 for assistance.",
            ),
        ],
    )

    # State t6: User has NOT checked Report Problem AND suspects fraud
    t6 = await t5.target.transition_to(
        condition="User has NOT checked the Report Problem button AND suspects fraud",
        chat_state="Inform the user about authorized user transactions and merchant resolution process, and ask if they want to continue to dispute the transaction.",
        canned_responses=[
            await server.create_canned_response(
                template="Here's what you need to know about authorized user transactions and merchant resolution process [INFORMATION...].\n\nYou can also contact customer care at 123456789.\n\nWould you still like to continue to dispute the transaction with me?",
            ),
            await server.create_canned_response(
                template="I'm happy to help. Here's what you should know about handling suspected fraud cases.",
            ),
            await server.create_canned_response(
                template="Based on this information, would you like to continue to dispute the transaction?",
            ),
        ],
    )

    # State t7: Confirm help and ask for transaction date
    t7 = await t6.target.transition_to(
        condition="They want to continue to dispute the transaction",
        chat_state="Confirm you're happy to help and ask for the date of the transaction they want to dispute",
        canned_responses=[
            await server.create_canned_response(
                template="Perfect, I'm happy to help you dispute that transaction.\nTo get started, what's the date of the transaction you'd like to dispute?"
            ),
            await server.create_canned_response(
                template="I'll be happy to help you with that.\n\nCould you please provide the date of the transaction you want to dispute?",
                signals=[
                    "I will assist  you with you disputing the transaction. Please provide the date of the transaction you want to dispute?",
                    "I'm happy to help you dispute this $50 Amazon transaction on your Chase Freedom card.What date did this transaction occur?",
                ],
            ),
            await server.create_canned_response(
                template="Could you please provide the date of the transaction you want to dispute?",
            ),
        ],
    )

    _ = await t6.target.transition_to(
        condition="They don't want to continue to dispute the transaction",
        state=p.END_JOURNEY,
    )

    # State t8: User has NOT checked Report Problem AND does NOT suspect fraud
    t8 = await t5.target.transition_to(
        condition="User has NOT checked the Report Problem button AND does NOT suspect fraud",
        chat_state="Inform the user about merchant resolution process, then ask if they want to continue to dispute the transaction.",
        canned_responses=[
            await server.create_canned_response(
                template="In cases where you don't suspect fraud, it's often helpful to first try resolving the issue directly with the merchant. They might be able to provide more details or resolve the issue quickly.\n\nWould you like to proceed with disputing the transaction through us, or would you prefer to contact the merchant first?",
            ),
            await server.create_canned_response(
                template="I'm happy to help. Here's what you should know about transaction disputes when fraud is not suspected.",
            ),
        ],
    )

    _ = await t8.target.transition_to(
        condition="They want to continue to dispute the transaction",
        state=t7.target,
    )

    _ = await t8.target.transition_to(
        condition="They don't want to continue to dispute the transaction",
        state=p.END_JOURNEY,
    )

    # State t9: Ask for transaction amount
    t9 = await t7.target.transition_to(
        chat_state="Ask for the amount of the transaction they want to dispute",
        canned_responses=[
            await server.create_canned_response(
                template="Now I'll need the amount of the transaction you want to dispute. What was the dollar amount?",
            ),
            await server.create_canned_response(
                template="Could you please provide the amount of the transaction?",
            ),
        ],
    )

    # State t10: Ask for merchant name
    t10 = await t9.target.transition_to(
        chat_state="Ask for the merchant name of the transaction they want to dispute",
        canned_responses=[
            await server.create_canned_response(
                template="And what's the name of the merchant for this transaction?",
            ),
            await server.create_canned_response(
                template="Could you please provide the merchant name of the transaction?",
            ),
        ],
    )

    # State t11: Ask for dispute reason
    t11 = await t10.target.transition_to(
        chat_state="Ask for the reason for the dispute",
        canned_responses=[
            await server.create_canned_response(
                template="Now I need to understand the specific reason for disputing this charge. Could you tell me why you're disputing this transaction?\n\nFor example, did you not authorize it, was it a duplicate charge, or was there an issue with the goods or services?"
            ),
            await server.create_canned_response(
                template="What is the reason for the dispute?",
            ),
            await server.create_canned_response(
                template="Could you please provide the reason for the dispute?",
            ),
        ],
    )

    # State t12: File dispute (tool state)
    t12 = await t11.target.transition_to(
        tool_state=[file_dispute],
    )

    # State t13: Restate details and confirm filing
    t13 = await t12.target.transition_to(
        chat_state="Restate the dispute details and inform them whether the dispute has been filed successfully.",
        canned_responses=[
            await server.create_canned_response(
                template="Your dispute has been filed successfully. Dispute ID: {{dispute_id}}. We will investigate and resolve it as soon as possible.",
                signals=[
                    "Your dispute has been filed successfully. Dispute ID: DISP_12345. We will investigate and resolve it as soon as possible.",
                    "Your dispute has been filed successfully. Dispute ID: DISP_67890. We will investigate and resolve it as soon as possible.",
                ],
            ),
            await server.create_canned_response(
                template="All set! Your dispute has been filed successfully.\n\nFor your reference, your dispute ID is {{dispute_id}}.",
            ),
            await server.create_canned_response(
                template="I encountered an error while processing your dispute!",
            ),
            await server.create_canned_response(
                template="Thank you for confirming. You want to continue disputing that transaction, correct?",
                signals=[
                    "Thank you for confirming. You want to dispute the transaction with Amazon for $89.99 made on 2025-07-05 from your Chase Freedom card. Is that correct?",
                    "Thank you for confirming. You want to dispute the transaction with Best Buy for $250.00 made on 2025-07-02 from your Chase Sapphire card. Is that correct?",
                ],
            ),
            await server.create_canned_response(
                template="Can you please confirm the merchant name, amount, and date again?",
                signals=[
                    "Can you confirm that the merchant name is Amazon, amount is $89.99 and date is 2025-07-05?",
                    "Can you confirm that the merchant name is Starbucks, amount is $45.50 and date is 2025-07-04?",
                ],
            ),
        ],
    )

    _ = t13

    # Add guidelines for handling deviations
    await journey.create_guideline(
        condition="the customer does not remember a detail that you requested",
        action="fetch latest transactions to help them identify the transaction detail they would need",
        tools=[fetch_recent_transactions],
    )

    await journey.create_guideline(
        condition="the customer wants to dispute multiple transactions at once",
        action="inform them that you can only process one dispute at a time and ask them to complete the current dispute first",
    )

    await journey.create_guideline(
        condition="The customer changed their mind and wants to cancel a dispute which was already filed",
        action="inform them that unfortunately you cannot cancel disputes at the moment, but they can contact customer care at 123456789 for assistance",
    )

    await journey.create_guideline(
        condition="the customer asks about the status of a previously filed dispute (not the one already discussed in the current conversation)",
        action="inform them that meanwhile they can check the status of their dispute by contacting customer care at 123456789, but that in the near future you will also be able to help them with this",
    )

    # Journey-level canned responses for guidelines and general use
    journey_level_templates = [
        {
            "template": "I need to verify some information first. Are you over 18 years old?",
        },
        {
            "template": "Minors cannot dispute transactions. Please ask your guardian to help you with this dispute.",
        },
        {
            "template": "I need to check your account eligibility. Unfortunately, you are not entitled to dispute transactions. Please call customer care at 123456789 for further assistance.",
        },
        {
            "template": "Here are your recent transactions: {% for t in transactions %}: \n Date: {{t.date}} - Merchant:{{t.merchant_name}} - Amount:${{t.amount}}{% endfor %}\n\nWhich would would you like to dispute?",
            "signals": [
                "Here are your recent transactions: \n- Date: 2025-07-05 - Merchant: Amazon - Amount: $89.99\n- Date: 2025-07-04 - Merchant: Starbucks - Amount: $45.50\n- Date: 2025-07-03 - Merchant: Shell Gas Station - Amount: $120.00",
                "Here are your recent transactions: \n- Date: 2025-07-06 - Merchant: Netflix - Amount: $15.99\n- Date: 2025-07-05 - Merchant: McDonald's - Amount: $8.50\n- Date: 2025-07-04 - Merchant: iTunes - Amount: $25.00",
            ],
        },
    ]

    for item in journey_level_templates:
        await journey.create_canned_response(
            template=item["template"],
            signals=item.get("signals", []),
        )

    return journey
