# Anju AI — Session Checkpoint
**Date:** July 28, 2026

## ✅ Completed This Session

### Voice & UI Improvements
- Upgraded `voice/tts.py` to use `tts-1-hd` for clearer OpenAI TTS
- Improved `sanitizeTextForVoice()` with better pronunciation rules
- Added typing indicator, message timestamps, scroll-to-bottom button in UI
- Fixed Chrome speech synthesis bug (stalling after cancel())
- Better voice selection: Microsoft Natural > Google > English voices
- Added voice status bar in sidebar
- Fixed `currentScanMsgEl` reference leak

### Bug Fixes
- Removed duplicate cache check in `brain/brain.py` `_call_gemini()`
- Fixed null voice guard in `speakNextChunk()`

### Phone Control (ADB)
- Created `tools/phone_control.py` — full ADB wrapper module
- Integrated into `brain/brain.py` sentry (local commands) & Gemini prompt
- Added "Phone Link" UI panel in sidebar with Connect/Disconnect buttons
- Downloaded Android Platform Tools to `adb_tools/platform-tools/`
- Updated ADB_PATH to auto-detect local installation

### 6-Feature Upgrade
1. **Multi-step task planning** → `brain/workflow_engine.py`
2. **Autonomous workflows** → `run_autonomous()` in workflow_engine
3. **Multi-model support** → `MODEL_REGISTRY` in `utils/api_handler.py`
4. **Long-term memory** → Enhanced `brain/memory_manager.py` (consolidation, importance scoring)
5. **Plugin ecosystem** → `tools/plugin_manager.py` (11 plugins, 22 actions)
6. **Local + cloud intelligence** → `brain/local_intelligence.py` (smart routing)

## ⏳ Pending — Next Session

### Phone Connection Setup
1. On phone: **Settings → About Phone → Tap Build Number 7x** (enable Developer Options)
2. **Settings → Developer Options → Enable USB Debugging**
3. Connect phone via USB cable → Tap "Allow" on phone
4. Then run Anju AI → Say "Connect my phone" to switch to wireless mode

### Future Ideas
- Conversation export feature (PDF/text)
- Settings panel in UI
- More plugin development
