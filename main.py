import logging

import tornado.ioloop
import tornado.web
import redis
from tornado.httpclient import AsyncHTTPClient

from controllers.meta_handler import MetaHandler
from controllers.meta_update_handler import MetaUpdateHandler
from controllers.pkg_handler import PackageHandler
from settings import port
from utils import NoQueueTimeoutHTTPClient, load_etag_cache, load_proxy

logging.basicConfig(level=logging.DEBUG, format="%(asctime)s %(levelname)s %(name)s %(message)s")

log = logging.getLogger(__name__)


def make_app():
    AsyncHTTPClient.configure("tornado.curl_httpclient.CurlAsyncHTTPClient", max_clients=500)
    # AsyncHTTPClient.configure(NoQueueTimeoutHTTPClient, max_clients=200)
    load_etag_cache()
    load_proxy()
    return tornado.web.Application([
        (r"/_registry/(.*)", MetaHandler),
        (r"/_pkg/(.*)", PackageHandler),
        (r"/meta/update", MetaUpdateHandler),
    ])


if __name__ == "__main__":
    app = make_app()
    app.listen(port)
    tornado.ioloop.IOLoop.current().start()
