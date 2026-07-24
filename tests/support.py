from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class SeededUser:
    id: int
    email: str
    password: str
