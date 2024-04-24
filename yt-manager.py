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
from project_functions import check_dependencies, show_help
from database_manager import check_db
from config_handler import check_for_config
# Python Modules
import logging
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
dependencies = check_dependencies()

if not dependencies:
    logging.error("Error while prepare dependencies... Check log.")
    exit()

#All Tables exists needed to run this thing...
logging.info("All mandatory tables are existing...")

#Deciding action based on given arguments
if len(sys.argv) > 1:
    #Command provided
    match sys.argv[1]:
        case "help":
            #provide help
            show_help()
        case "add-subscription":
            #Add a new subscription
            exit()
        case "del-subscription":
            #Delete a subscription
            exit()
        case "list-subscriptions":
            #Show all subscriptions
            exit()
        case "custom":
            #Download a custom Item without being part of a subscription
            exit()
        case "start":
            #Run the script to check for new content and download it
            exit()
        case "validate":
            #Rehash all files and compare them to the already stored files.
            exit()
else:
    show_help()