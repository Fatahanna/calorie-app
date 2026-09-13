import streamlit as st
import sqlite3
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, date, timedelta
from PIL import Image
import json
import base64
import os

# -------------------------------------------------------------
# 1. ตั้งค่าเป้าหมายตามโปรไฟล์ผู้ใช้
# -------------------------------------------------------------
DAILY_GOALS = {
    "calories": 1850,
    "protein": 135,
    "carbs": 205,
    "fat": 52
}

# -------------------------------------------------------------
# 2. การจัดการฐานข้อมูล (SQLite)
# -------------------------------------------------------------
def init_db():
    conn = sqlite3.connect("calorie_tracker.db")
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS meals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            meal_name TEXT NOT NULL,
            calories INTEGER NOT NULL,
            protein REAL NOT NULL,
            carbs REAL NOT NULL,
            fat REAL NOT NULL,
            logged_date DATE NOT NULL,
            logged_time TEXT NOT NULL
        )
    ''')
    conn.commit()
    conn.close()

def insert_meal(name, cal, pro, carb, fat, log_date=None):
    conn = sqlite3.connect("calorie_tracker.db")
    c = conn.cursor()
    now = datetime.now()
    meal_date = log_date if log_date else now.strftime("%Y-%m-%d")
    meal_time = now.strftime("%H:%M")
    c.execute('''
        INSERT INTO meals (meal_name, calories, protein, carbs, fat, logged_date, logged_time)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', (name, cal, pro, carb, fat, meal_date, meal_time))
    conn.commit()
    conn.close()

def get_meals_by_date(selected_date):
    conn = sqlite3.connect("calorie_tracker.db")
    df = pd.read_sql_query(
        "SELECT * FROM meals WHERE logged_date = ?", 
        conn, 
        params=(str(selected_date),)
    )
    conn.close()
    return df

def get_meals_date_range(start_date, end_date):
    conn = sqlite3.connect("calorie_tracker.db")
    df = pd.read_sql_query(
        "SELECT * FROM meals WHERE logged_date BETWEEN ? AND ? ORDER BY logged_date ASC", 
        conn, 
        params=(str(start_date), str(end_date))
    )
    conn.close()
    return df

# -------------------------------------------------------------
# 3. AI Food Vision Recognition
# -------------------------------------------------------------
def analyze_food_image(image: Image.Image, api_key: str = None):
    """วิเคราะห์ภาพอาหารด้วย AI (หากไม่มี API Key จะคำนวณ Mock ให้ทันที)"""
    if not api_key:
        # Fallback Mock ข้อมูลตัวอย่างเมื่อยังไม่ได้ใส่ Key
        return {
            "name": "ข้าวกะเพราอกไก่ไข่ดาว (Mock AI)",
            "calories": 520,
            "protein": 38.0,
            "carbs": 55.0,
            "fat": 16.0
        }
    
    try:
        from google import genai
        client = genai.Client(api_key=api_key)
        prompt = """
        วิเคราะห์ภาพอาหารนี้ ระบุชื่ออาหาร พร้อมประมาณการพลังงานและสารอาหาร (แคลอรี, โปรตีน, คาร์บ, ไขมัน)
        ตอบกลับในรูปแบบ JSON เท่านั้น โดยมีคีย์ดังนี้:
        {
          "name": "ชื่ออาหารภาษาไทย",
          "calories": ตัวเลขจำนวนเต็ม,
          "protein": ตัวเลขทศนิยม,
          "carbs": ตัวเลขทศนิยม,
          "fat": ตัวเลขทศนิยม
        }
        """
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=[prompt, image]
        )
        clean_json = response.text.replace("```json", "").replace("```", "").strip()
        data = json.loads(clean_json)
        return data
    except Exception as e:
        st.error(f"เกิดข้อผิดพลาดในการเชื่อมต่อ AI: {e}")
        return {
            "name": "อาหารจานสแกน",
            "calories": 450,
            "protein": 25.0,
            "carbs": 50.0,
            "fat": 15.0
        }

