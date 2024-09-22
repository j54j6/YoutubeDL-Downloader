#!/usr/bin/env python
"""
#
# Project by j54j6
# This file provides a simple abstraction layer database files for most projects
#
"""
#Python modules
import logging
import os
import json

#temporarily removed sql alchemy.
#It is not possible to use a dynamic database scheme (JSON Based) scheme.
#HELP NEEDED :)
#Feel free to add it - so we can support both SQLite and MySQL
#from sqlalchemy import create_engine, Column, Integer, String, engine, MetaData, StaticPool, text

#As replacement use sqlite python module
import sqlite3

#own Modules
from config_handler import config

#DB Stuff
#Variabvle to check if the db is already initialized
db_init:bool = False
#ENGINE Object
ENGINE = None

# init logger
logger = logging.getLogger(__name__)

def check_db():
    """This function is used to initialize the database.

    Return Values:
        - True -> Success
        - False -> Failed
    """
    global ENGINE
    global db_init
    logger.info("Init database...")
    logger.info("read config...")

    if not config:
        logger.error("Config is not initialized! - Please init first!")
        return False

    db_driver = config.get("db", "db_driver")
    try:
        if db_driver == "sqlite":
            logger.info("Selected DB Driver is SQLite")
            db_path = os.path.abspath(config.get("db", "db_path"))

            #Not needed - SQLite creates a db file if it not exist
            #if not os.path.exists(db_path):
            #    logger.error("The given path %s does not exists!", db_path)
            #    return False

            #OLD SQL ALCHEMY CODE
            #ENGINE = create_ENGINE(f"sqlite:///{db_path}")
            #ENGINE.connect()
            #logger.info("ENGINE created")
            #db_init = True

            #NEW SQLite Code
            try:
                ENGINE = sqlite3.connect(db_path, check_same_thread=False)
                encoding = ENGINE.cursor()
                encoding.execute('pragma encoding=UTF8')
                ENGINE.commit()
                db_init = True
                logger.debug("DB initializied!")
                return True

            except sqlite3.Error as e:
                logger.error("Error while conencting to SQLite DB! - Error: %s", e)
                return False

        elif db_driver == "mysql":
            #Linebreak because of Pylint C0301
            logger.error("""Currently MySQL is not supported :( -
                         If you are able to use SQLAlchemy
                         feel free to modify this file and create a PR <3)""")
            return False
        #    username = config.get("db", "db_user")
        #    password = config.get("db", "db_pass")
        #    hostname = config.get("db", "db_host")
        #    database_name = config.get("db", "db_name")
        #    ENGINE = create_ENGINE(f"mysql://{username}:{password}@{hostname}/{database_name}")
        #    ENGINE.connect()
        #    logger.info("ENGINE created")
        #    db_init = True
        #    return True
        elif db_driver == "memory":
            logger.info("Selected DB Driver is SQLite-Memory")

            #OLD SQLALCHEMY Code
            #ENGINE = create_ENGINE("sqlite://" ,
            #        connect_args={'check_same_thread':False},
            #        poolclass=StaticPool)
            #ENGINE.connect()
            #logger.info("ENGINE created")
            #db_init = True
            #return True
            try:
                ENGINE = sqlite3.connect("file::memory:?cache=shared")
                encoding = ENGINE.cursor()
                encoding.execute('pragma encoding=UTF8')
                ENGINE.commit()
                db_init = True
                return True
            except sqlite3.Error as e:
                #Line Break because of PyLint best Practice (C0301)
                logger.error("Error while creating in memory %s Database! - SQL Error: %s",
                             db_driver, e)
        else:
            logger.error("Currently only SQLite and MySQL is supported :) - Please choose one ^^")
    except sqlite3.Error as e:
        logger.error("Error while initiating %s Database! - SQL Error: %s", db_driver, e)
    return False

