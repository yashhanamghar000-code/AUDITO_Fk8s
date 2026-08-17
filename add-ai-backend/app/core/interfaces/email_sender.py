from abc import ABC, abstractmethod


class IEmailSender(ABC):


    @abstractmethod
    def send(self, to_email: str, to_name: str, subject: str, html_body: str) -> None:
        raise NotImplementedError
