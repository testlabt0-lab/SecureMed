/**
 * WebAuthn API for SecureMed
 *
 * Security requirement #4: تسجيل الدخول بالبصمة + الاعتماد على البصمة
 *
 * Implements real WebAuthn (FIDO2) for browser biometric authentication.
 * Uses the Web Authentication API (window.PublicKeyCredential) to:
 * - Register biometric credentials (fingerprint, Face ID, security key)
 * - Authenticate users via challenge-response mechanism
 * - Store credentials securely on the device (never sent to server)
 */

// WebAuthn type definitions
interface PublicKeyCredentialCreationOptionsJSON {
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

interface PublicKeyCredentialRequestOptionsJSON {
  challenge: string; // base64url
  rpId?: string;
  timeout?: number;
  allowCredentials?: Array<{
    type: 'public-key';
    id: string; // base64url
    transports?: string[];
  }>;
  userVerification?: 'required' | 'preferred' | 'discouraged';
  extensions?: Record<string, unknown>;
}

interface AuthenticatorAttestationResponseJSON {
  attestationObject: string; // base64url
  clientDataJSON: string; // base64url
}

interface AuthenticatorAssertionResponseJSON {
  authenticatorData: string; // base64url
  clientDataJSON: string; // base64url
  signature: string; // base64url
  userHandle?: string; // base64url
}

interface RegistrationResponseJSON {
  id: string;
  rawId: string; // base64url
  type: 'public-key';
  response: AuthenticatorAttestationResponseJSON;
  getClientExtensionResults?: () => Record<string, unknown>;
}

interface AuthenticationResponseJSON {
  id: string;
  rawId: string; // base64url
  type: 'public-key';
  response: AuthenticatorAssertionResponseJSON;
  getClientExtensionResults?: () => Record<string, unknown>;
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
 * Initiate WebAuthn credential registration.
 * The user will be prompted to use their biometric (fingerprint/Face ID) or security key.
 *
 * @param userId - The user's ID from the server
 * @param userEmail - The user's email
 * @param userDisplayName - The user's full name
 * @returns The registration response to send to the server
 */
export async function registerWebAuthnCredential(
  userId: string,
  userEmail: string,
  userDisplayName: string
): Promise<RegistrationResponseJSON> {
  if (!isWebAuthnAvailable()) {
    throw new Error('WebAuthn غير مدعوم في هذا المتصفح');
  }

  // Check for platform authenticator (biometric)
  const platformAuthAvailable = await isBiometricAvailable();
  if (!platformAuthAvailable) {
    throw new Error('البصمة غير متاحة على هذا الجهاز. استخدم متصفحاً حديثاً يدعم WebAuthn');
  }

  // Generate a challenge (in production, this comes from the server)
  const challenge = new Uint8Array(32);
  crypto.getRandomValues(challenge);

  // Generate user ID (random bytes)
  const userIdBuffer = new Uint8Array(32);
  crypto.getRandomValues(userIdBuffer);

  const publicKeyOptions: PublicKeyCredentialCreationOptions = {
    challenge: challenge,
    rp: {
      name: 'SecureMed',
      id: window.location.hostname,
    },
    user: {
      id: userIdBuffer,
      name: userEmail,
      displayName: userDisplayName || userEmail,
    },
    pubKeyCredParams: [
      { type: 'public-key', alg: -7 },   // ES256
      { type: 'public-key', alg: -257 }, // RS256
    ],
    timeout: 60000,
    excludeCredentials: [],
    authenticatorSelection: {
      authenticatorAttachment: 'platform', // Require platform biometric
      residentKey: 'preferred',
      userVerification: 'required', // Require biometric verification
    },
    attestation: 'none',
  };

  // Create the credential
  const credential = (await navigator.credentials.create({
    publicKey: publicKeyOptions,
  })) as PublicKeyCredential | null;

  if (!credential) {
    throw new Error('فشل في إنشاء بيانات الاعتماد البيومترية');
  }

  const response = credential.response as AuthenticatorAttestationResponse;

  // Convert to JSON-serializable format
  const registrationResponse: RegistrationResponseJSON = {
    id: credential.id,
    rawId: bufferToBase64URL(credential.rawId),
    type: 'public-key',
    response: {
      attestationObject: bufferToBase64URL(response.attestationObject),
      clientDataJSON: bufferToBase64URL(response.clientDataJSON),
    },
  };

  return registrationResponse;
}

// ============== Authentication ==============

/**
 * Authenticate with a registered WebAuthn credential.
 * The user will be prompted to verify their biometric.
 *
 * @param credentialId - The credential ID from a previous registration
 * @returns The authentication response to send to the server
 */
export async function authenticateWebAuthn(
  credentialId?: string
): Promise<AuthenticationResponseJSON> {
  if (!isWebAuthnAvailable()) {
    throw new Error('WebAuthn غير مدعوم في هذا المتصفح');
  }

  // Generate a challenge (in production, this comes from the server)
  const challenge = new Uint8Array(32);
  crypto.getRandomValues(challenge);

  const publicKeyOptions: PublicKeyCredentialRequestOptions = {
    challenge: challenge,
    rpId: window.location.hostname,
    timeout: 60000,
    userVerification: 'required', // Require biometric
  };

  // If we have a credential ID, add it to allowCredentials
  if (credentialId) {
    publicKeyOptions.allowCredentials = [{
      type: 'public-key',
      id: base64URLToBuffer(credentialId),
      transports: ['internal'],
    }];
  }

  // Get the assertion
  const assertion = (await navigator.credentials.get({
    publicKey: publicKeyOptions,
  })) as PublicKeyCredential | null;

  if (!assertion) {
    throw new Error('فشل في المصادقة البيومترية');
  }

  const response = assertion.response as AuthenticatorAssertionResponse;

  const authResponse: AuthenticationResponseJSON = {
    id: assertion.id,
    rawId: bufferToBase64URL(assertion.rawId),
    type: 'public-key',
    response: {
      authenticatorData: bufferToBase64URL(response.authenticatorData),
      clientDataJSON: bufferToBase64URL(response.clientDataJSON),
      signature: bufferToBase64URL(response.signature),
      userHandle: response.userHandle
        ? bufferToBase64URL(response.userHandle)
        : undefined,
    },
  };

  return authResponse;
}

// ============== Storage ==============

const CREDENTIAL_STORAGE_KEY = 'securemed_webauthn_credentials';

interface StoredCredential {
  userId: string;
  credentialId: string;
  userEmail: string;
  createdAt: string;
}

/**
 * Store a WebAuthn credential ID locally (the actual biometric never leaves the device).
 */
export function storeCredential(userId: string, credentialId: string, userEmail: string): void {
  const credentials = getStoredCredentials();
  const existingIdx = credentials.findIndex((c) => c.userId === userId);
  const newCred: StoredCredential = {
    userId,
    credentialId,
    userEmail,
    createdAt: new Date().toISOString(),
  };
  if (existingIdx >= 0) {
    credentials[existingIdx] = newCred;
  } else {
    credentials.push(newCred);
  }
  localStorage.setItem(CREDENTIAL_STORAGE_KEY, JSON.stringify(credentials));
}

/**
 * Get all stored WebAuthn credentials.
 */
export function getStoredCredentials(): StoredCredential[] {
  try {
    const data = localStorage.getItem(CREDENTIAL_STORAGE_KEY);
    return data ? JSON.parse(data) : [];
  } catch {
    return [];
  }
}

/**
 * Get a stored credential by user email.
 */
export function getCredentialByEmail(email: string): StoredCredential | null {
  return getStoredCredentials().find((c) => c.userEmail === email) || null;
}

/**
 * Remove a stored credential.
 */
export function removeCredential(userId: string): void {
  const credentials = getStoredCredentials().filter((c) => c.userId !== userId);
  localStorage.setItem(CREDENTIAL_STORAGE_KEY, JSON.stringify(credentials));
}

/**
 * Clear all stored credentials.
 */
export function clearAllCredentials(): void {
  localStorage.removeItem(CREDENTIAL_STORAGE_KEY);
}

// ============== High-level API ==============

/**
 * Enroll biometric authentication for the current user.
 * This is the main function to call from the UI.
 */
export async function enrollBiometric(
  userId: string,
  userEmail: string,
  userDisplayName: string
): Promise<{ success: boolean; credentialId: string; error?: string }> {
  try {
    const response = await registerWebAuthnCredential(userId, userEmail, userDisplayName);
    // Store the credential ID for future logins
    storeCredential(userId, response.id, userEmail);
    return { success: true, credentialId: response.id };
  } catch (err: any) {
    if (err.name === 'InvalidStateError') {
      return {
        success: false,
        credentialId: '',
        error: 'البصمة مسجلة مسبقاً على هذا الجهاز',
      };
    }
    if (err.name === 'NotAllowedError') {
      return {
        success: false,
        credentialId: '',
        error: 'تم رفض الإذن أو انتهت المهلة',
      };
    }
    return {
      success: false,
      credentialId: '',
      error: err.message || 'فشل في تسجيل البصمة',
    };
  }
}

/**
 * Login with biometric authentication.
 * Returns the WebAuthn assertion to send to the server.
 */
export async function loginWithBiometric(
  userEmail: string
): Promise<{ success: boolean; assertion?: AuthenticationResponseJSON; error?: string }> {
  try {
    // Look up the stored credential for this user
    const stored = getCredentialByEmail(userEmail);
    if (!stored) {
      return {
        success: false,
        error: 'البصمة غير مسجلة لهذا المستخدم على هذا الجهاز',
      };
    }

    const assertion = await authenticateWebAuthn(stored.credentialId);
    return { success: true, assertion };
  } catch (err: any) {
    if (err.name === 'NotAllowedError') {
      return {
        success: false,
        error: 'تم رفض المصادقة البيومترية',
      };
    }
    return {
      success: false,
      error: err.message || 'فشل في المصادقة البيومترية',
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
