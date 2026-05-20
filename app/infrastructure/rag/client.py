import os

import chromadb


def get_chroma_client() -> chromadb.ClientAPI:
    """FastAPI-compatible dependency. Override in tests with EphemeralClient."""
    url = os.environ.get("CHROMA_URL", "http://localhost:8000")
    without_scheme = url.split("//", 1)[-1].rstrip("/")
    if ":" in without_scheme:
        host, port_str = without_scheme.rsplit(":", 1)
        port = int(port_str)
    else:
        host = without_scheme
        port = 8000
    return chromadb.HttpClient(host=host, port=port)
