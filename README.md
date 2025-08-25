# Video Localizer - Translator
***An automated video localizer/translator for native Indian languages.***

## 📋 Table of Contents 
- [Installation](#-installation)
- [Dependencies](#-dependencies)
- [Configuration](#️-configuration)
- [System Architecture](#️-system-architecture)
    - [Doctype Design](#-doctype-design)
    - [Doctype Dataflow & Processing](#-doctype-dataflow--processing--ux-)
    - [API Flows](#-current-api-flows)
    - [Sequence Diagram](#-sequence-diagram)
- [Contributing](#-contributing)
- [License](#-license)

---

## 📦 Installation
### Bench Installation
You can install this app using the [bench](https://github.com/frappe/bench) CLI:

```bash
cd $PATH_TO_YOUR_BENCH
bench get-app git@github.com:theapprenticeproject/Video_Translation.git --branch main
bench install-app my_app
```

### Video Preview app ( Optional )
This frappe app provides a better preview for video uploads upon saving a record for a doctype, improving user experience.
```
bench get-app git@github.com:Z4nzu/frappe-preview-attachment.git
bench --site your-site-name install-app preview_attachment
```
Reference : https://github.com/Z4nzu/frappe-preview-attachment 

## 🧰 Dependencies
### Python Depedency Management ( using `uv` )
Install `uv` : ( official site : https://docs.astral.sh/uv/getting-started/installation/ )
```
curl -LsSf https://astral.sh/uv/install.sh | sh
```
Install Dependencies: 
```
uv pip install -r pyproject.toml
```
### Core Tools/Libraries
* FFMPEG
* Bhashini API Services ( STS, Lang Detection )
* Groq ( STT - Whisper )
* Elevenlabs ( Dubbing API )


## 🛠️ Configuration
We utilise Frappe `site_config.json` for settings & environment variables ( local dev setup ).
```json
{
 "db_name": "[Your_DB_Name]",
 "db_password": "[Your_DB_Password]",
 "db_type": "mariadb",
 "db_user": "_2019e6edbf45109e",
 "max_file_size": 104857600, // based on needs
 "encryption_key": "[Encrption_Key]",
 "api_auth_value": "[API Authentication value]",
 "groq_api_key":"gs-xxxxxx",
 "elevenlabs_api_key":"sk-xxxxxx"
}
```
All values can be loaded by `frappe.conf.[variable_key_name]`


## 🏗️ System Architecture

### 📐 Doctype Design
The database schema contains this application's Doctypes: Video Info, Processed Video Info, & Educator Profile. The diagram below highlights the definitions and relationships for the doctypes afformentioned. 
```mermaid
erDiagram
    VIDEO_INFO {
        Data title
        Link educator "Educator Profile"
        Select target_lang "Hindi, Marathi, Punjabi"
        Attach original_vid
        Attach original_audio_extracted
        Datetime created_on
    }

    PROCESSED_VIDEO_INFO {
        Attach translated_aud
        Attach translated_srt
        Attach localized_vid
        Datetime processed_on
        Data status
        Link origin_vid_link "Video Info"
    }

    EDUCATOR_PROFILE {
        Data full_name
        Data email
        SmallText bio
        AttachImage prof_pic
    }

    EDUCATOR_PROFILE ||--o{ VIDEO_INFO : "uploads"
    VIDEO_INFO ||--o{ PROCESSED_VIDEO_INFO : "has"
```
---

### 🗃️ Doctype Dataflow & Processing ( UX )
The diagram illustrates dataflow for a video localization system that utilises background queues to handle a series of sequential functions/tasks. An overview of the steps are highlighted below:
1. A user uploads a video with the details, which creates a **Video Info** record. This uploaded video is saved into the local filesystem under `public/` directory of `original/` (created manually).
2. Once user initiates the process (by clicking "Start Process" button), a chain of background jobs begin. These jobs are managed by **Frappe Queues** system which allows multiple videos to be processed concurrently. Multiple queues are used each dedicated to a specific function:
    * Audio extraction function processes original video file and extracts audio file, thus placing this audio file into another queue for next step.
    * Language detection function processes audio output from previous step (audio extraction function) and detects spoken language. 
    * Subsequent API functions are called and executed in respective queues like subtitle generation, dubbing, etc.
This queuing system ensures each function is executed only after preceding function is completed.
3. As each function in queue completes, it creates and updates a record in **Processed Video Info** doctype. This new record is updated with status with the queuing process allowing us to micro-manage it. The processed Video files along with translated audio files (if any) are stored under `public/` directory of `processed/` (created beforehand).

<img width="2826" height="952" alt="image" src="https://github.com/user-attachments/assets/484acdac-d7da-41f4-af94-784e6416e022" />

---

### 🌐 Current API Flows
The diagram showcases API flow which are versioned as v1 and v2 and details it as respectively below:  
* **v1 - Non-Hindi Translations :** This flow is designed for multi-step translations often Indic languages other than hindi. Its a pipeline of API calls and local processing stages.
    * Detecting Source language is the common step among both API version which begins with Bhashini language detection API. Audio Extracted using FFMPEG & the output audio file is passed onto next step.
    * Bhashini Speech to Speech (STS) API is a core pipelined translation service which takes audio file and ouputting a new Translated audio file.
    * Muxing of the translated audio is done by overwriting(using FFMPEG) the original audio thus creating a new Translated video file with translated audio track.
    * The final step using FFMPEG is to merge the generated subtitle file with the newly created translated video file.

* **v2 - Hindi Translations :** This flow involves specialized processes for translating to Hindi for a better integrated dubbing experience and can be represented as:
    * **Path I (ElevenLabs)**:
        * The workflow takes the detected language(optional) along with video file and uses the ElevenLabs Dubbing API which handles dubbing. The API outputs a Dubbed Video thus avoiding muxing multiple times.
    * **Path II (Sievedata) :** (option)
        * This represents highly configurable, alternative service. This is intended for more requirements as it can also handle lip sync such services in addition to direct dubbing.

* **Common Processes**
    * When subtitles are needed (end of Video Processing Pipeline), FFMPEG is used to extract the audio track from the original video. This extracted audio is passed to a Speech-to-Text (STT) Groq service to generate a subtitle file (SRT/VTT).

<img width="2746" height="1228" alt="image" src="https://github.com/user-attachments/assets/df6aae0e-7cb4-4061-b121-c2df131c2a9d" />

---

### 🔁 Sequence Diagram

```mermaid
sequenceDiagram
  autonumber

  participant UserVideo
  participant BhashiniAPI as Bhashini API
  participant FFMPEG
  participant STSAPI as Bhashini STS API
  participant GroqSTT as Groq STT API
  participant ElevenLabs as ElevenLabs Dubbing API
  participant SieveData
  participant Output as Final Output

  %% V1 - Non-Hindi Translations
  UserVideo->>BhashiniAPI: Detect source language
  UserVideo->>FFMPEG: Extract audio (mp3 or wav)
  FFMPEG->>STSAPI: Send audio for translation
  STSAPI->>GroqSTT: Translated audio → transcription
  GroqSTT->>Output: Generate SRT subtitle file
  STSAPI->>FFMPEG: Return translated audio
  FFMPEG->>Output: Mux translated audio with video
  Output->>Output: Mux SRT with video (final subtitles)

  Note over UserVideo,Output: V1 - Non-Hindi Translation Flow

  %% V2 - Hindi Direct Translation
  UserVideo->>ElevenLabs: Send video for dubbing (Option I)
  ElevenLabs->>GroqSTT: Transcription from dubbed video
  GroqSTT->>Output: Generate SRT subtitle file

  UserVideo->>SieveData: Send video for dubbing + lip sync (Option II)

  Note over ElevenLabs,SieveData: V2 - Hindi Direct Translation Options
```
## 🤝 Contributing

Follow Installation steps above to run locally.

This app uses `pre-commit` for code formatting and linting. Please [install pre-commit](https://pre-commit.com/#installation) and enable it for this repository:

```bash
cd apps/my_app
pre-commit install
```

Pre-commit is configured to use the following tools for checking and formatting your code:

- ruff
- eslint
- prettier
- pyupgrade

## 📜 License

The project is licensed under the MIT License. See the LICENSE file ( `license.txt` ) for details.
