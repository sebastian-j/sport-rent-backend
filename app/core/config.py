import datetime
import os
from dataclasses import dataclass


def _required_environment_variable(name: str) -> str:
    value = os.getenv(name)

    if value is None or not value:
        raise ValueError(f"{name} must be set")

    return value


def _positive_integer(name: str, default: int | None = None) -> int:
    raw_value = os.getenv(name)

    if raw_value is None:
        if default is None:
            raise ValueError(f"{name} must be set")

        value = default
    else:
        try:
            value = int(raw_value)
        except ValueError:
            raise ValueError(f"{name} must be an integer") from None

    if value <= 0:
        raise ValueError(f"{name} must be greater than zero")

    return value


def _boolean(name: str, default: bool) -> bool:
    raw_value = os.getenv(name)

    if raw_value is None:
        return default

    normalized_value = raw_value.strip().casefold()

    if normalized_value in {"1", "true", "yes", "on"}:
        return True

    if normalized_value in {"0", "false", "no", "off"}:
        return False

    raise ValueError(f"{name} must be a boolean")


def _non_empty_string(name: str, default: str) -> str:
    value = os.getenv(name, default).strip()

    if not value:
        raise ValueError(f"{name} must not be empty")

    return value


@dataclass(frozen=True, slots=True)
class Settings:
    allowed_origins: tuple[str, ...]
    database_url: str
    jwt_access_secret: str
    jwt_access_expiration: int
    jwt_refresh_secret: str
    jwt_refresh_expiration: int
    jwt_issuer: str
    jwt_audience: str
    refresh_token_grace_period: datetime.timedelta
    auth_cookie_secure: bool
    seed_user_password: str | None

    @classmethod
    def from_environment(cls) -> Settings:
        access_secret = _required_environment_variable("JWT_ACCESS_SECRET")
        refresh_secret = _required_environment_variable("JWT_REFRESH_SECRET")

        if len(access_secret) < 32:
            raise ValueError("JWT_ACCESS_SECRET must be at least 32 characters long")

        if len(refresh_secret) < 32:
            raise ValueError("JWT_REFRESH_SECRET must be at least 32 characters long")

        allowed_origins = tuple(
            origin.strip()
            for origin in os.getenv("ALLOWED_ORIGINS", "").split(",")
            if origin.strip()
        )

        return cls(
            allowed_origins=allowed_origins,
            database_url=_required_environment_variable("DATABASE_URL"),
            jwt_access_secret=access_secret,
            jwt_access_expiration=_positive_integer("JWT_ACCESS_EXPIRATION"),
            jwt_refresh_secret=refresh_secret,
            jwt_refresh_expiration=_positive_integer("JWT_REFRESH_EXPIRATION"),
            jwt_issuer=_non_empty_string(
                "JWT_ISSUER",
                "sport-rent-backend",
            ),
            jwt_audience=_non_empty_string(
                "JWT_AUDIENCE",
                "sport-rent-backend",
            ),
            refresh_token_grace_period=datetime.timedelta(
                seconds=_positive_integer("JWT_REFRESH_GRACE_PERIOD", default=5)
            ),
            auth_cookie_secure=_boolean("AUTH_COOKIE_SECURE", default=True),
            seed_user_password=os.getenv("SEED_USER_PASSWORD"),
        )

    def require_seed_user_password(self) -> str:
        if self.seed_user_password is None:
            raise ValueError("SEED_USER_PASSWORD must be set to run the seed script")

        return self.seed_user_password


settings = Settings.from_environment()
