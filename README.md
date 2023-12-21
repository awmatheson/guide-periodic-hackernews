# Streaming Hacker News

- Skill level
    
    **Intermediate, no prior knowledge requirements**
    
- Time to complete
    
    **Approx. 25 min**
    

Introduction: *A common pattern is to poll endpoints to get the most recent updates from an api or service if they don't offer a push based service like server-sent events or websockets. In this guide we will show how you can use bytewax to create a data stream by polling an endpoint using the PeriodicInput connector (Available in > v0.17). In our code we will publish the data stream to a Redpanda topic, so it can be used by multiple services downstream.*

## ****Prerequisites****

**Python modules**
bytewax==0.17.1
requests

## Your Takeaway

*The main takeaway from this guide is that you will be able to leverage Bytewax to turn an HTTP endpoint into multiple data streams to compute live analytics, react to changes in the stream in real-time or publish the data to Kafka to be consumed by other applications*

## Table of content

- Polling Input
- Cleaning things up and enriching
- Splitting the stream
- A little fun recursion
- Real-time analysis

#### Step-by-Step Breakdown

##### 1. Setting Up the Environment

```python
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
```

- We import necessary libraries and set up logging. `requests` is used for HTTP requests, and Bytewax components are imported for the dataflow.

##### 2. Defining the Data Source

```python
class HNSource(SimplePollingSource):
    def next_item(self):
        return (
            "GLOBAL_ID",
            requests.get("https://hacker-news.firebaseio.com/v0/maxitem.json").json(),
        )
```

- `HNSource` is a custom polling source extending Bytewax's `SimplePollingSource`.
- It periodically polls the Hacker News API for the latest item ID.

Our new HNSource input connector can be used as the input to our dataflow object as shown below.

```python
flow = Dataflow("hn_scraper")
max_id = op.input("in", flow, HNSource(timedelta(seconds=15)))
```

##### 3. Processing ID Stream

The output of our input is a single id, we want to convert that into a stream of the most recent ids since we last polled the endpoint. To do that, we will use a stateful map operator that keeps track of the last id used and returns a list of ids. We will take these and flat map them so we will operate on them as a stream and then use the redistribute operator to spread the ids over multiple workers if workers are configured.

```python
def get_id_stream(old_max_id, new_max_id) -> Tuple[str,list]:
    if old_max_id is None:
        old_max_id = new_max_id - 10
    return (new_max_id, range(old_max_id, new_max_id))

ids = op.stateful_map("range", max_id, lambda: None, get_id_stream).then(
    op.flat_map, "strip_key_flatten", lambda key_ids: key_ids[1]).then(
    op.redistribute, "redist")
```

##### 4. Downloading Item Metadata

```python
def download_metadata(hn_id) -> Optional[Tuple[str, dict]]:
    data = requests.get(
        f"https://hacker-news.firebaseio.com/v0/item/{hn_id}.json"
    ).json()

    if data is None:
        logger.warning(f"Couldn't fetch item {hn_id}, skipping")
        return None
    return (str(hn_id), data)

items = op.filter_map("meta_download", ids, download_metadata)
```

- Fetches metadata for a given Hacker News ID.
- If the data is not available, it logs a warning and skips that item.

##### 7. Splitting the Stream into Comments and Stories

The stream contains comments and stories that are different shapes and we want to split these out. To do this, we can use the branch operator. 

```python
split_stream = op.branch("split_comments", items, lambda item: item[1]["type"] == "story")
stories = split_stream.trues
comments = split_stream.falses
```

##### 6. Keying on Parent

We have both comments and stories in our original stream and the comments aren't necessarily attributed directly to the story if the comment is not a direct descendant of the story, but rather another comment. use the key_on_parent function, which will then call the recurse_tree function which recursively fetches parent metadata for comments, allowing us to track the comment tree.

```python
def key_on_parent(key__metadata) -> tuple:
    key, metadata = recurse_tree(key__metadata[1])
    return (str(key), metadata)


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

comments = op.map("key_on_parent", comments, key_on_parent)
```

##### 9. Outputting Data

```python
op.output("stories-out", stories,StdOutSink())
op.output("comments-out", comments, StdOutSink())
```

Outputs both stories and comments to standard output.

#### Conclusion

Congratulations! You've just built a real-time Hacker News scraper using Bytewax. This scraper fetches the latest stories and comments, processes them, and outputs the results. Bytewax's dataflow approach makes it easy to handle streaming data and perform complex processing tasks. Happy scraping!

## We want to hear from you!

If you have any trouble with the process or have ideas about how to improve this document, come talk to us in the #troubleshooting Slack channel!

## Where to next?

- [More guides](https://bytewax.io/guides)

[Share your tutorial progress!](https://twitter.com/intent/tweet?text=I%27m%20mastering%20data%20streaming%20with%20%40bytewax!%20&url=https://bytewax.io/tutorials/&hashtags=Bytewax,Tutorials)
