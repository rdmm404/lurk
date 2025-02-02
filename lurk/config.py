from pydantic import BaseModel, Field, ConfigDict
from typing import Annotated

from lurk.misc import snake_to_kebab
from lurk.models import ProductFilter


class KebabCaseAliasedModel(BaseModel):
    model_config = ConfigDict(alias_generator=snake_to_kebab)


class FilterConfig(KebabCaseAliasedModel, ProductFilter): ...


class GlobalConfig(KebabCaseAliasedModel):
    """Global search filters that apply to all checkers unless overridden."""

    filters: Annotated[FilterConfig, Field(default_factory=FilterConfig)]


class CheckerConfig(KebabCaseAliasedModel):
    """Configuration for each individual checker."""

    enabled: bool = True
    filters: FilterConfig | None = None


class ClientConfig(KebabCaseAliasedModel):
    """HTTP client settings."""

    random_useragent: bool = False  # TODO
    headers: dict[str, str] = {
        "Cache-Control": "no-cache",
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/131.0.0.0 Safari/537.36",
    }


class Config(KebabCaseAliasedModel):
    """Main configuration model."""

    global_config: Annotated[GlobalConfig, Field(alias="global")]
    checkers: dict[str, CheckerConfig] = {}
    client: ClientConfig
