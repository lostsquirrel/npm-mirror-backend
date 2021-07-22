import json
import logging
from pathlib import Path
from queue import Queue

import requests

from settings import pkg_base_npm, mirror_address, meta_etag_file_path, meta_base_path, max_retry_amount

log = logging.getLogger(__name__)

etag_cache = dict()
task_queue = Queue(maxsize=2000)


def load_etag_cache():
    try:
        with open(meta_etag_file_path) as fh:
            content = fh.read()
            if content is not None and len(content) > 0:
                etag_cache.update(json.loads(content))
    except FileNotFoundError as e:
        log.error(f'etag file not exist {e}')


def save_etag_cache():
    task_queue.put((meta_etag_file_path, json.dumps(etag_cache).encode()))


def get_index_url(meta_id: str) -> str:
    return "{}/{}".format(pkg_base_npm, meta_id)


def http_ok(code: int) -> bool:
    return 200 <= code < 400


def check_and_update(meta_id: str):
    index_url = get_index_url(meta_id)
    log.debug("checking update {}".format(index_url))
    try:
        meta_file = meta_base_path / meta_id
        if not meta_file.exists():
            return update_index(meta_id)
        r = requests.head(index_url)
        if http_ok(r.status_code):
            etag = r.headers.get('etag')
            if is_index_update(meta_id, etag):
                #  fetch new index,and save to file
                return update_index(meta_id)
            else:
                log.debug("no update for {}".format(index_url))
        else:
            raise Exception("fetch HEAD {} failed {}".format(index_url, r.status_code))
    except Exception as e:
        log.warning("update failed for %s", e)


def update_index(meta_id: str):
    log.info("start to update %s", meta_id)
    index_url = get_index_url(meta_id)

    r = query_index(index_url, int(max_retry_amount))
    if r is not None and http_ok(r.status_code):
        data = r.json()
        for k, v in data["versions"].items():
            old_pkg_url = v["dist"]["tarball"]
            prefix = old_pkg_url.replace(pkg_base_npm, "")[1:]
            v["dist"]["tarball"] = "{}/_pkg/{}".format(mirror_address, prefix)
        # save meta to file
        meta_file = meta_base_path / meta_id
        assume_file_parent(meta_file)
        save_file(str(meta_file), json.dumps(data).encode())
        # update etag
        etag_cache[meta_id] = r.headers.get('etag')
        save_etag_cache()
        log.info("success updated %s last-modified: %s", index_url, r.headers.get("last-modified"))
        return data
    else:
        raise Exception("fetch GET {} failed".format(index_url))


def is_index_update(meta_id, current_etag):
    cached_etag = etag_cache.get(meta_id)
    if cached_etag is None:
        return True
    log.debug("compare etag %s, %s", cached_etag, current_etag)
    return cached_etag != current_etag


def query_index(index_url, retry):
    try:
        r = requests.get(index_url)
        return r
    except Exception as e:
        log.warning("update failed for %s, retry %d", e, retry)
        if retry > 0:
            return query_index(index_url, retry - 1)
        log.error("all retry failed on %s", index_url)


def save_file(file_path: str, content: bytes):
    task_queue.put((file_path, content))


async def send_content(req, content: bytes):
    req.write(content)
    req.set_header('Content-Type', 'application/octet-stream')
    await req.finish()


def assume_file_parent(pkg_path):
    if not pkg_path.parent.exists():
        pkg_path.parent.mkdir(parents=True)


def file_save_worker():
    while True:
        file_path, file_content = task_queue.get()
        assume_file_parent(Path(file_path))
        with open(file_path, 'wb') as fh:
            fh.write(file_content)
            log.info(f'save  {file_path}')

        task_queue.task_done()
