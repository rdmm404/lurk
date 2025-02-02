from pydantic.dataclasses import dataclass
from json import JSONDecodeError
from typing import Self, Any, cast
from curl_cffi import requests
from lurk.config import ClientConfig
from collections.abc import Mapping

JsonResponse = dict[str, Any]


@dataclass
class Response:
    status_code: int
    json: JsonResponse
    ok: bool
    raw: str


class ApiClient:
    def __init__(self, base_url: str, config: ClientConfig):
        self.base_url = base_url.rstrip("/")
        self.session = requests.AsyncSession()
        self._config = config

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(self, *_: Any) -> None:
        await self.close()

    async def close(self) -> None:
        await self.session.close()

    async def _make_request(
        self,
        method: requests.session.HttpMethod,
        route: str,
        headers: Mapping[str, str] | None = None,
        params: Mapping[str, str] | None = None,
        body: Mapping[str, Any] | None = None,
        cookies: Mapping[str, str] | None = None,
    ) -> Response:
        route = f"/{route}" if not route.startswith("/") else route
        res_headers = self._config.headers
        print(
            f"Making request to {self.base_url + route} with {body=} headers={res_headers} {params=} {cookies=}"
        )
        if headers:
            res_headers.update(headers)
        resp = await self.session.request(
            method,
            self.base_url + route,
            params=cast(dict[str, str], params),
            headers=res_headers,
            json=cast(dict[str, str], body),
            cookies=cast(dict[str, str], cookies),
        )
        print(f"Received response with status {resp.status_code}")
        try:
            data = resp.json()  # type: ignore
        except JSONDecodeError:
            print(f"Invalid json received {resp.text}")
            return Response(
                status_code=resp.status_code, ok=resp.ok, json={}, raw=resp.text
            )
        print(f"Response body: {resp.text[:500]}...")

        return Response(
            status_code=resp.status_code, ok=resp.ok, json=data, raw=resp.text
        )

    async def get(
        self,
        route: str,
        headers: Mapping[str, str] | None = None,
        params: Mapping[str, Any] | None = None,
        body: Mapping[str, Any] | None = None,
        cookies: Mapping[str, str] | None = None,
    ) -> Response:
        return await self._make_request("GET", route, headers, params, body, cookies)

    async def post(
        self,
        route: str,
        headers: Mapping[str, str] | None = None,
        params: Mapping[str, str] | None = None,
        body: Mapping[str, Any] | None = None,
        cookies: Mapping[str, str] | None = None,
    ) -> Response:
        return await self._make_request("POST", route, headers, params, body, cookies)
