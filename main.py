import asyncio
from src.checkers.best_buy import BestBuyChecker
from src.models import ProductFilter
from rich import print


async def main() -> None:
    checker = BestBuyChecker()
    products = await checker.get_products(
        filter=ProductFilter(
            search="nvidia 4070",
            categories=["Computers & Tablets", "PC Components"],
            max_price=1500,
        )
    )
    print(products)


if __name__ == "__main__":
    asyncio.run(main())
