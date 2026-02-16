/**
 * AES-256-GCM encryption for LLM API keys.
 * Format: base64(iv_12bytes + ciphertext + tag_16bytes)
 * Key: 32 bytes from LLM_CONFIG_ENCRYPTION_KEY (hex, base64, or hashed).
 */

import { createCipheriv, createDecipheriv, createHash, randomBytes } from "node:crypto";

const ALG = "aes-256-gcm";
const IV_LEN = 12;
const TAG_LEN = 16;
const KEY_LEN = 32;

function getKey(): Buffer {
  const raw = process.env.LLM_CONFIG_ENCRYPTION_KEY;
  if (!raw || raw.length < 16) {
    throw new Error("LLM_CONFIG_ENCRYPTION_KEY must be set (32+ chars) for encryption");
  }
  if (raw.length === 64 && /^[0-9a-fA-F]+$/.test(raw)) {
    return Buffer.from(raw, "hex");
  }
  if (raw.length === 44 && /^[A-Za-z0-9+/=]+$/.test(raw)) {
    const b = Buffer.from(raw, "base64");
    if (b.length === 32) return b;
  }
  return createHash("sha256").update(raw).digest();
}

const ENC_PREFIX = "enc:";

/** Encrypt plaintext. Returns "enc:" + base64. If no key configured, returns plaintext (dev fallback). */
export function encryptLlmKey(plaintext: string): string {
  if (!plaintext) return "";
  if (!isEncryptionConfigured()) {
    console.warn("LLM_CONFIG_ENCRYPTION_KEY not set; storing API key in plain text (dev only)");
    return plaintext;
  }
  const key = getKey();
  const iv = randomBytes(IV_LEN);
  const cipher = createCipheriv(ALG, key, iv);
  const enc = Buffer.concat([cipher.update(plaintext, "utf8"), cipher.final()]);
  const tag = cipher.getAuthTag();
  return ENC_PREFIX + Buffer.concat([iv, enc, tag]).toString("base64");
}

/** Decrypt ciphertext. If prefixed with "enc:", decrypts; else returns as-is (plain). */
export function decryptLlmKey(ciphertext: string): string {
  if (!ciphertext) return "";
  if (!ciphertext.startsWith(ENC_PREFIX)) return ciphertext;
  const key = getKey();
  const buf = Buffer.from(ciphertext.slice(ENC_PREFIX.length), "base64");
  if (buf.length < IV_LEN + TAG_LEN) {
    throw new Error("Invalid encrypted payload");
  }
  const iv = buf.subarray(0, IV_LEN);
  const tag = buf.subarray(buf.length - TAG_LEN);
  const enc = buf.subarray(IV_LEN, buf.length - TAG_LEN);
  const decipher = createDecipheriv(ALG, key, iv);
  decipher.setAuthTag(tag);
  return decipher.update(enc) + decipher.final("utf8");
}

/** Returns true if encryption is configured. */
export function isEncryptionConfigured(): boolean {
  const raw = process.env.LLM_CONFIG_ENCRYPTION_KEY;
  return !!(raw && raw.length >= 16);
}
