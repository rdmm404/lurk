import asyncio
import itertools

from typing import Any
from rich import print

from lurk.config import Config, CheckerConfig, SearchConfig
from lurk.checkers import best_buy, checker
from lurk.models import Product
from lurk.api_client import ApiClient
from lurk.notifiers.telegram import TelegramNotifier

class Lurk:
    def __init__(self, config: Config):
        self.config = config

        self.AVAILABLE_CHECKERS: dict[str, type[checker.Checker]] = {
            "best-buy": best_buy.BestBuyChecker,
        }

    async def run(self) -> None:
        tasks: list[asyncio.Task[list[Product]]] = []

        for c in self.AVAILABLE_CHECKERS:
            if c in self.config.checkers:
                continue

            self.config.checkers[c] = CheckerConfig()

        api_clients: dict[str, ApiClient] = {}
        async with asyncio.TaskGroup() as tg:
            for checker_name, checker_cfg in self.config.checkers.items():
                if not checker_cfg.enabled:
                    print(f"Skipping disabled checker: {checker_name}")
                    continue

                checker_cls = self.AVAILABLE_CHECKERS.get(checker_name)
                if not checker_cls:
                    raise ValueError(f"Checker does not exist: {checker_name}")

                api_client = ApiClient(self.config.client)
                checker_instance = checker_cls(api_client)
                api_clients[checker_name] = api_client

                merged_search = self.config.search | checker_cfg.search
                for search_id, search_cfg in merged_search.items():
                    if not search_cfg.enabled:
                        print(f"Skipping disabled search: {search_id} in checker: {checker_name}")
                        continue

                    if search_id in self.config.search:
                        global_search_cfg = self.config.search[search_id]
                        global_search_dict = global_search_cfg.model_dump()
                        current_search_dict = search_cfg.model_dump(
                            exclude={"enabled"},
                            exclude_unset=True,
                            exclude_defaults=True,
                        )

                        filters_merge: dict[str, Any] = global_search_dict["filters"]
                        filters_merge.update(current_search_dict.get("filters", {}))

                        search_merge = global_search_dict | current_search_dict
                        search_merge["filters"] = filters_merge

                        merged_config = SearchConfig(**search_merge)
                    else:
                        merged_config = search_cfg

                    task = tg.create_task(
                        checker_instance.get_products(merged_config.query, merged_config.filters)
                    )
                    tasks.append(task)

        for client in api_clients.values():
            await client.close()

        found_products = itertools.chain.from_iterable(task.result() for task in tasks)
        await TelegramNotifier().notify(found_products)