def check_table_exist(table_name:str):
    """ This function checks if the passed table name exists in the database

        Return Values: bool
        - True -> Table exist
        - False -> Table dont exist / Error
    """
    #OLD SQLALCHEMY CODE
    #sql_meta = MetaData()
    #try:
    #    sql_meta.reflect(bind=ENGINE)#

    #    if table_name in sql_meta.tables:
    #        return True
    #    else:
    #        return False
    #except Exception as e:
    #    logger.error(f"Error while checking for table! - Error: {e}")
    #    exit()

    if not db_init:
        init = check_db()

        if not init:
            return False

    cursor = ENGINE.cursor()

    try:
        table_exist = cursor.execute("""SELECT name FROM sqlite_master WHERE type='table'
                            AND name=?; """, [table_name]).fetchall()

        if table_exist == []:
            return False
        return True
    except sqlite3.Error as e:
        logger.error("Error while checking for table! - Error: %s",e)
        return False

def prepare_sql_create_statement(name, scheme):
    """ This function is used to create tables based on a defined json scheme.
        Check documentation for help

        Return Values:
            - None -> Error
            - SQL Statement
    """
    query:str = f"CREATE TABLE {name} ("
    primary_key_defined = False
    #Iterate over all defined columns. Check for different optionas and add them to the query.
    for column_name in scheme:
        logger.debug("Column_Name: %s, Type: %s", column_name, scheme[column_name])
        c_query = column_name
        try:
            options = scheme[column_name]
        except IndexError as e:
            #PyLint C0301
            logger.error("""Error while creating table! -
                         Can't load options for coumn %s - Error: %s""", column_name, e)
            return None

        #For each column create a cache query based on SQL -> <<Name>> <<type>> <<options>>
        if not "type" in options:
            #PyLint C0301
            logger.error("""Error while creating table! -
                         Column %s does not include a valid \"type\" field!""", column_name)
            return None
        c_query += " " + options["type"]

        if "not_null" in options and options["not_null"] is True:
            c_query += " NOT NULL"

        if "primary_key" in options and options["primary_key"] is True and not primary_key_defined:
            c_query += " PRIMARY KEY"
            primary_key_defined = True
        #PyLint C0301
        elif ("primary_key" in options and options["primary_key"] is True and
              primary_key_defined is True):
            logger.warning("""There are at least 2 primary keys defined! -
                           Please check config. Ignore Primary Key %s""", column_name)

        if "auto_increment" in options and options["auto_increment"] is True:
            c_query += " AUTOINCREMENT"

        if "unique" in options and options["unique"] is True:
            c_query += " UNIQUE"

        if "default" in options:
            c_query += " DEFAULT " + options["default"]

        query += c_query + ", "
    query = query[:-2]
    query +=");"
    return query

def prepare_sql_add_column_statement(table_name, column_name, options):
    """ This function is used to add columns to an existing table based on a defined json scheme.
        Check documentation for help

        Return Values:
            - None -> Error
            - SQL Statement
    """
    query:str = f"ALTER TABLE {table_name} ADD COLUMN {column_name}"

    #Iterate over all defined columns. Check for different optionas and add them to the query.

    #For each column create a cache query based on SQL -> <<Name>> <<type>> <<options>>
    if not "type" in options:
        #PyLint C0301
        logger.error("""Error while creating table! -
                     Column %s does not include a valid \"type\" field!""", column_name)
        return None
    c_query:str = ""
    c_query += " " + options["type"]
    if "not_null" in options and options["not_null"] is True and "default" in options and options["default"] != "":
        c_query += " NOT NULL"
    if "primary_key" in options and options["primary_key"] is True:
        logger.warning("Altering a table and changing the primary key is NOT supported!")
    if "auto_increment" in options and options["auto_increment"] is True:
        logger.warning("Altering a table and changing the primary key is NOT supported! -> Auto increment is also disabled...")
    if "unique" in options and options["unique"] is True:
        c_query += " UNIQUE"
    if "default" in options:
        c_query += " DEFAULT " + options["default"]
    query += c_query + ", "
    query = query[:-2]
    query +=";"
    return query

