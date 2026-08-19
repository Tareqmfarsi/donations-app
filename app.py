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

# --- STYLING (CSS) ---
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Cairo:wght@400;600;700;800&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Cairo', sans-serif;
        direction: rtl;
        text-align: right;
    }
    
    /* Sidebar Styling */
    section[data-testid="stSidebar"] {
        background-color: #f8fafc;
        border-left: 1px solid #e2e8f0;
    }
    
    /* Header Styling */
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
    .main-header p {
        margin: 5px 0 0 0;
        opacity: 0.9;
    }
    
    /* Card Container */
    .card {
        background-color: white;
        padding: 20px;
        border-radius: 10px;
        border: 1px solid #e2e8f0;
        margin-bottom: 15px;
    }
</style>
""", unsafe_allow_html=True)

# --- DATABASE AUTO-MIGRATION SETUP ---
DB_FILE = "donations_system.db"

def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    
    # Create tables
    c.execute("CREATE TABLE IF NOT EXISTS categories (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT UNIQUE NOT NULL)")
    c.execute("CREATE TABLE IF NOT EXISTS subcategories (id INTEGER PRIMARY KEY AUTOINCREMENT, category_name TEXT NOT NULL, name TEXT NOT NULL)")
    c.execute("CREATE TABLE IF NOT EXISTS donors (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL, project TEXT NOT NULL, category TEXT NOT NULL, subcategory TEXT DEFAULT 'عام', support_type TEXT NOT NULL, monthly_expected REAL DEFAULT 0, annual_expected REAL DEFAULT 0, method TEXT NOT NULL, phone TEXT, notes TEXT)")
    c.execute("CREATE TABLE IF NOT EXISTS receipts (id INTEGER PRIMARY KEY AUTOINCREMENT, date TEXT NOT NULL, date_hijri TEXT, donor_id INTEGER, donor_name TEXT, project TEXT, category TEXT, subcategory TEXT DEFAULT 'عام', amount REAL NOT NULL, month TEXT NOT NULL, year INTEGER DEFAULT 2026)")
    c.execute("CREATE TABLE IF NOT EXISTS expenses (id INTEGER PRIMARY KEY AUTOINCREMENT, date TEXT NOT NULL, date_hijri TEXT, beneficiary TEXT NOT NULL, category TEXT NOT NULL, subcategory TEXT DEFAULT 'عام', amount REAL NOT NULL, notes TEXT, year INTEGER DEFAULT 2026)")

    # Auto-fix missing columns if database exists from older versions
    tables = ['donors', 'receipts', 'expenses']
    for table in tables:
        c.execute(f"PRAGMA table_info({table})")
        cols = [col[1] for col in c.fetchall()]
        if 'subcategory' not in cols:
            c.execute(f"ALTER TABLE {table} ADD COLUMN subcategory TEXT DEFAULT 'عام'")
        if table in ['receipts', 'expenses'] and 'date_hijri' not in cols:
            c.execute(f"ALTER TABLE {table} ADD COLUMN date_hijri TEXT DEFAULT ''")
            
    # Default Categories
    c.execute("SELECT COUNT(*) FROM categories")
    if c.fetchone()[0] == 0:
        default_cats = [('رواتب',), ('البرامج والأنشطة',), ('الجوائز والتكريم',), ('دعومات أخرى',)]
        c.executemany("INSERT INTO categories (name) VALUES (?)", default_cats)
        
        default_subcats = [
            ('رواتب', 'رواتب المعلمين'),
            ('رواتب', 'رواتب الإداريين'),
            ('البرامج والأنشطة', 'برنامج رمضان لعام 1448 هـ'),
            ('الجوائز والتكريم', 'تكريم الحفاظ')
        ]
        c.executemany("INSERT INTO subcategories (category_name, name) VALUES (?,?)", default_subcats)
        
    conn.commit()
    conn.close()

init_db()

def get_connection():
    return sqlite3.connect(DB_FILE)

def get_hijri_str(dt):
    try:
        day, month, year = dt.day, dt.month, dt.year
        if month < 3:
            year -= 1
            month += 12
        a = math.floor(year / 100)
        b = 2 - a + math.floor(a / 4)
        jd = math.floor(365.25 * (year + 4716)) + math.floor(30.6001 * (month + 1)) + day + b - 1524.5
        z = jd - 1948439.5
        cyc = math.floor(z / 10631)
        z -= cyc * 10631
        hy = math.floor((z - 0.5) / 354.366)
        z -= math.floor(hy * 354.366 + 0.5)
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

MONTHS = ["يناير", "فبراير", "مارس", "أبريل", "مايو", "يونيو", "يوليو", "أغسطس", "سبتمبر", "أكتوبر", "نوفمبر", "ديسمبر"]
YEARS_LIST = list(range(2024, 2031))

# --- SIDEBAR NAVIGATION ---
with st.sidebar:
    st.image("https://img.icons8.com/isometric-folders/100/mosque.png", width=60)
    st.title("🕌 وقف الإرتقاء")
    
    # قائمة مطوية (Flyout/Collapsible Menu)
    with st.expander("📂 **قائمة أجزاء النظام (إضغط للفتح)**", expanded=True):
        choice = st.radio(
            "اختر الشاشة:",
            [
                "📊 لوحة التحكم المباشرة",
                "👥 دليل الداعمين وتعديل البيانات",
                "📥 تسجيل وتعديل المقبوضات",
                "💸 تسجيل وتعديل المصروفات",
                "🗓️ جدول متابعة الأشهر والسنوات",
                "📄 تقارير البنود المخصصة",
                "📱 مركز تذكير الواتساب",
                "🖨️ التقارير القابلة للطباعة والتصدير",
                "⚙️ إعدادات البنود الرئيسية والفرعية"
            ],
            label_visibility="collapsed"
        )
# --- HEADER ---
st.markdown("""
<div class='main-header'>
    <h2>🕌 وقف الإرتقاء الخيري</h2>
    <p>نظام إدارة المقبوضات والمصروفات والداعمين</p>
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
        bal = cat_inc - cat_exp
        cat_donors = len(donors_df[donors_df['category'] == cat]) if not donors_df.empty else 0
        
        summary_data.append({
            "البند الرئيسي": cat,
            "المقبوضات": f"{cat_inc:,.2f} ر.س",
            "المصروفات": f"{cat_exp:,.2f} ر.س",
            "المتبقي": f"{bal:,.2f} ر.س",
            "عدد الداعمين": cat_donors
        })
    st.dataframe(pd.DataFrame(summary_data), use_container_width=True)

