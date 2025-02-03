from pydantic import BaseModel, Field, ConfigDict
from typing import Annotated

from lurk.misc import snake_to_kebab


class BaseConfigModel(BaseModel):
    model_config = ConfigDict(alias_generator=snake_to_kebab, populate_by_name=True)



class FilterConfig(BaseConfigModel):
    min_price: int | None = None
    max_price: int | None = None
    in_stock: bool | None = None
    stores: list[str] | None = None
    zip_code: str | None = None
    region: str | None = None
    language: str | None = None
    categories: list[str] | None = None


class GlobalConfig(BaseConfigModel):
    """Global search filters that apply to all checkers unless overridden."""

    search: Annotated[list[str], Field(min_length=1)]
    filters: Annotated[FilterConfig, Field(default_factory=FilterConfig)]


class CheckerConfig(BaseConfigModel):
    """Configuration for each individual checker."""

    enabled: bool = True
    search: Annotated[list[str], Field(min_length=1)]
    filters: Annotated[FilterConfig, Field(default_factory=FilterConfig)]


class ClientConfig(BaseConfigModel):
    """HTTP client settings."""

    random_useragent: bool = False  # TODO
    headers: dict[str, str] = {}


class Config(BaseConfigModel):
    """Main configuration model."""

    global_config: Annotated[GlobalConfig, Field(alias="global")]
    checkers: dict[str, CheckerConfig] = {}
    client: Annotated[ClientConfig, Field(default_factory=ClientConfig)]
