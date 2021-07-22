import logging
import threading

import tornado.ioloop
import tornado.web

from controllers.meta_handler import MetaHandler
from controllers.meta_update_handler import MetaUpdateHandler
from controllers.pkg_handler import PackageHandler
from settings import port
from utils import load_etag_cache, file_save_worker

logging.basicConfig(level=logging.DEBUG, format="%(asctime)s %(levelname)s %(name)s %(message)s")

log = logging.getLogger(__name__)


def make_app():
    load_etag_cache()
    threading.Thread(target=file_save_worker, daemon=True).start()
    return tornado.web.Application([
        (r"/_registry/(.*)", MetaHandler),
        (r"/_pkg/(.*)", PackageHandler),
        (r"/meta/update", MetaUpdateHandler),
    ])


if __name__ == "__main__":
    app = make_app()
    log.info("start server on port: {}".format(port))
    app.listen(port)
    tornado.ioloop.IOLoop.current().start()