# --- 2. DONORS DIRECTORY ---
elif choice == "👥 دليل الداعمين وتعديل البيانات":
    st.subheader("👥 دليل الداعمين")
    conn = get_connection()
    cats = pd.read_sql("SELECT name FROM categories", conn)['name'].tolist()
    if not cats: cats = ["رواتب"]

    tab1, tab2 = st.tabs(["➕ إضافة داعم جديد", "✏️ تعديل بيانات داعم"])
    
    with tab1:
        with st.form("add_donor_form"):
            col1, col2 = st.columns(2)
            d_name = col1.text_input("اسم الداعم")
            d_project = col2.text_input("الحلقة / المشروع المخصص")
            
            d_cat = col1.selectbox("البند الرئيسي", cats)
            d_subcat = col2.selectbox("البند الفرعي", get_subcategories(d_cat))
            d_type = col1.selectbox("حالة الدعم", ["مستمر", "منقطع / مقطوع"])
            
            monthly_exp = 0.0
            if d_type == "مستمر":
                monthly_exp = col2.number_input("المبلغ المتوقع شهرياً (ر.س)", min_value=0.0, value=500.0)
            
            d_method = col1.selectbox("طريقة الدعم", ["مسبق", "لاحق", "تحويل بنكي", "نقدي"])
            d_phone = col2.text_input("رقم الواتساب (مثال: 966500000000)")
            d_notes = st.text_area("ملاحظات")
            
            if st.form_submit_button("💾 حفظ البيانات") and d_name:
                c = conn.cursor()
                c.execute("INSERT INTO donors (name, project, category, subcategory, support_type, monthly_expected, annual_expected, method, phone, notes) VALUES (?,?,?,?,?,?,?,?,?,?)",
                          (d_name, d_project, d_cat, d_subcat, d_type, monthly_exp, monthly_exp*12, d_method, d_phone, d_notes))
                conn.commit()
                st.success("تم الحفظ بنجاح!")
                st.rerun()

    with tab2:
        donors_df_all = pd.read_sql("SELECT * FROM donors", conn)
        if not donors_df_all.empty:
            donor_to_edit = st.selectbox("اختر الداعم للتعديل:", donors_df_all['name'].tolist())
            d_data = donors_df_all[donors_df_all['name'] == donor_to_edit].iloc[0]
            
            with st.form("edit_donor_form"):
                col1, col2 = st.columns(2)
                ed_name = col1.text_input("اسم الداعم", value=d_data['name'])
                ed_project = col2.text_input("الحلقة / المشروع", value=d_data['project'])
                
                ed_cat = col1.selectbox("البند الرئيسي", cats, index=cats.index(d_data['category']) if d_data['category'] in cats else 0)
                ed_subcat = col2.selectbox("البند الفرعي", get_subcategories(ed_cat))
                ed_type = col1.selectbox("حالة الدعم", ["مستمر", "منقطع / مقطوع"], index=0 if "مستمر" in d_data['support_type'] else 1)
                ed_monthly = col1.number_input("المبلغ الشهري", value=float(d_data['monthly_expected']))
                ed_phone = col2.text_input("رقم الواتساب", value=str(d_data['phone'] or ''))
                ed_notes = st.text_area("ملاحظات", value=str(d_data['notes'] or ''))
                
                b1, b2 = st.columns(2)
                if b1.form_submit_button("✏️ تحديث"):
                    c = conn.cursor()
                    c.execute("UPDATE donors SET name=?, project=?, category=?, subcategory=?, support_type=?, monthly_expected=?, annual_expected=?, phone=?, notes=? WHERE id=?",
                              (ed_name, ed_project, ed_cat, ed_subcat, ed_type, ed_monthly, ed_monthly*12, ed_phone, ed_notes, int(d_data['id'])))
                    conn.commit()
                    st.success("تم التحديث!")
                    st.rerun()
                if b2.form_submit_button("🗑️ حذف"):
                    c = conn.cursor()
                    c.execute("DELETE FROM donors WHERE id=?", (int(d_data['id']),))
                    conn.commit()
                    st.warning("تم الحذف.")
                    st.rerun()

    st.divider()
    donors_df = pd.read_sql("SELECT id as 'م', name as 'اسم الداعم', project as 'الحلقة', category as 'البند الرئيسي', subcategory as 'البند الفرعي', support_type as 'الحالة', monthly_expected as 'الشهري', phone as 'الواتساب' FROM donors", conn)
    conn.close()
    st.dataframe(donors_df, use_container_width=True)

