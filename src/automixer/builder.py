from automixer.config import InstantiableClassConfig


def _build_nested(value, **global_kwargs):
    if isinstance(value, InstantiableClassConfig):
        return build_from_config(value, **global_kwargs)

    if isinstance(value, list):
        return [_build_nested(item, **global_kwargs) for item in value]

    if isinstance(value, tuple):
        return tuple(_build_nested(item, **global_kwargs) for item in value)

    if isinstance(value, dict):
        return {k: _build_nested(v, **global_kwargs) for k, v in value.items()}

    return value


def build_from_config(
    config: InstantiableClassConfig,
    **global_kwargs
) -> object:
    """
    Build an instance of a class from its configuration.
    Support nested configs.
    """
    # Get the class and arguments from the config
    init_kwargs = dict(config)
    init_kwargs.update(global_kwargs)
    init_kwargs = config.filter_kwargs(init_kwargs)

    for key, value in init_kwargs.items():
        init_kwargs[key] = _build_nested(value, **global_kwargs)

    return config.instantiate(**init_kwargs)
