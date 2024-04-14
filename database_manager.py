#!/usr/bin/env python

#
# Project by j54j6
# This file provides a simple abstraction layer database files for most projects 
#

#Python modules
import logging
import logging
import os
from sqlalchemy import create_engine, Column, Integer, String, Engine, MetaData



#own Modules
from config_handler import config, check_for_config, loaded

#DB Stuff
#Variabvle to check if the db is already initialized
db_init:bool = False
#Engine Object
engine:Engine = Engine()

# init logger
logger = logging.getLogger(__name__)

def check_db():
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
            engine = create_engine(f"sqlite:///{db_path}")
            engine.connect()
            db_init = True
            return True
        elif(db_driver == "mysql"):
            username = config.get("db", "db_user")
            password = config.get("db", "db_pass")
            hostname = config.get("db", "db_host")
            database_name = config.get("db", "db_name")
            engine = create_engine(f"mysql://{username}:{password}@{hostname}/{database_name}")
            engine.connect()
            db_init = True
            return True
        else:
            logger.error("Currently only SQLite and MySQL is supported :) - Please choose one ^^")
            return False
    except Exception as e:
        logging.error(f"Error while initiating {db_driver} Database! - Error: {e}")

def check_table_exist(table_name:str):
    sql_meta = MetaData()
    try:
        sql_meta.reflect(bind=engine)

        if table_name in sql_meta.tables:
            return True
        else:
            return False
    except Exception as e:
        logging.error(f"Error while checking for table! - Error{e}")