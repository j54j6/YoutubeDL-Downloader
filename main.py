#!/usr/bin/env python

#
# Project by j54j6
# This program is used to make a private copy of youtube videos and potentially other websites
# supported by youtubedl Furthermore it supports automatic periodic checking
# of channels and auto downloading.
# It also checks if the downlaoded video already exists in the specified storage space and checks
# integrity of videos and redownload them if needed
#


#
# This file contains the "User Logic" this means that all User Experience related stuff is located
# in here and also the "main Controls"
# In general this projects is made out of different modules (see ReadME ). This file combines them...
#


# Own Modules
from project_functions import check_dependencies
from database_manager import db_init, check_db, check_table_exist, create_table
from config_handler import config, check_for_config
# Python Modules
import logging
import json
import sys


# Init. Logging
logging.getLogger(__name__).addHandler(logging.StreamHandler(sys.stdout))
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

logger.info("Running startup checks...")

#Check for config File
config_loaded = check_for_config()
if not config_loaded:
    logger.error("Error while loading config! - Check log...")
    exit()

#Check for database and init
database_check_successful = check_db()
if not database_check_successful:
    logging.error("Error while initializing DB! - Please check log...")
    exit()

#Check database content
#Check if needed tables existing ("config", "items", "subscriptions")
logger.info("Check if all tables exist..")
if not check_table_exist("config"):
    #Create config table from scheme
    logger.info("Config table does not exist - Create Table...")
    try:
        with open("./scheme/project.json") as config_scheme: 
            config_data = config_scheme.read()
    except Exception as e:
        logger.error(f"Error while reading Config Scheme! - Error: {e}")
        exit()
    
    try:
        config_data_as_json = json.loads(config_data)
        logging.debug("Config Data loaded - create table..")
    except Exception as e:
        logger.error(f"Error while parsing JSON from config Scheme! - Error: {e}")
        exit()
    
    result = create_table(config_data_as_json["db"]["table_name"], config_data_as_json["db"]["columns"])
    if not result:
        logging.error("Error while creating table! - Check log")
        exit()
    
if not check_table_exist("items"):
    #Create items table from scheme
    #Create config table from scheme
    logger.info("Items table does not exist - Create Table...")
    try:
        with open("./scheme/saved_items.json") as table_scheme: 
            column_data = table_scheme.read()
    except Exception as e:
        logger.error(f"Error while reading items table Scheme! - Error: {e}")
        exit()
    
    try:
        column_data_as_json = json.loads(column_data)
        logging.debug("Config Data loaded - create table..")
    except Exception as e:
        logger.error(f"Error while parsing JSON from config Scheme! - Error: {e}")
        exit()
    
    result = create_table(column_data_as_json["db"]["table_name"], column_data_as_json["db"]["columns"])

    if not result:
        logging.error("Error while creating table! - Check log")
        exit()
if not check_table_exist("subscriptions"):
    #Create subscriptions table
    #Create items table from scheme
    #Create config table from scheme
    logger.info("Items table does not exist - Create Table...")
    try:
        with open("./scheme/subscriptions.json") as table_scheme: 
            column_data = table_scheme.read()
    except Exception as e:
        logger.error(f"Error while reading subscription table Scheme! - Error: {e}")
        exit()
    
    try:
        column_data_as_json = json.loads(column_data)
        logging.debug("Config Data loaded - create table..")
    except Exception as e:
        logger.error(f"Error while parsing JSON from subscription Scheme! - Error: {e}")
        exit()
    
    result = create_table(column_data_as_json["db"]["table_name"], column_data_as_json["db"]["columns"])
    if not result:
        logging.error("Error while creating table! - Check log")
        exit()