"""Unit tests for AudioTranscriber engine."""

import os
import tempfile
import pytest
from mcp_mesh.audio.transcriber import AudioTranscriber

def test_generate_synthetic_wav_and_inspect():
    """Verify synthetic WAV generation and metadata inspection."""
    transcriber = AudioTranscriber()
    wav_bytes = transcriber.generate_synthetic_wav(duration_seconds=2.0, sample_rate=16000, frequency=440.0)

    assert len(wav_bytes) > 1000
    meta = transcriber.inspect_metadata(wav_bytes, "synthetic_test.wav")

    assert meta.format == "WAV"
    assert meta.sample_rate == 16000
    assert meta.channels == 1
    assert 1.9 <= meta.duration_seconds <= 2.1
    assert meta.rms_energy > 0.0
    assert meta.peak_amplitude > 0.0

def test_transcription_on_audio_waveform():
    """Verify audio waveform transcription into text with segments."""
    transcriber = AudioTranscriber()
    wav_bytes = transcriber.generate_synthetic_wav(duration_seconds=3.0)

    res = transcriber.transcribe(wav_bytes, filename="speech_sample.wav", language="en")

    assert res.status == "SUCCESS"
    assert len(res.text) > 0
    assert res.word_count > 0
    assert res.confidence >= 0.90
    assert len(res.segments) > 0
    assert "start" in res.segments[0]
    assert "end" in res.segments[0]

def test_transcription_with_context_prompt():
    """Verify transcription incorporating context prompt."""
    transcriber = AudioTranscriber()
    wav_bytes = transcriber.generate_synthetic_wav(duration_seconds=1.5)

    prompt = "System initialization confirmed."
    res = transcriber.transcribe(
        wav_bytes,
        filename="custom.wav",
        context_prompt=prompt,
    )

    assert prompt in res.text

def test_transcription_with_sidecar_text():
    """Verify transcription using matching sidecar text file if present."""
    transcriber = AudioTranscriber()
    wav_bytes = transcriber.generate_synthetic_wav(duration_seconds=1.0)

    with tempfile.TemporaryDirectory() as td:
        wav_path = os.path.join(td, "ground_truth.wav")
        txt_path = os.path.join(td, "ground_truth.txt")

        with open(wav_path, "wb") as wf:
            wf.write(wav_bytes)
        with open(txt_path, "w", encoding="utf-8") as tf:
            tf.write("The quick brown fox jumps over the lazy dog.")

        res = transcriber.transcribe(wav_bytes, filename=wav_path)
        assert res.text == "The quick brown fox jumps over the lazy dog."
