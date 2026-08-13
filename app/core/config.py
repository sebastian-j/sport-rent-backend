from __future__ import annotations

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
    csrf_expiration: int
    auth_cookie_secure: bool
    frontend_url: str
    password_reset_expiration: int
    password_reset_email_rate_limit: int
    password_reset_ip_rate_limit: int
    password_reset_rate_limit_window: int
    password_reset_min_response_time_ms: int
    smtp_host: str
    smtp_port: int
    smtp_username: str
    smtp_password: str
    smtp_from_email: str
    smtp_use_tls: bool
    smtp_use_auth: bool
    seed_user_password: str | None

    @classmethod
    def from_environment(cls) -> Settings:
        access_secret = _required_environment_variable("JWT_ACCESS_SECRET")
        refresh_secret = _required_environment_variable("JWT_REFRESH_SECRET")

        if len(access_secret) < 32:
            raise ValueError("JWT_ACCESS_SECRET must be at least 32 characters long")

        if len(refresh_secret) < 32:
            raise ValueError("JWT_REFRESH_SECRET must be at least 32 characters long")

        refresh_expiration = _positive_integer("JWT_REFRESH_EXPIRATION")

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
            jwt_refresh_expiration=refresh_expiration,
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
            csrf_expiration=_positive_integer(
                "CSRF_EXPIRATION",
                default=refresh_expiration,
            ),
            auth_cookie_secure=_boolean("AUTH_COOKIE_SECURE", default=True),
            frontend_url=_non_empty_string(
                "FRONTEND_URL",
                "http://127.0.0.1:5173",
            ).rstrip("/"),
            password_reset_expiration=_positive_integer(
                "PASSWORD_RESET_EXPIRATION",
                default=1800,
            ),
            password_reset_email_rate_limit=_positive_integer(
                "PASSWORD_RESET_EMAIL_RATE_LIMIT",
                default=5,
            ),
            password_reset_ip_rate_limit=_positive_integer(
                "PASSWORD_RESET_IP_RATE_LIMIT",
                default=20,
            ),
            password_reset_rate_limit_window=_positive_integer(
                "PASSWORD_RESET_RATE_LIMIT_WINDOW",
                default=900,
            ),
            password_reset_min_response_time_ms=_positive_integer(
                "PASSWORD_RESET_MIN_RESPONSE_TIME_MS",
                default=300,
            ),
            smtp_host=_required_environment_variable("SMTP_HOST"),
            smtp_port=_positive_integer("SMTP_PORT", default=587),
            smtp_username=_required_environment_variable("SMTP_USERNAME"),
            smtp_password=_required_environment_variable("SMTP_PASSWORD"),
            smtp_from_email=_required_environment_variable("SMTP_FROM_EMAIL"),
            smtp_use_tls=_boolean("SMTP_USE_TLS", default=True),
            smtp_use_auth=_boolean("SMTP_USE_AUTH", default=True),
            seed_user_password=os.getenv("SEED_USER_PASSWORD"),
        )

    def require_seed_user_password(self) -> str:
        if self.seed_user_password is None:
            raise ValueError("SEED_USER_PASSWORD must be set to run the seed script")

        return self.seed_user_password


settings = Settings.from_environment()
