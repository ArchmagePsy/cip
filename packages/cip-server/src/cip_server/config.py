from pydantic import BaseModel
from pydantic_settings import BaseSettings, SettingsConfigDict, TomlConfigSettingsSource


class DaemonConfig(BaseModel):
    host: str = "127.0.0.1"
    port: int = 3916
    workers: int = 4

    @property
    def channel(self):
        return f"{self.host}:{self.port}"

class DatabaseConfig(BaseModel):
    name: str
    username: str
    password: str
    host: str = "127.0.0.1"
    port: int = 5432

    def url(self, async_db=False):
        if async_db:
            return f"postgresql+asyncpg://{self.username}:{self.password}@{self.host}:{self.port}/{self.name}"
        else:
            return f"postgresql+psycopg2://{self.username}:{self.password}@{self.host}:{self.port}/{self.name}"

class CipServerConfig(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="cip_server_", env_nested_delimiter="__", toml_file="cip-server.toml")

    daemon: DaemonConfig
    database: DatabaseConfig

    @classmethod
    def settings_customise_sources(cls, settings_cls, init_settings, env_settings, dotenv_settings, file_secret_settings):
        TomlConfigSettingsSource
        return init_settings, env_settings, dotenv_settings, TomlConfigSettingsSource(settings_cls), file_secret_settings
    
_config = None

def get_config():
    global _config
    if _config is None:
        _config = CipServerConfig()
        return _config
    else:
        return _config