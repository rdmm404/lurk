import os

from aiogram import Bot
from aiogram.client.default import DefaultBotProperties
from aiogram.exceptions import TelegramAPIError
from aiogram.enums import ParseMode

from rich import print
from collections.abc import Iterable

from lurk.models import Product
from lurk.misc import InvalidConfigException


PRODUCTS_TEMPLATE = """
<u><b>Found some products:</b></u>

{product_list}
"""


class TelegramNotifier:
    API_TOKEN_VAR = "LURK_TELEGRAM_TOKEN"
    CHAT_ID_VAR = "LURK_TELEGRAM_CHAT_ID"

    def __init__(self, api_token: str | None = None, chat_id: str | None = None):
        self.api_token = api_token or os.getenv(self.API_TOKEN_VAR)
        self.chat_id = chat_id or os.getenv(self.CHAT_ID_VAR)

        if not self.api_token:
            raise InvalidConfigException(
                f"Telegram api token not found. Please set it using {self.API_TOKEN_VAR}"
            )

        if not self.chat_id:
            raise InvalidConfigException(
                f"Telegram chat id not found. Please set it using {self.CHAT_ID_VAR}"
            )

    def format_message(self, products: Iterable[Product]) -> str:
        product_list = "\n".join(f'<a href="{p.url}">{p.name}</a> for ${p.price}' for p in products)
        return PRODUCTS_TEMPLATE.format(product_list=product_list)

    async def notify(self, products: Iterable[Product]) -> None:
        assert self.api_token and self.chat_id

        if not any(products):
            print("No products to notify about.")
            return

        async with Bot(
            token=self.api_token, default=DefaultBotProperties(parse_mode=ParseMode.HTML)
        ) as bot:
            try:
                await bot.send_message(chat_id=self.chat_id, text=self.format_message(products))
                print("Telegram notification sent successfully!")
            except TelegramAPIError as e:
                print(f"Failed to send Telegram message: {e}")
