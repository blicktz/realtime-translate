"""
Enums and constants for Nebula Translate backend.
"""

from enum import Enum


class SessionState(str, Enum):
    """Session state machine states."""
    DISCONNECTED = "disconnected"
    CONNECTED = "connected"
    USER_SPEAKING = "user_speaking"
    USER_PROCESSING = "user_processing"
    PARTNER_LISTENING = "partner_listening"
    PARTNER_PROCESSING = "partner_processing"
    ERROR = "error"


class PTTState(str, Enum):
    """Push-to-Talk button states."""
    PRESSED = "pressed"
    RELEASED = "released"


class SpeakerTurn(str, Enum):
    """Who is currently speaking."""
    USER = "user"
    PARTNER = "partner"


class MessageType(str, Enum):
    """WebSocket/DataChannel message types."""
    # Control Messages
    PTT_STATE = "ptt_state"
    CONNECTION_STATE = "connection_state"
    ERROR = "error"

    # Data Messages
    TRANSCRIPT = "transcript"
    TRANSLATION = "translation"
    AUDIO_LEVEL = "audio_level"

    # System Messages
    THINKING = "thinking"
    PROCESSING_STAGE = "processing_stage"


class ProcessingStage(str, Enum):
    """Translation pipeline processing stages."""
    IDLE = "idle"
    STT = "stt"
    TRANSLATION = "translation"
    TTS = "tts"
    COMPLETE = "complete"


class LanguageCode(str, Enum):
    """Supported language codes (ISO 639-1)."""
    # Major languages supported by OpenAI Whisper and TTS
    ENGLISH = "en"
    SPANISH = "es"
    FRENCH = "fr"
    GERMAN = "de"
    ITALIAN = "it"
    PORTUGUESE = "pt"
    RUSSIAN = "ru"
    JAPANESE = "ja"
    KOREAN = "ko"
    CHINESE = "zh"
    ARABIC = "ar"
    HINDI = "hi"
    DUTCH = "nl"
    POLISH = "pl"
    TURKISH = "tr"
    VIETNAMESE = "vi"
    INDONESIAN = "id"
    THAI = "th"
    SWEDISH = "sv"
    DANISH = "da"
    NORWEGIAN = "no"
    FINNISH = "fi"
    CZECH = "cs"
    GREEK = "el"
    HEBREW = "he"
    UKRAINIAN = "uk"


# Language display names for UI
LANGUAGE_NAMES = {
    LanguageCode.ENGLISH: "English",
    LanguageCode.SPANISH: "Español",
    LanguageCode.FRENCH: "Français",
    LanguageCode.GERMAN: "Deutsch",
    LanguageCode.ITALIAN: "Italiano",
    LanguageCode.PORTUGUESE: "Português",
    LanguageCode.RUSSIAN: "Русский",
    LanguageCode.JAPANESE: "日本語",
    LanguageCode.KOREAN: "한국어",
    LanguageCode.CHINESE: "中文",
    LanguageCode.ARABIC: "العربية",
    LanguageCode.HINDI: "हिन्दी",
    LanguageCode.DUTCH: "Nederlands",
    LanguageCode.POLISH: "Polski",
    LanguageCode.TURKISH: "Türkçe",
    LanguageCode.VIETNAMESE: "Tiếng Việt",
    LanguageCode.INDONESIAN: "Bahasa Indonesia",
    LanguageCode.THAI: "ไทย",
    LanguageCode.SWEDISH: "Svenska",
    LanguageCode.DANISH: "Dansk",
    LanguageCode.NORWEGIAN: "Norsk",
    LanguageCode.FINNISH: "Suomi",
    LanguageCode.CZECH: "Čeština",
    LanguageCode.GREEK: "Ελληνικά",
    LanguageCode.HEBREW: "עברית",
    LanguageCode.UKRAINIAN: "Українська",
}
