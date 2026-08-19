import streamlit as st
import pandas as pd
import sqlite3
import datetime
import urllib.parse
import math

# --- PAGE CONFIGURATION ---
st.set_page_config(
    page_title="وقف الإرتقاء الخيري",
    page_icon="🕌",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- MODERN LUXURY RTL STYLING (CSS) ---
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Cairo:wght@400;600;700;800;900&display=swap');
    
    html, body, [class*="css"], div, span, label, input, select, textarea, button {
        font-family: 'Cairo', sans-serif !important;
        direction: rtl !important;
        text-align: right !important;
    }
    
    .stApp {
        background: #f8fafc;
    }
    
    section[data-testid="stSidebar"] {
        background: linear-gradient(180deg, #0f382c 0%, #164032 100%);
        color: #ffffff !important;
        border-left: 2px solid #d4af37;
    }
    
    section[data-testid="stSidebar"] * {
        color: #f1f5f9 !important;
    }

    .main-header {
        background: linear-gradient(135deg, #0f382c 0%, #1a5241 60%, #d4af37 100%);
        color: white;
        padding: 22px;
        border-radius: 16px;
        text-align: center;
        margin-bottom: 25px;
        box-shadow: 0px 8px 20px rgba(15, 56, 44, 0.15);
        border: 1px solid rgba(212, 175, 55, 0.4);
    }
    .main-header h1 {
        color: #ffffff !important;
        margin: 0;
        font-weight: 900;
        font-size: 2.1rem;
    }
    .main-header p {
        color: #f1f5f9 !important;
        font-size: 0.95rem;
        margin-top: 5px;
    }

    .stButton>button {
        background: linear-gradient(135deg, #1a5241 0%, #0f382c 100%) !important;
        color: #ffffff !important;
        border-radius: 10px !important;
        border: 1px solid #d4af37 !important;
        padding: 8px 20px !important;
        font-weight: 700 !important;
        font-size: 0.95rem !important;
        transition: all 0.3s ease !important;
        box-shadow: 0 4px 10px rgba(26, 82, 65, 0.12) !important;
        width: 100%;
    }
    .stButton>button:hover {
        background: linear-gradient(135deg, #d4af37 0%, #b89228 100%) !important;
        color: #0f382c !important;
        transform: translateY(-2px);
    }

    div[data-testid="stMetric"] {
        background: #ffffff;
        padding: 18px;
        border-radius: 14px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.04);
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

    div[data-testid="stDataFrame"] {
        background: white;
        padding: 12px;
        border-radius: 12px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.03);
        border: 1px solid #e2e8f0;
    }
    
    .custom-card {
        background: white;
        padding: 22px;
        border-radius: 16px;
        box-shadow: 0 4px 15px rgba(0,0,0,0.03);
        margin-bottom: 20px;
        border: 1px solid #e2e8f0;
    }
</style>
""", unsafe_allow_html=True)

# --- SAFE DATABASE SETUP (PRESERVES EXISTING DATA) ---
DB_FILE = "donations_system_v5.db"

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
    c.execute("CREATE TABLE IF NOT EXISTS donor_allocations (id INTEGER PRIMARY KEY AUTOINCREMENT, donor_id INTEGER NOT NULL, donor_name TEXT NOT NULL, beneficiary_type TEXT NOT NULL, beneficiary_name TEXT NOT NULL, allocated_amount REAL NOT NULL, notes TEXT)")

    c.execute("SELECT COUNT(*) FROM categories")
    if c.fetchone()[0] == 0:
        c.executemany("INSERT OR IGNORE INTO categories (name) VALUES (?)", [('رواتب',), ('البرامج والأنشطة',), ('الجوائز والتكريم',), ('دعومات أخرى',)])
        c.executemany("INSERT OR IGNORE INTO subcategories (category_name, name) VALUES (?,?)", [
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

# ---------------------------------------------------------
# 1. DASHBOARD
# ---------------------------------------------------------
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

# ---------------------------------------------------------
# 2. DONORS MANAGEMENT
# ---------------------------------------------------------
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
            for i in range(int(num_allocs)):
                ac1, ac2, ac3 = st.columns([1.5, 2, 1.5])
                b_type = ac1.selectbox(f"النوع #{i+1}", ["معلم", "إداري"], key=f"btype_{i}")
                b_opts = teachers_df['name'].tolist() if b_type == "معلم" else staff_df['name'].tolist()
                if not b_opts: b_opts = ["لا يوجد عناصر"]
                b_name = ac2.selectbox(f"المستفيد #{i+1}", b_opts, key=f"bname_{i}")
                b_amt = ac3.number_input(f"المبلغ المخصص #{i+1}", min_value=0.0, value=monthly_exp/num_allocs if num_allocs > 0 else 0.0, step=50.0, key=f"bamt_{i}")
                
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
                    c.execute("DELETE FROM donor_allocations WHERE donor_id=?", (int(d_data['id']),))
                    conn.commit()
                    st.warning("تم الحذف!")
                    st.rerun()
    conn.close()
    st.markdown("</div>", unsafe_allow_html=True)

# ---------------------------------------------------------
# 3. DONOR ALLOCATIONS
# ---------------------------------------------------------
elif choice == "🎯 كفالات وتوزيع الدعم":
    st.markdown("<div class='custom-card'>", unsafe_allow_html=True)
    st.subheader("🎯 إدارة كفالات وتقسيم دعومات المستفيدين")
    conn = get_connection()
    alloc_df = pd.read_sql("SELECT * FROM donor_allocations", conn)
    
    if not alloc_df.empty:
        st.dataframe(alloc_df[['donor_name', 'beneficiary_type', 'beneficiary_name', 'allocated_amount', 'notes']], use_container_width=True)
    else:
        st.info("لم يتم إدخال تخصيصات كفالات حتى الآن.")
    conn.close()
    st.markdown("</div>", unsafe_allow_html=True)

# ---------------------------------------------------------
# 4. SYSTEM DEFINITIONS & MANAGEMENT
# ---------------------------------------------------------
elif choice == "🛠️ إدارة وتعاريف النظام":
    st.markdown("<div class='custom-card'>", unsafe_allow_html=True)
    st.subheader("🛠️ تعاريف وإعدادات النظام")
    
    t1, t2, t3 = st.tabs(["👨‍🏫 المعلمين والإداريين", "📁 البنود والتصنيفات", "🕌 الحلقات والمشاريع"])
    conn = get_connection()
    
    with t1:
        st.write("#### إضافة معلم / إداري جديد")
        col1, col2, col3 = st.columns(3)
        p_type = col1.selectbox("الصفة", ["معلم", "إداري"])
        p_name = col2.text_input("الاسم الثلاثي")
        p_salary = col3.number_input("الراتب / المستحق الشهري", min_value=0.0, step=100.0)
        
        if st.button("➕ إضافة المستفيد") and p_name:
            c = conn.cursor()
            if p_type == "معلم":
                c.execute("INSERT INTO teachers (name, salary) VALUES (?,?)", (p_name, p_salary))
            else:
                c.execute("INSERT INTO staff (name, role, salary) VALUES (?,?,?)", (p_name, "إداري", p_salary))
            conn.commit()
            st.success("تمت الإضافة بنجاح!")
            st.rerun()

    with t2:
        st.write("#### إضافة بند جديد")
        c1, c2 = st.columns(2)
        cat_in = c1.text_input("اسم البند الرئيسي الجديد")
        if c1.button("إضافة بند رئيسي") and cat_in:
            c = conn.cursor()
            c.execute("INSERT OR IGNORE INTO categories (name) VALUES (?)", (cat_in,))
            conn.commit()
            st.success("تمت الإضافة!")
            st.rerun()

    with t3:
        st.write("#### إضافة مشروع / حلقة")
        p_in = st.text_input("اسم الحلقة / المشروع")
        if st.button("إضافة مشروع") and p_in:
            c = conn.cursor()
            c.execute("INSERT OR IGNORE INTO projects (name) VALUES (?)", (p_in,))
            conn.commit()
            st.success("تمت الإضافة!")
            st.rerun()

    conn.close()
    st.markdown("</div>", unsafe_allow_html=True)

# ---------------------------------------------------------
# 5. RECEIPTS (ACCURATE MONTHLY SPLIT)
# ---------------------------------------------------------
elif choice == "📥 تسجيل المقبوضات":
    st.markdown("<div class='custom-card'>", unsafe_allow_html=True)
    st.subheader("📥 تسجيل دفعة مقبوضات جديدة")
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
            
            selected_months = st.multiselect("📅 حدد الشهر / الأشهر المسددة بهذه الدفعة حصراً:", MONTHS)

            if st.form_submit_button("تسجيل المقبوضات ✅"):
                if not selected_months:
                    st.error("⚠️ يرجى تحديد الشهر المدفوع بالتحديد!")
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
                    st.success("✅ تم تسجيل المقبوضات للشهر / الأشهر المحددة بنجاح!")
                    st.rerun()
    else:
        st.info("يرجى إضافة داعمين أولاً قبل تسجيل المقبوضات.")
    conn.close()
    st.markdown("</div>", unsafe_allow_html=True)

# ---------------------------------------------------------
# 6. EXPENSES
# ---------------------------------------------------------
elif choice == "💸 تسجيل المصروفات":
    st.markdown("<div class='custom-card'>", unsafe_allow_html=True)
    st.subheader("💸 تسجيل المصروفات والنفقات")
    conn = get_connection()
    cats = pd.read_sql("SELECT name FROM categories", conn)['name'].tolist()
    
    with st.form("expense_form"):
        col1, col2 = st.columns(2)
        e_beneficiary = col1.text_input("اسم المستفيد / الجهة")
        e_cat = col2.selectbox("البند الرئيسي", cats)
        
        col3, col4, col5 = st.columns([2, 1, 1])
        e_amount = col3.number_input("المبلغ (ر.س)", min_value=1.0, step=50.0)
        e_date = col4.date_input("التاريخ", datetime.date.today())
        e_year = col5.selectbox("السنة المالية", YEARS_LIST, index=YEARS_LIST.index(2026))
        
        e_notes = st.text_area("ملاحظات / بيان الصرف")
        
        if st.form_submit_button("تسجيل المصروفات 💸"):
            hijri_str = get_hijri_str(e_date)
            c = conn.cursor()
            c.execute(
                "INSERT INTO expenses (date, date_hijri, beneficiary, category, subcategory, amount, notes, year) VALUES (?,?,?,?,?,?,?,?)",
                (str(e_date), hijri_str, e_beneficiary, e_cat, "عام", e_amount, e_notes, int(e_year))
            )
            conn.commit()
            st.success("✅ تم تسجيل المصروف بنجاح!")
            st.rerun()
            
    conn.close()
    st.markdown("</div>", unsafe_allow_html=True)

# ---------------------------------------------------------
# 7. MONTHLY MATRIX (PER-MONTH ACCURACY)
# ---------------------------------------------------------
elif choice == "🗓️ متابعة الأشهر والالتزامات":
    st.markdown("<div class='custom-card'>", unsafe_allow_html=True)
    st.subheader("🗓️ جدول المتابعة الشهري الدقيق للداعمين")
    selected_matrix_year = st.selectbox("📅 اختر السنة:", YEARS_LIST, index=YEARS_LIST.index(2026))

    conn = get_connection()
    donors_df = pd.read_sql("SELECT * FROM donors", conn)
    receipts_df = pd.read_sql("SELECT donor_id, month FROM receipts WHERE year = ?", conn, params=(selected_matrix_year,))
    allocations_df = pd.read_sql("SELECT DISTINCT donor_id FROM donor_allocations", conn)
    conn.close()
    
    st.markdown("""
    **دليل الرموز:** 
    * (✅ مدفوع) : مسجل تبرع ومقبوضات لهذا الشهر بالتحديد.
    * (🎯 مخصص) : داعم مستمر لديه كفالة مخصصة ولم يسدد بعد لهذا الشهر.
    * (🚨 متأخر) : داعم مستمر بدون كفالة مخصصة ولم يسدد لهذا الشهر.
    * (⚪) : دعم منقطع أو غير مستمر.
    """)

    if not donors_df.empty:
        matrix_rows = []
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
                # الفحص المباشر للشهر المالي والسنة بدقة متناهية
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
    else:
        st.info("لا يوجد داعمين مسجلين للنظام بعد.")
    st.markdown("</div>", unsafe_allow_html=True)

# ---------------------------------------------------------
# 8. WHATSAPP REMINDER CENTER
# ---------------------------------------------------------
elif choice == "📱 مركز تذكير الواتساب":
    st.markdown("<div class='custom-card'>", unsafe_allow_html=True)
    st.subheader("📱 مركز تذكير الواتساب وإرسال الرسائل")
    
    conn = get_connection()
    donors_df = pd.read_sql("SELECT * FROM donors WHERE phone IS NOT NULL AND phone != ''", conn)
    conn.close()
    
    if not donors_df.empty:
        selected_d_name = st.selectbox("اختر الداعم للتواصل معهم عبر الواتساب:", donors_df['name'].tolist())
        donor_info = donors_df[donors_df['name'] == selected_d_name].iloc[0]
        
        msg_template = f"السلام عليكم ورحمة الله وبركاته، {donor_info['title']} {donor_info['name']} المحترم، نذكركم بدعمكم الشهري لوقف الإرتقاء الخيري. جزاكم الله خيراً."
        msg_text = st.text_area("نص الرسالة:", value=msg_template, height=120)
        
        phone = str(donor_info['phone']).replace("+", "").replace(" ", "")
        encoded_msg = urllib.parse.quote(msg_text)
        wa_url = f"https://api.whatsapp.com/send?phone={phone}&text={encoded_msg}"
        
        st.markdown(f'<a href="{wa_url}" target="_blank"><button style="background-color:#25D366; color:white; border:none; padding:12px 24px; border-radius:10px; font-weight:bold; cursor:pointer; width:100%;">📲 إرسال عبر الواتساب الآن</button></a>', unsafe_allow_html=True)
    else:
        st.info("لا يوجد داعمين لديهم أرقام هواتف مسجلة بالنظام.")
    st.markdown("</div>", unsafe_allow_html=True)

# ---------------------------------------------------------
# 9. REPORTS AND PRINTING
# ---------------------------------------------------------
elif choice == "🖨️ التقارير والطباعة":
    st.markdown("<div class='custom-card'>", unsafe_allow_html=True)
    st.subheader("🖨️ تقارير المقبوضات والمصروفات")
    
    rep_year = st.selectbox("اختر السنة المالية:", YEARS_LIST, index=YEARS_LIST.index(2026))
    conn = get_connection()
    
    r_df = pd.read_sql("SELECT date AS التاريخ, donor_name AS الداعم, project AS المشروع, amount AS المبلغ, month AS الشهر FROM receipts WHERE year = ?", conn, params=(rep_year,))
    e_df = pd.read_sql("SELECT date AS التاريخ, beneficiary AS المستفيد, category AS البند, amount AS المبلغ FROM expenses WHERE year = ?", conn, params=(rep_year,))
    conn.close()
    
    st.write("### 📥 سجل المقبوضات")
    st.dataframe(r_df, use_container_width=True)
    
    st.write("### 💸 سجل المصروفات")
    st.dataframe(e_df, use_container_width=True)
    
    st.markdown("</div>", unsafe_allow_html=True)
