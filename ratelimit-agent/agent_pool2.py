import queue
import threading
from contextlib import AbstractContextManager, contextmanager
from typing import TypeVar, Callable

T = TypeVar("T")

class ObjectPool:
    def __init__(self,create_func:Callable[[],T],  max_size:int=5):
        self.create_func = create_func
        self.max_size = max_size
        self._pool = queue.Queue(maxsize=max_size)
        for _ in range(max_size):
            self._pool.put(create_func())

    def get(self, timeout = None) -> T:
        try:
            obj = self._pool.get_nowait()
            return obj
        except queue.Empty:
            return None

    def put(self,obj:T):
        if obj:
            try:
                self._pool.put_nowait(obj)
            except queue.Full:
                pass

    @contextmanager
    def acquire(self, timeout = None) -> T:
        obj = self.get(timeout=timeout)
        try:
            yield obj
        finally:
            self.put(obj)