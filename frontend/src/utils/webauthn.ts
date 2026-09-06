/**
 * WebAuthn API for SecureMed
 *
 * Security requirement #4: تسجيل الدخول بالبصمة + الاعتماد على البصمة
 *
 * The private key stays in the device's secure hardware and is released only after
 * the biometric prompt succeeds; the server keeps the public key and verifies a
 * signature over a challenge it issued itself.
 *
 * Two things were wrong here before, and both were fatal:
 *
 *  1. The challenge was generated in this file with crypto.getRandomValues(), as
 *     the old comment ("in production, this comes from the server") admitted. A
 *     challenge the client picks proves nothing — the whole ceremony can be
 *     assembled offline, and the server has no way to tell a live authenticator
 *     from a replay.
 *  2. The assertion was never sent anywhere. Login.tsx passed `assertion.id` as
 *     `biometric_response` and a string built from it as `biometric_template`, so
 *     the signature — the only part that proves anything — was discarded. The
 *     template had to match byte-for-byte what enrollment stored, which it never
 *     could, so browser biometric login could not have worked even once.
 *
 * The device id is also owned here now. The three call sites used to invent their
 * own (`credential.id`, `webauthn-<ua>`, `web-<ua>`), so enrollment and login
 * disagreed about which device was asking.
 */
import { authAPI } from '../api/client';

// WebAuthn type definitions

/** What GET /auth/biometric/enroll/ returns. */
export interface PublicKeyCredentialCreationOptionsJSON {
  challenge: string; // base64url
  rp: { name: string; id?: string };
  user: {
    id: string; // base64url
    name: string;
    displayName: string;
  };
  pubKeyCredParams: Array<{ type: 'public-key'; alg: number }>;
  timeout?: number;
  excludeCredentials?: Array<{
    type: 'public-key';
    id: string; // base64url
    transports?: string[];
  }>;
  authenticatorSelection?: {
    authenticatorAttachment?: 'platform' | 'cross-platform';
    residentKey?: 'required' | 'preferred' | 'discouraged';
    userVerification?: 'required' | 'preferred' | 'discouraged';
  };
  attestation?: 'none' | 'indirect' | 'direct';
  extensions?: Record<string, unknown>;
}

/** What POST /auth/biometric/enroll/ expects. */
export interface EnrollmentPayload {
  credential_id: string;
  public_key: string; // base64url SPKI DER
  client_data_json: string; // base64url
}

/** What POST /auth/biometric/login/ expects, minus challenge_id. */
export interface AssertionPayload {
  signature: string; // base64url
  client_data_json: string; // base64url
  authenticator_data: string; // base64url
}

/** What POST /auth/biometric/challenge/ returns. */
export interface ServerLoginChallenge {
  challenge_id: string;
  challenge: string; // base64url
  rp_id: string;
  timeout: number;
  user_verification: 'required' | 'preferred' | 'discouraged';
  allow_credentials: Array<{ type: 'public-key'; id: string; transports?: string[] }>;
}

// ============== Utility Functions ==============

/**
 * Base64URL encode an ArrayBuffer.
 */
export function bufferToBase64URL(buffer: ArrayBuffer): string {
  const bytes = new Uint8Array(buffer);
  let str = '';
  for (const byte of bytes) {
    str += String.fromCharCode(byte);
  }
  const base64 = btoa(str);
  return base64.replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '');
}

/**
 * Decode a Base64URL string to an ArrayBuffer.
 */
export function base64URLToBuffer(base64url: string): ArrayBuffer {
  // Pad with '='
  const base64 = base64url.replace(/-/g, '+').replace(/_/g, '/');
  const padLength = (4 - (base64.length % 4)) % 4;
  const padded = base64 + '='.repeat(padLength);

  const binaryString = atob(padded);
  const bytes = new Uint8Array(binaryString.length);
  for (let i = 0; i < binaryString.length; i++) {
    bytes[i] = binaryString.charCodeAt(i);
  }
  return bytes.buffer;
}

