import logging.config
from pathlib import Path
from typing import Literal

import bpy

MODES = Literal["extension", "standalone"]


def configure(mode: MODES = "extension"):
    cfg = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "logfmt": {
                "format": "%(asctime)s level=%(levelname)s logger=%(name)s msg=%(message)s",
                "datefmt": "%Y-%m-%dT%H:%M:%S%z",
            },
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "formatter": "logfmt",
                "level": "INFO",
            },
        },
        "root": {"handlers": ["console"], "level": "INFO"},
    }

    if mode == "extension":
        log_dir_str: str = bpy.utils.user_resource(
            "CONFIG", path="blender_senpai/logs", create=True
        )
        log_dir = Path(log_dir_str)

        cfg["handlers"]["file"] = {
            "class": "logging.handlers.RotatingFileHandler",
            "filename": str(log_dir / "blender_senpai.log"),
            "formatter": "logfmt",
            "level": "DEBUG",
            "encoding": "utf-8",
            "maxBytes": 1_048_576,  # 1 MB
            "backupCount": 5,
        }
        cfg["root"]["handlers"].append("file")

    logging.config.dictConfig(cfg)
