from __future__ import annotations

from dataclasses import dataclass
from typing import Any
import time

import requests


@dataclass(frozen=True)
class HttpConfig:
    timeout_seconds: int = 30
    user_agent: str = "ProSlim-Microbiome-AI/0.1"
    retry_count: int = 2


class ApiRequestError(RuntimeError):
    pass


class ApiClient:
    def __init__(self, http_config: HttpConfig | None = None) -> None:
        self.http_config = http_config or HttpConfig()

    def get_json(self, url: str, params: dict[str, Any]) -> dict[str, Any]:
        last_error: requests.RequestException | None = None
        for attempt in range(self.http_config.retry_count + 1):
            try:
                response = requests.get(
                    url,
                    params=params,
                    timeout=self.http_config.timeout_seconds,
                    headers={"User-Agent": self.http_config.user_agent},
                )
                response.raise_for_status()
                break
            except requests.RequestException as exc:
                last_error = exc
                if attempt >= self.http_config.retry_count:
                    raise ApiRequestError(f"API request failed for {url}: {exc}") from exc
                time.sleep(1 + attempt)
        else:
            raise ApiRequestError(f"API request failed for {url}: {last_error}")
        payload = response.json()
        if not isinstance(payload, dict):
            raise ValueError(f"Expected JSON object from {url}")
        return payload

    def get_text(self, url: str, params: dict[str, Any] | None = None) -> str:
        last_error: requests.RequestException | None = None
        for attempt in range(self.http_config.retry_count + 1):
            try:
                response = requests.get(
                    url,
                    params=params or {},
                    timeout=self.http_config.timeout_seconds,
                    headers={"User-Agent": self.http_config.user_agent},
                )
                response.raise_for_status()
                return response.text
            except requests.RequestException as exc:
                last_error = exc
                if attempt >= self.http_config.retry_count:
                    raise ApiRequestError(f"API request failed for {url}: {exc}") from exc
                time.sleep(1 + attempt)
        raise ApiRequestError(f"API request failed for {url}: {last_error}")


class PubMedClient:
    def __init__(self, base_url: str, api_client: ApiClient) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_client = api_client

    def search_pmids(self, query: str, retmax: int) -> list[str]:
        payload = self.api_client.get_json(
            f"{self.base_url}/esearch.fcgi",
            {
                "db": "pubmed",
                "term": query,
                "retmode": "json",
                "retmax": retmax,
            },
        )
        return [str(pmid) for pmid in payload.get("esearchresult", {}).get("idlist", [])]

    def summaries(self, pmids: list[str]) -> list[dict[str, Any]]:
        if not pmids:
            return []
        payload = self.api_client.get_json(
            f"{self.base_url}/esummary.fcgi",
            {
                "db": "pubmed",
                "id": ",".join(pmids),
                "retmode": "json",
            },
        )
        result = payload.get("result", {})
        return [result[pmid] for pmid in result.get("uids", []) if pmid in result]


class NcbiAssemblyClient:
    def __init__(self, base_url: str, api_client: ApiClient) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_client = api_client

    def search_ids(self, query: str, retmax: int) -> list[str]:
        payload = self.api_client.get_json(
            f"{self.base_url}/esearch.fcgi",
            {
                "db": "assembly",
                "term": query,
                "retmode": "json",
                "retmax": retmax,
            },
        )
        return [str(item) for item in payload.get("esearchresult", {}).get("idlist", [])]

    def summaries(self, assembly_ids: list[str]) -> list[dict[str, Any]]:
        if not assembly_ids:
            return []
        payload = self.api_client.get_json(
            f"{self.base_url}/esummary.fcgi",
            {
                "db": "assembly",
                "id": ",".join(assembly_ids),
                "retmode": "json",
            },
        )
        result = payload.get("result", {})
        return [result[item] for item in result.get("uids", []) if item in result]


class EuropePmcClient:
    def __init__(self, base_url: str, api_client: ApiClient) -> None:
        self.base_url = base_url
        self.api_client = api_client

    def search(self, query: str, page_size: int) -> list[dict[str, Any]]:
        payload = self.api_client.get_json(
            self.base_url,
            {
                "query": query,
                "format": "json",
                "pageSize": page_size,
            },
        )
        result_list = payload.get("resultList", {}).get("result", [])
        return result_list if isinstance(result_list, list) else []


class ClinicalTrialsClient:
    def __init__(self, base_url: str, api_client: ApiClient) -> None:
        self.base_url = base_url
        self.api_client = api_client

    def search(self, query: str, page_size: int) -> list[dict[str, Any]]:
        payload = self.api_client.get_json(
            self.base_url,
            {
                "query.term": query,
                "pageSize": page_size,
                "format": "json",
            },
        )
        studies = payload.get("studies", [])
        return studies if isinstance(studies, list) else []
