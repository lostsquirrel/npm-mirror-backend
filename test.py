import json
import re
import time
import unittest

import requests
from tornado import httpclient
from tornado.httpclient import AsyncHTTPClient

from main import cache_id_key


class Test(unittest.TestCase):

    def test_pkg_conf(self):
        pass

    def test_fetch_head(self):
        http_client = httpclient.HTTPClient()

        try:
            url = "https://registry.npm.taobao.org/@types/react"
            r = http_client.fetch(
                url, method="HEAD")
            print(r.code, r.body)
        except httpclient.HTTPError as e:
            # HTTPError is raised for non-200 responses; the response
            # can be found in e.response.
            print("HTTP Error: " + str(e))
            # print(dir(e))
            print(e.code)
            print(type(e.code))
        except Exception as e:
            # Other errors are possible, such as IOError.
            print("Error: " + str(e))

    def test_fetchx(self):
        url = "https://registry.npmjs.org/@types/react"
        # r = requests.get(url)
        # print(r)
        http_client = httpclient.HTTPClient()

        try:
            r = http_client.fetch(
                url,
                # proxy_host="127.0.0.1",
                # proxy_port=3128
            )
            print(r.code, r.body)
        except httpclient.HTTPError as e:
            # HTTPError is raised for non-200 responses; the response
            # can be found in e.response.
            print("HTTP Error: " + str(e))
            # print(dir(e))
            print(e.code)
            print(type(e.code))
        except Exception as e:
            # Other errors are possible, such as IOError.
            print("Error: " + str(e))
        finally:
            http_client.close()

    def test_fetch(self):
        http_client = httpclient.HTTPClient()
        try:
            r = http_client.fetch(
                "https://registry.npm.taobao.org/@types/babel__template/-/babel__template-7.0.2.tgz")
            print(r.code, r.body)
        except httpclient.HTTPError as e:
            # HTTPError is raised for non-200 responses; the response
            # can be found in e.response.
            print("HTTP Error: " + str(e))
            print(dir(e))
            print(e.code)
            print(type(e.code))
        except Exception as e:
            # Other errors are possible, such as IOError.
            print("Error: " + str(e))

    # def test_async_fetch(self):
    #     async def f():
    #         http_client = AsyncHTTPClient()
    #         try:
    #             response = await http_client.fetch("https://www.baidu.com", method="HEAD")
    #         except Exception as e:
    #             print("Error: %s" % e)
    #         else:
    #             print(response.body)
    #     x = await f()
    #     print(x)

    def test_split(self):
        "\.\d+\.\d+\.tgz$"
        pattern = r"-(\d+\.){2}\d+.*tgz$"
        re_suffix = re.compile(pattern)
        # print("/@types/babel__template/-/babel__template-7.0.2.tgz".split("/-/"))
        results = re.search(re_suffix, "cheerio/-/cheerio-1.0.0-rc.3.tgz")
        if results is not None:
            print(results.group())

    def test_pkg(self):
        import redis
        redis_conn = redis.Redis(host='192.168.10.196', port=6379, db=0, password="yg123456")
        for key in redis_conn.keys("FLAG:*"):
            meta_id = key.decode().split(":")[1]
            print(meta_id)
            redis_conn.sadd("NPM:PKG", meta_id)
            print(redis_conn.scard("NPM:PKG"))

    def test_migrate_data(self):
        import redis
        redis_conn = redis.Redis(host='192.168.10.196', port=6379, db=0, password="yg123456")
        meta_list = redis_conn.smembers(cache_id_key)
        cache = dict()
        with open("/tmp/data/npm/etag") as fh:
            content = fh.read()
            if len(content) > 0:
                cache.update(json.loads(content))
        for _meta_id in meta_list:
            meta_id = _meta_id.decode()
            print(meta_id)
            if cache.get(meta_id) is None:
                cache[meta_id] = ""
                print("add {}".format(meta_id))

        with open("/tmp/data/npm/etag", 'w') as fh:
            fh.write(json.dumps(cache))
