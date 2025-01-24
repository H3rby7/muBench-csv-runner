# µBench CSV Runner

Adapted excerpt from the [µBench repository](https://github.com/mSvcBench/muBench)

Adapts the `Benchmark/Runner` to take a CSV file with timestamps and traces as input to replay traces.

## Why adapt?

Original FileRunner has no support for POST requests (required to run traces against the service-cell).

Automatic docker build+publish via github actions ensuring consistency across updates.

Also provides a local docker-compose variant, mounting necessary files to test runner locally in a dry-run.

    docker-compose up
