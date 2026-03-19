# Automixer
Multimedia automation for video mixing sermon/presentation (switching between camera and slide).

## How does it work? (overview)
### Camera to slide
Automixer decides to set program to **slide** whenever a slide change is detected.

Multiple slide scene is supported. If the current preview is a slide scene, it will be set as program. Else, automixer will set the default slide scene as program.

### Slide to camera
Automixer decide to set program to camera when the current slide text (extracted with OCR) was read (using AI-based transcription) to a certain threshold.

The comparison is done by thresholding weighted summation of ROUGE-1 and ROUGE-L.


## Support
### Switcher Software
- OBS
### Transcriber
- OpenAI
### Notifier
- MQTT

## Requirements
- Python >= 3.11
- OpenAI API Key (with transcription permission)
- Virtual audio cable (VAC)

## Install
> [!TIP]
> It is recommended to use virtual environment.

1. Firstly, [**install Torch**](https://pytorch.org/get-started/locally/) according to your device setup.

2. Then, **clone and install this repo** (including extra for OBS and MQTT notification)
    ```bash
    git clone https://github.com/nathtjan/automixer.git
    cd automixer
    pip install .[obs,mqtt]
    ```

    If you do not use notification service, `pip install .[obs]` is enough.

3. **Copy environment file**
    ```bash
    cp .env.example .env
    ```

4. **Edit `.env` file** (see [Environment Variables Reference](#environment-variables-reference))

5. **Copy configuration file**
    ```bash
    cp config.yaml.example config.yaml
    ```

6. **Edit configuration file** (see [Configuration Reference](#configuration-reference))

## Setup
### OBS
1. Set virtual camera to output your slide.
2. Set audio monitor device to be sent to virtual audio cable, and ensure (preferably only) the speaker audio get sent to monitor device.

## Run
Run automixer from terminal.

### Run from script
```bash
automixer
```
Automixer automatically install `automixer` script upon installation.

### Run as package
```bash
python -m automixer
```

### Config file
Automixer by default uses `config.yaml` in current working directory. You can change the config file used by specifying the config file path using `--config` flag:
```bash
automixer --config ./another-config.yaml
```

### TUI vs Headless
Automixer by default provides Terminal User Interface (built with Textual) for live state update and logs. In TUI mode:
- Press `p` to pause/resume processing.
- Press `q` to quit.

You can disable the TUI by running in headless mode using `--headless` flag:
```bash
automixer --headless
```

### Verbose mode
Run Automixer in verbose mode to outputs debug log using `-v` or `--verbose` flag.
```bash
automixer -v
```

### File logging
You can save logs to a file in two ways (mutually exclusive):

- `--log-dir`: provide a directory and Automixer will create a log file named with startup timestamp, ending with `.log`.
- `--log-file`: provide the exact log file path. If the file already exists, the logs will be appended instead of being overwritten.

Examples:
```bash
automixer --log-dir ./logs
```
or
```bash
automixer --log-file ./logs/session.log
```

## Environment Variables Reference
- `OPENAI_API_KEY` (required): used by the OpenAI client for authentication.
- `OBS_PASSWORD` (optional): OBS WebSocket password (used when not provided in config).
- `MQTT_HOST` (optional): MQTT broker host (used when notification service uses `${MQTT_HOST}`).
- `MQTT_PORT` (optional): MQTT broker port (used when notification service uses `${MQTT_PORT}`).
- `MQTT_USERNAME` (optional): MQTT username.
- `MQTT_PASSWORD` (optional): MQTT password.


## Configuration Reference

> [!IMPORTANT]
> While this documentation uses dot notation for nested structures, the configuration file should always uses traditional YAML nested format.

Configuration file starts with the `version` of it. Look at `config.yaml.example` for current version number.

> [!TIP]
> Automixer support environment variable substitution in the config file using Docker Compose file syntax (e.g. `${OBS_PASSWORD}`).

### Mixer Services
`mixer.services` is a list of service configurations, which type is determined by the field `service_type`.

#### Camera Service (`camera`)

* `camera` (`dict`):
Initialization keyword arguments for `cv2.VideoCapture`. Ensure you set the `index` argument.

* `read_delay` (`float`):
Delay between each frame capture

---

#### Interaction Service (`interaction`)

* `interactor.software` (`str`):
Name of switcher software used in lowercase (currently only support `'obs'`)

* `interactor.host` (`str`):
IP address of OBS Websocket Server

* `interactor.port` (`str`):
Port of OBS Websocket Server

* `slide_scenenames` (`list[str]`):
Name of scenes that is considered as showing presentation.

* `default_slide_scenename` (`str`):
Name of a scene that is considered as default scene showing presentation. This is used when preview scene is not a presentation scene. Make sure this scene name exists in `slide_scenenames`.

* `cam_scenename` (`str`):
Name of a scene that is considered as showing camera (speaker).

* `program_check_delay` (`float`):
Delay between each program check (program name request).

---

#### Mic Service (`mic`)

* `input_stream` (`dict`):
Initialization keyword arguments for `sounddevice.InputStream`. Normally, the `device` argument used will be the VAC input device index.

* `read_frames` (`int`):
The number of audio frames read for each audio segment. For example, if the sampling rate is set to `48000` and you want to set each audio segments to be 2 seconds long, set this value to `96000`. Consider the latency-accuracy tradeoff when changing this value.

---

#### Mixing Service (`mixing`)

* `slide2cam_scorer` (`dict`):
Scorer configuration used to compute `slide2camscore`. Supported scorer types are:
`rouge_1gram`, `rouge_l`, and `weighted_average`.

* `slide2cam_jury` (`dict`):
Jury configuration used to decide whether the score sequence indicates switching to camera.
Supported jury types are: `threshold`, `total_variation_threshold`, `and`, `or`.

* `slide2cam_delay` (`int`):
Delay between the time the slide2cam decision is made and it being acted upon. If a slide change is detected during this delay period, the slide2cam decision will be overriden/cancelled.

##### Scorer Type: `rouge_1gram`

* `scorer_type` (`"rouge_1gram"`):
Word-level fuzzy LCS scorer. Compares OCR words and transcription words with edit-distance tolerance and returns a normalized overlap score.

* `tolerance` (`int`, default: `3`):
Maximum Levenshtein distance for two words to be treated as equal.

##### Scorer Type: `rouge_l`

* `scorer_type` (`"rouge_l"`):
Exact-token LCS scorer. Computes ROUGE-L style sequence overlap between slide text and transcription.

##### Scorer Type: `weighted_average`

* `scorer_type` (`"weighted_average"`):
Composite scorer that combines multiple child scorers.

* `weight_scorer_set` (`list[dict]`):
List of weighted scorer items used to compute the final score as a weighted mean.

* Weighted scorer item fields:
Each item must provide `weight` (`float`) and `scorer` (`dict`, one scorer config).

##### Jury Type: `threshold`

* `jury_type` (`"threshold"`):
Passes when the latest score is greater than or equal to `threshold`.

* `threshold` (`float`):
Minimum latest-score value required to pass.

##### Jury Type: `total_variation_threshold`

* `jury_type` (`"total_variation_threshold"`):
Passes when score fluctuation is stable enough over a selected window.

* `threshold` (`float`):
Maximum allowed total variation (sum of absolute deltas between consecutive scores in the window).

* `length` (`int`, default: `0`):
Window size for the variation check. `0` means use all available scores.

##### Jury Type: `and`

* `jury_type` (`"and"`):
Logical AND composition. Passes only if all child juries pass.

* `juries` (`list[dict]`):
List of child jury configs.

##### Jury Type: `or`

* `jury_type` (`"or"`):
Logical OR composition. Passes if at least one child jury passes.

* `juries` (`list[dict]`):
List of child jury configs.

---

#### OCR Service (`ocr`)

* `reader` (`dict`):
Initialization keyword arguments for `easyocr.reader`. Ensure you set the `lang_list` argument.

* `expect_frame_timeout` (`float`):
Maximum duration between program change happening and a valid camera frame is received to be OCR-ed.

---

#### Slide Service (`slide`)

* `diff_threshold` (`int`):
Threshold to detect slide difference.

* `edge_threshold` (`int`):
Threshold used when determining if a pixel is semantically an edge. This is done for ignoring noises around semantic edges. If you do not need this, set this value as high as possible to disable it.

* `full_black_threshold_mean` (`int`):
Threshold of mean used when determining a frame is full black.

* `full_black_threshold_std` (`int`):
Threshold of standard deviation used when determining a frame is full black.

---

#### Transcription Service (`transcription`)

* `transcriber.client` (`dict`):
Initialization keyword arguments for `openai.OpenAI`. This is usually left empty if you already provide the API key using environment variable.

* `transcriber.model` (`str`):
OpenAI model used for transcription

* `transcriber.language` (`str`):
Language that may appear in the audio being transcribed.

* `run_delay` (`float`):
Additional delay between each transcription process.

---

#### Notification Service (`notification`)

`notification` service sends selected events through a notifier backend.

* `notifier` (`str`):
Notifier backend configuration.

* `include_event_types` (`list[str]`, optional):
If provided, only events in this list are sent. Values must use event names
(for example `program_change`), not class names. Defaults to all events if not provided.

* `exclude_event_types` (`list[str]`, optional):
Events in this list are not sent (applied after include filtering). Values
must use event names.

##### MQTT Notifier (`mqtt`)

* `host` (`str`):
MQTT broker hostname or IP.

* `port` (`int`, default: `1883`):
MQTT broker port.

* `base_topic` (`str`):
MQTT base topic used for publishing event notifications.
The events will be published to `{base_topic}/{event_type_name}`
(e.g. `automixer/events/program_change`)
for more robust topic/event subscription.

* `qos` (`int`, default: `0`):
MQTT QoS level (`0`, `1`, `2`).

* `retain` (`bool`, default: `false`):
Whether published notifications are retained by broker.

* `keepalive` (`int`, default: `60`):
MQTT keepalive interval in seconds.

* `use_tls` (`bool`, default: `false`):
Enable TLS for MQTT connection.

* `mqtt_version` (`int`, default: `5`):
MQTT protocol version value passed to Paho client.

* `client_id` (`str`, optional):
Custom MQTT client id.

* `username` (`str`, optional):
MQTT username.

* `password` (`str`, optional):
MQTT password.

Published payload format:
```json
{
    "event_type_name": "program_change",
    "data": {"...": "..."},
    "timestamp": "2026-03-17T12:34:56.000000+00:00"
}
```

In verbose mode (`-v`), MQTT notifier also logs callback lifecycle information (connect, disconnect, publish ack, etc.) to simplify broker troubleshooting.


## License
Automixer is licensed under GNU GPLv3 (see [LICENSE](LICENSE))
