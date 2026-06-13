"""
10_custom_tool.py — Define and attach a custom Python function as a tool

Any Python function with type hints and a docstring becomes an agent tool.

Install:
    pip install buddy-ai

Set your API key:
    export OPENAI_API_KEY=sk-...
"""

from buddy import Agent
from buddy.models.openai import OpenAIChat
from buddy.tools.function import Function


def get_stock_price(symbol: str) -> dict:
    """
    Get the current stock price for a given ticker symbol.

    Args:
        symbol: Stock ticker symbol (e.g. AAPL, GOOGL, MSFT)

    Returns:
        Dictionary with price, currency, and market status.
    """
    # Mock implementation — replace with a real API call
    mock_prices = {
        "AAPL": 189.50,
        "GOOGL": 175.20,
        "MSFT": 420.80,
        "NVDA": 875.40,
    }
    price = mock_prices.get(symbol.upper(), 100.0)
    return {
        "symbol": symbol.upper(),
        "price": price,
        "currency": "USD",
        "market": "OPEN",
    }


def calculate_portfolio_value(symbols: list[str], quantities: list[int]) -> dict:
    """
    Calculate the total value of a stock portfolio.

    Args:
        symbols: List of stock ticker symbols
        quantities: Number of shares for each symbol (same order as symbols)

    Returns:
        Total portfolio value and per-stock breakdown.
    """
    breakdown = []
    total = 0.0
    for symbol, qty in zip(symbols, quantities):
        data = get_stock_price(symbol)
        value = data["price"] * qty
        total += value
        breakdown.append({"symbol": symbol, "qty": qty, "price": data["price"], "value": value})

    return {"total_value": total, "currency": "USD", "breakdown": breakdown}


agent = Agent(
    name="finance_agent",
    model=OpenAIChat(id="gpt-4o-mini"),
    tools=[get_stock_price, calculate_portfolio_value],
    show_tool_calls=True,
    instructions=["You are a helpful financial assistant.", "Always show exact numbers."],
    markdown=True,
)

if __name__ == "__main__":
    agent.print_response(
        "I own 10 shares of AAPL, 5 shares of NVDA, and 20 shares of MSFT. "
        "What is my portfolio worth?"
    )
