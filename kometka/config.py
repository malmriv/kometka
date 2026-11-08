"""Settings, read from environment variables."""
import os
import re
from dataclasses import dataclass

SOURCES = ("letterboxd", "rottentomatoes", "imdb")


class ConfigError(Exception):
    pass


def _list(value):
    return tuple(v.strip() for v in value.split(",") if v.strip())


def _secret(name):
    """NAME, or the contents of the file named in NAME_FILE (for Docker secrets)."""
    value = os.environ.get(name, "").strip()
    path = os.environ.get(name + "_FILE", "").strip()
    if not value and path:
        with open(path, encoding="utf-8") as f:
            value = f.read().strip()
    return value


@dataclass
class Config:
    jellyfin_url: str
    jellyfin_api_key: str
    mdblist_api_key: str
    data_dir: str = "/data"
    schedule: str = "05:00"
    run_on_start: bool = True
    sources: tuple = SOURCES
    libraries: tuple = ()
    ratings_max_age_days: int = 7
    letterboxd_scale: int = 5

    @classmethod
    def from_env(cls):
        env = os.environ.get
        cfg = cls(
            jellyfin_url=env("JELLYFIN_URL", "").strip().rstrip("/"),
            jellyfin_api_key=_secret("JELLYFIN_API_KEY"),
            mdblist_api_key=_secret("MDBLIST_API_KEY"),
            data_dir=env("DATA_DIR", "/data"),
            schedule=env("SCHEDULE", "05:00").strip(),
            run_on_start=env("RUN_ON_START", "true").strip().lower() in ("1", "true", "yes"),
            sources=_list(env("SOURCES", ",".join(SOURCES)).lower()),
            libraries=_list(env("LIBRARIES", "")),
            ratings_max_age_days=int(env("RATINGS_MAX_AGE_DAYS", "7")),
            letterboxd_scale=int(env("LETTERBOXD_SCALE", "5")),
        )
        cfg.validate()
        return cfg

    def validate(self):
        missing = [name for name, value in (("JELLYFIN_URL", self.jellyfin_url),
                                            ("JELLYFIN_API_KEY", self.jellyfin_api_key),
                                            ("MDBLIST_API_KEY", self.mdblist_api_key)) if not value]
        if missing:
            raise ConfigError("Missing required setting(s): " + ", ".join(missing))
        if not re.fullmatch(r"([01]\d|2[0-3]):[0-5]\d", self.schedule):
            raise ConfigError("SCHEDULE must be HH:MM, got %r" % self.schedule)
        unknown = [s for s in self.sources if s not in SOURCES]
        if unknown or not self.sources:
            raise ConfigError("SOURCES must be a comma-separated subset of %s" % ",".join(SOURCES))
        if self.letterboxd_scale not in (5, 10):
            raise ConfigError("LETTERBOXD_SCALE must be 5 or 10, got %r" % self.letterboxd_scale)
