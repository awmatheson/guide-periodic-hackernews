import requests
from datetime import datetime, timedelta
import time
from typing import Any, Optional

from bytewax.connectors.periodic import SimplePollingInput
from bytewax.connectors.stdio import StdOutput
from bytewax.dataflow import Dataflow

import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class HNInput(SimplePollingInput):
    def __init__(self, interval: timedelta, align_to: Optional[datetime] = None, init_item: Optional[int] = None):
        super().__init__(interval, align_to)
        logger.info(f"received starting id: {init_item}")
        self.max_id = init_item

    def next_item(self):
        '''
        Get all the items from hacker news API between 
        the last max id and the current max id
        '''
        if not self.max_id:
            self.max_id = requests.get("https://hacker-news.firebaseio.com/v0/maxitem.json").json()
        new_max_id = requests.get("https://hacker-news.firebaseio.com/v0/maxitem.json").json()
        logger.info(f"current id: {self.max_id}, new id: {new_max_id}")
        ids = [int(i) for i in range(self.max_id, new_max_id)]
        self.max_id = new_max_id
        return ids
    
def download_metadata(hn_id):
    # Given an hacker news id returned from the api, fetch metadata
    req = requests.get(
        f"https://hacker-news.firebaseio.com/v0/item/{hn_id}.json"
    )
    if not req.json():
        logger.warning(f"error getting payload from item {hn_id} trying again")
        time.sleep(0.5)
        return download_metadata(hn_id)
    return req.json()

def recurse_tree(metadata, og_metadata=None):
    if not og_metadata:
        og_metadata = metadata
    try:
        parent_id = metadata["parent"]
        parent_metadata = download_metadata(parent_id)
        return recurse_tree(parent_metadata, og_metadata)
    except KeyError:
        return (metadata["id"], 
                {
                    **og_metadata, 
                    "root_metadata":metadata
                }
                )

def key_on_parent(metadata: dict) -> tuple:
    key, metadata = recurse_tree(metadata)
    return (str(key), metadata)

class Story:
    def __init__(self):
        print(f"creating story object")
        self.comment_count = 0

    def update_count(self, metadata):
        print(metadata)
        print(self)
        self.comment_count += 1
        return (self, self.comment_count)

    
def run_hn_flow(init_item=None): 
    flow = Dataflow()
    flow.input("in", HNInput(timedelta(seconds=15), None, init_item)) # skip the align_to argument
    flow.flat_map(lambda x: x)
    # If you run this dataflow with multiple workers, downloads in
    # the next `map` will be parallelized thanks to .redistribute()
    flow.redistribute()
    flow.map(download_metadata)
    flow.inspect(logger.info)

    # We want to keep related data together so let's build a 
    # traversal function to get the ultimate parent
    flow.map(key_on_parent)
    
    # Calculate a running count of comments
    flow.stateful_map("count_comments", lambda: Story(), Story.update_count)

    flow.output("std-out", StdOutput())
    return flow