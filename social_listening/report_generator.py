"""
social_listening/report_generator.py
Executive Report Generator for NIDA Enterprise AI & Social Listening Platform.
Generates printable, executive-ready HTML/PDF Briefing Documents and CSV summaries.
"""
from __future__ import annotations

import datetime
from typing import Any, Dict, List
import pandas as pd


def generate_executive_html_report(
    total_comments: int,
    sentiment_counts: Dict[str, int],
    intent_counts: Dict[str, int],
    swot_data: Dict[str, List[str]],
    anomalies: List[Dict[str, Any]],
    user_role: str = "Dean / Executive Board",
) -> str:
    """Generate a clean, high-contrast, printable Executive Briefing HTML Report with NIDA styling."""
    now_str = datetime.datetime.now().strftime("%d/%m/%Y %H:%M") + " น."
    pos_count = sentiment_counts.get("Positive", 0)
    neg_count = sentiment_counts.get("Negative", 0)
    neu_count = sentiment_counts.get("Neutral", 0)
    total = max(total_comments, 1)
    
    pos_pct = round((pos_count / total) * 100, 1)
    neg_pct = round((neg_count / total) * 100, 1)
    neu_pct = round((neu_count / total) * 100, 1)

    html = f"""<!DOCTYPE html>
<html lang="th">
<head>
    <meta charset="UTF-8">
    <title>NIDA Executive Intelligence Report - Social Listening & Admissions AI</title>
    <style>
        @page {{ size: A4; margin: 1.5cm; }}
        body {{
            font-family: 'Sarabun', 'Segoe UI', Tahoma, sans-serif;
            color: #0f172a;
            background: #ffffff;
            margin: 0;
            padding: 20px;
            line-height: 1.6;
        }}
        .header {{
            border-bottom: 3px solid #002b66;
            padding-bottom: 12px;
            margin-bottom: 24px;
            display: flex;
            justify-content: space-between;
            align-items: flex-end;
        }}
        .header h1 {{
            margin: 0;
            color: #002b66;
            font-size: 22px;
            font-weight: 800;
        }}
        .header .subtitle {{
            color: #475569;
            font-size: 13px;
            margin-top: 4px;
        }}
        .meta-box {{
            background: #f8fafc;
            border: 1px solid #e2e8f0;
            border-radius: 8px;
            padding: 12px 16px;
            margin-bottom: 24px;
            font-size: 13px;
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 12px;
        }}
        .kpi-grid {{
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 12px;
            margin-bottom: 24px;
        }}
        .kpi-card {{
            border: 1px solid #e2e8f0;
            border-radius: 8px;
            padding: 12px;
            text-align: center;
            background: #ffffff;
            box-shadow: 0 1px 3px rgba(0,0,0,0.05);
        }}
        .kpi-card .num {{
            font-size: 24px;
            font-weight: 800;
            margin-top: 4px;
        }}
        .kpi-card .label {{
            font-size: 12px;
            color: #64748b;
            font-weight: 600;
        }}
        .section-title {{
            font-size: 16px;
            font-weight: 700;
            color: #002b66;
            border-left: 4px solid #1d4ed8;
            padding-left: 8px;
            margin: 24px 0 12px 0;
        }}
        .swot-grid {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 14px;
            margin-bottom: 24px;
        }}
        .swot-box {{
            border-radius: 8px;
            padding: 14px;
            font-size: 13px;
        }}
        .swot-s {{ background: #ecfdf5; border: 1px solid #a7f3d0; }}
        .swot-w {{ background: #fef2f2; border: 1px solid #fecaca; }}
        .swot-o {{ background: #eff6ff; border: 1px solid #bfdbfe; }}
        .swot-t {{ background: #fffbeb; border: 1px solid #fde68a; }}
        .swot-box h4 {{ margin: 0 0 8px 0; font-size: 14px; }}
        .swot-box ul {{ margin: 0; padding-left: 18px; }}
        .swot-box li {{ margin-bottom: 4px; }}
        table {{
            width: 100%;
            border-collapse: collapse;
            font-size: 13px;
            margin-bottom: 20px;
        }}
        th, td {{
            border: 1px solid #e2e8f0;
            padding: 8px 12px;
            text-align: left;
        }}
        th {{
            background: #f1f5f9;
            color: #0f172a;
            font-weight: 700;
        }}
        .badge-red {{ background: #fee2e2; color: #991b1b; padding: 2px 8px; border-radius: 12px; font-size: 11px; font-weight: 600; }}
        .badge-yellow {{ background: #fef3c7; color: #92400e; padding: 2px 8px; border-radius: 12px; font-size: 11px; font-weight: 600; }}
        .badge-blue {{ background: #dbeafe; color: #1e40af; padding: 2px 8px; border-radius: 12px; font-size: 11px; font-weight: 600; }}
        .footer {{
            border-top: 1px solid #e2e8f0;
            margin-top: 30px;
            padding-top: 12px;
            font-size: 11px;
            color: #94a3b8;
            display: flex;
            justify-content: space-between;
        }}
        @media print {{
            body {{ padding: 0; }}
            .no-print {{ display: none; }}
        }}
    </style>
</head>
<body>
    <div class="header">
        <div>
            <h1>🏛️ NIDA Executive Intelligence Report</h1>
            <div class="subtitle">สถาบันบัณฑิตพัฒนบริหารศาสตร์ • ระบบวิเคราะห์เสียงสะท้อนโซเชียลและการตัดสินใจศึกษาต่อ ป.โท-เอก</div>
        </div>
        <div style="text-align: right; font-size: 12px; color: #64748b;">
            <strong>สถานะเอกสาร:</strong> ชั้นความลับภายใน (Confidential)<br>
            <strong>พิมพ์รายงานเมื่อ:</strong> {now_str}
        </div>
    </div>

    <div class="meta-box">
        <div><strong>ผู้จัดทำรายงาน:</strong> NIDA Enterprise AI Platform</div>
        <div><strong>สิทธิ์การเข้าถึง:</strong> {user_role}</div>
        <div><strong>แหล่งข้อมูล:</strong> Pantip, Facebook, YouTube, Dek-D, News (1,500+ records)</div>
    </div>

    <div class="kpi-grid">
        <div class="kpi-card">
            <div class="label">ความคิดเห็นทั้งหมดในคลัง</div>
            <div class="num" style="color: #1e40af;">{total_comments:,}</div>
        </div>
        <div class="kpi-card">
            <div class="label">กระแสเชิงบวก (Positive)</div>
            <div class="num" style="color: #059669;">{pos_pct}%</div>
        </div>
        <div class="kpi-card">
            <div class="label">กระแสเชิงลบ/ข้อกังวล (Negative)</div>
            <div class="num" style="color: #dc2626;">{neg_pct}%</div>
        </div>
        <div class="kpi-card">
            <div class="label">ความสนใจสมัครเรียน (Intent)</div>
            <div class="num" style="color: #7c3aed;">{intent_counts.get('interest_apply', 0):,}</div>
        </div>
    </div>

    <div class="section-title">📊 การวิเคราะห์ SWOT เชิงกลยุทธ์ของสถาบัน (Executive SWOT Analysis)</div>
    <div class="swot-grid">
        <div class="swot-box swot-s">
            <h4 style="color: #065f46;">💪 จุดแข็ง (Strengths)</h4>
            <ul>
                {''.join(f'<li>{s}</li>' for s in swot_data.get('strengths', []))}
            </ul>
        </div>
        <div class="swot-box swot-w">
            <h4 style="color: #991b1b;">⚠️ ข้อควรปรับปรุง (Weaknesses)</h4>
            <ul>
                {''.join(f'<li>{w}</li>' for w in swot_data.get('weaknesses', []))}
            </ul>
        </div>
        <div class="swot-box swot-o">
            <h4 style="color: #1e40af;">🚀 โอกาสทางยุทธศาสตร์ (Opportunities)</h4>
            <ul>
                {''.join(f'<li>{o}</li>' for o in swot_data.get('opportunities', []))}
            </ul>
        </div>
        <div class="swot-box swot-t">
            <h4 style="color: #92400e;">🛡️ ภาวะคุกคามและการแข่งขัน (Threats)</h4>
            <ul>
                {''.join(f'<li>{t}</li>' for t in swot_data.get('threats', []))}
            </ul>
        </div>
    </div>

    <div class="section-title">🚨 รายการสัญญาณเตือนและประเด็นที่ต้องจับตา (Anomaly & Early Warning Radar)</div>
    <table>
        <thead>
            <tr>
                <th style="width: 15%;">ระดับความเสี่ยง</th>
                <th style="width: 25%;">หมวดหมู่อุปสรรค</th>
                <th style="width: 60%;">ข้อสังเกตและข้อเสนอแนะเชิงนโยบาย</th>
            </tr>
        </thead>
        <tbody>
            {''.join(f'''<tr>
                <td><span class="badge-{'red' if a.get('severity')=='HIGH' else 'yellow' if a.get('severity')=='MEDIUM' else 'blue'}">{a.get('severity', 'NORMAL')}</span></td>
                <td><strong>{a.get('topic', '-')}</strong></td>
                <td>{a.get('insight', '-')}</td>
            </tr>''' for a in anomalies)}
        </tbody>
    </table>

    <div class="section-title">🎯 ข้อเสนอแนะเชิงยุทธศาสตร์สำหรับสภามหาวิทยาลัยและคณบดี (Strategic Action Items)</div>
    <div style="background:#f8fafc; border: 1px solid #e2e8f0; border-radius:8px; padding: 14px; font-size:13px;">
        <ol style="margin: 0; padding-left: 20px;">
            <li style="margin-bottom: 6px;"><strong>ปรับโครงสร้างโปรโมชันและการผ่อนชำระ:</strong> ควรทำการตลาดประชาสัมพันธ์ "แผนผ่อนชำระค่าเทอม 0% 3 งวด" และ "ทุนการศึกษาสำหรับคนทำงาน" ให้ชัดเจนในสื่อออนไลน์ เพื่อลด Pain Point ด้านงบประมาณ</li>
            <li style="margin-bottom: 6px;"><strong>ขยายศูนย์สอบ NIDA TEAP ออนไลน์:</strong> เพิ่มรอบสอบภาษาอังกฤษแบบ Online Remote เพื่ออำนวยความสะดวกแก่ผู้สมัครต่างจังหวัดและคนทำงานประจำ</li>
            <li style="margin-bottom: 6px;"><strong>ชูจุดเด่นวิชาปรับพื้นฐาน (Foundation Courses):</strong> สื่อสารอย่างตรงจุดว่า "จบ ป.ตรี ไม่ตรงสาย ก็เรียน ป.โท Data Science หรือ MBA ที่นิด้าได้" เพื่อขยายฐานผู้สมัครให้กว้างขึ้น</li>
            <li><strong>เพิ่มหลักสูตร Hybrid / Micro-credentials:</strong> พัฒนารายวิชาเก็บสะสมหน่วยกิต (Credit Bank) เพื่อตอบรับเทรนด์การเรียนรู้ตลอดชีวิต (Lifelong Learning)</li>
        </ol>
    </div>

    <div class="footer">
        <div>สถาบันบัณฑิตพัฒนบริหารศาสตร์ (NIDA) • ถนนเสรีไทย คลองจั่น บางกะปิ กรุงเทพฯ 10240</div>
        <div>หน้า 1 จาก 1 • ระบบ Enterprise AI & Social Listening Platform</div>
    </div>
</body>
</html>
"""
    return html


def generate_executive_csv_summary(
    sentiment_counts: Dict[str, int],
    intent_counts: Dict[str, int],
    swot_data: Dict[str, List[str]],
) -> str:
    """Generate CSV text summary of key executive metrics for Excel import."""
    rows = []
    rows.append(["Category", "Metric", "Value"])
    for k, v in sentiment_counts.items():
        rows.append(["Sentiment Distribution", k, v])
    for k, v in intent_counts.items():
        rows.append(["Student Intent", k, v])
    for k, items in swot_data.items():
        for idx, item in enumerate(items, 1):
            rows.append([f"SWOT - {k.upper()}", f"Item {idx}", item])
    
    df = pd.DataFrame(rows[1:], columns=rows[0])
    return df.to_csv(index=False, encoding="utf-8-sig")
