from pydantic import BaseModel, Field, ConfigDict
from typing import Annotated

from lurk.misc import snake_to_kebab
from lurk.models import ProductFilter


class BaseConfigModel(BaseModel):
    model_config = ConfigDict(alias_generator=snake_to_kebab, populate_by_name=True)



class FilterConfig(BaseConfigModel, ProductFilter): ...


class GlobalConfig(BaseConfigModel):
    """Global search filters that apply to all checkers unless overridden."""

    filters: Annotated[FilterConfig, Field(default_factory=FilterConfig)]


class CheckerConfig(BaseConfigModel):
    """Configuration for each individual checker."""

    enabled: bool = True
    filters: FilterConfig | None = None


class ClientConfig(BaseConfigModel):
    """HTTP client settings."""

    random_useragent: bool = False  # TODO
    headers: dict[str, str] = {}


class Config(BaseConfigModel):
    """Main configuration model."""

    global_config: Annotated[GlobalConfig, Field(alias="global")]
    checkers: dict[str, CheckerConfig] = {}
    client: Annotated[ClientConfig, Field(default_factory=ClientConfig)]
