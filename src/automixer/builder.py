from automixer.config import InstantiableClassConfig


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
        if isinstance(value, InstantiableClassConfig):
            init_kwargs[key] = build_from_config(value, **global_kwargs)

    return config.instantiate(**init_kwargs)
