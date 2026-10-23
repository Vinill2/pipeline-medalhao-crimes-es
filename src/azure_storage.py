import os
from pathlib import Path

from azure.core.exceptions import ResourceNotFoundError
from azure.storage.blob import BlobServiceClient

from src.settings import get_project_path


def get_connection_string(settings: dict) -> str:
    env_var_name = settings["azure"]["connection_string_env_var"]
    connection_string = os.environ.get(env_var_name)
    if not connection_string:
        raise RuntimeError(
            f"Variavel de ambiente {env_var_name} nao encontrada. "
            "Defina a connection string da Storage Account antes de rodar o pipeline."
        )
    return connection_string


def get_blob_service_client(settings: dict) -> BlobServiceClient:
    connection_string = get_connection_string(settings)
    blob_service_client = BlobServiceClient.from_connection_string(connection_string)
    return blob_service_client


def upload_file(local_path: Path, container_name: str, blob_name: str, settings: dict) -> None:
    blob_service_client = get_blob_service_client(settings)
    blob_client = blob_service_client.get_blob_client(container=container_name, blob=blob_name)
    with open(local_path, "rb") as local_file:
        blob_client.upload_blob(local_file, overwrite=True, timeout=600, connection_timeout=600)


def download_file(container_name: str, blob_name: str, local_path: Path, settings: dict) -> Path:
    blob_service_client = get_blob_service_client(settings)
    blob_client = blob_service_client.get_blob_client(container=container_name, blob=blob_name)
    local_path.parent.mkdir(parents=True, exist_ok=True)
    with open(local_path, "wb") as local_file:
        download_stream = blob_client.download_blob()
        local_file.write(download_stream.readall())
    return local_path


def blob_exists(container_name: str, blob_name: str, settings: dict) -> bool:
    blob_service_client = get_blob_service_client(settings)
    blob_client = blob_service_client.get_blob_client(container=container_name, blob=blob_name)
    return blob_client.exists()


def try_download_file(container_name: str, blob_name: str, local_path: Path, settings: dict) -> bool:
    try:
        download_file(container_name, blob_name, local_path, settings)
        was_downloaded = True
    except ResourceNotFoundError:
        was_downloaded = False
    return was_downloaded


def list_blob_names(container_name: str, prefix: str, settings: dict) -> list:
    blob_service_client = get_blob_service_client(settings)
    container_client = blob_service_client.get_container_client(container_name)
    blob_names = [blob.name for blob in container_client.list_blobs(name_starts_with=prefix)]
    return blob_names


def get_work_path(relative_path: str, settings: dict) -> Path:
    work_directory = get_project_path(settings["paths"]["work_directory"])
    work_path = work_directory / relative_path
    return work_path
