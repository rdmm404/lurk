import asyncio
import typer
import yaml

from pathlib import Path
from typing import Annotated
from pydantic import ValidationError
from dataclasses import dataclass
from rich import print

from lurk.config import Config, CheckerConfig
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

        config.checkers[c] = CheckerConfig(
            search=config.global_config.search, filters=config.global_config.filters
        )

    async with asyncio.TaskGroup() as tg:
        for checker_name, checker_config in config.checkers.items():
            if not checker_config.enabled:
                print(f"Skipping disabled checker: {checker_name}")
                continue

            checker_cls = AVAILABLE_CHECKERS.get(checker_name)
            if not checker_cls:
                raise typer.BadParameter(f"Checker does not exist: {checker_name}")

            if not checker_config.filters:
                checker_config.filters = config.global_config.filters

            checker_instance = checker_cls(checker_config, api_client)
            task = tg.create_task(checker_instance.get_products())
            tasks.append(task)

    for task in tasks:
        print(task.result())


@app.command()
def run(ctx: typer.Context) -> None:
    """Run the product checkers using the specified config."""
    state: AppState = ctx.obj
    asyncio.run(run_checkers(state.config, state.api_client))


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
