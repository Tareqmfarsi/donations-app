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

# --- GLOBAL RTL & PRINT STYLING (CSS) ---
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Cairo:wght@400;600;700;800&display=swap');
    
    html, body, [class*="css"], div, span, label, input, select, textarea, button {
        font-family: 'Cairo', sans-serif !important;
        direction: rtl !important;
        text-align: right !important;
    }
    
    section[data-testid="stSidebar"] {
        background-color: #f8fafc;
        border-left: 1px solid #e2e8f0;
    }
    
    div[data-testid="stDataFrame"] div {
        direction: rtl !important;
        text-align: right !important;
    }

    .main-header {
        background: linear-gradient(135deg, #1B4D3E 0%, #2C5E4F 100%);
        color: white;
        padding: 20px;
        border-radius: 12px;
        text-align: center;
        margin-bottom: 25px;
    }
    .main-header h2 {
        color: #ffffff !important;
        margin: 0;
        font-weight: 800;
    }

    .printable-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        border-bottom: 3px solid #1B4D3E;
        padding-bottom: 15px;
        margin-bottom: 20px;
    }
    .printable-header .logo-box { text-align: right; }
    .printable-header .title-box { text-align: center; }
    .printable-header .meta-box { text-align: left; }
</style>
""", unsafe_allow_html=True)

# --- DATABASE SETUP & SAFE AUTO-MIGRATION ---
DB_FILE = "donations_system_v2.db"
def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    
    # 1. إنشاء الجداول الأساسية
    c.execute("CREATE TABLE IF NOT EXISTS categories (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT UNIQUE NOT NULL)")
    c.execute("CREATE TABLE IF NOT EXISTS subcategories (id INTEGER PRIMARY KEY AUTOINCREMENT, category_name TEXT NOT NULL, name TEXT NOT NULL)")
    c.execute("CREATE TABLE IF NOT EXISTS donors (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL, project TEXT NOT NULL, category TEXT NOT NULL, support_type TEXT NOT NULL, monthly_expected REAL DEFAULT 0, annual_expected REAL DEFAULT 0, method TEXT NOT NULL, phone TEXT, notes TEXT)")
    c.execute("CREATE TABLE IF NOT EXISTS receipts (id INTEGER PRIMARY KEY AUTOINCREMENT, date TEXT NOT NULL, date_hijri TEXT, donor_id INTEGER, donor_name TEXT, project TEXT, category TEXT, amount REAL NOT NULL, month TEXT NOT NULL, year INTEGER DEFAULT 2026)")
    c.execute("CREATE TABLE IF NOT EXISTS expenses (id INTEGER PRIMARY KEY AUTOINCREMENT, date TEXT NOT NULL, date_hijri TEXT, beneficiary TEXT NOT NULL, category TEXT NOT NULL, amount REAL NOT NULL, notes TEXT, year INTEGER DEFAULT 2026)")
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

    # 2. فحص وإضافة العمود المفقود في الجداول القديمة لتجنب خطأ DatabaseError
    def ensure_column_exists(table_name, column_name, column_type):
        c.execute(f"PRAGMA table_info({table_name})")
        columns = [row[1] for row in c.fetchall()]
        if column_name not in columns:
            c.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_type}")

    ensure_column_exists("donors", "subcategory", "TEXT DEFAULT 'عام'")
    ensure_column_exists("receipts", "subcategory", "TEXT DEFAULT 'عام'")
    ensure_column_exists("expenses", "subcategory", "TEXT DEFAULT 'عام'")

    # 3. القيم الافتراضية للبنود
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

# --- SIDEBAR MENU ---
with st.sidebar:
    st.image("https://img.icons8.com/isometric-folders/100/mosque.png", width=60)
    st.title("🕌 وقف الإرتقاء")
    
    with st.expander("📂 **قائمة أجزاء النظام (إضغط للفتح)**", expanded=True):
        choice = st.radio(
            "اختر الشاشة:",
            [
                "📊 لوحة التحكم المباشرة",
                "➕ إضافة وتعديل الداعمين",
                "🎯 كفالات وتوزيع دعم الداعمين",
                "🛠️ إدارة وتعريف وتعديل العناصر",
                "📥 تسجيل وتعديل المقبوضات",
                "💸 تسجيل وتعديل المصروفات",
                "🗓️ جدول متابعة الأشهر والسنوات",
                "📱 مركز تذكير الواتساب",
                "🖨️ التقارير والطباعة الرسمية"
            ],
            label_visibility="collapsed"
        )

# --- HEADER ---
st.markdown("""
<div class='main-header'>
    <h2>🕌 وقف الإرتقاء الخيري</h2>
    <p>نظام إدارة المقبوضات والمصروفات والداعمين والكفالات</p>
