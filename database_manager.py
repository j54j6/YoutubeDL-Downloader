#!/usr/bin/env python

#
# Project by j54j6
# This file provides a simple abstraction layer database files for most projects 
#

#Python modules
import logging
import logging
import os
import json

#temporarily removed sql alchemy. It is not possible to use a dynamic database scheme (JSON Based) scheme. HELP NEEDED :)
#Feel free to add it - so we can support both SQLite and MySQL
#from sqlalchemy import create_engine, Column, Integer, String, Engine, MetaData, StaticPool, text

#As replacement use sqlite python module
import sqlite3
from sqlite3 import Error

#own Modules
from config_handler import config, check_for_config, loaded

#DB Stuff
#Variabvle to check if the db is already initialized
global db_init
db_init:bool = False
#Engine Object
global engine
engine = None

# init logger
logger = logging.getLogger(__name__)

def check_db():
    global engine
    global db_init
    logger.info("Init database...")
    logger.info("read config...")
    
    if not config:
        logging.error("Config is not initialized! - Please init first!")
        return False

    db_driver = config.get("db", "db_driver")
    try:
        if(db_driver == "sqlite"):
            logger.info("Selected DB Driver is SQLite")
            db_path = os.path.abspath(config.get("db", "db_path"))

            if not os.path.exists(db_path):
                logging.error("The given path %s does not exists!", db_path)
                return False
            
            #OLD SQL ALCHEMY CODE
            #engine = create_engine(f"sqlite:///{db_path}")
            #engine.connect()
            #logger.info("Engine created")
            #db_init = True

            #NEW SQLite Code
            try:
                engine = sqlite3.connect(db_path, check_same_thread=False)
                db_init = True
                logging.debug("DB initializied!")
                return True
            except Exception as e:
                logging.error(f"Error while conencting to SQLite DB! - Error: {e}")
                return False
        
        elif(db_driver == "mysql"):
            logging.error("Currently MySQL is not supported :( - If you are able to use SQLAlchemy feel free to modify this file and create a PR <3)")
            return False
        #    username = config.get("db", "db_user")
        #    password = config.get("db", "db_pass")
        #    hostname = config.get("db", "db_host")
        #    database_name = config.get("db", "db_name")
        #    engine = create_engine(f"mysql://{username}:{password}@{hostname}/{database_name}")
        #    engine.connect()
        #    logger.info("Engine created")
        #    db_init = True
        #    return True
        elif(db_driver == "memory"):
            logger.info("Selected DB Driver is SQLite-Memory")

            #OLD SQLALCHEMY Code
            #engine = create_engine("sqlite://" ,
            #        connect_args={'check_same_thread':False},
            #        poolclass=StaticPool)
            #engine.connect()
            #logger.info("Engine created")
            #db_init = True
            #return True
            try:
                engine = sqlite3.connect("file::memory:?cache=shared")
                db_init = True
                return True
            except Exception as e:
                logger.error(F"Error while creating in memory SQLite DB! - Error: {e}")
                return False
            
        else:
            logger.error("Currently only SQLite and MySQL is supported :) - Please choose one ^^")
            return False
    except Exception as e:
        logging.error(f"Error while initiating {db_driver} Database! - Error: {e}")

def check_table_exist(table_name:str):
    #OLD SQLALCHEMY CODE
    #sql_meta = MetaData()
    #try:
    #    sql_meta.reflect(bind=engine)#

    #    if table_name in sql_meta.tables:
    #        return True
    #    else:
    #        return False
    #except Exception as e:
    #    logging.error(f"Error while checking for table! - Error: {e}")
    #    exit()

    if not db_init:
        init = check_db()

        if not init:
            return False
    
    cursor = engine.cursor()

    try:
        table_exist = cursor.execute("""SELECT name FROM sqlite_master WHERE type='table'
                            AND name=?; """, [table_name]).fetchall()
        
        if table_exist == []:
            return False
        else:
            return True
    except Exception as e:
        logger.error(f"Error while checking for table! - Error: {e}")
        return False

