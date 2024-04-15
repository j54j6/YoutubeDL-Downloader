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
from database_manager import engine, db_init, check_db, check_table_exist
from config_handler import config, check_for_config
# Python Modules
import logging

# Init. Logging
logger = logging.getLogger(__name__)



def main():
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
        
    if not check_table_exist("items"):
        #Create items table from scheme

    if not check_table_exist("subscriptions"):
        #Create subscriptions table

