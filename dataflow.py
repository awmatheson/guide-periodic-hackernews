import requests
from datetime import timedelta
import json
import time

from bytewax.connectors.periodic import SimplePollingInput
from bytewax.connectors.stdio import StdOutput
# from bytewax.connectors.kafka import KafkaOutput as RedpandaOutput
from bytewax.dataflow import Dataflow

class HNInput(SimplePollingInput):
    def next_item(self):
        # Extract the first 10 item ids from newstories api.
        # You can then use the id to fetch metadata about
        # a hackernews item
        if not hasattr(self, "max_id"):
            self.max_id = requests.get("https://hacker-news.firebaseio.com/v0/maxitem.json").json()
        new_max_id = requests.get("https://hacker-news.firebaseio.com/v0/maxitem.json").json()
        print(self.max_id, new_max_id)
        ids = [int(i) for i in range(self.max_id, new_max_id)]
        self.max_id = new_max_id
        return ids
    
def download_metadata(hn_id):
    # Given an hacker news id returned from the api, fetch metadata
    req = requests.get(
        f"https://hacker-news.firebaseio.com/v0/item/{hn_id}.json"
    )
    if not req.json():
        print(f"error getting payload from item {hn_id} trying again")
        time.sleep(0.5)
        return download_metadata(hn_id)
    return req.json()

def recurse_tree(metadata):
    try:
        parent_id = metadata["parent"]
        parent_metadata = download_metadata(parent_id)
        return recurse_tree(parent_metadata)
    except KeyError:
        return (metadata["id"], {**metadata, "key_id": metadata["id"]})

def key_on_parent(metadata: dict) -> tuple:
    key, metadata = recurse_tree(metadata)
    return (key, metadata)

def serialize_with_key(key_payload):
    key, payload = key_payload
    return json.dumps(key).encode("utf-8"), json.dumps(payload).encode("utf-8")
    
flow = Dataflow()
flow.input("in", HNInput(timedelta(seconds=15)))
flow.flat_map(lambda x: x)
# flow.inspect(print)
# If you run this dataflow with multiple workers, downloads in
# the next `map` will be parallelized thanks to .redistribute()
flow.redistribute()
flow.map(download_metadata)
flow.inspect(print)

# We want to keep related data together so let's build a 
# traversal function to get the ultimate parent
flow.map(key_on_parent)

# Now we can serialize our key and value for Redpanda
flow.map(serialize_with_key)

# flow.output("kafka-out", RedpandaOutput(["localhost:9092"], "hacker-news-raw"))
flow.output("std-out", StdOutput())