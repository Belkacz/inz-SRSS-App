from pydantic_settings import BaseSettings, SettingsConfigDict

# klasa ustawień zaczytująca dane z środowiska
class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore"
    )

    #raspberry data 
    WS_SERVER_URL: str
    WS_CAMERA_URL: str
    WS_CARD_URL: str
    
    #databse
    DB_URL: str
    
    #emial
    EMAIL_HOST: str = "smtp.gmail.com"
    EMAIL_PORT: int = 587
    EMAIL_HOST_USER: str = ""
    EMAIL_PASS: str = ""
    RECIPIENT_EMAIL: str = ""

settings = Settings()
