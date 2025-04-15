import traceback
from typing import cast, Any
from bs4 import BeautifulSoup, Tag, ResultSet
from pydantic import HttpUrl
from lurk.http_client import HttpClient, TextResponse
from lurk.checkers.checker import Checker
from lurk.config import SearchFilters
from lurk.models import Product
from rich import print


class MemoryExpressChecker(Checker):
    base_url = "https://www.memoryexpress.com"

    def __init__(self, http_client: HttpClient) -> None:
        self.http_client = http_client.set_base_url(self.base_url)

    # TODO: Implement a proper schema with different filters per vendor
    def validate_filters(self, filters: SearchFilters) -> None:
        if filters.stores and len(filters.stores) > 1:
            raise ValueError("Memory Express only supports one store")
        if not filters.categories:
            raise ValueError("Memory Express requires at least one category")
        if len(filters.categories) > 1:
            raise ValueError("Memory Express only supports one category")

    async def get_products(
        self, search: str, filters: SearchFilters | None = None
    ) -> list[Product]:
        if not filters:
            filters = SearchFilters()
        self.validate_filters(filters)

        resp = await self._fetch_products(search, filters)
        products = await self._parse_products(resp)
        return await self._filter_products(products, filters)

    async def _fetch_products(self, search: str, filters: SearchFilters) -> TextResponse:
        category = cast(list[str], filters.categories)[0]

        query_params = {"Search": search}

        if filters.in_stock:
            query_params["InventoryType"] = "InStock"

        if filters.stores:
            query_params["Inventory"] = filters.stores[0]

        return await self.http_client.get(f"/Category/{category}", params=query_params)

    async def _parse_products(self, resp: TextResponse) -> list[Product]:
        soup = BeautifulSoup(resp.content, "html.parser")
        products = []

        # Find all product containers
        product_containers: ResultSet[Any] = soup.find_all("div", {"class": "c-shca-icon-item"})

        for container in product_containers:
            if not isinstance(container, Tag):
                continue

            try:
                # Extract product name
                name_elem = container.find("div", {"class": "c-shca-icon-item__body-name"})
                if not isinstance(name_elem, Tag):
                    continue
                name = name_elem.text.strip()

                # Extract product URL
                url_div_elem = container.find("div", {"class": "c-shca-icon-item__body-image"})
                if not isinstance(url_div_elem, Tag):
                    continue
                url_elem = url_div_elem.find("a")
                if not isinstance(url_elem, Tag):
                    continue
                url = None
                if isinstance(url_elem, Tag) and "href" in url_elem.attrs:
                    href = url_elem.attrs["href"]
                    if isinstance(href, list):
                        href = href[0]
                    url = HttpUrl(f"{self.base_url}{href}")

                # Extract SKU
                sku_elem = container.find("div", {"class": "c-shca-icon-item__body-ref"})
                sku = None
                if isinstance(sku_elem, Tag):
                    span_elem = sku_elem.find("span")
                    if isinstance(span_elem, Tag):
                        sku = span_elem.text.strip()

                # Extract price
                price_elem = container.find("div", {"class": "c-shca-icon-item__summary-list"})
                price = None
                if isinstance(price_elem, Tag):
                    price_span = price_elem.find("span")
                    if isinstance(price_span, Tag):
                        price_text = price_span.text.strip()
                        try:
                            price = float(price_text.replace("$", "").replace(",", ""))
                        except (ValueError, AttributeError):
                            print(f"Error parsing price: {price_text}")
                            traceback.print_exc()
                            continue
                # Extract availability
                availability_elem = container.find(
                    "div", {"class": "c-shca-icon-item__body-inventory"}
                )
                in_stock = True  # Default to True if no inventory status is shown
                if isinstance(availability_elem, Tag):
                    availability_text = availability_elem.text.strip().lower()
                    in_stock = (
                        "while supplies last" in availability_text
                        or "in stock" in availability_text
                    )

                # Use name as description since Memory Express doesn't provide separate descriptions
                description = name

                if name and url and sku and price is not None:
                    products.append(
                        Product(
                            name=name,
                            url=url,
                            price=price,
                            in_stock=in_stock,
                            sku=sku,
                            description=description,
                        )
                    )
            except Exception as e:
                print(f"Error parsing product: {e}")
                traceback.print_exc()
                continue
        return products

    async def _filter_products(
        self, products: list[Product], filters: SearchFilters
    ) -> list[Product]:
        filtered_products = []

        for product in products:
            if filters.min_price and product.price < filters.min_price:
                continue
            if filters.max_price and product.price > filters.max_price:
                continue
            filtered_products.append(product)

        return filtered_products
