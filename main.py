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

def get_logs():
    # API에서 로그를 가져옴
    response = requests.get(f"{API_URL}/logs")
    if response.status_code == 200:
        log_data = response.text.split("\n")
        # 각 로그 항목을 JSON으로 파싱함
        return [json.loads(log_str) for log_str in log_data if log_str]
    return None

def get_company_parm(json_file_path, company_name, request_parm):
    try:
        with open(json_file_path, 'r', encoding='utf-8') as file:
            data = json.load(file)
        # 지정된 회사에 대한 요청된 매개변수를 찾음
        for entry in data["info"]:
            if entry["company"] == company_name:
                return entry.get(request_parm)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        print(f"Error: {e}")
    return None

def parse_log(logs):
    # 파싱된 로그 데이터를 저장할 리스트를 초기화함
    time_list, company_list, path, status_code, duration = [], [], [], [], []
    current_time = datetime.now()
    
    for log in logs[0]:
        log_list = re.split('[:|,|}]', log)
        try:
            if log_list[7][2:-1] == "POST":
                # 시간 정보를 추출하고 포맷함
                time_info = f"{log_list[5][2:6]}년 {log_list[5][6:8]}월 {log_list[5][8:10]}일 {log_list[5][10:12]}:{log_list[5][12:14]}"
                compare_time = datetime.strptime(time_info, "%Y년 %m월 %d일 %H:%M")

                if current_time < compare_time:
                    continue
                # 파싱된 데이터를 각각의 리스트에 추가함
                time_list.append(time_info)
                company_list.append(log_list[3][2:-1])
                path.append(log_list[9].split('/')[-1][:-1])
                status = "성공" if log_list[11][1:] == '200' else '실패'
                status_code.append(status)
                duration.append(float(log_list[13][1:5]))
        except Exception as e:
            print(f"Error parsing log: {e}")
    return time_list, company_list, path, status_code, duration

def main():
    st.title("서비스 사용이력")
    logs = get_logs()
    
    if logs:
        st.write("Logs from FastAPI:")
        # 로그를 파싱하고 데이터를 추출함
        time_list, company_list, path, status_code, duration = parse_log(logs)
    else:
        st.error("No logs found")
        return

    # 파싱된 로그 데이터로 데이터프레임을 생성
    df = pd.DataFrame({
        '회사명': company_list,
        '요청 시각': time_list,
        '요청한 api': path,
        '성공 여부': status_code,
        '처리 시간': duration
    })

    # 시작 월에 대한 회사 목록
    june_list = ['제이투케이코리아 주식회사', '(주)지에프인터랙티브', '앙비떼', '매직스코리아 주식회사', '주식회사 예지컴퍼니', '주식회사 더웨이유']
    august_list = ['주식회사 유스비', '두리홈데코', '주식회사 제이로브컴퍼니', '딥테크', '영웅딸기']

    st.sidebar.title('조회하기')

    # 사이드바 설정
    select_company = st.sidebar.selectbox(
        '조회하고자 하는 기업을 선택하세요',
        june_list + august_list
    )

    with st.sidebar:
        # 선택한 회사에 따라 조회할 월을 선택함
        if select_company in june_list:
            select_month = st.radio('조회하고자 하는 월을 선택하세요', ['6월', '7월', '8월', '9월', '10월'])
        else:
            select_month = st.radio('조회하고자 하는 월을 선택하세요', ['8월', '9월', '10월'])

    json_file_path = 'login_info.json'
    with open(json_file_path, 'r', encoding='utf-8') as file:
        data = json.load(file)

    info_list = []
    continue_list = [0, 3, 7]
    for entry in data["info"]:
        # 선택한 회사의 정보를 추출
        if entry["company"] == select_company:
            # continue_list에 포함되지 않은 인덱스의 값을 info_list에 추가함
            info_list.extend(entry[i] for index, i in enumerate(entry.keys()) if index not in continue_list)

    string_list = ['대표자명', '사용자 ID', '사용자 API', '사업자번호', '관리자 생년월일', '대표자 전화번호']
    for i, value in enumerate(string_list):
        # 사이드바에 회사 정보 표시
        st.sidebar.info(f"{value} : {info_list[i]}")

    # 데이터프레임의 '요청 시각'을 datetime 형식으로 변환함
    df['요청시각'] = pd.to_datetime(df['요청 시각'], format='%Y년 %m월 %d일 %H:%M')
    # 선택한 월과 회사에 따라 데이터를 필터링함
    tmp_df = df[df['요청시각'].dt.month == int(select_month[:-1])]
    tmp_df = tmp_df[tmp_df['회사명'] == select_company]
    tmp_df['요청한 api'] = info_list[2]
    tmp_df = tmp_df.reset_index(drop=True)
    tmp_df.index += 1

    # Log에 대한 통계량 계산
    use_api = [info_list[2]]
    total_count = [tmp_df.shape[0]]
    pct_succeed = f"{(tmp_df[tmp_df['성공 여부'] == '성공'].shape[0] / total_count[0]) * 100:.2f}%" if total_count[0] > 0 else "0%"
    avg_succeed = [pct_succeed]
    avg_duration = [tmp_df['처리 시간'].mean()]

    # 통계량을 데이터프레임으로 생성함
    stat_df = pd.DataFrame({
        '사용 API': use_api,
        '콜링 횟수': total_count,
        '평균 처리 시간': avg_duration,
        '콜링 성공률': avg_succeed
    }).set_index(['사용 API'])

    # 시각화 설정
    fig = make_subplots(1, 3, subplot_titles=['총 콜링 횟수', '평균 처리 시간', '콜링 성공률'])
    fig.add_trace(go.Bar(x=['콜링 횟수'], y=total_count, showlegend=False), 1, 1)
    fig.add_trace(go.Bar(x=['평균 처리 시간'], y=avg_duration, showlegend=False), 1, 2)
    fig.add_trace(go.Bar(x=['콜링 성공률'], y=avg_succeed, showlegend=False), 1, 3)

    # y축 범위를 설정함
    fig.update_yaxes(range=[0, 2000], row=1, col=1)
    fig.update_yaxes(range=[0, 5], row=1, col=2)
    fig.update_yaxes(range=[0, 100], row=1, col=3)

    # 대시보드에 그래프와 테이블 시각화
    st.plotly_chart(fig)
    st.table(stat_df)
    st.table(tmp_df.iloc[:, 0:5])

    # 6초 후에 대시보드를 갱신함
    time.sleep(6)
    st.rerun()

if __name__ == "__main__":
    main()








