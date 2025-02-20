import asyncio
import typer

from pathlib import Path
from typing import Annotated
from dataclasses import dataclass
from rich import print

from lurk.config import Config, parse_config
from lurk.lurk import Lurk

app = typer.Typer(no_args_is_help=True)


@dataclass
class AppState:
    config: Config


@app.command()
def run(ctx: typer.Context) -> None:
    """Run the product checkers using the specified config."""
    state: AppState = ctx.obj
    lurk_app = Lurk(state.config)
    asyncio.run(lurk_app.run())

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
    cfg = parse_config(config)
    ctx.obj = AppState(config=cfg)


if __name__ == "__main__":
    app()
