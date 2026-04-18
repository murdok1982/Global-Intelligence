'use client';

import { useRef, useState, useEffect } from 'react';
import { Shield, Lock, Send, AlertTriangle } from 'lucide-react';
import apiClient from '@/lib/api-client';
import type { IntakeRequest, IntakeResponse } from '@/lib/types';

interface ChatEntry {
  role: 'agent' | 'user';
  text: string;
}

export default function ContributePage() {
  const [messages, setMessages] = useState<ChatEntry[]>([
    {
      role: 'agent',
      text: 'Connection secure. I am the Intake Operative parsing voluntary submissions. All data provided here is processed by structured generation to protect direct attribution. What alias shall I record for this interaction?',
    },
  ]);
  const [input, setInput] = useState('');
  const [sessionId, setSessionId] = useState<string | undefined>(undefined);
  const [isSending, setIsSending] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const handleSend = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || isSending) return;

    const userMessage = input.trim();
    setInput('');
    setMessages((prev) => [...prev, { role: 'user', text: userMessage }]);
    setIsSending(true);

    try {
      const payload: IntakeRequest = { message: userMessage };
      if (sessionId) payload.session_id = sessionId;

      const { data } = await apiClient.post<IntakeResponse>(
        '/contributors/intake',
        payload
      );

      if (data.session_id && !sessionId) {
        setSessionId(data.session_id);
      }

      setMessages((prev) => [
        ...prev,
        { role: 'agent', text: data.response },
      ]);
    } catch {
      setMessages((prev) => [
        ...prev,
        {
          role: 'agent',
          text: 'Signal lost. Please re-transmit your data packet.',
        },
      ]);
    } finally {
      setIsSending(false);
    }
  };

  return (
    <div className="max-w-4xl mx-auto h-[calc(100vh-8rem)] flex flex-col pt-8 animate-in fade-in duration-700">

      {/* Header */}
      <div className="mb-6 flex items-start justify-between">
        <div>
          <h1 className="text-3xl font-light tracking-tight text-white uppercase flex items-center gap-3">
            <Shield className="text-blue-500" /> SECURE INTAKE
          </h1>
          <p className="text-neutral-500 mt-2 font-mono text-xs uppercase tracking-widest max-w-xl leading-relaxed">
            Voluntary intelligence extraction. We utilize dynamic parsing to
            restructure original inputs, eliminating direct traceable markers
            while preserving signal integrity.
          </p>
        </div>
        <div className="hidden sm:flex items-center gap-2 border border-blue-900/50 bg-blue-900/10 px-3 py-1.5 rounded font-mono text-xs text-blue-400">
          <Lock size={12} /> END-TO-END ENCRYPTED
        </div>
      </div>

      {/* Chat Interface */}
      <div className="flex-1 overflow-hidden flex flex-col bg-neutral-950 border border-neutral-800 rounded-lg shadow-2xl">

        {/* Messages Feed */}
        <div className="flex-1 overflow-y-auto p-6 space-y-6">
          <div className="bg-amber-500/10 border border-amber-500/30 rounded p-4 flex gap-4 max-w-3xl">
            <AlertTriangle
              size={20}
              className="text-amber-500 flex-shrink-0"
            />
            <p className="font-mono text-[11px] text-amber-500/80 uppercase tracking-widest leading-relaxed">
              WARNING: Do not disclose classified material from your respective
              jurisdiction if not authorized. By proceeding, you consent to our
              extraction models structuring your narrative into qualitative
              metadata.
            </p>
          </div>

          {messages.map((msg, i) => (
            <div
              key={i}
              className={`flex gap-4 ${
                msg.role === 'user' ? 'justify-end' : ''
              }`}
            >
              {msg.role === 'agent' && (
                <div className="w-8 h-8 rounded bg-neutral-900 border border-neutral-800 flex items-center justify-center text-blue-500 flex-shrink-0">
                  <Shield size={14} />
                </div>
              )}
              <div
                className={`p-4 rounded-lg max-w-[80%] ${
                  msg.role === 'user'
                    ? 'bg-blue-600/10 border border-blue-500/20 text-blue-100 font-mono text-sm'
                    : 'bg-neutral-900 border border-neutral-800 text-neutral-300 font-light'
                }`}
              >
                {msg.text}
              </div>
            </div>
          ))}

          {isSending && (
            <div className="flex gap-4">
              <div className="w-8 h-8 rounded bg-neutral-900 border border-neutral-800 flex items-center justify-center text-blue-500 flex-shrink-0">
                <Shield size={14} />
              </div>
              <div className="p-4 rounded-lg bg-neutral-900 border border-neutral-800">
                <div className="flex gap-1">
                  <span className="w-2 h-2 bg-blue-500 rounded-full animate-bounce [animation-delay:0ms]" />
                  <span className="w-2 h-2 bg-blue-500 rounded-full animate-bounce [animation-delay:150ms]" />
                  <span className="w-2 h-2 bg-blue-500 rounded-full animate-bounce [animation-delay:300ms]" />
                </div>
              </div>
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>

        {/* Input Form */}
        <div className="p-4 bg-neutral-950 border-t border-neutral-800">
          <form
            onSubmit={handleSend}
            className="relative flex items-center"
          >
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Transmit signal..."
              disabled={isSending}
              aria-label="Intelligence submission message"
              className="w-full bg-neutral-900 border border-neutral-700/50 rounded p-4 pr-12 text-sm text-white placeholder-neutral-600 focus:outline-none focus:ring-1 focus:ring-blue-500 font-mono disabled:opacity-50"
            />
            <button
              type="submit"
              disabled={!input.trim() || isSending}
              aria-label="Send message"
              className="absolute right-4 text-blue-500 hover:text-blue-400 disabled:text-neutral-700 transition-colors"
            >
              <Send size={18} />
            </button>
          </form>
        </div>
      </div>
    </div>
  );
}
