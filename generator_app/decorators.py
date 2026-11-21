"""Dekoratory funkcji i metod używane w generatorze i walidatorze danych."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError
import functools
import time
from typing import Any, Callable, ParamSpec, TypeVar

P = ParamSpec("P")
R = TypeVar("R")

"""Dekorator z parametrami ponawiający wywołanie funkcji przy wskazanych wyjątkach."""
def retry_call(
    attempts: int = 3,
    delay: float = 0.05,
    exceptions: tuple[type[BaseException], ...] = (Exception,),
) -> Callable[[Callable[P, R]], Callable[P, R]]:
    if attempts < 1:
        raise ValueError("attempts musi być >= 1")
    if delay < 0:
        raise ValueError("delay nie może być ujemne")

    def decorator(func: Callable[P, R]) -> Callable[P, R]:
        @functools.wraps(func)
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            last_error: BaseException | None = None
            for attempt in range(1, attempts + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as exc:
                    last_error = exc
                    if attempt < attempts and delay > 0:
                        time.sleep(delay)
            assert last_error is not None
            raise last_error

        return wrapper

    return decorator

"""Dekorator z parametrem ograniczający czas wykonania funkcji."""
def time_limit(seconds: float) -> Callable[[Callable[P, R]], Callable[P, R]]:
    if seconds <= 0:
        raise ValueError("seconds musi być > 0")

    def decorator(func: Callable[P, R]) -> Callable[P, R]:
        @functools.wraps(func)
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            with ThreadPoolExecutor(max_workers=1) as pool:
                future = pool.submit(func, *args, **kwargs)
                try:
                    return future.result(timeout=seconds)
                except FuturesTimeoutError as exc:
                    raise TimeoutError(
                        f"Przekroczono limit {seconds:.2f} s w {func.__qualname__}"
                    ) from exc

        return wrapper

    return decorator

"""Dekorator metody korzystający z atrybutów instancji (self)."""
def require_active_config(method: Callable[..., Any]) -> Callable[..., Any]:
    @functools.wraps(method)
    def wrapper(self: Any, *args: Any, **kwargs: Any) -> Any:
        if getattr(self, "locked", False):
            raise RuntimeError(f"Konfiguracja {type(self).__name__} jest zablokowana do zmian")
        return method(self, *args, **kwargs)
    return wrapper