import streamlit as st
import pandas as pd
import os
from datetime import date

# 1. إعدادات الصفحة الأساسية
st.set_page_config(
    page_title="تطبيق إدارة التبرعات والمتابعة",
    page_icon="💰",
    layout="wide"
)

# تخصيص واجهة المستخدم بالاتجاه من اليمين لليسار (RTL)
st.markdown("""
    <style>
    .main { text-align: right; direction: rtl; }
    div[data-baseweb="select"] { direction: rtl; }
    div[class*="stDateInput"] { direction: rtl; }
    </style>
""", unsafe_allow_html=True)

st.title("💰 تطبيق إدارة ومتابعة التبرعات")

# 2. إعداد أوراق العمل / الملفات
DONATIONS_FILE = "donations_data.csv"
SCHEDULE_FILE = "monthly_schedule_data.csv"

# إنشاء ملف التبرعات إن لم يكن موجوداً
if not os.path.exists(DONATIONS_FILE):
    df_donations = pd.DataFrame(columns=["اسم المتبرع", "المبلغ", "التاريخ", "النوع", "ملاحظات"])
    df_donations.to_csv(DONATIONS_FILE, index=False)

# إنشاء ملف المتابعة الشهرية إن لم يكن موجوداً
if not os.path.exists(SCHEDULE_FILE):
    df_schedule = pd.DataFrame(columns=["السنة", "الشهر", "الداعم / الجهة", "مبلغ الدعم", "تاريخ الدعم الفعلية", "ملاحظات"])
    df_schedule.to_csv(SCHEDULE_FILE, index=False)

# قراءة البيانات
df_donations = pd.read_csv(DONATIONS_FILE)
df_schedule = pd.read_csv(SCHEDULE_FILE)

# تأكد من تحويل عمود السنة إلى رقم صحيح
if not df_schedule.empty and "السنة" in df_schedule.columns:
    df_schedule["السنة"] = pd.to_numeric(df_schedule["السنة"], errors="coerce").fillna(2026).astype(int)

# 3. القائمة الجانبية والتنقل بين الصفحات
st.sidebar.title("📌 القائمة الرئيسية")
page = st.sidebar.radio(
    "اختر الصفحة:",
    ["➕ تسجيل تبرع جديد", "📊 سجل وإحصائيات التبرعات", "🗓️ جدول متابعة الأشهر"]
)

