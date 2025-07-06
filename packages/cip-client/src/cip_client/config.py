from pydantic_settings import BaseSettings, SettingsConfigDict, TomlConfigSettingsSource


class CipClientConfig(BaseSettings):

    model_config = SettingsConfigDict(env_prefix="cip_client_", env_nested_delimiter="__", toml_file="cip-client.toml")

    api_url: str
    git_server_url: str
    
    @classmethod
    def settings_customise_sources(cls, settings_cls, init_settings, env_settings, dotenv_settings, file_secret_settings):
        return init_settings, env_settings, dotenv_settings, TomlConfigSettingsSource(settings_cls), file_secret_settings
    
_config = None

def get_config():
    global _config
    if _config is None:
        _config = CipClientConfig()
        return _config
    else:
        return _config