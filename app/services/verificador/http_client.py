import asyncio

import httpx

OPENALEX_BASE        = "https://api.openalex.org"
CROSSREF_BASE        = "https://api.crossref.org"
SEMANTICSCHOLAR_BASE = "https://api.semanticscholar.org/graph/v1"
PUBMED_BASE          = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
GOOGLEBOOKS_BASE     = "https://www.googleapis.com/books/v1"
CORE_BASE            = "https://api.core.ac.uk/v3"

HEADERS       = {"User-Agent": "TesisApp/1.0 (mailto:tesisp68@hotmail.com)"}
PUBMED_PARAMS = {"tool": "TesisApp", "email": "tesisp68@hotmail.com", "retmode": "json", "db": "pubmed"}

HTTP_CLIENT = httpx.AsyncClient(timeout=10.0, headers=HEADERS)
SEM         = asyncio.Semaphore(10)


async def _get(url: str, **kwargs):
    """Wrapper de HTTP_CLIENT.get con semáforo de concurrencia."""
    async with SEM:
        return await HTTP_CLIENT.get(url, **kwargs)
