import asyncio

from pydantic.dataclasses import dataclass
from json import JSONDecodeError
from typing import Self, Any, cast, Union, overload, Literal
from curl_cffi import requests
from lurk.config import ClientConfig
from collections.abc import Mapping

from rich import print

JsonResponse = dict[str, Any]

@dataclass
class JsonApiResponse:
    status_code: int
    content: JsonResponse
    ok: bool
    raw: str
    is_json: Literal[True]


@dataclass
class TextResponse:
    status_code: int
    content: str
    ok: bool
    raw: str
    is_json: Literal[False]


Response = Union[JsonApiResponse, TextResponse]


class HttpClient:
    def __init__(self, config: ClientConfig):
        self.base_url: str | None = None
        self.session = requests.AsyncSession(impersonate="chrome")
        self._config = config

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(self, *_: Any) -> None:
        await self.close()

    async def close(self) -> None:
        await self.session.close()

    def set_base_url(self, url: str) -> Self:
        self.base_url = url.rstrip("/")
        return self

    async def _make_request(
        self,
        method: requests.session.HttpMethod,
        route: str,
        headers: Mapping[str, str] | None = None,
        params: Mapping[str, str] | None = None,
        body: Mapping[str, Any] | None = None,
        cookies: Mapping[str, str] | None = None,
        expect_json: bool = False,
    ) -> Response:
        assert self.base_url is not None, "Please set the base url"
        route = f"/{route}" if not route.startswith("/") else route
        res_headers = self._config.headers
        if headers:
            res_headers.update(headers)
        print(
            f"Making request to {self.base_url + route} with {body=} headers={res_headers} {params=} {cookies=}"
        )
        resp = await self.session.request(
            method,
            self.base_url + route,
            params=cast(dict[str, str], params),
            headers=res_headers,
            json=cast(dict[str, str], body),
            cookies=cast(dict[str, str], cookies),
        )
        print(f"Received response with status {resp.status_code}")

        raw_text = resp.text

        if expect_json:
            try:
                data = resp.json()
                print(f"Response body (JSON): {raw_text[:500]}...")
                # TODO: replace this dumb sleep with a proper rate limiting method like a request queue
                await asyncio.sleep(1)
                return JsonApiResponse(
                    status_code=resp.status_code,
                    ok=resp.ok,
                    content=data,
                    raw=raw_text,
                    is_json=True,
                )
            except JSONDecodeError:
                print(f"Expected JSON but received non-JSON content: {raw_text[:100]}...")
                raise ValueError("Expected JSON response but got non-JSON content")
        else:
            print(f"Response body (text): {raw_text[:500]}...")
            # TODO: replace this dumb sleep with a proper rate limiting method like a request queue
            await asyncio.sleep(1)
            return TextResponse(
                status_code=resp.status_code,
                ok=resp.ok,
                content=raw_text,
                raw=raw_text,
                is_json=False,
            )

    @overload
    async def get(
        self,
        route: str,
        *,
        expect_json: Literal[False] = False,
        headers: Mapping[str, str] | None = None,
        params: Mapping[str, Any] | None = None,
        body: Mapping[str, Any] | None = None,
        cookies: Mapping[str, str] | None = None,
    ) -> TextResponse: ...
    @overload
    async def get(
        self,
        route: str,
        *,
        expect_json: Literal[True],
        headers: Mapping[str, str] | None = None,
        params: Mapping[str, Any] | None = None,
        body: Mapping[str, Any] | None = None,
        cookies: Mapping[str, str] | None = None,
    ) -> JsonApiResponse: ...
    async def get(
        self,
        route: str,
        *,
        expect_json: bool = False,
        headers: Mapping[str, str] | None = None,
        params: Mapping[str, Any] | None = None,
        body: Mapping[str, Any] | None = None,
        cookies: Mapping[str, str] | None = None,
    ) -> Response:
        return await self._make_request("GET", route, headers, params, body, cookies, expect_json)

    @overload
    async def post(
        self,
        route: str,
        *,
        expect_json: Literal[False] = False,
        headers: Mapping[str, str] | None = None,
        params: Mapping[str, str] | None = None,
        body: Mapping[str, Any] | None = None,
        cookies: Mapping[str, str] | None = None,
    ) -> TextResponse: ...

    @overload
    async def post(
        self,
        route: str,
        *,
        expect_json: Literal[True],
        headers: Mapping[str, str] | None = None,
        params: Mapping[str, str] | None = None,
        body: Mapping[str, Any] | None = None,
        cookies: Mapping[str, str] | None = None,
    ) -> JsonApiResponse: ...

    async def post(
        self,
        route: str,
        *,
        expect_json: bool = False,
        headers: Mapping[str, str] | None = None,
        params: Mapping[str, str] | None = None,
        body: Mapping[str, Any] | None = None,
        cookies: Mapping[str, str] | None = None,
    ) -> Response:
        return await self._make_request("POST", route, headers, params, body, cookies, expect_json)
