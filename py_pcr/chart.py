import pymysql
import plotly.graph_objects as go


def get_pcr_data(security_code):
    db = pymysql.connect(
        host='axiba.idnmd.top',
        user='root',
        passwd='ilikecs123!',
        port=8306,
        db='quant'
    )
    cursor = db.cursor()

    query = f"""
    SELECT TRADE_DATE, PC_RATE
    FROM pcr
    WHERE SECURITY_CODE = '{security_code}'
    ORDER BY TRADE_DATE ASC
    """
    cursor.execute(query)
    results = cursor.fetchall()
    db.close()

    dates = [row[0] for row in results]
    pc_rates = [row[1] for row in results]

    return dates, pc_rates


def plot_pcr_data(dates, pc_rates):
    fig = go.Figure(data=go.Scatter(x=dates, y=pc_rates, mode='lines+markers', name='PCR Rate'))

    fig.update_layout(
        title='510300 PCR Rate Over Time',
        xaxis_title='Date',
        yaxis_title='PCR Rate',
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
dates, pc_rates = get_pcr_data('510300')

# 生成折线图
plot_pcr_data(dates, pc_rates)
