import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    # PostgreSQL
    DB_USER = os.getenv("DB_USER", "postgres")
    DB_PASSWORD = os.getenv("DB_PASSWORD", "tu_nueva_contraseña")
    DB_HOST = os.getenv("DB_HOST", "localhost")
    DB_PORT = os.getenv("DB_PORT", "5432")
    DB_NAME = os.getenv("DB_NAME", "tiendatecnologia")

    # SQLAlchemy
    # Se mantiene la URI en un solo lugar para evitar
    # configuraciones diferentes entre archivos.
    SQLALCHEMY_DATABASE_URI = (
        f"postgresql://{DB_USER}:{DB_PASSWORD}@"
        f"{DB_HOST}:{DB_PORT}/{DB_NAME}"
    )

    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Flask
    SECRET_KEY = os.getenv(
        "SECRET_KEY",
        "tiendatecnologia_secret_key"
    )
