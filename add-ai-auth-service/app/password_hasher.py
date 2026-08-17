from passlib.context import CryptContext

from add_ai_core.interfaces.password_hasher import IPasswordHasher


class BcryptPasswordHasher(IPasswordHasher):

    def __init__(self):
        self._ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")

    def hash(self, plain_password: str) -> str:
        return self._ctx.hash(plain_password)

    def verify(self, plain_password: str, hashed_password: str) -> bool:
        return self._ctx.verify(plain_password, hashed_password)
