from bumusic.config import BALANCED_PROFILE, TranscriptionProfile


def test_balanced_profile_is_frozen() -> None:
    assert BALANCED_PROFILE.sample_rate == 22_050
    assert BALANCED_PROFILE.hop_length == 128
    assert BALANCED_PROFILE.voiced_threshold == 0.35
    assert BALANCED_PROFILE.min_note_seconds == 0.045
    assert BALANCED_PROFILE.max_gap_seconds == 0.055
    assert BALANCED_PROFILE.median_size == 3
    assert BALANCED_PROFILE.onset_delta == 0.10
    assert BALANCED_PROFILE.onset_min_separation_seconds == 0.10
    assert BALANCED_PROFILE.onset_rms_dip_ratio == 0.50
    assert BALANCED_PROFILE.trim_top_db == 35
    assert BALANCED_PROFILE.fmin_note == "C2"
    assert BALANCED_PROFILE.fmax_note == "C7"


def test_transcription_profile_keeps_legacy_positional_constructor() -> None:
    profile = TranscriptionProfile(22_050, 128, 0.35, 0.045, 0.055, 3, 35, "C2", "C7")

    assert profile.onset_delta == 0.10
    assert profile.onset_min_separation_seconds == 0.10
    assert profile.onset_rms_dip_ratio == 0.50
