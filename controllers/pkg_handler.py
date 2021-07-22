import logging
import re
from abc import ABC

import requests
import tornado.web

from settings import pkg_base_path, re_suffix, pkg_base_custom, pkg_base_npm
from utils import send_content, save_file, assume_file_parent

log = logging.getLogger(__name__)


class PackageHandler(tornado.web.RequestHandler, ABC):

    async def get(self, pkg_url):

        async def download_success(req, file_path: str, content: bytes):
            save_file(file_path, content)
            await send_content(req, content)

        log.info("fetch package {}".format(pkg_url))

        pkg_path = pkg_base_path / pkg_url
        assume_file_parent(pkg_path)

        results = re.search(re_suffix, pkg_url)
        if results is None:
            log.error("version not recognised {}".format(pkg_url))
            self.set_status(400)
        pkg_id = pkg_url.split("/-/")[0]
        pkg_url_custom = "{}/{}/download/{}{}".format(pkg_base_custom, pkg_id, pkg_id, results.group())
        try:
            r = requests.get(pkg_url_custom)
            await download_success(self, str(pkg_path), r.content)
        except Exception as e:
            log.warning("fetch {} failed: {}".format(pkg_url_custom, e))
            pkg_url_npm = "{}/{}".format(pkg_base_npm, pkg_url)
            try:
                r = requests.get(pkg_url_npm)
                await download_success(self, str(pkg_path), r.content)
            except Exception as e:
                log.error("fetch {} failed: {}".format(pkg_url_npm, e))