</div>
""", unsafe_allow_html=True)

# --- 1. DASHBOARD ---
if choice == "📊 لوحة التحكم المباشرة":
    st.subheader("📊 لوحة التحكم والتحليل المالي")
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
    col4.metric("عدد الداعمين", f"{len(donors_df)}")
    
    st.divider()
    st.write(f"**📈 ملخص الميزانية حسب البنود لسنة {selected_dash_year}**")
    
    summary_data = []
    for cat in categories_df['name']:
        cat_inc = receipts_df[receipts_df['category'] == cat]['amount'].sum() if not receipts_df.empty else 0.0
        cat_exp = expenses_df[expenses_df['category'] == cat]['amount'].sum() if not expenses_df.empty else 0.0
        summary_data.append({
            "البند الرئيسي": cat,
            "إجمالي المقبوضات": f"{cat_inc:,.2f} ر.س",
            "إجمالي المصروفات": f"{cat_exp:,.2f} ر.س",
            "المتبقي (الصافي)": f"{cat_inc - cat_exp:,.2f} ر.س"
        })
    st.dataframe(pd.DataFrame(summary_data), use_container_width=True)

# --- 2. DONORS MANAGEMENT ---
elif choice == "➕ إضافة وتعديل الداعمين":
    st.subheader("👥 دليل وتخصيص الداعمين (إضافة - تعديل - حذف)")
    
    tab_add_d, tab_edit_d = st.tabs(["➕ إضافة داعم جديد", "✏️ تعديل وحذف بيانات داعم"])
    conn = get_connection()
    cats = pd.read_sql("SELECT name FROM categories", conn)['name'].tolist()
    if not cats: cats = ["رواتب"]
    
    projects_options = get_projects_list() + ["➕ إضافة حلقة جديدة..."]

    with tab_add_d:
        st.write("### ➕ تسجيل بيانات داعم جديد")
        
        col1, col2 = st.columns(2)
        d_name = col1.text_input("اسم الداعم الكامل")
        d_project_sel = col2.selectbox("الحلقة / المشروع المخصص", projects_options)
        
        final_project = d_project_sel
        if d_project_sel == "➕ إضافة حلقة جديدة...":
            new_p_input = col2.text_input("📝 اكتب اسم الحلقة الجديدة لتسجيلها:")
            if new_p_input:
                final_project = new_p_input.strip()

        d_cat = col1.selectbox("البند الرئيسي", cats)
        d_subcat = col2.selectbox("البند الفرعي", get_subcategories(d_cat))
        d_type = col1.selectbox("حالة الدعم", ["مستمر", "منقطع / مقطوع"])
        
        monthly_exp = 0.0
        if d_type == "مستمر":
            monthly_exp = col2.number_input("المبلغ الشهري المتوقع (ر.س)", min_value=0.0, value=500.0)
        
        d_method = col1.selectbox("طريقة الدعم", ["تحويل بنكي", "نقدي", "مسبق", "لاحق"])
        d_phone = col2.text_input("رقم الواتساب (مثال: 966500000000)")
        d_notes = st.text_area("ملاحظات أخرى")
        
        if st.button("💾 حفظ الداعم في النظام") and d_name:
            c = conn.cursor()
            if d_project_sel == "➕ إضافة حلقة جديدة..." and final_project:
                c.execute("INSERT OR IGNORE INTO projects (name, notes) VALUES (?, ?)", (final_project, "أضيفت من شاشة الداعمين"))
                conn.commit()

            c.execute("INSERT INTO donors (name, project, category, subcategory, support_type, monthly_expected, annual_expected, method, phone, notes) VALUES (?,?,?,?,?,?,?,?,?,?)",
                      (d_name, final_project, d_cat, d_subcat, d_type, monthly_exp, monthly_exp*12, d_method, d_phone, d_notes))
            conn.commit()
            st.success("تم إضافة الداعم وحفظ البيانات بنجاح!")
            st.rerun()

    with tab_edit_d:
        st.write("### ✏️ تعديل أو حذف داعم مسجل")
        donors_df_all = pd.read_sql("SELECT * FROM donors", conn)
        if donors_df_all.empty:
            st.warning("لا يوجد داعمين مسجلين حالياً.")
        else:
            donor_to_edit = st.selectbox("اختر الداعم للتعامل معه:", donors_df_all['name'].tolist())
            d_data = donors_df_all[donors_df_all['name'] == donor_to_edit].iloc[0]
            
            with st.form("edit_donor_form"):
                col1, col2 = st.columns(2)
                ed_name = col1.text_input("اسم الداعم", value=d_data['name'])
                
                cur_proj_list = get_projects_list()
                p_idx = cur_proj_list.index(d_data['project']) if d_data['project'] in cur_proj_list else 0
                ed_project = col2.selectbox("الحلقة / المشروع", cur_proj_list, index=p_idx)
                
                ed_cat = col1.selectbox("البند الرئيسي", cats, index=cats.index(d_data['category']) if d_data['category'] in cats else 0)
                ed_subcat = col2.selectbox("البند الفرعي", get_subcategories(ed_cat))
                ed_type = col1.selectbox("حالة الدعم", ["مستمر", "منقطع / مقطوع"], index=0 if "مستمر" in d_data['support_type'] else 1)
                ed_monthly = col1.number_input("المبلغ الشهري المتوقع", value=float(d_data['monthly_expected']))
                ed_phone = col2.text_input("رقم الواتساب", value=str(d_data['phone'] or ''))
                ed_notes = st.text_area("ملاحظات", value=str(d_data['notes'] or ''))
                
                b1, b2 = st.columns(2)
                if b1.form_submit_button("✏️ تحديث بيانات الداعم"):
                    c = conn.cursor()
                    c.execute("UPDATE donors SET name=?, project=?, category=?, subcategory=?, support_type=?, monthly_expected=?, annual_expected=?, phone=?, notes=? WHERE id=?",
                              (ed_name, ed_project, ed_cat, ed_subcat, ed_type, ed_monthly, ed_monthly*12, ed_phone, ed_notes, int(d_data['id'])))
                    conn.commit()
                    st.success("تم تحديث الداعم!")
                    st.rerun()
                if b2.form_submit_button("🗑️ حذف الداعم نهائياً"):
                    c = conn.cursor()
                    c.execute("DELETE FROM donors WHERE id=?", (int(d_data['id']),))
                    c.execute("DELETE FROM donor_allocations WHERE donor_id=?", (int(d_data['id']),))
                    conn.commit()
                    st.warning("تم حذف الداعم.")
                    st.rerun()

    st.divider()
    st.write("### 📋 قائمة الداعمين المسجلين بالكامل:")
    df_show = pd.read_sql("SELECT name as 'اسم الداعم', project as 'الحلقة المخصصة', category as 'البند الرئيسي', subcategory as 'البند الفرعي', support_type as 'حالة الدعم', monthly_expected as 'المبلغ الشهري', phone as 'الهاتف', notes as 'الملاحظات' FROM donors", conn)
    st.dataframe(df_show, use_container_width=True)
    conn.close()

# --- 3. ALLOCATIONS SYSTEM ---
elif choice == "🎯 كفالات وتوزيع دعم الداعمين":
    st.subheader("🎯 توزيع كفالات ودعم الداعمين (ربط الداعم بالمعلمين والإداريين)")
    
    conn = get_connection()
    donors_df = pd.read_sql("SELECT * FROM donors", conn)
    teachers_list = pd.read_sql("SELECT name FROM teachers", conn)['name'].tolist()
    staff_list = pd.read_sql("SELECT name FROM staff", conn)['name'].tolist()
    
    if donors_df.empty:
        st.warning("يرجى إدخال داعمين أولاً.")
    else:
        st.write("### 📌 إضافة / تخصيص رعاية جديدة")
        with st.form("add_alloc_form"):
            col1, col2 = st.columns(2)
            sel_d_name = col1.selectbox("اختر الداعم:", donors_df['name'].tolist())
            d_info = donors_df[donors_df['name'] == sel_d_name].iloc[0]
            
            alloc_existing = pd.read_sql("SELECT SUM(allocated_amount) as sum_a FROM donor_allocations WHERE donor_id=?", conn, params=(int(d_info['id']),))
            allocated_so_far = alloc_existing['sum_a'].iloc[0] if alloc_existing['sum_a'].iloc[0] else 0.0
            remaining_unalloc = float(d_info['monthly_expected']) - allocated_so_far
            
            st.info(f"💡 إجمالي دعم الداعم ({sel_d_name}): **{d_info['monthly_expected']} ر.س** | المُوزّع حالياً: **{allocated_so_far} ر.س** | المتبقي غير الموزع: **{remaining_unalloc} ر.س**")
            
            b_type = col1.selectbox("جهة التخصيص:", ["معلم", "إداري"])
            b_list = teachers_list if b_type == "معلم" else staff_list
            
            if not b_list:
                st.error(f"لا يوجد {b_type}ين مسجلين في النظام. أضفهم أولاً من صفحة التعريفات.")
                target_ben = None
            else:
                target_ben = col2.selectbox(f"اختر الـ {b_type}:", b_list)
            
            alloc_amt = col2.number_input("المبلغ المخصص شهرياً (ر.س)", min_value=1.0, value=remaining_unalloc if remaining_unalloc > 0 else 500.0)
            alloc_notes = st.text_area("ملاحظات / بيان التخصيص")
            
            if st.form_submit_button("💾 حفظ تخصيص الدعم") and target_ben:
                c = conn.cursor()
                c.execute("INSERT INTO donor_allocations (donor_id, donor_name, beneficiary_type, beneficiary_name, allocated_amount, notes) VALUES (?,?,?,?,?,?)",
                          (int(d_info['id']), d_info['name'], b_type, target_ben, alloc_amt, alloc_notes))
                conn.commit()
                st.success("تم تخصيص المبلغ بنجاح!")
                st.rerun()

    st.divider()
    
    st.write("### 🔍 كشف التغطيات والرعايات المسجلة")
    v_tab1, v_tab2 = st.tabs(["📊 حسب المعلم / الإداري", "👤 حسب الداعم"])
    
    with v_tab1:
        all_bens = teachers_list + staff_list
        if all_bens:
            sel_target_ben = st.selectbox("اختر المعلم أو الإداري لرؤية داعميه:", all_bens)
            ben_alloc_df = pd.read_sql("SELECT donor_name as 'اسم الداعم', beneficiary_type as 'الجهة', allocated_amount as 'المبلغ المخصص (ر.س)', notes as 'ملاحظات' FROM donor_allocations WHERE beneficiary_name=?", conn, params=(sel_target_ben,))
            
            tot_covered = ben_alloc_df['المبلغ المخصص (ر.س)'].sum() if not ben_alloc_df.empty else 0.0
            st.metric(f"إجمالي الدعم المغطى لـ ({sel_target_ben})", f"{tot_covered:,.2f} ر.س")
            st.dataframe(ben_alloc_df, use_container_width=True)
            
    with v_tab2:
        all_alloc_df = pd.read_sql("SELECT donor_name as 'الداعم', beneficiary_type as 'نوع المستفيد', beneficiary_name as 'المستفيد (المعلم/الإداري)', allocated_amount as 'المبلغ المخصص (ر.س)', notes as 'ملاحظات' FROM donor_allocations", conn)
        st.dataframe(all_alloc_df, use_container_width=True)

    conn.close()

# --- 4. MANAGEMENT OF OTHER ENTITIES ---
elif choice == "🛠️ إدارة وتعريف وتعديل العناصر":
    st.subheader("🛠️ مركز إضافة، تعديل، وحذف الحلقات والبنود والكوادر")
    
    tab_proj, tab_cats, tab_teach, tab_staff = st.tabs([
        "🕌 الحلقات والمشاريع", 
        "🏷️ البنود الرئيسية والفرعية", 
        "👨‍🏫 المعلمون", 
        "👔 الإداريون"
    ])
    
    conn = get_connection()
    cats = pd.read_sql("SELECT name FROM categories", conn)['name'].tolist()
    if not cats: cats = ["رواتب"]
    projects_list = get_projects_list()

    with tab_proj:
        st.write("### 🕌 إدارة الحلقات والمشاريع")
        c1, c2 = st.columns(2)
        with c1:
            st.write("**➕ إضافة حلقة جديدة:**")
            with st.form("add_proj_f"):
                p_name = st.text_input("اسم الحلقة / المشروع")
                p_notes = st.text_area("ملاحظات")
                if st.form_submit_button("حفظ الحلقة") and p_name:
                    try:
                        c = conn.cursor()
                        c.execute("INSERT INTO projects (name, notes) VALUES (?,?)", (p_name.strip(), p_notes))
                        conn.commit()
                        st.success("تم الإضافة!")
                        st.rerun()
                    except: st.error("الحلقة موجودة بالفعل.")

        with c2:
            st.write("**✏️ تعديل / 🗑️ حذف حلقة:**")
            projs_df = pd.read_sql("SELECT * FROM projects", conn)
            if not projs_df.empty:
                sel_p = st.selectbox("اختر الحلقة:", projs_df['name'].tolist(), key="p_edit_sel")
                p_data = projs_df[projs_df['name'] == sel_p].iloc[0]
                
                with st.form("edit_proj_f"):
                    new_p_name = st.text_input("اسم الحلقة المعدل", value=p_data['name'])
                    new_p_notes = st.text_area("الملاحظات المعدلة", value=str(p_data['notes'] or ''))
                    
                    b1, b2 = st.columns(2)
                    if b1.form_submit_button("تحديث"):
                        c = conn.cursor()
                        c.execute("UPDATE projects SET name=?, notes=? WHERE id=?", (new_p_name, new_p_notes, int(p_data['id'])))
                        conn.commit()
                        st.success("تم التعديل!")
                        st.rerun()
                    if b2.form_submit_button("حذف"):
                        c = conn.cursor()
                        c.execute("DELETE FROM projects WHERE id=?", (int(p_data['id']),))
                        conn.commit()
                        st.warning("تم الحذف!")
                        st.rerun()

        st.divider()
        st.dataframe(pd.read_sql("SELECT id as 'الرقم المرجعي', name as 'اسم الحلقة', notes as 'الملاحظات' FROM projects", conn), use_container_width=True)

    with tab_cats:
        st.write("### 🏷️ إدارة البنود الرئيسية والفرعية")
        col1, col2 = st.columns(2)
        with col1:
            st.write("**➕ إضافة بند رئيسي:**")
            new_cat = st.text_input("اسم البند الرئيسي الجديد")
            if st.button("حفظ الرئيسي") and new_cat:
                try:
                    c = conn.cursor()
                    c.execute("INSERT INTO categories (name) VALUES (?)", (new_cat.strip(),))
                    conn.commit()
                    st.success("تم الإضافة!")
                    st.rerun()
                except: st.error("البند موجود بالفعل.")
            
            st.divider()
            st.write("**✏️ تعديل / 🗑️ حذف بند رئيسي:**")
            edit_cat_target = st.selectbox("اختر البند للتحرير:", cats, key="cat_target")
            renamed_cat = st.text_input("الاسم الجديد للبند الرئيسي:", value=edit_cat_target)
            
            cb1, cb2 = st.columns(2)
            if cb1.button("تحديث البند الرئيسي"):
                c = conn.cursor()
                c.execute("UPDATE categories SET name=? WHERE name=?", (renamed_cat, edit_cat_target))
                c.execute("UPDATE subcategories SET category_name=? WHERE category_name=?", (renamed_cat, edit_cat_target))
                conn.commit()
                st.success("تم التحديث!")
                st.rerun()
            if cb2.button("حذف البند الرئيسي"):
                c = conn.cursor()
                c.execute("DELETE FROM categories WHERE name=?", (edit_cat_target,))
                c.execute("DELETE FROM subcategories WHERE category_name=?", (edit_cat_target,))
                conn.commit()
                st.warning("تم الحذف!")
                st.rerun()

        with col2:
            st.write("**➕ إضافة بند فرعي:**")
            parent_cat = st.selectbox("البند الرئيسي الأب", cats, key="parent_c")
            new_subcat = st.text_input("اسم البند الفرعي الجديد")
            if st.button("حفظ الفرعي") and new_subcat:
                c = conn.cursor()
                c.execute("INSERT INTO subcategories (category_name, name) VALUES (?,?)", (parent_cat, new_subcat.strip()))
                conn.commit()
                st.success("تم الإضافة!")
                st.rerun()

        st.divider()
        st.dataframe(pd.read_sql("SELECT category_name as 'البند الرئيسي', name as 'البند الفرعي' FROM subcategories", conn), use_container_width=True)

    with tab_teach:
        st.write("### 👨‍🏫 إدارة المعلمين")
        c1, c2 = st.columns(2)
        with c1:
            st.write("**➕ إضافة معلم جديد:**")
            with st.form("add_teach_f"):
                t_name = st.text_input("اسم المعلم")
                t_phone = st.text_input("رقم التواصل")
                t_salary = st.number_input("الراتب الشهري (ر.س)", min_value=0.0, value=1500.0)
                t_project = st.selectbox("الحلقة المكلّف بها", projects_list)
                if st.form_submit_button("حفظ المعلم") and t_name:
                    c = conn.cursor()
                    c.execute("INSERT INTO teachers (name, phone, salary, project) VALUES (?,?,?,?)", (t_name, t_phone, t_salary, t_project))
                    conn.commit()
                    st.success("تم التسجيل!")
                    st.rerun()

        with c2:
            st.write("**✏️ تعديل / 🗑️ حذف معلم:**")
            teach_df = pd.read_sql("SELECT * FROM teachers", conn)
            if not teach_df.empty:
                sel_t = st.selectbox("اختر المعلم:", teach_df['name'].tolist(), key="t_edit_sel")
                t_data = teach_df[teach_df['name'] == sel_t].iloc[0]
                
                with st.form("edit_teach_f"):
                    ed_t_name = st.text_input("اسم المعلم", value=t_data['name'])
                    ed_t_phone = st.text_input("الهاتف", value=str(t_data['phone'] or ''))
                    ed_t_salary = st.number_input("الراتب الشهري", value=float(t_data['salary']))
                    ed_t_proj = st.selectbox("الحلقة", projects_list, index=projects_list.index(t_data['project']) if t_data['project'] in projects_list else 0)
                    
                    tb1, tb2 = st.columns(2)
                    if tb1.form_submit_button("تحديث"):
                        c = conn.cursor()
                        c.execute("UPDATE teachers SET name=?, phone=?, salary=?, project=? WHERE id=?", (ed_t_name, ed_t_phone, ed_t_salary, ed_t_proj, int(t_data['id'])))
                        conn.commit()
                        st.success("تم التعديل!")
                        st.rerun()
                    if tb2.form_submit_button("حذف"):
                        c = conn.cursor()
                        c.execute("DELETE FROM teachers WHERE id=?", (int(t_data['id']),))
                        conn.commit()
                        st.warning("تم الحذف!")
                        st.rerun()

        st.divider()
        st.dataframe(pd.read_sql("SELECT name as 'اسم المعلم', phone as 'الهاتف', salary as 'الراتب (ر.س)', project as 'الحلقة المكلّف بها' FROM teachers", conn), use_container_width=True)

    with tab_staff:
        st.write("### 👔 إدارة الإداريين")
        c1, c2 = st.columns(2)
        with c1:
            st.write("**➕ إضافة إداري جديد:**")
            with st.form("add_staff_f"):
                s_name = st.text_input("اسم الإداري")
                s_role = st.text_input("المسمى الوظيفي")
                s_phone = st.text_input("رقم الجوال")
                s_salary = st.number_input("الراتب الشهري (ر.س)", min_value=0.0, value=2500.0)
                if st.form_submit_button("حفظ الإداري") and s_name:
                    c = conn.cursor()
                    c.execute("INSERT INTO staff (name, phone, role, salary) VALUES (?,?,?,?)", (s_name, s_phone, s_role, s_salary))
                    conn.commit()
                    st.success("تم التسجيل!")
                    st.rerun()

        with c2:
            st.write("**✏️ تعديل / 🗑️ حذف إداري:**")
            staff_df = pd.read_sql("SELECT * FROM staff", conn)
            if not staff_df.empty:
                sel_s = st.selectbox("اختر الإداري:", staff_df['name'].tolist(), key="s_edit_sel")
                s_data = staff_df[staff_df['name'] == sel_s].iloc[0]
                
                with st.form("edit_staff_f"):
                    ed_s_name = st.text_input("الاسم", value=s_data['name'])
                    ed_s_role = st.text_input("المسمى الوظيفي", value=s_data['role'])
                    ed_s_phone = st.text_input("الهاتف", value=str(s_data['phone'] or ''))
                    ed_s_salary = st.number_input("الراتب", value=float(s_data['salary']))
                    
                    sb1, sb2 = st.columns(2)
                    if sb1.form_submit_button("تحديث"):
                        c = conn.cursor()
                        c.execute("UPDATE staff SET name=?, role=?, phone=?, salary=? WHERE id=?", (ed_s_name, ed_s_role, ed_s_phone, ed_s_salary, int(s_data['id'])))
                        conn.commit()
                        st.success("تم التعديل!")
                        st.rerun()
                    if sb2.form_submit_button("حذف"):
                        c = conn.cursor()
                        c.execute("DELETE FROM staff WHERE id=?", (int(s_data['id']),))
                        conn.commit()
                        st.warning("تم الحذف!")
                        st.rerun()

        st.divider()
        st.dataframe(pd.read_sql("SELECT name as 'اسم الإداري', role as 'الوظيفة/المسمى', phone as 'الهاتف', salary as 'الراتب (ر.س)' FROM staff", conn), use_container_width=True)

    conn.close()

# --- 5. RECEIPTS ---
elif choice == "📥 تسجيل وتعديل المقبوضات":
    st.subheader("📥 تسجيل وإدارة المقبوضات")
    conn = get_connection()
    donors_df = pd.read_sql("SELECT * FROM donors", conn)
    cats = pd.read_sql("SELECT name FROM categories", conn)['name'].tolist()
    if not cats: cats = ["رواتب"]

    if donors_df.empty:
        st.warning("يرجى إضافة داعمين أولاً.")
    else:
        selected_donor = st.selectbox("اختر الداعم:", donors_df['name'].tolist())
        donor_info = donors_df[donors_df['name'] == selected_donor].iloc[0]
        
        with st.form("receipt_form"):
            c1, c2 = st.columns(2)
            r_cat = c1.selectbox("البند الرئيسي", cats, index=cats.index(donor_info['category']) if donor_info['category'] in cats else 0)
            r_subcat = c2.selectbox("البند الفرعي", get_subcategories(r_cat))

            c3, c4 = st.columns(2)
            r_amount = c3.number_input("المبلغ (ر.س)", min_value=1.0, value=float(donor_info['monthly_expected']) if donor_info['monthly_expected'] > 0 else 1000.0)
            r_date = c4.date_input("التاريخ", datetime.date.today())
            hijri_str = get_hijri_str(r_date)

            c5, c6 = st.columns(2)
            r_month = c5.selectbox("الشهر", MONTHS, index=datetime.datetime.now().month - 1)
            r_year = c6.selectbox("السنة", YEARS_LIST, index=YEARS_LIST.index(r_date.year) if r_date.year in YEARS_LIST else 2)
            
            if st.form_submit_button("تسجيل المقبوضات ✅"):
                c = conn.cursor()
                c.execute("INSERT INTO receipts (date, date_hijri, donor_id, donor_name, project, category, subcategory, amount, month, year) VALUES (?,?,?,?,?,?,?,?,?,?)",
                          (str(r_date), hijri_str, donor_info['id'], donor_info['name'], donor_info['project'], r_cat, r_subcat, r_amount, r_month, int(r_year)))
                conn.commit()
                st.success("تم تسجيل العملية بنجاح!")
                st.rerun()

    st.divider()
    receipts_df = pd.read_sql("SELECT id as 'رقم السند', date as 'التاريخ', date_hijri as 'التاريخ الهجري', donor_name as 'اسم الداعم', project as 'الحلقة', category as 'البند الرئيسي', subcategory as 'البند الفرعي', amount as 'المبلغ (ر.س)', month as 'الشهر', year as 'السنة' FROM receipts ORDER BY id DESC", conn)
    conn.close()
    st.dataframe(receipts_df, use_container_width=True)

# --- 6. EXPENSES ---
elif choice == "💸 تسجيل وتعديل المصروفات":
    st.subheader("💸 تسجيل وإدارة المصروفات")
    conn = get_connection()
    cats = pd.read_sql("SELECT name FROM categories", conn)['name'].tolist()
    if not cats: cats = ["رواتب"]

    with st.form("expense_form"):
        col1, col2 = st.columns(2)
        exp_date = col1.date_input("التاريخ", datetime.date.today())
        exp_beneficiary = col2.text_input("المستفيد / الجهة")
        
        exp_cat = col1.selectbox("البند الرئيسي", cats)
        exp_subcat = col2.selectbox("البند الفرعي", get_subcategories(exp_cat))

        c1, c2, c3 = st.columns([1, 2, 1])
        exp_amount = c1.number_input("المبلغ (ر.س)", min_value=1.0, value=500.0)
        exp_notes = c2.text_input("البيان")
        exp_year = c3.selectbox("السنة", YEARS_LIST, index=YEARS_LIST.index(exp_date.year) if exp_date.year in YEARS_LIST else 2)
        
        if st.form_submit_button("تسجيل المصروف 💸") and exp_beneficiary:
            c = conn.cursor()
            c.execute("INSERT INTO expenses (date, date_hijri, beneficiary, category, subcategory, amount, notes, year) VALUES (?,?,?,?,?,?,?,?)",
                      (str(exp_date), get_hijri_str(exp_date), exp_beneficiary, exp_cat, exp_subcat, exp_amount, exp_notes, int(exp_year)))
            conn.commit()
            st.success("تم تسجيل المصروف!")
            st.rerun()

    expenses_df = pd.read_sql("SELECT id as 'رقم السند', date as 'التاريخ', date_hijri as 'التاريخ الهجري', beneficiary as 'المستفيد', category as 'البند الرئيسي', subcategory as 'البند الفرعي', amount as 'المبلغ (ر.س)', notes as 'البيان', year as 'السنة' FROM expenses ORDER BY id DESC", conn)
    conn.close()
    st.dataframe(expenses_df, use_container_width=True)

# --- 7. MONTHLY TRACKING ---
elif choice == "🗓️ جدول متابعة الأشهر والسنوات":
    st.subheader("🗓️ جدول متابعة التزامات الداعمين")
    selected_matrix_year = st.selectbox("📅 اختر السنة:", YEARS_LIST, index=YEARS_LIST.index(2026))

    conn = get_connection()
    donors_df = pd.read_sql("SELECT * FROM donors", conn)
    receipts_df = pd.read_sql("SELECT * FROM receipts WHERE year = ?", conn, params=(selected_matrix_year,))
    conn.close()
    
    if not donors_df.empty:
        matrix_rows = []
        for _, d in donors_df.iterrows():
            row = {"اسم الداعم": d['name'], "الحلقة": d['project'], "البند الرئيسي": d['category']}
            for m in MONTHS:
                if "منقطع" in str(d['support_type']):
                    row[m] = "⚪"
                else:
                    paid = not receipts_df[(receipts_df['donor_id'] == d['id']) & (receipts_df['month'] == m)].empty
                    row[m] = "✅" if paid else "🚨"
            matrix_rows.append(row)
        st.dataframe(pd.DataFrame(matrix_rows), use_container_width=True)

# --- 8. WHATSAPP REMINDERS ---
elif choice == "📱 مركز تذكير الواتساب":
    st.subheader("📱 إرسال تذكيرات الواتساب للداعمين")
    c1, c2 = st.columns(2)
    selected_month = c1.selectbox("اختر الشهر", MONTHS, index=datetime.datetime.now().month - 1)
    selected_wa_year = c2.selectbox("اختر السنة", YEARS_LIST, index=YEARS_LIST.index(2026))

    conn = get_connection()
    donors_df = pd.read_sql("SELECT * FROM donors WHERE support_type LIKE '%مستمر%'", conn)
    receipts_df = pd.read_sql("SELECT * FROM receipts WHERE month=? AND year=?", conn, params=(selected_month, selected_wa_year))
    conn.close()
    
    if not donors_df.empty:
        for _, d in donors_df.iterrows():
            paid = not receipts_df[receipts_df['donor_id'] == d['id']].empty
            if not paid:
                phone = str(d['phone']).replace("+", "").replace(" ", "")
                msg = f"السلام عليكم ورحمة الله وبركاته، الأخ/ {d['name']}، نود تذكيركم بدعم شهر ({selected_month}) لسنة ({selected_wa_year}) المخصص لـ ({d['project']}) - وقف الإرتقاء الخيري."
                wa_url = f"https://wa.me/{phone}?text={urllib.parse.quote(msg)}"
                
                col_a, col_b = st.columns([3, 1])
                col_a.write(f"👤 **{d['name']}** - ({d['project']})")
                col_b.markdown(f"[📲 إرسال واتساب]({wa_url})", unsafe_allow_html=True)

# --- 9. PRINTABLE REPORTS ---
elif choice == "🖨️ التقارير والطباعة الرسمية":
    st.subheader("🖨️ التقارير المالية الرسمية والطباعة")
    
    conn = get_connection()
    donors_list = pd.read_sql("SELECT name FROM donors", conn)['name'].tolist()
    projects_list = get_projects_list()
    categories_list = pd.read_sql("SELECT name FROM categories", conn)['name'].tolist()
    
    col1, col2, col3 = st.columns(3)
    
    rep_type = col1.selectbox("نوع التقرير:", ["إجمالي الميزانية (المقبوضات والمصروفات)", "تقرير داعم معين", "تقرير حلقة/مشروع معين", "تقرير بند معين"])
    rep_period = col2.selectbox("الفترة الزمنية:", ["سنوي شامل", "شهري", "ربع سنوي (Q1-Q4)", "نصف سنوي"])
    rep_year = col3.selectbox("السنة المالية:", YEARS_LIST, index=YEARS_LIST.index(2026))
    
    target_filter = None
    if rep_type == "تقرير داعم معين":
        target_filter = st.selectbox("اختر الداعم:", donors_list if donors_list else ["لا يوجد"])
    elif rep_type == "تقرير حلقة/مشروع معين":
        target_filter = st.selectbox("اختر الحلقة:", projects_list)
    elif rep_type == "تقرير بند معين":
        target_filter = st.selectbox("اختر البند:", categories_list if categories_list else ["رواتب"])

    months_filter = MONTHS
    if rep_period == "شهري":
        m_selected = st.selectbox("اختر الشهر:", MONTHS)
        months_filter = [m_selected]
    elif rep_period == "ربع سنوي (Q1-Q4)":
        q_selected = st.selectbox("اختر الربع:", ["الربع الأول (يناير - مارس)", "الربع الثاني (أبريل - يونيو)", "الربع الثالث (يوليو - سبتمبر)", "الربع الرابع (أكتوبر - ديسمبر)"])
        if "الأول" in q_selected: months_filter = MONTHS[0:3]
        elif "الثاني" in q_selected: months_filter = MONTHS[3:6]
        elif "الثالث" in q_selected: months_filter = MONTHS[6:9]
        else: months_filter = MONTHS[9:12]
    elif rep_period == "نصف سنوي":
        h_selected = st.selectbox("اختر النصف:", ["النصف الأول (يناير - يونيو)", "النصف الثاني (يوليو - ديسمبر)"])
        months_filter = MONTHS[0:6] if "الأول" in h_selected else MONTHS[6:12]

    receipts_df = pd.read_sql("SELECT * FROM receipts WHERE year=?", conn, params=(rep_year,))
    expenses_df = pd.read_sql("SELECT * FROM expenses WHERE year=?", conn, params=(rep_year,))
    conn.close()

    if not receipts_df.empty:
        receipts_df = receipts_df[receipts_df['month'].isin(months_filter)]
        if rep_type == "تقرير داعم معين" and target_filter:
            receipts_df = receipts_df[receipts_df['donor_name'] == target_filter]
        elif rep_type == "تقرير حلقة/مشروع معين" and target_filter:
            receipts_df = receipts_df[receipts_df['project'] == target_filter]
        elif rep_type == "تقرير بند معين" and target_filter:
            receipts_df = receipts_df[receipts_df['category'] == target_filter]

    if not expenses_df.empty:
        if rep_type == "تقرير حلقة/مشروع معين" and target_filter:
            expenses_df = pd.DataFrame()
        elif rep_type == "تقرير بند معين" and target_filter:
            expenses_df = expenses_df[expenses_df['category'] == target_filter]

    st.divider()

    st.markdown(f"""
    <div class="printable-header">
        <div class="logo-box">
            <img src="https://img.icons8.com/isometric-folders/100/mosque.png" width="70"><br>
            <strong>وقف الإرتقاء الخيري</strong>
        </div>
        <div class="title-box">
            <h2>📄 {rep_type}</h2>
            <p><strong>الفترة:</strong> {rep_period} | <strong>السنة المالية:</strong> {rep_year}</p>
        </div>
        <div class="meta-box">
            <p><strong>تاريخ الطباعة:</strong> {datetime.date.today()}</p>
            <p><strong>التاريخ الهجري:</strong> {get_hijri_str(datetime.date.today())}</p>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    tot_rec = receipts_df['amount'].sum() if not receipts_df.empty else 0.0
    tot_exp = expenses_df['amount'].sum() if not expenses_df.empty else 0.0
    
    m1, m2, m3 = st.columns(3)
    m1.metric("إجمالي المقبوضات للفترة", f"{tot_rec:,.2f} ر.س")
    m2.metric("إجمالي المصروفات للفترة", f"{tot_exp:,.2f} ر.س")
    m3.metric("الصافي المتبقي", f"{tot_rec - tot_exp:,.2f} ر.س")

    rec_renamed = receipts_df.rename(columns={
        "id": "رقم السند", "date": "التاريخ", "date_hijri": "التاريخ الهجري", 
        "donor_name": "اسم الداعم", "project": "الحلقة/المشروع", "category": "البند الرئيسي",
        "subcategory": "البند الفرعي", "amount": "المبلغ (ر.س)", "month": "الشهر", "year": "السنة"
    })
    
    exp_renamed = expenses_df.rename(columns={
        "id": "رقم السند", "date": "التاريخ", "date_hijri": "التاريخ الهجري", 
        "beneficiary": "المستفيد", "category": "البند الرئيسي",
        "subcategory": "البند الفرعي", "amount": "المبلغ (ر.س)", "notes": "البيان", "year": "السنة"
    })

    st.write("### 📄 تفاصيل حركة المقبوضات")
    st.dataframe(rec_renamed, use_container_width=True)
    
    st.write("### 💸 تفاصيل حركة المصروفات")
    st.dataframe(exp_renamed, use_container_width=True)

    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        rec_renamed.to_excel(writer, sheet_name='المقبوضات', index=False)
        exp_renamed.to_excel(writer, sheet_name='المصروفات', index=False)
    
    st.download_button(
        label="📥 تصدير هذا التقرير إلى Excel",
        data=output.getvalue(),
        file_name=f"Report_{rep_year}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
