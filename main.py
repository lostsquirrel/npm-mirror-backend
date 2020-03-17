import json
import os
from pathlib import Path
from typing import Any

import couchdb
import tornado.ioloop
import tornado.web
from tornado import httputil
from tornado.httpclient import AsyncHTTPClient

pkg_base = os.getenv("ORIGIN_SOURCE", "https://registry.npmjs.org")
mirror_address = os.getenv("MIRROR_ADDRESS", "https://npm.lisong.pub")
pkg_base_path = Path("/data/npm/_pkg")


class MataHandler(tornado.web.RequestHandler):
    def __init__(self, application: "Application", request: httputil.HTTPServerRequest, **kwargs: Any):
        super().__init__(application, request, **kwargs)
        couch = couchdb.Server('http://192.168.10.196:5984/')
        self.db = couch['registry']

    def get(self, meta_id):
        print(meta_id)

        data = self.db[meta_id]

        for k, v in data["versions"].items():
            old_pkg_url = v["dist"]["tarball"]
            prefix = old_pkg_url.replace(pkg_base, "")[1:]
            v["dist"]["tarball"] = "{}/_pkg/{}".format(mirror_address, prefix)
            # print(k, v["name"], v["dist"]["tarball"])
        self.set_header('Content-Type', 'application/json;charset=UTF-8')
        self.write(json.dumps(data))
        self.finish()


class PackageHandler(tornado.web.RequestHandler):

    async def get(self, pkg_url):
        print(pkg_url)

        pkg_url_full = "{}/{}".format(pkg_base, pkg_url)
        pkg_path = pkg_base_path / pkg_url
        if not pkg_path.parent.exists():
            pkg_path.parent.mkdir(parents=True)

        http_client = AsyncHTTPClient()
        try:
            r = await http_client.fetch(pkg_url_full, request_timeout=600.0)
        except Exception as e:
            print("Error: %s" % e)
        else:
            pkg_path.write_bytes(r.body)
            self.set_header('Content-Type', 'application/octet-stream')
            self.write(pkg_path.read_bytes())
        await self.finish()


def make_app():
    AsyncHTTPClient.configure("tornado.curl_httpclient.CurlAsyncHTTPClient")

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
