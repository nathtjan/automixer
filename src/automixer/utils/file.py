import os
import re
import yaml


# Matches Docker Compose-style variable expressions:
#   $$                      → literal $
#   ${VAR}                  → value of VAR, empty string if unset
#   ${VAR:-default}         → value of VAR, or default if unset/empty
#   ${VAR-default}          → value of VAR, or default if unset (not if empty)
#   ${VAR:?error message}   → value of VAR, or raise error if unset/empty
#   ${VAR?error message}    → value of VAR, or raise error if unset
#   $VAR                    → value of VAR, empty string if unset
_ENV_VAR_RE = re.compile(
    r"\$\$"                                         # escaped $$
    r"|\$\{(?P<braced>[^}:?][^}:?]*)(?::?(?P<op>[?-])(?P<modifier>[^}]*))?\}"  # ${VAR...}
    r"|\$(?P<bare>[A-Za-z_][A-Za-z0-9_]*)"         # $VAR
)

def _substitute_env_vars(text: str) -> str:
    """Substitute environment variables in *text* using Docker Compose syntax."""
    def replace(match: re.Match) -> str:
        if match.group() == "$$":
            return "$"

        if (var_name := match.group("bare")) is not None:
            return os.environ.get(var_name, "")

        var_name = match.group("braced")
        op = match.group("op")       # '-' or '?', may be None
        modifier = match.group("modifier") or ""
        raw_op = match.group(0)      # for error context

        value = os.environ.get(var_name)
        is_empty = value == ""

        if op is None:
            return value if value is not None else ""

        colon_prefix = ":?" in raw_op or ":-" in raw_op

        if op == "-":
            # ${VAR:-default} → use default if unset OR empty
            # ${VAR-default}  → use default only if unset
            if value is None or (colon_prefix and is_empty):
                return modifier
            return value

        if op == "?":
            # ${VAR:?msg} → error if unset OR empty
            # ${VAR?msg}  → error if unset
            if value is None or (colon_prefix and is_empty):
                msg = modifier or f"environment variable '{var_name}' is not set"
                raise ValueError(msg)
            return value

        return value if value is not None else ""

    return _ENV_VAR_RE.sub(replace, text)


def load_yaml(config_path: str, encoding: str = "utf-8", sub_env: bool = True) -> dict:
    """
    Load a YAML configuration file with environment variable
    substitution and return it as a dictionary.
    """

    with open(config_path, "r", encoding=encoding) as f:
        raw = f.read()

    if sub_env:
        raw = _substitute_env_vars(raw)

    config = yaml.safe_load(raw)

    return config


__all__ = ["load_yaml"]
