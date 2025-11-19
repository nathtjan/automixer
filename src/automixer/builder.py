import inspect
from automixer.config import InstatiableClassConfig


def build_from_config(
    config: InstatiableClassConfig,
    **global_kwargs
) -> object:
    """
    Build an instance of a class from its configuration.
    Support nested configs.
    """
    # Get the class and arguments from the config
    cls = config.get_class()
    init_kwargs = {k: v for k, v in config}

    init_kwargs.update(global_kwargs)

    # Filter kwargs to only those accepted by the class constructor
    sig = inspect.signature(cls.__init__)
    param_names = set(sig.parameters.keys()) - {"self"}
    init_kwargs = {k: v for k, v in init_kwargs.items() if k in param_names}

    for key, value in init_kwargs.items():
        if isinstance(value, InstatiableClassConfig):
            init_kwargs[key] = build_from_config(value, **global_kwargs)

    return cls(**init_kwargs)
