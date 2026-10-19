import asyncio
import dataclasses
import threading

from argon2 import PasswordHasher

from app.security.passwords import Hasher

PASSWORD = "correct horse battery"


class ThreadRecordingHasher(PasswordHasher):
    """Real argon2 hashing that also records which thread ran it."""

    def __init__(self) -> None:
        super().__init__()
        self.threads: list[int] = []

    def hash(self, password: str | bytes, *, salt: bytes | None = None) -> str:
        self.threads.append(threading.get_ident())
        return super().hash(password, salt=salt)


class BlockingHasher(PasswordHasher):
    """A stand-in for argon2 that holds every call until released and records the peak number running at once."""

    def __init__(self) -> None:
        super().__init__()
        self.release = threading.Event()
        self.lock = threading.Lock()
        self.running = 0
        self.peak = 0

    def hash(self, password: str | bytes, *, salt: bytes | None = None) -> str:
        with self.lock:
            self.running += 1
            self.peak = max(self.peak, self.running)
        self.release.wait(timeout=5)
        with self.lock:
            self.running -= 1
        return "fake-hash"


async def test_hash_verifies_the_same_password() -> None:
    hasher = await Hasher.owasp(concurrency=4)
    assert await hasher.verify(await hasher.hash(PASSWORD), PASSWORD)


async def test_hash_rejects_another_password() -> None:
    hasher = await Hasher.owasp(concurrency=4)
    assert not await hasher.verify(await hasher.hash(PASSWORD), "wrong horse battery")


async def test_hasher_uses_owasp_parameters() -> None:
    hasher = await Hasher.owasp(concurrency=4)
    password_hash = await hasher.hash(PASSWORD)
    assert password_hash.startswith("$argon2id$v=19$m=19456,t=2,p=1$")


async def test_hashing_runs_off_the_event_loop_thread() -> None:
    recorder = ThreadRecordingHasher()
    await dataclasses.replace(await Hasher.owasp(concurrency=4), hasher=recorder).hash(PASSWORD)
    assert recorder.threads
    assert threading.get_ident() not in recorder.threads


async def test_hashing_never_runs_more_than_four_at_once() -> None:
    blocking = BlockingHasher()
    hasher = dataclasses.replace(await Hasher.owasp(concurrency=4), hasher=blocking)
    async with asyncio.timeout(5), asyncio.TaskGroup() as group:
        for _ in range(10):
            group.create_task(hasher.hash(PASSWORD))
        while blocking.running < 4:
            await asyncio.sleep(0.01)
        # Give any call the gate failed to hold back time to start before releasing them all.
        await asyncio.sleep(0.1)
        blocking.release.set()
    assert blocking.peak == 4
