#!/usr/bin/env python3.8

from dropbox import Dropbox
from keyring import get_password
from shutil import make_archive
from socket import gethostname
import argparse
import dropbox
import json
import os


def dropbox_upload(dbx: Dropbox, source_path: str, destination_path: str):
    chunk_size = 100 * 1024 * 1024
    file_size = os.path.getsize(source_path)

    if file_size <= chunk_size:
        with open(source_path, "rb") as f:
            dbx.files_upload(f.read(), destination_path)
    else:
        with open(source_path, "rb") as f:
            session = dbx.files_upload_session_start(f.read(chunk_size))
            cursor = dropbox.files.UploadSessionCursor(
                session_id=session.session_id, offset=f.tell()
            )
            commit = dropbox.files.CommitInfo(path=destination_path)
            while f.tell() < file_size:
                if file_size - f.tell() <= chunk_size:
                    dbx.files_upload_session_finish(f.read(chunk_size), cursor, commit)
                else:
                    dbx.files_upload_session_append_v2(
                        f.read(chunk_size), cursor.session_id, cursor.offset
                    )
                    cursor.offset = f.tell()


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
        make_archive(
            archive_path, format="zip", base_dir=path,
        )
        archive_path += ".zip"

        dropbox_upload(dbx, archive_path, f"/{args.base}/{name}.zip")

        os.remove(archive_path)