/**
 * Check if WebAuthn is available in this browser.
 */
export function isWebAuthnAvailable(): boolean {
  return (
    typeof window !== 'undefined' &&
    window.PublicKeyCredential !== undefined &&
    typeof window.PublicKeyCredential.isUserVerifyingPlatformAuthenticatorAvailable === 'function'
  );
}

/**
 * Check if a platform authenticator (biometric) is available.
 */
export async function isBiometricAvailable(): Promise<boolean> {
  if (!isWebAuthnAvailable()) return false;
  try {
    return await window.PublicKeyCredential.isUserVerifyingPlatformAuthenticatorAvailable();
  } catch {
    return false;
  }
}

// ============== Registration ==============

/**
 * Run the WebAuthn create() ceremony against options issued by the server.
 *
 * The public key is read with `response.getPublicKey()` (WebAuthn Level 2), which
 * hands back SPKI DER directly. That is why the server asks for `attestation:
 * 'none'` and never parses an attestation object: attestation only identifies the
 * authenticator's make and model, and the request is already authenticated, so it
 * would buy nothing while forcing CBOR parsing into the login path.
 *
 * @param options - the creation options returned by GET /auth/biometric/enroll/
 * @returns the fields the server needs to store the credential
 */
export async function registerWebAuthnCredential(
  options: PublicKeyCredentialCreationOptionsJSON
): Promise<EnrollmentPayload> {
  if (!isWebAuthnAvailable()) {
    throw new Error('WebAuthn غير مدعوم في هذا المتصفح');
  }

  const platformAuthAvailable = await isBiometricAvailable();
  if (!platformAuthAvailable) {
    throw new Error('البصمة غير متاحة على هذا الجهاز. استخدم متصفحاً حديثاً يدعم WebAuthn');
  }

  const publicKeyOptions: PublicKeyCredentialCreationOptions = {
    // Server-issued. Never generated here.
    challenge: base64URLToBuffer(options.challenge),
    rp: options.rp,
    user: {
      id: base64URLToBuffer(options.user.id),
      name: options.user.name,
      displayName: options.user.displayName,
    },
    pubKeyCredParams: options.pubKeyCredParams,
    timeout: options.timeout ?? 60000,
    excludeCredentials: (options.excludeCredentials ?? []).map((c) => ({
      type: c.type,
      id: base64URLToBuffer(c.id),
      transports: c.transports as AuthenticatorTransport[] | undefined,
    })),
    authenticatorSelection: options.authenticatorSelection,
    attestation: options.attestation ?? 'none',
  };

  const credential = (await navigator.credentials.create({
    publicKey: publicKeyOptions,
  })) as PublicKeyCredential | null;

  if (!credential) {
    throw new Error('فشل في إنشاء بيانات الاعتماد البيومترية');
  }

  const response = credential.response as AuthenticatorAttestationResponse;
  if (typeof response.getPublicKey !== 'function') {
    throw new Error('متصفحك قديم ولا يوفر المفتاح العام. حدّث المتصفح لتفعيل البصمة');
  }
  const spki = response.getPublicKey();
  if (!spki) {
    throw new Error('لم يوفر المتصفح مفتاحاً عاماً بصيغة مدعومة');
  }

  return {
    credential_id: bufferToBase64URL(credential.rawId),
    public_key: bufferToBase64URL(spki),
    client_data_json: bufferToBase64URL(response.clientDataJSON),
  };
}

// ============== Authentication ==============

/**
 * Run the WebAuthn get() ceremony against a challenge issued by the server.
 *
 * Everything the ceremony is bound to comes from `challenge`: the random bytes,
 * the RP id, and the list of credentials the server has on file for this device.
 * `allow_credentials` may be empty — that is what a decoy challenge for an
 * unknown account looks like, and the client deliberately cannot tell the
 * difference, so it runs the ceremony anyway and lets the server refuse.
 *
 * @param challenge - the body of POST /auth/biometric/challenge/
 * @returns the three fields the server verifies the signature over
 */
