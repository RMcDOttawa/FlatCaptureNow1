import functools

display_trace_log: bool = True


def tracelog(func):
    """Print the function signature and return value"""

    @functools.wraps(func)
    def wrapper_debug(*args, **kwargs):
        if display_trace_log:
            args_repr = [repr(a) for a in args]  # 1
            kwargs_repr = [f"{k}={v!r}" for k, v in kwargs.items()]  # 2
            signature = ", ".join(args_repr + kwargs_repr)  # 3
            print(f"Calling {func.__name__}({signature})")
        value = func(*args, **kwargs)
        if display_trace_log:
            print(f"{func.__name__!r} returned {value!r}")  # 4
        return value

    return wrapper_debug
