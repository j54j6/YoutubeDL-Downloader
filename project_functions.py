#!/usr/bin/env python

#
# Project by j54j6
# This program is used to make a private copy of youtube videos and potentially other websites supported by youtubedl
# Furthermore it supports automatic periodic checking of channels and auto downloading. 
# It also checks if the downlaoded video already exists in the specified storage space and checks integrity of videos and redownload them if needed
# 

#
# This file contains the "Project specific funtions" this means that all functions I cannot reuse in other projects 
# like controls or checks are located inside this file. 
#
#Python modules
from prettytable import PrettyTable
import logging
import json

#own modules
from database_manager import check_table_exist, create_table

# init logger
logger = logging.getLogger(__name__)

def check_dependencies():
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


def show_help():
    print("------------------------------ Help ------------------------------")
    print("You asked for help... Here it is :) - Run YT-Manager with the following commands and you're good to go")
    help_table = PrettyTable(['Command', 'argument', 'description'])
    help_table.align['Command'] = "l"
    help_table.align['argument'] = "l"
    help_table.align['description'] = "l"
    help_table.add_row(['--Subscriptions--', '', ''])
    help_table.add_row(['add-subscription', '<<url>>', 'Add a new subscription'])
    help_table.add_row(['del-subscription', '<<number>> | <<Name>>, <<delete_content>>', 'Delete a subscription. You can either provide the ID of your subscription (use list-subscriptions)'])
    help_table.add_row(['', '', 'or the name of the subscription (Name of a channel). The second parameter defines if all content of this channel also should be removed (Default: False = NO)"'])
    help_table.add_row(['list-subscriptions', '<<filter>>', 'List all subscriptions - You can provide a Filter (Array) of schemes you want to include'])
    help_table.add_row(['', '', ''])
    help_table.add_row(['--Other--', '', ''])
    help_table.add_row(['validate', '', 'After any downloaded file a hash is generated and stored. For both checking for any duplicate files (independent of the name) and checking integrity of files (and maybe redownload them).'])
    help_table.add_row(['', '', 'If you use this command all files will be revalidated and a report will be generated if there are any mismatches. '])
    help_table.add_row(['', '', 'But be aware - This operation can take very long and consumes much power... Use it with care or overnight :) -  At the end you will see a report and you can decide if mismatched files should be redonwloaded'])
    help_table.add_row(['', '', ''])
    help_table.add_row(['--Operation--', '', ''])
    help_table.add_row(['custom', '<<url>>', 'In case you want to download a video from a channel without a subscription you can do it here... The file will saved in the default scheme based folder under /custom'])
    help_table.add_row(['start', '', 'Run the script -> Check all subscriptions for new content and download it'])
    print(help_table)
    print("Example: yt-manager.py add-subscription youtube-url")
    print("------------------------------------------------------------------")