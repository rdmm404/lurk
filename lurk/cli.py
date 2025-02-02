import asyncio
import typer
import yaml

from pathlib import Path
from typing import Annotated
from pydantic import ValidationError, BaseModel
from rich import print

from lurk.config import Config, CheckerConfig
from lurk.checkers import best_buy, checker
from lurk.models import Product

app = typer.Typer(no_args_is_help=True)

AVAILABLE_CHECKERS: dict[str, type[checker.Checker]] = {
    "best-buy": best_buy.BestBuyChecker,
}

class AppState(BaseModel):
    config: Config


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


async def run_checkers(config: Config) -> None:
    """Run the enabled checkers with merged global parameters."""
    tasks: list[asyncio.Task[list[Product]]] = []

    for c in AVAILABLE_CHECKERS:
        if c in config.checkers:
            continue

        config.checkers[c] = CheckerConfig(filters=config.global_config.filters)

    for checker_name, checker_config in config.checkers.items():
        if not checker_config.enabled:
            print(f"Skipping disabled checker: {checker_name}")
            continue

        checker_cls = AVAILABLE_CHECKERS.get(checker_name)
        if not checker_cls:
            raise typer.BadParameter(f"Checker does not exist: {checker_name}")

        if not checker_config.filters:
            checker_config.filters = config.global_config.filters

        checker = checker_cls(config)
        async with checker:
            task: asyncio.Task[list[Product]] = asyncio.create_task(
                checker.get_products(checker_config.filters)
            )
            tasks.append(task)

    results: list[list[Product]] = await asyncio.gather(*tasks)
    for result in results:
        print(result)


@app.command()
def run(ctx: typer.Context) -> None:
    """Run the product checkers using the specified config."""
    state: AppState = ctx.obj
    asyncio.run(run_checkers(state.config))

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
    ctx.obj = AppState(config=cfg)

if __name__ == "__main__":
    app()
