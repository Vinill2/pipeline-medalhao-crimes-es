from azure.core.exceptions import ResourceNotFoundError

from src.azure_storage import get_blob_service_client


def get_blob_last_modified(container_name: str, blob_name: str, settings: dict):
    """Data de modificacao do blob segundo o proprio Azure, ou None se o blob nao existe."""
    blob_service_client = get_blob_service_client(settings)
    blob_client = blob_service_client.get_blob_client(container=container_name, blob=blob_name)
    try:
        blob_properties = blob_client.get_blob_properties()
    except ResourceNotFoundError:
        return None
    return blob_properties.last_modified


def is_derived_up_to_date(source_last_modified, derived_last_modified) -> bool:
    # Um arquivo derivado esta em dia se existe e foi gerado depois (ou junto) da origem.
    # As duas datas vem do Azure, entao nao ha problema de fuso/relogio entre maquinas.
    if source_last_modified is None or derived_last_modified is None:
        return False
    return derived_last_modified >= source_last_modified
