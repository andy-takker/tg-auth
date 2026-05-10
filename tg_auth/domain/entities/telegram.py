from dataclasses import dataclass


@dataclass(frozen=True, slots=True, kw_only=True)
class TelegramAuthDTO:
    id_token: str
