"use client";

import React, { useEffect, useState } from "react";
import { MessageSquare, Clock, ArrowLeft, Bot, User, Archive } from "lucide-react";
import Link from "next/link";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { motion, AnimatePresence } from "framer-motion";

type Session = {
  session_id: string;
  title: string;
  updated_at: string;
};

type Message = {
  id: string;
  role: "user" | "assistant";
  content: string;
};

export default function ArchivePage() {
  const [sessions, setSessions] = useState<Session[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedSession, setSelectedSession] = useState<string | null>(null);
  const [history, setHistory] = useState<Message[]>([]);
  const [historyLoading, setHistoryLoading] = useState(false);

  useEffect(() => {
    const fetchSessions = async () => {
      try {
        const res = await fetch("/api/sessions");
        if (res.ok) {
          const data = await res.json();
          setSessions(data.sessions || []);
        }
      } catch (err) {
        console.error("Error fetching sessions:", err);
      } finally {
        setLoading(false);
      }
    };
    fetchSessions();
  }, []);

  const handleSelectSession = async (sessionId: string) => {
    setSelectedSession(sessionId);
    setHistoryLoading(true);
    setHistory([]);
    try {
      const res = await fetch(`/api/history?session_id=${sessionId}`);
      if (res.ok) {
        const data = await res.json();
        setHistory(data.history || []);
      }
    } catch (err) {
      console.error("Error fetching history:", err);
    } finally {
      setHistoryLoading(false);
    }
  };

  const formatDate = (dateString: string) => {
    const d = new Date(dateString);
    return d.toLocaleDateString("th-TH", {
      year: "numeric",
      month: "short",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  };

  return (
    <div className="h-full flex flex-col md:flex-row bg-white relative">
      {/* Sidebar for Sessions */}
      <div className={`md:w-1/3 lg:w-1/4 border-r border-gray-200 h-full flex flex-col ${selectedSession ? 'hidden md:flex' : 'flex'}`}>
        <div className="p-6 border-b border-gray-100 flex items-center justify-between">
          <h2 className="text-xl font-bold text-[#003B70] flex items-center gap-2">
            <Clock size={20} /> คลังประวัติแชท
          </h2>
        </div>
        <div className="flex-1 overflow-y-auto p-4 space-y-3">
          {loading ? (
            <div className="flex items-center justify-center h-full text-gray-400 text-sm">กำลังโหลด...</div>
          ) : sessions.length === 0 ? (
            <div className="text-center text-gray-500 mt-10">ยังไม่มีประวัติการแชท</div>
          ) : (
            sessions.map((s) => (
              <div
                key={s.session_id}
                onClick={() => handleSelectSession(s.session_id)}
                className={`p-4 rounded-xl cursor-pointer border transition-all ${
                  selectedSession === s.session_id
                    ? "bg-blue-50 border-blue-200"
                    : "bg-white border-gray-100 hover:border-gray-300 hover:bg-gray-50 shadow-sm"
                }`}
              >
                <div className="flex items-start gap-3">
                  <MessageSquare size={16} className={`mt-1 shrink-0 ${selectedSession === s.session_id ? 'text-blue-500' : 'text-gray-400'}`} />
                  <div>
                    <h3 className="text-sm font-medium text-gray-800 line-clamp-2 leading-relaxed">
                      {s.title}
                    </h3>
                    <p className="text-xs text-gray-400 mt-2">{formatDate(s.updated_at)}</p>
                  </div>
                </div>
              </div>
            ))
          )}
        </div>
      </div>

      {/* Main Content Area for Chat History */}
      <div className={`flex-1 h-full flex flex-col bg-gray-50/50 ${!selectedSession ? 'hidden md:flex' : 'flex'}`}>
        {selectedSession ? (
          <>
            <div className="p-4 border-b border-gray-200 bg-white flex items-center gap-4 md:hidden">
              <button onClick={() => setSelectedSession(null)} className="p-2 hover:bg-gray-100 rounded-full">
                <ArrowLeft size={20} className="text-gray-600" />
              </button>
              <h2 className="font-medium text-gray-800 line-clamp-1">
                {sessions.find((s) => s.session_id === selectedSession)?.title || "Chat History"}
              </h2>
            </div>
            
            <div className="flex-1 overflow-y-auto p-4 md:p-8 scroll-smooth">
              <div className="max-w-3xl mx-auto space-y-8">
                {historyLoading ? (
                  <div className="flex justify-center mt-20">
                    <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500"></div>
                  </div>
                ) : history.length === 0 ? (
                  <div className="text-center text-gray-500 mt-20">ไม่พบข้อความในประวัติการแชทนี้</div>
                ) : (
                  <AnimatePresence>
                    {history.map((m) => (
                      <motion.div
                        key={m.id}
                        initial={{ opacity: 0, y: 10 }}
                        animate={{ opacity: 1, y: 0 }}
                        className={`flex gap-4 ${m.role === "user" ? "justify-end" : "justify-start"}`}
                      >
                        {m.role === "assistant" && (
                          <div className="w-8 h-8 rounded-full bg-blue-100 flex items-center justify-center shrink-0 mt-1 shadow-sm border border-blue-200">
                            <Bot size={18} className="text-blue-700" />
                          </div>
                        )}
                        
                        <div className={`max-w-[85%] ${
                          m.role === "user" 
                            ? "bg-white border border-gray-200 shadow-sm text-gray-800 rounded-2xl px-5 py-3" 
                            : "text-gray-800 prose prose-p:leading-relaxed prose-blue"
                        }`}>
                          <ReactMarkdown remarkPlugins={[remarkGfm]}>
                            {m.content}
                          </ReactMarkdown>
                        </div>

                        {m.role === "user" && (
                          <div className="w-8 h-8 rounded-full bg-gray-200 flex items-center justify-center shrink-0 mt-1 shadow-sm">
                            <User size={18} className="text-gray-500" />
                          </div>
                        )}
                      </motion.div>
                    ))}
                  </AnimatePresence>
                )}
              </div>
            </div>
          </>
        ) : (
          <div className="flex-1 flex flex-col items-center justify-center text-gray-400">
            <Archive size={48} className="mb-4 opacity-20" />
            <p className="text-lg">เลือกประวัติการแชททางด้านซ้ายเพื่ออ่านย้อนหลัง</p>
          </div>
        )}
      </div>
    </div>
  );
}
