import streamlit as st
import requests
import json
import pandas as pd
import re
import plotly.express as px
from plotly.subplots import make_subplots
import plotly.graph_objects as go
from datetime import datetime
import time

API_URL = "http://203.252.147.202:8000"

def fetch_logs():
    """API에서 로그 데이터 가져오기"""
    try:
        response = requests.get(f"{API_URL}/logs")
        response.raise_for_status()
        return [json.loads(log) for log in response.text.split("\n") if log]
    except requests.RequestException as e:
        st.error(f"Error fetching logs: {e}")
        return []

def parse_log(log):
    """로그 데이터를 파싱."""
    log_list = re.split('[:|,|}]', log)
    if len(log_list) < 14 or log_list[7][2:-1] != "POST":
        return None

    time_info = f"{log_list[5][2:6]}년 {log_list[5][6:8]}월 {log_list[5][8:10]}일 {log_list[5][10:12]}:{log_list[5][12:14]}"
    company_info = log_list[3][2:-1]
    path_endpoint = log_list[9].split('/')[-1][:-1]
    status = "성공" if log_list[11][1:] == '200' else "실패"
    duration_time = float(log_list[13][1:5])

    return {
        "time_info": time_info,
        "company_info": company_info,
        "path_endpoint": path_endpoint,
        "status": status,
        "duration_time": duration_time
    }

def get_company_info(json_file_path, company_name):
    """지정된 JSON 파일에서 회사 정보 뽑기"""
    try:
        with open(json_file_path, 'r', encoding='utf-8') as file:
            data = json.load(file)
        return next((entry for entry in data["info"] if entry["company"] == company_name), None)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        st.error(f"Error loading company info: {e}")
        return None

def main():

    st.title("서비스 사용이력")
    logs = fetch_logs()
    parsed_logs = [parse_log(log) for log in logs[0] if parse_log(log)]
    
    if not parsed_logs:
        st.error("No valid logs found")
        return

    df = pd.DataFrame(parsed_logs)
    df['요청시각'] = pd.to_datetime(df['time_info'], format='%Y년 %m월 %d일 %H:%M')

    # 조회 가능한 회사 목록 (시작 날짜)
    june_list = ['제이투케이코리아 주식회사', '(주)지에프인터랙티브', '앙비떼', '매직스코리아 주식회사', '주식회사 예지컴퍼니', '주식회사 더웨이유']
    august_list = ['주식회사 유스비', '두리홈데코', '주식회사 제이로브컴퍼니', '딥테크', '영웅딸기']

    # 사이드바에서 회사와 월 선택
    st.sidebar.title('조회하기')
    select_company = st.sidebar.selectbox('조회하고자 하는 기업을 선택하세요', june_list + august_list)
    select_month = st.sidebar.radio('조회하고자 하는 월을 선택하세요', ['6월', '7월', '8월', '9월', '10월'] if select_company in june_list else ['8월', '9월', '10월'])

    # 선택한 회사의 정보 표시
    company_info = get_company_info('login_info.json', select_company)
    if company_info:
        info_keys = ['대표자명', '사용자 ID', '사용자 API', '사업자번호', '관리자 생년월일', '대표자 전화번호']
        for key in info_keys:
            st.sidebar.info(f"{key} : {company_info.get(key, '정보 없음')}")

    # 선택한 월과 회사에 대한 데이터 필터링
    tmp_df = df[df['요청시각'].dt.month == int(select_month[:-1])]
    tmp_df = tmp_df[tmp_df['company_info'] == select_company]
    tmp_df = tmp_df.reset_index(drop=True)
    tmp_df.index += 1

    # 통계량 계산
    use_api = company_info.get('사용자 API', '정보 없음')
    total_count = tmp_df.shape[0]
    pct_succeed = f"{(tmp_df[tmp_df['status'] == '성공'].shape[0] / total_count) * 100:.2f}%" if total_count else "0%"
    avg_duration = tmp_df['duration_time'].mean()

    # 통계 데이터프레임 생성
    stat_df = pd.DataFrame({
        '사용 API': [use_api],
        '콜링 횟수': [total_count],
        '평균 처리 시간': [avg_duration],
        '콜링 성공률': [pct_succeed]
    }).set_index(['사용 API'])

    # 시각화 생성
    fig = make_subplots(1, 3, subplot_titles=['총 콜링 횟수', '평균 처리 시간', '콜링 성공률'])
    fig.add_trace(go.Bar(x=['콜링 횟수'], y=[total_count], showlegend=False), 1, 1)
    fig.add_trace(go.Bar(x=['평균 처리 시간'], y=[avg_duration], showlegend=False), 1, 2)
    fig.add_trace(go.Bar(x=['콜링 성공률'], y=[pct_succeed], showlegend=False), 1, 3)

    # y축 범위 설정
    fig.update_yaxes(range=[0, 2000], row=1, col=1)
    fig.update_yaxes(range=[0, 5], row=1, col=2)
    fig.update_yaxes(range=[0, 100], row=1, col=3)

    # 결과 출력
    st.plotly_chart(fig)
    st.table(stat_df)
    st.table(tmp_df.iloc[:, :5])

    # 6초마다 새로고침
    time.sleep(6)
    st.rerun()

if __name__ == "__main__":
    main()