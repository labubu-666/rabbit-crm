from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", env_prefix="RABBIT_CMS_"
    )

    admin_username: str = ""
    admin_password: str = ""
    language_code: str = "en"
    working_directory: str = "."
