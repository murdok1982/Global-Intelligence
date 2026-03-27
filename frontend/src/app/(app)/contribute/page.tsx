"use client";

import { useState } from "react";
import { Shield, Lock, Send, AlertTriangle } from "lucide-react";

export default function ContributePage() {
  const [consent, setConsent] = useState(false);
  const [messages, setMessages] = useState([
    {
      role: "agent",
      text: "Connection secure. I am the Intake Operative parsing voluntary submissions. All data provided here is processed by structured generation to protect direct attribution. What alias shall I record for this interaction?",
    }
  ]);
  const [input, setInput] = useState("");

  const handleSend = (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim()) return;
    
    setMessages(prev => [...prev, { role: "user", text: input }]);
    setInput("");

    // Mock branching logic
    setTimeout(() => {
      if (messages.length === 1) {
         setMessages(prev => [...prev, { 
           role: "agent", 
           text: "Acknowledged. Please stipulate the Country and Intelligence Sector (Economic, Military, etc.) corresponding to your data vector." 
         }]);
      } else if (messages.length === 3) {
         setMessages(prev => [...prev, { 
           role: "agent", 
           text: "Understood. Before processing specifics: If you wish internal analysts to verify this signal, you may voluntarily provide a secure phone number with international prefix. This is STRICTLY OPTIONAL. Do you consent to providing verification metadata?" 
         }]);
      } else {
         setMessages(prev => [...prev, { 
           role: "agent", 
           text: "Data packet received and encrypted. Initial confidence score pending internal human-in-the-loop review. This channel remains open for further evidence." 
         }]);
      }
    }, 1000);
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
            Voluntary intelligence extraction. We utilize dynamic parsing to restructure original inputs, eliminating direct traceable markers while preserving signal integrity.
          </p>
        </div>
        <div className="hidden sm:flex items-center gap-2 border border-blue-900/50 bg-blue-900/10 px-3 py-1.5 rounded font-mono text-xs text-blue-400">
          <Lock size={12} /> END-TO-END ENCRYPTED
        </div>
      </div>

      {/* Main Chat Interface */}
      <div className="flex-1 overflow-hidden flex flex-col bg-neutral-950 border border-neutral-800 rounded-lg shadow-2xl">
        
        {/* Messages Feed */}
        <div className="flex-1 overflow-y-auto p-6 space-y-6">
          
          <div className="bg-amber-500/10 border border-amber-500/30 rounded p-4 flex gap-4 max-w-3xl">
            <AlertTriangle size={20} className="text-amber-500 flex-shrink-0" />
            <p className="font-mono text-[11px] text-amber-500/80 uppercase tracking-widest leading-relaxed">
              WARNING: Do not disclose classified material from your respective jurisdiction if not authorized. 
              By proceeding, you consent to our extraction models structuring your narrative into qualitative metadata.
            </p>
          </div>

          {messages.map((msg, i) => (
            <div key={i} className={`flex gap-4 ${msg.role === 'user' ? 'justify-end' : ''}`}>
              {msg.role === 'agent' && (
                <div className="w-8 h-8 rounded bg-neutral-900 border border-neutral-800 flex items-center justify-center text-blue-500 flex-shrink-0">
                  <Shield size={14} />
                </div>
              )}
              <div className={`p-4 rounded-lg max-w-[80%] ${
                msg.role === 'user' 
                  ? 'bg-blue-600/10 border border-blue-500/20 text-blue-100 font-mono text-sm' 
                  : 'bg-neutral-900 border border-neutral-800 text-neutral-300 font-light'
              }`}>
                {msg.text}
              </div>
            </div>
          ))}
        </div>

        {/* Input Form */}
        <div className="p-4 bg-neutral-950 border-t border-neutral-800">
          <form onSubmit={handleSend} className="relative flex items-center">
            <input 
              type="text" 
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Transmit signal..." 
              className="w-full bg-neutral-900 border border-neutral-700/50 rounded p-4 pr-12 text-sm text-white placeholder-neutral-600 focus:outline-none focus:ring-1 focus:ring-blue-500 font-mono"
            />
            <button 
              type="submit" 
              disabled={!input.trim()}
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
