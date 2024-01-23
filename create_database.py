import sqlite3
import os
from datetime import *
import sys


'''Global functions that may be called '''

def assert_valid_datetime_format(date_string):
    try:
        #datetime.datetime.
        datetime.strptime(date_string, '%Y-%m-%d %H:%M:%S.%f')
        print(f"{date_string} is a valid SQL datetime format")
        return True
    except ValueError:
        print(f"{date_string} is not a valid SQL datetime format")
        return False


class fibre_database:

    '''
    A class to create the structure of the fibre calibration database.

    Attributes:
    -----------
    fibid: int
    An integer to represent the fibre ID number
    tble: str
    A string to represent the names of each table in the database, which represents a different move type
    item: tuple
    A tuple that contains each component for a single database entry, current length 17
    id_sequence: list
    A list of fibre id numbers (integers) that will be processed
    filename: str
    The name of the logfile

    Methods:
    --------
    create_tables()
    Creates the database structure. This is a reginal database which contains three tables, one for each movement type, which stores the attributes in the list below.
    [Move_id, Fibreid, Robot, Plate, Move_start, Move_end, Traj_X, Traj_Y, Release_X, Release_Y, Carry_X, Carry_Y, Gripper_X, Gripper_Y, Targ_X, Targ_Y, Rot, Elev, Logname]
    This database is stored within WEAVE/var.

    add_move(item, tble='moves')
    Inserts a new entry to the database. the tble attricute is set to 'moves' by default but can also be changed to 'parks' or 'unparks'

    check_count(fibid, tble)
    Returns the total number of database entries for a chosen fibre number in the selected table

    update_move(item, tble, fibid)
    modifies a database entry to contain new information based on the oldest entry stored

    evaluate_logfile(id_sequence)
    prints the number of moves for each type as a statement for a sequence of fibre ID's

    check_count(tble)
    returns all entries in a table for a specified fibre ID number

    count_all_moves(tble)
    gives the total number of entries in a table

    scrub_logfile(filename)
    removes all entries from a specified logfile that has been processed into the database

    get_attribute(attribute, fibrelist, columnlist)
    a function to extract a specific database attribute for a sequence of fibres
    
    scrub_fibre_entries(fibre_id, datetime)
    a function to remove all entries for a specific fibre ID before a specified datetime

    '''
    def __init__(self, backup=False):
        """Initialises the class and establishes a connction to the database"""            
        self.conn = sqlite3.connect('/home/pos_eng/WEAVE/var/fibre_moves.db')
        if backup:
            self.conn = sqlite3.connect('/home/pos_eng/WEAVE/pos/positioner/python/FIBRE_CALIB_STORE/database/backups/fibre_moves.db')
        self.c = self.conn.cursor()
        self.tables = ['moves', 'parks', 'unparks']

    def create_tables(self):
        """A function to create the database structure. It contains three tables called moves, parks, and unparks. 
           Each fibre will have multiple movement entries with unique timestamps and placement information"""
        self.c.execute("""CREATE TABLE moves(
                Move_id INTEGER PRIMARY KEY AUTOINCREMENT,
                Fibreid INTEGER,
                Robot INTEGER,
                Plate INTEGER,
                Move_start DATETIME,
                Move_end DATETIME,
                Traj_X REAL,
                Traj_Y REAL,
                Release_X REAL,
                Release_Y REAL,
                Carry_X REAL,
                Carry_Y REAL,
                Gripper_X REAL,
                Gripper_Y REAL,
                Targ_X REAL,
                Targ_Y REAL,
                Rot NULL,
                Elev NULL,
                Logname TEXT
                );""")

        self.c.execute("""CREATE TABLE parks(
                Move_id INTEGER PRIMARY KEY AUTOINCREMENT,
                Fibreid INTEGER,
                Robot INTEGER,
                Plate INTEGER,
                Move_start DATETIME,
                Move_end DATETIME,
                Traj_X REAL,
                Traj_Y REAL,
                Release_X REAL,
                Release_Y REAL,
                Carry_X REAL,
                Carry_Y REAL,
                Gripper_X REAL,
                Gripper_Y REAL,
                TARG_X REAL,
                TARG_Y REAL,
                Rot Null,
                Elev NULL,
                Logname TEXT
                );""")

        self.c.execute("""CREATE TABLE unparks (
                Move_id INTEGER PRIMARY KEY AUTOINCREMENT,
                Fibreid INTEGER,
                Robot INTEGER,
                Plate INTEGER,
                Move_start DATETIME,
                Move_end DATETIME,
                Traj_X REAL,
                Traj_Y REAL,
                Release_X REAL,
                Release_Y REAL,
                Carry_X REAL,
                Carry_Y REAL,
                Gripper_X REAL,
                Gripper_Y REAL,
                TARG_X REAL,
                TARG_Y REAL,
                Rot NULL,
                Elev NULL,
                Logname TEXT
                );""")
        #number of columns = 17 at this stage #18 now with Logname
        #Move_id INTEGER PRIMARY KEY AUTOINCREMENT,
        self.conn.commit()
        self.tables = ['moves', 'parks', 'unparks']
        return 'Tables created'

    def check_count(self, fibid, tble):
        """A function to return the number of entries stored in a specified database table for an individual fibre ID."""
        assert tble in self.tables, 'tble variable must be either moves, parks, or unparks'
        tup = (str(fibid),)
        self.c.execute("""SELECT COUNT(*) from """+str(tble)+"""
                        WHERE Fibreid = ?;""", tup)
        count = self.c.fetchall()

        return count

    def add_move(self, item, tble="moves"):
        """A function to add an entry to a specific table within the database"""
        assert tble in self.tables, 'tble variable must be either moves, parks, or unparks'
        assert type(item)==tuple, 'Entires muist be entered as a tuple'
        tup = (None,) + item
        self.c.execute("INSERT INTO "+str(tble)+" VALUES (?,?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,?,?,?,?,?)", tup)
        self.conn.commit()
        print('Entry added')
        return

    def close_connection(self):
        """A function to close the connection to the database"""
        self.conn.close()
        return 'Connection closed'


    def update_move(self, item, tble, fibid):
        """A function to update the oldest stored entry in a specified table for an individual fibre ID."""
        ###Need to spend some time thinking on the best way to execute this is
        assert type(item)==tuple, 'Information item must be given as a tuple'
        assert tble in self.tables, 'tble variable must be either moves, parks, or unparks'
        tup =  item + (str(fibid),) + (str(fibid),)

        self.c.execute("""UPDATE """+str(tble)+""" 
                        SET (Fibreid, Robot, Plate, Move_start, Move_end, Traj_X, Traj_Y, Release_X, Release_Y, Carry_X, Carry_Y, Gripper_X, Gripper_Y, TARG_X, TARG_Y, Rot, Elev, Logname) = (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                        WHERE Fibreid = ?  AND Move_start = (SELECT MIN(Move_start) FROM """+str(tble)+""" WHERE Fibreid = ?);""", tup)
        self.conn.commit()
        return

    def check_entries(self, fibid, tble, plate=None, robot=None, All=False):
        """A function to retrun all or a subset of database entries for an individual fibre ID. This query can be restricted by it's plate and robot attributtes."""
        assert tble in self.tables, 'tble variable must be either moves, parks, or unparks'
        tup = (str(fibid),)
        if type(plate)==int and type(robot)==int:
            assert type(plate)==int, 'plate must be either 0 or 1'
            self.c.execute("""SELECT * from """+str(tble)+""" WHERE Fibreid = ? AND Plate ="""+str(plate)+""" AND Robot = """+str(robot)+""";""", tup)
            rows = self.c.fetchall()
            return rows
        if All:
            self.c.execute("""SELECT * from """+str(tble)+""" WHERE Fibreid = ?;""", tup)
            rows = self.c.fetchall()
            return rows
        else:
            return
    
    def count_all_moves(self, tble='moves'):
        """Returns the sum of all entries for a specified table."""
        assert tble in self.tables, 'tble variable must be either moves, parks, or unparks'
        self.c.execute("""SELECT COUNT(*) FROM """+str(tble))
        rows = self.c.fetchall()
        return rows

    def evaluate_entries(self, id_sequence):
        """Prints the number of entries added to the database for each movement type"""
        ###This function needs to be modified to make sure the entries are isolated to a specific logfile
        
        names = ['moves', 'parks', 'unparks']
        self.info = []
        for index, item in enumerate(id_sequence):
            for j in names:#for j in item:
                N = self.check_count(item, j)[0][0]
                summary = (item, N, j)
                self.info.append(summary)
                print(f"For fibre {item}, {N} {j} entires were added")

        return

    def scrub_logfile(self, filename, list_file_dir='/home/pos_eng/WEAVE/pos/positioner/python/FIBRE_CALIB_STORE/database/'):
        assert type(filename)==str, 'Logfile must be enetered as a string'
        self.c.execute("""DELETE FROM moves WHERE Logname=\'"""+str(filename)+"""\'""")
        self.conn.commit()
        self.c.execute("""DELETE FROM parks WHERE Logname=\'"""+str(filename)+"""\'""")
        self.conn.commit()
        self.c.execute("""DELETE FROM unparks WHERE Logname=\'"""+str(filename)+"""\'""")
        self.conn.commit()
        print(filename+' deleted from all tables')
        temp = 'temp.txt'
        os.chdir(list_file_dir)
        with open('files_in_database.txt', 'r') as input:
            with open(temp, 'w') as output:
                for line in input:
                    if filename in line:
                        line = ''
                    output.write(line)
        os.replace(temp, 'files_in_database.txt')
        print('Listed files in database updated')
        return



    def get_attributes(self, attribute, fibrelist, column_list, tble='moves'):
        assert tble in self.tables, 'tble variable must be either moves, parks, or unparks'
        assert type(fibrelist)==list, 'Fibres must be entered as a list'
        assert type(attribute)==str, 'Attribute must be given as a string'
        assert attribute in column_list, 'Attribute must be listed in the database columns'
        multi_rows = []
        column_idx = [index for index, item in enumerate(column_list) if item==attribute][0]


        for index, item in enumerate(fibrelist):
            entries = self.check_entries(item, tble)
            for jindex, jitem in enumerate(entries):
                value = jitem[int(column_idx)]
                multi_rows.append((item, value, tble))
        return multi_rows
    

