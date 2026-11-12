from abc import ABC, abstractmethod


class IEmailVerifier(ABC):


    @abstractmethod
    def is_real(self, email: str) -> bool:
        
        raise NotImplementedError
