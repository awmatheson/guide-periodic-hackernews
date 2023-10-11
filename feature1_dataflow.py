import json

from bytewax.connectors.stdio import StdOutput
from bytewax.connectors.kafka import KafkaInput as RedpandaInput
from bytewax.connectors.kafka import KafkaOutput as RedpandaOutput
from bytewax.dataflow import Dataflow

import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def deserialize(key_bytes__payload_bytes):
    key_bytes, payload_bytes = key_bytes__payload_bytes
    key = str(json.loads(key_bytes)) if key_bytes else None
    payload = json.loads(payload_bytes) if payload_bytes else None
    return key, payload

class Story:
    def __init__(self):
        self.comment_count = 0

    def update_count(self, metadata):
        self.comment_count += 1
        return (self, self.comment_count)


def serialize_with_key(key_payload):
    key, payload = key_payload
    return json.dumps(key).encode("utf-8"), json.dumps(payload).encode("utf-8")

    
flow = Dataflow()
flow.input("hn-raw-input", RedpandaInput(["localhost:19092"], ["hacker-news-raw"]))
flow.inspect(logger.info)

flow.map(deserialize)

# Calculate a running count of comments
flow.stateful_map("count_comments", lambda: Story(), Story.update_count)

flow.map(serialize_with_key)

flow.output("rp-feature1-out", RedpandaOutput(["localhost:19092"], "hn-feature1"))
