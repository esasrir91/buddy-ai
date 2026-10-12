from pathlib import Path


def load_env(env: dict[str, str] | None = None, dotenv_dir: Path | None = None) -> None:
    from os import environ

    if dotenv_dir is not None:
        dotenv_file = dotenv_dir.joinpath(".env")
        if dotenv_file.exists() and dotenv_file.is_file():
            from dotenv.main import dotenv_values

            dotenv_dict: dict[str, str | None] = dotenv_values(dotenv_file)
            for key, value in dotenv_dict.items():
                if value is not None:
                    environ[key] = value

    if env is not None:
        environ.update(env)
