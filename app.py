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
    @import url('https://fonts.googleapis.com/css2?family=Cairo:wght@400;600;700&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Cairo', sans-serif;
        direction: rtl;
        text-align: right;
    }
    
    .stMetric {
        background-color: #f8f9fa;
        padding: 15px;
        border-radius: 10px;
        border-right: 5px solid #1B4D3E;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
    }
    
    .main-header {
        background: linear-gradient(135deg, #1B4D3E 0%, #2C5E4F 100%);
        color: white;
        padding: 20px;
        border-radius: 12px;
        text-align: center;
        margin-bottom: 25px;
    }
    
    .card {
        background-color: white;
        padding: 20px;
        border-radius: 10px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.05);
        margin-bottom: 20px;
        border: 1px solid #e9ecef;
    }
    
    .stButton>button {
        background-color: #1B4D3E;
        color: white;
        border-radius: 8px;
        font-weight: bold;
        width: 100%;
    }
    
    .stButton>button:hover {
        background-color: #276A55;
        color: white;
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
                
    c.execute("CREATE TABLE IF NOT EXISTS donors (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL, project TEXT NOT NULL, category TEXT NOT NULL, support_type TEXT NOT NULL, method TEXT NOT NULL, phone TEXT, notes TEXT)")
                
    c.execute("CREATE TABLE IF NOT EXISTS receipts (id INTEGER PRIMARY KEY AUTOINCREMENT, date TEXT NOT NULL, donor_id INTEGER, donor_name TEXT, project TEXT, category TEXT, amount REAL NOT NULL, month TEXT NOT NULL)")
                
    c.execute("CREATE TABLE IF NOT EXISTS expenses (id INTEGER PRIMARY KEY AUTOINCREMENT, date TEXT NOT NULL, beneficiary TEXT NOT NULL, category TEXT NOT NULL, amount REAL NOT NULL, notes TEXT)")
                
    # Insert default categories if empty
    c.execute("SELECT COUNT(*) FROM categories")
    if c.fetchone()[0] == 0:
        default_cats = [('رواتب المعلمين',), ('الجوائز والتكريم',), ('الفعاليات والأنشطة',), ('دعومات أخرى',)]
        c.executemany("INSERT INTO categories (name) VALUES (?)", default_cats)
        
    conn.commit()
    conn.close()

init_db()

# Database Helper Functions
def get_connection():
    return sqlite3.connect(DB_FILE)

# --- APP LAYOUT & NAVIGATION ---
st.markdown("<div class='main-header'><h1>🕌 نظام إدارة الدعومات والميزانية المطور</h1><p>منظومة متكاملة لمدفوعات الحلقات، المصروفات، وتذكيرات الواتساب</p></div>", unsafe_allow_html=True)

menu = [
    "📊 لوحة التحكم المباشرة",
    "👥 دليل الداعمين والحلقات",
    "📥 تسجيل الدعم (المقبوضات)",
    "💸 سجل المصروفات",
    "🗓️ جدول متابعة الأشهر",
    "📄 تقارير البنود المخصصة",
    "📱 مركز تذكير الواتساب",
    "🖨️ التقارير القابلة للطباعة والتصدير",
    "⚙️ إعدادات النظام والثوابت"
]

choice = st.sidebar.selectbox("📋 القائمة الرئيسية", menu)

MONTHS = ["يناير", "فبراير", "مارس", "أبريل", "مايو", "يونيو", "يوليو", "أغسطس", "سبتمبر", "أكتوبر", "نوفمبر", "ديسمبر"]

# --- 1. DASHBOARD ---
if choice == "📊 لوحة التحكم المباشرة":
    st.header("📊 لوحة التحكم والتحليل المالي المباشر")
    
    conn = get_connection()
    receipts_df = pd.read_sql("SELECT * FROM receipts", conn)
    expenses_df = pd.read_sql("SELECT * FROM expenses", conn)
    categories_df = pd.read_sql("SELECT * FROM categories", conn)
    donors_df = pd.read_sql("SELECT * FROM donors", conn)
    conn.close()
    
    total_income = receipts_df['amount'].sum() if not receipts_df.empty else 0.0
    total_expense = expenses_df['amount'].sum() if not expenses_df.empty else 0.0
    net_surplus = total_income - total_expense
    
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("إجمالي الدعم المقبوض", f"{total_income:,.2f} ر.س")
    col2.metric("إجمالي المصروفات", f"{total_expense:,.2f} ر.س")
    col3.metric("صافي الفائض المتبقي", f"{net_surplus:,.2f} ر.س", delta_color="normal" if net_surplus >= 0 else "inverse")
    col4.metric("إجمالي عدد الداعمين", f"{len(donors_df)}")
    
    st.divider()
    st.subheader("📈 ملخص الميزانية والسيولة حسب البنود المخصصة")
    
    summary_data = []
    for cat in categories_df['name']:
        cat_inc = receipts_df[receipts_df['category'] == cat]['amount'].sum() if not receipts_df.empty else 0.0
        cat_exp = expenses_df[expenses_df['category'] == cat]['amount'].sum() if not expenses_df.empty else 0.0
        bal = cat_inc - cat_exp
        cat_donors = len(donors_df[donors_df['category'] == cat]) if not donors_df.empty else 0
        cov_rate = (cat_inc / cat_exp * 100) if cat_exp > 0 else (100.0 if cat_inc > 0 else 0.0)
        
        summary_data.append({
            "اسم البند المخصص": cat,
            "إجمالي المقبوضات": f"{cat_inc:,.2f} ر.س",
            "إجمالي المصروفات": f"{cat_exp:,.2f} ر.س",
            "المتبقي (الرصيد)": f"{bal:,.2f} ر.س",
            "عدد الداعمين": cat_donors,
            "نسبة تغطية البند": f"{cov_rate:.1f}%"
        })
        
    st.table(pd.DataFrame(summary_data))

# --- 2. DONORS DIRECTORY ---
elif choice == "👥 دليل الداعمين والحلقات":
    st.header("👥 دليل الداعمين والحلقات المخصصة وبنود الدعم")
    
    conn = get_connection()
    cats = pd.read_sql("SELECT name FROM categories", conn)['name'].tolist()
    
    with st.expander("➕ إضافة داعم جديد", expanded=False):
        with st.form("add_donor_form"):
            col1, col2 = st.columns(2)
            d_name = col1.text_input("اسم الداعم / الجهة")
            d_project = col2.text_input("اسم الحلقة / المشروع المخصص")
            d_cat = col1.selectbox("البند الرئيسي", cats if cats else ["رواتب المعلمين"])
            d_type = col2.selectbox("طبيعة الدعم", ["مستمر (شهري/دوري)", "مقطوع (مرة واحدة)"])
            d_method = col1.selectbox("طريقة الدعم", ["مسبق (بداية الشهر)", "لاحق (نهاية الشهر)", "تحويل بنكي", "نقدي", "استقطاع شهري"])
            d_phone = col2.text_input("رقم الواتساب / الجوال (مثال: +966500000000)")
            d_notes = st.text_area("ملاحظات")
            
            submit = st.form_submit_button("حفظ البيانات")
            if submit and d_name:
                c = conn.cursor()
                c.execute("INSERT INTO donors (name, project, category, support_type, method, phone, notes) VALUES (?,?,?,?,?,?,?)",
                          (d_name, d_project, d_cat, d_type, d_method, d_phone, d_notes))
                conn.commit()
                st.success("تم إضافة الداعم بنجاح!")
                st.rerun()

    donors_df = pd.read_sql("SELECT id as 'م', name as 'اسم الداعم', project as 'الحلقة/المشروع', category as 'البند', support_type as 'طبيعة الدعم', method as 'طريقة الدعم', phone as 'الواتساب', notes as 'ملاحظات' FROM donors", conn)
    conn.close()
    st.dataframe(donors_df, use_container_width=True)

# --- 3. INCOME REGISTRATION ---
elif choice == "📥 تسجيل الدعم (المقبوضات)":
    st.header("📥 نموذج تسجيل ودفع المقبوضات")
    
    conn = get_connection()
    donors_df = pd.read_sql("SELECT * FROM donors", conn)
    
    if donors_df.empty:
        st.warning("يرجى إضافة داعمين أولاً في قائمة 'دليل الداعمين'.")
    else:
        donor_names = donors_df['name'].tolist()
        selected_donor = st.selectbox("اختر الداعم / الجهة (سيتم جلب التفاصيل تلقائياً ⚡)", donor_names)
        
        donor_info = donors_df[donors_df['name'] == selected_donor].iloc[0]
        
        col1, col2 = st.columns(2)
        col1.info(f"📍 الحلقة المخصصة: **{donor_info['project']}**")
        col2.info(f"🏷️ البند المخصص: **{donor_info['category']}**")
        
        with st.form("receipt_form"):
            c1, c2, c3 = st.columns(3)
            r_date = c1.date_input("التاريخ", datetime.date.today())
            r_amount = c2.number_input("المبلغ المقبوض (ر.س)", min_value=1.0, value=1000.0, step=100.0)
            r_month = c3.selectbox("الشهر المخصص", MONTHS, index=datetime.datetime.now().month - 1)
            
            save_receipt = st.form_submit_button("تسجيل المقبوضات ✅")
            if save_receipt:
                c = conn.cursor()
                c.execute("INSERT INTO receipts (date, donor_id, donor_name, project, category, amount, month) VALUES (?,?,?,?,?,?,?)",
                          (str(r_date), donor_info['id'], donor_info['name'], donor_info['project'], donor_info['category'], r_amount, r_month))
                conn.commit()
                st.success("تم تسجيل المقبوضات بنجاح!")
                st.rerun()

    st.subheader("📋 سجل المقبوضات الأخير")
    receipts_df = pd.read_sql("SELECT id as 'م', date as 'التاريخ', donor_name as 'الداعم', project as 'الحلقة', category as 'البند', amount as 'المبلغ (ر.س)', month as 'الشهر المخصص' FROM receipts ORDER BY id DESC", conn)
    conn.close()
    st.dataframe(receipts_df, use_container_width=True)

# --- 4. EXPENSES REGISTRATION ---
elif choice == "💸 سجل المصروفات":
    st.header("💸 سجل المصروفات والتسديدات (الخصم المباشر من البنود)")
    
    conn = get_connection()
    cats = pd.read_sql("SELECT name FROM categories", conn)['name'].tolist()
    
    with st.form("expense_form"):
        col1, col2, col3 = st.columns(3)
        exp_date = col1.date_input("التاريخ", datetime.date.today())
        exp_beneficiary = col2.text_input("الجهة / المستفيد / الحلقة")
        exp_cat = col3.selectbox("البند المخصوم منه", cats)
        
        c1, c2 = st.columns([1, 2])
        exp_amount = c1.number_input("المبلغ المصروف (ر.س)", min_value=1.0, value=500.0, step=50.0)
        exp_notes = c2.text_input("البيان / سبب الصرف")
        
        submit_exp = st.form_submit_button("تسجيل المصروف 💸")
        if submit_exp and exp_beneficiary:
            c = conn.cursor()
            c.execute("INSERT INTO expenses (date, beneficiary, category, amount, notes) VALUES (?,?,?,?,?)",
                      (str(exp_date), exp_beneficiary, exp_cat, exp_amount, exp_notes))
            conn.commit()
            st.success("تم تسجيل المصروف خصماً من البند المخصص!")
            st.rerun()
            
    expenses_df = pd.read_sql("SELECT id as 'م', date as 'التاريخ', beneficiary as 'المستفيد/الحلقة', category as 'البند المخصوم', amount as 'المبلغ (ر.س)', notes as 'البيان' FROM expenses ORDER BY id DESC", conn)
    conn.close()
    st.dataframe(expenses_df, use_container_width=True)

# --- 5. MONTHLY TRACKING MATRIX ---
elif choice == "🗓️ جدول متابعة الأشهر":
    st.header("🗓️ جدول متابعة دعم الأشهر الديناميكي")
    st.caption("💡 التذكير والمتابعة ينطبقان على الداعم 'المستمر'. الداعم 'المقطوع' يظهر بحالة غير متطلب مسبقاً.")
    
    conn = get_connection()
    donors_df = pd.read_sql("SELECT * FROM donors", conn)
    receipts_df = pd.read_sql("SELECT * FROM receipts", conn)
    conn.close()
    
    if donors_df.empty:
        st.info("لا يوجد داعمين مسجلين حالياً.")
    else:
        matrix_rows = []
        for _, d in donors_df.iterrows():
            row = {
                "الداعم": d['name'],
                "الحلقة": d['project'],
                "البند": d['category'],
                "طبيعة الدعم": d['support_type']
            }
            supported_count = 0
            for m in MONTHS:
                if "مقطوع" in d['support_type']:
                    row[m] = "⚪ مقطوع"
                else:
                    has_paid = not receipts_df[(receipts_df['donor_id'] == d['id']) & (receipts_df['month'] == m)].empty
                    if has_paid:
                        row[m] = "✅ تم الدعم"
                        supported_count += 1
                    else:
                        row[m] = "🚨 لم يدعم"
            
            if "مستمر" in d['support_type']:
                row["التزام"] = f"{(supported_count/12)*100:.0f}%"
            else:
                row["التزام"] = "N/A"
                
            matrix_rows.append(row)
            
        st.dataframe(pd.DataFrame(matrix_rows), use_container_width=True)

# --- 6. CATEGORY DETAILED REPORTS ---
elif choice == "📄 تقارير البنود المخصصة":
    st.header("📄 تفاصيل البنود المخصصة وسجل واردها")
    
    conn = get_connection()
    cats = pd.read_sql("SELECT name FROM categories", conn)['name'].tolist()
    
    selected_cat = st.selectbox("اختر البند المخصص لعرض تفاصيله", cats)
    
    receipts_df = pd.read_sql("SELECT * FROM receipts WHERE category=?", conn, params=(selected_cat,))
    expenses_df = pd.read_sql("SELECT * FROM expenses WHERE category=?", conn, params=(selected_cat,))
    conn.close()
    
    cat_inc = receipts_df['amount'].sum() if not receipts_df.empty else 0.0
    cat_exp = expenses_df['amount'].sum() if not expenses_df.empty else 0.0
    cat_bal = cat_inc - cat_exp
    
    c1, c2, c3 = st.columns(3)
    c1.metric("إجمالي الوارد (الدعم)", f"{cat_inc:,.2f} ر.س")
    c2.metric("إجمالي المنصرف", f"{cat_exp:,.2f} ر.س")
    c3.metric("الرصيد المتبقي للبند", f"{cat_bal:,.2f} ر.س")
    
    st.subheader(f"📥 وارد ومقبوضات بند ({selected_cat})")
    st.dataframe(receipts_df[['date', 'donor_name', 'project', 'amount', 'month']], use_container_width=True)

# --- 7. WHATSAPP REMINDERS ---
elif choice == "📱 مركز تذكير الواتساب":
    st.header("📱 مركز إرسال تذكير الواتساب المباشر")
    st.caption("📲 يتم جلب الداعمين 'المستمرين' المتأخرين عن الدعم للشهر المحدد لتوليد رابط واتساب مباشر بنص مخصص.")
    
    selected_month = st.selectbox("اختر الشهر المراد المتابعة عنه", MONTHS, index=datetime.datetime.now().month - 1)
    
    conn = get_connection()
    donors_df = pd.read_sql("SELECT * FROM donors WHERE support_type LIKE '%مستمر%'", conn)
    receipts_df = pd.read_sql("SELECT * FROM receipts WHERE month=?", conn, params=(selected_month,))
    conn.close()
    
    if donors_df.empty:
        st.info("لا يوجد داعمين ذوي دعم 'مستمر' مسجلين.")
    else:
        pending_list = []
        for _, d in donors_df.iterrows():
            paid = not receipts_df[receipts_df['donor_id'] == d['id']].empty
            if not paid:
                phone = str(d['phone']).replace("+", "").replace(" ", "")
                msg = f"السلام عليكم ورحمة الله وبركاته، الأخ العزيز/ {d['name']}، نود تذكيركم ودعوتكم لاستكمال دعم شهر ({selected_month}) المخصص لـ ({d['project']}). كتب الله أجركم وبارك في رزقكم."
                encoded_msg = urllib.parse.quote(msg)
                wa_url = f"https://wa.me/{phone}?text={encoded_msg}"
                
                pending_list.append({
                    "اسم الداعم": d['name'],
                    "الحلقة / المشروع": d['project'],
                    "البند": d['category'],
                    "رقم الواتساب": d['phone'],
                    "الحالة": f"🚨 لم يدعم شهر {selected_month}",
                    "رابط الإرسال المباشر": wa_url
                })
                
        if pending_list:
            st.warning(f"يوجد ({len(pending_list)}) داعمين لم يتلق النظام دعمهم لشهر {selected_month}:")
            for item in pending_list:
                col1, col2, col3 = st.columns([3, 2, 2])
                col1.write(f"👤 **{item['اسم الداعم']}** ({item['الحلقة / المشروع']})")
                col2.write(f"📱 {item['رقم الواتساب']}")
                col3.markdown(f"[📲 إرسال تذكير واتساب]({item['رابط الإرسال المباشر']})", unsafe_allow_html=True)
        else:
            st.success(f"🎉 جميع الداعمين المستمرين أتموا دعم شهر {selected_month} بنجاح!")

# --- 8. PRINTABLE REPORTS & EXPORT ---
elif choice == "🖨️ التقارير القابلة للطباعة والتصدير":
    st.header("🖨️ التقرير المالي الدوري والسنوي (جاهز للطباعة والتصدير)")
    
    conn = get_connection()
    receipts_df = pd.read_sql("SELECT * FROM receipts", conn)
    expenses_df = pd.read_sql("SELECT * FROM expenses", conn)
    categories_df = pd.read_sql("SELECT * FROM categories", conn)
    conn.close()
    
    c1, c2 = st.columns(2)
    rep_type = c1.selectbox("نوع التقرير المطلوب", ["شهري", "سنوي (كامل)"])
    selected_m = c2.selectbox("الفترة / الشهر المحدد", MONTHS) if rep_type == "شهري" else "كل الأشهر"
    
    if rep_type == "شهري":
        filtered_inc = receipts_df[receipts_df['month'] == selected_m]
    else:
        filtered_inc = receipts_df
        
    tot_inc = filtered_inc['amount'].sum() if not filtered_inc.empty else 0.0
    tot_exp = expenses_df['amount'].sum() if not expenses_df.empty else 0.0
    surplus = tot_inc - tot_exp
    
    st.markdown(f"""
    <div class='card'>
        <h3 style='text-align:center;'>تقرير مالي ({rep_type}) - {selected_m}</h3>
        <p><b>إجمالي مقبوضات الفترة:</b> {tot_inc:,.2f} ر.س</p>
        <p><b>إجمالي المصروفات كلياً:</b> {tot_exp:,.2f} ر.س</p>
        <p><b>الفائض / العجز:</b> <span style='color: {"green" if surplus >=0 else "red"}; font-weight:bold;'>{surplus:,.2f} ر.س</span></p>
    </div>
    """, unsafe_allow_html=True)
    
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        filtered_inc.to_excel(writer, sheet_name='المقبوضات', index=False)
        expenses_df.to_excel(writer, sheet_name='المصروفات', index=False)
    
    st.download_button(
        label="📥 تصدير التقرير المالي كملف إكسل (Excel)",
        data=output.getvalue(),
        file_name=f"Financial_Report_{rep_type}_{selected_m}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

# --- 9. SETTINGS ---
elif choice == "⚙️ إعدادات النظام والثوابت":
    st.header("⚙️ إعدادات النظام والقوائم المنسدلة (الثوابت)")
    
    conn = get_connection()
    cats_df = pd.read_sql("SELECT * FROM categories", conn)
    
    st.subheader("📌 إدارة بنود الأنشطة والدعومات")
    new_cat = st.text_input("إضافة بند جديد")
    if st.button("إضافة البند") and new_cat:
        try:
            c = conn.cursor()
            c.execute("INSERT INTO categories (name) VALUES (?)", (new_cat,))
            conn.commit()
            st.success("تم إضافة البند بنجاح!")
            st.rerun()
        except:
            st.error("البند موجود بالفعل.")
            
    st.table(cats_df)
    conn.close()
