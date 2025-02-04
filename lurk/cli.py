import asyncio
import typer
import yaml

from pathlib import Path
from typing import Annotated, Any
from pydantic import ValidationError
from dataclasses import dataclass
from rich import print

from lurk.config import Config, CheckerConfig, SearchConfig
from lurk.checkers import best_buy, checker
from lurk.models import Product
from lurk.api_client import ApiClient

app = typer.Typer(no_args_is_help=True)

AVAILABLE_CHECKERS: dict[str, type[checker.Checker]] = {
    "best-buy": best_buy.BestBuyChecker,
}


@dataclass
class AppState:
    config: Config
    api_client: ApiClient


def load_config(path: Path) -> Config:
    """Load and validate configuration from YAML."""
    with open(path, "r", encoding="utf-8") as file:
        try:
            config_data = yaml.safe_load(file) or {}
            config = Config(**config_data)
        except ValidationError as e:
            raise typer.BadParameter(
                f"Your configuration is not valid. Here is the error:\n{e}"
            )
        return config


async def run_checkers(config: Config, api_client: ApiClient) -> None:
    """Run the enabled checkers with merged global parameters."""
    tasks: list[asyncio.Task[list[Product]]] = []

    for c in AVAILABLE_CHECKERS:
        if c in config.checkers:
            continue

        config.checkers[c] = CheckerConfig()

    async with asyncio.TaskGroup() as tg:
        for checker_name, checker_cfg in config.checkers.items():
            if not checker_cfg.enabled:
                print(f"Skipping disabled checker: {checker_name}")
                continue

            checker_cls = AVAILABLE_CHECKERS.get(checker_name)
            if not checker_cls:
                raise typer.BadParameter(f"Checker does not exist: {checker_name}")

            checker_instance = checker_cls(api_client)
            merged_search = config.search | checker_cfg.search
            for search_id, search_cfg in merged_search.items():
                if not search_cfg.enabled:
                    print(
                        f"Skipping disabled search: {search_id} in checker: {checker_name}"
                    )
                    continue

                if search_id in config.search:
                    global_search_cfg = config.search[search_id]
                    global_search_dict = global_search_cfg.model_dump()
                    current_search_dict = search_cfg.model_dump(
                        exclude={"enabled"}, exclude_unset=True, exclude_defaults=True
                    )

                    filters_merge: dict[str, Any] = global_search_dict["filters"]
                    filters_merge.update(current_search_dict.get("filters", {}))

                    search_merge = global_search_dict | current_search_dict
                    search_merge["filters"] = filters_merge

                    merged_config = SearchConfig(**search_merge)
                else:
                    merged_config = search_cfg

                task = tg.create_task(
                    checker_instance.get_products(
                        merged_config.query, merged_config.filters
                    )
                )
                tasks.append(task)

    for task in tasks:
        print(task.result())


@app.command()
def run(ctx: typer.Context) -> None:
    """Run the product checkers using the specified config."""
    state: AppState = ctx.obj
    asyncio.run(run_checkers(state.config, state.api_client))

@app.command()
def validate(ctx: typer.Context) -> None:
    state: AppState = ctx.obj
    print("Your config is valid!")
    print(state.config)

@app.callback()
def callback(
    ctx: typer.Context,
    config: Annotated[
        Path,
        typer.Option(
            "--config",
            "-c",
            help="Path to the config file",
            envvar="LURK_CONFIG",
            exists=True,
            file_okay=True,
            dir_okay=False,
            readable=True,
            resolve_path=True,
        ),
    ] = Path("lurk.yaml"),
) -> None:
    cfg = load_config(config)
    api_client = ApiClient(cfg.client)  # TODO: figure out where to close this
    ctx.obj = AppState(config=cfg, api_client=api_client)


if __name__ == "__main__":
    app()
