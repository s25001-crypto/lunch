import streamlit as st
import requests
import datetime
import calendar
import re

st.set_page_config(page_title="월간 학교 급식 달력", page_icon="📅", layout="wide")
st.title("📅 우리 학교 월간 급식 달력")
st.caption("선택한 월의 급식 메뉴와 매운맛, 알레르기 정보를 한눈에 확인합니다.")

ALLERGY_MAP = {
    1: "난류", 2: "우유", 3: "메밀", 4: "땅콩", 5: "대두",
    6: "밀", 7: "고등어", 8: "게", 9: "새우", 10: "돼지고기",
    11: "복숭아", 12: "토마토", 13: "아황산류", 14: "호두", 15: "닭고기",
    16: "쇠고기", 17: "오징어", 18: "조개류(굴/전복/홍합 포함)", 19: "잣",
}

def replace_allergy_codes(dish_text, convert_to_text=True, highlight_spicy=True):
    """메뉴명 뒤의 알레르기 번호를 치환하고, 매운 음식 메뉴를 시각적으로 강조합니다."""
    if not dish_text:
        return dish_text

    spicy_keywords = ["매운", "불닭", "김치찌개", "부대찌개", "떡볶이", "닭갈비", "오징어볶음", "제육볶음", "고추장", "청양", "마라", "낙지", "짬뽕"]

    def convert_match(match):
        raw = match.group(0)
        nums = re.findall(r"\d+", raw)
        allergens = [ALLERGY_MAP[int(n)] for n in nums if int(n) in ALLERGY_MAP]
        if convert_to_text and allergens:
            return f" :orange[[{', '.join(allergens)}]]"
        return raw

    pattern = r"\(?(\d+\.)+\)?"
    processed_text = re.sub(pattern, convert_match, dish_text)

    if highlight_spicy:
        lines = processed_text.split("\n")
        highlighted_lines = []
        for line in lines:
            is_spicy = any(kw in line for kw in spicy_keywords)
            if is_spicy and "🔥" not in line:
                highlighted_lines.append(f"🔥 {line}")
            else:
                highlighted_lines.append(line)
        processed_text = "\n".join(highlighted_lines)

    return processed_text

st.sidebar.header("⚙️ 학교 정보 설정")
office_code = st.sidebar.text_input("시도교육청코드", value="T10", help="기본값: 제주특별자치도교육청(T10)")
school_code = st.sidebar.text_input("표준학교코드", value="9290088", help="기본값: 제주중앙고등학교(9290088)")

st.sidebar.markdown("---")
st.sidebar.subheader("🍽️ 부가 정보 설정")
show_allergen_names = st.sidebar.toggle(
    "알레르기 식품명으로 변환", value=True,
    help="체크 시 숫자 대신 [난류, 대두] 형태로 변환하여 표시합니다.",
)
show_spicy_icon = st.sidebar.toggle(
    "매운 음식 아이콘 표시 (🔥)", value=True,
    help="매운맛이 예상되는 메뉴 앞에 불꽃 아이콘을 표시합니다.",
)

with st.sidebar.expander("📖 나이스 알레르기 번호 안내표"):
    table_md = "\n".join([f"- **{k}번**: {v}" for k, v in ALLERGY_MAP.items()])
    st.markdown(table_md)

today = datetime.date.today()
col_y, col_m, col_filter = st.columns([1, 1, 2])
with col_y:
    year = st.selectbox("연도 선택", options=list(range(today.year - 1, today.year + 2)), index=1)
with col_m:
    month = st.selectbox("월 선택", options=list(range(1, 13)), index=today.month - 1)
with col_filter:
    meal_filter = st.radio(
        "급식 종류 선택", options=["전체 보기", "중식만 보기", "석식만 보기"], index=0, horizontal=True,
    )

def fetch_monthly_meals(key, ofcdc_code, schul_code, yr, mo):
    """선택한 월의 1일부터 말일까지의 급식을 조회합니다."""
    _, last_day = calendar.monthrange(yr, mo)
    from_ymd = f"{yr}{mo:02d}01"
    to_ymd = f"{yr}{mo:02d}{last_day:02d}"
    url = "https://open.neis.go.kr/hub/mealServiceDietInfo"
    params = {
        "KEY": key,
        "Type": "json",
        "pIndex": 1,
        "pSize": 100,
        "ATPT_OFCDC_SC_CODE": ofcdc_code,
        "SD_SCHUL_CODE": schul_code,
        "MLSV_FROM_YMD": from_ymd,
        "MLSV_TO_YMD": to_ymd,
    }
    
    try:
        response = requests.get(url, params=params)
        data = response.json()
        if "mealServiceDietInfo" in data:
            rows = data["mealServiceDietInfo"][1]["row"]
            meal_dict = {}
            for row in rows:
                ymd = row["MLSV_YMD"]
                m_code = row["MMEAL_SC_CODE"]  # 1: 조식, 2: 중식, 3: 석식
                m_name = row["MMEAL_SC_NM"]
                dish_info = row["DDISH_NM"].replace("<br/>", "\n")
                if ymd not in meal_dict:
                    meal_dict[ymd] = {}
                meal_dict[ymd][m_code] = {
                    "name": m_name,
                    "dish": dish_info
                }
            return meal_dict
    except Exception as e:
        st.error(f"급식 데이터를 불러오는 중 오류가 발생했습니다: {e}")
    return {}

meals_data = fetch_monthly_meals("", office_code, school_code, year, month)

st.markdown("---")

if not meals_data:
    st.info("해당 기간에 등록된 급식 데이터가 없습니다.")
else:
    _, last_day = calendar.monthrange(year, month)
    first_weekday, _ = calendar.monthrange(year, month)  # 0: 월요일, 6: 일요일
    
    current_date = 1
    weeks = []
    week = [None] * first_weekday
    
    while current_date <= last_day:
        week.append(current_date)
        if len(week) == 7:
            weeks.append(week)
            week = []
        current_date += 1
        
    if week:
        week.extend([None] * (7 - len(week)))
        weeks.append(week)
        
    weekdays_kr = ["월", "화", "수", "목", "금", "토", "일"]
    
    for week_days in weeks:
        cols = st.columns(7)
        for d_idx, day in enumerate(week_days):
            with cols[d_idx]:
                st.markdown(f"**{weekdays_kr[d_idx]}**")
                if day is not None:
                    ymd_str = f"{year}{month:02d}{day:02d}"
                    st.subheader(f"{day}일")
                    
                    if ymd_str in meals_data:
                        day_meals = meals_data[ymd_str]
                        for m_code, m_info in day_meals.items():
                            if meal_filter == "중식만 보기" and m_code != "2":
                                continue
                            if meal_filter == "석식만 보기" and m_code != "3":
                                continue
                                
                            st.markdown(f"**[{m_info['name']}]**")
                            processed_dish = replace_allergy_codes(
                                m_info['dish'], 
                                convert_to_text=show_allergen_names, 
                                highlight_spicy=show_spicy_icon
                            )
                            st.markdown(processed_dish)
                            st.write("")
                    else:
                        st.caption("급식 없음")
                else:
                    st.write("")
        st.markdown("---")
