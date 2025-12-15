# Audio Processing Debugging Session - 2025-12-15

## Problem Statement
Audio is reaching the backend via WebRTC connection, but it's not being processed through the pipeline. No speech-to-text transcription is occurring.

---

## What We Confirmed is WORKING ✅

### 1. WebRTC Connection
- ✅ WebRTC connection establishes successfully
- ✅ ICE negotiation completes
- ✅ Audio track is detected: `Audio input track found: [track-id] (readyState=live)`
- ✅ State machine transitions to CONNECTED
- ✅ State shows: `should_enable_vad: True` (partner listening mode)

### 2. Audio Reception
- ✅ Transport receives audio frames from WebRTC
- ✅ Logs show: `[TRANSPORT] Received audio frame #1, #101, #201...` every 100 frames
- ✅ Frame sizes are consistent: 608-640 bytes per frame
- ✅ Audio frames reach `AudioLevelMonitor` processor
- ✅ Logs show: `[AUDIO_MONITOR] Frame #1 received, size=608 bytes`

### 3. Services Creation
- ✅ VAD analyzer created: `confidence=0.7, start=0.2s, stop=0.8s`
- ✅ STT service created for language: en
- ✅ TTS service created: language=es, voice=nova
- ✅ Translation processor created: en → es
- ✅ Pipeline setup completes without errors

---

## What is NOT WORKING ❌

### Audio Processing Stops at AudioLevelMonitor
- ❌ No logs from `VADLogger` (next processor in pipeline)
- ❌ No logs from `AudioRouterProcessor`
- ❌ No VAD speech detection events: `[VAD] 🎤 Speech STARTED`
- ❌ No STT transcription occurring
- ❌ No audio frames being forwarded beyond AudioLevelMonitor

### Pipeline Flow Breakdown
```
✅ WebRTC → ✅ Transport → ✅ AudioLevelMonitor → ❌ VADLogger → ❌ AudioRouter → ❌ STT
                                                     │
                                                 STOPS HERE
```

---

## Fixes Applied During Session

### Fix #1: VAD Analyzer Integration (CORRECT)
**Problem:** VAD analyzer (`SileroVADAnalyzer`) was being added to the pipeline directly
**Error:** `'SileroVADAnalyzer' object has no attribute 'link'`
**Solution:** Moved VAD analyzer to `TransportParams` where it belongs

**Before:**
```python
pipeline = Pipeline([
    transport.input(),
    audio_level_monitor,
    vad_processor,  # ❌ WRONG - not a FrameProcessor
    audio_router,
    ...
])
```

**After:**
```python
transport_params = TransportParams(
    audio_in_enabled=True,
    audio_out_enabled=True,
    audio_in_sample_rate=16000,
    audio_out_sample_rate=16000,
    audio_in_passthrough=True,
    vad_analyzer=vad_processor  # ✅ CORRECT
)
```

**Location:** `backend/main.py:366-376`
**Status:** ✅ FIXED - No more errors

---

### Fix #2: Frame Type Mismatch (CORRECT)
**Problem:** Transport generates `VADUserStartedSpeakingFrame` but code checked for `UserStartedSpeakingFrame`

**Solution:** Updated frame type checks to handle both variants

**Changes:**
1. Added imports in `backend/core/pipeline_manager.py:18-29`:
```python
from pipecat.frames.frames import (
    ...
    VADUserStartedSpeakingFrame,
    VADUserStoppedSpeakingFrame
)
```

2. Updated `VADLogger.process_frame()` (line 371-374):
```python
if isinstance(frame, (VADUserStartedSpeakingFrame, UserStartedSpeakingFrame)):
    self.manager.logger.info("[VAD] 🎤 Speech STARTED - VAD detected voice activity")
elif isinstance(frame, (VADUserStoppedSpeakingFrame, UserStoppedSpeakingFrame)):
    self.manager.logger.info("[VAD] 🔇 Speech STOPPED - VAD detected silence")
```

3. Updated `AudioRouterProcessor.process_frame()` (line 252-253, 263, 273):
```python
if not isinstance(frame, (AudioRawFrame, UserStartedSpeakingFrame, UserStoppedSpeakingFrame,
                           VADUserStartedSpeakingFrame, VADUserStoppedSpeakingFrame)):
```

**Status:** ✅ FIXED - Would work if frames reached these processors

