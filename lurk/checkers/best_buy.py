from typing import Self, Any, TypedDict, no_type_check
from rich import print
from pydantic import ValidationError

from enum import StrEnum
from lurk.models import Product, ProductFilter
from lurk.checkers.checker import Checker
from lurk.api_client import ApiClient
from lurk.config import Config


class BestBuyRoutes(StrEnum):
    SEARCH = "/api/v2/json/search"
    STOCK = "/ecomm-api/availability/products"


class BestBuySearchParams(TypedDict, total=False):
    currentRegion: str
    lang: str
    query: str
    sortBy: str
    sortDir: str
    path: str


BestBuyProductsParams = TypedDict(
    "BestBuyProductsParams",
    {
        "accept": str,
        "accept-language": str,
        "locations": str,
        "postalCode": str,
        "skus": str,
    },
    total=False,
)


class BestBuyChecker(Checker):
    base_url = "https://www.bestbuy.ca"

    def __init__(self, config: Config) -> None:
        self.client = ApiClient(base_url=self.base_url, config=config.client)

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(self, *_: Any) -> None:
        await self.client.close()

    async def get_products(self, filter: ProductFilter) -> list[Product]:
        raw_products = await self._search_products(filter)
        products: list[Product] = []

        for p in raw_products:
            try:
                product = self._parse_product(p)  # type: ignore
            except ValidationError:
                pass

            products.append(product)

        stocks = await self._fetch_products([p.sku for p in products], filter)

        for product in products:
            availability = stocks.get(product.sku)
            if not availability:
                print(f"availability not found for product {product.sku}")
                continue
            pickup_available = availability.get("pickup", {}).get("purchasable", False)
            shipping_available = availability.get("shipping", {}).get(
                "purchasable", False
            )
            product.in_stock = pickup_available or shipping_available

        return products

    async def _search_products(self, filter: ProductFilter) -> list[dict[str, Any]]:
        default_search_params: BestBuySearchParams = {
            "currentRegion": "ON",
            "lang": "en-CA",
            "sortBy": "relevance",
            "sortDir": "desc",
        }
        filter_params: BestBuySearchParams = {"query": filter.search}
        if filter.region:
            filter_params["currentRegion"] = filter.region
        if filter.language:
            filter_params["lang"] = filter.language
        if filter.categories:
            filter_params["path"] = ";".join(f"category:{c}" for c in filter.categories)
        if filter.min_price or filter.max_price:
            price_range_str = f";currentPrice:[{filter.min_price or '*'} TO {filter.max_price or '*'}]"
            filter_params["path"] += price_range_str

        search_resp = await self.client.get(
            BestBuyRoutes.SEARCH, params=default_search_params | filter_params
        )
        products: list[dict[str, Any]] = search_resp.json.get("products", [])
        return products

    @no_type_check
    def _parse_product(self, raw_product: dict[str, Any]) -> Product:
        return Product(
            sku=raw_product.get("sku"),
            url=self.base_url + raw_product.get("productUrl"),
            in_stock=False,
            name=raw_product.get("name"),
            description=raw_product.get("shortDescription"),
            price=raw_product.get("salePrice"),
        )

    async def _fetch_products(
        self, skus: list[str], filter: ProductFilter
    ) -> dict[str, dict[str, Any]]:
        if not skus:
            return {}
        default_params: BestBuyProductsParams = {
            "accept": "application/vnd.bestbuy.simpleproduct.v1+json",
            "accept-language": "en-CA",
        }
        params: BestBuyProductsParams = {"skus": "|".join(skus)}
        if filter.stores:
            params["locations"] = "|".join(filter.stores)
        if filter.zip_code:
            params["postalCode"] = filter.zip_code

        resp = await self.client.get(
            BestBuyRoutes.STOCK, params=default_params | params
        )
        stocks = resp.json.get("availabilities", [])
        stocks_mapping: dict[str, dict[str, Any]] = {}
        for s in stocks:
            if not (sku := s.get("sku")):
                continue
            stocks_mapping[sku] = s
        return stocks_mapping
