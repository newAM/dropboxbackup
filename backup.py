#!/usr/bin/env python3.8

from dropbox import Dropbox
from keyring import get_password
from math import ceil
from shutil import make_archive
from socket import gethostname
import argparse
import dropbox
import json
import logging
import logging.handlers
import os


def dropbox_upload(dbx: Dropbox, source_path: str, destination_path: str):
    logger = logging.getLogger(__name__)
    chunk_size = 100 * 1024 * 1024
    file_size = os.path.getsize(source_path)

    num_chunk = ceil(file_size / chunk_size)

    logger.debug(f"archive size: {file_size:,} bytes")

    if file_size <= chunk_size:
        logger.debug("uploading archive")
        with open(source_path, "rb") as f:
            dbx.files_upload(f.read(), destination_path)
    else:
        logger.debug(f"uploading archive in {chunk_size:,} byte chunks")
        with open(source_path, "rb") as f:
            session = dbx.files_upload_session_start(f.read(chunk_size))
            cursor = dropbox.files.UploadSessionCursor(
                session_id=session.session_id, offset=f.tell()
            )
            commit = dropbox.files.CommitInfo(path=destination_path)
            chunk = 1
            while f.tell() < file_size:
                chunk += 1
                logger.debug(f"uploading chunk {chunk}/{num_chunk}")
                if file_size - f.tell() <= chunk_size:
                    dbx.files_upload_session_finish(f.read(chunk_size), cursor, commit)
                else:
                    dbx.files_upload_session_append_v2(f.read(chunk_size), cursor)
                    cursor.offset = f.tell()

    logger.debug("done archive upload")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Uploads folders to Dropbox for backup."
    )
    parser.add_argument("config", help="Configuration file JSON.")
    parser.add_argument(
        "--base",
        default=gethostname(),
        help="Specify the base directory, defaults to the system hostname.",
    )
    args = parser.parse_args()

    logging_dir = "/var/log/dropboxbackup"
    os.makedirs(logging_dir, exist_ok=True)

    root_logger = logging.getLogger()
    formatter = logging.Formatter(
        fmt="[{asctime}] [{name}] [{levelname:<8}] {message}", style="{"
    )
    file_handler = logging.handlers.RotatingFileHandler(
        os.path.join(logging_dir, "log.txt"), maxBytes=256 * 1024, backupCount=10
    )
    file_handler.setFormatter(formatter)
    root_logger.addHandler(file_handler)
    root_logger.setLevel(logging.DEBUG)
    logger = logging.getLogger(__name__)

    with open(args.config, "r") as f:
        config = json.load(f)

    assert isinstance(config, list)
    for backup in config:
        assert isinstance(backup, dict)
        assert "path" in backup
        assert "name" in backup
        assert isinstance(backup["path"], str)
        assert isinstance(backup["name"], str)

    token = get_password("dropbox", "token")
    dbx = Dropbox(token)

    backup_tmp = os.path.join("/tmp", "bup")
    os.makedirs(backup_tmp, exist_ok=True)

    for backup in config:
        name = backup["name"]
        path = backup["path"]
        archive_path = os.path.join(backup_tmp, name)
        logger.info(f"archiving {name}")
        make_archive(
            archive_path, format="zip", base_dir=path,
        )
        logger.info(f"done archiving {name}")
        archive_path += ".zip"

        dropbox_upload(dbx, archive_path, f"/{args.base}/{name}.zip")

        logger.debug("removing archive {name}")
        os.remove(archive_path)
