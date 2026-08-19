import streamlit as st
import pandas as pd
import sqlite3
import datetime
import urllib.parse
from io import BytesIO

# --- PAGE CONFIGURATION ---
st.set_page_config(
    page_title="نظام إدارة الدعومات والمالية المطور",
    page_icon="🕌",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for Professional Arabic RTL UI
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Cairo:wght@400;600;700;800&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Cairo', sans-serif;
        direction: rtl;
        text-align: right;
    }
    
    .stMetric {
        background: linear-gradient(135deg, #ffffff 0%, #f4f7f5 100%);
        padding: 18px;
        border-radius: 12px;
        border-right: 6px solid #1B4D3E;
        box-shadow: 0 4px 12px rgba(0,0,0,0.05);
    }
    
    .main-header {
        background: linear-gradient(135deg, #1B4D3E 0%, #2C5E4F 100%);
        color: white;
        padding: 25px;
        border-radius: 15px;
        text-align: center;
        margin-bottom: 25px;
        box-shadow: 0 6px 15px rgba(27, 77, 62, 0.2);
    }
    
    .main-header h1 {
        color: #ffffff;
        font-weight: 800;
        margin-bottom: 8px;
    }
    
    .card {
        background-color: white;
        padding: 22px;
        border-radius: 12px;
        box-shadow: 0 4px 10px rgba(0,0,0,0.04);
        margin-bottom: 20px;
        border: 1px solid #e2e8f0;
    }
    
    .stButton>button {
        background: linear-gradient(135deg, #1B4D3E 0%, #276A55 100%);
        color: white;
        border: none;
        border-radius: 8px;
        font-weight: 700;
        padding: 8px 16px;
        transition: all 0.3s ease;
    }
    
    .stButton>button:hover {
        background: linear-gradient(135deg, #276A55 0%, #1B4D3E 100%);
        box-shadow: 0 4px 10px rgba(0,0,0,0.15);
    }
</style>
""", unsafe_allow_html=True)

# --- DATABASE SETUP ---
DB_FILE = "donations_system.db"

def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    
    # Tables creation
    c.execute("CREATE TABLE IF NOT EXISTS categories (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT UNIQUE NOT NULL)")
    
    c.execute("CREATE TABLE IF NOT EXISTS subcategories (id INTEGER PRIMARY KEY AUTOINCREMENT, category_name TEXT NOT NULL, name TEXT NOT NULL)")
                
    c.execute("CREATE TABLE IF NOT EXISTS donors (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL, project TEXT NOT NULL, category TEXT NOT NULL, subcategory TEXT DEFAULT 'عام', support_type TEXT NOT NULL, method TEXT NOT NULL, phone TEXT, notes TEXT)")
                
    c.execute("CREATE TABLE IF NOT EXISTS receipts (id INTEGER PRIMARY KEY AUTOINCREMENT, date TEXT NOT NULL, donor_id INTEGER, donor_name TEXT, project TEXT, category TEXT, subcategory TEXT DEFAULT 'عام', amount REAL NOT NULL, month TEXT NOT NULL, year INTEGER DEFAULT 2026)")
                
    c.execute("CREATE TABLE IF NOT EXISTS expenses (id INTEGER PRIMARY KEY AUTOINCREMENT, date TEXT NOT NULL, beneficiary TEXT NOT NULL, category TEXT NOT NULL, subcategory TEXT DEFAULT 'عام', amount REAL NOT NULL, notes TEXT, year INTEGER DEFAULT 2026)")
                
    # Migrations
    try:
        c.execute("ALTER TABLE receipts ADD COLUMN year INTEGER DEFAULT 2026")
    except sqlite3.OperationalError: pass
    
    try:
        c.execute("ALTER TABLE expenses ADD COLUMN year INTEGER DEFAULT 2026")
    except sqlite3.OperationalError: pass

    try:
        c.execute("ALTER TABLE donors ADD COLUMN subcategory TEXT DEFAULT 'عام'")
    except sqlite3.OperationalError: pass

    try:
        c.execute("ALTER TABLE receipts ADD COLUMN subcategory TEXT DEFAULT 'عام'")
    except sqlite3.OperationalError: pass

    try:
        c.execute("ALTER TABLE expenses ADD COLUMN subcategory TEXT DEFAULT 'عام'")
    except sqlite3.OperationalError: pass

    # Insert default categories if empty
    c.execute("SELECT COUNT(*) FROM categories")
    if c.fetchone()[0] == 0:
        default_cats = [('رواتب المعلمين',), ('الجوائز والتكريم',), ('الفعاليات والأنشطة',), ('دعومات أخرى',)]
        c.executemany("INSERT INTO categories (name) VALUES (?)", default_cats)
        
        default_subcats = [
            ('رواتب المعلمين', 'راتب معلم'),
            ('رواتب المعلمين', 'راتب طاقم إداري'),
            ('الجوائز والتكريم', 'تكريم طلاب'),
            ('الجوائز والتكريم', 'حفل سنوي')
        ]
        c.executemany("INSERT INTO subcategories (category_name, name) VALUES (?,?)", default_subcats)
        
    conn.commit()
    conn.close()

init_db()

def get_connection():
    return sqlite3.connect(DB_FILE)

# Helper function to get subcategories
def get_subcategories(cat_name):
    conn = get_connection()
    subs = pd.read_sql("SELECT name FROM subcategories WHERE category_name = ?", conn, params=(cat_name,))['name'].tolist()
    conn.close()
    return subs if subs else ["عام"]

# --- APP LAYOUT ---
st.markdown("""
<div class='main-header'>
    <h1>🕌 نظام إدارة الدعومات والميزانية المطور</h1>
    <p>منظومة متكاملة لمدفوعات الحلقات، المصروفات، البنود الفرعية والتعديل المباشر</p>
</div>
""", unsafe_allow_html=True)

menu = [
    "📊 لوحة التحكم المباشرة",
    "👥 دليل الداعمين وتعديل البيانات",
    "📥 تسجيل وتعديل المقبوضات",
    "💸 تسجيل وتعديل المصروفات",
    "🗓️ جدول متابعة الأشهر والسنوات",
    "📄 تقارير البنود المخصصة",
    "📱 مركز تذكير الواتساب",
    "🖨️ التقارير القابلة للطباعة والتصدير",
    "⚙️ إعدادات البنود الرئيسية والفرعية"
]

choice = st.sidebar.selectbox("📋 القائمة الرئيسية", menu)

MONTHS = ["يناير", "فبراير", "مارس", "أبريل", "مايو", "يونيو", "يوليو", "أغسطس", "سبتمبر", "أكتوبر", "نوفمبر", "ديسمبر"]
YEARS_LIST = list(range(2024, 2031))

# --- 1. DASHBOARD ---
if choice == "📊 لوحة التحكم المباشرة":
    st.header("📊 لوحة التحكم والتحليل المالي المباشر")
    
    selected_dash_year = st.selectbox("📅 اختر سنة التقرير:", YEARS_LIST, index=YEARS_LIST.index(2026) if 2026 in YEARS_LIST else 0)
    
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
    col1.metric(f"إجمالي مقبوضات {selected_dash_year}", f"{total_income:,.2f} ر.س")
    col2.metric(f"إجمالي مصروفات {selected_dash_year}", f"{total_expense:,.2f} ر.س")
    col3.metric("صافي الفائض المتبقي", f"{net_surplus:,.2f} ر.س", delta_color="normal" if net_surplus >= 0 else "inverse")
    col4.metric("إجمالي عدد الداعمين", f"{len(donors_df)}")
    
    st.divider()
    st.subheader(f"📈 ملخص الميزانية والسيولة حسب البنود لسنة {selected_dash_year}")
    
    summary_data = []
    for cat in categories_df['name']:
        cat_inc = receipts_df[receipts_df['category'] == cat]['amount'].sum() if not receipts_df.empty else 0.0
        cat_exp = expenses_df[expenses_df['category'] == cat]['amount'].sum() if not expenses_df.empty else 0.0
        bal = cat_inc - cat_exp
        cat_donors = len(donors_df[donors_df['category'] == cat]) if not donors_df.empty else 0
        cov_rate = (cat_inc / cat_exp * 100) if cat_exp > 0 else (100.0 if cat_inc > 0 else 0.0)
        
        summary_data.append({
            "اسم البند الرئيسي": cat,
            "إجمالي المقبوضات": f"{cat_inc:,.2f} ر.س",
            "إجمالي المصروفات": f"{cat_exp:,.2f} ر.س",
            "المتبقي (الرصيد)": f"{bal:,.2f} ر.س",
            "عدد الداعمين": cat_donors,
            "نسبة تغطية البند": f"{cov_rate:.1f}%"
        })
        
    st.dataframe(pd.DataFrame(summary_data), use_container_width=True)

# --- 2. DONORS DIRECTORY & EDITING ---
elif choice == "👥 دليل الداعمين وتعديل البيانات":
    st.header("👥 دليل الداعمين وإدارة بياناتهم")
    
    conn = get_connection()
    cats = pd.read_sql("SELECT name FROM categories", conn)['name'].tolist()
    if not cats: cats = ["رواتب المعلمين"]
    default_cat_index = cats.index("رواتب المعلمين") if "رواتب المعلمين" in cats else 0

    tab1, tab2 = st.tabs(["➕ إضافة داعم جديد", "✏️ تعديل بيانات داعم حالي"])
    
    with tab1:
        with st.form("add_donor_form"):
            col1, col2 = st.columns(2)
            d_name = col1.text_input("اسم الداعم / الجهة")
            d_project = col2.text_input("اسم الحلقة / المشروع المخصص")
            
            d_cat = col1.selectbox("البند الرئيسي", cats, index=default_cat_index)
            sub_cats = get_subcategories(d_cat)
            d_subcat = col2.selectbox("البند الفرعي", sub_cats)
            
            d_type = col1.selectbox("طبيعة الدعم", ["مستمر (شهري/دوري)", "مقطوع (مرة واحدة)"])
            d_method = col2.selectbox("طريقة الدعم", ["مسبق (بداية الشهر)", "لاحق (نهاية الشهر)", "تحويل بنكي", "نقدي", "استقطاع شهري"])
            d_phone = col1.text_input("رقم الواتساب / الجوال (مثال: 966500000000)")
            d_notes = col2.text_area("ملاحظات")
            
            submit = st.form_submit_button("💾 حفظ الداعم")
            if submit and d_name:
                c = conn.cursor()
                c.execute("INSERT INTO donors (name, project, category, subcategory, support_type, method, phone, notes) VALUES (?,?,?,?,?,?,?,?)",
                          (d_name, d_project, d_cat, d_subcat, d_type, d_method, d_phone, d_notes))
                conn.commit()
                st.success("تم إضافة الداعم بنجاح!")
                st.rerun()

    with tab2:
        donors_df_all = pd.read_sql("SELECT * FROM donors", conn)
        if not donors_df_all.empty:
            donor_to_edit = st.selectbox("اختر الداعم المراد تعديل بياناته:", donors_df_all['name'].tolist())
            d_data = donors_df_all[donors_df_all['name'] == donor_to_edit].iloc[0]
            
            with st.form("edit_donor_form"):
                col1, col2 = st.columns(2)
                ed_name = col1.text_input("اسم الداعم", value=d_data['name'])
                ed_project = col2.text_input("اسم الحلقة / المشروع", value=d_data['project'])
                
                ed_cat = col1.selectbox("البند الرئيسي", cats, index=cats.index(d_data['category']) if d_data['category'] in cats else 0)
                sub_cats_edit = get_subcategories(ed_cat)
                ed_subcat = col2.selectbox("البند الفرعي", sub_cats_edit, index=sub_cats_edit.index(d_data['subcategory']) if d_data['subcategory'] in sub_cats_edit else 0)
                
                ed_type = col1.selectbox("طبيعة الدعم", ["مستمر (شهري/دوري)", "مقطوع (مرة واحدة)"], index=0 if "مستمر" in d_data['support_type'] else 1)
                ed_method = col2.selectbox("طريقة الدعم", ["مسبق (بداية الشهر)", "لاحق (نهاية الشهر)", "تحويل بنكي", "نقدي", "استقطاع شهري"])
                ed_phone = col1.text_input("رقم الواتساب", value=d_data['phone'])
                ed_notes = col2.text_area("ملاحظات", value=d_data['notes'])
                
                c_btn1, c_btn2 = st.columns(2)
                update_btn = c_btn1.form_submit_button("✏️ حفظ التعديلات")
                delete_btn = c_btn2.form_submit_button("🗑️ حذف الداعم")
                
                if update_btn:
                    c = conn.cursor()
                    c.execute("UPDATE donors SET name=?, project=?, category=?, subcategory=?, support_type=?, method=?, phone=?, notes=? WHERE id=?",
                              (ed_name, ed_project, ed_cat, ed_subcat, ed_type, ed_method, ed_phone, ed_notes, int(d_data['id'])))
                    conn.commit()
                    st.success("تم تحديث بيانات الداعم بنجاح!")
                    st.rerun()
                    
                if delete_btn:
                    c = conn.cursor()
                    c.execute("DELETE FROM donors WHERE id=?", (int(d_data['id']),))
                    conn.commit()
                    st.warning("تم حذف الداعم من النظام.")
                    st.rerun()

    st.divider()
    donors_df = pd.read_sql("SELECT id as 'م', name as 'اسم الداعم', project as 'الحلقة/المشروع', category as 'البند الرئيسي', subcategory as 'البند الفرعي', support_type as 'طبيعة الدعم', phone as 'الواتساب' FROM donors", conn)
    conn.close()
    st.dataframe(donors_df, use_container_width=True)

# --- 3. INCOME REGISTRATION & EDITING ---
elif choice == "📥 تسجيل وتعديل المقبوضات":
    st.header("📥 تسجيل وتعديل عمليات الدعم (المقبوضات)")
    
    conn = get_connection()
    donors_df = pd.read_sql("SELECT * FROM donors", conn)
    cats = pd.read_sql("SELECT name FROM categories", conn)['name'].tolist()
    if not cats: cats = ["رواتب المعلمين"]

    tab1, tab2 = st.tabs(["➕ تسجيل دعم جديد", "✏️ تعديل / حذف عملية دعم مسجلة"])

    with tab1:
        if donors_df.empty:
            st.warning("يرجى إضافة داعمين أولاً.")
        else:
            selected_donor = st.selectbox("اختر الداعم / الجهة ⚡", donors_df['name'].tolist())
            donor_info = donors_df[donors_df['name'] == selected_donor].iloc[0]
            
            donor_default_cat = donor_info['category'] if donor_info['category'] in cats else "رواتب المعلمين"
            donor_cat_index = cats.index(donor_default_cat) if donor_default_cat in cats else 0
            
            col1, col2 = st.columns(2)
            col1.info(f"📍 الحلقة المخصصة: **{donor_info['project']}**")
            col2.info(f"🏷️ البند المسجل للداعم: **{donor_info['category']} ({donor_info['subcategory']})**")
            
            with st.form("receipt_form"):
                c1, c2 = st.columns(2)
                r_cat = c1.selectbox("البند الرئيسي للدفعة", cats, index=donor_cat_index)
                sub_cats = get_subcategories(r_cat)
                r_subcat = c2.selectbox("البند الفرعي للدفعة", sub_cats)

                c3, c4, c5, c6 = st.columns(4)
                r_amount = c3.number_input("المبلغ (ر.س)", min_value=1.0, value=1000.0, step=100.0)
                r_date = c4.date_input("تاريخ الدعم الفعلي", datetime.date.today())
                r_month = c5.selectbox("الشهر المخصص", MONTHS, index=datetime.datetime.now().month - 1)
                r_year = c6.selectbox("السنة المخصصة", YEARS_LIST, index=YEARS_LIST.index(r_date.year) if r_date.year in YEARS_LIST else 2)
                
                save_receipt = st.form_submit_button("تسجيل المقبوضات ✅")
                if save_receipt:
                    c = conn.cursor()
                    c.execute("INSERT INTO receipts (date, donor_id, donor_name, project, category, subcategory, amount, month, year) VALUES (?,?,?,?,?,?,?,?,?)",
                              (str(r_date), donor_info['id'], donor_info['name'], donor_info['project'], r_cat, r_subcat, r_amount, r_month, int(r_year)))
                    conn.commit()
                    st.success(f"تم تسجيل مبلغ {r_amount:,.2f} ر.س بنجاح!")
                    st.rerun()

    with tab2:
        receipts_all = pd.read_sql("SELECT * FROM receipts ORDER BY id DESC", conn)
        if not receipts_all.empty:
            receipt_options = [f"م: {r['id']} | {r['donor_name']} | {r['amount']} ر.س | {r['month']} {r['year']}" for _, r in receipts_all.iterrows()]
            selected_rec_str = st.selectbox("اختر العملية للتعديل أو الحذف:", receipt_options)
            rec_id = int(selected_rec_str.split("|")[0].replace("م:", "").strip())
            rec_data = receipts_all[receipts_all['id'] == rec_id].iloc[0]

            with st.form("edit_receipt_form"):
                col1, col2 = st.columns(2)
                ed_r_amount = col1.number_input("المبلغ (ر.س)", value=float(rec_data['amount']))
                ed_r_cat = col2.selectbox("البند الرئيسي", cats, index=cats.index(rec_data['category']) if rec_data['category'] in cats else 0)
                
                sub_cats_rec = get_subcategories(ed_r_cat)
                ed_r_subcat = col1.selectbox("البند الفرعي", sub_cats_rec)
                ed_r_month = col2.selectbox("الشهر", MONTHS, index=MONTHS.index(rec_data['month']) if rec_data['month'] in MONTHS else 0)
                ed_r_year = col1.selectbox("السنة", YEARS_LIST, index=YEARS_LIST.index(int(rec_data['year'])) if int(rec_data['year']) in YEARS_LIST else 2)

                btn1, btn2 = st.columns(2)
                up_rec = btn1.form_submit_button("✏️ تحديث العملية")
                del_rec = btn2.form_submit_button("🗑️ حذف العملية")

                if up_rec:
                    c = conn.cursor()
                    c.execute("UPDATE receipts SET amount=?, category=?, subcategory=?, month=?, year=? WHERE id=?",
                              (ed_r_amount, ed_r_cat, ed_r_subcat, ed_r_month, int(ed_r_year), rec_id))
                    conn.commit()
                    st.success("تم تحديث عملية الدعم بنجاح!")
                    st.rerun()

                if del_rec:
                    c = conn.cursor()
                    c.execute("DELETE FROM receipts WHERE id=?", (rec_id,))
                    conn.commit()
                    st.warning("تم حذف عملية الدعم.")
                    st.rerun()

    st.subheader("📋 سجل المقبوضات الأخير")
    receipts_df = pd.read_sql("SELECT id as 'م', date as 'التاريخ', donor_name as 'الداعم', project as 'الحلقة', category as 'البند الرئيسي', subcategory as 'البند الفرعي', amount as 'المبلغ (ر.س)', month as 'الشهر', year as 'السنة' FROM receipts ORDER BY id DESC", conn)
    conn.close()
    st.dataframe(receipts_df, use_container_width=True)

# --- 4. EXPENSES REGISTRATION & EDITING ---
elif choice == "💸 تسجيل وتعديل المصروفات":
    st.header("💸 تسجيل وتعديل المصروفات والتسديدات")
    
    conn = get_connection()
    cats = pd.read_sql("SELECT name FROM categories", conn)['name'].tolist()
    if not cats: cats = ["رواتب المعلمين"]

    tab1, tab2 = st.tabs(["➕ تسجيل مصروف جديد", "✏️ تعديل / حذف مصروف"])

    with tab1:
        with st.form("expense_form"):
            col1, col2 = st.columns(2)
            exp_date = col1.date_input("تاريخ الصرف", datetime.date.today())
            exp_beneficiary = col2.text_input("الجهة / المستفيد / الحلقة")
            
            exp_cat = col1.selectbox("البند الرئيسي المخصوم منه", cats)
            sub_cats = get_subcategories(exp_cat)
            exp_subcat = col2.selectbox("البند الفرعي", sub_cats)

            c1, c2, c3 = st.columns([1, 2, 1])
            exp_amount = c1.number_input("المبلغ المصروف (ر.س)", min_value=1.0, value=500.0, step=50.0)
            exp_notes = c2.text_input("البيان / سبب الصرف")
            exp_year = c3.selectbox("السنة المالية", YEARS_LIST, index=YEARS_LIST.index(exp_date.year) if exp_date.year in YEARS_LIST else 2)
            
            submit_exp = st.form_submit_button("تسجيل المصروف 💸")
            if submit_exp and exp_beneficiary:
                c = conn.cursor()
                c.execute("INSERT INTO expenses (date, beneficiary, category, subcategory, amount, notes, year) VALUES (?,?,?,?,?,?,?)",
                          (str(exp_date), exp_beneficiary, exp_cat, exp_subcat, exp_amount, exp_notes, int(exp_year)))
                conn.commit()
                st.success("تم تسجيل المصروف بنجاح!")
                st.rerun()

    with tab2:
        exp_all = pd.read_sql("SELECT * FROM expenses ORDER BY id DESC", conn)
        if not exp_all.empty:
            exp_options = [f"م: {e['id']} | {e['beneficiary']} | {e['amount']} ر.س | {e['category']}" for _, e in exp_all.iterrows()]
            selected_exp_str = st.selectbox("اختر المصروف للتعديل أو الحذف:", exp_options)
            exp_id = int(selected_exp_str.split("|")[0].replace("م:", "").strip())
            exp_data = exp_all[exp_all['id'] == exp_id].iloc[0]

            with st.form("edit_exp_form"):
                col1, col2 = st.columns(2)
                ed_e_ben = col1.text_input("المستفيد", value=exp_data['beneficiary'])
                ed_e_amount = col2.number_input("المبلغ (ر.س)", value=float(exp_data['amount']))
                
                ed_e_cat = col1.selectbox("البند الرئيسي", cats, index=cats.index(exp_data['category']) if exp_data['category'] in cats else 0)
                sub_cats_exp = get_subcategories(ed_e_cat)
                ed_e_subcat = col2.selectbox("البند الفرعي", sub_cats_exp)
                ed_e_notes = st.text_input("البيان", value=exp_data['notes'])

                b1, b2 = st.columns(2)
                up_exp = b1.form_submit_button("✏️ تحديث المصروف")
                del_exp = b2.form_submit_button("🗑️ حذف المصروف")

                if up_exp:
                    c = conn.cursor()
                    c.execute("UPDATE expenses SET beneficiary=?, amount=?, category=?, subcategory=?, notes=? WHERE id=?",
                              (ed_e_ben, ed_e_amount, ed_e_cat, ed_e_subcat, ed_e_notes, exp_id))
                    conn.commit()
                    st.success("تم تحديث المصروف بنجاح!")
                    st.rerun()

                if del_exp:
                    c = conn.cursor()
                    c.execute("DELETE FROM expenses WHERE id=?", (exp_id,))
                    conn.commit()
                    st.warning("تم حذف المصروف.")
                    st.rerun()

    expenses_df = pd.read_sql("SELECT id as 'م', date as 'التاريخ', beneficiary as 'المستفيد/الحلقة', category as 'البند الرئيسي', subcategory as 'البند الفرعي', amount as 'المبلغ (ر.س)', year as 'السنة', notes as 'البيان' FROM expenses ORDER BY id DESC", conn)
    conn.close()
    st.dataframe(expenses_df, use_container_width=True)

# --- 5. MONTHLY TRACKING MATRIX ---
elif choice == "🗓️ جدول متابعة الأشهر والسنوات":
    st.header("🗓️ جدول متابعة دعم الأشهر والسنوات الديناميكي")
    
    col_sel_y, _ = st.columns([1, 2])
    with col_sel_y:
        selected_matrix_year = st.selectbox("📅 اختر سنة المتابعة:", YEARS_LIST, index=YEARS_LIST.index(2026) if 2026 in YEARS_LIST else 2)

    conn = get_connection()
    donors_df = pd.read_sql("SELECT * FROM donors", conn)
    receipts_df = pd.read_sql("SELECT * FROM receipts WHERE year = ?", conn, params=(selected_matrix_year,))
    conn.close()
    
    if donors_df.empty:
        st.info("لا يوجد داعمين مسجلين حالياً.")
    else:
        matrix_rows = []
        for _, d in donors_df.iterrows():
            row = {
                "الداعم": d['name'],
                "الحلقة": d['project'],
                "البند الرئيسي": d['category'],
                "البند الفرعي": d['subcategory'],
                "طبيعة الدعم": d['support_type']
            }
            supported_count = 0
            for m in MONTHS:
                if "مقطوع" in d['support_type']:
                    row[m] = "⚪ مقطوع"
                else:
                    # تحقق عام برقم الداعم للتحكم الدقيق بغض النظر عن اختلاف البند المختار وقت التسجيل
                    has_paid = not receipts_df[(receipts_df['donor_id'] == d['id']) & (receipts_df['month'] == m)].empty
                    if has_paid:
                        row[m] = "✅ تم الدعم"
                        supported_count += 1
                    else:
                        row[m] = "🚨 لم يدعم"
            
            if "مستمر" in d['support_type']:
                row["نسبة الالتزام"] = f"{(supported_count/12)*100:.0f}%"
            else:
                row["نسبة الالتزام"] = "غير متطلب"
                
            matrix_rows.append(row)
            
        st.dataframe(pd.DataFrame(matrix_rows), use_container_width=True)

# --- 6. CATEGORY DETAILED REPORTS ---
elif choice == "📄 تقارير البنود المخصصة":
    st.header("📄 تفاصيل البنود المخصصة والفرعية")
    
    conn = get_connection()
    cats = pd.read_sql("SELECT name FROM categories", conn)['name'].tolist()
    if not cats: cats = ["رواتب المعلمين"]
        
    col_c, col_y = st.columns(2)
    selected_cat = col_c.selectbox("اختر البند الرئيسي", cats)
    selected_y = col_y.selectbox("اختر السنة", YEARS_LIST, index=YEARS_LIST.index(2026) if 2026 in YEARS_LIST else 2)
    
    receipts_df = pd.read_sql("SELECT * FROM receipts WHERE category=? AND year=?", conn, params=(selected_cat, selected_y))
    expenses_df = pd.read_sql("SELECT * FROM expenses WHERE category=? AND year=?", conn, params=(selected_cat, selected_y))
    conn.close()
    
    cat_inc = receipts_df['amount'].sum() if not receipts_df.empty else 0.0
    cat_exp = expenses_df['amount'].sum() if not expenses_df.empty else 0.0
    cat_bal = cat_inc - cat_exp
    
    c1, c2, c3 = st.columns(3)
    c1.metric(f"إجمالي الوارد لسنة {selected_y}", f"{cat_inc:,.2f} ر.س")
    c2.metric(f"إجمالي المنصرف لسنة {selected_y}", f"{cat_exp:,.2f} ر.س")
    c3.metric("الرصيد المتبقي للبند", f"{cat_bal:,.2f} ر.س")
    
    st.subheader(f"📥 المقبوضات حسب البنود الفرعية لـ ({selected_cat})")
    if not receipts_df.empty:
        st.dataframe(receipts_df[['date', 'donor_name', 'project', 'category', 'subcategory', 'amount', 'month']], use_container_width=True)
    else:
        st.info("لا توجد مقبوضات مسجلة لهذا البند في هذه السنة.")

# --- 7. WHATSAPP REMINDERS ---
elif choice == "📱 مركز تذكير الواتساب":
    st.header("📱 مركز إرسال تذكير الواتساب المباشر")
    
    col_m, col_y = st.columns(2)
    selected_month = col_m.selectbox("اختر الشهر المراد المتابعة عنه", MONTHS, index=datetime.datetime.now().month - 1)
    selected_wa_year = col_y.selectbox("اختر السنة", YEARS_LIST, index=YEARS_LIST.index(2026) if 2026 in YEARS_LIST else 2)

    conn = get_connection()
    donors_df = pd.read_sql("SELECT * FROM donors WHERE support_type LIKE '%مستمر%'", conn)
    receipts_df = pd.read_sql("SELECT * FROM receipts WHERE month=? AND year=?", conn, params=(selected_month, selected_wa_year))
    conn.close()
    
    if donors_df.empty:
        st.info("لا يوجد داعمين ذوي دعم 'مستمر' مسجلين.")
    else:
        pending_list = []
        for _, d in donors_df.iterrows():
            paid = not receipts_df[receipts_df['donor_id'] == d['id']].empty
            if not paid:
                phone = str(d['phone']).replace("+", "").replace(" ", "")
                msg = f"السلام عليكم ورحمة الله وبركاته، الأخ العزيز/ {d['name']}، نود تذكيركم ودعوتكم لاستكمال دعم شهر ({selected_month}) لسنة ({selected_wa_year}) المخصص لـ ({d['project']}). كتب الله أجركم وبارك في رزقكم."
                encoded_msg = urllib.parse.quote(msg)
                wa_url = f"https://wa.me/{phone}?text={encoded_msg}"
                
                pending_list.append({
                    "اسم الداعم": d['name'],
                    "الحلقة / المشروع": d['project'],
                    "البند": d['category'],
                    "رقم الواتساب": d['phone'],
                    "رابط الإرسال المباشر": wa_url
                })
                
        if pending_list:
            st.warning(f"يوجد ({len(pending_list)}) داعمين لم يتلق النظام دعمهم لشهر {selected_month} لسنة {selected_wa_year}:")
            for item in pending_list:
                col1, col2, col3 = st.columns([3, 2, 2])
                col1.write(f"👤 **{item['اسم الداعم']}** ({item['الحلقة / المشروع']})")
                col2.write(f"📱 {item['رقم الواتساب']}")
                col3.markdown(f"[📲 إرسال تذكير واتساب]({item['رابط الإرسال المباشر']})", unsafe_allow_html=True)
        else:
            st.success(f"🎉 جميع الداعمين المستمرين أتموا دعم شهر {selected_month} لسنة {selected_wa_year} بنجاح!")

# --- 8. PRINTABLE REPORTS & EXPORT ---
elif choice == "🖨️ التقارير القابلة للطباعة والتصدير":
    st.header("🖨️ التقرير المالي الدوري والسنوي")
    
    c1, c2, c3 = st.columns(3)
    rep_type = c1.selectbox("نوع التقرير المطلوب", ["شهري", "سنوي (كامل)"])
    selected_y = c2.selectbox("السنة المالية", YEARS_LIST, index=YEARS_LIST.index(2026) if 2026 in YEARS_LIST else 2)
    selected_m = c3.selectbox("الشهر المحدد", MONTHS) if rep_type == "شهري" else "كل الأشهر"

    conn = get_connection()
    if rep_type == "شهري":
        receipts_df = pd.read_sql("SELECT * FROM receipts WHERE year=? AND month=?", conn, params=(selected_y, selected_m))
        expenses_df = pd.read_sql("SELECT * FROM expenses WHERE year=?", conn, params=(selected_y,))
    else:
        receipts_df = pd.read_sql("SELECT * FROM receipts WHERE year=?", conn, params=(selected_y,))
        expenses_df = pd.read_sql("SELECT * FROM expenses WHERE year=?", conn, params=(selected_y,))
    conn.close()
    
    tot_inc = receipts_df['amount'].sum() if not receipts_df.empty else 0.0
    tot_exp = expenses_df['amount'].sum() if not expenses_df.empty else 0.0
    surplus = tot_inc - tot_exp
    
    st.markdown(f"""
    <div class='card'>
        <h3 style='text-align:center;'>تقرير مالي ({rep_type}) - لسنة {selected_y} {f"({selected_m})" if rep_type == "شهري" else ""}</h3>
        <p><b>إجمالي مقبوضات الفترة:</b> {tot_inc:,.2f} ر.س</p>
        <p><b>إجمالي المصروفات الفترة:</b> {tot_exp:,.2f} ر.س</p>
        <p><b>الفائض / العجز:</b> <span style='color: {"green" if surplus >=0 else "red"}; font-weight:bold;'>{surplus:,.2f} ر.س</span></p>
    </div>
    """, unsafe_allow_html=True)
    
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        receipts_df.to_excel(writer, sheet_name='المقبوضات', index=False)
        expenses_df.to_excel(writer, sheet_name='المصروفات', index=False)
    
    st.download_button(
        label="📥 تصدير التقرير المالي كملف إكسل (Excel)",
        data=output.getvalue(),
        file_name=f"Financial_Report_{selected_y}_{selected_m}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

# --- 9. SETTINGS (CATEGORIES & SUBCATEGORIES) ---
elif choice == "⚙️ إعدادات البنود الرئيسية والفرعية":
    st.header("⚙️ إدارة البنود الرئيسية والبنود الفرعية")
    
    conn = get_connection()
    cats_df = pd.read_sql("SELECT * FROM categories", conn)
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("📌 إضافة بند رئيسي جديد")
        new_cat = st.text_input("اسم البند الرئيسي الجديد")
        if st.button("حفظ البند الرئيسي") and new_cat:
            try:
                c = conn.cursor()
                c.execute("INSERT INTO categories (name) VALUES (?)", (new_cat.strip(),))
                conn.commit()
                st.success("تم إضافة البند الرئيسي بنجاح!")
                st.rerun()
            except:
                st.error("البند موجود بالفعل.")

    with col2:
        st.subheader("🔹 إضافة بند فرعي جديد")
        selected_parent_cat = st.selectbox("اختر البند الرئيسي الأب", cats_df['name'].tolist() if not cats_df.empty else ["رواتب المعلمين"])
        new_subcat = st.text_input("اسم البند الفرعي الجديد")
        if st.button("حفظ البند الفرعي") and new_subcat:
            c = conn.cursor()
            c.execute("INSERT INTO subcategories (category_name, name) VALUES (?,?)", (selected_parent_cat, new_subcat.strip()))
            conn.commit()
            st.success(f"تم إضافة البند الفرعي ({new_subcat}) تحت بند ({selected_parent_cat}) بنجاح!")
            st.rerun()

    st.divider()
    st.subheader("📋 شجرة البنود المسجلة حالياً")
    subcats_df = pd.read_sql("SELECT category_name as 'البند الرئيسي', name as 'البند الفرعي' FROM subcategories", conn)
    conn.close()
    
    st.dataframe(subcats_df, use_container_width=True)