#This function can create a table bases on a defined JSON scheme
def create_table(name:str, scheme:json):
    if not db_init:
        init = check_db()
        if not init:
            logging.error("Error while initializing DB")
            return False
    #Check if the table already exist. If so - SKIP
    if check_table_exist(name):
        logger.warning(f"Table {name} already exist! - SKIP")
        return True

    logger.info(f"Create table {name}")
    #Check if the scheme parameter is valid JSON
    if not type(scheme) == dict:
        try:
            data = json.loads(scheme)
        except Exception as e:
            logging.error(f"Error while reading JSON Scheme! - Error: {e}")
            return False
    else:
        data = scheme
    
    query:str = f"CREATE TABLE {name} ("
    primary_key_defined = False
    #Iterate over all defined columns. Check for different optionas and add them to the query.
    for column_name in data:
        logging.debug(f"Column_Name: {column_name}, Type: {scheme[column_name]}")
        c_query = column_name
        try:
            options = scheme[column_name]
        except Exception as e:
            logger.error(f"Error while creating table! - Can't load options for coumn {column_name}")
            return False

        #For each column create a cache query based on SQL -> <<Name>> <<type>> <<options>>
        if not "type" in options:
            logging.error(f"Error while creating table! - Column {column_name} does not include a valid \"type\" field!")
            return False
        c_query += " " + options["type"]

        if "not_null" in options and options["not_null"] == True:
            c_query += " NOT NULL"

        if "primary_key" in options and options["primary_key"] == True and not primary_key_defined:
            c_query += " PRIMARY KEY"
            primary_key_defined = True
        elif "primary_key" in options and options["primary_key"] == True and primary_key_defined == True:
            logging.warning(f"There are at least 2 primary keys defined! - Please check config. Ignore Primary Key {column_name}")

        if "auto_increment" in options and options["auto_increment"] == True:
            c_query += " AUTOINCREMENT"
        
        if "unique" in options and options["unique"] == True:
            c_query += " UNIQUE"

        if "default" in options:
            c_query += " DEFAULT " + options["default"]

        query += c_query + ", "
    query = query[:-2]
    query +=");"
    logging.debug(f"Query successfully generated. Query: {query}")

    #OLD SQLALCHEMY CODE
    #try:
    #    with engine.connect() as conn:
    #        conn.execute(text(query))
    #        conn.commit()
    #        return True
    #except Exception as e:
    #    logging.error(f"Error while executing creation Statement! - Error: {e}")
    #    return False

    try:
        cursor = engine.cursor()
        cursor.execute(query)
        engine.commit()

        table_exist = check_table_exist(name)

        if not table_exist:
            logging.error(F"Error while creating table {name}! - After creating table does not exist!")
            return False
        return True
    except Exception as e:
        logging.error(f"Error while creating table {name} Error: {e}")
        return False

#Fetch a value from a database based on a json filter {""}
def fetch_value(table:str, row_name:str, value:str, filter:list = None, is_unique=False):
    if not db_init:
        init = check_db()
        if not init:
            logging.error("Error while initializing db!")
            return False
        
    #Check if the table already exist. If so - SKIP
    if not check_table_exist(table):
        logger.warning(f"Table {table} does not exist!")
        return False
    
    #create SELECT query
    if filter != None:
        query_filter = ""
        for element in filter:
            query_filter += element + ","
        query_filter = query_filter[:-1]
    else:
        query_filter = "*"
    
    #OLD SQLALCHEMY CODE
    #query = F"SELECT {query_filter} from {table} WHERE {row_name} = \"{value}\""
    #logging.debug(f"Prepared Query: {query}")

    #try:
    #    with engine.connect() as conn:
    #        logging.debug(f"Prepared query: {query}")
    #        data = conn.execute(text(query))
    #        if not is_unique:
    #            return data.all()
    #        else:
    #            return data.first()
    #except Exception as e:
    #    logging.error(f"Error while executing Insert Statement! - Error: {e}")
    #    return False
    cursor = engine.cursor()
    try:
        query = f"SELECT {query_filter} from {table} WHERE {row_name} = ?;"
        data = cursor.execute(query, [value])

        if not is_unique:
            return data.fetchall()
        else:
            return data.fetchone()
    except Exception as e:
        logging.error(f"Error while fetching value from table {table} Error: {e}")
        return False

def insert_value(table:str, data:json):
    if not db_init:
        init = check_db()
        if not init:
            logging.error("Error while initializing db!")
            return False
    if not check_table_exist(table):
        logger.error(f"Table {table} does not exist!")
        return False
    keys = []
    for data_keys in data:
        keys.append(data_keys)
    values = []
    for data_values in data:
        values.append(data[data_values])
    keys = ",".join(keys)
    
    values = ""
    for value in data:
        if type(data[value]) == str or type(data[value]) == json:
            values += f"\"{data[value]}\","
        elif type(data[value]) == int:
            values += data[value] +","
        elif type(data(value)) == bool:
            values += data[value] +","
        else:
            logging.warning(f"Unsuported type {type(data[value])} for value {value}!")
            continue
    values = values[:-1]

    #OLD SQL ALCHEMY CODE
    #query = f"Insert into {table} ({keys}) VALUES ({values});"
    #logging.debug(f"Prepared Query: {query}")
    #try:
    #    with engine.connect() as conn:
    #        conn.execute(text(query))
    #        conn.commit()
    #        return True
    #except Exception as e:
    #    logging.error(f"Error while executing Insert Statement! - Error: {e}")
    #    return False

    try:
        cursor = engine.cursor()
        query = f"Insert into  {table} ({keys}) VALUES ({values})"
        cursor.execute(query)
        engine.commit()
        
        #Maybe a check if all data are inserted will be added in the future by adding a select statement (call fetch function)
        return True
    except Exception as e:
        logging.error(f"Error while inserting value in table {table} Error: {e}")
        logging.error(f"Statemet: Insert into  {table} ({keys}) VALUES (?), {values}")
        return False

