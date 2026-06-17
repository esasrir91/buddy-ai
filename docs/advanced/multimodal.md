# Multimodal Agents

`MultiModalAgent` (`buddy.multimodal`) extends [`Agent`](../agents/agent-class.md)
with structured handling for images, audio, and video alongside text. It defines
typed analysis results and a fusion pipeline for reasoning across modalities.

!!! note "Optional dependency"
    Vision and audio processing require the `multimodal` extra:

    ```bash
    pip install "buddy-ai[multimodal]"
    ```

    This installs `Pillow`, `opencv-python`, `librosa`, and `soundfile`. The
    feature is gated — confirm it with `check_feature("multimodal")`.

```python
from buddy import check_feature, MultiModalAgent, ModalityType, MultiModalResponse
assert check_feature("multimodal")
```

## Modalities

`ModalityType` enumerates supported inputs:

| Member | Value |
|--------|-------|
| `ModalityType.TEXT` | `"text"` |
| `ModalityType.IMAGE` | `"image"` |
| `ModalityType.AUDIO` | `"audio"` |
| `ModalityType.VIDEO` | `"video"` |

A `MultiModalAgent` always supports `TEXT`. Image, audio, and video become
available when the corresponding model wrapper (`vision_model`, `audio_model`,
`video_model`) is configured on the agent. Inspect what is enabled with the
`supported_modalities` property:

```python
from buddy.models.openai import OpenAIChat

agent = MultiModalAgent(model=OpenAIChat(id="gpt-4o"))
print(agent.supported_modalities)   # [ModalityType.TEXT] until others are set
```

!!! warning "Modality guards"
    Calling `process_image`, `process_audio`, or `process_video` without the
    matching model raises `ValueError` ("… processing not available. Configure
    *_model."). Configure the relevant model wrapper before invoking these
    methods.

## Processing methods

| Method | Returns | Analysis types |
|--------|---------|----------------|
| `process_image(image, prompt, analysis_type)` | `ImageAnalysis` | `general`, `detailed`, `objects`, `text`, `faces` |
| `process_audio(audio, prompt, analysis_type)` | `AudioAnalysis` | `transcription`, `analysis`, `speaker`, `emotion` |
| `process_video(video, prompt, analysis_type)` | `VideoAnalysis` | `general`, `activities`, `objects`, `faces`, `audio` |
| `multimodal_understanding(inputs, prompt, fusion_strategy)` | `MultiModalResponse` | `early`, `late`, `hybrid` |

Inputs are flexible: images accept a file path, raw `bytes`, a `data:` URL, or a
PIL `Image`; audio and video accept a path or `bytes`.

## Result schemas

The analysis result models are Pydantic types you can rely on:

- **`ImageAnalysis`** — `description`, `objects` (`ObjectDetection`), `faces`
  (`FaceDetection`), `text_content` (`OCRResult`), `scene_type`, `colors`,
  `tags`, `confidence_score`.
- **`AudioAnalysis`** — `transcription`, `segments` (`SpeechSegment`),
  `speakers`, `language`, `sentiment`, `emotions`.
- **`VideoAnalysis`** — `description`, `duration`, `frame_rate`, `resolution`,
  `activities` (`ActivityDetection`), `objects_timeline`, `faces_timeline`,
  `audio_analysis`.
- **`MultiModalResponse`** — `text_response`, `modality_analyses`,
  `cross_modal_insights`, `confidence_score`, `processing_time`.

## Cross-modal understanding

`multimodal_understanding` runs each modality, optionally fuses them, and asks
the agent's base model to produce a unified answer:

```python
response = agent.multimodal_understanding(
    inputs={
        ModalityType.TEXT: "Describe what's happening in this scene.",
        ModalityType.IMAGE: "scene.jpg",
    },
    prompt="Summarize the scene for an accessibility caption.",
    fusion_strategy="hybrid",
)
print(response.text_response)
print(response.cross_modal_insights)
```

The `modality_weights` attribute controls how much each modality contributes to
the overall `confidence_score` (text `1.0`, video `0.9`, image `0.8`, audio
`0.7` by default).

!!! note "Provider wiring"
    The processing methods return fully typed analysis objects, but the actual
    detection/transcription quality depends on the model wrapper you attach. Plug
    a provider-backed vision/audio/video model into `vision_model` /
    `audio_model` / `video_model` to get real results rather than schema
    defaults.
