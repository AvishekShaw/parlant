"""
Mock tool implementations for the Chase Digital Assistant.

These tools simulate backend operations for credit card management,
including listing cards, fetching transactions, filing disputes, and
managing card locks and replacements.
"""

import random
from datetime import datetime, timedelta
from typing import List, Dict, Any
import parlant.sdk as p


# Mock data: Credit cards for different customer types
MOCK_CARDS = {
    "Elder": [
        {"card_name": "Chase Freedom", "card_number": "**** **** **** 1234"},
    ],
    "Millenial": [
        {"card_name": "Chase Freedom", "card_number": "**** **** **** 5678"},
        {"card_name": "Chase Sapphire", "card_number": "**** **** **** 9012"},
    ],
    "Small Business Owner": [
        {"card_name": "Chase Ink Business", "card_number": "**** **** **** 3456"},
        {"card_name": "Chase Sapphire Reserve", "card_number": "**** **** **** 7890"},
    ],
    "Foreigner": [
        {"card_name": "Chase Student Card", "card_number": "**** **** **** 2468"},
    ],
}

# Mock transaction data - realistic merchants and amounts
MOCK_TRANSACTION_TEMPLATES = [
    {"merchant_name": "Amazon.com", "amount_range": (15.99, 299.99)},
    {"merchant_name": "Starbucks", "amount_range": (4.50, 25.00)},
    {"merchant_name": "Shell Gas Station", "amount_range": (35.00, 120.00)},
    {"merchant_name": "Walmart", "amount_range": (20.00, 250.00)},
    {"merchant_name": "Netflix", "amount_range": (15.99, 15.99)},
    {"merchant_name": "McDonald's", "amount_range": (6.50, 28.00)},
    {"merchant_name": "Best Buy", "amount_range": (50.00, 800.00)},
    {"merchant_name": "Target", "amount_range": (25.00, 200.00)},
    {"merchant_name": "Whole Foods", "amount_range": (30.00, 150.00)},
    {"merchant_name": "Apple.com", "amount_range": (0.99, 1299.00)},
    {"merchant_name": "Uber", "amount_range": (8.00, 45.00)},
    {"merchant_name": "DoorDash", "amount_range": (15.00, 65.00)},
    {"merchant_name": "Home Depot", "amount_range": (25.00, 400.00)},
    {"merchant_name": "CVS Pharmacy", "amount_range": (8.00, 75.00)},
]

# Mock addresses for different customers
MOCK_ADDRESSES = {
    "Elder": "1234 Oak Street, Springfield, IL 62701",
    "Millenial": "567 Urban Loft Ave, Brooklyn, NY 11201",
    "Small Business Owner": "890 Commerce Drive, Austin, TX 78701",
    "Foreigner": "321 Campus Road, Boston, MA 02215",
}


def _generate_recent_transactions(card_number: str, num_transactions: int = 10) -> List[Dict[str, Any]]:
    """Generate realistic recent transactions for a card."""
    transactions = []
    current_date = datetime.now()

    for i in range(num_transactions):
        # Pick a random merchant template
        template = random.choice(MOCK_TRANSACTION_TEMPLATES)

        # Generate transaction
        transaction_date = current_date - timedelta(days=i * 2 + random.randint(0, 1))
        amount = round(random.uniform(*template["amount_range"]), 2)

        transactions.append({
            "date": transaction_date.strftime("%Y-%m-%d"),
            "merchant_name": template["merchant_name"],
            "amount": amount,
            "card_number": card_number,
        })

    return transactions


@p.tool
async def list_user_cards(context: p.ToolContext) -> p.ToolResult:
    """
    Returns the list of credit cards associated with the customer's account.

    Returns:
        ToolResult containing a 'cards' list with card information including card_name and card_number.
    """
    # Get customer name from context
    customer_name = context.customer.name if context.customer else "Elder"

    # Return cards for this customer
    cards = MOCK_CARDS.get(customer_name, MOCK_CARDS["Elder"])

    return p.ToolResult(data={"cards": cards})


@p.tool
async def fetch_recent_transactions(
    context: p.ToolContext,
    card_number: str = "",
    num_transactions: int = 10
) -> p.ToolResult:
    """
    Fetches recent transactions for a specific credit card.

    Args:
        card_number: The card number to fetch transactions for (partial or full)
        num_transactions: Number of recent transactions to return (default: 10)

    Returns:
        ToolResult containing a 'transactions' list with transaction details.
    """
    transactions = _generate_recent_transactions(card_number, num_transactions)

    return p.ToolResult(data={"transactions": transactions})