# --- 3. RECEIPTS ---
elif choice == "📥 تسجيل وتعديل المقبوضات":
    st.subheader("📥 تسجيل وتعديل المقبوضات")
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
    receipts_df = pd.read_sql("SELECT id as 'م', date as 'التاريخ', date_hijri as 'الهجري', donor_name as 'الداعم', project as 'الحلقة', category as 'البند الرئيسي', subcategory as 'البند الفرعي', amount as 'المبلغ', month as 'الشهر', year as 'السنة' FROM receipts ORDER BY id DESC", conn)
    conn.close()
    st.dataframe(receipts_df, use_container_width=True)

# --- 4. EXPENSES ---
elif choice == "💸 تسجيل وتعديل المصروفات":
    st.subheader("💸 تسجيل المصروفات")
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

    expenses_df = pd.read_sql("SELECT id as 'م', date as 'التاريخ', date_hijri as 'الهجري', beneficiary as 'المستفيد', category as 'البند الرئيسي', subcategory as 'البند الفرعي', amount as 'المبلغ', year as 'السنة', notes as 'البيان' FROM expenses ORDER BY id DESC", conn)
    conn.close()
    st.dataframe(expenses_df, use_container_width=True)

# --- 5. MONTHLY TRACKING ---
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
            row = {"الداعم": d['name'], "الحلقة": d['project'], "البند": d['category']}
            for m in MONTHS:
                if "منقطع" in d['support_type']:
                    row[m] = "⚪"
                else:
                    paid = not receipts_df[(receipts_df['donor_id'] == d['id']) & (receipts_df['month'] == m)].empty
                    row[m] = "✅" if paid else "🚨"
            matrix_rows.append(row)
        st.dataframe(pd.DataFrame(matrix_rows), use_container_width=True)

