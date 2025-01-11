"""
邢不行｜策略分享会
选股策略框架𝓟𝓻𝓸

版权所有 ©️ 邢不行
微信: xbx1717

本代码仅供个人学习使用，未经授权不得复制、修改或用于商业用途。

Author: 邢不行
"""
import os
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.offline import plot
from plotly.subplots import make_subplots
from plotly.io import to_html


def draw_equity_curve_plotly(df, data_dict, date_col=None, right_axis=None, pic_size=None, chg=False,
                             title=None, rtn_add=pd.DataFrame(), desc=None, to_zero=True):
    if pic_size is None:
        pic_size = [1500, 572]

    draw_df = df.copy()

    # 设置时间序列
    if date_col:
        time_data = draw_df[date_col]
    else:
        time_data = draw_df.index

    # 绘制左轴数据
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    for key in data_dict:
        if chg:
            draw_df[data_dict[key]] = (draw_df[data_dict[key]] + 1).fillna(1).cumprod()
        fig.add_trace(go.Scatter(x=time_data, y=draw_df[data_dict[key]], name=key, ))

    # 绘制右轴数据
    # 绘制右轴数据
    if right_axis:
        key = list(right_axis.keys())[0]
        if to_zero:
            fig.add_trace(go.Scatter(x=time_data, y=draw_df[right_axis[key]], name=key + '(右轴)', opacity=0.1,
                                     marker_color='orange', line=dict(width=0), fill='tozeroy',
                                     yaxis='y2'))  # 标明设置一个不同于trace1的一个坐标轴
        else:
            fig.add_trace(go.Scatter(x=time_data, y=draw_df[right_axis[key]], name=key + '(右轴)', yaxis='y2'))
    fig.update_layout(template="none", width=pic_size[0], height=pic_size[1],
                      title={'text': title, 'x': 170 / pic_size[0], 'xanchor': 'left'},
                      hovermode="x unified", hoverlabel=dict(bgcolor='rgba(255,255,255,0.5)', ), margin=dict(t=50),
                      annotations=[dict(text=desc, xref='paper', yref='paper', x=0.005, y=1.05, showarrow=False,
                                        font=dict(size=12, color='black'), align='left',
                                        bgcolor='rgba(255,255,255,0.8)')])
    x_limit = 0.98 if rtn_add.empty else 0.73
    fig.update_layout(
        updatemenus=[dict(buttons=[dict(label="线性 y轴", method="relayout", args=[{"yaxis.type": "linear"}]),
                                   dict(label="Log y轴", method="relayout", args=[{"yaxis.type": "log"}]), ])],
        xaxis=dict(domain=[0.0, x_limit]))

    fig.update_yaxes(showspikes=True, spikemode='across', spikesnap='cursor', spikedash='solid', spikethickness=1)
    fig.update_xaxes(showspikes=True, spikemode='across+marker', spikesnap='cursor', spikedash='solid',
                     spikethickness=1)
    if not rtn_add.empty:
        # 把rtn放进图里
        rtn_add = rtn_add.T
        rtn_add['最大回撤开始时间'] = rtn_add['最大回撤开始时间'].str.replace('00:00:00', '')
        rtn_add['最大回撤结束时间'] = rtn_add['最大回撤结束时间'].str.replace('00:00:00', '')
        rtn_add = rtn_add.T
        header_list = ['项目', '策略表现'] if rtn_add.shape[1] == 1 else ['项目'] + list(rtn_add.columns)
        rtn_add.reset_index(drop=False, inplace=True)
        table_trace = go.Table(header=dict(values=header_list),
                               cells=dict(values=rtn_add.T.values.tolist()),
                               domain=dict(x=[0.77, 1.0], y=[0.0, 0.79]))
        fig.add_trace(table_trace)
        # 图例调一下位置
        fig.update_layout(legend=dict(x=0.8, y=1))

    return_fig = plot(fig, include_plotlyjs=True, output_type='div')
    return return_fig


def draw_table(table_df, width=1500, row_height=26, title=None, max_line_length=200, first_col_width=53):
    """
    绘制表格
    :param table_df: 表格数据
    :param width: 图片的宽度
    :param row_height: 表格的默认行高
    :param title: 表格的标题
    :param max_line_length: 每行文字的最大长度（超过则换行）
    :param first_col_width: 第一列的固定宽度
    :return: 返回表格的 HTML div
    """
    # 计算每一列的最大宽度
    max_widths = [max([len(str(value)) for value in table_df[col]]) for col in table_df.columns]

    # 设置列宽
    # 第一列固定宽度，其他列按比例分配剩余宽度
    remaining_width = width - first_col_width  # 剩余宽度
    other_col_widths = [max_width / np.sum(max_widths[1:]) * remaining_width for max_width in max_widths[1:]]
    column_width = [first_col_width] + other_col_widths  # 第一列固定宽度，其他列按比例分配

    # 自动换行函数
    def wrap_text(text, max_length):
        if not isinstance(text, str):
            text = str(text)
        words = text.split()
        lines = []
        current_line = ""
        for word in words:
            if len(current_line) + len(word) + 1 <= max_length:
                current_line += (" " + word if current_line else word)
            else:
                lines.append(current_line)
                current_line = word
        if current_line:
            lines.append(current_line)
        return "<br>".join(lines)

    # 对表格中的每个单元格应用自动换行
    wrapped_values = table_df.applymap(lambda x: wrap_text(x, max_line_length))

    # 计算每行的最大高度（根据换行后的行数）
    row_heights = []
    for _, row in wrapped_values.iterrows():
        max_lines = max([len(str(cell).split("<br>")) for cell in row])
        row_heights.append(max_lines * row_height)

    # 计算表格的总高度
    total_height = sum(row_heights) + 107  # 107 是标题和边距的额外高度

    # 创建表格
    table_trace = go.Table(
        header=dict(
            values=list(table_df.columns),
            align='left',  # 表头左对齐
            fill=dict(color='lightgrey')  # 表头背景色
        ),
        cells=dict(
            values=wrapped_values.T.values.tolist(),
            align='left',  # 单元格内容左对齐
            line=dict(width=1, color='grey'),  # 单元格边框
            font=dict(size=12)  # 字体大小
        ),
        columnwidth=column_width  # 设置列宽
    )

    # 创建图表
    fig = go.Figure(data=[table_trace])
    fig.update_layout(
        width=width,
        height=total_height,  # 动态调整总高度
        title_text=title,
        title_x=0.5,
        margin=dict(t=50, b=20, l=20, r=20)  # 调整边距
    )

    # 返回 HTML div
    return_fig = plot(fig, include_plotlyjs=True, output_type='div')
    return return_fig


def merge_html(fig_path, fig_list):
    # 创建自定义HTML页面，嵌入fig对象的HTML内容
    html_content = """
    <!DOCTYPE html>
    <html>
    <head>
    <meta Charset="UTF-8">
    <style>
        .figure-container {{
            display: flex;
            flex-direction: column;
            align-items: center;
        }}
    </style>
    </head>
    <body>"""
    for fig in fig_list:
        # 将fig对象转换为HTML字符串
        if not isinstance(fig, str):
            fig = to_html(fig, full_html=False)
        html_content += f"""
        <div class="figure-container">
            {fig}
        </div>
        """
    html_content += '</body> </html>'

    # 保存自定义HTML页面
    with open(fig_path, 'w', encoding='utf-8') as f:
        f.write(html_content)

    res = os.system('start ' + str(fig_path))
    if res != 0:
        os.system('open ' + str(fig_path))
