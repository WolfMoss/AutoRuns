import pymysql
import plotly.graph_objects as go


def get_pcr_data():
    db = pymysql.connect(
        host='axiba.idnmd.top',
        user='root',
        passwd='ilikecs123!',
        port=8306,
        db='quant'
    )
    cursor = db.cursor()

    query = f"""
    SELECT cj_date, cj_top5_proportion,cj_szzs
    FROM a_cj
    ORDER BY cj_date ASC
    """
    cursor.execute(query)
    results = cursor.fetchall()
    db.close()

    cj_dates = [row[0] for row in results]
    cj_top5_proportions = [row[1] for row in results]
    cj_szzss = [row[2] for row in results]

    return cj_dates, cj_top5_proportions,cj_szzss


def plot_pcr_data(cj_dates, cj_top5_proportions,cj_szzss):
    fig = go.Figure()

    # 添加第一个散点图数据，使用默认的 y 轴
    fig.add_trace(go.Scatter(x=cj_dates, y=cj_top5_proportions, mode='lines+markers', name='Top 5 Proportions'))

    # 添加第二个散点图数据，使用第二个 y 轴
    fig.add_trace(go.Scatter(x=cj_dates, y=cj_szzss, mode='lines+markers', name='SZZSS', yaxis='y2'))

    # 更新布局
    fig.update_layout(
        title='前五成交额占比情绪图',
        xaxis_title='Date',
        yaxis_title='Top 5 Proportions',
        yaxis2=dict(
            title='SZZSS',
            overlaying='y',
            side='right'
        ),
        xaxis=dict(
            rangeselector=dict(
                buttons=list([
                    dict(count=1, label="1m", step="month", stepmode="backward"),
                    dict(count=6, label="6m", step="month", stepmode="backward"),
                    dict(count=1, label="YTD", step="year", stepmode="todate"),
                    dict(count=1, label="1y", step="year", stepmode="backward"),
                    dict(step="all")
                ])
            ),
            rangeslider=dict(visible=True),
            type="date",
            tickformat="%Y-%m-%d"  # 设置日期格式为 YYYY-MM-DD
        ),
        hovermode='x'
    )

    fig.show()


# 获取数据
cj_dates, cj_top5_proportions,cj_szzss = get_pcr_data()

# 生成折线图
plot_pcr_data(cj_dates, cj_top5_proportions,cj_szzss)