---

### Fix #3: Sample Rate Configuration (GOOD PRACTICE)
**Problem:** Implicit sample rates could cause mismatches
**Solution:** Explicit sample rate configuration

**Location:** `backend/main.py:370-371`
```python
audio_in_sample_rate=16000,   # Match VAD and STT
audio_out_sample_rate=16000,
```

**Status:** ✅ APPLIED - Ensures consistency

---

### Fix #4: AudioLevelMonitor Frame Forwarding (CRITICAL - BUT STILL NOT WORKING)
**Problem:** `AudioLevelMonitor` was calling `super().process_frame()` which only handles system frames (StartFrame, CancelFrame, etc.) but doesn't forward AudioRawFrame

**Root Cause:**
- Base `FrameProcessor.process_frame()` only processes specific system frames
- It does NOT automatically forward other frame types
- AudioRawFrame was being received but not forwarded to next processor

**Solution:** Changed to call `push_frame()` to forward frames

**Before (BROKEN):**
```python
async def process_frame(self, frame: Frame, direction: FrameDirection):
    if isinstance(frame, AudioRawFrame):
        # ... monitor audio ...

    await super().process_frame(frame, direction)  # ❌ Only handles system frames!
```

**After (SHOULD WORK):**
```python
async def process_frame(self, frame: Frame, direction: FrameDirection):
    # FIRST: Let parent class handle system frames
    await super().process_frame(frame, direction)

    if isinstance(frame, AudioRawFrame):
        # ... monitor audio ...

    # SECOND: Forward ALL frames to next processor
    await self.push_frame(frame, direction)  # ✅ Forwards frames
```

**Location:** `backend/core/pipeline_manager.py:391-417`
**Status:** ⚠️ APPLIED BUT STILL NOT WORKING

---

## Current Pipeline Configuration

### Pipeline Structure
```python
pipeline = Pipeline([
    transport.input(),           # WebRTC audio input (VAD handled by transport)
    audio_level_monitor,         # Monitor audio levels
    vad_logger,                  # Log VAD events for debugging
    audio_router,                # Route based on PTT state
    stt_processor,               # Speech-to-text
    translation_processor,       # Translation
    text_router,                 # Route text based on state
    tts_processor,               # Text-to-speech (only for user turn)
    transport.output(),          # WebRTC audio output
])
```

**Location:** `backend/main.py:461-471`

### Processor Details

#### 1. `transport.input()` (Pipecat BaseInputTransport)
- **Role:** Receives audio from WebRTC, runs VAD analysis, generates VAD events
- **VAD Integration:** Via `TransportParams.vad_analyzer`
- **Expected Behavior:**
  - Analyzes audio with SileroVADAnalyzer
  - Generates `VADUserStartedSpeakingFrame` when speech detected
  - Generates `VADUserStoppedSpeakingFrame` when silence detected
  - Pushes `AudioRawFrame` downstream if `audio_in_passthrough=True`
- **Status:** ✅ Working - receives and logs audio frames

#### 2. `audio_level_monitor` (AudioLevelMonitor)
- **Role:** Monitor audio levels for visualization
- **Location:** `backend/core/pipeline_manager.py:381-418`
- **Expected Behavior:**
  - Receives frames from transport.input()
  - Calculates audio levels
  - Calls `super().process_frame()` for system frames
  - Calls `push_frame()` to forward ALL frames
- **Status:** ⚠️ Receives frames but next processor not getting them

#### 3. `vad_logger` (VADLogger)
- **Role:** Log VAD speech detection events for debugging
- **Location:** `backend/core/pipeline_manager.py:358-377`
- **Expected Behavior:**
  - Logs when `VADUserStartedSpeakingFrame` received
  - Logs when `VADUserStoppedSpeakingFrame` received
  - Forwards all frames
- **Status:** ❌ NOT RECEIVING FRAMES - No logs appearing

#### 4. `audio_router` (AudioRouterProcessor)
- **Role:** Route audio based on PTT state and VAD
- **Location:** `backend/core/pipeline_manager.py:239-311`
- **Expected Behavior:**
  - Forwards audio if `is_user_turn` (PTT pressed)
  - Forwards audio if `should_enable_vad` (partner turn)
  - Logs routing decisions every 50 frames
