import React, { useState, useEffect } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth, useLanguage } from '../context/AppContext';
import { Logo } from '../components/common/Logo';
import { ArrowRight, ArrowLeft, UserCheck, Lock, LogIn, Contact, Send, Shield, CheckCircle2 } from 'lucide-react';
import { authService } from '../services/authService';

// Same boxes, button and message styles as the login form, so both look the same.
const INPUT_CLASS = "w-full pl-9.5 pr-4 py-2 bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800 rounded-lg text-slate-800 dark:text-slate-100 placeholder-slate-450 dark:placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-primary-500/20 focus:border-primary-500 dark:focus:border-primary-400 text-sm transition-all";
const BUTTON_CLASS = "w-full inline-flex items-center justify-center gap-2 py-2.5 border border-transparent rounded-lg text-sm font-bold text-white bg-primary-600 hover:bg-primary-700 dark:bg-primary-600 dark:hover:bg-primary-700 shadow-md shadow-primary-500/10 hover:translate-y-[-1px] active:translate-y-[0] transition-all cursor-pointer disabled:opacity-60";
const LABEL_CLASS = "block text-xs font-bold text-slate-500 dark:text-slate-400 uppercase tracking-wider";
const RESEND_SECONDS = 60;

// "Forgot password?" -- uses the backend's existing reset endpoints (routes/auth.py, section 7):
// step 1 sends a code by email (Brevo) or SMS, step 2 checks the code and saves the new password.
const ForgotPasswordForm = ({ startIdentifier, onDone, onBack }) => {
  const [identifier, setIdentifier] = useState(startIdentifier || "");
  const [sentTo, setSentTo] = useState(null);          // identifier the code was sent to
  const [otp, setOtp] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [error, setError] = useState("");
  const [info, setInfo] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [cooldown, setCooldown] = useState(0);

  useEffect(() => {
    if (cooldown <= 0) return undefined;
    const timer = setTimeout(() => setCooldown((c) => c - 1), 1000);
    return () => clearTimeout(timer);
  }, [cooldown]);

  const sendCode = async (e) => {
    if (e) e.preventDefault();
    setError(""); setInfo("");
    if (!identifier.trim()) {
      setError("Please enter your email or mobile number.");
      return;
    }
    setIsLoading(true);
    try {
      const res = await authService.sendResetCode(identifier);
      setSentTo(res.identifier);
      setCooldown(RESEND_SECONDS);
      setInfo(`Code sent to ${res.identifier}. It is valid for 5 minutes.`);
    } catch (err) {
      setError(err.message || "Could not send the code. Please try again.");
    } finally {
      setIsLoading(false);
    }
  };

  const changePassword = async (e) => {
    e.preventDefault();
    setError(""); setInfo("");
    if (!otp.trim() || !newPassword || !confirmPassword) {
      setError("Please fill in all fields.");
      return;
    }
    if (newPassword.length < 6) {
      setError("Password must be at least 6 characters.");
      return;
    }
    if (newPassword !== confirmPassword) {
      setError("Passwords do not match.");
      return;
    }
    setIsLoading(true);
    try {
      await authService.resetPassword({ identifier: sentTo, otp, newPassword });
      onDone(sentTo);
    } catch (err) {
      const msg = String(err.message || "");
      if (/invalid verification code/i.test(msg)) setError("Incorrect code. Please check and try again.");
      else if (/expired/i.test(msg)) setError("Code expired. Please tap Resend code and try again.");
      else setError(msg || "Could not change the password. Please try again.");
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <>
      {error && (
        <div className="mb-4 p-3 bg-red-50 dark:bg-red-950/20 border border-red-200 dark:border-red-900/40 text-xs font-semibold text-red-600 dark:text-red-400 rounded-lg animate-message-appear">
          {error}
        </div>
      )}
      {info && !error && (
        <div className="mb-4 p-3 bg-emerald-50 dark:bg-emerald-950/20 border border-emerald-200 dark:border-emerald-900/40 text-xs font-semibold text-emerald-700 dark:text-emerald-400 rounded-lg animate-message-appear">
          {info}
        </div>
      )}

      {!sentTo ? (
        <form className="space-y-5" onSubmit={sendCode}>
          <p className="text-xs text-slate-500 dark:text-slate-400">
            Enter the email or mobile number you registered with. We will send you a 6-digit code.
          </p>
          <div className="space-y-1.5">
            <label htmlFor="reset-identifier" className={LABEL_CLASS}>Email or mobile number</label>
            <div className="relative flex items-center">
              <Contact className="absolute left-3 h-4 w-4 text-slate-400" />
              <input
                id="reset-identifier"
                type="text"
                required
                value={identifier}
                onChange={(e) => setIdentifier(e.target.value)}
                placeholder="name@example.gov.in or +91 9876543210"
                className={INPUT_CLASS}
              />
            </div>
          </div>
          <button type="submit" disabled={isLoading} className={BUTTON_CLASS}>
            <Send className="h-4.5 w-4.5" />
            <span>{isLoading ? "Sending code..." : "Send code"}</span>
          </button>
        </form>
      ) : (
        <form className="space-y-5" onSubmit={changePassword}>
          <div className="space-y-1.5">
            <div className="flex justify-between items-center">
              <label htmlFor="reset-otp" className={LABEL_CLASS}>Verification code</label>
              <button
                type="button"
                onClick={() => sendCode()}
                disabled={cooldown > 0 || isLoading}
                className="text-[10px] font-bold text-primary-600 hover:text-primary-700 dark:text-primary-400 disabled:text-slate-400 disabled:cursor-not-allowed"
              >
                {cooldown > 0 ? `Resend code in ${cooldown}s` : "Resend code"}
              </button>
            </div>
            <div className="relative flex items-center">
              <Shield className="absolute left-3 h-4 w-4 text-slate-400" />
              <input
                id="reset-otp"
                type="text"
                inputMode="numeric"
                autoComplete="one-time-code"
                maxLength={10}
                required
                value={otp}
                onChange={(e) => setOtp(e.target.value.replace(/\D/g, ""))}
                placeholder="6-digit code"
                className={`${INPUT_CLASS} tracking-widest`}
              />
            </div>
          </div>
          <div className="space-y-1.5">
            <label htmlFor="reset-password" className={LABEL_CLASS}>New password</label>
            <div className="relative flex items-center">
              <Lock className="absolute left-3 h-4 w-4 text-slate-400" />
              <input
                id="reset-password"
                type="password"
                required
                value={newPassword}
                onChange={(e) => setNewPassword(e.target.value)}
                placeholder="At least 6 characters"
                autoComplete="new-password"
                className={INPUT_CLASS}
              />
            </div>
          </div>
          <div className="space-y-1.5">
            <label htmlFor="reset-confirm" className={LABEL_CLASS}>Confirm new password</label>
            <div className="relative flex items-center">
              <Lock className="absolute left-3 h-4 w-4 text-slate-400" />
              <input
                id="reset-confirm"
                type="password"
                required
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                placeholder="••••••••"
                autoComplete="new-password"
                className={INPUT_CLASS}
              />
            </div>
          </div>
          <button type="submit" disabled={isLoading} className={BUTTON_CLASS}>
            <CheckCircle2 className="h-4.5 w-4.5" />
            <span>{isLoading ? "Changing password..." : "Change password"}</span>
          </button>
        </form>
      )}

      <div className="text-center mt-6">
        <button
          type="button"
          onClick={onBack}
          className="inline-flex items-center gap-1 text-xs font-bold text-primary-600 hover:text-primary-700 dark:text-primary-400"
        >
          <ArrowLeft className="h-3.5 w-3.5" />
          Back to login
        </button>
      </div>
    </>
  );
};

export const Login = () => {
  const { login, continueAsGuest } = useAuth();
  const { t } = useLanguage();
  const navigate = useNavigate();

  const [identifier, setIdentifier] = useState("");
  const [password, setPassword] = useState("");
  const [rememberMe, setRememberMe] = useState(false);
  const [error, setError] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [mode, setMode] = useState("login");          // "login" | "forgot"
  const [success, setSuccess] = useState("");

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError("");
    setSuccess("");

    if (!identifier.trim() || !password) {
      setError("Please fill in all fields.");
      return;
    }

    setIsLoading(true);
    try {
      await login(identifier, password);
      navigate('/dashboard');
    } catch (err) {
      setError(err.message || "Invalid credentials. Please try again.");
    } finally {
      setIsLoading(false);
    }
  };

  const handleGuestLogin = () => {
    continueAsGuest();
    navigate('/dashboard');
  };

  return (
    <div className="min-h-screen bg-slate-50 dark:bg-slate-950 flex flex-col justify-center py-12 sm:px-6 lg:px-8 transition-colors duration-150">
      <div className="sm:mx-auto sm:w-full sm:max-w-md flex flex-col items-center">
        <Link to="/">
          <Logo className="h-12 w-12" />
        </Link>
        <h2 className="mt-6 text-center text-2xl font-black font-display text-slate-850 dark:text-white">
          {mode === "forgot" ? "Reset your password" : "Sign in to Sahakar Sahayak"}
        </h2>
        <p className="mt-1 text-center text-xs text-slate-400 dark:text-slate-550">
          “Cooperative knowledge and legal guidance, made simple.”
        </p>
      </div>

      <div className="mt-8 sm:mx-auto sm:w-full sm:max-w-md px-4 sm:px-0">
        <div className="bg-white dark:bg-slate-900 border border-slate-200/80 dark:border-slate-800 py-8 px-6 sm:px-10 rounded-2xl shadow-sm transition-colors">
          {mode === "forgot" ? (
            <ForgotPasswordForm
              startIdentifier={identifier}
              onBack={() => setMode("login")}
              onDone={(id) => {
                setIdentifier(id);
                setPassword("");
                setError("");
                setSuccess("Password changed. Please log in with your new password.");
                setMode("login");
              }}
            />
          ) : (
          <>
          {success && !error && (
            <div className="mb-4 p-3 bg-emerald-50 dark:bg-emerald-950/20 border border-emerald-200 dark:border-emerald-900/40 text-xs font-semibold text-emerald-700 dark:text-emerald-400 rounded-lg animate-message-appear">
              {success}
            </div>
          )}

          {error && (
            <div className="mb-4 p-3 bg-red-50 dark:bg-red-950/20 border border-red-200 dark:border-red-900/40 text-xs font-semibold text-red-600 dark:text-red-400 rounded-lg animate-message-appear">
              {error}
            </div>
          )}

          <form className="space-y-5" onSubmit={handleSubmit}>
            {/* Email or Phone Number Input */}
            <div className="space-y-1.5">
              <label htmlFor="identifier" className="block text-xs font-bold text-slate-500 dark:text-slate-400 uppercase tracking-wider">
                {t('emailOrPhone')}
              </label>
              <div className="relative flex items-center">
                <Contact className="absolute left-3 h-4 w-4 text-slate-400" />
                <input
                  id="identifier"
                  type="text"
                  required
                  value={identifier}
                  onChange={(e) => setIdentifier(e.target.value)}
                  placeholder="name@example.gov.in or +91 9876543210"
                  className="w-full pl-9.5 pr-4 py-2 bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800 rounded-lg text-slate-800 dark:text-slate-100 placeholder-slate-450 dark:placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-primary-500/20 focus:border-primary-500 dark:focus:border-primary-400 text-sm transition-all"
                />
              </div>
            </div>

            {/* Password Input */}
            <div className="space-y-1.5">
              <div className="flex justify-between items-center">
                <label htmlFor="password" className="block text-xs font-bold text-slate-500 dark:text-slate-400 uppercase tracking-wider">
                  {t('password')}
                </label>
                <button
                  type="button"
                  onClick={() => { setError(""); setSuccess(""); setMode("forgot"); }}
                  className="text-[10px] font-bold text-primary-600 hover:text-primary-700 dark:text-primary-400"
                >
                  {t('forgotPassword')}
                </button>
              </div>
              <div className="relative flex items-center">
                <Lock className="absolute left-3 h-4 w-4 text-slate-400" />
                <input
                  id="password"
                  type="password"
                  required
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="••••••••"
                  className="w-full pl-9.5 pr-4 py-2 bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800 rounded-lg text-slate-800 dark:text-slate-100 placeholder-slate-450 dark:placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-primary-500/20 focus:border-primary-500 dark:focus:border-primary-400 text-sm transition-all"
                />
              </div>
            </div>

            {/* Remember Me */}
            <div className="flex items-center">
              <input
                id="remember-me"
                type="checkbox"
                checked={rememberMe}
                onChange={(e) => setRememberMe(e.target.checked)}
                className="h-4 w-4 rounded border-slate-350 dark:border-slate-700 text-primary-600 focus:ring-primary-500"
              />
              <label htmlFor="remember-me" className="ml-2 block text-xs font-semibold text-slate-650 dark:text-slate-400">
                {t('rememberMe')}
              </label>
            </div>

            {/* Log In Button */}
            <button
              type="submit"
              disabled={isLoading}
              className="w-full inline-flex items-center justify-center gap-2 py-2.5 border border-transparent rounded-lg text-sm font-bold text-white bg-primary-600 hover:bg-primary-700 dark:bg-primary-600 dark:hover:bg-primary-700 shadow-md shadow-primary-500/10 hover:translate-y-[-1px] active:translate-y-[0] transition-all cursor-pointer disabled:opacity-60"
            >
              <LogIn className="h-4.5 w-4.5" />
              <span>{isLoading ? "Signing in..." : t('login')}</span>
            </button>
          </form>

          {/* Spacer / Separator */}
          <div className="relative my-6">
            <div className="absolute inset-0 flex items-center">
              <div className="w-full border-t border-slate-200 dark:border-slate-800" />
            </div>
            <div className="relative flex justify-center text-xs">
              <span className="bg-white dark:bg-slate-900 px-3 text-slate-400 dark:text-slate-500">
                Or explore without password
              </span>
            </div>
          </div>

          {/* Guest CTA */}
          <button
            onClick={handleGuestLogin}
            className="w-full inline-flex items-center justify-center gap-2 py-2.5 border border-slate-200 dark:border-slate-800 rounded-lg text-sm font-bold text-slate-700 dark:text-slate-200 bg-slate-50 hover:bg-slate-100 dark:bg-slate-800 dark:hover:bg-slate-800/80 transition-colors cursor-pointer"
          >
            <UserCheck className="h-4.5 w-4.5 text-slate-400" />
            <span>{t('continueAsGuest')}</span>
            <ArrowRight className="h-3.5 w-3.5" />
          </button>

          {/* Register Link */}
          <div className="text-center mt-6">
            <Link to="/register" className="text-xs font-bold text-primary-600 hover:text-primary-700 dark:text-primary-400">
              {t('dontHaveAccount')}
            </Link>
          </div>
          </>
          )}
        </div>
      </div>
    </div>
  );
};

export default Login;
