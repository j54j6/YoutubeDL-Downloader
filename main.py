#!/usr/bin/env python

#
# Project by j54j6
# This program is used to make a private copy of youtube videos and potentially other websites supported by youtubedl
# Furthermore it supports automatic periodic checking of channels and auto downloading. 
# It also checks if the downlaoded video already exists in the specified storage space and checks integrity of videos and redownload them if needed
# 


#
# This file contains the "User Logic" this means that all User Experience related stuff is located in here and also the "main Controls"
# In general this projects is made out of different modules (see ReadME ). This file combines them...
#


# Own Modules
from project_functions import check_dependencies, check_db 
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
    
    #Check for database
    

