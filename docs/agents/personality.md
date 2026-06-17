# Agent Personality

The personality engine (`buddy.agent.personality`) models an agent's traits,
emotional state, and communication style, and uses them to color responses. It
is a heuristic, rule-based layer that adapts to a conversation over time.

!!! note "What it does"
    The engine shapes *tone and phrasing* — it tracks emotions, picks a
    communication style, and applies stylistic flourishes on top of a base
    response. It is not a separate model; it post-processes text and updates
    internal state from keyword/context signals.

Personality is feature-gated:

```python
from buddy import check_feature
assert check_feature("personality")

from buddy import (
    PersonalityEngine, PersonalityProfile, EmotionalState, CommunicationStyle
)
```

## The profile

`PersonalityProfile` is a Pydantic model describing an agent's disposition:

| Area | Fields (selection) |
|------|--------------------|
| Identity | `personality_id`, `name`, `description` |
| Traits | `traits` (per `PersonalityDimension`) |
| Emotions | `current_emotions`, `emotional_baseline`, `emotional_volatility`, `emotional_recovery_rate` |
| Communication | `preferred_communication_style`, `style_adaptability` |
| Behavior | `dominant_behaviors`, `behavioral_flexibility` |
| Adaptation | `learning_rate`, `adaptation_threshold`, `memory_influence` |

Traits use the Big Five plus AI-specific dimensions
(`PersonalityDimension`): openness, conscientiousness, extraversion,
agreeableness, neuroticism, intelligence, creativity, adaptability, empathy,
humor.

## Emotional states & communication styles

`EmotionalState` enumerates emotions the engine tracks, including `JOY`,
`SADNESS`, `ANGER`, `FEAR`, `CURIOSITY`, `CONFIDENCE`, `FRUSTRATION`,
`EXCITEMENT`, `CALM`, and `NEUTRAL`.

`CommunicationStyle` defines how the agent phrases output:

| Style | Tone |
|-------|------|
| `FORMAL` | Professional, structured |
| `CASUAL` | Relaxed, conversational |
| `TECHNICAL` | Precise, expert-level |
| `EMPATHETIC` | Warm, supportive |
| `DIRECT` | Concise, straightforward |
| `DIPLOMATIC` | Tactful, careful |
| `HUMOROUS` | Light-hearted, witty |
| `INSPIRATIONAL` | Motivating |

## Using the engine directly

```python
from buddy.agent.personality import PersonalityEngine

engine = PersonalityEngine()   # builds a balanced default profile

# Update internal emotional/style state from user input
data = engine.process_interaction("This is amazing, thank you so much!")
print(data["primary_emotion"], data["communication_style"])

# Color a base answer with the current personality
styled = engine.generate_personality_driven_response(
    "Here is the report you requested."
)
print(styled)

# Inspect a summary of current traits and dominant emotions
print(engine.get_personality_summary())
```

## Adding personality to an agent

`PersonalityMixin` wires the engine into an agent class. Compose it with `Agent`
so it can read its keyword arguments (`personality_enabled`,
`adaptive_personality`, `emotional_awareness`, `personality_config`):

```python
from buddy import Agent
from buddy.agent.personality import PersonalityMixin

class FriendlyAgent(PersonalityMixin, Agent):
    pass

agent = FriendlyAgent(personality_enabled=True, adaptive_personality=True)

# Generate a personality-flavored version of a response
styled = agent.generate_personality_response("Your order has shipped.")

# Set an explicit emotional state
from buddy import EmotionalState
agent.set_emotional_state({EmotionalState.CONFIDENCE: 0.8})

# Read the current personality state
print(agent.get_personality_state())
```

!!! tip "Adapting to the user"
    With `adaptive_personality=True` and a high `style_adaptability`, the engine
    nudges `preferred_communication_style` toward the user's detected style over
    repeated interactions. Lower `style_adaptability` keeps the agent's voice
    stable.

!!! warning "Stylistic, not factual"
    Personality affects delivery, including occasional emoji and empathetic
    phrasing. Keep it disabled (`personality_enabled=False`) for strictly
    formal or machine-consumed output.