# --- 6. CATEGORY REPORTS ---
elif choice == "📄 تقارير البنود المخصصة":
    st.subheader("📄 تفاصيل البنود")
    conn = get_connection()
    cats = pd.read_sql("SELECT name FROM categories", conn)['name'].tolist()
    if not cats: cats = ["رواتب"]
        
    c1, c2 = st.columns(2)
    selected_cat = c1.selectbox("اختر البند الرئيسي", cats)
    selected_y = c2.selectbox("اختر السنة", YEARS_LIST, index=YEARS_LIST.index(2026))
    
    receipts_df = pd.read_sql("SELECT * FROM receipts WHERE category=? AND year=?", conn, params=(selected_cat, selected_y))
    expenses_df = pd.read_sql("SELECT * FROM expenses WHERE category=? AND year=?", conn, params=(selected_cat, selected_y))
    conn.close()
    
    cat_inc = receipts_df['amount'].sum() if not receipts_df.empty else 0.0
    cat_exp = expenses_df['amount'].sum() if not expenses_df.empty else 0.0
    
    col1, col2, col3 = st.columns(3)
    col1.metric("المقبوضات", f"{cat_inc:,.2f} ر.س")
    col2.metric("المصروفات", f"{cat_exp:,.2f} ر.س")
    col3.metric("المتبقي", f"{cat_inc - cat_exp:,.2f} ر.س")
    
    st.write("**سجل المقبوضات:**")
    st.dataframe(receipts_df, use_container_width=True)

# --- 7. WHATSAPP REMINDERS ---
elif choice == "📱 مركز تذكير الواتساب":
    st.subheader("📱 إرسال تذكيرات الواتساب")
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

# --- 8. REPORTS & EXPORT ---
elif choice == "🖨️ التقارير القابلة للطباعة والتصدير":
    st.subheader("🖨️ التقرير المالي والتصدير")
    selected_y = st.selectbox("السنة المالية", YEARS_LIST, index=YEARS_LIST.index(2026))

    conn = get_connection()
    receipts_df = pd.read_sql("SELECT * FROM receipts WHERE year=?", conn, params=(selected_y,))
    expenses_df = pd.read_sql("SELECT * FROM expenses WHERE year=?", conn, params=(selected_y,))
    conn.close()
    
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        receipts_df.to_excel(writer, sheet_name='المقبوضات', index=False)
        expenses_df.to_excel(writer, sheet_name='المصروفات', index=False)
    
    st.download_button(
        label="📥 تصدير التقرير المالي كملف إكسل (Excel)",
        data=output.getvalue(),
        file_name=f"Report_{selected_y}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

# --- 9. SETTINGS ---
elif choice == "⚙️ إعدادات البنود الرئيسية والفرعية":
    st.subheader("⚙️ إدارة البنود الرئيسية والفرعية")
    conn = get_connection()
    cats_df = pd.read_sql("SELECT * FROM categories", conn)
    
    col1, col2 = st.columns(2)
    with col1:
        new_cat = st.text_input("بند رئيسي جديد")
        if st.button("إضافة رئيسي") and new_cat:
            c = conn.cursor()
            c.execute("INSERT INTO categories (name) VALUES (?)", (new_cat.strip(),))
            conn.commit()
            st.success("تم الإضافة!")
            st.rerun()

    with col2:
        parent_cat = st.selectbox("اختر البند الرئيسي الأب", cats_df['name'].tolist() if not cats_df.empty else ["رواتب"])
        new_subcat = st.text_input("بند فرعي جديد")
        if st.button("إضافة فرعي") and new_subcat:
            c = conn.cursor()
            c.execute("INSERT INTO subcategories (category_name, name) VALUES (?,?)", (parent_cat, new_subcat.strip()))
            conn.commit()
            st.success("تم الإضافة!")
            st.rerun()

    st.divider()
    subcats_df = pd.read_sql("SELECT category_name as 'البند الرئيسي', name as 'البند الفرعي' FROM subcategories", conn)
    conn.close()
    st.dataframe(subcats_df, use_container_width=True)

