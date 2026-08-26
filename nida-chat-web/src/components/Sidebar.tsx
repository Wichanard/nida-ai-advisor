"use client";

import React, { useState } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { MessageSquare, Book, Briefcase, Edit, Search, Video, Archive, ChevronLeft, ChevronRight } from "lucide-react";

export default function Sidebar() {
  const pathname = usePathname();
  const router = useRouter();
  const [collapsed, setCollapsed] = useState(false);

  const navItems = [
    { name: "NIDACHAT", path: "/", icon: <MessageSquare size={18} /> },
    { name: "สารบบหลักสูตร", path: "/courses", icon: <Book size={18} /> },
    { name: "สำหรับผู้บริหาร", path: "/admin", icon: <Briefcase size={18} /> },
  ];

  const subNavItems = [
    { name: "แชทใหม่", icon: <Edit size={18} />, action: "new_chat" },
    { name: "ค้นหาแชท", icon: <Search size={18} />, path: "/archive?search=true" },
    { name: "วิดีโอ", icon: <Video size={18} /> },
    { name: "คลัง", icon: <Archive size={18} />, path: "/archive" },
  ];

  const handleNewChat = (e?: React.MouseEvent) => {
    if (e) e.preventDefault();
    localStorage.removeItem("nida_session_id");
    if (pathname === "/") {
      window.location.reload();
    } else {
      router.push("/");
    }
  };



  return (
    <div className={`relative flex flex-col h-full bg-white border-r border-gray-200 transition-all duration-300 ${collapsed ? "w-16" : "w-64"} shrink-0`}>
      {/* Toggle Button */}
      <button 
        onClick={() => setCollapsed(!collapsed)}
        className="absolute -right-3 top-6 bg-white border border-gray-200 rounded-full p-1 shadow-sm text-gray-400 hover:text-gray-600 z-50"
      >
        {collapsed ? <ChevronRight size={14} /> : <ChevronLeft size={14} />}
      </button>

      {/* Logo Area */}
      <div className="flex flex-col items-center py-6 px-4">
        {!collapsed ? (
          <div className="text-center">
            <h1 className="text-[#003B70] font-bold text-xl tracking-wider">NIDA</h1>
            <p className="text-xs text-gray-500 mt-1">AI & Social Listening</p>
          </div>
        ) : (
          <div className="text-[#003B70] font-bold text-xl">N</div>
        )}
      </div>

      <div className="flex-1 overflow-y-auto overflow-x-hidden no-scrollbar">
        {/* Navigation */}
        <div className="px-3 mb-6">
          {!collapsed && <div className="text-[10px] font-semibold text-gray-400 mb-2 px-2 uppercase tracking-wider">NAVIGATION</div>}
          <div className="space-y-1">
            {navItems.map((item) => {
              const isActive = pathname === item.path || (item.path !== "/" && pathname.startsWith(item.path));
              if (item.name === "NIDACHAT") {
                return (
                  <Link key={item.name} href={item.path}>
                    <div className={`flex items-center gap-3 px-3 py-2.5 rounded-lg transition-colors cursor-pointer ${
                      isActive ? "bg-white border border-gray-200 shadow-sm text-[#003B70] font-medium" : "text-gray-600 hover:bg-gray-50 hover:text-[#003B70]"
                    }`}>
                      {item.icon}
                      {!collapsed && <span className="text-sm">{item.name}</span>}
                    </div>
                  </Link>
                );
              }
              return (
                <Link key={item.name} href={item.path}>
                  <div className={`flex items-center gap-3 px-3 py-2.5 rounded-lg transition-colors cursor-pointer ${
                    isActive ? "bg-white border border-gray-200 shadow-sm text-[#003B70] font-medium" : "text-gray-600 hover:bg-gray-50 hover:text-[#003B70]"
                  }`}>
                    {item.icon}
                    {!collapsed && <span className="text-sm">{item.name}</span>}
                  </div>
                </Link>
              );
            })}
          </div>
        </div>

        <div className="px-6 mb-6">
          <div className="h-px bg-gray-100 w-full"></div>
        </div>

        {/* Sub Navigation */}
        <div className="px-3 mb-6">
          <div className="space-y-1">
            {subNavItems.map((item) => {
              const isActive = pathname === item.path;
              const content = (
                <div key={item.name} onClick={item.action === "new_chat" ? handleNewChat : undefined} className={`flex items-center gap-3 px-3 py-2 rounded-lg transition-colors cursor-pointer ${isActive ? "bg-white border border-gray-200 shadow-sm text-[#003B70] font-medium" : "text-gray-600 hover:bg-gray-50 hover:text-[#003B70]"}`}>
                  {item.icon}
                  {!collapsed && <span className="text-sm">{item.name}</span>}
                </div>
              );
              
              if (item.path) {
                return <Link key={item.name} href={item.path}>{content}</Link>;
              }
              return content;
            })}
          </div>
        </div>

      </div>
    </div>
  );
}