def create_table(name:str, scheme:json):
    """This function can create a table bases on a defined JSON scheme

        Return Values:bool
        - true -> Success
        - false -> Failed
    """
    if not db_init:
        init = check_db()
        if not init:
            logger.error("Error while initializing DB")
            return False
    #Check if the table already exist. If so - SKIP
    if check_table_exist(name):
        logger.warning("Table %s already exist! - SKIP", name)
        return True

    logger.info("Create table %s", name)
    #Check if the scheme parameter is valid JSON
    if not isinstance(scheme, dict):
        try:
            data = json.loads(scheme)
        except json.JSONDecodeError as e:
            logger.error("Error while reading JSON Scheme! - JSON Error: %s", e)
            return False
    else:
        data = scheme

    query = prepare_sql_create_statement(name, data)
    logger.debug("Query successfully generated. Query: %s", query)

    #OLD SQLALCHEMY CODE
    #try:
    #    with ENGINE.connect() as conn:
    #        conn.execute(text(query))
    #        conn.commit()
    #        return True
    #except Exception as e:
    #    logger.error(f"Error while executing creation Statement! - Error: {e}")
    #    return False

    try:
        cursor = ENGINE.cursor()
        cursor.execute(query)
        ENGINE.commit()

        table_exist = check_table_exist(name)

        if not table_exist:
            #PyLint C0301
            logger.error("""Error while creating table %s! -
                         After creating table does not exist!""", name)
            return False
        return True
    except sqlite3.Error as e:
        logger.error("Error while creating table %s Error: %s", name, e)
        return False

def check_scheme_match(table_name: str, scheme:json):
    """ 
    This function is used to check if a given (existing) table is matching a given scheme (it checks if all columns of the scheme actually existing inside the db table)
    If there are missing columns they will be added (but nothing removed!)
    """
    if not db_init:
        init = check_db()
        if not init:
            logger.error("Error while initializing DB")
            return False
    #Check if the table already exist. If so - SKIP
    if not check_table_exist(table_name):
        logger.warning("Table %s does not exist! - Can't check if the table matches a scheme...", table_name)
        return False
    
    #Fetch all rows of the table
    cursor = cursor = ENGINE.cursor()
    cursor.execute("SELECT * from " + table_name)
    ENGINE.commit()

    names = list(map(lambda x: x[0], cursor.description))

    missing_columns:list = []
    
    for needed_column in scheme:
        if not needed_column in names:
            print(needed_column)
            print("Is missing")
            missing_columns.append(needed_column)
    
    if len(missing_columns) > 0:
        logger.info("Table %s misses %i columns. Add missing columns...", table_name, len(missing_columns))
        for missing_column in missing_columns:
            try:
                sql_statement = prepare_sql_add_column_statement(table_name, missing_column, scheme[missing_column])
                cursor = cursor = ENGINE.cursor()
                cursor.execute(sql_statement)
                ENGINE.commit()
                return True
            except sqlite3.Error as e:
                logger.error("Error while adding column %s to table %s Error: %s", missing_column, table_name, e)
                return False
    else:
        logger.info("Table %s is up to date...", table_name)
        return True

def fetch_value(table:str, conditions:dict|list=None, data_filter:dict|list = None,
                is_unique=False, extra_sql=None):
    """ Fetch a value from a database based on a json filter {""} """
    if not db_init:
        init = check_db()
        if not init:
            logger.error("Error while initializing db!")
            return False

    #Check if the table already exist. If so - SKIP
    if not check_table_exist(table):
        logger.warning("Table %s does not exist!", table)
        return False

    #create SELECT query
    if data_filter is not None:
        query_filter = ""
        for element in data_filter:
            query_filter += element + ","
        query_filter = query_filter[:-1]
    else:
        query_filter = "*"

    #OLD SQLALCHEMY CODE
    #query = F"SELECT {query_filter} from {table} WHERE {row_name} = \"{value}\""
    #logger.debug(f"Prepared Query: {query}")

    #try:
    #    with ENGINE.connect() as conn:
    #        logger.debug(f"Prepared query: {query}")
    #        data = conn.execute(text(query))
    #        if not is_unique:
    #            return data.all()
    #        else:
    #            return data.first()
    #except Exception as e:
    #    logger.error(f"Error while executing Insert Statement! - Error: {e}")
    #    return False
    values = []
    query = f"SELECT {query_filter} from {table} "
    #Create filter
    conditions_part = ""
    if conditions is not None:
        if isinstance(conditions, dict):
            query += " WHERE "
            for condition in conditions:
                conditions_part += condition + "= ? AND "
                values.append(conditions[condition])
            conditions_part = conditions_part[:-5]
        elif isinstance(conditions, list):
            query += " WHERE "
            for condition_set in conditions:
                #Iterate over all conditions
                for condition in condition_set:
                    conditions_part += condition + "= ? AND "
                    values.append(condition_set[condition])
                conditions_part = conditions_part[:-5]
                conditions_part += " OR "
            conditions_part = conditions_part[:-4]
        else:
            logging.error("""Unsupported type for conditions! -
                          Conditions will be ignored! - Type: %s""", type(conditions))


    query = query + conditions_part

    if extra_sql is not None:
        query = query + " " + extra_sql

    logging.debug("Prepared Query: %s \n data: %s", query, values)
    cursor = ENGINE.cursor()
    try:
        data = cursor.execute(query, values)
        if not is_unique:
            return data.fetchall()
        return data.fetchone()
    except sqlite3.Error as e:
        logger.error("Error while fetching value from table %s SQL Error: %s", table, e)
        return False
    except TypeError as e:
        logging.error("Error while fetching Value. Unexcepted type received! - Error: %s", e)
        return False