@p.tool
async def file_dispute(
    context: p.ToolContext,
    card_number: str,
    date: str,
    amount: str,
    merchant_name: str,
    reason: str,
) -> p.ToolResult:
    """
    Files a dispute for a transaction.

    Args:
        card_number: The card number where the disputed transaction occurred
        date: Date of the disputed transaction (YYYY-MM-DD format)
        amount: Amount of the disputed transaction
        merchant_name: Name of the merchant
        reason: Reason for disputing the transaction

    Returns:
        ToolResult containing dispute_id and status.
    """
    # Generate a unique dispute ID
    dispute_id = f"DISP_{random.randint(10000, 99999)}"

    return p.ToolResult(data={
        "dispute_id": dispute_id,
        "status": "filed",
        "card_number": card_number,
        "date": date,
        "amount": amount,
        "merchant_name": merchant_name,
        "reason": reason,
        "filed_at": datetime.now().isoformat(),
    })


@p.tool
async def lock_card(
    context: p.ToolContext,
    card_number: str,
    reason: str,
) -> p.ToolResult:
    """
    Locks a credit card for security reasons.

    Args:
        card_number: The card number to lock
        reason: Reason for locking (e.g., "lost", "stolen", "temporary")

    Returns:
        ToolResult containing lock confirmation and card details.
    """
    # Find the card name from the card number
    customer_name = context.customer.name if context.customer else "Elder"
    cards = MOCK_CARDS.get(customer_name, MOCK_CARDS["Elder"])

    locked_card = None
    for card in cards:
        if card["card_number"] == card_number:
            locked_card = card
            break

    if not locked_card:
        locked_card = {"card_name": "Unknown Card", "card_number": card_number}

    return p.ToolResult(data={
        "status": "locked",
        "locked_card": locked_card,
        "reason": reason,
        "locked_at": datetime.now().isoformat(),
    })


@p.tool
async def get_user_address(context: p.ToolContext) -> p.ToolResult:
    """
    Retrieves the customer's registered address for card delivery.

    Returns:
        ToolResult containing address information.
    """
    customer_name = context.customer.name if context.customer else "Elder"
    address = MOCK_ADDRESSES.get(customer_name, MOCK_ADDRESSES["Elder"])

    return p.ToolResult(data={
        "address": address,
        "customer_name": customer_name,
    })


@p.tool
async def process_card_replacement(
    context: p.ToolContext,
    card_number: str,
    reason: str,
    address: str,
    delivery_speed: str,
) -> p.ToolResult:
    """
    Processes a card replacement request.

    Args:
        card_number: The card number to replace
        reason: Reason for replacement (e.g., "lost", "stolen", "damaged", "expired")
        address: Delivery address for the new card
        delivery_speed: Delivery speed ("standard" or "express")

    Returns:
        ToolResult containing replacement confirmation, reference number, and delivery details.
    """
    # Generate reference ID
    reference_id = f"CR_{random.randint(10000, 99999)}"

    # Calculate expected delivery date
    if delivery_speed.lower() == "express":
        delivery_days = random.randint(2, 3)
    else:
        delivery_days = random.randint(5, 7)

    delivery_date = (datetime.now() + timedelta(days=delivery_days)).strftime("%B %d, %Y")

    # Find card details
    customer_name = context.customer.name if context.customer else "Elder"
    cards = MOCK_CARDS.get(customer_name, MOCK_CARDS["Elder"])

    card_name = "Unknown Card"
    for card in cards:
        if card["card_number"] == card_number:
            card_name = card["card_name"]
            break

    return p.ToolResult(data={
        "status": "processed",
        "reference_id": reference_id,
        "card_name": card_name,
        "card_number": card_number,
        "reason": reason,
        "delivery_address": address,
        "delivery_speed": delivery_speed,
        "delivery_date": delivery_date,
        "processed_at": datetime.now().isoformat(),
        "deactivation_info": "has been immediately deactivated due to security concerns"
            if reason.lower() in ["lost", "stolen"]
            else "will be deactivated when you activate your new card",
    })
