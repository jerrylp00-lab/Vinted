"""PoC-2 : construction du client Google Drive (service account).

Accepte soit un chemin vers le fichier JSON (GOOGLE_SERVICE_ACCOUNT_FILE,
pratique en local), soit le JSON inline en variable d'environnement
(GOOGLE_SERVICE_ACCOUNT_JSON, pratique avec un secret manager de
plateforme de déploiement qui n'expose pas de fichier sur disque).
"""

from __future__ import annotations

import json
import os

from google.oauth2 import service_account
from googleapiclient.discovery import build

SCOPES = ["https://www.googleapis.com/auth/drive.readonly"]


def build_drive_service():
    inline_json = os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON")
    if inline_json:
        info = json.loads(inline_json)
        creds = service_account.Credentials.from_service_account_info(info, scopes=SCOPES)
    else:
        credentials_path = os.environ["GOOGLE_SERVICE_ACCOUNT_FILE"]
        creds = service_account.Credentials.from_service_account_file(credentials_path, scopes=SCOPES)
    return build("drive", "v3", credentials=creds, cache_discovery=False)
