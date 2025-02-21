def snake_to_kebab(s: str) -> str:
    return s.replace("_", "-")


class InvalidConfigException(Exception): ...