#Pylint C0301
def fetch_value_as_bool(table:str, conditions:dict|list=None,
                        data_filter:list = None, is_unique=False):
    """ This function is used to fetch a value from a database.
        The filter is a list containing all fields that need to be returned.
        If "is_unique" = True, fetchfirst() instead of fetchall() is returned"""
    try:
        value = fetch_value(table, conditions, data_filter, is_unique)
        value = value[0]

        if isinstance(value, str):
            value = value.lower()
            if value in ("true", 1):
                return True
        elif isinstance(value, int):
            if value == 1:
                return True
        else:
            logger.error("""Error while converting fetched \"%s\" value to bool! -
                         Unsupported type %s""", value, type(value))
        return False
    except sqlite3.Error as e:
        logger.error("Error while fetching data from DB! - Error %s", e)
        return False

def insert_value(table:str, data:dict):
    """Insert a value into a given table.
        Data are passed as JSON with the following format:
        {"column_name": value:str|dict|list}

        Return Values:bool
        - True -> Success
        - False -> Failed
    """

    if not db_init:
        init = check_db()
        if not init:
            logger.error("Error while initializing db!")
            return False
    if not check_table_exist(table):
        logger.error("Table %s does not exist!", table)
        return False
    keys = []
    for data_keys in data:
        keys.append(data_keys)

    keys = ",".join(keys)

    values = []
    for value in data:
        try:
            if isinstance(data[value], (dict, list)):
                dict_data = json.dumps(data[value])
                values.append(dict_data)
            else:
                values.append(data[value])
        except json.JSONDecodeError as e:
            logger.error("Error while decoding json! - Error: %s", e)


    #OLD SQL ALCHEMY CODE
    #query = f"Insert into {table} ({keys}) VALUES ({values});"
    #logger.debug(f"Prepared Query: {query}")
    #try:
    #    with ENGINE.connect() as conn:
    #        conn.execute(text(query))
    #        conn.commit()
    #        return True
    #except Exception as e:
    #    logger.error(f"Error while executing Insert Statement! - Error: {e}")
    #    return False

    try:
        cursor = ENGINE.cursor()
        len_data = len(data)
        value_placeholder = ""
        for _ in range(len_data):
            value_placeholder += "?,"
        value_placeholder = value_placeholder[:-1]
        query = f"Insert into  {table} ({keys}) VALUES ({value_placeholder})"
        logging.debug(query)
        cursor.execute(query, values)
        ENGINE.commit()
        #Maybe a check if all data are inserted will be added in the future
        #by adding a select statement (call fetch function)
        return True
    except sqlite3.Error as e:
        logger.error("Error while inserting value in table %s SQL Error: %s", table, e)
        logger.error("Statemet: Insert into  %s (%s) VALUES (?), %s", table, keys, values)
        return False

