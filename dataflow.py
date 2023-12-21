import logging
from datetime import timedelta
from typing import Optional, Tuple

import requests
from bytewax import operators as op
from bytewax.connectors.stdio import StdOutSink
from bytewax.dataflow import Dataflow
from bytewax.inputs import SimplePollingSource

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class HNSource(SimplePollingSource):
    def next_item(self):
        return (
            "GLOBAL_ID",
            requests.get("https://hacker-news.firebaseio.com/v0/maxitem.json").json(),
        )


def get_id_stream(old_max_id, new_max_id) -> Tuple[str,list]:
    if old_max_id is None:
        # Get the last 10 items on the first run.
        old_max_id = new_max_id - 10
    return (new_max_id, range(old_max_id, new_max_id))


def download_metadata(hn_id) -> Optional[Tuple[str, dict]]:
    # Given an hacker news id returned from the api, fetch metadata
    # Try 3 times, waiting more and more, or give up
    data = requests.get(
        f"https://hacker-news.firebaseio.com/v0/item/{hn_id}.json"
    ).json()

    if data is None:
        logger.warning(f"Couldn't fetch item {hn_id}, skipping")
        return None
    return (str(hn_id), data)


def recurse_tree(metadata, og_metadata=None) -> any:
    if not og_metadata:
        og_metadata = metadata
    try:
        parent_id = metadata["parent"]
        parent_metadata = download_metadata(parent_id)
        return recurse_tree(parent_metadata[1], og_metadata)
    except KeyError:
        return (metadata["id"], 
                {
                    **og_metadata, 
                    "root_metadata":metadata
                }
                )


def key_on_parent(key__metadata) -> tuple:
    key, metadata = recurse_tree(key__metadata[1])
    return (str(key), metadata)


flow = Dataflow("hn_scraper")
max_id = op.input("in", flow, HNSource(timedelta(seconds=15)))
ids = op.stateful_map("range", max_id, lambda: None, get_id_stream).then(
    op.flat_map, "strip_key_flatten", lambda key_ids: key_ids[1]).then(
    op.redistribute, "redist")
items = op.filter_map("meta_download", ids, download_metadata)
split_stream = op.branch("split_comments", items, lambda item: item[1]["type"] == "story")
stories = split_stream.trues
comments = split_stream.falses
comments = op.map("key_on_parent", comments, key_on_parent)
op.output("stories-out", stories, StdOutSink())
op.output("comments-out", comments, StdOutSink())
