# 🎙️ Video Localization & Translation Review Guide
### *A Practical Playbook for the Marketing & Content Team*

---

## 📌 Introduction

Welcome to **Localizer**! While our AI automatically extracts audio, transcribes speech, and generates localized translations, the **Review Step (Step 4)** is where raw machine output transforms into studio-grade, broadcast-ready voiceovers.

This guide walks you through every tool available on the Review screen, explaining how to shape pacing, human emotion, and natural conversational cadence.

---

## 🧭 The Review Workspace: 4 Key Columns

```
┌──────┬──────────────────────┬──────────────────────────────┬──────────────────────────────────────────────────┐
│ TIME │    ORIGINAL TEXT     │   INTERACTIVE WORD CHUNKS    │         TRANSLATION & VOICE CONTROLS             │
├──────┼──────────────────────┼──────────────────────────────┼──────────────────────────────────────────────────┤
│ 0:01 │ China just launched  │ [China] [just] [launched]... │ VOICE: Roger ▾   [⚙️ Settings]                   │
│      │ competitor to Sora.  │ (Click edge/middle pills)    │ [ Translated Textarea                          ] │
│      │                      │                              │ 42 chars   [✨ AI Retranslate]    [🔗 Merge Down]│
└──────┴──────────────────────┴──────────────────────────────┴──────────────────────────────────────────────────┘
```

1. **Time (`0:01`)**: The precise timestamp in the video where this audio chunk begins.
2. **Original Text**: The reference transcription from the source language.
3. **Interactive Word Chunks**: Clickable word pills that allow you to modify segment boundaries on the fly.
4. **Translation & Voice Controls**: Where you edit the translated script, audition voices, tune emotion, and merge sentences.

---

## 🛠️ Core Features: How & When to Use Them

### 1. 🔗 Merge Down
* **Where to find it**: At the bottom of each segment card.
* **What it does**: Combines the current segment with the segment directly below it into a single, unified chunk.
* **When to use it**: Whenever a single speaker continues talking across multiple short sentence fragments.

> [!IMPORTANT]
> **Golden Rule of Natural Audio:**
> **If there are multiple chunks with the same voice continuously, ALWAYS merge them.**
> 
> Text-to-speech models (ElevenLabs `eleven_v3`) calculate pitch, emotion, breathing, and pacing based on full sentence context. If a thought is sliced into 3 separate chunks, the AI restarts its tone on each chunk, sounding choppy and robotic. Merging them into a single coherent paragraph produces seamless, broadcast-quality delivery.

---

### 2. 🔀 Interactive Word Splitting & Shifting
Need to adjust where a sentence starts or ends without starting over? Use the interactive word pills:

* **Click the FIRST word in a chunk (amber border)**:
  * Shifts that word **UP** into the previous chunk.
* **Click the LAST word in a chunk (amber border)**:
  * Shifts that word **DOWN** into the next chunk.
* **Click any MIDDLE word**:
  * **Splits** the chunk into two separate segments starting at that word.
  * *Use case*: When a long sentence transitions to a new slide or a second speaker interrupts.

---

### 3. ✨ AI Retranslate
* **Where to find it**: Directly beneath the translation text box.
* **What it does**: Automatically asks the translation engine to retranslate just that specific chunk from scratch.
* **When to use it**: Whenever you have shifted words, split a chunk, or merged two chunks. Since the sentence boundary changed, one click of **✨ AI Retranslate** instantly produces a natural, grammatically correct translation.

---

### 4. ⚙️ Voice Settings & Emotion Tuner
Click **⚙️ Settings** on any chunk to reveal the delivery controls:

| Control | Recommended Range | What It Does & When to Adjust |
| :--- | :--- | :--- |
| **Speed** | `0.90x – 1.15x` | **0.90x – 0.95x**: Slow down dense educational explanations.<br>**1.05x – 1.15x**: Speed up long translations to fit fast visual cuts before the next slide. |
| **Stability (Emotion)** | `35% – 75%` | **35% – 45% (High Emotion)**: Dynamic, lively delivery. Ideal for enthusiastic dialogue, student questions (*"Haan ma'am!"*), or promotional hype.<br>**50% – 60% (Natural)**: Balanced everyday conversational tone.<br>**70% – 85% (Calm)**: Serious, steady narration. |
| **Style Boost** | `10% – 30%` | Accentuates voice actor character and dramatic inflection. **Keep under 40%** to prevent audio distortion. |

---

### 5. 👥 Batch Settings: "Same Voice" vs. "All Chunks"

When you dial in the perfect speed or emotion on one chunk, you don't have to repeat the sliders for 50 other chunks:

* **👥 Apply to same voice (`N` chunks)**:
  * Copies that chunk’s **Speed, Stability, and Style** **only** to chunks assigned to that same voice actor.
  * *Example*: Set teacher voice to `55% Stability` and apply to all teacher chunks, without affecting the student voice!
* **🌐 Apply to all chunks (keeps voices)**:
  * Copies **Speed, Stability, and Style** across the entire script.
  * **Does NOT change assigned voices**: Every character retains their chosen actor!

---

## 💡 Best Practices for High-Impact Voiceovers

### 1. Merge Short Reaction Phrases
Isolated words like *"Yes!"*, *"Exactly"*, *"Right"*, or *"Haan bilkul"* will sound flat or robotic if voiced in their own standalone chunk.
* **Action**: Always **Merge Down** short reactions with the following sentence so the AI understands the emotional momentum.

### 2. Punctuation Controls the AI's Breathing
ElevenLabs pays heavy attention to punctuation:
* **Commas (`,`)**: Insert a natural, slight pause and breath.
* **Periods (`.`)**: Complete a thought with downward pitch cadence.
* **Question Marks (`?`)**: Natural upward pitch inflection.
* **Exclamation Marks (`!`)**: Inject energy and emphasis.
* *Tip*: If the AI is rushing through two thoughts, add a comma or semicolon between them in the translation textarea.

### 3. Maintain Speaker Separation
* Never merge two segments if the speaker changes on camera.
* Assign distinct voices for Teacher vs. Student, Narrator vs. Host, etc.

### 4. Check the Script Character Counter
* Look at the character counter beneath the textarea. If the target language has 30% more characters than the original, increase the **Speed** slider slightly (e.g. `1.05x` or `1.10x`) to prevent audio overlapping video slide transitions.

---

## 🚀 5-Step Review Checklist

Before clicking **"Approve & Generate Audio"**:

1. [ ] **Scan & Merge Monologues**: Continuous sentences from the same speaker? Click **🔗 Merge Down**.
2. [ ] **Assign Actors**: Pick the appropriate voice for each speaker in the `VOICE ·` dropdown.
3. [ ] **Retranslate Changed Chunks**: Click **✨ AI Retranslate** on any chunks you split or merged.
4. [ ] **Dial Emotion**: Set **Stability** (`40%` for expressive, `60%` for neutral) and **Style Boost** (`20%`). Use **👥 Apply to same voice** to propagate.
5. [ ] **Preview**: Click **▶ Preview Voice** on 2–3 key chunks to test the sound before full approval.
