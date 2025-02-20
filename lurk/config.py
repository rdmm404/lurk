import yaml
from pydantic import BaseModel, Field, ConfigDict, model_validator, ValidationError
from typing import Annotated, Literal, Self
from pathlib import Path

from lurk.misc import snake_to_kebab


class BaseConfigModel(BaseModel):
    model_config = ConfigDict(alias_generator=snake_to_kebab, populate_by_name=True)

# TODO: Separate model-specific filters
class SearchFilters(BaseConfigModel):
    model_config = ConfigDict(coerce_numbers_to_str=True)

    min_price: int | None = None
    max_price: int | None = None
    in_stock: bool | None = None
    stores: list[str] | None = None
    zip_code: str | None = None
    categories: list[str] | None = None


class SearchConfig(BaseConfigModel):
    """Global search filters that apply to all checkers unless overridden."""

    query: str
    filters: SearchFilters | None = None
    notify: Literal["availability", "deal"] = "availability"  # TODO
    enabled: bool = True


class CheckerSearchConfig(SearchConfig):
    query: str = ""


class CheckerConfig(BaseConfigModel):
    """Configuration for each individual checker."""

    enabled: bool = True
    search: dict[str, CheckerSearchConfig] = {}


class ClientConfig(BaseConfigModel):
    """HTTP client settings."""

    random_useragent: bool = False  # TODO
    headers: dict[str, str] = {}


class Config(BaseConfigModel):
    """Main configuration model."""

    search: Annotated[dict[str, SearchConfig], Field(min_length=1)]
    checkers: dict[str, CheckerConfig] = {}
    client: Annotated[ClientConfig, Field(default_factory=ClientConfig)]

    @model_validator(mode="after")
    def validate_checkers_search(self) -> Self:
        for checker_name, checker in self.checkers.items():
            for search_id, search_config in checker.search.items():
                if not checker.enabled:
                    continue

                global_search = self.search.get(search_id)

                if not global_search and not search_config.query:
                    raise ValueError(
                        f"Query is required for search '{search_id}' in checker '{checker_name}',"
                        " since this search is not in the global 'search' config."
                    )

        return self

def parse_config(path: Path) -> Config:
    """Load and validate configuration from YAML."""
    with open(path, "r", encoding="utf-8") as file:
        try:
            config_data = yaml.safe_load(file) or {}
            config = Config(**config_data)
        except ValidationError as e:
            raise ValueError(f"Your configuration is not valid. Here is the error:\n{e}")
        return config