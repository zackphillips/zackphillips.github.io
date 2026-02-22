#!/usr/bin/env python3
"""Swell analysis module for calculating dominant swell characteristics from IMU data."""

import logging
import math
from collections import deque

import numpy as np
from scipy import signal

logger = logging.getLogger(__name__)

# Swell analysis parameters
SWELL_MIN_FREQ = 0.05  # Hz (20 second period)
SWELL_MAX_FREQ = 0.5  # Hz (2 second period)
MIN_SAMPLES = 128  # Minimum samples for analysis (about 2 minutes at 1 Hz)
MAX_SAMPLES = 512  # Maximum samples to keep in buffer
SAMPLE_RATE = 1.0  # Hz (assumes 1 sample per second)


class SwellAnalyzer:
    """Analyzes vessel motion to determine dominant swell characteristics."""

    def __init__(self, sample_rate: float = SAMPLE_RATE):
        """
        Initialize swell analyzer.

        Args:
            sample_rate: Sampling rate in Hz (default: 1.0 Hz)
        """
        self.sample_rate = sample_rate
        self.pitch_buffer = deque(maxlen=MAX_SAMPLES)
        self.roll_buffer = deque(maxlen=MAX_SAMPLES)
        self.timestamps = deque(maxlen=MAX_SAMPLES)

        # Design bandpass filter for swell frequencies
        nyquist = sample_rate / 2.0
        low = SWELL_MIN_FREQ / nyquist
        high = SWELL_MAX_FREQ / nyquist

        # Ensure frequencies are within valid range [0, 1]
        low = max(0.01, min(0.99, low))
        high = max(0.01, min(0.99, high))

        if low >= high:
            # Fallback if frequencies are too close
            low = 0.01
            high = 0.5

        try:
            self.b, self.a = signal.butter(4, [low, high], btype="band")
        except ValueError as e:
            logger.warning(f"Filter design failed: {e}, using default filter")
            self.b, self.a = signal.butter(4, [0.01, 0.5], btype="band")

        logger.info(
            f"SwellAnalyzer initialized: sample_rate={sample_rate}Hz, "
            f"filter=[{SWELL_MIN_FREQ:.3f}, {SWELL_MAX_FREQ:.3f}]Hz"
        )

    def add_sample(self, pitch: float, roll: float, timestamp: float = None):
        """
        Add a new pitch/roll sample to the buffer.

        Args:
            pitch: Pitch angle in radians
            roll: Roll angle in radians
            timestamp: Optional timestamp (defaults to current time)
        """
        import time

        if timestamp is None:
            timestamp = time.time()

        self.pitch_buffer.append(pitch)
        self.roll_buffer.append(roll)
        self.timestamps.append(timestamp)

    def analyze(self) -> dict[str, float | None]:
        """
        Analyze collected data to determine dominant swell characteristics.

        Returns:
            Dictionary with 'period' (s), 'direction' (rad), and 'height' (m)
            Returns None for values that cannot be determined
        """
        if len(self.pitch_buffer) < MIN_SAMPLES:
            return {
                "period": None,
                "direction": None,
                "height": None,
            }

        try:
            # Convert to numpy arrays
            pitch_array = np.array(self.pitch_buffer)
            roll_array = np.array(self.roll_buffer)

            # Remove DC component (mean)
            pitch_centered = pitch_array - np.mean(pitch_array)
            roll_centered = roll_array - np.mean(roll_array)

            # Apply bandpass filter
            try:
                pitch_filtered = signal.filtfilt(self.b, self.a, pitch_centered)
                roll_filtered = signal.filtfilt(self.b, self.a, roll_centered)
            except Exception as e:
                logger.warning(f"Filtering failed: {e}, using unfiltered data")
                pitch_filtered = pitch_centered
                roll_filtered = roll_centered

            # Calculate combined motion magnitude
            motion_magnitude = np.sqrt(pitch_filtered**2 + roll_filtered**2)

            # FFT analysis
            n = len(pitch_filtered)
            fft_pitch = np.fft.rfft(pitch_filtered)
            fft_roll = np.fft.rfft(roll_filtered)
            fft_magnitude = np.fft.rfft(motion_magnitude)

            # Frequency axis
            freqs = np.fft.rfftfreq(n, 1.0 / self.sample_rate)

            # Find dominant frequency (within swell range)
            valid_mask = (freqs >= SWELL_MIN_FREQ) & (freqs <= SWELL_MAX_FREQ)
            if not np.any(valid_mask):
                return {
                    "period": None,
                    "direction": None,
                    "height": None,
                }

            # Find peak in magnitude spectrum
            magnitude_spectrum = np.abs(fft_magnitude)
            valid_magnitude = magnitude_spectrum[valid_mask]
            valid_freqs = freqs[valid_mask]

            if len(valid_magnitude) == 0:
                return {
                    "period": None,
                    "direction": None,
                    "height": None,
                }

            peak_idx = np.argmax(valid_magnitude)
            dominant_freq = valid_freqs[peak_idx]
            period = 1.0 / dominant_freq if dominant_freq > 0 else None

            # Calculate direction from phase relationship
            # Direction is determined by the phase difference between pitch and roll
            # at the dominant frequency
            phase_pitch = np.angle(fft_pitch[valid_mask][peak_idx])
            phase_roll = np.angle(fft_roll[valid_mask][peak_idx])
            amp_pitch = np.abs(fft_pitch[valid_mask][peak_idx])
            amp_roll = np.abs(fft_roll[valid_mask][peak_idx])

            # Calculate direction using the phase relationship
            # The phase difference tells us how pitch and roll are related
            # The amplitudes tell us the relative strength
            phase_diff = phase_pitch - phase_roll

            # Use the complex representation to get direction
            # Direction is atan2 of the cross-spectral component
            # This gives the direction from which the swell is coming
            if amp_pitch > 0 and amp_roll > 0:
                # Calculate direction from amplitudes and phase
                # This represents the direction of maximum motion
                direction = math.atan2(
                    amp_roll * math.sin(phase_diff),
                    amp_pitch * math.cos(phase_diff),
                )
            else:
                # Fallback: use phase difference directly
                direction = phase_diff

            # Normalize to [0, 2π)
            direction = direction % (2 * math.pi)
            if direction < 0:
                direction += 2 * math.pi

            # Estimate height from motion amplitude
            # This is a rough estimate - actual height would require
            # knowledge of vessel characteristics
            # Using RMS of filtered motion as a proxy
            rms_motion = np.sqrt(np.mean(motion_magnitude**2))

            # Rough conversion: assume small angle approximation
            # Height estimate is proportional to motion amplitude
            # This is a simplified model - actual conversion would be more complex
            height = rms_motion * 2.0  # Rough scaling factor

            return {
                "period": period,
                "direction": direction,
                "height": height,
            }

        except Exception as e:
            logger.error(f"Error in swell analysis: {e}", exc_info=True)
            return {
                "period": None,
                "direction": None,
                "height": None,
            }

    def reset(self):
        """Reset the data buffers."""
        self.pitch_buffer.clear()
        self.roll_buffer.clear()
        self.timestamps.clear()
        logger.info("SwellAnalyzer buffers reset")

