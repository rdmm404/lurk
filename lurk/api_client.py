import asyncio
import dataclasses
from json import JSONDecodeError
from typing import Any, Mapping, cast
from curl_cffi import requests
from lurk.config import ClientConfig
from rich import print

JsonResponse = dict[str, Any]

from pydantic.dataclasses import dataclass

@dataclass
class Response:
    status_code: int
    json: JsonResponse
    ok: bool
    raw: str

@dataclasses.dataclass
class _QueuedRequest:
    method: requests.session.HttpMethod
    route: str
    headers: Mapping[str, str] | None
    params: Mapping[str, str] | None
    body: Mapping[str, Any] | None
    cookies: Mapping[str, str] | None
    future: asyncio.Future  # This future will eventually contain the Response.


class ApiClient:
    def __init__(self, config: ClientConfig, requests_per_second: float = 10.0):
        self.base_url: str | None = None
        self.session = requests.AsyncSession()
        self._config = config

        if requests_per_second <= 0:
            raise ValueError("requests_per_second must be positive")
        self._rps = requests_per_second  # Allowed request initiations per second.
        # We'll treat the integer part as our batch size.
        self._batch_size = max(1, int(requests_per_second))
        # Create the asyncio.Queue to hold enqueued requests.
        self._queue: asyncio.Queue[_QueuedRequest] = asyncio.Queue()
        # Start the background task that processes the queue.
        self._worker_task = asyncio.create_task(self._process_queue())

    async def __aenter__(self) -> "ApiClient":
        return self

    async def __aexit__(self, *_: Any) -> None:
        await self.close()

    async def close(self) -> None:
        if self._worker_task:
            self._worker_task.cancel()
            try:
                await self._worker_task
            except asyncio.CancelledError:
                pass
        await self.session.close()

    def set_base_url(self, url: str) -> "ApiClient":
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
    ) -> Response:
        """
        Instead of immediately executing the request, wrap the request parameters
        and a Future into a _QueuedRequest, enqueue it, and then await the Future.
        """
        loop = asyncio.get_running_loop()
        future: asyncio.Future[Response] = loop.create_future()
        queued_req = _QueuedRequest(
            method, route, headers, params, body, cookies, future
        )
        await self._queue.put(queued_req)
        return await future

    async def _execute_request(
        self,
        method: requests.session.HttpMethod,
        route: str,
        headers: Mapping[str, str] | None,
        params: Mapping[str, str] | None,
        body: Mapping[str, Any] | None,
        cookies: Mapping[str, str] | None,
    ) -> Response:
        """
        This method encapsulates your original request logic.
        """
        assert self.base_url is not None, "Please set the base url"
        # Ensure the route starts with a slash.
        route = f"/{route}" if not route.startswith("/") else route
        # Begin with the default headers and update if provided.
        res_headers = self._config.headers.copy()
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
            json=cast(dict[str, Any], body),
            cookies=cast(dict[str, str], cookies),
        )
        print(f"Received response with status {resp.status_code}")
        try:
            data = resp.json()
        except JSONDecodeError:
            print(f"Invalid json received {resp.text}")
            return Response(
                status_code=resp.status_code, ok=resp.ok, json={}, raw=resp.text
            )
        print(f"Response body: {resp.text[:500]}...")
        return Response(
            status_code=resp.status_code, ok=resp.ok, json=data, raw=resp.text
        )

    async def _handle_request(self, queued_req: _QueuedRequest) -> None:
        """
        Process a single queued request by executing it and setting the result on its future.
        """
        try:
            response = await self._execute_request(
                queued_req.method,
                queued_req.route,
                queued_req.headers,
                queued_req.params,
                queued_req.body,
                queued_req.cookies,
            )
            queued_req.future.set_result(response)
        except Exception as e:
            queued_req.future.set_exception(e)

    async def _process_queue(self) -> None:
        """
        Each loop, attempt to get up to self._batch_size requests from the queue,
        fire them concurrently using a TaskGroup, and then wait until one second (or more,
        if requests took longer) has elapsed since the batch started.
        """
        try:
            while True:
                start_time = asyncio.get_running_loop().time()
                batch = []
                # Collect up to self._batch_size requests.
                for _ in range(self._batch_size):
                    try:
                        queued_req = self._queue.get_nowait()
                        batch.append(queued_req)
                    except asyncio.QueueEmpty:
                        break

                if batch:
                    # Use TaskGroup to run all tasks concurrently.
                    async with asyncio.TaskGroup() as tg:
                        for qr in batch:
                            tg.create_task(self._handle_request(qr))
                    # Mark each request as processed.
                    for _ in batch:
                        self._queue.task_done()
                else:
                    # If no requests are waiting, yield a bit before checking again.
                    await asyncio.sleep(0.01)

                elapsed = asyncio.get_running_loop().time() - start_time
                # Ensure that the total loop duration is at least one second.
                if elapsed < 1.0:
                    await asyncio.sleep(1.0 - elapsed)
        except asyncio.CancelledError:
            # Exit gracefully if the task is cancelled.
            pass

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
