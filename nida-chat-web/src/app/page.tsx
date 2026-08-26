"use client";

import React, { useState, useRef, useEffect } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { motion, AnimatePresence } from "framer-motion";
import { ArrowUp, Bot, User, Sparkles, Lightbulb } from "lucide-react";

type Message = {
  id: string;
  role: "user" | "assistant";
  content: string;
};

export default function ChatPage() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const [sessionId, setSessionId] = useState<string>("");

  useEffect(() => {
    let storedSession = localStorage.getItem("nida_session_id");
    if (!storedSession) {
      storedSession = crypto.randomUUID ? crypto.randomUUID() : Date.now().toString();
      localStorage.setItem("nida_session_id", storedSession);
    }
    setSessionId(storedSession);
  }, []);

  useEffect(() => {
    if (!sessionId) return;
    const fetchHistory = async () => {
      try {
        const res = await fetch(`/api/history?session_id=${sessionId}`);
        if (res.ok) {
          const data = await res.json();
          if (data.history && data.history.length > 0) {
            // Remove intro message if it existed in old format
            const history = data.history.filter((m: any) => m.id !== "intro");
            setMessages(history);
          }
        }
      } catch (err) {
        console.error("Error fetching history", err);
      }
    };
    fetchHistory();
  }, [sessionId]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const sendPrompt = (text: string) => {
    setInput(text);
    // Use a short timeout to let state update before submission
    setTimeout(() => {
      const form = document.getElementById("chat-form") as HTMLFormElement;
      if (form) form.requestSubmit();
    }, 50);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || isLoading) return;

    const userMessage: Message = { id: Date.now().toString(), role: "user", content: input };
    setMessages((prev) => [...prev, userMessage]);
    const currentInput = input;
    setInput("");
    setIsLoading(true);

    const assistantMessageId = (Date.now() + 1).toString();
    setMessages((prev) => [...prev, { id: assistantMessageId, role: "assistant", content: "" }]);

    try {
      const response = await fetch("/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: currentInput, session_id: sessionId }),
      });

      if (!response.body) throw new Error("No response body");
      const reader = response.body.getReader();
      const decoder = new TextDecoder();

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        const chunk = decoder.decode(value, { stream: true });
        
        setMessages((prev) => 
          prev.map((msg) => 
            msg.id === assistantMessageId 
              ? { ...msg, content: msg.content + chunk } 
              : msg
          )
        );
      }
    } catch (error) {
      console.error("Chat error:", error);
      setMessages((prev) => 
        prev.map((msg) => 
          msg.id === assistantMessageId 
            ? { ...msg, content: "ขออภัยครับ เกิดข้อผิดพลาดในการเชื่อมต่อระบบ" } 
            : msg
        )
      );
    } finally {
      setIsLoading(false);
    }
  };

  const quickPrompts = [
    { icon: "💼", text: "ทำงานประจำ อยากเรียน MBA เสาร์-อาทิตย์ ค่าเทอมไม่เกิน 1.5 แสน มีไหม?" },
    { icon: "📊", text: "จบไม่ตรงสาย อยากเรียน Data Science & AI นิด้า มีเงื่อนไขอะไรบ้าง?" },
    { icon: "🏛️", text: "ข้าราชการ เรียน MPA แนะนำ แผน ก (วิทยานิพนธ์) หรือ แผน ข (IS) ดีกว่ากัน?" },
    { icon: "📝", text: "เกณฑ์คะแนนสอบ NIDA TEAP และระเบียบเทียบโอนหน่วยกิตเป็นอย่างไร?" }
  ];

  return (
    <div className="h-full flex flex-col bg-white relative">
      {messages.length === 0 ? (
        // Empty State (Hero)
        <div className="flex-1 flex flex-col items-center justify-center px-4 max-w-4xl mx-auto w-full mt-10">
          <div className="text-center mb-12">
            <h1 className="text-4xl md:text-5xl font-bold mb-4 bg-clip-text text-transparent bg-gradient-to-r from-blue-600 to-purple-500 inline-flex items-center gap-3">
              <span className="text-blue-500">✨</span> สวัสดี คุณสนใจศึกษาที่ NIDA ไหม?
            </h1>
          </div>

          <div className="w-full max-w-3xl">
            <div className="flex items-center justify-center gap-2 text-sm text-yellow-600 font-medium mb-6">
              <Lightbulb size={16} />
              ตัวอย่างประเด็นที่สามารถสอบถามได้ทันที:
            </div>
            
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {quickPrompts.map((prompt, i) => (
                <button
                  key={i}
                  onClick={() => sendPrompt(prompt.text)}
                  className="flex items-center gap-3 p-4 bg-white border border-gray-200 rounded-xl hover:bg-gray-50 hover:border-gray-300 transition-all text-left shadow-sm"
                >
                  <span className="text-lg">{prompt.icon}</span>
                  <span className="text-sm text-gray-600">{prompt.text}</span>
                </button>
              ))}
            </div>
          </div>
        </div>
      ) : (
        // Chat History State
        <div className="flex-1 overflow-y-auto px-4 py-20 scroll-smooth">
          <div className="max-w-3xl mx-auto space-y-8">
            <AnimatePresence>
              {messages.map((m) => (
                <motion.div
                  key={m.id}
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  className={`flex gap-4 ${m.role === "user" ? "justify-end" : "justify-start"}`}
                >
                  {m.role === "assistant" && (
                    <div className="w-8 h-8 rounded-full bg-blue-100 flex items-center justify-center shrink-0 mt-1">
                      <Bot size={18} className="text-blue-700" />
                    </div>
                  )}
                  
                  <div className={`max-w-[85%] ${
                    m.role === "user" 
                      ? "bg-gray-100 text-gray-800 rounded-2xl px-5 py-3" 
                      : "text-gray-800 prose prose-p:leading-relaxed prose-blue"
                  }`}>
                    <ReactMarkdown remarkPlugins={[remarkGfm]}>
                      {m.content || (isLoading && m.role === "assistant" ? "..." : "")}
                    </ReactMarkdown>
                  </div>

                  {m.role === "user" && (
                    <div className="w-8 h-8 rounded-full bg-gray-200 flex items-center justify-center shrink-0 mt-1">
                      <User size={18} className="text-gray-500" />
                    </div>
                  )}
                </motion.div>
              ))}
            </AnimatePresence>
            <div ref={messagesEndRef} className="h-4" />
          </div>
        </div>
      )}

      {/* Input Form at Bottom */}
      <div className="w-full bg-gradient-to-t from-white via-white to-transparent pb-8 pt-10 px-4 mt-auto">
        <div className="max-w-3xl mx-auto relative">
          <form id="chat-form" onSubmit={handleSubmit} className="relative flex items-center shadow-lg rounded-full bg-white border border-gray-200">
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="ถาม NIDA"
              className="w-full bg-transparent pl-6 pr-14 py-4 text-gray-800 placeholder-gray-400 focus:outline-none rounded-full"
              disabled={isLoading || !sessionId}
            />
            <button
              type="submit"
              disabled={!input.trim() || isLoading || !sessionId}
              className="absolute right-2 p-2 bg-blue-500 hover:bg-blue-600 disabled:bg-gray-200 disabled:text-gray-400 text-white rounded-full transition-colors flex items-center justify-center"
            >
              {isLoading ? (
                <Sparkles className="w-5 h-5 animate-pulse" />
              ) : (
                <ArrowUp className="w-5 h-5" />
              )}
            </button>
          </form>
          <div className="text-center mt-3 text-xs text-gray-400">
            AI อาจให้ข้อมูลที่ไม่ถูกต้อง โปรดตรวจสอบข้อมูลอีกครั้งกับเว็บไซต์สถาบัน
          </div>
        </div>
      </div>
    </div>
  );
}
