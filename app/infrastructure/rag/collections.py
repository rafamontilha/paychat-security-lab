import chromadb

PRODUCTS_COLLECTION = "products"
FAQ_COLLECTION = "faq"

_COSINE = {"hnsw:space": "cosine"}


def get_or_create_products_collection(client: chromadb.ClientAPI) -> chromadb.Collection:
    return client.get_or_create_collection(name=PRODUCTS_COLLECTION, metadata=_COSINE)


def get_or_create_faq_collection(client: chromadb.ClientAPI) -> chromadb.Collection:
    return client.get_or_create_collection(name=FAQ_COLLECTION, metadata=_COSINE)
