'use client';

import Link from 'next/link';
import { use, useEffect, useRef, useState } from 'react';
import {
  ArrowLeft,
  MessageSquare,
  Download,
  Share2,
  Cpu,
} from 'lucide-react';
import { useReport } from '@/hooks/useReports';
import {
  useCreateSession,
  useChatMessages,
  useSendMessage,
} from '@/hooks/useChat';
import { Skeleton } from '@/components/ui/skeleton';
import { ErrorState } from '@/components/ui/error-state';
import toast from 'react-hot-toast';

export default function ReportDetail({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = use(params);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [chatInput, setChatInput] = useState('');
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const { data: report, isLoading, isError } = useReport(id);
  const createSession = useCreateSession();
  const { data: messages, isLoading: loadingMessages } = useChatMessages(
    sessionId ?? ''
  );
  const sendMessage = useSendMessage(sessionId ?? '');

  // Create chat session when report loads
  useEffect(() => {
    if (report && !sessionId && !createSession.isPending) {
      createSession
        .mutateAsync({ report_id: report.id })
        .then((session) => setSessionId(session.id))
        .catch(() => {
          // Non-fatal — chat is optional
        });
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [report?.id]);

  // Auto-scroll on new messages
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const handleSendMessage = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!chatInput.trim() || !sessionId) return;
    const content = chatInput.trim();
    setChatInput('');
    try {
      await sendMessage.mutateAsync({ content });
    } catch {
      toast.error('Failed to send message');
      setChatInput(content);
    }
  };

  const reportDate = report?.report_date
    ? new Date(report.report_date).toISOString().split('T')[0]
    : '';

  return (
    <div className="grid grid-cols-1 lg:grid-cols-[1fr_400px] gap-8 animate-in fade-in duration-700 h-[calc(100vh-8rem)]">

      {/* Report Section */}
      <div className="bg-neutral-950 border border-neutral-800/50 rounded-lg p-8 overflow-y-auto">
        <Link
          href="/reports"
          className="flex items-center gap-2 text-neutral-500 hover:text-neutral-300 text-sm w-fit transition-colors mb-8 font-mono tracking-widest uppercase"
        >
          <ArrowLeft size={16} /> Report Archive
        </Link>

        {isLoading && (
          <div className="space-y-6">
            <Skeleton className="h-10 w-3/4 rounded" />
            <div className="flex gap-3">
              <Skeleton className="h-6 w-28 rounded" />
              <Skeleton className="h-6 w-36 rounded" />
              <Skeleton className="h-6 w-24 rounded" />
            </div>
            <Skeleton className="h-40 rounded" />
            <Skeleton className="h-32 rounded" />
          </div>
        )}

        {isError && (
          <ErrorState message="Failed to load this report" />
        )}

        {!isLoading && !isError && report && (
          <>
            <div className="flex justify-between items-start mb-10 pb-6 border-b border-neutral-800/80">
              <div>
                <h1 className="text-3xl font-light tracking-tight text-white leading-tight">
                  {report.executive_summary}
                </h1>
                <div className="flex gap-4 mt-6 uppercase tracking-widest text-[10px] font-mono font-bold flex-wrap">
                  <span className="text-blue-500 bg-blue-500/10 px-2 py-1 rounded">
                    OSINT Generation
                  </span>
                  <span className="text-neutral-400 bg-neutral-800 px-2 py-1 rounded">
                    {reportDate}
                  </span>
                  {report.published && (
                    <span className="text-emerald-400 bg-emerald-500/10 px-2 py-1 rounded">
                      Published
                    </span>
                  )}
                </div>
              </div>
              <div className="flex gap-2 flex-shrink-0">
                <button
                  aria-label="Download report"
                  className="p-2 bg-neutral-900 border border-neutral-800 text-neutral-400 hover:text-white rounded transition-colors min-h-[44px] min-w-[44px] flex items-center justify-center"
                >
                  <Download size={16} />
                </button>
                <button
                  aria-label="Share report"
                  className="p-2 bg-neutral-900 border border-neutral-800 text-neutral-400 hover:text-white rounded transition-colors min-h-[44px] min-w-[44px] flex items-center justify-center"
                >
                  <Share2 size={16} />
                </button>
              </div>
            </div>

            <article className="prose prose-invert prose-neutral max-w-none">
              {report.content_json ? (
                (() => {
                  try {
                    const parsed = JSON.parse(report.content_json);
                    return (
                      <>
                        {parsed.executive_summary && (
                          <>
                            <h3 className="text-blue-500 font-mono tracking-widest text-sm uppercase">
                              Executive Summary
                            </h3>
                            <p className="text-neutral-300 font-light leading-relaxed">
                              {parsed.executive_summary}
                            </p>
                          </>
                        )}
                        {parsed.key_indicators && (
                          <>
                            <h3 className="text-blue-500 font-mono tracking-widest text-sm uppercase mt-8">
                              Key Indicators
                            </h3>
                            <ul className="list-disc pl-5 space-y-2 text-neutral-400 font-light">
                              {parsed.key_indicators.map(
                                (item: string, i: number) => (
                                  <li key={i}>{item}</li>
                                )
                              )}
                            </ul>
                          </>
                        )}
                        {parsed.scenarios && (
                          <>
                            <h3 className="text-blue-500 font-mono tracking-widest text-sm uppercase mt-8">
                              Alternative Scenario Generation
                            </h3>
                            <p className="text-neutral-300 font-light leading-relaxed">
                              {parsed.scenarios}
                            </p>
                          </>
                        )}
                        {!parsed.executive_summary &&
                          !parsed.key_indicators &&
                          !parsed.scenarios && (
                            <pre className="text-neutral-400 font-mono text-xs whitespace-pre-wrap">
                              {report.content_json}
                            </pre>
                          )}
                      </>
                    );
                  } catch {
                    return (
                      <p className="text-neutral-300 font-light leading-relaxed">
                        {report.content_json}
                      </p>
                    );
                  }
                })()
              ) : (
                <p className="text-neutral-500 font-mono text-sm uppercase tracking-widest">
                  Report content unavailable
                </p>
              )}
            </article>
          </>
        )}
      </div>

      {/* Chat Sidebar */}
      <div className="bg-neutral-900 border border-neutral-800/80 rounded-lg flex flex-col overflow-hidden relative shadow-2xl">
        <div className="bg-blue-950/20 border-b border-blue-900/40 p-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded bg-blue-600/10 border border-blue-500/30 flex items-center justify-center text-blue-500">
              <Cpu size={16} />
            </div>
            <div>
              <h3 className="text-sm font-bold text-white uppercase tracking-widest">
                Scenario Agent
              </h3>
              <p className="text-[10px] text-blue-400 font-mono uppercase tracking-widest">
                Locked to Report Context
              </p>
            </div>
          </div>
          <div
            className={`h-2 w-2 rounded-full ring-2 ${
              sessionId
                ? 'bg-blue-500 animate-pulse ring-blue-500/20'
                : 'bg-neutral-700 ring-neutral-700/20'
            }`}
          />
        </div>

        {/* Chat Feed */}
        <div className="flex-1 p-4 overflow-y-auto space-y-6">
          {/* System greeting */}
          {!sessionId && !createSession.isPending && (
            <div className="flex gap-4">
              <div className="w-6 h-6 rounded-full bg-neutral-800 flex-shrink-0" />
              <div>
                <p className="text-sm text-neutral-500 bg-neutral-800/50 border border-neutral-800 p-3 rounded-lg rounded-tl-none font-mono text-xs">
                  Chat session unavailable
                </p>
              </div>
            </div>
          )}

          {createSession.isPending && (
            <div className="flex gap-4">
              <div className="w-6 h-6 rounded-full bg-blue-600/20 flex-shrink-0" />
              <Skeleton className="h-16 flex-1 rounded-lg rounded-tl-none" />
            </div>
          )}

          {sessionId && !loadingMessages && messages?.length === 0 && (
            <div className="flex gap-4">
              <div className="w-6 h-6 rounded-full bg-blue-600/20 flex-shrink-0" />
              <div>
                <p className="text-sm text-neutral-300 bg-neutral-800/50 border border-neutral-800 p-3 rounded-lg rounded-tl-none font-light">
                  I am explicitly constrained to this intelligence brief. I
                  cannot access broader knowledge. What variable would you like
                  me to simulate against these findings?
                </p>
              </div>
            </div>
          )}

          {messages?.map((msg) => (
            <div
              key={msg.id}
              className={`flex gap-4 ${
                msg.role === 'user' ? 'justify-end' : ''
              }`}
            >
              {msg.role === 'assistant' && (
                <div className="w-6 h-6 rounded-full bg-blue-600/20 flex-shrink-0" />
              )}
              <div
                className={`p-3 rounded-lg max-w-[85%] text-sm ${
                  msg.role === 'user'
                    ? 'bg-blue-600/10 border border-blue-500/20 text-blue-100 font-mono rounded-tr-none'
                    : 'bg-neutral-800/50 border border-neutral-800 text-neutral-300 font-light rounded-tl-none'
                }`}
              >
                {msg.content}
              </div>
            </div>
          ))}

          {sendMessage.isPending && (
            <div className="flex gap-4">
              <div className="w-6 h-6 rounded-full bg-blue-600/20 flex-shrink-0" />
              <div className="p-3 rounded-lg bg-neutral-800/50 border border-neutral-800">
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

        {/* Chat Input */}
        <div className="p-4 border-t border-neutral-800 bg-neutral-950">
          <form onSubmit={handleSendMessage} className="relative">
            <input
              type="text"
              value={chatInput}
              onChange={(e) => setChatInput(e.target.value)}
              placeholder="Extract drivers, or simulate a 'what-if' node..."
              disabled={!sessionId || sendMessage.isPending}
              className="w-full bg-neutral-900 border border-neutral-700 rounded p-3 pr-10 text-sm text-white placeholder-neutral-500 focus:outline-none focus:ring-1 focus:ring-blue-500 font-mono disabled:opacity-50"
              aria-label="Chat message"
            />
            <button
              type="submit"
              disabled={!chatInput.trim() || !sessionId || sendMessage.isPending}
              className="absolute right-3 top-3 text-neutral-500 hover:text-blue-500 disabled:text-neutral-700 transition-colors"
              aria-label="Send message"
            >
              <MessageSquare size={16} />
            </button>
          </form>
        </div>
      </div>
    </div>
  );
}
