import os
import re
from pathlib import Path

pkg_base_npm = "https://registry.npmjs.org"
pkg_base_custom = os.getenv("ORIGIN_SOURCES", "https://registry.npm.taobao.org")
mirror_address = os.getenv("MIRROR_ADDRESS", "https://npm.lisong.pub")
password = os.getenv("PASSWORD", "yg123456")
data_base_path = os.getenv("DATA_PATH", "/tmp/data")
pkg_base_path = Path("{}/npm/_pkg".format(data_base_path))
meta_base_path = Path("{}/npm/_registry".format(data_base_path))
meta_etag_file_path = Path("{}/npm/etag".format(data_base_path))
pattern = r"-(\d+\.){2}\d+.*tgz$"
re_suffix = re.compile(pattern)
proxy_host = os.getenv("PROXY_HOST", None)
proxy_port = os.getenv("PROXY_PORT")
port = int(os.getenv("SERVER_PORT", "8888"))
max_retry_amount = os.getenv("MAX_RETRY", "3")
