import vesselUtils from '../../assets/utils.js';
import { describe, expect, it } from 'vitest';

const { haversine, getAnchorDistanceColor, getWindDirection } = vesselUtils;

describe('vesselUtils', () => {
  it('computes haversine distance in kilometers', () => {
    const sanFrancisco = { lat: 37.7749, lon: -122.4194 };
    const losAngeles = { lat: 34.0522, lon: -118.2437 };
    const distance = haversine(
      sanFrancisco.lat,
      sanFrancisco.lon,
      losAngeles.lat,
      losAngeles.lon
    );
    expect(distance).toBeGreaterThan(540);
    expect(distance).toBeLessThan(570);
  });

  it('computes anchor distance color with explicit theme', () => {
    expect(getAnchorDistanceColor(true, 'light')).toBe('#e74c3c');
    expect(getAnchorDistanceColor(true, 'dark')).toBe('#ff6b6b');
    expect(getAnchorDistanceColor(false, 'light')).toBe('#27ae60');
    expect(getAnchorDistanceColor(false, 'dark')).toBe('#51cf66');
  });

  it('maps degrees to wind directions', () => {
    expect(getWindDirection(0)).toBe('N');
    expect(getWindDirection(90)).toBe('E');
    expect(getWindDirection(225)).toBe('SW');
    expect(getWindDirection(-45)).toBe('NW');
  });
});
