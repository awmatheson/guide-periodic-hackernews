# Template for a sample app

- Skill level
    
    **Beginner, no prior knowledge requirements**
    
- Time to complete
    
    **Approx. 25 min**
    

Introduction: *A common pattern is to poll endpoints to get the most recent updates from an api or service if they don't offer a push based service like server-sent events or websockets. In this guide we will show how you can use bytewax to create a data stream by polling an endpoint using the PeriodicInput connector (Available in > v0.17). In our code we will publish the data stream to a Redpanda topic, so it can be used by multiple services downstream.*

## ****Prerequisites****

**Kafka/Redpanda**

Before starting this guide, you will need to have Redpanda (or kafka) installed. You should have some familiarity with how to setup one or the other. Checkout the [Redpanda documentation](https://docs.redpanda.com/current/get-started/quick-start/) to get started. The docker compose yaml file has been included here for ease of use, but it is recommended to use the most recent one from the redpanda documentation.

**Python modules**
bytewax==0.17.1
confluent-kafka

## Your Takeaway

*The main takeaway from this guide is that you will be able to leverage Bytewax to turn an HTTP endpoint into a data stream to compute live analytics, react to changes in the stream in real-time or publish the data to Kafka to be consumed by other applications*

## Table of content

- All-in-one
- Breaking it apart
- Feature Pipelines

## All-in-one

The `all_in_1_dataflow.py` will allow you to run the polling and count all in one dataflow and Redpanda is not needed. To run it, you can simply run `python -m bytewax.run all_in_1_dataflow:run_hn_flow()` if you want to pass in a certain item id, you can put the id in the parentheses. To scale this pipeline up add the -p flag and the number of processes. 


## Breaking it apart

It is important to have some redundancy in our code because things eventually fail. Or just so we can have multiple pipelines consuming the same raw hacker news stream without having to create a very complicated single dataflow or without polling the same endpoint for each pipeline. This section breaks out the hacker news stream from the count comments and uses redpanda as the durable layer between them

To run this setup you should first start Redpanda, then create the topic `hacker-news-raw`. You can do this in the console UI provided by Redpanda.

```shell
docker compose up -d
```

Then open the UI at localhost:8080

Next you can run the base dataflow to stream the results into redpanda.

`python -m bytewax.run base_dataflow:run_hn_flow()`

Once again if you would like to start from a specific ID you can pass that through and if you would like to scale this across processes, use -p followed by the number of processes.

## Feature Pipelines

Now that we have our raw data stream available we can write multiple feature pipelines. First let's rerun the same comment count we had running before.
`python -m bytewax.run feature1_dataflow.py`

## Summary

That’s it, you are awesome.

## We want to hear from you!

If you have any trouble with the process or have ideas about how to improve this document, come talk to us in the #troubleshooting Slack channel!

## Where to next?

- [More guides](https://bytewax.io/guides)

[Share your tutorial progress!](https://twitter.com/intent/tweet?text=I%27m%20mastering%20data%20streaming%20with%20%40bytewax!%20&url=https://bytewax.io/tutorials/&hashtags=Bytewax,Tutorials)
