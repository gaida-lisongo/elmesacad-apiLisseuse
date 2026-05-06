from functools import lru_cache

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    mongo_uri: str = Field(
        validation_alias=AliasChoices("MONGO_URI", "MONGODB_URI"),
    )
    mongo_db_name: str | None = Field(default=None, alias="MONGO_DB_NAME")

    cloudinary_cloud_name: str = Field(
        validation_alias=AliasChoices(
            "CLOUDINARY_CLOUD_NAME",
            "CLOUDINARY_NAME",
        ),
    )
    cloudinary_api_key: str = Field(alias="CLOUDINARY_API_KEY")
    cloudinary_secret_key: str = Field(alias="CLOUDINARY_SECRET_KEY")
    cloudinary_upload_preset: str | None = Field(
        default=None,
        alias="CLOUDINARY_PRESET",
        description="Preset optionnel (uploads non signés côté client) ; l’API utilise la signature serveur.",
    )
    cloudinary_folder: str | None = Field(default=None, alias="CLOUDINARY_FOLDER")

    cors_github_pages_origin: str | None = Field(
        default=None,
        alias="CORS_GITHUB_PAGES_ORIGIN",
        description="Ex: https://owner.github.io/repo/",
    )
    cors_extra_origins: str = Field(
        default="",
        alias="CORS_EXTRA_ORIGINS",
        description="Liste séparée par des virgules.",
    )

    credits_per_progress_update: float = Field(
        default=1.15,
        alias="CREDITS_PER_PROGRESS_UPDATE",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()

