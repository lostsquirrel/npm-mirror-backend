import re
import time
import unittest

from tornado import httpclient
from tornado.httpclient import AsyncHTTPClient


class Test(unittest.TestCase):

    def test_pkg_conf(self):
        pass

    def test_fetch_head(self):
        http_client = httpclient.HTTPClient()

        try:
            r = http_client.fetch(
                "https://registry.npm.taobao.org/@types/babel__template/-/babel__template-7.0.2.tgz", method="HEAD")
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


    def test_split(self):
        "\.\d+\.\d+\.tgz$"
        pattern = r"-(\d+\.){2}\d+.*tgz$"
        re_suffix = re.compile(pattern)
        # print("/@types/babel__template/-/babel__template-7.0.2.tgz".split("/-/"))
        results = re.search(re_suffix, "cheerio/-/cheerio-1.0.0-rc.3.tgz")
        if results is not None:
            print(results.group())