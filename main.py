import json
import logging
import os
import re
from pathlib import Path
from typing import Any

import tornado.ioloop
import tornado.web
import redis
from aiofile import AIOFile
from tornado import httputil
from tornado.httpclient import AsyncHTTPClient
from tornado.simple_httpclient import SimpleAsyncHTTPClient, HTTPTimeoutError

pkg_base_npm = "https://registry.npmjs.org"
pkg_base_custom = os.getenv("ORIGIN_SOURCES", "https://registry.npm.taobao.org")
mirror_address = os.getenv("MIRROR_ADDRESS", "https://npm.lisong.pub")
password = os.getenv("PASSWORD", "yg123456")
pkg_base_path = Path("/data/npm/_pkg")
pattern = r"-(\d+\.){2}\d+.*tgz$"
re_suffix = re.compile(pattern)
cache_flag_key = "FLAG:{}"
cache_update_key = "ETAG:{}"
cache_id_key = "NPM:PKG"

logging.basicConfig(level=logging.DEBUG, format="%(asctime)s %(levelname)s %(name)s %(message)s")

log = logging.getLogger(__name__)


def get_flag_key(meta_id: str) -> str:
    return cache_flag_key.format(meta_id)


def get_update_key(meta_id: str) -> str:
    return cache_update_key.format(meta_id)


def get_index_url(meta_id: str) -> str:
    return "{}/{}".format(pkg_base_npm, meta_id)


def http_ok(code: int) -> bool:
    return 200 <= code < 400


async def update_index(meta_id):
    log.info("start to update %s", meta_id)
    index_url = get_index_url(meta_id)

    r = await query_index(index_url)
    if http_ok(r.code):
        data = json.loads(r.body.decode())
        for k, v in data["versions"].items():
            old_pkg_url = v["dist"]["tarball"]
            prefix = old_pkg_url.replace(pkg_base_npm, "")[1:]
            v["dist"]["tarball"] = "{}/_pkg/{}".format(mirror_address, prefix)

        redis_conn.set(meta_id, json.dumps(data))
        redis_conn.set(get_update_key(meta_id), r.headers.get('etag'))
        redis_conn.set(get_flag_key(meta_id), 1, 60 * 60 * 24)
        log.info("success updated %s last-modified: %s", index_url, r.headers.get("last-modified"))
    else:
        raise Exception("fetch GET {} failed".format(index_url))


async def query_index(index_url):
    try:
        http_client = AsyncHTTPClient(defaults=dict(request_timeout=30, connect_timeout=10))
        r = await http_client.fetch(index_url)
        return r
    except HTTPTimeoutError as e:
        log.warning("update failed, retry. %s", e)
        return await query_index(index_url)


class MataHandler(tornado.web.RequestHandler):
    def __init__(self, application: "Application", request: httputil.HTTPServerRequest, **kwargs: Any):
        super().__init__(application, request, **kwargs)
        self.db = redis_conn

    def is_index_update(self, meta_id, current_etag):
        return self.db.get(get_update_key(meta_id)) != current_etag

    async def get(self, meta_id):
        log.info("query meta {}".format(meta_id))

        if not self.db.exists(get_flag_key(meta_id)):
            self.db.sadd(cache_id_key, meta_id)
            http_client = AsyncHTTPClient(defaults=dict(request_timeout=3600, connect_timeout=300))
            index_url = get_index_url(meta_id)
            log.debug(index_url)
            r = await http_client.fetch(index_url, method="HEAD")
            if http_ok(r.code):
                etag = r.headers.get('etag')
                if self.is_index_update(meta_id, etag):
                    #             fetch new index,and save to redis, update etag, set flag
                    await update_index(meta_id)

            else:
                raise Exception("fetch HEAD {} failed".format(index_url))
        data = self.db.get(meta_id)
        self.set_header('Content-Type', 'application/json;charset=UTF-8')
        self.write(data)
        await self.finish()


class MataUpdateHandler(tornado.web.RequestHandler):
    def __init__(self, application: "Application", request: httputil.HTTPServerRequest, **kwargs: Any):
        super().__init__(application, request, **kwargs)

    async def get(self):
        meta_id = self.get_argument("meta_id", None)
        if meta_id is None:
            # update all meta info
            meta_list = redis_conn.smembers(cache_id_key)
            for meta_id in meta_list:
                await update_index(meta_id.decode())
            self.write("update {} packages\n".format(len(meta_list)))
        else:
            # force update this meta
            await update_index(meta_id)
            if not redis_conn.sismember(cache_id_key, meta_id):
                redis_conn.sadd(cache_id_key, meta_id)
            self.write("update {}".format(meta_id))

        await self.finish()


class PackageHandler(tornado.web.RequestHandler):

    async def get(self, pkg_url):

        async def download_success(req, file_path: str, content: bytes):
            async with AIOFile(file_path, 'wb') as afp:
                await afp.write(content)
                await afp.fsync()
                req.write(content)
                req.set_header('Content-Type', 'application/octet-stream')
                await req.finish()

        log.info("fetch package {}".format(pkg_url))

        pkg_path = pkg_base_path / pkg_url
        if not pkg_path.parent.exists():
            pkg_path.parent.mkdir(parents=True)

        http_client = AsyncHTTPClient()

        pkg_url_custom = None
        try:

            results = re.search(re_suffix, pkg_url)
            if results is None:
                raise Exception("version not recognised {}".format(pkg_url))
            pkg_id = pkg_url.split("/-/")[0]
            pkg_url_custom = "{}/{}/download/{}{}".format(pkg_base_custom, pkg_id, pkg_id, results.group())
            r = await http_client.fetch(pkg_url_custom)
        except Exception as e:
            log.warning("fetch {} failed: {}".format(pkg_url_custom, e))
            pkg_url_npm = "{}/{}".format(pkg_base_npm, pkg_url)
            try:
                r = await http_client.fetch(pkg_url_npm, request_timeout=300.0)
            except Exception as e:
                log.error("fetch {} failed: {}".format(pkg_url_npm, e))
            else:
                await download_success(self, str(pkg_path), r.body)
        else:
            await download_success(self, str(pkg_path), r.body)
        finally:
            http_client.close()


class NoQueueTimeoutHTTPClient(SimpleAsyncHTTPClient):
    def fetch_impl(self, request, callback):
        key = object()

        self.queue.append((key, request, callback))
        self.waiting[key] = (request, callback, None)

        self._process_queue()

        if self.queue:
            log.debug("max_clients limit reached, request queued. %d active, %d queued requests." % (
                len(self.active), len(self.queue)))


def make_app():
    # AsyncHTTPClient.configure("tornado.curl_httpclient.CurlAsyncHTTPClient", max_clients=50)
    AsyncHTTPClient.configure(NoQueueTimeoutHTTPClient, max_clients=20)
    return tornado.web.Application([
        (r"/_registry/(.*)", MataHandler),
        (r"/_pkg/(.*)", PackageHandler),
        (r"/meta/update", MataUpdateHandler),
    ])


if __name__ == "__main__":
    redis_conn = redis.Redis(host='localhost', port=6379, db=0, password=password)
    port = int(os.getenv("PORT", "8888"))
    app = make_app()
    app.listen(port)
    tornado.ioloop.IOLoop.current().start()