# -------------------------------------------------------------
# 4. Streamlit UI Layout
# -------------------------------------------------------------
st.set_page_config(page_title="AI Calorie Tracker", page_icon="🥗", layout="wide")
init_db()

st.title("🥗 AI Calorie Tracker & Diet Dashboard")
st.caption(f"เป้าหมายลดไขมันส่วนบุคคล: **{DAILY_GOALS['calories']} kcal/วัน** | โปรตีน {DAILY_GOALS['protein']}g | คาร์บ {DAILY_GOALS['carbs']}g | ไขมัน {DAILY_GOALS['fat']}g")

tabs = st.tabs(["📸 สแกนและบันทึกอาหาร", "📅 สรุปผลรายวัน", "📊 สรุปผลรายสัปดาห์"])

# -------------------------------------------------------------
# TAB 1: อัปโหลดรูปภาพ / สแกนอาหาร
# -------------------------------------------------------------
with tabs[0]:
    st.subheader("บันทึกมื้ออาหารด้วยรูปถ่าย")
    
    col_input, col_preview = st.columns([1, 1])
    
    with col_input:
        api_key_input = st.text_input("Gemini API Key (เว้นว่างไว้เพื่อทดลองใช้ Mock ได้):", type="password")
        uploaded_file = st.file_uploader("เลือกรูปภาพมื้ออาหาร หรือถ่ายรูป", type=["jpg", "jpeg", "png"])
        
        if uploaded_file is not None:
            image = Image.open(uploaded_file)
            st.image(image, caption="ภาพมื้ออาหารของคุณ", use_container_width=True)
            
            if st.button("🔍 วิเคราะห์แคลอรีจากภาพด้วย AI", type="primary"):
                with st.spinner("กำลังวิเคราะห์สารอาหาร..."):
                    result = analyze_food_image(image, api_key=api_key_input)
                    st.session_state['detected_food'] = result
                    st.success("วิเคราะห์สำเร็จ! ตรวจสอบหรือแก้ไขข้อมูลทางด้านขวา")

    with col_preview:
        st.subheader("ยืนยันและบันทึกข้อมูล")
        if 'detected_food' in st.session_state:
            res = st.session_state['detected_food']
            with st.form("confirm_meal_form"):
                f_name = st.text_input("ชื่อเมนู", value=res.get("name", ""))
                f_cal = st.number_input("แคลอรีรวม (kcal)", value=int(res.get("calories", 0)), step=10)
                c1, c2, c3 = st.columns(3)
                f_pro = c1.number_input("โปรตีน (g)", value=float(res.get("protein", 0)), step=1.0)
                f_carb = c2.number_input("คาร์บ (g)", value=float(res.get("carbs", 0)), step=1.0)
                f_fat = c3.number_input("ไขมัน (g)", value=float(res.get("fat", 0)), step=1.0)
                f_date = st.date_input("วันที่บันทึก", value=date.today())
                
                submit_button = st.form_submit_button("💾 บันทึกลงไดอารี่")
                if submit_button:
                    insert_meal(f_name, f_cal, f_pro, f_carb, f_fat, f_date)
                    st.success(f"บันทึกเมนู '{f_name}' เรียบร้อยแล้ว!")
                    del st.session_state['detected_food']
                    st.rerun()
        else:
            st.info("💡 อัปโหลดรูปภาพทางซ้ายและกดปุ่มวิเคราะห์ ระบบจะแสดงข้อมูลสารอาหารให้คุณตรวจสอบก่อนบันทึก")