- **Status:** ❌ NOT RECEIVING FRAMES - No logs appearing

---

## Hypotheses for Why It's Still Not Working

### Hypothesis #1: Pipeline Linking Issue
**Theory:** The pipeline processors may not be properly linked together
**Evidence:**
- AudioLevelMonitor receives frames
- AudioLevelMonitor calls push_frame()
- But VADLogger (next processor) receives nothing

**What to Check:**
1. Verify pipeline initialization in pipecat
2. Check if processors are properly connected
3. Verify push_frame() is finding the next processor

**Test:**
```python
# Add to AudioLevelMonitor after line 417:
if self._frame_count % 100 == 1:
    self.manager.logger.info(f"[AUDIO_MONITOR] Downstream processors: {len(self._downstream_queue) if hasattr(self, '_downstream_queue') else 'unknown'}")
```

---

### Hypothesis #2: Exception Being Swallowed
**Theory:** `push_frame()` might be raising an exception that's being caught silently
**Evidence:** No error logs showing up

**What to Check:**
1. Add try/except around push_frame() with explicit logging
2. Check pipecat's push_frame() implementation for error handling

**Test:**
```python
# In AudioLevelMonitor.process_frame():
try:
    await self.push_frame(frame, direction)
    if self._frame_count % 100 == 1:
        self.manager.logger.info(f"[AUDIO_MONITOR] push_frame() succeeded for frame #{self._frame_count}")
except Exception as e:
    self.manager.logger.error(f"[AUDIO_MONITOR] push_frame() failed: {e}", exc_info=True)
```

---

### Hypothesis #3: Async Task Not Running
**Theory:** VADLogger or AudioRouter's processing task may not be running
**Evidence:** No logs from these processors at all

**What to Check:**
1. Verify all processors are started
2. Check if frame queues are being processed
3. Verify no deadlocks or waiting conditions

**Test:**
Add logging to VADLogger.__init__() and process_frame() to confirm it's being instantiated and called

---

### Hypothesis #4: VAD Not Generating Events
**Theory:** VAD analyzer might not be detecting speech, so no VAD events are generated
**Evidence:**
- No `[VAD] 🎤 Speech STARTED` logs
- Could mean VAD is working but not detecting speech (confidence too high?)

**What to Check:**
1. Lower VAD confidence threshold from 0.7 to 0.3
2. Add logging in transport's VAD handling code
3. Check if audio quality is sufficient for VAD

**Test:**
```python
# In main.py, before creating VAD:
vad_processor = VADServiceFactory.create_vad_processor(
    session_id=session.session_id,
    confidence_threshold=0.3,  # Lower threshold
    start_secs=0.1,             # Faster response
    stop_secs=0.5
)
```

---

### Hypothesis #5: Frame Direction Issue
**Theory:** Frames might be going UPSTREAM instead of DOWNSTREAM
**Evidence:** All checks use `direction == FrameDirection.DOWNSTREAM`

**What to Check:**
1. Log the direction in AudioLevelMonitor
2. Verify transport.input() is pushing frames DOWNSTREAM

**Test:**
```python
# In AudioLevelMonitor.process_frame(), line 396:
if self._frame_count % 100 == 1:
    self.manager.logger.info(f"[AUDIO_MONITOR] Frame #{self._frame_count}, direction={direction}")
```

---

## Next Steps for Debugging

### Priority 1: Trace Frame Flow in Pipecat
Add logging to pipecat's `FrameProcessor.push_frame()` method:

**File:** `backend/pipecat/src/pipecat/processors/frame_processor.py`

Find the `push_frame()` method and add logging:
```python
async def push_frame(self, frame: Frame, direction: FrameDirection = FrameDirection.DOWNSTREAM):
    logger.info(f"[PIPECAT] {self.__class__.__name__}.push_frame() called with {frame.__class__.__name__}, direction={direction}")
    # ... existing code ...
    logger.info(f"[PIPECAT] {self.__class__.__name__}.push_frame() completed")
```

This will show exactly where frames are going after AudioLevelMonitor.

---

### Priority 2: Verify Pipeline Initialization
Check that all processors are properly linked:

**File:** `backend/main.py` after pipeline creation (line 471)

```python
# Add diagnostic logging
logger.info(f"Pipeline created with {len(pipeline._processors)} processors:")
for i, proc in enumerate(pipeline._processors):
    logger.info(f"  [{i}] {proc.__class__.__name__}")
```

