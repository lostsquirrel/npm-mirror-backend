import json

from aiofile import AIOFile
from tornado.httpclient import AsyncHTTPClient
import logging

from tornado.simple_httpclient import HTTPTimeoutError, SimpleAsyncHTTPClient

from settings import cache_flag_key, cache_update_key, pkg_base_npm, mirror_address, http_client_config, \
    meta_etag_file_path, proxy_host, proxy_port, meta_base_path, max_retry_amount

log = logging.getLogger(__name__)

etag_cache = dict()


class MetaTag:

    def __init__(self, meta_id, etag):
        self.meta_id = meta_id
        self.etag = etag


def load_etag_cache():
    with open(meta_etag_file_path) as fh:
        content = fh.read()
        etag_cache.update(json.loads(content))


def save_etag_cache():
    with open(meta_etag_file_path, 'w') as fh:
        fh.write(json.dumps(etag_cache))


def get_flag_key(meta_id: str) -> str:
    return cache_flag_key.format(meta_id)


def get_update_key(meta_id: str) -> str:
    return cache_update_key.format(meta_id)


def get_index_url(meta_id: str) -> str:
    return "{}/{}".format(pkg_base_npm, meta_id)


def http_ok(code: int) -> bool:
    return 200 <= code < 400


def load_proxy():
    if proxy_host is not None:
        http_client_config['proxy_host'] = proxy_host
        http_client_config['proxy_port'] = int(proxy_port)


async def check_and_update(meta_id: str):
    http_client = AsyncHTTPClient(defaults=dict(request_timeout=10, connect_timeout=10))
    index_url = get_index_url(meta_id)
    log.debug("checking update {}".format(index_url))
    try:
        r = await http_client.fetch(index_url, method="HEAD", **http_client_config)
        if http_ok(r.code):
            etag = r.headers.get('etag')
            if is_index_update(meta_id, etag):
                #  fetch new index,and save to file
                return await update_index(meta_id)
            else:
                log.debug("no update for {}".format(index_url))
        else:
            raise Exception("fetch HEAD {} failed".format(index_url))
    except Exception as e:
        log.warning("update failed for %s", e)


async def update_index(meta_id: str):
    log.info("start to update %s", meta_id)
    index_url = get_index_url(meta_id)

    r = await query_index(index_url, int(max_retry_amount))
    if r is not None and http_ok(r.code):
        data = json.loads(r.body.decode())
        for k, v in data["versions"].items():
            old_pkg_url = v["dist"]["tarball"]
            prefix = old_pkg_url.replace(pkg_base_npm, "")[1:]
            v["dist"]["tarball"] = "{}/_pkg/{}".format(mirror_address, prefix)
        # save meta to file
        meta_file = meta_base_path / meta_id
        assume_file_parent(meta_file)
        await save_file(str(meta_file), json.dumps(data).encode())
        # update etag
        etag_cache[meta_id] = r.headers.get('etag')
        save_etag_cache()
        log.info("success updated %s last-modified: %s", index_url, r.headers.get("last-modified"))
        return data
    else:
        raise Exception("fetch GET {} failed".format(index_url))


def is_index_update(meta_id, current_etag):
    cached_etag = etag_cache.get(meta_id)
    if cached_etag is None:
        return True
    log.debug("compare etag %s, %s", cached_etag, current_etag)
    return cached_etag != current_etag


async def query_index(index_url, retry):
    http_client = AsyncHTTPClient(defaults=dict(request_timeout=30, connect_timeout=10))
    try:
        r = await http_client.fetch(index_url, **http_client_config)
        return r
    except HTTPTimeoutError as e:
        log.warning("update failed for %s, retry %d", e, retry)
        if retry > 0:
            return await query_index(index_url, retry - 1)
        log.error("all retry failed on %s", index_url)


async def save_file(file_path: str, content: bytes):
    async with AIOFile(file_path, 'wb') as afp:
        await afp.write(content)
        await afp.fsync()


async def send_content(req, content: bytes):
    req.write(content)
    req.set_header('Content-Type', 'application/octet-stream')
    await req.finish()


class NoQueueTimeoutHTTPClient(SimpleAsyncHTTPClient):
    def fetch_impl(self, request, callback):
        key = object()

        self.queue.append((key, request, callback))
        self.waiting[key] = (request, callback, None)

        self._process_queue()

        if self.queue:
            log.debug("max_clients limit reached, request queued. %d active, %d queued requests." % (
                len(self.active), len(self.queue)))


def assume_file_parent(pkg_path):
    if not pkg_path.parent.exists():
        pkg_path.parent.mkdir(parents=True)
