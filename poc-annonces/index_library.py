"""Script d'indexation de la bibliothèque Drive — à relancer manuellement
après avoir ajouté de nouvelles photos.

Usage :
    python index_library.py
"""

from __future__ import annotations

import os

from dotenv import load_dotenv
from google.oauth2 import service_account
from googleapiclient.discovery import build

from library import index_library, save_index

load_dotenv()

SCOPES = ["https://www.googleapis.com/auth/drive.readonly"]


def build_drive_service():
    credentials_path = os.environ["GOOGLE_SERVICE_ACCOUNT_FILE"]
    creds = service_account.Credentials.from_service_account_file(credentials_path, scopes=SCOPES)
    return build("drive", "v3", credentials=creds, cache_discovery=False)


def main() -> None:
    root_folder_id = os.environ["GOOGLE_DRIVE_ROOT_FOLDER_ID"]
    service = build_drive_service()
    entries = index_library(service, root_folder_id)
    save_index(entries)
    print(f"{len(entries)} photo(s) indexée(s) -> decor_index.json")


if __name__ == "__main__":
    main()
