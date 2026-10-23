import logging

# O SDK do Azure loga cada requisicao HTTP (headers, 404 de "blob nao existe" que o
# codigo ja trata, etc.) em nivel INFO. Isso afogava os logs do pipeline. Aqui
# silenciamos so o SDK; os logs do proprio pipeline continuam no nivel do settings.json.
logging.getLogger("azure").setLevel(logging.WARNING)
