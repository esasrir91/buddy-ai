# Buddy AI 3.0.0: Planning and Agent Collaboration

Buddy AI 3.0.0 strengthens task planning, agent collaboration, token management, and cross-platform tooling. Existing team workflows remain available, with new opt-in controls for delegation, parallel calls, and provider-native prompt caching.

## Agent collaboration

Agents can use built-in advisors and judges, and delegate work through subagents. Subagents use the existing team transfer mechanism:

```python
from buddy import Agent
from buddy.models.openai import OpenAIChat

model = OpenAIChat(id="gpt-4o-mini")
researcher = Agent(name="researcher", model=model)

agent = Agent(
    model=model,
    subagents=[researcher],
    advisor=True,
    judge=True,
    parallel_tool_calls=True,
    cache_prompt=True,
)

response = agent.run("Review the deployment plan")
print(response.advisor_feedback)
print(response.judge_result)
```

Advisor and judge configuration can provide custom instructions, criteria, or a separate model. `parallel_tool_calls=True` enables safe synchronous tool batches to run concurrently. Calls that need confirmation, user input, or external execution remain paused. Set `parallel_tool_calls=False` to run async tool calls sequentially.

When supported by the provider, `cache_prompt=True` enables native prompt caching and propagates the setting to auxiliary and subagent models.

## Planning and tools

`PlanningAgent` can use its configured Buddy model to decompose hierarchical plans. Plans now validate dependencies, schedule ready steps, retry failures, dispatch actions to registered tools, and preserve dependencies during optimization and replanning. If model output cannot be parsed, planning falls back to a single goal task.

The shell toolkit accepts a native shell command string or an argument list. Strings run through the host shell; argument lists run directly without a shell:

```python
from buddy.tools.shell import ShellTools

shell = ShellTools()
print(shell.run_shell_command("echo hello"))
print(shell.run_shell_command(["python", "--version"]))
```

## Token management

`TokenManager` accepts a provider-specific token counter for models without a matching bundled tokenizer. It also handles common provider usage formats, enforces explicit zero and context-window limits, and avoids counting the current request twice during limit checks.

```python
from buddy.tools.token_manager import TokenManager

manager = TokenManager(
    token_counter=lambda text: len(my_tokenizer.encode(text)),
    max_input_tokens=10000,
)
```

See the [full changelog](https://github.com/esasrir91/buddy-ai/blob/main/CHANGELOG.md) for the complete 3.0.0 change list.