def delete_value(table:str, conditions: dict|list, delete_all_content=False):
    """ Delete a value from db. Conditions are passed as json with columnname as key
        and column value as value

        Return Values: bool
        - True -> Success
        - False -> Failed
    """
    logging.debug("Remove from table %s", table)
    if not delete_all_content:
        query = f"DELETE FROM {table} WHERE "
        conditions_part = ""

        if isinstance(conditions, dict):
            for condition in conditions:
                conditions_part += condition + f"=\"{conditions[condition]}\" AND "
            conditions_part = conditions_part[:-5]
        elif isinstance(conditions, list):
            for condition_set in conditions:
                #Iterate over all conditions
                for condition in condition_set:
                    conditions_part += condition + f"=\"{condition_set[condition]}\" AND "
                conditions_part = conditions_part[:-5]
                conditions_part += " OR "
            conditions_part = conditions_part[:-4]
        query = query + conditions_part
    else:
        query = f"DELETE FROM {table}"
    try:
        cursor = ENGINE.cursor()
        cursor.execute(query)
        ENGINE.commit()

        #Maybe a check if all data are inserted will be added in the future
        #by adding a select statement (call fetch function)
        return True
    except sqlite3.Error as e:
        logger.error("Error while deleting value from table %s SQL Error: %s", table, e)
        logger.error("Statemet: %s", query)
        return False

def update_value(table:str, data:dict, conditions:dict|list, extra_sql:str=None):
    """ This function updates a table based on the passed data

        all data are passed as a dict in the followiung scheme {"key_name": "key_value"}
        conditions can be passed as dict (one condition) (OR) or as a list of dict (AND)
        also in the scheme {"column_name": "desired_value"}. If you use multiple keys they are
        connected with an logic OR. if you use a list [{}, {}] -> It is a logic AND

        Return Values: bool
        - True -> Success
        - False -> Failed
    """
    if not check_table_exist(table):
        logging.error("Table %s does not exist! - Can't update table...", table)
        return False
    values = []
    query = f"UPDATE {table} SET "

    for data_set in data:
        if isinstance(data[data_set], int):
            logging.debug("Key %s is an int", data_set)
            query += data_set + "= ?"
            values.append(data[data_set])
        elif isinstance(data[data_set], (dict, list)):
            logging.debug("Key %s is a dict or list", data_set)
            try:
                json_data = json.dumps(data[data_set])

                query += data_set + "= ?"
                values.append(json_data)
            except json.JSONDecodeError:
                logging.error("Error while converting value to json!")
                return False
        elif isinstance(data[data_set], str):
            #try to convert to json
            logging.debug("Key %s is a str", data_set)
            query += data_set + "= ?"
            values.append(data[data_set])
        else:
            logger.info("Type %s is not supported by update()! - Ignore value %s...",
                        type(data[data_set]), data_set)
            continue
        query += ", "
    query = query[:-2]

    conditions_part = ""
    if isinstance(conditions, dict):
        query += " WHERE "
        for condition in conditions:
            conditions_part += condition + f"=\"{conditions[condition]}\" AND "
        conditions_part = conditions_part[:-5]
    elif isinstance(conditions, list):
        query += " WHERE "
        for condition_set in conditions:
            #Iterate over all conditions
            for condition in condition_set:
                conditions_part += condition + f"=\"{condition_set[condition]}\" AND "
            conditions_part = conditions_part[:-5]
            conditions_part += " OR "
        conditions_part = conditions_part[:-4]
    else:
        logging.error("Unsupported type for conditions! - Condition will be ignored! - Type: %s",
                      type(conditions))
    query = query + conditions_part + ";"
    logger.debug("Prepared Query: %s ", query)
    logger.debug("Data %s", values)
    if extra_sql is not None:
        query += " " + extra_sql
    try:
        cursor = ENGINE.cursor()
        cursor.execute(query, values)
        ENGINE.commit()

        #Maybe a check if all data are inserted will be added in the future
        #by adding a select statement (call fetch function)
        return True
    except sqlite3.Error as e:
        logger.error("Error while updateing value in table %s SQL Error: %s", table, e)
        logger.error("Statement: %s", query)
        return False
