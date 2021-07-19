from abc import ABC
from typing import Any

import tornado.web
from tornado import httputil
from tornado.web import Application

from utils import check_and_update, etag_cache
from settings import cache_id_key


class MetaUpdateHandler(tornado.web.RequestHandler, ABC):
    def __init__(self, application: Application, request: httputil.HTTPServerRequest, **kwargs: Any):
        super().__init__(application, request, **kwargs)

    async def get(self):
        meta_id = self.get_argument("meta_id", None)
        if meta_id is None:
            # update all meta info
            meta_list = etag_cache.keys()
            for meta_id in meta_list:
                await check_and_update(meta_id)
            self.write("update {} packages\n".format(len(meta_list)))
        else:
            await check_and_update(meta_id)
            self.write("updated {}".format(meta_id))

        await self.finish()
