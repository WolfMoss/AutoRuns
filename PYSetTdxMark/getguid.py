import pymysql
import uuid

# 创建数据库连接
connection = pymysql.connect(host='axiba.idnmd.top', user='root', passwd='ilikecs123!', port=8306, db='quant')

try:
    with connection.cursor() as cursor:
        # 生成十个GUID
        guids = [str(uuid.uuid4()) for _ in range(1000)]

        # 构建插入语句
        for guid in guids:
            sql = "INSERT INTO gainian_key (key_guid, is_used) VALUES (%s, %s)"
            cursor.execute(sql, (guid, 0))

        # 提交事务
        connection.commit()

except pymysql.MySQLError as e:
    print(f"Error: {e}")

finally:
    # 关闭数据库连接
    connection.close()
