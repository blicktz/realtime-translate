# Product Requirement Document: Nebula Translate

## 1. Executive Summary
**Nebula Translate** is a high-fidelity, real-time voice translation interface designed for face-to-face interactions. Unlike standard translation apps, Nebula enforces a strict "Interpreter" workflow using a Push-to-Talk (PTT) mechanic to distinctively separate the user's turn from the partner's turn. This design minimizes confusion in bidirectional conversations and provides specific output modalities (Audio vs. Text) based on who is speaking.

## 2. Core Logic & Workflow

The application operates on a strict **State-Based Logic** determined by the User's interaction with the Push-to-Talk (PTT) button. The AI model does not auto-detect the speaker turn; the User manually dictates the flow.

### 2.1. User Turn (Active Transmission)
*   **Trigger:** The User **PRESSES AND HOLDS** the PTT button.
*   **Input Assumption:** The system assumes the **User** is speaking in the **Home Language**.
*   **Action:**
    1.  Capture audio from the microphone.
    2.  Transcribe the Home Language.
    3.  Translate the text into the **Target Language**.
*   **Output Behavior:**
    *   **Audio:** The system **PLAYS** the translated audio (Target Language) via speakers.
    *   **Display:** A message bubble appears on the **Right** side containing the Home Language text (verification).
    *   **Goal:** The Partner hears the translation.

### 2.2. Partner Turn (Passive Reception)
*   **Trigger:** The User **RELEASES** (is not touching) the PTT button.
*   **Input Assumption:** The system assumes the **Partner** is speaking in the **Target Language**.
*   **Action:**
    1.  Continuously listen to the microphone (Open Mic).
    2.  Detect speech activity.
    3.  Transcribe the Target Language.
    4.  Translate the text into the **Home Language**.
*   **Output Behavior:**
    *   **Audio:** The system stays **SILENT** (No audio playback).
    *   **Display:** A message bubble appears on the **Left** side containing the translated **Home Language** text.
    *   **Goal:** The User reads what the Partner said in the User's own language.

## 3. User Interface (UI) Requirements

### 3.1. Aesthetic Theme
*   **Visual Style:** "High-Tech/Cyberpunk." Dark backgrounds (#0a0a0f), neon accents (Cyan/Magenta), and monospaced typography.
*   **Atmosphere:** Professional, futuristic interpreter console.

### 3.2. Main Controls
*   **Connection Toggle:** A distinct "Power" button to initialize or terminate the session.
    *   *State:* Disconnected (Standby), Connecting (Pulse), Connected (Active).
*   **Push-to-Talk (PTT) Button:**
    *   **Size:** Prominent, easily accessible (occupying significant screen width).
    *   **Visual Feedback:**
        *   *Idle:* "HOLD TO SPEAK" (Muted colors).
        *   *Active (Held):* "SPEAKING..." (High contrast, accent color, internal animation).
*   **Settings:** Access to language configuration.

### 3.3. Feedback Indicators
*   **Audio Visualizer:** A real-time bar graph reacting to microphone input amplitude.
    *   *Color Logic:* Accented color when User speaks (PTT Held); Secondary color when Partner speaks (PTT Released).
*   **Processing State ("The Thinking Indicator"):**
    *   **Trigger:** When significant audio input is detected but the model has not yet returned a response.
    *   **Visual:** A dedicated "NEBULA IS THINKING..." pulse animation with a loader icon overlaying the visualizer area.
    *   **Purpose:** To inform the user that the system heard the speech and is currently processing the translation, preventing user frustration during latency gaps.

### 3.4. Chat/Transcript Feed
*   **Layout:** Vertical scroll, auto-scrolling to the newest message.
*   **User Messages (Right Aligned):**
    *   Visual: Accent color border/glow.
    *   Content: Home Language text.
    *   Label: "YOU (HOME LANGUAGE)"
*   **Partner Messages (Left Aligned):**
    *   Visual: Secondary color, solid/muted background.
    *   Content: **Home Language** text (Translated result).
    *   Label: "PARTNER (TRANSLATION)"

## 4. Configuration Requirements

### 4.1. Language Selection
*   **Home Language:** The language spoken by the device owner (User).
*   **Target Language:** The language spoken by the interlocutor (Partner).
*   **Bidirectional Capability:** The system must support translating A->B and B->A within the same session without reconfiguring, governed solely by the PTT state.

## 5. Technical Constraints & Behavior
*   **Silence Handling:** The system must filter out background noise and only trigger "Processing" states when actual speech amplitude thresholds are met.
*   **Race Conditions:** PTT state must strictly override auto-detection logic. If the user presses the button, the system forces the turn direction to "User" regardless of prior context.
*   **Latency:** The interface must provide immediate visual feedback (button press states) even if the audio processing has network latency.

