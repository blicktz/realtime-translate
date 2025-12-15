# Pipeline Status - Audio Processing Issues

**Date:** December 15, 2025
**Session:** Audio debugging and fixes

## Summary

The real-time translation pipeline is now mostly functional with audio flowing through all processors. Translation is working, but translated text is not appearing on the frontend.

---

## ✅ What's Working

### 1. Audio Pipeline Flow
- ✅ WebRTC connection established successfully
- ✅ Audio frames received from transport
- ✅ Audio flows through all processors:
  - Transport → AudioLevelMonitor → VADLogger → AudioRouterProcessor → STT → Translation → TextRouter → TTS → Output

### 2. VAD (Voice Activity Detection)
- ✅ VAD successfully detects speech start/stop
- ✅ VADUserStartedSpeakingFrame and VADUserStoppedSpeakingFrame generated correctly
- ✅ Partner processing state triggered when VAD detects speech

### 3. Speech-to-Text (STT)
- ✅ Audio reaches OpenAI STT service
- ✅ Transcription completes successfully
- ✅ TranscriptionFrame/TextFrame created with transcribed text

### 4. Translation
- ✅ TranslationProcessor receives TextFrame/TranscriptionFrame
- ✅ Translation API called successfully (OpenRouter)
- ✅ Translation completes (e.g., "This is Owen speaking" → "Habla Owen")
- ✅ Translated TextFrame created and pushed downstream

### 5. Frame Forwarding (Fixed!)
- ✅ **AudioLevelMonitor**: Now properly calls `push_frame()` to forward all frames
- ✅ **VADLogger**: Fixed to call `push_frame()` (was missing - critical bug!)
- ✅ **AudioRouterProcessor**: Now forwards SystemFrames with `push_frame()`
- ✅ **TextRouterProcessor**: Now forwards SystemFrames with `push_frame()`
- ✅ **TranslationProcessor**: Now properly handles and forwards all frame types

### 6. State Management
- ✅ Partner processing state correctly triggered when VAD detects speech
- ✅ `start_partner_processing()` called when UserStartedSpeakingFrame received
- ✅ `finish_partner_processing()` called when UserStoppedSpeakingFrame received
- ✅ State transitions working: connected → partner_processing → partner_listening

---

## ❌ Current Problems

### Problem #1: Text Not Displaying on Frontend
**Status:** Translation works, but text doesn't appear on screen

**What's happening:**
- Translation completes successfully: `[TRANSLATION] ✅ Translation complete: 'Habla Owen.'`
- TextFrame is created and pushed downstream
- TextRouterProcessor should receive the frame and emit it via WebSocket
- **BUT:** No text appears on the frontend

**Root cause:** `current_speaker` is set by state machine, but TextRouterProcessor may not be emitting text correctly, OR WebSocket emission is failing

**Location:**
- `backend/core/pipeline_manager.py` - TextRouterProcessor (lines 339-365)
- WebSocket emission in PipelineManager

**Next steps to debug:**
1. Add logging to TextRouterProcessor to see if it receives the TextFrame
2. Check if `_emit_text_output()` is being called
3. Verify WebSocket is connected and message is sent
4. Check frontend to see if WebSocket message is received

---

### Problem #2: Audio Level / Waveform Not Showing
**Status:** Related to Problem #1

**What's happening:**
- AudioLevelMonitor calculates audio levels correctly
- BUT only emits them if `current_speaker` is not None
- Since `current_speaker` is set by partner processing, this should work now
- Waveform not showing movement on frontend

**Root cause:** Same as Problem #1 - either `current_speaker` state issue or WebSocket emission issue

**Location:**
- `backend/core/pipeline_manager.py` - AudioLevelMonitor (lines 391-449)
- Audio level emission via `_emit_audio_level()`

**Next steps:**
1. Add logging to confirm audio levels are being calculated
2. Verify `current_speaker` is set when audio is detected
3. Check if `_emit_audio_level()` is being called
4. Verify WebSocket message is sent and received by frontend

---

### Problem #3: AudioRouterProcessor Dropping Frames in "connected" State
**Status:** Not critical but inefficient

**What's happening:**
```
[AUDIO_ROUTER] ❌ DROPPING frame #101 - State: connected, PTT: False
```

**Root cause:** AudioRouterProcessor routing logic only forwards frames when:
- `is_user_turn` (PTT pressed), OR
- `is_partner_turn` (partner_listening or partner_processing)

When state is `connected` (before any speech), frames are dropped. This is fine since VAD hasn't detected speech yet, but creates noisy logs.

**Location:**
- `backend/core/pipeline_manager.py` - AudioRouterProcessor (lines 300-335)

**Fix needed:** Add `should_enable_vad` to routing condition:
```python
elif self.manager.state_machine.is_partner_turn or self.manager.state_machine.should_enable_vad:
    # Forward when VAD enabled OR partner turn
    await self.push_frame(frame, direction)
```