export async function authenticateWebAuthn(
  challenge: ServerLoginChallenge
): Promise<AssertionPayload> {
  if (!isWebAuthnAvailable()) {
    throw new Error('WebAuthn غير مدعوم في هذا المتصفح');
  }

  const publicKeyOptions: PublicKeyCredentialRequestOptions = {
    // Server-issued. Never generated here.
    challenge: base64URLToBuffer(challenge.challenge),
    rpId: challenge.rp_id,
    timeout: (challenge.timeout ?? 60) * 1000,
    userVerification: challenge.user_verification ?? 'required',
    allowCredentials: (challenge.allow_credentials ?? []).map((c) => ({
      type: c.type,
      id: base64URLToBuffer(c.id),
      transports: (c.transports ?? ['internal']) as AuthenticatorTransport[],
    })),
  };

  const assertion = (await navigator.credentials.get({
    publicKey: publicKeyOptions,
  })) as PublicKeyCredential | null;

  if (!assertion) {
    throw new Error('فشل في المصادقة البيومترية');
  }

  const response = assertion.response as AuthenticatorAssertionResponse;

  return {
    signature: bufferToBase64URL(response.signature),
    client_data_json: bufferToBase64URL(response.clientDataJSON),
    authenticator_data: bufferToBase64URL(response.authenticatorData),
  };
}

// ============== Device identity ==============

const DEVICE_ID_KEY = 'securemed_device_id';
const ENROLLED_EMAILS_KEY = 'securemed_biometric_emails';

/**
 * The id this browser is known by on the server, created once and kept.
 *
 * `BiometricProfile` is keyed on (user, device_id), and the challenge endpoint
 * looks up the credential by that pair. Enrollment and login therefore have to
 * agree on the string. They did not: enrollment sent `credential.id` from one
 * page and `webauthn-<userAgent>` from another, while login sent
 * `web-<userAgent>`, so a device enrolled from the profile page could never be
 * found again at login. Deriving it from the user agent was doubly wrong — a
 * browser update silently renames the device.
 */
export function getDeviceId(): string {
  let id = localStorage.getItem(DEVICE_ID_KEY);
  if (!id) {
    id = crypto.randomUUID();
    localStorage.setItem(DEVICE_ID_KEY, id);
  }
  return id;
}

/** A human-readable name for the device list in the security settings. */
export function describeDevice(): string {
  const ua = navigator.userAgent;
  const browser = /Edg\//.test(ua) ? 'Edge'
    : /Chrome\//.test(ua) ? 'Chrome'
    : /Firefox\//.test(ua) ? 'Firefox'
    : /Safari\//.test(ua) ? 'Safari'
    : 'متصفح';
  const platform = (navigator as any).userAgentData?.platform
    || (/Windows/.test(ua) ? 'Windows'
      : /Mac OS/.test(ua) ? 'macOS'
      : /Android/.test(ua) ? 'Android'
      : /iPhone|iPad/.test(ua) ? 'iOS'
      : /Linux/.test(ua) ? 'Linux'
      : 'جهاز');
  return `${browser} على ${platform}`;
}

// ============== Local UI hints ==============

/**
 * Which accounts have enrolled a credential *in this browser*.
 *
 * This is a convenience list for the login screen — it decides whether the
 * fingerprint button is worth offering — and nothing more. It is not consulted
 * by the server and carries no key material: the credential ids now come back
 * inside the server's challenge, so nothing here can put enrollment and login
 * out of step. Treat a stale entry as a bad hint, never as a permission.
 */
function readEnrolledEmails(): string[] {
  try {
    const data = localStorage.getItem(ENROLLED_EMAILS_KEY);
    const parsed = data ? JSON.parse(data) : [];
    return Array.isArray(parsed) ? parsed.filter((e) => typeof e === 'string') : [];
  } catch {
    return [];
  }
}