# -------------------------------------------------------------
# الصفحة الأولى: تسجيل تبرع جديد
# -------------------------------------------------------------
if page == "➕ تسجيل تبرع جديد":
    st.header("➕ إضافة تبرع جديد")
    with st.form("donation_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            name = st.text_input("اسم المتبرع")
            amount = st.number_input("المبلغ (بالريال)", min_value=1.0, step=10.0)
        with col2:
            donation_date = st.date_input("تاريخ التبرع", date.today())
            donation_type = st.selectbox("نوع التبرع", ["زكاة", "صدقة", "كفالة", "عام", "أخرى"])
            
        notes = st.text_area("ملاحظات إضافية (اختياري)")
        submitted = st.form_submit_button("💾 حفظ التبرع")

        if submitted:
            if name.strip() != "":
                new_data = pd.DataFrame({
                    "اسم المتبرع": [name.strip()],
                    "المبلغ": [amount],
                    "التاريخ": [str(donation_date)],
                    "النوع": [donation_type],
                    "ملاحظات": [notes.strip()]
                })
                df_donations = pd.concat([df_donations, new_data], ignore_index=True)
                df_donations.to_csv(DONATIONS_FILE, index=False)
                st.success(f"✅ تم حفظ تبرع {name} بقيمة {amount} ريال بنجاح!")
            else:
                st.error("⚠️ يرجى كتابة اسم المتبرع.")

# -------------------------------------------------------------
# الصفحة الثانية: سجل وإحصائيات التبرعات
# -------------------------------------------------------------
elif page == "📊 سجل وإحصائيات التبرعات":
    st.header("📊 إحصائيات وسجل التبرعات التفصيلي")
    
    if not df_donations.empty:
        # ملخص سريع
        c1, c2, c3 = st.columns(3)
        c1.metric("إجمالي التبرعات", f"{df_donations['المبلغ'].sum():,.2f} ريال")
        c2.metric("عدد التبرعات المسجلة", len(df_donations))
        c3.metric("متوسط التبرع", f"{df_donations['المبلغ'].mean():,.2f} ريال")
        
        st.divider()
        st.subheader("📋 جميع التبرعات المسجلة")
        st.dataframe(df_donations, use_container_width=True)
    else:
        st.info("لا توجد تبرعات مسجلة حتى الآن.")

# -------------------------------------------------------------
# الصفحة الثالثة: جدول متابعة الأشهر (المُعدّلة)
# -------------------------------------------------------------
elif page == "🗓️ جدول متابعة الأشهر":
    st.header("🗓️ جدول متابعة دعم الأشهر")
    st.write("هنا يمكنك تسجيل الدعم المالي لكل شهر وتحديث تاريخ الدعم الفعلي (حتى لو كان بأثر رجعي).")

    # 1. فلترة وتحديد السنة
    col_year, col_space = st.columns([1, 2])
    with col_year:
        # يتيح لك اختيار أي سنة من 2024 حتى 2030 (يمكن اختيار السنة الحالية افتراضياً)
        current_year = date.today().year
        selected_year = st.selectbox(
            "📅 اختر السنة للمتابعة:",
            options=list(range(2024, 2031)),
            index=list(range(2024, 2031)).index(current_year) if current_year in range(2024, 2031) else 2
        )

    st.subheader(f"📌 إضافة / تحديث دعم شهر لسنة ({selected_year})")

    # قائمة الأشهر
    months_list = [
        "يناير (1)", "فبراير (2)", "مارس (3)", "أبريل (4)",
        "مايو (5)", "يونيو (6)", "يوليو (7)", "أغسطس (8)",
        "سبتمبر (9)", "أكتوبر (10)", "نوفمبر (11)", "ديسمبر (12)"
    ]

    with st.form("schedule_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            selected_month = st.selectbox("اختر الشهر", months_list)
            supporter = st.text_input("الداعم / الجهة الداعمة")
            support_amount = st.number_input("مبلغ الدعم (بالريال)", min_value=0.0, step=100.0)

        with col2:
            # خيار تحديد هل تم الدعم مع إمكانية إدخال التاريخ بأثر رجعي
            support_actual_date = st.date_input("تاريخ الدعم الفعلي (يمكن اختياره بأثر رجعي)", value=date.today())
            has_supported = st.checkbox("تأكيد إتمام الدعم لهذا الشهر", value=True)
            schedule_notes = st.text_input("ملاحظات إضافية")

        submit_schedule = st.form_submit_button("💾 حفظ / تحديث دعم الشهر")

        if submit_schedule:
            if supporter.strip() != "":
                # تاريخ الدعم المسجل
                date_str = str(support_actual_date) if has_supported else "لم يتم الدعم بعد"

                # التحقق مما إذا كان السجل موجوداً لنفس السنة والشهر للتحديث
                mask = (df_schedule["السنة"] == selected_year) & (df_schedule["الشهر"] == selected_month)
                
                if not df_schedule[mask].empty:
                    # تحديث السجل الحالي
                    df_schedule.loc[mask, "الداعم / الجهة"] = supporter.strip()
                    df_schedule.loc[mask, "مبلغ الدعم"] = support_support_amount if 'support_support_amount' in locals() else support_amount
                    df_schedule.loc[mask, "تاريخ الدعم الفعلية"] = date_str
                    df_schedule.loc[mask, "ملاحظات"] = schedule_notes.strip()
                else:
                    # إضافة سجل جديد
                    new_entry = pd.DataFrame({
                        "السنة": [int(selected_year)],
                        "الشهر": [selected_month],
                        "الداعم / الجهة": [supporter.strip()],
                        "مبلغ الدعم": [support_amount],
                        "تاريخ الدعم الفعلية": [date_str],
                        "ملاحظات": [schedule_notes.strip()]
                    })
                    df_schedule = pd.concat([df_schedule, new_entry], ignore_index=True)

                df_schedule.to_csv(SCHEDULE_FILE, index=False)
                st.success(f"✅ تم حفظ بيانات شهر ({selected_month}) لسنة {selected_year} بنجاح!")
                st.rerun()
            else:
                st.error("⚠️ يرجى كتابة اسم الداعم أو الجهة.")

    st.divider()

    # عرض جدول السنة المختارة فقط
    st.subheader(f"📊 جدول دعم الأشهر لسنة {selected_year}")
    
    # تصفية البيانات حسب السنة المختارة
    year_data = df_schedule[df_schedule["السنة"] == selected_year] if not df_schedule.empty else pd.DataFrame()

    if not year_data.empty:
        # ترتيب العرض
        display_df = year_data[["الشهر", "الداعم / الجهة", "مبلغ الدعم", "تاريخ الدعم الفعلية", "ملاحظات"]].reset_index(drop=True)
        st.dataframe(display_df, use_container_width=True)

        # إحصائية بسيطة للسنة المختارة
        total_year_support = year_data["مبلغ الدعم"].sum()
        st.info(f"💡 **إجمالي الدعم المسجل لسنة {selected_year}:** {total_year_support:,.2f} ريال")
    else:
        st.warning(f"لا توجد بيانات مسجلة لسنة {selected_year} حتى الآن.")
