"use client";

import React, { useState } from "react";
import { Lock, Shield, KeyRound, ArrowRight } from "lucide-react";

export default function AdminPortal() {
  const [authMethod, setAuthMethod] = useState<"sso" | "pin">("sso");
  
  return (
    <div className="min-h-screen bg-slate-50 flex flex-col items-center justify-center p-6 font-sans">
      <div className="w-full max-w-xl bg-white rounded-3xl shadow-sm border border-gray-100 overflow-hidden">
        
        {/* Header */}
        <div className="p-8 pb-6 text-center border-b border-gray-100">
          <div className="w-16 h-16 bg-blue-50 rounded-2xl flex items-center justify-center mx-auto mb-4">
            <Lock className="w-8 h-8 text-[#003B70]" />
          </div>
          <h1 className="text-2xl font-bold text-[#003B70] mb-2">
            🔒 เข้าสู่ระบบ NIDA Executive & Staff Portal
          </h1>
          <p className="text-gray-500 text-sm leading-relaxed max-w-md mx-auto">
            ระบบนี้สงวนสิทธิ์เฉพาะอาจารย์ เจ้าหน้าที่ และผู้บริหารสถาบันบัณฑิตพัฒนบริหารศาสตร์ (NIDA) เท่านั้น
          </p>
        </div>

        {/* Body */}
        <div className="p-8 space-y-6">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div 
              onClick={() => setAuthMethod("sso")}
              className={`p-4 rounded-2xl border-2 cursor-pointer transition-all ${
                authMethod === "sso" 
                  ? "border-[#003B70] bg-blue-50/50" 
                  : "border-gray-100 hover:border-gray-200"
              }`}
            >
              <div className="flex items-center gap-3 mb-2">
                <div className={`p-2 rounded-lg ${authMethod === "sso" ? "bg-[#003B70] text-white" : "bg-gray-100 text-gray-500"}`}>
                  <Shield size={18} />
                </div>
                <div className="font-semibold text-sm text-gray-800">NIDA SSO</div>
              </div>
              <p className="text-xs text-gray-500 ml-11">NIDA Academic Single Sign-On (@nida.ac.th)</p>
            </div>

            <div 
              onClick={() => setAuthMethod("pin")}
              className={`p-4 rounded-2xl border-2 cursor-pointer transition-all ${
                authMethod === "pin" 
                  ? "border-[#003B70] bg-blue-50/50" 
                  : "border-gray-100 hover:border-gray-200"
              }`}
            >
              <div className="flex items-center gap-3 mb-2">
                <div className={`p-2 rounded-lg ${authMethod === "pin" ? "bg-[#003B70] text-white" : "bg-gray-100 text-gray-500"}`}>
                  <KeyRound size={18} />
                </div>
                <div className="font-semibold text-sm text-gray-800">Master PIN</div>
              </div>
              <p className="text-xs text-gray-500 ml-11">Master Passcode PIN (Direct Key)</p>
            </div>
          </div>

          <div className="space-y-3 pt-2">
            <label className="block text-sm font-medium text-gray-700">
              เลือกบัญชีผู้บริหารหรือกรอกอีเมลสถาบัน:
            </label>
            <select className="w-full p-4 border border-gray-300 rounded-xl bg-white focus:outline-none focus:ring-2 focus:ring-[#003B70] text-gray-800">
              <option value="">-- เลือกบัญชี --</option>
              <option value="admin1">admin@nida.ac.th (ผู้ดูแลระบบ)</option>
              <option value="exec1">executive@nida.ac.th (ผู้บริหาร)</option>
              <option value="staff1">staff@nida.ac.th (เจ้าหน้าที่)</option>
            </select>
          </div>

          <button className="w-full py-4 px-6 bg-[#003B70] hover:bg-[#002a52] text-white rounded-xl font-bold text-lg shadow-md hover:shadow-lg transition-all flex items-center justify-center gap-2 mt-4">
            🚀 ยืนยันตัวตนผ่าน NIDA SSO
            <ArrowRight size={20} />
          </button>
        </div>
      </div>
      
      <div className="mt-8 text-center text-xs text-gray-400">
        <p>หากพบปัญหาในการเข้าสู่ระบบ กรุณาติดต่อสำนักเทคโนโลยีสารสนเทศ (IT Center)</p>
        <p className="mt-1">© 2026 National Institute of Development Administration</p>
      </div>
    </div>
  );
}