**Priority:** Low (doesn't affect functionality, just creates log noise)

---

## 🔧 Fixes Applied in This Session

### 1. VADLogger Missing push_frame() - CRITICAL FIX
**Problem:** VADLogger was receiving frames but never forwarding them to the next processor
**Fix:** Added `await self.push_frame(frame, direction)` at the end of `process_frame()`
**File:** `backend/core/pipeline_manager.py` (VADLogger class)
**Impact:** This was the PRIMARY bug blocking the entire pipeline!

### 2. AudioRouterProcessor Not Forwarding SystemFrames
**Problem:** SystemFrames (StartFrame, etc.) were processed but not forwarded
**Fix:** Added `await self.push_frame(frame, direction)` after `super().process_frame()`
**File:** `backend/core/pipeline_manager.py` (AudioRouterProcessor)

### 3. TextRouterProcessor Not Forwarding SystemFrames
**Problem:** Same as #2
**Fix:** Same as #2
**File:** `backend/core/pipeline_manager.py` (TextRouterProcessor)

### 4. TranslationProcessor Not Handling TranscriptionFrame
**Problem:** Only checked for TextFrame, but STT outputs TranscriptionFrame
**Fix:** Import TranscriptionFrame and check for both types
**File:** `backend/services/translation_service.py`

### 5. Partner Processing State Machine Integration
**Problem:** `start_partner_processing()` was never called when VAD detected speech
**Fix:** Added state machine calls in AudioRouterProcessor when UserStartedSpeakingFrame received
**File:** `backend/core/pipeline_manager.py` (AudioRouterProcessor)

### 6. StartFrame Propagation Wait Time
**Problem:** 0.5s wasn't long enough for StartFrame to reach all 11 processors
**Fix:** Increased wait time from 0.5s to 1.5s
**File:** `backend/main.py` (line 496)

### 7. Excessive Logging Cleanup
**Problem:** Translation logging every InputAudioRawFrame (too noisy)
**Fix:** Removed verbose frame logging, kept only translation events
**File:** `backend/services/translation_service.py`

---

## 🏗️ Pipeline Architecture

### Complete Frame Flow
```
1. WebRTC Transport (Input)
   ↓ InputAudioRawFrame
2. AudioLevelMonitor
   ↓ (calculates levels, forwards all frames)
3. VADLogger
   ↓ (logs VAD events, forwards all frames)
4. AudioRouterProcessor
   ↓ (routes based on state: user turn vs partner turn)
5. OpenAI STT Service
   ↓ TranscriptionFrame/TextFrame
6. TranslationProcessor
   ↓ TextFrame (translated)
7. TextRouterProcessor
   ↓ (should emit to WebSocket + optionally forward to TTS)
8. OpenAI TTS Service
   ↓ AudioFrame
9. WebRTC Transport (Output)
```

### State Machine Flow (Partner Turn)
```
1. State: CONNECTED
   ↓ (user not speaking, VAD listening)
2. VAD detects speech → UserStartedSpeakingFrame
   ↓
3. AudioRouterProcessor calls start_partner_processing()
   ↓
4. State: PARTNER_PROCESSING
   - current_speaker = PARTNER
   - Audio forwarded to STT
   - Audio levels emitted
   ↓
5. VAD detects silence → UserStoppedSpeakingFrame
   ↓
6. AudioRouterProcessor calls finish_partner_processing()
   ↓
7. State: PARTNER_LISTENING
   - current_speaker = None
```

---

## 📋 Next Steps

### Immediate Priority
1. **Debug TextRouterProcessor**
   - Add logging to see if TextFrame is received
   - Verify `_emit_text_output()` is called
   - Check if WebSocket message is sent

2. **Debug Frontend WebSocket**
   - Verify WebSocket connection is active
   - Check if messages are being received
   - Confirm UI is updating with received text

3. **Test End-to-End**
   - Speak without PTT
   - Confirm text appears on screen
   - Confirm waveform shows activity

### Lower Priority
4. **Fix AudioRouterProcessor Frame Dropping**
   - Add `should_enable_vad` to routing condition
   - Reduce log noise when in "connected" state

5. **Cleanup Diagnostic Logging**
   - Remove or reduce frequency of frame counting logs
   - Keep only essential logs for production

---

## 🧪 Testing Checklist

- [ ] VAD detects speech when speaking without PTT
- [ ] State transitions to partner_processing
- [ ] Transcription appears in backend logs
- [ ] Translation appears in backend logs
- [ ] **Text appears on frontend (FAILING)**
- [ ] **Waveform shows activity (FAILING)**
- [ ] Audio plays back when user presses PTT

---

## 📝 Code Locations

### Key Files Modified
- `backend/core/pipeline_manager.py` - Custom processors (AudioLevelMonitor, VADLogger, AudioRouterProcessor, TextRouterProcessor)
- `backend/services/translation_service.py` - TranslationProcessor
- `backend/pipecat/src/pipecat/processors/frame_processor.py` - Added logging to _check_started()
- `backend/main.py` - Increased StartFrame propagation wait time

### Key Files to Debug Next
- `backend/core/pipeline_manager.py` - TextRouterProcessor and _emit_text_output()
- Frontend WebSocket handler - Check message reception
- Frontend UI components - Check text display logic
