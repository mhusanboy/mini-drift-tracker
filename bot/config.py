from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", extra="ignore", populate_by_name=True
    )

    bot_token: str
    # Kept as a raw string so pydantic-settings does not JSON-decode it (a
    # ``list[int]`` field would try ``json.loads("111,222")`` and crash). The
    # parsed list is exposed via the ``admin_ids`` property below.
    admin_ids_raw: str = Field(default="", validation_alias="ADMIN_IDS")
    db_path: str = "carting.db"

    @property
    def admin_ids(self) -> list[int]:
        return [int(x) for x in self.admin_ids_raw.split(",") if x.strip()]

    def is_admin(self, user_id: int) -> bool:
        return user_id in self.admin_ids


@lru_cache
def get_settings() -> Settings:
    return Settings()
