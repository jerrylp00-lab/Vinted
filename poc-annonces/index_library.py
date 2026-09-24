"""Script d'indexation de la bibliothèque Drive — à relancer manuellement
après avoir ajouté de nouvelles photos.

Usage :
    python index_library.py
"""

from __future__ import annotations

import os

from dotenv import load_dotenv

from drive_client import build_drive_service
from library import index_library, save_index

load_dotenv()


def main() -> None:
    root_folder_id = os.environ["GOOGLE_DRIVE_ROOT_FOLDER_ID"]
    service = build_drive_service()
    entries = index_library(service, root_folder_id)
    save_index(entries)
    print(f"{len(entries)} photo(s) indexée(s) -> decor_index.json")


if __name__ == "__main__":
    main()
