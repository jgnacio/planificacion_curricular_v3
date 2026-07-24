import os
from datetime import timedelta

import google.auth
import google.auth.impersonated_credentials
import google.auth.transport.requests
from google.cloud import storage


def _impersonated_credentials(scope: str) -> tuple[google.auth.impersonated_credentials.Credentials, str]:
    """Credenciales impersonadas del SA de GCS.

    Cloud Run corre con ADC sin clave privada, así que no puede firmar URLs por sí
    mismo. Impersonar al SA (que tiene roles/iam.serviceAccountTokenCreator sobre sí
    mismo) devuelve credenciales capaces de firmar.
    """
    sa_email = os.environ["GCS_SERVICE_ACCOUNT_EMAIL"]

    source_credentials, project = google.auth.default()
    source_credentials.refresh(google.auth.transport.requests.Request())

    credentials = google.auth.impersonated_credentials.Credentials(
        source_credentials=source_credentials,
        target_principal=sa_email,
        target_scopes=[scope],
    )
    return credentials, project


def get_signed_read_url(blob_name: str, minutes: int = 60) -> str:
    """Signed URL v4 de lectura para un objeto privado del bucket.

    Se usa para servir los PDFs del currículo oficial al visor del frontend sin
    hacer público el bucket. La expiración larga (1h) evita que el visor pierda
    acceso mientras la docente navega el documento.
    """
    bucket_name = os.environ["GCS_BUCKET_NAME"]
    credentials, project = _impersonated_credentials(
        "https://www.googleapis.com/auth/devstorage.read_only"
    )

    client = storage.Client(credentials=credentials, project=project)
    blob = client.bucket(bucket_name).blob(blob_name)

    return blob.generate_signed_url(
        version="v4",
        expiration=timedelta(minutes=minutes),
        method="GET",
        credentials=credentials,
    )


def get_signed_upload_url(blob_name: str) -> tuple[str, str]:
    """Genera una signed URL v4 PUT para subir un PDF directo a GCS desde el browser.

    Usa self-impersonation porque Cloud Run ADC no puede firmar URLs directamente.
    El SA necesita roles/iam.serviceAccountTokenCreator sobre sí mismo.

    Returns:
        (upload_url, final_url) — upload_url es la signed URL temporal (15 min),
        final_url es la URL pública permanente del objeto en GCS.
    """
    bucket_name = os.environ["GCS_BUCKET_NAME"]

    target_credentials, project = _impersonated_credentials(
        "https://www.googleapis.com/auth/devstorage.read_write"
    )

    client = storage.Client(credentials=target_credentials, project=project)
    blob = client.bucket(bucket_name).blob(blob_name)

    upload_url = blob.generate_signed_url(
        version="v4",
        expiration=timedelta(minutes=15),
        method="PUT",
        content_type="application/pdf",
        credentials=target_credentials,
    )

    final_url = f"https://storage.googleapis.com/{bucket_name}/{blob_name}"
    return upload_url, final_url
