"""
Service integrations for Nebula Translate backend.
"""

from .stt_service import (
    STTServiceFactory,
    AdaptiveSTTService,
    get_stt_config,
    validate_stt_config
)

from .tts_service import (
    TTSServiceFactory,
    AdaptiveTTSService,
    get_tts_config,
    validate_tts_config,
    list_available_voices,
    AVAILABLE_VOICES
)

from .translation_service import (
    TranslationProcessor,
    TranslationServiceFactory,
    get_translation_config,
    validate_translation_config,
    list_supported_models,
    SUPPORTED_MODELS
)

from .vad_service import (
    VADServiceFactory,
    DynamicVADService,
    get_vad_config,
    validate_vad_config,
    get_vad_preset,
    list_vad_presets,
    VAD_PRESETS
)

__all__ = [
    # STT
    "STTServiceFactory",
    "AdaptiveSTTService",
    "get_stt_config",
    "validate_stt_config",

    # TTS
    "TTSServiceFactory",
    "AdaptiveTTSService",
    "get_tts_config",
    "validate_tts_config",
    "list_available_voices",
    "AVAILABLE_VOICES",

    # Translation
    "TranslationProcessor",
    "TranslationServiceFactory",
    "get_translation_config",
    "validate_translation_config",
    "list_supported_models",
    "SUPPORTED_MODELS",

    # VAD
    "VADServiceFactory",
    "DynamicVADService",
    "get_vad_config",
    "validate_vad_config",
    "get_vad_preset",
    "list_vad_presets",
    "VAD_PRESETS",
]
