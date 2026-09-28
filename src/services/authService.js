// Authentication Service communicating with FastAPI Backend

// FIXED: Forced the absolute URL to your Python backend so it never talks to itself
const BACKEND_URL = import.meta.env.VITE_API_URL || "https://sahakar-sahayak-4.onrender.com";
const API_BASE = `${BACKEND_URL.replace(/\/$/, '')}/api/auth`;

const getUrl = (path) => `${API_BASE}${path}`;

export const authService = {
  /**
   * Step 1: Initiate registration with name, email, phone, and password.
   * Generates secure Email OTP and Phone OTP, returns session ID.
   */
  initiateRegistration: async ({ name, email, phone, password, userType = 'Citizen', preferredLanguage = 'en' }) => {
    try {
      const response = await fetch(getUrl('/register/initiate'), {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          name: name.trim(),
          email: email.trim(),
          phone: phone.trim(),
          password,
          userType,
          preferredLanguage,
        }),
      });

      const data = await response.json().catch(() => ({}));

      if (!response.ok) {
        const errorMsg = data.detail || data.message || 'Failed to initiate registration. Please check your details.';
        throw new Error(errorMsg);
      }

      return data;
    } catch (error) {
      console.error('[authService] initiateRegistration error:', error);
      throw error;
    }
  },

  /**
   * Step 2a: Verify Email OTP
   */
  verifyEmailOtp: async ({ sessionId, otp }) => {
    try {
      const response = await fetch(getUrl('/register/verify-email'), {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          sessionId,
          otp: otp.trim(),
        }),
      });

      const data = await response.json().catch(() => ({}));

      if (!response.ok) {
        const errorMsg = data.detail || data.message || 'Email OTP verification failed.';
        throw new Error(errorMsg);
      }

      return data;
    } catch (error) {
      console.error('[authService] verifyEmailOtp error:', error);
      throw error;
    }
  },

  /**
   * Step 2b: Verify Phone OTP
   */
  verifyPhoneOtp: async ({ sessionId, otp }) => {
    try {
      const response = await fetch(getUrl('/register/verify-phone'), {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          sessionId,
          otp: otp.trim(),
        }),
      });

      const data = await response.json().catch(() => ({}));

      if (!response.ok) {
        const errorMsg = data.detail || data.message || 'Phone OTP verification failed.';
        throw new Error(errorMsg);
      }

      return data;
    } catch (error) {
      console.error('[authService] verifyPhoneOtp error:', error);
      throw error;
    }
  },

  /**
   * Resend OTP for email, phone, or both with 60s cooldown
   */
  resendOtp: async ({ sessionId, target = 'email' }) => {
    try {
      const response = await fetch(getUrl('/register/resend-otp'), {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          sessionId,
          target,
        }),
      });

      const data = await response.json().catch(() => ({}));

      if (!response.ok) {
        const errorMsg = data.detail || data.message || 'Failed to resend verification code.';
        throw new Error(errorMsg);
      }

      return data;
    } catch (error) {
      console.error('[authService] resendOtp error:', error);
      throw error;
    }
  },

  /**
   * Fetch current verification status for a session
   */
  getVerificationStatus: async (sessionId) => {
    try {
      const response = await fetch(getUrl(`/register/status/${sessionId}`), {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
        },
      });

      const data = await response.json().catch(() => ({}));

      if (!response.ok) {
        const errorMsg = data.detail || data.message || 'Failed to fetch verification status.';
        throw new Error(errorMsg);
      }

      return data;
    } catch (error) {
      console.error('[authService] getVerificationStatus error:', error);
      throw error;
    }
  },

  /**
   * Log in user with identifier (email OR phone) and password
   */
  login: async (identifier, password) => {
    try {
      const response = await fetch(getUrl('/login'), {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          identifier: identifier.trim(),
          password,
        }),
      });

      const data = await response.json().catch(() => ({}));

      if (!response.ok) {
        const errorMsg = data.detail || data.message || 'Authentication failed. Please check credentials.';
        throw new Error(errorMsg);
      }

      return data;
    } catch (error) {
      console.error('[authService] login error:', error);
      throw error;
    }
  },

  /**
   * Legacy register helper for backward compatibility
   */
  register: async ({ name, email, phone, password, userType = 'Citizen', preferredLanguage = 'en' }) => {
    return authService.initiateRegistration({ name, email, phone, password, userType, preferredLanguage });
  },

  /**
   * Fetch authenticated user details with JWT token
   */
  getMe: async (token) => {
    try {
      const response = await fetch(getUrl('/me'), {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
      });

      const data = await response.json().catch(() => ({}));

      if (!response.ok) {
        throw new Error(data.detail || data.message || 'Session expired or invalid.');
      }

      return data;
    } catch (error) {
      console.error('[authService] getMe error:', error);
      throw error;
    }
  },

  /**
   * Update profile details (name, email, phone, preferredLanguage, userType)
   */
  updateProfile: async ({ name, email, phone, preferredLanguage, userType }, token) => {
    try {
      const response = await fetch(getUrl('/profile'), {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          name: name?.trim(),
          email: email?.trim(),
          phone: phone?.trim(),
          preferredLanguage,
          userType,
        }),
      });

      const data = await response.json().catch(() => ({}));

      if (!response.ok) {
        const errorMsg = data.detail || data.message || 'Failed to update profile.';
        throw new Error(errorMsg);
      }

      return data;
    } catch (error) {
      console.error('[authService] updateProfile error:', error);
      throw error;
    }
  },

  /**
   * Forgot password, step 1: send a reset code to the email or mobile number.
   * Uses the existing backend endpoint (/password-reset/send-otp): the code is made in Python and
   * sent by Brevo (email) or the SMS gateway (mobile), exactly like registration.
   * A mobile number is tried as typed, then as +91XXXXXXXXXX and as 10 digits (accounts may be
   * saved either way). Returns the identifier that worked -- step 2 must use the same one.
   */
  sendResetCode: async (identifier) => {
    const typed = identifier.trim();
    const digits = typed.replace(/\D/g, '');
    const isPhone = !typed.includes('@') && digits.length >= 10;
    const tries = isPhone ? [...new Set([typed, `+91${digits.slice(-10)}`, digits.slice(-10)])] : [typed];
    let lastError = null;
    for (const id of tries) {
      const response = await fetch(getUrl('/password-reset/send-otp'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ identifier: id }),
      });
      const data = await response.json().catch(() => ({}));
      if (response.ok) return { identifier: id, message: data.message };
      lastError = new Error(data.detail || data.message || 'Could not send the code. Please try again.');
      if (response.status !== 404) break;       // only "account not found" is worth another format
    }
    console.error('[authService] sendResetCode error:', lastError);
    throw lastError;
  },

  /**
   * Forgot password, step 2: check the code and save the new password (/password-reset/confirm).
   */
  resetPassword: async ({ identifier, otp, newPassword }) => {
    const response = await fetch(getUrl('/password-reset/confirm'), {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ identifier, otp: otp.trim(), new_password: newPassword }),
    });
    const data = await response.json().catch(() => ({}));
    if (!response.ok) {
      const detail = String(data.detail || data.message || '');
      const error = new Error(detail || 'Could not change the password. Please try again.');
      error.status = response.status;
      console.error('[authService] resetPassword error:', error);
      throw error;
    }
    return data;
  },
};

export default authService;