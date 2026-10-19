"""Hash and check passwords with argon2id, off the event loop and a few at a time."""

import asyncio
import secrets
from dataclasses import dataclass
from typing import Final, Self

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError

HASH_CONCURRENCY: Final = 4


@dataclass(frozen=True)
class Hasher:
    """argon2id behind a semaphore, run on worker threads so the event loop keeps serving requests.

    `dummy_hash` is the hash of a random value nobody keeps, made by this same hasher, so checking a
    password against it costs exactly what a real check costs.
    """

    hasher: PasswordHasher
    gate: asyncio.Semaphore
    dummy_hash: str

    @classmethod
    async def owasp(cls, concurrency: int) -> Self:
        """Build a hasher with OWASP's argon2id minimum that runs at most `concurrency` hashes at once.

        The minimum is 19 MiB of memory, 2 passes and 1 lane:
        https://cheatsheetseries.owasp.org/cheatsheets/Password_Storage_Cheat_Sheet.html#argon2id
        """
        hasher = PasswordHasher(time_cost=2, memory_cost=19456, parallelism=1)
        dummy_hash = await asyncio.to_thread(hasher.hash, secrets.token_urlsafe(32))
        return cls(hasher, asyncio.Semaphore(concurrency), dummy_hash)

    async def hash(self, password: str) -> str:
        """Return the encoded argon2id hash of a password."""
        async with self.gate:
            return await asyncio.to_thread(self.hasher.hash, password)

    async def verify(self, password_hash: str, password: str) -> bool:
        """Return whether the password matches the stored hash."""
        async with self.gate:
            try:
                return await asyncio.to_thread(self.hasher.verify, password_hash, password)
            except VerifyMismatchError:
                return False

    async def verify_without_an_account(self, password: str) -> None:
        """Spend the time of one real check, so a missing account answers as slowly as a wrong password."""
        await self.verify(self.dummy_hash, password)
