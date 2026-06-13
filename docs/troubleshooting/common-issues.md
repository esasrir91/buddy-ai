# Common Issues

## `ImportError: No module named 'openai'`

The OpenAI package is a core dependency and should be installed automatically.
If it is missing, run:

```bash
pip install "buddy-ai" --upgrade
```

## `ImportError: No module named 'torch'`

Training features require PyTorch. Install the training extras:

```bash
pip install "buddy-ai[training]"
```

## `ImportError: No module named 'PIL'` or `cv2`

Multi-modal features require Pillow and OpenCV:

```bash
pip install "buddy-ai[multimodal]"
```

## `buddy --version` returns `dev-local`

This is fixed in v2.0.0. Upgrade:

```bash
pip install --upgrade buddy-ai
```

## `ValueError: Planning strategy 'reactive' not implemented`

This was a bug in v1.x. All planning strategies are implemented in v2.0.0. Upgrade:

```bash
pip install --upgrade buddy-ai
```

## Agent returns empty response

1. Check your API key is set: `echo $OPENAI_API_KEY`
2. Enable debug mode: `Agent(..., debug_mode=True)`
3. Check network connectivity: `buddy ping`

## Rate limit errors

Add retry logic or reduce request frequency:

```python
agent = Agent(model=OpenAIChat(id="gpt-4o-mini", max_retries=3))
```

## Memory not persisting between runs

Ensure you are passing the same `session_id` and `user_id` across calls:

```python
agent.run("Hello", session_id="my-session", user_id="user-123")
agent.run("Remember me?", session_id="my-session", user_id="user-123")
```

## See Also

- [Debugging](debugging.md)
- [FAQ](faq.md)
