#!/usr/bin/env python

"""
#
# Project by j54j6
# This program is used to make a private copy of youtube videos and potentially
# other websites supported by youtubedl Furthermore it supports automatic
# periodic checking of channels and auto downloading.
# It also checks if the downlaoded video already exists in the
# specified storage space and checks
# integrity of videos and redownload them if needed
#


#
# This file contains the "User Logic" this means that all User
# Experience related stuff is located in here and also the "main Controls"
# In general this projects is made out of different modules (see ReadME ).
# This file combines them...
#
"""


# Python Modules
import logging
import sys
#import argparse

# Own Modules
from project_functions import show_help, direct_download, scheme_setup
from database_manager import check_db
from config_handler import check_for_config


# Init. Logging
logging.getLogger(__name__).addHandler(logging.StreamHandler(sys.stdout))
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

logger.info("Running startup checks...")

#Check for config File
ConfigLoaded = check_for_config()
if not ConfigLoaded:
    logger.error("Error while loading config! - Check log...")
    sys.exit()

#Check for database and init
DatabaseCheckSuccessful = check_db()
if not DatabaseCheckSuccessful:
    logging.error("Error while initializing DB! - Please check log...")
    sys.exit()

#Check database content
Dependencies = scheme_setup()

if not Dependencies:
    logging.error("Error while prepare dependencies... Check log.")
    sys.exit()

#All Tables exists needed to run this thing...
logging.info("All mandatory tables are existing...")

#POSTPONED
#parser = argparse.ArgumentParser(
#description="""YT-DL Manager - Download and manage Videos from different sources.
#               Further you can download new content completly automatic""")
#parser.add_argument("command",
#       type=str,
#       choices=["help",
#       "add-subscription",
#       "del-subscription",
#       "list-subscriptions",
#       "custom",
#       "start",
#       "validate"],
#help="Command - What do you want to do?")
#parser.add_argument("--url",
#           help="Url to add a subscription or directly download a video",
#           default=None)

#args = parser.parse_args()


#Deciding action based on given arguments
if len(sys.argv) > 1:
    #Command provided
    match sys.argv[1]:
        case "help":
            #provide help
            show_help()
            sys.exit()
        case "add-subscription":
            #Add a new subscription

            sys.exit()
        case "del-subscription":
            #Delete a subscription
            sys.exit()
        case "list-subscriptions":
            #Show all subscriptions
            sys.exit()
        case "custom":
            #Download a custom Item without being part of a subscription
            #parser = argparse
            if len(sys.argv) > 2:
                direct_download(sys.argv[2])
            else:
                logging.error("No url provided!")
                show_help()
            sys.exit()
        case "start":
            #Run the script to check for new content and download it
            sys.exit()
        case "validate":
            #Rehash all files and compare them to the already stored files.
            sys.exit()
else:
    show_help()