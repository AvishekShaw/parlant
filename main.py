import asyncio
from textwrap import dedent
from dotenv import load_dotenv

import parlant.sdk as p

from journeys import dispute_transaction, lock_card, replace_card


async def create_customers(server: p.Server) -> None:
    await server.create_customer(name="Elder")
    await server.create_customer(name="Millenial")
    await server.create_customer(name="Small Business Owner")
    await server.create_customer(name="Foreigner")


async def add_global_guidelines(agent: p.Agent) -> None:
    await agent.create_guideline(
        condition="user is not in a position to call customer care (can't call, can't wait on hold, etc.)",
        action="ask if they'd like you to connect them with a human representative through chat",
    )

    await agent.create_guideline(
        condition="the customer switched to a different intent while in the middle of handling another one, without clearly abandoning the initial intent",
        action="consider asking them whether they'd like to continue handling the initial intent",
    )


async def add_global_canned_responses(agent: p.Agent) -> None:
    for template in [
        "How can I help you today?",
        "Could you please clarify what you mean?",
        "Would you like to dispute a transaction or lock your card?",
        "There's a number of ways I can help you with that. Would you like to dispute a transaction, lock your card, or replace it?",
        "Since you are not in a position to call customer care, would you like me to connect you with a human representative through chat to assist you further with this dispute?",
        "Great. Feel free to reach out again if you need any other assistance with your accounts.",
        "Unfortunately, I cannot cancel disputes at the moment, but you can contact customer care at 123456789 for assistance with that.",
    ]:
        await agent.create_canned_response(template)

    # Preamble responses
    for template in [
        "Sure.",
        "Got it.",
        "Understood.",
        "Let me look into that.",
        "On it.",
        "Sorry to hear that.",
    ]:
        await agent.create_canned_response(template, tags=[p.Tag.preamble()])


async def add_capabilities(agent: p.Agent) -> None:
    await agent.experimental_features.create_capability(
        title="Dispute a transaction",
        description="Customer does not recognize a transaction and wants to dispute it. Also includes cases where the customer is suspicious of fraud transactions to have taken place from their card",
        signals=[
            "Dispute transaction",
            "I don't recognize the 400$ charge",
            "I dont remember making this payment",
        ],
    )

    await agent.experimental_features.create_capability(
        title="Lock a card",
        description="Customer wants to lock their card for security reasons, such as lost or stolen card. Also includes cases where the customer is suspicious of fraud transactions to have taken place from their card",
        signals=["Lock card", "I want to lock my card for security reasons"],
    )


class CustomNoMatchResponseProvider(p.NoMatchResponseProvider):
    async def get_template(self, context: p.LoadedContext, draft: str | None) -> str:
        return "I'm sorry, I didn't understand that. Could you please rephrase or provide more details?"


async def configure(container: p.Container) -> p.Container:
    container[p.NoMatchResponseProvider] = CustomNoMatchResponseProvider()
    return container


async def main() -> None:
    load_dotenv()

    async with p.Server(
        log_level=p.LogLevel.DEBUG,
        session_store="local",
        nlp_service=p.NLPServices.anthropic,
        configure_container=configure,
    ) as server:
        await create_customers(server)

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
            composition_mode=p.CompositionMode.FLUID,  # Changed from STRICT to allow dynamic response generation
        )

        dispute_transaction_journey = await dispute_transaction.create_journey(
            server, agent
        )
        lock_card_journey = await lock_card.create_journey(server, agent)
        replace_card_journey = await replace_card.create_journey(server, agent)

        disambiguator = await agent.create_observation(
            "The user has a credit card related problem but it's not clear which action they wish to take.",
        )

        await disambiguator.disambiguate(
            [dispute_transaction_journey, replace_card_journey, lock_card_journey]
        )

        await add_global_guidelines(agent)
        await add_global_canned_responses(agent)
        await add_capabilities(agent)


asyncio.run(main())
