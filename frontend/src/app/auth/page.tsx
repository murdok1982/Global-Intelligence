'use client';

import { useState } from 'react';
import { useLogin, useRegister } from '@/hooks/useAuth';
import { isMfaRequired } from '@/lib/api/types';
import { Shield, Lock, Eye, EyeOff, AlertTriangle } from 'lucide-react';
import toast from 'react-hot-toast';

type Tab = 'login' | 'register';

export default function AuthPage() {
  const [tab, setTab] = useState<Tab>('login');

  // Login state
  const [loginEmail, setLoginEmail] = useState('');
  const [loginPassword, setLoginPassword] = useState('');

  // Register state
  const [regEmail, setRegEmail] = useState('');
  const [regPassword, setRegPassword] = useState('');
  const [regConfirm, setRegConfirm] = useState('');

  const [showPassword, setShowPassword] = useState(false);

  const login = useLogin();
  const register = useRegister();

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!loginEmail || !loginPassword) return;
    try {
      const result = await login.mutateAsync({
        email: loginEmail,
        password: loginPassword,
      });
      if (isMfaRequired(result)) {
        toast('Verificación adicional requerida', { icon: '🔐' });
      } else {
        toast.success('Acceso concedido');
      }
    } catch (err: unknown) {
      const message =
        err instanceof Error ? err.message : 'Authentication failed';
      toast.error(message);
    }
  };

  const handleRegister = async (e: React.FormEvent) => {
    e.preventDefault();
    if (regPassword !== regConfirm) {
      toast.error('Passwords do not match');
      return;
    }
    if (regPassword.length < 8) {
      toast.error('Password must be at least 8 characters');
      return;
    }
    try {
      await register.mutateAsync({ email: regEmail, password: regPassword });
      toast.success('Account created — please log in');
      setTab('login');
    } catch (err: unknown) {
      const message =
        err instanceof Error ? err.message : 'Registration failed';
      toast.error(message);
    }
  };

  const isLoginLoading = login.isPending;
  const isRegisterLoading = register.isPending;

  return (
    <main className="min-h-screen bg-neutral-950 flex items-center justify-center p-4">
      <div className="w-full max-w-md">
        {/* Header */}
        <div className="text-center mb-10">
          <div className="inline-flex items-center justify-center w-14 h-14 rounded bg-blue-600/10 border border-blue-500/20 mb-6">
            <Shield size={28} className="text-blue-500" />
          </div>
          <h1 className="text-2xl font-light tracking-widest text-white uppercase">
            Global Intelligence
          </h1>
          <p className="text-neutral-500 font-mono text-xs mt-2 uppercase tracking-widest">
            Secure Access Terminal
          </p>
        </div>

        {/* Tab Toggle */}
        <div className="flex border border-neutral-800 rounded overflow-hidden mb-8">
          <button
            onClick={() => setTab('login')}
            className={`flex-1 py-2.5 font-mono text-xs uppercase tracking-widest transition-colors ${
              tab === 'login'
                ? 'bg-blue-600/10 text-blue-400 border-b-2 border-blue-500'
                : 'text-neutral-500 hover:text-neutral-300'
            }`}
          >
            Login
          </button>
          <button
            onClick={() => setTab('register')}
            className={`flex-1 py-2.5 font-mono text-xs uppercase tracking-widest transition-colors ${
              tab === 'register'
                ? 'bg-blue-600/10 text-blue-400 border-b-2 border-blue-500'
                : 'text-neutral-500 hover:text-neutral-300'
            }`}
          >
            Register
          </button>
        </div>

        {/* Login Form */}
        {tab === 'login' && (
          <form onSubmit={handleLogin} className="space-y-5">
            <div>
              <label
                htmlFor="login-email"
                className="block font-mono text-[10px] uppercase tracking-widest text-neutral-500 mb-2"
              >
                Email Address
              </label>
              <input
                id="login-email"
                type="email"
                value={loginEmail}
                onChange={(e) => setLoginEmail(e.target.value)}
                placeholder="operator@agency.gov"
                required
                autoComplete="email"
                className="w-full bg-neutral-900 border border-neutral-700 rounded p-3 text-sm text-white placeholder-neutral-600 focus:outline-none focus:ring-1 focus:ring-blue-500 font-mono"
              />
            </div>

            <div>
              <label
                htmlFor="login-password"
                className="block font-mono text-[10px] uppercase tracking-widest text-neutral-500 mb-2"
              >
                Passphrase
              </label>
              <div className="relative">
                <input
                  id="login-password"
                  type={showPassword ? 'text' : 'password'}
                  value={loginPassword}
                  onChange={(e) => setLoginPassword(e.target.value)}
                  placeholder="••••••••••••"
                  required
                  autoComplete="current-password"
                  className="w-full bg-neutral-900 border border-neutral-700 rounded p-3 pr-10 text-sm text-white placeholder-neutral-600 focus:outline-none focus:ring-1 focus:ring-blue-500 font-mono"
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute right-3 top-3.5 text-neutral-500 hover:text-neutral-300 transition-colors"
                  aria-label={showPassword ? 'Hide password' : 'Show password'}
                >
                  {showPassword ? <EyeOff size={16} /> : <Eye size={16} />}
                </button>
              </div>
            </div>

            {login.isError && (
              <div className="flex items-center gap-3 p-3 bg-red-500/10 border border-red-500/20 rounded">
                <AlertTriangle size={14} className="text-red-500 flex-shrink-0" />
                <p className="text-red-400 font-mono text-xs">
                  Invalid credentials or account not active.
                </p>
              </div>
            )}

            <button
              type="submit"
              disabled={isLoginLoading || !loginEmail || !loginPassword}
              className="w-full py-3 bg-blue-600/10 text-blue-400 hover:bg-blue-600/20 hover:text-blue-300 border border-blue-600/30 rounded font-mono text-xs uppercase tracking-widest transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2 min-h-[44px]"
            >
              {isLoginLoading ? (
                <>
                  <div className="w-3 h-3 border border-blue-500 border-t-transparent rounded-full animate-spin" />
                  Authenticating...
                </>
              ) : (
                <>
                  <Lock size={14} />
                  Authenticate
                </>
              )}
            </button>
          </form>
        )}

        {/* Register Form */}
        {tab === 'register' && (
          <form onSubmit={handleRegister} className="space-y-5">
            <div>
              <label
                htmlFor="reg-email"
                className="block font-mono text-[10px] uppercase tracking-widest text-neutral-500 mb-2"
              >
                Email Address
              </label>
              <input
                id="reg-email"
                type="email"
                value={regEmail}
                onChange={(e) => setRegEmail(e.target.value)}
                placeholder="operator@agency.gov"
                required
                autoComplete="email"
                className="w-full bg-neutral-900 border border-neutral-700 rounded p-3 text-sm text-white placeholder-neutral-600 focus:outline-none focus:ring-1 focus:ring-blue-500 font-mono"
              />
            </div>

            <div>
              <label
                htmlFor="reg-password"
                className="block font-mono text-[10px] uppercase tracking-widest text-neutral-500 mb-2"
              >
                Passphrase
              </label>
              <div className="relative">
                <input
                  id="reg-password"
                  type={showPassword ? 'text' : 'password'}
                  value={regPassword}
                  onChange={(e) => setRegPassword(e.target.value)}
                  placeholder="Min. 8 characters"
                  required
                  autoComplete="new-password"
                  className="w-full bg-neutral-900 border border-neutral-700 rounded p-3 pr-10 text-sm text-white placeholder-neutral-600 focus:outline-none focus:ring-1 focus:ring-blue-500 font-mono"
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute right-3 top-3.5 text-neutral-500 hover:text-neutral-300 transition-colors"
                  aria-label={showPassword ? 'Hide password' : 'Show password'}
                >
                  {showPassword ? <EyeOff size={16} /> : <Eye size={16} />}
                </button>
              </div>
            </div>

            <div>
              <label
                htmlFor="reg-confirm"
                className="block font-mono text-[10px] uppercase tracking-widest text-neutral-500 mb-2"
              >
                Confirm Passphrase
              </label>
              <input
                id="reg-confirm"
                type={showPassword ? 'text' : 'password'}
                value={regConfirm}
                onChange={(e) => setRegConfirm(e.target.value)}
                placeholder="Repeat passphrase"
                required
                autoComplete="new-password"
                className="w-full bg-neutral-900 border border-neutral-700 rounded p-3 text-sm text-white placeholder-neutral-600 focus:outline-none focus:ring-1 focus:ring-blue-500 font-mono"
              />
            </div>

            {register.isError && (
              <div className="flex items-center gap-3 p-3 bg-red-500/10 border border-red-500/20 rounded">
                <AlertTriangle size={14} className="text-red-500 flex-shrink-0" />
                <p className="text-red-400 font-mono text-xs">
                  Registration failed. Email may already be in use.
                </p>
              </div>
            )}

            <button
              type="submit"
              disabled={isRegisterLoading || !regEmail || !regPassword || !regConfirm}
              className="w-full py-3 bg-blue-600/10 text-blue-400 hover:bg-blue-600/20 hover:text-blue-300 border border-blue-600/30 rounded font-mono text-xs uppercase tracking-widest transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2 min-h-[44px]"
            >
              {isRegisterLoading ? (
                <>
                  <div className="w-3 h-3 border border-blue-500 border-t-transparent rounded-full animate-spin" />
                  Creating account...
                </>
              ) : (
                'Create Secure Account'
              )}
            </button>
          </form>
        )}

        <p className="text-center text-neutral-600 font-mono text-[10px] uppercase tracking-widest mt-8">
          All transmissions encrypted · TLS 1.3
        </p>
      </div>
    </main>
  );
}
