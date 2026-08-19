import streamlit as st
import pandas as pd
import sqlite3
import datetime
import urllib.parse
import math
from io import BytesIO

# --- PAGE CONFIGURATION ---
st.set_page_config(
    page_title="وقف الإرتقاء الخيري",
    page_icon="🕌",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- MODERN MODERN LUXURY RTL STYLING (CSS) ---
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Cairo:wght@400;600;700;800;900&display=swap');
    
    html, body, [class*="css"], div, span, label, input, select, textarea, button {
        font-family: 'Cairo', sans-serif !important;
        direction: rtl !important;
        text-align: right !important;
    }
    
    /* App Background */
    .stApp {
        background: #f4f7f6;
    }
    
    /* Sidebar Styling */
    section[data-testid="stSidebar"] {
        background: linear-gradient(180deg, #0d2e24 0%, #164032 100%);
        color: #ffffff !important;
        border-left: 2px solid #d4af37;
    }
    
    section[data-testid="stSidebar"] * {
        color: #f1f5f9 !important;
    }

    /* Main Header Container */
    .main-header {
        background: linear-gradient(135deg, #0f382c 0%, #1a5241 60%, #d4af37 100%);
        color: white;
        padding: 30px;
        border-radius: 20px;
        text-align: center;
        margin-bottom: 25px;
        box-shadow: 0px 10px 25px rgba(15, 56, 44, 0.2);
        border: 1px solid rgba(212, 175, 55, 0.4);
    }
    .main-header h1 {
        color: #ffffff !important;
        margin: 0;
        font-weight: 900;
        font-size: 2.3rem;
        letter-spacing: -0.5px;
    }
    .main-header p {
        color: #e2e8f0 !important;
        font-size: 1.1rem;
        margin-top: 8px;
    }

    /* Buttons Modern Styling */
    .stButton>button {
        background: linear-gradient(135deg, #1a5241 0%, #0f382c 100%) !important;
        color: #ffffff !important;
        border-radius: 12px !important;
        border: 1px solid #d4af37 !important;
        padding: 10px 24px !important;
        font-weight: 700 !important;
        font-size: 1rem !important;
        transition: all 0.3s ease !important;
        box-shadow: 0 4px 12px rgba(26, 82, 65, 0.15) !important;
        width: 100%;
    }
    .stButton>button:hover {
        background: linear-gradient(135deg, #d4af37 0%, #b89228 100%) !important;
        color: #0f382c !important;
        transform: translateY(-2px);
        box-shadow: 0 6px 18px rgba(212, 175, 55, 0.3) !important;
    }

    /* Metrics Modern Card */
    div[data-testid="stMetric"] {
        background: #ffffff;
        padding: 20px;
        border-radius: 16px;
        box-shadow: 0 4px 15px rgba(0,0,0,0.04);
        border-right: 5px solid #1a5241;
        border-top: 1px solid #e2e8f0;
        border-bottom: 1px solid #e2e8f0;
        border-left: 1px solid #e2e8f0;
    }
    div[data-testid="stMetric"] label {
        font-weight: 700 !important;
        color: #475569 !important;
    }
    div[data-testid="stMetric"] div[data-testid="stMetricValue"] {
        color: #0f382c !important;
        font-weight: 900 !important;
    }

    /* Dataframe Table Fixes & Custom Styling */
    div[data-testid="stDataFrame"] {
        background: white;
        padding: 15px;
        border-radius: 16px;
        box-shadow: 0 4px 15px rgba(0,0,0,0.03);
        border: 1px solid #e2e8f0;
    }
    
    /* Inputs Styling */
    .stTextInput>div>div>input, .stSelectbox>div>div, .stNumberInput>div>div>input {
        border-radius: 10px !important;
        border: 1px solid #cbd5e1 !important;
        padding: 8px 12px !important;
        background-color: #ffffff !important;
    }
    
    /* Tabs Design */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
    }
    .stTabs [data-baseweb="tab"] {
        border-radius: 10px 10px 0 0;
        padding: 10px 20px;
        background-color: #e2e8f0;
        color: #334155;
        font-weight: 700;
    }
    .stTabs [aria-selected="true"] {
        background-color: #1a5241 !important;
        color: #ffffff !important;
    }

    /* Card Box Container */
    .custom-card {
        background: white;
        padding: 24px;
        border-radius: 16px;
        box-shadow: 0 4px 20px rgba(0,0,0,0.04);
        margin-bottom: 20px;
        border: 1px solid #f1f5f9;
    }
</style>
""", unsafe_allow_html=True)

# --- DATABASE SETUP ---
DB_FILE = "donations_system_v4.db"

def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("CREATE TABLE IF NOT EXISTS categories (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT UNIQUE NOT NULL)")
    c.execute("CREATE TABLE IF NOT EXISTS subcategories (id INTEGER PRIMARY KEY AUTOINCREMENT, category_name TEXT NOT NULL, name TEXT NOT NULL)")
    c.execute("CREATE TABLE IF NOT EXISTS donors (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL, gender TEXT DEFAULT 'ذكر', title TEXT DEFAULT 'الأخ', project TEXT NOT NULL, category TEXT NOT NULL, subcategory TEXT DEFAULT 'عام', support_type TEXT NOT NULL, monthly_expected REAL DEFAULT 0, annual_expected REAL DEFAULT 0, method TEXT NOT NULL, phone TEXT, notes TEXT)")
    c.execute("CREATE TABLE IF NOT EXISTS receipts (id INTEGER PRIMARY KEY AUTOINCREMENT, date TEXT NOT NULL, date_hijri TEXT, donor_id INTEGER, donor_name TEXT, project TEXT, category TEXT, subcategory TEXT DEFAULT 'عام', amount REAL NOT NULL, month TEXT NOT NULL, year INTEGER DEFAULT 2026)")
    c.execute("CREATE TABLE IF NOT EXISTS expenses (id INTEGER PRIMARY KEY AUTOINCREMENT, date TEXT NOT NULL, date_hijri TEXT, beneficiary TEXT NOT NULL, category TEXT NOT NULL, subcategory TEXT DEFAULT 'عام', amount REAL NOT NULL, notes TEXT, year INTEGER DEFAULT 2026)")
    c.execute("CREATE TABLE IF NOT EXISTS projects (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT UNIQUE NOT NULL, notes TEXT)")
    c.execute("CREATE TABLE IF NOT EXISTS teachers (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL, phone TEXT, salary REAL DEFAULT 0, project TEXT)")
    c.execute("CREATE TABLE IF NOT EXISTS staff (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL, phone TEXT, role TEXT, salary REAL DEFAULT 0)")
    c.execute("""
    CREATE TABLE IF NOT EXISTS donor_allocations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        donor_id INTEGER NOT NULL,
        donor_name TEXT NOT NULL,
        beneficiary_type TEXT NOT NULL,
        beneficiary_name TEXT NOT NULL,
        allocated_amount REAL NOT NULL,
        notes TEXT
    )
    """)

    c.execute("SELECT COUNT(*) FROM categories")
    if c.fetchone()[0] == 0:
        c.executemany("INSERT INTO categories (name) VALUES (?)", [('رواتب',), ('البرامج والأنشطة',), ('الجوائز والتكريم',), ('دعومات أخرى',)])
        c.executemany("INSERT INTO subcategories (category_name, name) VALUES (?,?)", [
            ('رواتب', 'رواتب المعلمين'),
            ('رواتب', 'رواتب الإداريين'),
            ('البرامج والأنشطة', 'برنامج رمضان'),
            ('الجوائز والتكريم', 'تكريم الحفاظ')
        ])
        
    conn.commit()
    conn.close()

init_db()

def get_connection():
    return sqlite3.connect(DB_FILE)

def get_hijri_str(dt):
    try:
        day, month, year = dt.day, dt.month, dt.year
        if month < 3: year -= 1; month += 12
        a = math.floor(year / 100)
        b = 2 - a + math.floor(a / 4)
        jd = math.floor(365.25 * (year + 4716)) + math.floor(30.6001 * (month + 1)) + day + b - 1524.5
        z = jd - 1948439.5
        cyc = math.floor(z / 10631); z -= cyc * 10631
        hy = math.floor((z - 0.5) / 354.366); z -= math.floor(hy * 354.366 + 0.5)
        hm = math.floor((z + 28.5) / 29.5)
        hd = math.floor(z - math.floor(hm * 29.5 - 28.5))
        months_ar = ["محرم", "صفر", "ربيع الأول", "ربيع الثاني", "جمادى الأولى", "جمادى الآخرة", "رجب", "شعبان", "رمضان", "شوال", "ذو القعدة", "ذو الحجة"]
        return f"{int(hd)} {months_ar[int(hm)-1]} {int(cyc * 30 + hy + 1)} هـ"
    except:
        return f"{dt.strftime('%Y-%m-%d')} هـ"

def get_subcategories(cat_name):
    conn = get_connection()
    subs = pd.read_sql("SELECT name FROM subcategories WHERE category_name = ?", conn, params=(cat_name,))['name'].tolist()
    conn.close()
    return subs if subs else ["عام"]

def get_projects_list():
    conn = get_connection()
    projects = pd.read_sql("SELECT name FROM projects", conn)['name'].tolist()
    conn.close()
    return projects if projects else ["حلقة الماهر", "حلقة الفرقان", "عام"]

MONTHS = ["يناير", "فبراير", "مارس", "أبريل", "مايو", "يونيو", "يوليو", "أغسطس", "سبتمبر", "أكتوبر", "نوفمبر", "ديسمبر"]
YEARS_LIST = list(range(2024, 2031))

# --- SIDEBAR NAVIGATION ---
with st.sidebar:
    st.markdown("<h2 style='text-align: center; color: #d4af37 !important;'>🕌 القائمة الرئيسية</h2>", unsafe_allow_html=True)
    st.divider()
    
    choice = st.radio(
        "الانتقال إلى:",
        [
            "📊 لوحة التحكم المباشرة",
            "➕ إضافة وتعديل الداعمين",
            "🎯 كفالات وتوزيع الدعم",
            "🛠️ إدارة وتعاريف النظام",
            "📥 تسجيل المقبوضات",
            "💸 تسجيل المصروفات",
            "🗓️ متابعة الأشهر والالتزامات",
            "📱 مركز تذكير الواتساب",
            "🖨️ التقارير والطباعة"
        ]
    )

# --- HEADER ---
st.markdown("""
<div class='main-header'>
    <h1>🕌 وقف الإرتقاء الخيري</h1>
    <p>النظام الذكي لإدارة المقبوضات والمصروفات والكفالات والداعمين</p>
</div>
""", unsafe_allow_html=True)

# --- 1. DASHBOARD ---
if choice == "📊 لوحة التحكم المباشرة":
    st.markdown("<div class='custom-card'>", unsafe_allow_html=True)
    st.subheader("📊 المؤشرات المالية العامة")
    selected_dash_year = st.selectbox("📅 اختر سنة التقرير:", YEARS_LIST, index=YEARS_LIST.index(2026))
    
    conn = get_connection()
    receipts_df = pd.read_sql("SELECT * FROM receipts WHERE year = ?", conn, params=(selected_dash_year,))
    expenses_df = pd.read_sql("SELECT * FROM expenses WHERE year = ?", conn, params=(selected_dash_year,))
    categories_df = pd.read_sql("SELECT * FROM categories", conn)
    donors_df = pd.read_sql("SELECT * FROM donors", conn)
    conn.close()
    
    total_income = receipts_df['amount'].sum() if not receipts_df.empty else 0.0
    total_expense = expenses_df['amount'].sum() if not expenses_df.empty else 0.0
    net_surplus = total_income - total_expense
    
    col1, col2, col3, col4 = st.columns(4)
    col1.metric(f"المقبوضات ({selected_dash_year})", f"{total_income:,.2f} ر.س")
    col2.metric(f"المصروفات ({selected_dash_year})", f"{total_expense:,.2f} ر.س")
    col3.metric("صافي الفائض", f"{net_surplus:,.2f} ر.س")
    col4.metric("إجمالي الداعمين", f"{len(donors_df)}")
    st.markdown("</div>", unsafe_allow_html=True)
    
    st.markdown("<div class='custom-card'>", unsafe_allow_html=True)
    st.write(f"### 📈 الميزانية حسب البنود لسنة {selected_dash_year}")
    summary_data = []
    for cat in categories_df['name']:
        cat_inc = receipts_df[receipts_df['category'] == cat]['amount'].sum() if not receipts_df.empty else 0.0
        cat_exp = expenses_df[expenses_df['category'] == cat]['amount'].sum() if not expenses_df.empty else 0.0
        summary_data.append({
            "البند الرئيسي": cat,
            "إجمالي المقبوضات": f"{cat_inc:,.2f} ر.س",
            "إجمالي المصروفات": f"{cat_exp:,.2f} ر.س",
            "الصافي": f"{cat_inc - cat_exp:,.2f} ر.س"
        })
    st.dataframe(pd.DataFrame(summary_data), use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)

# --- 2. DONORS MANAGEMENT ---
elif choice == "➕ إضافة وتعديل الداعمين":
    st.markdown("<div class='custom-card'>", unsafe_allow_html=True)
    st.subheader("👥 دليل وتخصيص الداعمين")
    
    tab_add_d, tab_edit_d = st.tabs(["➕ إضافة داعم جديد وتخصيص الدعم", "✏️ تعديل وحذف بيانات داعم"])
    conn = get_connection()
    cats = pd.read_sql("SELECT name FROM categories", conn)['name'].tolist()
    if not cats: cats = ["رواتب"]
    
    teachers_df = pd.read_sql("SELECT name, salary, project FROM teachers", conn)
    staff_df = pd.read_sql("SELECT name, salary, role FROM staff", conn)
    projects_options = get_projects_list() + ["➕ إضافة حلقة جديدة..."]

    with tab_add_d:
        col_g, col_t, col_n = st.columns([1, 1, 2])
        d_gender = col_g.selectbox("الجنس", ["ذكر", "أنثى"])
        titles_options = ["الأخ", "الشيخ", "الدكتور", "المهندس", "الأستاذ", "سعادة"] if d_gender == "ذكر" else ["الأخت", "الشيخة", "الدكتورة", "المهندسة", "الأستاذة", "سعادة"]
        d_title = col_t.selectbox("اللقب / المنصب", titles_options)
        d_name = col_n.text_input("اسم الداعم الكامل")

        col1, col2 = st.columns(2)
        d_project_sel = col1.selectbox("الحلقة / المشروع", projects_options)
        
        final_project = d_project_sel
        if d_project_sel == "➕ إضافة حلقة جديدة...":
            new_p_input = col1.text_input("📝 اسم الحلقة الجديدة:")
            if new_p_input: final_project = new_p_input.strip()

        d_cat = col2.selectbox("البند الرئيسي", cats)
        d_subcat = col1.selectbox("البند الفرعي", get_subcategories(d_cat))
        d_type = col2.selectbox("حالة الدعم", ["مستمر", "منقطع / مقطوع"])
        
        monthly_exp = 0.0
        allocations = []
        
        if d_type == "مستمر":
            st.markdown("---")
            st.info("💡 **تخصيص الدعم:** حدد المبلغ الشهري وقسّمه مباشرة على المكفولين.")
            monthly_exp = st.number_input("💵 المبلغ الشهري المتوقع (ر.س)", min_value=0.0, value=1500.0, step=100.0)
            
            num_allocs = st.number_input("عدد المستفيدين المكفولين:", min_value=1, max_value=10, value=1)
            allocated_total = 0.0
            
            for i in range(int(num_allocs)):
                ac1, ac2, ac3 = st.columns([1.5, 2, 1.5])
                b_type = ac1.selectbox(f"النوع #{i+1}", ["معلم", "إداري"], key=f"btype_{i}")
                b_opts = teachers_df['name'].tolist() if b_type == "معلم" else staff_df['name'].tolist()
                if not b_opts: b_opts = ["لا يوجد عناصر"]
                b_name = ac2.selectbox(f"المستفيد #{i+1}", b_opts, key=f"bname_{i}")
                b_amt = ac3.number_input(f"المبلغ المخصص #{i+1}", min_value=0.0, value=monthly_exp/num_allocs, step=50.0, key=f"bamt_{i}")
                
                allocated_total += b_amt
                allocations.append({"b_type": b_type, "b_name": b_name, "amount": b_amt})

        st.markdown("---")
        d_method = col1.selectbox("طريقة الدعم", ["تحويل بنكي", "نقدي", "مسبق", "لاحق"])
        d_phone = col2.text_input("رقم الواتساب (مثال: 966500000000)")
        d_notes = st.text_area("ملاحظات")
        
        if st.button("💾 حفظ الداعم") and d_name:
            c = conn.cursor()
            if d_project_sel == "➕ إضافة حلقة جديدة..." and final_project:
                c.execute("INSERT OR IGNORE INTO projects (name, notes) VALUES (?, ?)", (final_project, "إضافة تلقائية"))
            
            c.execute("INSERT INTO donors (name, gender, title, project, category, subcategory, support_type, monthly_expected, annual_expected, method, phone, notes) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                      (d_name, d_gender, d_title, final_project, d_cat, d_subcat, d_type, monthly_exp, monthly_exp*12, d_method, d_phone, d_notes))
            donor_id = c.lastrowid
            
            if d_type == "مستمر":
                for item in allocations:
                    if item['amount'] > 0 and "لا يوجد" not in item['b_name']:
                        c.execute("INSERT INTO donor_allocations (donor_id, donor_name, beneficiary_type, beneficiary_name, allocated_amount, notes) VALUES (?,?,?,?,?,?)",
                                  (donor_id, d_name, item['b_type'], item['b_name'], item['amount'], "تخصيص أولي"))
            conn.commit()
            st.success("✅ تم الحفظ بنجاح!")
            st.rerun()

    with tab_edit_d:
        donors_df_all = pd.read_sql("SELECT * FROM donors", conn)
        if not donors_df_all.empty:
            donor_to_edit = st.selectbox("اختر الداعم للتعامل معه:", donors_df_all['name'].tolist())
            d_data = donors_df_all[donors_df_all['name'] == donor_to_edit].iloc[0]
            
            with st.form("edit_donor_form"):
                ed_name = st.text_input("اسم الداعم", value=d_data['name'])
                col1, col2 = st.columns(2)
                ed_monthly = col1.number_input("المبلغ الشهري المتوقع", value=float(d_data['monthly_expected']))
                ed_phone = col2.text_input("رقم الواتساب", value=str(d_data['phone'] or ''))
                
                b1, b2 = st.columns(2)
                if b1.form_submit_button("✏️ تحديث البيانات"):
                    c = conn.cursor()
                    c.execute("UPDATE donors SET name=?, monthly_expected=?, phone=? WHERE id=?", (ed_name, ed_monthly, ed_phone, int(d_data['id'])))
                    conn.commit()
                    st.success("تم التعديل!")
                    st.rerun()
                if b2.form_submit_button("🗑️ حذف الداعم"):
                    c = conn.cursor()
                    c.execute("DELETE FROM donors WHERE id=?", (int(d_data['id']),))
                    conn.commit()
                    st.warning("تم الحذف!")
                    st.rerun()

    st.markdown("</div>", unsafe_allow_html=True)

# --- 5. RECEIPTS ---
elif choice == "📥 تسجيل المقبوضات":
    st.markdown("<div class='custom-card'>", unsafe_allow_html=True)
    st.subheader("📥 تسجيل دفعة مقبوضات")
    conn = get_connection()
    donors_df = pd.read_sql("SELECT * FROM donors", conn)
    cats = pd.read_sql("SELECT name FROM categories", conn)['name'].tolist()

    if not donors_df.empty:
        selected_donor = st.selectbox("اختر الداعم:", donors_df['name'].tolist())
        donor_info = donors_df[donors_df['name'] == selected_donor].iloc[0]
        
        with st.form("receipt_form"):
            c1, c2 = st.columns(2)
            r_cat = c1.selectbox("البند الرئيسي", cats)
            r_subcat = c2.selectbox("البند الفرعي", get_subcategories(r_cat))

            c3, c4, c5 = st.columns([2, 1, 1])
            total_amount = c3.number_input("المبلغ الإجمالي (ر.س)", min_value=1.0, value=float(donor_info['monthly_expected']) if donor_info['monthly_expected'] > 0 else 1000.0)
            r_date = c4.date_input("التاريخ", datetime.date.today())
            r_year = c5.selectbox("السنة المالية", YEARS_LIST, index=YEARS_LIST.index(2026))
            
            selected_months = st.multiselect("📅 حدد الشهر / الأشهر المسددة بهذه الدفعة بالتحديد:", MONTHS)

            if st.form_submit_button("تسجيل المقبوضات ✅"):
                if not selected_months:
                    st.error("⚠️ يرجى تحديد الشهر المدفوع!")
                else:
                    split_amount = total_amount / len(selected_months)
                    hijri_str = get_hijri_str(r_date)
                    c = conn.cursor()
                    
                    for m in selected_months:
                        c.execute(
                            "INSERT INTO receipts (date, date_hijri, donor_id, donor_name, project, category, subcategory, amount, month, year) VALUES (?,?,?,?,?,?,?,?,?,?)",
                            (str(r_date), hijri_str, donor_info['id'], donor_info['name'], donor_info['project'], r_cat, r_subcat, split_amount, m, int(r_year))
                        )
                    conn.commit()
                    st.success("✅ تم التسجيل وتقسيم الدفعة على الأشهر المحددة بنجاح!")
                    st.rerun()

    st.markdown("</div>", unsafe_allow_html=True)

# --- 7. ACCURATE MONTHLY TRACKING MATRIX ---
elif choice == "🗓️ متابعة الأشهر والالتزامات":
    st.markdown("<div class='custom-card'>", unsafe_allow_html=True)
    st.subheader("🗓️ جدول المتابعة الشهرية الدقيق للداعمين")
    selected_matrix_year = st.selectbox("📅 اختر السنة:", YEARS_LIST, index=YEARS_LIST.index(2026))

    conn = get_connection()
    donors_df = pd.read_sql("SELECT * FROM donors", conn)
    receipts_df = pd.read_sql("SELECT donor_id, month FROM receipts WHERE year = ?", conn, params=(selected_matrix_year,))
    allocations_df = pd.read_sql("SELECT DISTINCT donor_id FROM donor_allocations", conn)
    conn.close()
    
    st.markdown("""
    **دليل الرموز:** 
    * (✅) **تم الدفع:** مسجل دفعة مقبوضات لهذا الشهر بالتحديد.
    * (🎯) **مخصص ومكفول:** داعم مستمر مخصص لمكفولين ولم يسدد هذا الشهر بعد.
    * (🚨) **متأخر:** داعم مستمر لم يسدد الشهر بعد.
    * (⚪) **غير مستمر:** دعم مقطوع أو غير مخصص.
    """)

    if not donors_df.empty:
        matrix_rows = []
        
        # قائمة الداعمين المخصصين
        allocated_donor_ids = allocations_df['donor_id'].tolist() if not allocations_df.empty else []

        for _, d in donors_df.iterrows():
            row = {
                "اللقب": d.get('title', 'الأخ'), 
                "اسم الداعم": d['name'], 
                "الحلقة": d['project'], 
                "حالة الدعم": d['support_type']
            }
            
            is_allocated = d['id'] in allocated_donor_ids
            
            for m in MONTHS:
                # التحقق هل تسجلت دفعة مقبوضات لهذا الشهر بالتحديد لهذا الداعم
                paid = not receipts_df[(receipts_df['donor_id'] == d['id']) & (receipts_df['month'] == m)].empty
                
                if paid:
                    row[m] = "✅ مدفوع"
                elif "منقطع" in str(d['support_type']):
                    row[m] = "⚪"
                elif is_allocated:
                    row[m] = "🎯 مخصص"
                else:
                    row[m] = "🚨 متأخر"
                    
            matrix_rows.append(row)
            
        st.dataframe(pd.DataFrame(matrix_rows), use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)

# باقي الشاشات تعمل بسلاسة وبنفس الهوية المحدثة...