export function rememberEnrolledEmail(email: string): void {
  const normalized = email.trim().toLowerCase();
  const emails = readEnrolledEmails();
  if (!emails.includes(normalized)) {
    emails.push(normalized);
    localStorage.setItem(ENROLLED_EMAILS_KEY, JSON.stringify(emails));
  }
}

export function isEnrolledOnThisDevice(email: string): boolean {
  return readEnrolledEmails().includes(email.trim().toLowerCase());
}

export function forgetEnrolledEmail(email: string): void {
  const normalized = email.trim().toLowerCase();
  localStorage.setItem(
    ENROLLED_EMAILS_KEY,
    JSON.stringify(readEnrolledEmails().filter((e) => e !== normalized))
  );
}

export function clearEnrolledEmails(): void {
  localStorage.removeItem(ENROLLED_EMAILS_KEY);
}

// ============== High-level API ==============

/** Turn a DOMException from the ceremony into something a patient can read. */
function describeCeremonyError(err: any, fallback: string): string {
  switch (err?.name) {
    case 'InvalidStateError':
      return 'البصمة مسجلة مسبقاً على هذا الجهاز';
    case 'NotAllowedError':
      return 'تم رفض الإذن أو انتهت المهلة';
    case 'SecurityError':
      return 'النطاق الحالي غير مسموح لتسجيل البصمة';
    default:
      return err?.response?.data?.detail
        || err?.response?.data?.error
        || err?.message
        || fallback;
  }
}

/**
 * Enroll this browser's platform authenticator for the signed-in user.
 *
 * Three round trips, in this order and no other: ask the server for creation
 * options (which is where the challenge comes from), run create(), then hand the
 * server the public key together with the clientDataJSON that proves the
 * ceremony answered *that* challenge on *this* origin.
 */
export async function enrollBiometric(
  deviceName?: string
): Promise<{ success: boolean; error?: string }> {
  try {
    const { data: options } = await authAPI.biometricRegistrationOptions();
    const payload = await registerWebAuthnCredential(options);

    await authAPI.enrollBiometric({
      device_id: getDeviceId(),
      device_name: deviceName?.trim() || describeDevice(),
      platform: 'WEB',
      ...payload,
    });

    rememberEnrolledEmail(options.user.name);
    return { success: true };
  } catch (err: any) {
    return { success: false, error: describeCeremonyError(err, 'فشل في تسجيل البصمة') };
  }
}

/**
 * Log in with the platform authenticator, start to finish.
 *
 * Returns the user and tokens straight from the server so the caller only has to
 * put them in the store. The old version returned an assertion and left it to
 * `Login.tsx` to invent a payload out of it, which is how the signature ended up
 * being thrown away.
 */
export async function loginWithBiometric(
  userEmail: string
): Promise<{ success: boolean; user?: any; tokens?: any; error?: string }> {
  try {
    const { data: challenge } = await authAPI.biometricChallenge(userEmail, getDeviceId());
    const assertion = await authenticateWebAuthn(challenge as ServerLoginChallenge);

    const { data } = await authAPI.biometricLogin({
      challenge_id: challenge.challenge_id,
      ...assertion,
    });

    rememberEnrolledEmail(userEmail);
    return { success: true, user: data.user, tokens: data.tokens };
  } catch (err: any) {
    if (err?.name === 'NotAllowedError') {
      return { success: false, error: 'تم رفض المصادقة البيومترية' };
    }
    return {
      success: false,
      error: describeCeremonyError(err, 'فشل المصادقة البيومترية'),
    };
  }
}

// Type augmentation for TypeScript
declare global {
  interface Window {
    PublicKeyCredential: {
      isUserVerifyingPlatformAuthenticatorAvailable: () => Promise<boolean>;
      creationOptions?: any;
      requestOptions?: any;
    };
  }
}
