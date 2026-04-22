import { readFileSync } from 'fs';
import vm from 'vm';
import { resolve, dirname } from 'path';
import { fileURLToPath } from 'url';
import { describe, expect, it } from 'vitest';

const ROOT = resolve(dirname(fileURLToPath(import.meta.url)), '../..');
const constantsSrc = readFileSync(`${ROOT}/assets/constants.js`, 'utf8');
const appSrc = readFileSync(`${ROOT}/assets/app.js`, 'utf8');

// vm.runInNewContext mirrors browser script scoping:
//   var x = 1  → sandbox.x === 1   (same as window.x in a browser)
//   const x = 1 → sandbox.x === undefined
// This lets us verify the exact property that broke the site.
function evalInSandbox(src) {
  const sandbox = {};
  vm.runInNewContext(src, sandbox);
  return sandbox;
}

describe('constants.js', () => {
  it('uses var so VESSEL_CONSTANTS is accessible as a window property', () => {
    const sandbox = evalInSandbox(constantsSrc);
    expect(sandbox.VESSEL_CONSTANTS).toBeDefined();
  });

  it('exports a frozen object', () => {
    const { VESSEL_CONSTANTS } = evalInSandbox(constantsSrc);
    expect(Object.isFrozen(VESSEL_CONSTANTS)).toBe(true);
  });

  it('contains every C.KEY referenced in app.js', () => {
    const { VESSEL_CONSTANTS } = evalInSandbox(constantsSrc);
    const keys = [...new Set([...appSrc.matchAll(/\bC\.([A-Z_]+)\b/g)].map((m) => m[1]))];
    expect(keys.length).toBeGreaterThan(0);
    for (const key of keys) {
      expect(VESSEL_CONSTANTS, `C.${key} used in app.js but missing from VESSEL_CONSTANTS`).toHaveProperty(key);
    }
  });
});
