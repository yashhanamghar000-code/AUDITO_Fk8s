# add-ai-core

Shared **domain layer** for the ADD_AI / AUDITO AI platform: `DocumentChunk`,
`ChatAnswer`, `Citation`, and every `Ixxx` interface (`IEmbeddingProvider`,
`IVectorStore`, `ILLMClient`, `IReranker`, `ISparseIndex`, `IDocumentParser`,
`IPasswordHasher`, `ITokenService`, repository interfaces).

This package has **zero framework dependencies** and is not a running
service — it does not get its own Docker image. It's the contract every
other repo (services and microservices) is written against, so:

- every microservice repo depends on `add-ai-core` to know the shape of
  the data it sends/receives over HTTP
- the `add-ai-backend` repo depends on it for its service layer + the
  HTTP-client adapters that implement each interface

## Local development (editable install)

Because every other repo needs to pick up your changes here immediately
while you're iterating, install it in **editable mode** from each
consumer repo instead of publishing a version and bumping it every time:

```bash
# from any consumer repo's virtualenv
pip install -e ../add-ai-core
```

or, if the consumer repo is a Docker container and you want live-reload
during local development, bind-mount this repo into the container and
`pip install -e /add-ai-core` in the container's entrypoint/dev
Dockerfile stage (see each service's `docker-compose.override.yml`).

## Testing this repo standalone

```bash
pip install -e .[dev]
pytest
```

## Publishing changes

Consumers pin this in their `requirements.txt` as:

```
git+https://github.com/<you>/add-ai-core.git@v0.1.0
```

Tag a release here whenever the contract changes, then bump the pinned
tag in whichever consumer repos need the new version. This is what keeps
"swap an adapter" cheap: the interface is versioned once, in one place.
