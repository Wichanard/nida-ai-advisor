"use client";

import React, { useState, useEffect } from "react";
import { Search, ChevronRight } from "lucide-react";

type Course = {
  faculty: string;
  department: string;
  program_name: string;
  degree_level: string;
  type: string;
  total_fee: string; // From tuition, could be string like "70,000"
  study_time: string;
  application_link: string;
};

export default function CoursesPage() {
  const [courses, setCourses] = useState<Course[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  // Search and Filter States for Directory
  const [searchQuery, setSearchQuery] = useState("");
  const [degreeFilter, setDegreeFilter] = useState("ทั้งหมด");
  const [facultyFilter, setFacultyFilter] = useState("ทั้งหมด");
  const [timeFilter, setTimeFilter] = useState("ทั้งหมด");

  // Comparison States
  const [compare1, setCompare1] = useState<string>("");
  const [compare2, setCompare2] = useState<string>("");
  const [compare3, setCompare3] = useState<string>("");

  useEffect(() => {
    const fetchCourses = async () => {
      try {
        const res = await fetch("/api/courses");
        if (res.ok) {
          const data = await res.json();
          // Flatten the hierarchical data
          let flatCourses: Course[] = [];
          if (Array.isArray(data)) {
            data.forEach((fac: any) => {
              if (fac.departments) {
                fac.departments.forEach((dept: any) => {
                  if (dept.programs) {
                    dept.programs.forEach((prog: any) => {
                      let tuition = "ไม่ระบุ";
                      let studyMode = "ไม่ระบุ";
                      if (prog.semesters && prog.semesters.length > 0) {
                        tuition = prog.semesters[0].tuition || "ไม่ระบุ";
                        studyMode = prog.semesters.map((s: any) => s.study_mode).join(", ") || "ไม่ระบุ";
                      }

                      flatCourses.push({
                        faculty: fac.faculty || "",
                        department: dept.department || "",
                        program_name: prog.program || "",
                        degree_level: prog.degree || "",
                        type: prog.keywords ? prog.keywords.join(", ") : "",
                        total_fee: tuition,
                        study_time: studyMode,
                        application_link: prog.application_link || "#",
                      });
                    });
                  }
                });
              }
            });
          }
          setCourses(flatCourses);
        }
      } catch (err) {
        console.error("Failed to load courses:", err);
      } finally {
        setIsLoading(false);
      }
    };
    fetchCourses();
  }, []);

  // Filter options for dropdowns
  const uniqueFaculties = ["ทั้งหมด", ...Array.from(new Set(courses.map(c => c.faculty)))].filter(Boolean);
  
  // Apply filters
  const filteredCourses = courses.filter(c => {
    const matchesSearch = 
      (c.program_name && c.program_name.toLowerCase().includes(searchQuery.toLowerCase())) ||
      (c.faculty && c.faculty.toLowerCase().includes(searchQuery.toLowerCase())) ||
      (c.department && c.department.toLowerCase().includes(searchQuery.toLowerCase()));
    
    const matchesDegree = degreeFilter === "ทั้งหมด" || (c.degree_level && c.degree_level.includes(degreeFilter));
    const matchesFaculty = facultyFilter === "ทั้งหมด" || c.faculty === facultyFilter;
    const matchesTime = timeFilter === "ทั้งหมด" || (c.study_time && c.study_time.includes(timeFilter));

    return matchesSearch && matchesDegree && matchesFaculty && matchesTime;
  });

  const getCourseDetails = (programName: string) => {
    return courses.find(c => c.program_name === programName);
  };

  const formatCurrency = (amount: string) => {
    if (amount === "ไม่ระบุ") return amount;
    // If it's already a formatted string like "70,000", just add ฿
    return `฿${amount}`;
  };

  return (
    <div className="min-h-screen bg-slate-50 p-6 md:p-10 font-sans">
      <div className="max-w-7xl mx-auto space-y-10">
        
        {/* Header */}
        <div className="bg-white p-8 rounded-2xl shadow-sm border border-gray-100">
          <h1 className="text-3xl font-bold text-[#003B70] mb-2 flex items-center gap-3">
            <span className="text-4xl">🏛️</span> สารบบและเปรียบเทียบ {courses.length} หลักสูตรนิด้า
          </h1>
          <p className="text-gray-500 text-lg">
            ฐานข้อมูลหลักสูตรทางการระดับปริญญาโท-เอก สถาบันบัณฑิตพัฒนบริหารศาสตร์ ครบทั้ง 14 คณะ/วิทยาลัย
          </p>
        </div>

        {/* Comparison Section */}
        <div className="bg-white p-8 rounded-2xl shadow-sm border border-gray-100">
          <h2 className="text-xl font-bold text-gray-800 mb-6 flex items-center gap-2">
            <span>⚖️</span> เปรียบเทียบหลักสูตรแบบเคียงข้าง (Side-by-Side Comparison)
          </h2>
          
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-6">
            <select 
              value={compare1} 
              onChange={(e) => setCompare1(e.target.value)}
              className="w-full p-3 border border-gray-300 rounded-xl bg-gray-50 focus:outline-none focus:ring-2 focus:ring-blue-500 text-sm"
            >
              <option value="">-- เลือกหลักสูตรที่ 1 --</option>
              {courses.map((c, i) => <option key={i} value={c.program_name}>{c.program_name}</option>)}
            </select>
            <select 
              value={compare2} 
              onChange={(e) => setCompare2(e.target.value)}
              className="w-full p-3 border border-gray-300 rounded-xl bg-gray-50 focus:outline-none focus:ring-2 focus:ring-blue-500 text-sm"
            >
              <option value="">-- เลือกหลักสูตรที่ 2 --</option>
              {courses.map((c, i) => <option key={i} value={c.program_name}>{c.program_name}</option>)}
            </select>
            <select 
              value={compare3} 
              onChange={(e) => setCompare3(e.target.value)}
              className="w-full p-3 border border-gray-300 rounded-xl bg-gray-50 focus:outline-none focus:ring-2 focus:ring-blue-500 text-sm"
            >
              <option value="">-- เลือกหลักสูตรที่ 3 --</option>
              {courses.map((c, i) => <option key={i} value={c.program_name}>{c.program_name}</option>)}
            </select>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            {[compare1, compare2, compare3].map((comp, idx) => {
              const details = getCourseDetails(comp);
              if (!details) return (
                <div key={idx} className="border-2 border-dashed border-gray-200 rounded-2xl p-8 flex items-center justify-center text-gray-400 bg-gray-50/50">
                  <p>เลือกหลักสูตรเพื่อเปรียบเทียบ</p>
                </div>
              );

              return (
                <div key={idx} className="bg-white border border-gray-200 rounded-2xl overflow-hidden shadow-sm hover:shadow-md transition-shadow">
                  <div className="bg-[#003B70] p-4 text-white">
                    <h3 className="font-bold text-lg leading-tight line-clamp-2">{details.program_name}</h3>
                    <p className="text-blue-200 text-xs mt-1">{details.degree_level}</p>
                  </div>
                  <div className="p-5 space-y-4">
                    <div>
                      <p className="text-xs text-gray-500 uppercase font-semibold tracking-wider">คณะ/วิทยาลัย</p>
                      <p className="text-sm font-medium text-gray-800 mt-1">{details.faculty}</p>
                    </div>
                    <hr className="border-gray-100" />
                    <div>
                      <p className="text-xs text-gray-500 uppercase font-semibold tracking-wider">ค่าเทอม (เริ่มต้นประมาณ)</p>
                      <p className="text-lg font-bold text-green-600 mt-1">{formatCurrency(details.total_fee)}</p>
                    </div>
                    <hr className="border-gray-100" />
                    <div>
                      <p className="text-xs text-gray-500 uppercase font-semibold tracking-wider">รูปแบบเวลาเรียน</p>
                      <div className="mt-1 flex flex-wrap gap-2">
                        {details.study_time.split(',').map((mode, i) => (
                          <span key={i} className="inline-block px-2.5 py-1 bg-blue-50 text-blue-700 rounded-md text-xs font-medium">
                            {mode.trim()}
                          </span>
                        ))}
                      </div>
                    </div>
                    <hr className="border-gray-100" />
                    <div>
                      <p className="text-xs text-gray-500 uppercase font-semibold tracking-wider">ประเภท/จุดเด่น</p>
                      <p className="text-sm text-gray-800 mt-1">{details.type}</p>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* Directory Section */}
        <div className="bg-white p-8 rounded-2xl shadow-sm border border-gray-100">
          <h2 className="text-xl font-bold text-gray-800 mb-6 flex items-center gap-2">
            <span>📋</span> รายการหลักสูตรทั้งหมด {filteredCourses.length} สาขาวิชา (Filterable Directory)
          </h2>

          <div className="flex flex-col md:flex-row gap-4 mb-6">
            <select 
              className="p-3 border border-gray-300 rounded-xl bg-white focus:outline-none focus:ring-2 focus:ring-[#003B70] text-sm md:w-48"
              value={degreeFilter}
              onChange={(e) => setDegreeFilter(e.target.value)}
            >
              <option value="ทั้งหมด">ระดับการศึกษา: ทั้งหมด</option>
              <option value="ป.โท">ปริญญาโท</option>
              <option value="ป.เอก">ปริญญาเอก</option>
            </select>
            
            <select 
              className="p-3 border border-gray-300 rounded-xl bg-white focus:outline-none focus:ring-2 focus:ring-[#003B70] text-sm md:w-64"
              value={facultyFilter}
              onChange={(e) => setFacultyFilter(e.target.value)}
            >
              {uniqueFaculties.map((f, i) => (
                <option key={i} value={f}>
                  {f === "ทั้งหมด" ? "คณะที่ต้องการเน้น: ทั้งหมด" : f}
                </option>
              ))}
            </select>

            <select 
              className="p-3 border border-gray-300 rounded-xl bg-white focus:outline-none focus:ring-2 focus:ring-[#003B70] text-sm md:w-48"
              value={timeFilter}
              onChange={(e) => setTimeFilter(e.target.value)}
            >
              <option value="ทั้งหมด">เวลาเรียน: ทั้งหมด</option>
              <option value="ภาคปกติ">ภาคปกติ</option>
              <option value="ภาคค่ำ">ภาคค่ำ</option>
              <option value="เสาร์-อาทิตย์">เสาร์-อาทิตย์</option>
            </select>

            <div className="relative flex-1">
              <Search className="absolute left-3 top-3.5 text-gray-400 w-4 h-4" />
              <input 
                type="text" 
                placeholder="ค้นหาหลักสูตรตามชื่อ, คณะ, หรือสายอาชีพ..."
                className="w-full p-3 pl-9 border border-gray-300 rounded-xl focus:outline-none focus:ring-2 focus:ring-[#003B70] text-sm"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
              />
            </div>
          </div>

          <div className="overflow-x-auto rounded-xl border border-gray-200">
            <table className="w-full text-left text-sm whitespace-nowrap">
              <thead className="bg-gray-50 border-b border-gray-200 text-gray-500 font-medium">
                <tr>
                  <th className="px-4 py-3">หลักสูตร</th>
                  <th className="px-4 py-3">ระดับ</th>
                  <th className="px-4 py-3">คณะ/วิทยาลัย</th>
                  <th className="px-4 py-3">สาขาวิชา</th>
                  <th className="px-4 py-3">ค่าเทอมประมาณ</th>
                  <th className="px-4 py-3">เวลาเรียน</th>
                  <th className="px-4 py-3">ลิงก์สมัครเรียน</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100 bg-white">
                {isLoading ? (
                  <tr>
                    <td colSpan={7} className="text-center py-8 text-gray-500">กำลังโหลดข้อมูล...</td>
                  </tr>
                ) : filteredCourses.length === 0 ? (
                  <tr>
                    <td colSpan={7} className="text-center py-8 text-gray-500">ไม่พบหลักสูตรที่ค้นหา</td>
                  </tr>
                ) : (
                  filteredCourses.map((c, i) => (
                    <tr key={i} className="hover:bg-gray-50 transition-colors">
                      <td className="px-4 py-3 font-medium text-[#003B70] whitespace-normal min-w-[250px]">{c.program_name}</td>
                      <td className="px-4 py-3">
                        <span className={`px-2 py-1 rounded-md text-xs font-medium ${
                          c.degree_level.includes('เอก') ? 'bg-purple-100 text-purple-700' : 'bg-blue-100 text-blue-700'
                        }`}>
                          {c.degree_level}
                        </span>
                      </td>
                      <td className="px-4 py-3 whitespace-normal min-w-[200px]">{c.faculty}</td>
                      <td className="px-4 py-3 text-gray-500">{c.department}</td>
                      <td className="px-4 py-3 font-semibold text-green-600">{formatCurrency(c.total_fee)}</td>
                      <td className="px-4 py-3 text-gray-600">{c.study_time}</td>
                      <td className="px-4 py-3">
                        <a href={c.application_link} target="_blank" rel="noreferrer" className="inline-flex items-center justify-center p-1.5 bg-gray-100 hover:bg-gray-200 rounded-md text-gray-600 transition-colors">
                          <ChevronRight size={16} />
                        </a>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  );
}
