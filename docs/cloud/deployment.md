---
sidebarDepth: 0
---

# From Core to Cloud: Deployment Considerations

There are many considerations that need to be made when moving from a local workflow to a distributed, dockerized workflow.  This document attempts to highlight many of these considerations and potential "gotchas" that users might encounter as they promote their workflows to Prefect Cloud.

[[toc]]

## Docker

Prefect Cloud requires the use of Docker containers.  Docker provides an excellent industry-standard abstraction for shipping code along with all of its dependencies for runtime consistency in diverse environments.  Ultimately, to deploy a Flow to Cloud it needs to be "packaged up" inside a Docker image that is then pushed to a registry of your choosing.  

### How are Prefect Flows stored inside Docker containers?

Whenever you call `flow.deploy` or build a [Docker storage object](../api/unreleased/environments/storage.html#docker) yourself, Prefect will perform the following actions:

- calls `cloudpickle.dumps(flow)` on your Flow object to convert it to serialized bytes
- stores these bytes inside the Docker image in the `/root/.prefect/` directory
- runs various health checks on your Flow inside the image to try and catch any issues

::: warning cloudpickle
[cloudpickle](https://github.com/cloudpipe/cloudpickle) is an excellent alternative to the standard libary's Pickle protocol for converting Python objects to a serialized byte representation.  Note that cloudpickle typically stores _imported objects_ as importable references.  So, for example, if you used a function `foo` that you imported as `from my_file import foo`, cloudpickle (and consequently Prefect) will assume this same import can take place inside the Docker container.  For this reason, it is considered best practice in Prefect to ensure all utility scripts and custom Python code be accessible on your Docker image's system `PATH`.
:::

### How are Prefect Flows run inside Docker containers?

Whenever a Prefect Cloud flow run is created and submitted for execution, Prefect performs the following actions inside your Flow's Docker image:
- calls `cloudpickle.load(...)` on the file described above containing the byte-representation of your Flow
- calls `flow.environment.setup` for your flow's specified [execution environment](../api/unreleased/environments/execution.html)
- calls `flow.environment.execute` 

Ultimately, regardless of the execution environment you use, a single `CloudFlowRunner` is created to run your Flow and configure it to communicate back to Prefect Cloud.

### Dependencies

Typically Prefect Flows have many dependencies; sometimes these dependencies are popular public Python packages, othertimes they are intricate non-Python bindings.  Either way, Docker provides a convenient abstraction for handling all forms of Flow dependencies:

- **PyPI dependencies**: for `pip` installable dependencies from PyPI, you can use the `python_dependencies` keyword argument on Docker storage objects and Prefect will automatically install these dependencies via `pip`
- **non-PyPI dependencies**: for all other forms of dependencies, the best way to include them in your Docker container is through your choice of `base_image`.  You can specify any base image that both you and your Prefect Agent have access to (note that Cloud _never_ requires access to your registries) that contains all your necessary dependencies.  Note that you might have to build one yourself if your dependencies are proprietary.  When not provided, Prefect automatically detects your local version of Prefect and Python and attempts to select an appropriate base image for your Flow.

::: warning Environment Variables
Prefect's Docker storage abstraction also exposes the ability to set environment variables on your image.  Oftentimes environment variables are used to store sensitive information (e.g., `GOOGLE_APPLICATION_CREDENTIALS`).  As a matter of best practice, you should only hardcode environment variables in Docker images if you are comfortable with all users who have pull access to your image seeing these values.
:::

## Data Handling

Data can be exchanged between Prefect Tasks as a first class operation.  This is achieved by creating tasks which accept inputs and return values (using Python's standard `return` statement).  Note that this section is _only_ focused on this type of data exchange.  Prefect does not track data which is handled _within_ your tasks (e.g., if your task extracts data from some third-party location or writes to some persisted storage but never returns this data).

### Result Handlers

During normal execution, the data exchanged between tasks is usually passed in memory.  However, there are [many situations](dataflow.html#when-is-data-persisted) in which this data needs to be _persisted_ somewhere.  Data is only persisted in Prefect Cloud using a [Result Handler](../core/concepts/results.html). Note that unless you turn [checkpointing](../core/concepts/persistence.html#checkpointing) on for your local Core flows, Result Handlers are never exercised in Core.

You want to choose a result handler that matches both your Task's data type as well as your preferred location for tracking the data.  For example, the `JSONResultHandler` is only capable of handling JSON-compatible data, whereas the `GCSResultHandler` can handle any `cloudpickle`-able Python object.  You can also always write a completely custom handler for your Flows and Tasks to use.

::: tip Debugging
If you experience a Task failure with the message:
```python
AssertionError: Result has no ResultHandler
```
it means that _something_ triggered Cloud to persist data, but neither your Task nor your Flow had a result handler to use.
:::

### Secrets

If your Flow relies on the use of Prefect Secrets, you will need to communicate those Secrets to Prefect Cloud via one of Prefect's [APIs](concepts/secrets.html#cloud-execution).  We are currently working on a more pluggable version of Secrets that will allow you to more easily swap out Prefect's Secret storage with your favorite secret provider.

## Infrastructure

Prefect Cloud workflows are executed inside Docker containers running in the execution environment of your choosing.  The only requirement for Prefect Cloud and its Agents are the ability to pull Docker images and "submit" them for execution in some fashion. This means that you may need to reconsider references to local filepaths, ensure certain environment variables are set, and make sure you understand any networking configurations that you rely on. 

Prefect makes it easy to control:
- all aspects of the Docker image your Flow is stored within
- what types of [Prefect Agents](agent/overview.html) can submit your Flows for execution
- what [execution environment](../api/unreleased/environments/execution.html) your Flow runs

Note that different workflows will have different resource requirements during execution.  For example, if you run a CPU intensive Flow using a Kubernetes Agent you should make sure your Kubernetes cluster has a sufficiently large node pool to run on.
