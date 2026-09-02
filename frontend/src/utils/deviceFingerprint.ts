/**
 * SecureMed Device Fingerprinting Library
 * Collects hardware, browser, and environment data to generate a unique device fingerprint.
 */

export interface DeviceInfo {
  mac_address?: string; // We can only simulate or request this from a native wrapper
  os_info: string;
  browser_info: string;
  screen_resolution: string;
  timezone_offset: string;
  language: string;
  hardware_concurrency: string;
  device_memory: string;
  device_fingerprint: string;
}

export const getDeviceFingerprint = async (): Promise<DeviceInfo> => {
  // We collect various pieces of information to generate a unique fingerprint
  const screen_resolution = `${window.screen.width}x${window.screen.height}x${window.screen.colorDepth}`;
  const timezone_offset = new Date().getTimezoneOffset().toString();
  const language = navigator.language || 'unknown';
  
  // navigator properties that might not be in standard TS lib
  const nav = navigator as any;
  const hardware_concurrency = (nav.hardwareConcurrency || 'unknown').toString();
  const device_memory = (nav.deviceMemory || 'unknown').toString();
  const userAgent = navigator.userAgent;

  // Basic OS and Browser parsing from UA (for frontend context)
  const os_info = parseOS(userAgent);
  const browser_info = parseBrowser(userAgent);

  // Generate a hash based on the collected info
  const rawString = `${screen_resolution}|${timezone_offset}|${language}|${hardware_concurrency}|${device_memory}|${userAgent}`;
  const device_fingerprint = await generateHash(rawString);

  return {
    os_info,
    browser_info,
    screen_resolution,
    timezone_offset,
    language,
    hardware_concurrency,
    device_memory,
    device_fingerprint,
    mac_address: getStoredMacAddress() // Will return stored or empty
  };
};

// Simple hashing function using Web Crypto API
async function generateHash(message: string): Promise<string> {
  const msgUint8 = new TextEncoder().encode(message);
  const hashBuffer = await crypto.subtle.digest('SHA-256', msgUint8);
  const hashArray = Array.from(new Uint8Array(hashBuffer));
  const hashHex = hashArray.map(b => b.toString(16).padStart(2, '0')).join('');
  return hashHex;
}

function parseOS(ua: string): string {
  if (ua.includes('Win')) return 'Windows';
  if (ua.includes('Mac')) return 'MacOS';
  if (ua.includes('Linux')) return 'Linux';
  if (ua.includes('Android')) return 'Android';
  if (ua.includes('like Mac OS X')) return 'iOS';
  return 'Unknown OS';
}

function parseBrowser(ua: string): string {
  if (ua.includes('Firefox')) return 'Firefox';
  if (ua.includes('Chrome')) return 'Chrome';
  if (ua.includes('Safari')) return 'Safari';
  if (ua.includes('Edge')) return 'Edge';
  if (ua.includes('MSIE') || ua.includes('Trident/')) return 'Internet Explorer';
  return 'Unknown Browser';
}

function getStoredMacAddress(): string {
  // In a real web app, we cannot get MAC address for security reasons.
  // This would typically be populated by an Electron wrapper or native mobile app.
  // For the sake of the demo, we check local storage if a simulated one exists.
  let mac = localStorage.getItem('simulated_mac_address');
  if (!mac) {
    // Generate a random simulated MAC for testing
    mac = 'XX:XX:XX:XX:XX:XX'.replace(/X/g, () => {
      return '0123456789ABCDEF'.charAt(Math.floor(Math.random() * 16));
    });
    localStorage.setItem('simulated_mac_address', mac);
  }
  return mac;
}
