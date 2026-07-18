import os

from mem0.utils.aws_rds_iam import generate_rds_iam_auth_token, rds_iam_auth_enabled
from sqlalchemy import URL, create_engine, event
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker


RDS_IAM_AUTH = rds_iam_auth_enabled()


def _build_database_url() -> str:
    host = os.environ.get("POSTGRES_HOST", "postgres")
    port = os.environ.get("POSTGRES_PORT", "5432")
    user = os.environ.get("POSTGRES_USER", "postgres")
    password = None if RDS_IAM_AUTH else os.environ.get("POSTGRES_PASSWORD", "postgres")
    db = os.environ.get("APP_DB_NAME", "mem0_app")
    return URL.create(
        "postgresql+psycopg",
        username=user,
        password=password,
        host=host,
        port=int(port),
        database=db,
        query={"sslmode": os.environ.get("POSTGRES_SSLMODE", "require")},
    ).render_as_string(hide_password=False)


def _create_engine():
    engine = create_engine(_build_database_url(), pool_pre_ping=True, pool_recycle=840)

    if RDS_IAM_AUTH:
        host = os.environ.get("POSTGRES_HOST", "postgres")
        port = int(os.environ.get("POSTGRES_PORT", "5432"))
        user = os.environ.get("POSTGRES_USER", "postgres")
        region = os.environ.get("AWS_REGION")

        @event.listens_for(engine, "do_connect")
        def _inject_fresh_iam_token(dialect, conn_rec, cargs, cparams):
            del dialect, conn_rec, cargs
            cparams["password"] = generate_rds_iam_auth_token(host, port, user, region)

    return engine


engine = _create_engine()

SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


def get_db():
    """FastAPI dependency that yields a SQLAlchemy session."""
    db: Session = SessionLocal()
    try:
        yield db
    finally:
        db.close()