---

### Priority 3: Test Minimal Pipeline
Create a minimal test pipeline to isolate the issue:

```python
# Simplified test pipeline
simple_pipeline = Pipeline([
    transport.input(),
    audio_level_monitor,
    transport.output(),
])
```

If audio works with this minimal pipeline, gradually add back processors one at a time.

---

### Priority 4: Check VAD Audio Processing
Add logging to the transport's VAD processing (if accessible):

**Theory:** VAD might be receiving audio but not generating events

**Where to look:**
- `backend/pipecat/src/pipecat/transports/base_input.py:469-470` - VAD analysis
- `backend/pipecat/src/pipecat/transports/base_input.py:414-418` - VAD event generation

---

## Log Analysis

### Last Known Good State
```
2025-12-15 20:17:06.158 | [TRANSPORT] Received audio frame #1: size=608 bytes
2025-12-15 20:17:06.160 | [AUDIO_MONITOR] Frame #1 received, size=608 bytes
```

### What's Missing (Should Appear But Doesn't)
```
[AUDIO_MONITOR] About to call push_frame()              # ❌ Not logged
[AUDIO_MONITOR] push_frame() completed                  # ❌ Not logged
[PIPECAT] AudioLevelMonitor.push_frame() called         # ❌ Not logged
[VAD] 🎤 Speech STARTED - VAD detected voice activity   # ❌ Not logged
[AUDIO_ROUTER] Frame #1 - State: connected              # ❌ Not logged
[STT] Processing audio                                  # ❌ Not logged
```

---

## Files Modified During Session

1. **`backend/main.py`**
   - Lines 366-381: VAD analyzer creation and TransportParams configuration
   - Lines 461-471: Pipeline structure

2. **`backend/core/pipeline_manager.py`**
   - Lines 18-29: Added VADUserStartedSpeakingFrame imports
   - Lines 252-287: Updated AudioRouterProcessor frame type checks
   - Lines 358-377: VADLogger with VAD* frame support
   - Lines 391-417: AudioLevelMonitor with push_frame() fix

---

## Summary

### What We Know
1. ✅ Audio IS reaching the backend
2. ✅ WebRTC connection IS working
3. ✅ VAD analyzer IS created correctly
4. ✅ All services ARE initialized
5. ✅ AudioLevelMonitor IS receiving frames
6. ❌ Frames are NOT being forwarded beyond AudioLevelMonitor
7. ❌ VAD events are NOT being generated or logged
8. ❌ No audio processing is occurring

### Most Likely Issue
**Pipeline processors are not properly linked**, or there's an issue with how `push_frame()` finds and calls the next processor in the chain.

### Recommended Next Action
**Add comprehensive logging to pipecat's `push_frame()` method** to trace exactly where frames go and why they stop at AudioLevelMonitor.

---

## Technical References

### Pipecat Frame Flow
```
WebRTC Audio → Transport._receive_audio()
           → Transport._audio_task_handler() [if VAD enabled]
           → VAD Analysis → VADUserStartedSpeakingFrame (if speech detected)
           → push_frame(InputAudioRawFrame) [if audio_in_passthrough=True]
           → BaseInputTransport.push_frame()
           → Pipeline downstream processors
```

### Frame Types
- `AudioRawFrame` - Audio data
- `InputAudioRawFrame` - Audio input from transport
- `VADUserStartedSpeakingFrame` - VAD detected speech start
- `VADUserStoppedSpeakingFrame` - VAD detected speech stop
- `UserStartedSpeakingFrame` - Generic speech start (PTT or VAD)
- `UserStoppedSpeakingFrame` - Generic speech stop
- `StartFrame` - Pipeline initialization
- `EndFrame` - Pipeline shutdown

### State Machine States
- `CONNECTED` - Session connected, waiting for speech
- `USER_SPEAKING` - User has PTT pressed
- `USER_PROCESSING` - Processing user's speech
- `PARTNER_LISTENING` - Waiting for partner to speak (VAD active)
- `PARTNER_PROCESSING` - Processing partner's speech

---

*Last Updated: 2025-12-15 20:20 UTC*
*Session Duration: ~2 hours*
*Status: ISSUE NOT RESOLVED - Frames stop at AudioLevelMonitor*
