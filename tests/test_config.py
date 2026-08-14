from bumusic.config import BALANCED_PROFILE


def test_balanced_profile_is_frozen() -> None:
    assert BALANCED_PROFILE.sample_rate == 22_050
    assert BALANCED_PROFILE.hop_length == 128
    assert BALANCED_PROFILE.voiced_threshold == 0.35
    assert BALANCED_PROFILE.min_note_seconds == 0.045
    assert BALANCED_PROFILE.max_gap_seconds == 0.055
    assert BALANCED_PROFILE.median_size == 3
    assert BALANCED_PROFILE.trim_top_db == 35
    assert BALANCED_PROFILE.fmin_note == "C2"
    assert BALANCED_PROFILE.fmax_note == "C7"
