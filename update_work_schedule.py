import psycopg2

conn = psycopg2.connect(host='127.0.0.1', dbname='fitnexus', user='postgres', password='postgres')
cur = conn.cursor()
cur.execute("UPDATE devices SET work_schedule = '{\"start\": \"08:00\", \"end\": \"22:00\"}' WHERE code = 'turnstile_test_de2736';")
conn.commit()
cur.close()
conn.close()
print('Work schedule updated!')