############# May need further testing ###################
    
    def scrub_fibre_entries(self, fibre_id, datetime, robot, plate, All=False, table=None):
        """a function to remove all entries for a specific fibre ID before a specified datetime"""
        assert type(datetime)==str, 'datetime must be entered as a string'
        if (assert_valid_datetime_format(datetime) == False):
            return
        assert type(robot)==int, 'Robot must be 0 or 1'
        assert robot==0 or robot==1, 'Robot must be 0 or 1'
        
        
        if not All:
            assert table is not None and All==False, 'Table entry required'
            self.c.execute("""DELETE FROM """+table+""" WHERE Move_start < """+datetime+""" AND Fibreid ="""+str(fibre_id)+""" AND Robot = """+str(robot)+""" AND Plate = """+str(plate)+""";""")
            self.conn.commit()
            print(f"{fibre_id}' deleted from {table} table before {datetime} for robot {robot} and plate {plate}")
            return

        
        if All:
            try:
                self.c.execute("""DELETE FROM moves WHERE Move_start < '"""+datetime+"""' AND Fibreid ="""+str(fibre_id)+""" AND Robot = """+str(robot)+""" AND Plate = """+str(plate)+""";""")
                self.c.execute("""DELETE FROM parks WHERE Move_start < '"""+datetime+"""' AND Fibreid ="""+str(fibre_id)+""" AND Robot = """+str(robot)+""" AND Plate = """+str(plate)+""";""")
                self.c.execute("""DELETE FROM unparks WHERE Move_start < '"""+datetime+"""' AND Fibreid ="""+str(fibre_id)+""" AND Robot = """+str(robot)+""" AND Plate = """+str(plate)+""";""")
                self.conn.commit()
                print(str(fibre_id)+' deleted from all tables before '+datetime)
                return
                
            except Exception as e:
                print(e)
                exception_type, exception_object, exception_traceback = sys.exc_info()
                filename = exception_traceback.tb_frame.f_code.co_filename
                line_number = exception_traceback.tb_lineno

                print("Exception type: ", exception_type)
                print("File name: ", filename)
                print("Line number: ", line_number)
                  
        
        return

######################


if __name__=="__main__":
    fb = fibre_database()
    fb.create_tables()
    print('Database created')

