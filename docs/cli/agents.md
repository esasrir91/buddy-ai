# Agent Commands

!!! note "There is no `buddy agent` group"
    The `buddy` CLI has no dedicated command group for running agents. You serve
    agents from **Python** (via the app classes) or, for declarative
    deployments, through the **workspace resources** system. The CLI's
    [top-level commands](overview.md) and [`buddy ws`](workspace.md) handle the
    latter.

## Serving an agent from Python

The most direct path is to build an app object and call `serve()`. For a REST
API:

```python
from buddy import Agent
from buddy.models.openai import OpenAIChat
from buddy.app.fastapi import FastAPIApp

agent = Agent(agent_id="api_agent", model=OpenAIChat(id="gpt-4o-mini"))

fastapi_app = FastAPIApp(agents=[agent])
app = fastapi_app.get_app()

if __name__ == "__main__":
    fastapi_app.serve(app, host="0.0.0.0", port=7777)
```

Run it like any script:

```bash
python my_agent.py
```

See [FastAPI Apps](../deployment/fastapi.md) for the endpoints and request
shape.

## Interactive playground

To chat with and debug an agent in the browser:

```python
from buddy.app.playground import Playground

playground = Playground(agents=[agent])
app = playground.get_app()
playground.serve(app, host="localhost", port=7777)
```

A Playground URL pointing at your local endpoint is printed to the console.

## Declarative deployment via a workspace

If you manage infrastructure with a `resources.py` file, start and stop your
agent resources through the CLI:

```bash
buddy start          # start resources defined in resources.py
buddy stop           # stop them
# or, for the active workspace:
buddy ws up
buddy ws down
```

See [Workspace Management](workspace.md) for filters and options.

## Related CLI groups

- [`buddy train`](training.md) — train a local model, then back an agent with it
  using `use_with_agent` (see [Model Training](../training/training.md))
- [`buddy pulse`](pulse.md) — run the PULSE virtual employee

## See also

- [Deployment Overview](../deployment/overview.md)
- [FastAPI Apps](../deployment/fastapi.md)