# -------------------------------------------------------------
# TAB 2: สรุปผลรายวัน (Daily Report)
# -------------------------------------------------------------
with tabs[1]:
    col_d1, col_d2 = st.columns([1, 3])
    with col_d1:
        target_date = st.date_input("เลือกวันที่ต้องการดูผล", value=date.today())
    
    daily_df = get_meals_by_date(target_date)
    
    total_cal = daily_df['calories'].sum() if not daily_df.empty else 0
    total_pro = daily_df['protein'].sum() if not daily_df.empty else 0
    total_carb = daily_df['carbs'].sum() if not daily_df.empty else 0
    total_fat = daily_df['fat'].sum() if not daily_df.empty else 0
    remaining_cal = DAILY_GOALS['calories'] - total_cal
    
    # แสดงตัวเลขการวัดผล
    m1, m2, m3, m4, m5 = st.columns(5)
    m1.metric("ทานไปแล้ว", f"{total_cal:,} kcal")
    m2.metric("เหลือทานได้อีก", f"{remaining_cal:,} kcal", delta=remaining_cal)
    m3.metric("โปรตีน", f"{total_pro:.1f} / {DAILY_GOALS['protein']} g")
    m4.metric("คาร์โบไฮเดรต", f"{total_carb:.1f} / {DAILY_GOALS['carbs']} g")
    m5.metric("ไขมัน", f"{total_fat:.1f} / {DAILY_GOALS['fat']} g")
    
    # กราฟ Donut สัดส่วนสารอาหาร
    if not daily_df.empty:
        col_chart, col_table = st.columns([1, 1])
        with col_chart:
            fig_pie = px.pie(
                values=[total_pro * 4, total_carb * 4, total_fat * 9],
                names=['โปรตีน (kcal)', 'คาร์บ (kcal)', 'ไขมัน (kcal)'],
                title="สัดส่วนพลังงานจากสารอาหารหลักวันนี้",
                color_discrete_sequence=['#3b82f6', '#10b981', '#f59e0b'],
                hole=0.45
            )
            st.plotly_chart(fig_pie, use_container_width=True)
            
        with col_table:
            st.write("📋 **รายการอาหารที่บันทึกวันนี้**")
            st.dataframe(
                daily_df[['logged_time', 'meal_name', 'calories', 'protein', 'carbs', 'fat']], 
                hide_index=True,
                use_container_width=True
            )
    else:
        st.warning("ยังไม่มีข้อมูลมื้ออาหารสำหรับวันนี้")

# -------------------------------------------------------------
# TAB 3: สรุปผลรายสัปดาห์ (Weekly Report)
# -------------------------------------------------------------
with tabs[2]:
    st.subheader("รายงานสรุปรายสัปดาห์ (7 วันย้อนหลัง)")
    today = date.today()
    start_week = today - timedelta(days=6)
    
    week_df = get_meals_date_range(start_week, today)
    
    if not week_df.empty:
        daily_summary = week_df.groupby('logged_date').agg({
            'calories': 'sum',
            'protein': 'sum',
            'carbs': 'sum',
            'fat': 'sum'
        }).reset_index()
        
        avg_cal = daily_summary['calories'].mean()
        
        w1, w2 = st.columns(2)
        w1.metric("แคลอรีเฉลี่ยต่อวัน (7 วัน)", f"{avg_cal:.0f} kcal", f"{avg_cal - DAILY_GOALS['calories']:.0f} จากเป้าหมาย")
        w2.metric("จำนวนวันที่บันทึก", f"{len(daily_summary)} / 7 วัน")
        
        fig_week = px.bar(
            daily_summary, 
            x='logged_date', 
            y='calories', 
            labels={'logged_date': 'วันที่', 'calories': 'แคลอรีที่รับประทาน (kcal)'},
            title="แคลอรีรวมแต่ละวัน เทียบกับเป้าหมาย",
            text='calories'
        )
        fig_week.add_hline(
            y=DAILY_GOALS['calories'], 
            line_dash="dash", 
            line_color="red", 
            annotation_text=f"เป้าหมาย ({DAILY_GOALS['calories']} kcal)"
        )
        fig_week.update_traces(marker_color='#3b82f6', textposition='outside')
        st.plotly_chart(fig_week, use_container_width=True)
    else:
        st.warning("ยังไม่มีข้อมูลบันทึกในรอบ 7 วันที่ผ่านมา ลองเริ่มบันทึกมื้ออาหารมื้อแรกได้ที่แท็บ 'สแกนและบันทึกอาหาร'")
          
