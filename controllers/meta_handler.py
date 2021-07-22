import json
import logging
from abc import ABC
from typing import Any

import tornado.web
from tornado import httputil
from tornado.web import Application

from settings import meta_base_path
from utils import check_and_update, update_index, send_content

log = logging.getLogger(__name__)


class MetaHandler(tornado.web.RequestHandler, ABC):
    def __init__(self, application: Application, request: httputil.HTTPServerRequest, **kwargs: Any):
        super().__init__(application, request, **kwargs)
        self.db = None

    async def get(self, meta_id):
        log.info("query meta {}".format(meta_id))

        meta_file = meta_base_path / meta_id
        if meta_file.exists():
            data = check_and_update(meta_id)
        else:
            data = update_index(meta_id)
        await send_content(self, json.dumps(data).encode())
