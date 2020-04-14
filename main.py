import json
import os
import re
import logging
from pathlib import Path
from typing import Any

from aiofile import AIOFile
import couchdb
import tornado.ioloop
import tornado.web
from tornado import httputil
from tornado.httpclient import AsyncHTTPClient

pkg_base_npm = "https://registry.npmjs.org"
pkg_base_custom = os.getenv("ORIGIN_SOURCES", "https://registry.npm.taobao.org")
mirror_address = os.getenv("MIRROR_ADDRESS", "https://npm.lisong.pub")
pkg_base_path = Path("/data/npm/_pkg")
pattern = r"-(\d+\.){2}\d+.*tgz$"
re_suffix = re.compile(pattern)

logging.basicConfig(format="%(processName)s %(thread)s %(levelname)s %(name)s %(message)s")

log = logging.getLogger(__name__)


class MataHandler(tornado.web.RequestHandler):
    def __init__(self, application: "Application", request: httputil.HTTPServerRequest, **kwargs: Any):
        super().__init__(application, request, **kwargs)
        couch = couchdb.Server('http://192.168.10.196:5984/')
        self.db = couch['registry']

    def get(self, meta_id):
        log.info("query meta {}".format(meta_id))

        data = self.db[meta_id]

        for k, v in data["versions"].items():
            old_pkg_url = v["dist"]["tarball"]
            prefix = old_pkg_url.replace(pkg_base_npm, "")[1:]
            v["dist"]["tarball"] = "{}/_pkg/{}".format(mirror_address, prefix)
            # print(k, v["name"], v["dist"]["tarball"])
        self.set_header('Content-Type', 'application/json;charset=UTF-8')
        self.write(json.dumps(data))
        self.finish()


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
                raise Exception("version not recognised")
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


def make_app():
    AsyncHTTPClient.configure("tornado.curl_httpclient.CurlAsyncHTTPClient", max_clients=20)

    return tornado.web.Application([
        (r"/_registry/(.*)", MataHandler),
        (r"/_pkg/(.*)", PackageHandler),
    ])


if __name__ == "__main__":
    port = int(os.getenv("PORT", "8888"))
    app = make_app()
    app.listen(port)
    # server = HTTPServer(app)
    # server.bind(int(port))
    # server.start(0)
    tornado.ioloop.IOLoop.current().start()
