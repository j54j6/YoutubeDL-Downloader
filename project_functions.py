#!/usr/bin/env python
"""
#
# Project by j54j6
# This program is used to make a private copy of youtube videos and potentially other websites
# supported by youtubedl
# Furthermore it supports automatic periodic checking of channels and auto downloading.
# It also checks if the downlaoded video already exists in the specified storage space and
# checks integrity of videos and redownload them if needed
#

#
# This file contains the "Project specific funtions" this means that all functions I cannot
# reuse in other projects
# like controls or checks are located inside this file.
#
"""

#Python modules
import os
import logging
import json
import pathlib
import hashlib
import re
from datetime import datetime

import urllib.parse as urlparse

import requests
import tldextract
import validators
import pytz

from prettytable import PrettyTable
from yt_dlp import YoutubeDL, DownloadError

#own modules
from database_manager import (check_table_exist, create_table, update_value,
                insert_value, fetch_value, fetch_value_as_bool, delete_value)

from config_handler import config
# init logger
logger = logging.getLogger(__name__)

#Define buffer per Thread in Bytes for filehashing - Default 2GB = 2147483648
#If you have problems adding files decrease the value!
BUF_SIZE = 4096


################# MAIN

def start():
    """This function iterates over all subscriptions and checks for new content and downloads it

    Return Values:
        - True: Success (All subscriptions updated and files downloaded)
        - False: Failed (There was an error either during update or download phase)
    """
    logger.info("Checking all subscriptions for updates")

    updated = update_subscriptions()

    if not updated:
        logger.error("Error while updating subscriptions!")
        return False

    return download_missing()

################# Subscription related

def add_subscription(url:str, downloaded:int = None, last_checked = None, meta_data = None):
    """ Add a subscription to the database

        Return Values:
        - True: Success (Subscription successfully added to db)
        - False: Failed (Error while adding subscription. Most likly Ytdlp or SQLite error)
    """
    #Lazy check if the entry already exist in db before downloading metadata and doing stuff...
    #Check if subscription already exist
    subscription_exist = fetch_value("subscriptions",
                                    [
                                        {"subscription_path": url},
                                        {"passed_subscription_path": url}
                                    ], ["id", "scheme", "subscription_name"], True)

    if subscription_exist is not None:
        logger.info("%s subscription for %s already exists!",
                    subscription_exist[1], subscription_exist[2])
        return True

    subscription_obj = get_subscription_data_obj(url, downloaded, last_checked, meta_data)

    if not subscription_obj["status"]:
        logger.error("Error while creating subscription obj!")
        return False

    #Check if the formatted link is already in db - This is url should every time the same
    if subscription_obj["exist_in_db"]:
        logger.info("%s subscription for %s already exists!", subscription_exist[1],
                        subscription_exist[2])
        return True

    added_subscr = insert_value("subscriptions", subscription_obj["obj"])

    if not added_subscr:
        logger.error("Error while inserting subscription for %s into db! - Check log",
                     subscription_obj["obj"]["subscription_name"])
        return False
    logger.info("Subscription for %s successfully created.",
                subscription_obj["obj"]["subscription_name"])
    return True

def add_subscription_batch(file:str):
    """ Add a subscription to the database using a file

        Return Values:
        - True: Success (Subscription successfully added to db)
        - False: Failed (Error while adding subscription. Most likly Ytdlp or SQLite error)
    """
    file = os.path.abspath(file)
    if not os.path.isfile(file):
        logger.error("File %s doesn't exist!", file)
        return False

    failed = False
    with open(file, 'r', encoding="UTF-8") as input_file:
        for line in input_file:
            line = line.strip()
            if not add_subscription(line):
                failed = True

    if not failed:
        logger.info("All subscriptions successfully added")
        return True
    logger.error("Error while adding subscription batch!")
    return False

def del_subscription(identifier:str):
    """ This function removes a passed subscription from the database
        (This function does NOT remove the files!)

        Return Values:
        - True: Success (Subscription successfully deleted from db)
        - False: Failed (Error while removing subscription from db - Most likly SQL Error)
    """
    if validators.url(identifier):
        #Remove with url as ident

        subscription_exist_1 = fetch_value("subscriptions", {"subscription_path": identifier},
                                           ["id"], True)
        subscription_exist_2 = fetch_value("subscriptions",
                                           {"passed_subscription_path": identifier},
                                           ["id"], True)

        if subscription_exist_1 is None and subscription_exist_2 is None:
            logger.info("Subscription does not exist!")
            return True

        subscription_deleted = delete_value("subscriptions", [
            {"subscription_path": identifier},
            {"passed_subscription_path": identifier}])
    else:
        subscription_exist = fetch_value("subscriptions",
                                         {"subscription_name": identifier},
                                         ["id"], True)

        if subscription_exist is None:
            logger.info("Subscription does not exist!")
            return True

        subscription_deleted = delete_value("subscriptions", {"subscription_name": identifier})

    if not subscription_deleted:
        logger.error("Error while removing subscription!")
        return False
    logger.info("Subscription removed.")
    return True

def list_subscriptions(scheme_filter:list=None):
    """This function list all subscriptions with prettyTables

        Return Values:
        - True: Success (Subscription Table was printed to CLI)
        - False: Failed (Failed to fetch all data needed to build table. Most likly SQL Error)
    """
    if scheme_filter is None:
        logger.debug("List all subscriptions")
        #List all subscriptions
        subscriptions = fetch_value("subscriptions",
                                    None,
                                    [
                                        "id",
                                        "subscription_name",
                                        "scheme",
                                        "subscription_content_count",
                                        "downloaded_content_count",
                                        "subscription_last_checked",
                                        "subscription_path"
                                    ], extra_sql="ORDER BY scheme")

    else:
        logger.debug("List subscriptions with Filter")
        conditions = []
        for condition in scheme_filter:
            conditions.append({"scheme": condition})

        subscriptions = fetch_value("subscriptions",
                                    conditions,
                                    [
                                        "id",
                                        "subscription_name",
                                        "scheme",
                                        "subscription_content_count",
                                        "downloaded_content_count",
                                        "subscription_last_checked",
                                        "subscription_path"
                                    ], extra_sql="ORDER BY scheme")

    if subscriptions is None:
        logger.error("Error while fetching DB data!")
        return False

    subscriptions_table = PrettyTable(
        ['ID', 'Name', 'Scheme', 'Avail. Videos', 'Downloaded Videos', 'Last checked', 'url'])
    subscriptions_table.align['ID'] = "c"
    subscriptions_table.align['Name'] = "l"
    subscriptions_table.align['Scheme'] = "l"
    subscriptions_table.align['Avail. Videos'] = "c"
    subscriptions_table.align['Downloaded Videos'] = "c"
    subscriptions_table.align['Last checked'] = "c"
    subscriptions_table.align['url'] = "l"
    video_is = 0
    video_should = 0
    for index, subscription in enumerate(subscriptions):
        video_is = video_is + int(subscription[4])
        video_should = video_should + int(subscription[3])
        enable_divider = False
        if index < len(subscriptions)-1:
            if subscription[2] != subscriptions[index+1][2]:
                enable_divider = True
            else:
                logger.debug("%s == %s", subscription[2] , subscriptions[index][2])

        if index == len(subscriptions)-1:
            enable_divider = True

        if enable_divider:
            logger.debug("For ID %s no divider needed!", subscription[0])
            subscriptions_table.add_row([
                subscription[0],
                subscription[1],
                subscription[2],
                subscription[3],
                subscription[4],
                subscription[5],
                subscription[6]],
                divider=True)
        else:
            logger.debug("For ID %s no divider needed!", subscription[0])
            subscriptions_table.add_row([
                subscription[0],
                subscription[1],
                subscription[2],
                subscription[3],
                subscription[4],
                subscription[5],
                subscription[6]],
                divider=False)
        enable_divider = False

    subscriptions_table.add_row(["Total: ",len(subscriptions),'',video_should,video_is,'',''])

    print(subscriptions_table)
    return True

def update_subscriptions():
    """ This function iterates over all subscriptions and update them.
        It will NOT download any files!

        Return Values:
        - True: Success (All subscriptions updated)
        - False: Failed (There was an error during updating the db. Most likly YT DLP or SQL Error)
    """
    subscriptions = fetch_value("subscriptions",
                                None,
                                [
                                    "scheme",
                                    "subscription_name",
                                    "subscription_path",
                                    "subscription_last_checked",
                                    "downloaded_content_count",
                                    "subscription_content_count",
                                    "id",
                                    "current_subscription_data"
                                ],
                                False,
                                "ORDER BY scheme")

    if not subscriptions:
        logger.error("Error while fetching subscription data! - Please check log.")
        return False

    error_during_process = False
    faulty_subscriptions = []
    faulty_messages = []
    current_time = get_current_time()

    if current_time == -1:
        #Time cant be fetched! - This will have effect on all subscriptions - abort...
        return False

    #Iterate over all subscriptions
    for subscription in subscriptions:
        #Fetch the current object of the subscription
        current_obj = get_subscription_data_obj(subscription[2])

        if not current_obj["status"]:
            logger.error("Error while fetching actual metadata for subscription %s",
                         subscription[1])

        #Check if subscription needs to be checked
        check_interval = fetch_value("config",
                                     {"option_name": "subscription_check_delay"},
                                     ["option_value"], True)

        if not check_interval:
            logger.error("Error while fetching check interval value! - Continue")
        else:
            check_interval = check_interval[0]
            last_checked = subscription[3]
            current_time = get_current_time()

            time_since_last_check = datetime.strptime(current_time, "%Y-%m-%d %H:%M:%S") - datetime.strptime(last_checked, "%Y-%m-%d %H:%M:%S")
            hours_since_last_check = time_since_last_check.seconds/3600

            if hours_since_last_check < int(check_interval):
                logger.info("Subscription %s was checked %s hours ago. Skip",
                            subscription[1], str(round(hours_since_last_check, 2)))
                continue

        #Check for number of items
        if (current_obj["obj"]["subscription_content_count"] == subscription[5] and
        not subscription[4] != current_obj["obj"]["subscription_content_count"]):
            #No update avail - Modify subscription data and continue

            table_updates = update_value(
                "subscriptions",
                {
                    "subscription_last_checked": current_time,
                    "last_subscription_data": subscription[7],
                    "current_subscription_data": current_obj["obj"]["current_subscription_data"],
                    "subscription_has_new_data": "0"
                },
                {"id": subscription[6]}
            )
        elif current_obj["obj"]["subscription_content_count"] < subscription[5]:
            #Less avail than before - just send a message...
            faulty_subscriptions.append(subscription[1])
            faulty_messages.append("""Number of items is less than the last check! -
                                   Last time: %s, This time: %s""",
                                   subscription[5],
                                   current_obj["obj"]["subscription_content_count"])

            #Update table
            table_updates = update_value(
                "subscriptions",
                {
                    "subscription_last_checked": current_time,
                    "last_subscription_data": subscription[7],
                    "current_subscription_data": current_obj["obj"]["current_subscription_data"],
                    "subscription_has_new_data": "0",
                    "subscription_content_count": current_obj["obj"]["subscription_content_count"]
                },
                {"id": subscription[6]}
            )
        else:
            #Updates avail
            logger.info("New content for %s availiable", current_obj["obj"]["subscription_name"])
            #Update table
            table_updates = update_value(
                "subscriptions",
                {
                    "subscription_last_checked": current_time,
                    "last_subscription_data": subscription[7],
                    "current_subscription_data": current_obj["obj"]["current_subscription_data"],
                    "subscription_has_new_data": "1",
                    "subscription_content_count": current_obj["obj"]["subscription_content_count"]
                },
                {"id": subscription[6]}
            )

        if not table_updates:
            logger.error("Error while updating table!")
            faulty_subscriptions.append(subscription[1])
            faulty_messages.append("Error while updating subscription!")
            error_during_process = True
            continue
        logger.info("Subscription %s successfully updated", subscription[1])

    if len(faulty_subscriptions) > 0:
        for index, subscription in enumerate(faulty_subscriptions):
            logger.warning("Subscription %s exited with an error! - Message: %s",
                           subscription, faulty_messages[index])

    if error_during_process:
        logger.error("Please check messages abve!")
        return False
    logger.info("All subscriptions updated!")
    return True

def export_subscriptions():
    "This functions exports all subscriptions saved in the db"

    subscriptions = fetch_value("subscriptions", None, ["subscription_path",
                                                        "subscription_last_checked",
                                                        "downloaded_content_count",
                                                        "last_subscription_data",
                                                        "subscription_name"])

    if subscriptions is None:
        logging.error("Error while fetching subscriptions")

    exported_subscriptions:list = []
    for subscription in subscriptions:
        subscription_obj = {
            "subscription_path": subscription[0],
            "subscription_last_checked": subscription[1],
            "downloaded_content_count": subscription[2],
            "last_subscription_data": subscription[3],
            "subscription_name": subscription[4]
        }
        exported_subscriptions.append(subscription_obj)
    base_path = fetch_value("config", {"option_name": "base_location"}, ["option_value"], True)

    if not base_path or not isinstance(base_path, tuple):
        logging.error("Error while fetching base path from config! - Use default (Partent directory)")
        base_path = "./"
    else:
        base_path = base_path[0]

    logging.info("Exported %i subscriptions. Create file at %s", len(exported_subscriptions), os.path.abspath(base_path))

    #Insert list into file.

    try:
        with open(os.path.join(os.path.abspath(base_path),
                               "subscriptions_export.json"),
                               encoding="UTF-8",
                               mode="w+") as subscription_file:
            subscriptions_as_json = json.dumps(exported_subscriptions)
            subscription_file.write(subscriptions_as_json)
        logging.info("Subscriptions exported")
    except FileNotFoundError as e:
        logging.error("Error while creating file! - Error: %s", e)
        return False
    except json.JSONDecodeError as e:
        logging.error("Error while parsing JSON array with subscriptions! - Error: %s", e)
        return False
    return True

def import_subscriptions(path="./", delelte_current_subscriptions=False):
    """ This function imports subscriptions based on a json file (generated by export_subscriptions function)"""

    if delelte_current_subscriptions:
        logger.info("Current subscriptions will be deleted before import!")
        if(delete_value("subscriptions", None, True)):
            logger.info("Subscriptions removed!")
        else:
            logger.error("Error while removing old subscriptions! - Abort")
            return False
    logging.info("Import subscriptions from %s", path)

    if not os.path.exists(path):
        logging.error("The given path does not exist!")
        return False

    try:
        with open(os.path.abspath(path), encoding="UTF-8", mode="r") as f:
            subscriptions = f.read()

        subscriptions = json.loads(subscriptions)
        #Iterate over json array
        error_raised = False
        failed_imports = []
        for subscription in subscriptions:
            success = add_subscription(subscription["subscription_path"],
                                       subscription["downloaded_content_count"],
                                       subscription["subscription_last_checked"],
                                       subscription["last_subscription_data"])
            if not success:
                error_raised = True
                failed_imports.append(subscription["subscription_name"])

        if error_raised:
            for failed_import in failed_imports:
                logging.error("Error while importing %s to db!", failed_import)
            return False
        logging.info("All subscriptions successfully imported!")
        return True
    except FileNotFoundError as e:
        logging.error("Subscriptiuon file not found! - Error: %s", e)
        return False
    except json.JSONDecodeError as e:
        logging.error("Error while loading JSON File! - Error: %s", e)
        return False
    return True
### Subscription helper

def create_subscription_url(url:str, scheme:json):
    """ This function creates the subscription url which will used to subscribe to a channel or
        anything else

        Return Value:dict
        {
            "status": False, -> Operation success or failed (probe this to check if
                                operation successfull)
            "subscribable": True, -> If status is false, it is possible that there was a
                                    video passed. If true -> Wrong url passed
            "scheme": None, -> Which scheme was used to create the url
            "tld": None, -> tld of the url (e.g. .com)
            "sld": None, -> sld of the url (e.g. reddit)
            "subd": None, -> subdomain of the url (e.g. www.) van be empty!
            "subscription_name": None, -> The subscription name - most likly playlist name /
                                            channel name
            "category_avail": False, -> Are there categories availiable
            "category": None, -> If categories availiable -> Which category is the url
            "subscription_url": None, -> passed url from parameters
            "formed_subscription_url": None -> function created subscription url to grttant
                                            uniform data
        }
    """
    logger.debug("Create subscription url for url %s", url)
    return_val = {
        "status": False,
        "subscribable": True,
        "scheme": None,
        "tld": None,
        "sld": None,
        "subd": None,
        "subscription_name": None,
        "category_avail": False,
        "category": None,
        "subscription_url": None,
        "formed_subscription_url": None
    }
    if(not "subscription" in scheme or
       not "available" in scheme["subscription"] or
       scheme["subscription"]["available"] is not True or
       not "url_blueprint" in scheme["subscription"]):

        if("subscription" in scheme and
           "available" in scheme["subscription"] and
           scheme["subscription"]["available"] is not True):
            logger.info("Scheme %s does not support subscriptions!", scheme["schema_name"])
            return_val["subscribable"] = False
            return return_val
        logger.error("Scheme does not contain a subscription key or url blueprint!")
        return return_val

    #Check which parts are needed
    url_blueprint:str = scheme["subscription"]["url_blueprint"]

    blueprint_data = re.findall(r'{\w*}',url_blueprint)

    tld_url_parts = tldextract.extract(url)
    parsed_url_parts = urlparse.urlparse(url)

    if parsed_url_parts.scheme is not None:
        logger.debug("Key scheme is in parsed urls")
        if "{scheme}" in blueprint_data:
            logger.debug("Key scheme is in the blueprint subscription link. Add it...")
            return_val["scheme"] = parsed_url_parts.scheme

    if tld_url_parts.subdomain is not None:
        logger.debug("Key subdomain is in parsed urls")
        if "{subd}" in blueprint_data:
            logger.debug("Key subd is in the blueprint subscription link. Add it...")
            return_val["subd"] = tld_url_parts.subdomain

    if tld_url_parts.domain is not None:
        logger.debug("Key domain is in parsed urls")
        if "{sld}" in blueprint_data:
            logger.debug("Key sld is in the blueprint subscription link. Add it...")
            return_val["sld"] = tld_url_parts.domain

    if tld_url_parts.suffix is not None:
        logger.debug("Key suffix is in parsed urls")
        if "{tld}" in blueprint_data:
            logger.debug("Key tld is in the blueprint subscription link. Add it...")
            return_val["tld"] = tld_url_parts.suffix

    #Check if the scheme supports categories
    if("categories" in scheme and
       "available" in scheme["categories"] and
       scheme["categories"]["available"] is True):
        logger.debug("Categories are available. Fetch data...")
        #extract the category from the url
        category = fetch_category_name(url, scheme)

        #Check if a category was fetched
        if category is not None:
            logger.debug("Category found")
            if "{category}" in blueprint_data:
                logger.debug("Key category is in the blueprint subscription link. Add it...")
                return_val["category_avail"] = True
                return_val["category"] = category

    subscription_name = fetch_subscription_name(url, scheme)

    if not subscription_name:
        logger.error("Can't fetch subscription name! - Maybe you cannot subscribe to the url?")
        return return_val
    if "{subscription_name}" in blueprint_data:
        logger.debug("Key subscription_name is in the blueprint subscription link. Add it...")
        return_val["subscription_name"] = subscription_name

    if "{subscription_url}" in blueprint_data:
        logger.debug("Key subscription_url is in the blueprint subscription link. Add it...")
        if(return_val["category_avail"] and
           category in scheme["categories"]["categories"] and
           "subscription_url" in scheme["categories"]["categories"][category]):

            if(scheme["categories"]["categories"][category]["subscription_url"] is not False and
               scheme["categories"]["categories"][category]["subscription_url"] is not None and
               scheme["categories"]["categories"][category]["subscription_url"] != ""):
                logger.debug("Subscription url added...")
                return_val["subscription_url"] = scheme["categories"]["categories"][category]["subscription_url"]

    logger.debug("All url data prepared. Create Link")

    supported_keys = ["scheme", "subd", "sld", "tld", "category",
                      "subscription_name", "subscription_url"]

    for part in supported_keys:
        if return_val[part] is not None and return_val[part] is not False:
            url_blueprint = url_blueprint.replace(f"{{{part}}}", return_val[part])
        else:
            url_blueprint = url_blueprint.replace(f"/{{{part}}}", "")

    if url_blueprint.find("{") != -1 or url_blueprint.find("}") != -1:
        logger.error("""Error while creating correct subscription url! -
                     Not all placeholders were replaced! - Url: %s""", url_blueprint)
        return return_val

    logger.debug("Url successfully created")
    return_val["formed_subscription_url"] = url_blueprint
    return_val["status"] = True
    return return_val

def get_subscription_data_obj(url:str, downloaded = None, last_checked=None, last_metadata=None):
    """ Returns a dict containing all information about a subscription (db obj) and
        also if the url already exist in db

    Return Value: dict
        {
            "status": False, -> Operation successfull? - Use this as probe!
            "exist_in_db": False, -> Does the subscription already exist?
            "obj": { -> The subscription object. This can directly passed to SQL Engine
                "scheme": None, -> Which scheme is used
                "subscription_name": None, -> friendly name - most likly playlist/channel name
                "subscription_path": None, -> function created url to the website
                "passed_subscription_path": url, -> url that was passed by the user to add the
                                                    subscription. (not necessarily the same)
                "subscription_content_count": None, -> How many entries have the channel/playlist
                "current_subscription_data": None, -> Current metadata object
                "last_subscription_data": None -> Last metadata object
                                                    (only used for stats if you want...)
            }
        }
    """
    subscription_entry:dict = {
        "status": False,
        "exist_in_db": False
    }

    subscription_entry["obj"] = {
            "scheme": None,
            "subscription_name": None,
            "subscription_path": None,
            "passed_subscription_path": url,
            "subscription_content_count": None,
            "current_subscription_data": None,
            "last_subscription_data": None,
            "downloaded_content_count": None
        }


    data = prepare_scheme_dst_data(url)
    if data["status"] is False or data["scheme"] is None:
        logger.error("The provided url is not supported!")
        return subscription_entry

    logger.debug("Used scheme for url is: %s", data["scheme"])

    subscription_data = create_subscription_url(url, data["scheme"])

    if not subscription_data["status"]:
        if subscription_data["subscribable"] is False:
            schema_name = data["scheme"]["scheme_name"]
            logger.info("Can't add subscription - Scheme %s does not support subscriptions",
                        schema_name)
            return subscription_entry
        logger.error("Error while fetching subscription data!")
        return subscription_entry

    metadata = get_metadata(subscription_data["formed_subscription_url"],
                            get_ydl_opts(data["dst_path"],
                                         {'quiet': False, 'extract_flat': 'in_playlist'}))

    if not metadata:
        logger.error("Error while fetching metadata for subscription! - Please check the log.")
        return subscription_entry

    if("playlist_count" not in metadata or
       "entries" not in metadata or
       "_type" not in metadata):
        logger.error("Fetched metadata does not contain all information needed! - Data: %s",
                     metadata)
        return subscription_entry

    obj = {}
    obj["scheme"] = data["scheme"]["schema_name"]
    obj["passed_subscription_path"] = url
    obj["subscription_name"] = subscription_data["subscription_name"]
    obj["subscription_path"] = subscription_data["formed_subscription_url"]
    obj["subscription_content_count"] = metadata["playlist_count"]
    obj["current_subscription_data"] = metadata

    if downloaded is not None and downloaded > 0:
        obj["downloaded_content_count"] = downloaded
    if last_checked is not None:
        obj["subscription_last_checked"] = last_checked
    if last_metadata is not None:
        obj["last_subscription_data"] = last_metadata


    subscription_entry["obj"] = obj

    entry_in_db = fetch_value("subscriptions",
                                {"subscription_path": subscription_data["formed_subscription_url"]},
                                ["id", "scheme", "subscription_name"], True)

    if entry_in_db is None:
        subscription_entry["exist_in_db"] = False
    else:
        subscription_entry["exist_in_db"] = True

    subscription_entry["status"] = True
    return subscription_entry

def fetch_subscription_name(url:str, scheme:json):
    """ This function is a helper to extract the "target name" of your subscription.
        Most likly it is the channel name or playlist name.

        The scheme is used to extract the name from the url.
        It is possible that this function will be changed in the future.
        Some sites only have numeric values for the playlists/channels in the url.
        In this case YT DLP need to fetch it. But for now
        it works without it...

        Return Value:str
        - None -> Nothing found (empty)
        - Subscription name string e.g j54j6
    """
    logger.debug("Fetch subscription name for url %s", url)
    if "subscription" in scheme:
        subscription_path = scheme["subscription"]["subscription_name_locator"]
    else:
        #This should not be used!
        subscription_path = 2
    try:
        parsed_url = urlparse.urlparse(url)
        subscription_name = parsed_url.path.split('/')[subscription_path]
    except IndexError:
        logger.error("No subscription name found!")
        return None
    return subscription_name

################# Download functions

def direct_download_batch(file:str):
    """ This function represents the "manual" video download approach but using a batch file
        You can pass an url and the file will be downlaoded, hashed and registered.

        The parameter "own_file_data" is from prepare_scheme_dst_data()!
        Return Values:bool
        - True (Successfully downloaded file and registered it in db)
        - False (Failed - either during download or registration / hashing)
    """

    file = os.path.abspath(file)
    if not os.path.isfile(file):
        logger.error("File %s doesn't exist!", file)
        return False

    failed = False
    with open(file, 'r', encoding="UTF-8") as input_file:
        for line in input_file:
            line = line.strip()
            if not direct_download(line):
                failed = True

    if not failed:
        logger.info("All files successfully downloaded")
        return True
    logger.error("Error while downloading batch!")
    return False

#This function is called from CLI
def direct_download(url:str, own_file_data:dict=None):
    """ This function represents the "manual" video download approach
        You can pass an url and the file will be downlaoded, hashed and registered.

        The parameter "own_file_data" is from prepare_scheme_dst_data()!
        Return Values:bool
        - True (Successfully downloaded file and registered it in db)
        - False (Failed - either during download or registration / hashing)
    """
    #Line Break for Pylint #C0301
    logger.info("""Directly download content from %s -
                Check prerequisites and prepare download data""", url)

    if not own_file_data:
        prepared_data = prepare_scheme_dst_data(url)
    else:
        prepared_data = own_file_data


    if prepared_data["status"] != 1:
        logger.error("Error while preparing download! - Check log.")
        return False

    path = prepared_data["dst_path"]

    logger.info("File will be saved under: %s", path)

    downloaded = download_file(url, path)

    if not downloaded["status"]:
        logger.error("Error while downloading file from %s - Please check log!", url)
        return False

    full_file_path = downloaded["full_file_path"]
    metadata = downloaded["metadata"]
    logger.debug("Full File path is: %s", full_file_path)
    #Compute hash from file
    file_hash = create_hash_from_file(full_file_path)
    #Check if hash created successfully

    if not file_hash["status"] or file_hash["hash"] is None:

        logger.error("Error while creating hash from file! - Please check log. - Results: %s, %s",
                     file_hash["status"], file_hash["hash"])

        error_post_processing(full_file_path)
        return False
    #Check if hash is already in database
    #If hash is not in db -> Video is new -
    #If hash is in db video already exist. Check if the url is the same
    hash_exist = fetch_value("items", {"file_hash": file_hash["hash"]}, None, True)

    if not hash_exist:
        video_registered = save_file_to_db(prepared_data,
                                           full_file_path,
                                           file_hash["hash"],
                                           {"url": [url]},
                                           metadata)
        if video_registered:
            logger.info("File successfully downlaoded.")
            return True
        logger.error("Error while register Video to db!")
        error_post_processing(full_file_path)
        return False

    return True

#This function will actually download a file...
def download_file(url, path, metadata=None, ignore_existing_url=False):
    """This function downloads the file specified in url and also provides the prepared
        file path from ydl

        if the metadata parameter is None they will be fetched

        Return Value:dict
        {
            "status": False, - Operation successfull? - Use it as probe!
            "full_file_path": None, - The full file path to the file (absolute path)
                                        including the filename
            "filename": None,
            "metadata": None - Metadata from the file
        }
    """
    return_val = {"status": False, "full_file_path": None, "filename": None, "metadata": None}
    metadata = get_metadata(url, get_ydl_opts(path))
    if metadata is None:
            logging.error("Error while fetching metadata to check if video already exists in db! - Continue without checking")
            return return_val

    full_file_path = YoutubeDL(get_ydl_opts(path)).prepare_filename(metadata,
                                                                      outtmpl=path +
                                                                      '/%(title)s.%(ext)s')

    filename = os.path.basename(full_file_path).split(os.path.sep)[-1]
    return_val["full_file_path"] = full_file_path
    return_val["filename"] = filename
    if not ignore_existing_url:
        #Check if video (path) is in db

        file_in_db = fetch_value("items", {"file_path": path, "file_name": filename}, ["file_path"], True)
        if  file_in_db is not None:
            logging.info("Video already exists in DB! - check if url exist")
            url_is_in_db = check_is_url_in_items_db(url, filename, path)
            if not url_is_in_db["status"]:
                logger.error("Error while checking if url is in db!")
                #Since the file already exist there is no really need to download the file again. The url add is only a double check.
                # So we will return true
                return_val["status"] = True
                return return_val
            if not url_is_in_db["url_exist"]:
                logger.debug("File is already in DB (name match) but url is not the same. Add url to entry!")
                url_added = add_url_to_item_is_db(url_is_in_db["id"], url)
                if not url_added:
                    logger.error("Error while adding url to file in DB!")
                    return_val["status"] = True
                    return return_val
            return_val["status"] = True
            return return_val

    logging.info("File %s dont exist in DB", full_file_path)

    logger.info("Downloading file from server")


    try:
        ydl_opts = get_ydl_opts(path)

        #Fetch metadata if not passed
        if metadata is None:
            metadata = get_metadata(url, ydl_opts)

        if not metadata or "title" not in metadata or "ext" not in metadata:
            #Line Break for Pylint #C0301
            logger.error("""Error while fetching metadata from target server! -
                         Metadata could not be fetched or key \"title\" / \"ext\" is missing""")
            return return_val

        with YoutubeDL(ydl_opts) as ydl:
            value = ydl.download([url])

        #https://github.com/yt-dlp/yt-dlp/issues/4262
        if value == 0 or value == 1 or value == 100:
            #Line Break for Pylint #C0301
            full_file_path = YoutubeDL(ydl_opts).prepare_filename(metadata,
                                                                  outtmpl=path +
                                                                  '/%(title)s.%(ext)s')

            full_file_path = os.path.abspath(full_file_path)
            return_val["status"] = True
            return_val["full_file_path"] = full_file_path
            return_val["metadata"] = metadata

            return return_val
        logger.error("YDL reported code %s", value)
        return return_val
    except DownloadError as e:
        logger.error("Error while downloading video!- Error: %s", e)
        return return_val

def download_missing():
    """
        This function iterates over all subscriptions and download missing videos
        (has_new_data = 1 or download count < plalist_content_count)
        The function does NOT check for new Videos on the playlist.
        It utilizes the metadata column from the db! -
        To fetch actual data the function update_subscriptions() should be called!

        Return Value: bool
        - True (Successfully downlaoded all files)
        - False (Error while downlaoding files)
    """
    logger.info("Download all missing videos...")

    subscriptions = fetch_value("subscriptions", None,
                                ["scheme",
                                 "subscription_name",
                                 "subscription_path",
                                 "downloaded_content_count",
                                 "subscription_content_count",
                                 "subscription_has_new_data",
                                 "current_subscription_data"], None, "ORDER BY scheme")

    if not subscriptions:
        logger.error("Error while fetching subscriptions!")
        return False
    failed_downloads = {}
    current_subscription = ""
    for subscription in subscriptions:
        downloaded = 0
        #Create a new error array for the current subscription
        failed_downloads[subscription[1]] = []
        if subscription[5] == 0:
            logger.info("Subscription %s does not have any new data! - Skip", subscription[1])
            continue
        #Downlaod data
        logger.info("Download content from %s", subscription[1])
        current_subscription = subscription[1]
        #try to load the json metadata from db
        try:
            metadata = json.loads(subscription[6])
        except json.JSONDecodeError:
            logger.error("Error while decoding data from db for subscription %s", subscription[1])
            continue

        #Iterate over all Videos from the playlist
        if not "entries" in metadata or not "playlist_count" in metadata:
            logger.error("Error while downloading content from %s! - Missing keys",
                         subscription[1])
            continue

        subscription_path = prepare_scheme_dst_data(subscription[2], True)

        if not subscription_path["status"] or not subscription_path["dst_path"]:
            logger.error("Error while deciding storage path for subscription %s!",
                          subscription[1])
            continue

        for entry in metadata["entries"]:
            #Check each entry if it already exist before downloading,
            #using the title and the link
            if not "title" in entry or not "url" in entry:
                logger.error("Entry misses needed keys! - SKIP")
                continue

            #To do all the work, the scheme is needed
            entry_scheme = load_scheme(entry["url"])

            if not entry_scheme["status"] or entry_scheme["scheme"] is None:
                logger.error("Error while loading scheme for %s! - SKIP", entry["title"])
                continue


            #Fetch the metadata of the current entry to try to check for the filename
            expected_path = subscription_path["dst_path"]

            if expected_path is None:
                logger.error("Error while fetching expected path for %s - SKIP", entry["title"])
                failed_downloads[subscription[1]].append(entry["title"])
                continue

            file_metadata = get_metadata(entry["url"], get_ydl_opts(expected_path))

            if file_metadata is None:
                logger.error("Error while fetching metadata! - Skip item %s", entry["title"])
                failed_downloads[subscription[1]].append(entry["title"])
                continue

            expected_filename = get_expected_filepath(file_metadata, expected_path)

            if not expected_filename["filename"]:
                logger.error("Error while fetching filename for %s! - Skip item", entry["title"])
                failed_downloads[subscription[1]].append(entry["title"])
                continue

            #This bool is used to decide if the current entry will be downloaded
            download_file_now = True

            file_already_exist_in_db = fetch_value("items", [
                {"file_name" : expected_filename["filename"]},
                {"url": entry["url"]}],
                ["id", "url", "tags", "data"], True)

            if(file_already_exist_in_db is not None and
               file_already_exist_in_db is not False and
               len(file_already_exist_in_db) > 0):
                download_file_now = False
                #Check if the file also exist on FS
                #Check if missing files should be redownlaoded automatically. If so do it here...
                # This function is also used in the check() function but only based on
                # db entries!
                redownload_missing_files = fetch_value_as_bool("config",
                                    {"option_name": "automatically_redownload_missing_files"},
                                    ["option_value"], True)

                if redownload_missing_files:
                    logger.debug("""File %s already exist on db! -
                             Redownload is enabled check for File on FS...""", entry["title"])

                    expected_file_path = os.path.join(expected_path, expected_filename["filename"])
                    file_already_exist_on_fs = os.path.isfile(expected_file_path)
                    if not file_already_exist_on_fs:
                        logger.info("""File %s already exists on db but not on your FS!
                                    File will be redownloaded...""", entry["title"])
                    else:
                        logger.debug("File also exist on FS - SKIP")
                        download_file_now = False
                        downloaded += 1
                else:
                    #Since files should not be redownloaded we will assume that the file exist
                    #on FS.
                    downloaded += 1
                    download_file_now = False

                #Check if all data are existing for the current file
                # url = file_already_exist_in_db[1], tags = 2, data = 3

                data_inserted = insert_missing_file_data_in_db(file_already_exist_in_db[0], entry["url"], file_metadata)

                if not data_inserted:
                    logger.error("Error while inserting data!")
            else:
                logger.info("New file %s will be downloaded", entry["title"])


            #If the file should not be downlaoded go to the next one
            if not download_file_now:
                continue

            file_downloaded = direct_download(entry["url"], subscription_path)

            if not file_downloaded:
                #Append to the current subscription error log
                failed_downloads[subscription[1]].append(entry["title"])
                continue
            logger.info("File %s successfully downloaded", entry["title"])
            downloaded += 1

        #Modify the "downloaded_content_count" column in db
        value_modified = update_value("subscriptions",
                                      {"downloaded_content_count": str(downloaded)},
                                      {"subscription_name" : str(current_subscription)})

        if not value_modified:
            logger.error("Error while modifing downlaoded content value")

    #Iterate over the error object and create error message
    error_shown = False
    for subscription_err_entry in failed_downloads:
        if len(failed_downloads[subscription_err_entry]) > 0:
            error_shown = True
            logger.error("Failed while downloading file for subscription %s",
                         subscription_err_entry)
            logger.error("Subscription: %s", subscription_err_entry)
            #Create a new error table
            error_table = PrettyTable(['title'])
            error_table.align["title"] = "l"
            for error_entry in failed_downloads[subscription_err_entry]:
                error_table.add_row([error_entry])
            print(error_table)
    if not error_shown:
        logger.info("All Data are successfully downlaoded!")
        return True
    return False

################# DB functions

def save_file_to_db(scheme_data, full_file_path, file_hash, url, metadata):
    """ This function is used to save a file into the items table. It is basically
        an SQL Insert wrapper

        Return Value: dict
        {
            "status": False -> Operation successfull? - Use it as probe
            "hash_exist": False -> Does the hash already exist in db?
            "file_id": 1 -> ID of the file with the same  hash
            "file_name": "hello.mp4" -> Name of the file with the same hash value
            "file_path": "/path/to/file" -> Path to the file
        }
    """
    return_val = {
        "status": False,
        "hash_exist": False,
        "file_id": None,
        "file_name": None,
        "file_path": None
    }
    #Video hash not exist as saved item add it...
    logger.info("Add Video to DB")
    scheme_path = scheme_data["scheme_path"]

    hash_exist = fetch_value("items", {"file_hash": file_hash}, ["id", "file_name", "file_path"], True)
    if  hash_exist is not None:
        logger.debug("File hash already exist in DB! - Skip saving File")
        return_val["file_id"] = hash_exist[0]
        return_val["file_name"] = hash_exist[1]
        return_val["file_path"] = hash_exist[2]
        return_val["hash_exist"] = True
        return_val["status"] = True


    head, tail = os.path.split(full_file_path)
    logger.debug("Scheme Data: %s", scheme_path)
    #Line Break for Pylint #C0301
    use_tags_ydl = fetch_value_as_bool("config", {"option_name": "use_tags_from_ydl"},
                                       ["option_value"], True)
    #Define base data
    video_data = {
        "scheme": scheme_data["scheme"]["schema_name"],
        "file_name": tail,
        "file_path": head,
        "file_hash": file_hash,
        "url": url,
        "data": metadata
    }
    if use_tags_ydl and metadata is not None:
        logger.info("Also insert tags from ydl metadata")
        if "tags" in metadata:
            logger.debug("Found key 'tags'")
            if len(metadata["tags"]) > 0:
                logger.debug("Tags found...")
                video_data["tags"] = metadata["tags"]
            else:
                logger.debug("Tags array is empty!")
        else:
            logger.debug("No tags key found in metadata")
    else:
        logger.info("Tags are not inserted from ydl")
    video_registered = insert_value("items", video_data)
    if not video_registered:
        logger.error("Error while saving file to db!! - Please check log.")
        #Line Break for Pylint #C0301
        remove_file = fetch_value_as_bool("config", {"option_name":
                                                     "remove_file_on_post_process_error"},
                                          ["option_value"], True)
        if remove_file:
            logger.info("Remove file due to config setting.")
            os.remove(full_file_path)
            if os.path.exists(full_file_path):
                #Line Break for Pylint #C0301
                logger.error("""Error while removing video after post processing error! -
                              Check permissions""")
            return return_val
        logger.warning("File will not be removed! - Be cautious, the file is not saved in the db!")
        return return_val
    logger.info("Video successfully saved. - Finished")
    return_val["status"] = True
    return return_val

def export_items():
    "This functions exports all items saved in the db"

    items = fetch_value("items", None, ["scheme",
                                                        "file_name",
                                                        "file_path",
                                                        "file_hash",
                                                        "url",
                                                        "created",
                                                        "tags",
                                                        "data"])

    if items is None:
        logging.error("Error while fetching items")

    exported_items:list = []
    for item in items:
        item_obj = {
            "scheme": item[0],
            "file_name": item[1],
            "file_path": item[2],
            "file_hash": item[3],
            "url": item[4],
            "created": item[5],
            "tags": item[6],
            "data": item[7]
        }
        exported_items.append(item_obj)
    base_path = fetch_value("config", {"option_name": "base_location"}, ["option_value"], True)

    if not base_path or not isinstance(base_path, tuple):
        logging.error("Error while fetching base path from config! - Use default (Partent directory)")
        base_path = "./"
    else:
        base_path = base_path[0]

    logging.info("Exported %i items. Create file at %s", len(exported_items), os.path.abspath(base_path))

    #Insert list into file.

    try:
        with open(os.path.join(os.path.abspath(base_path),
                               "items_export.json"),
                               encoding="UTF-8",
                               mode="w+") as item_file:
            items_as_json = json.dumps(exported_items)
            item_file.write(items_as_json)
        logging.info("items exported")
    except FileNotFoundError as e:
        logging.error("Error while creating file! - Error: %s", e)
        return False
    except json.JSONDecodeError as e:
        logging.error("Error while parsing JSON array with items! - Error: %s", e)
        return False
    return True

def import_items(path="./"):
    """ This function imports items based on a json file (generated by export_items function)"""
    logging.info("Import items from %s", path)

    if not os.path.exists(path):
        logging.error("The given path does not exist!")
        return False

    try:
        with open(os.path.abspath(path), encoding="UTF-8", mode="r") as f:
            items = f.read()

        items = json.loads(items)
        #Iterate over json array
        error_raised = False
        failed_imports = []
        for item in items:
            success = insert_value("items", item)
            if not success:
                error_raised = True
                failed_imports.append(item["file_name"])

        if error_raised:
            for failed_import in failed_imports:
                logging.error("Error while importing %s to db!", failed_import)
            return False
        logging.info("All items successfully imported!")
    except FileNotFoundError as e:
        logging.error("item file not found! - Error: %s", e)
        return False
    except json.JSONDecodeError as e:
        logging.error("Error while loading JSON File! - Error: %s", e)
        return False
    return True

################# Scheme functions

### Scheme functionality
def scheme_setup():
    """ Check all schemes if tables are needed in the db

        Return Values: bool
        - True (Success)
        - False (Error while creating table or loading scheme)
    """
    script_dir = pathlib.Path(__file__).parent.resolve()

    if not os.path.isdir(os.path.join(script_dir, "scheme")):
        logger.error("The scheme folder does not exist in the script folder! - Please add it!")
        return False

    error_occured = False
    #Iterate over all existing scheme files and create tables if needed
    for scheme in os.listdir(os.path.join(script_dir, "scheme")):
        try:
            #load scheme data
            scheme_path = os.path.join(script_dir, "scheme")
            scheme_path = os.path.join(scheme_path, scheme)
            scheme_data = load_json_file(scheme_path)

            #check if there is a "db" key -> If not a table is not needed - SKIP
            if "db" in scheme_data and "table_needed" in scheme_data["db"]:
                #Check if a table is needed
                if scheme_data["db"]["table_needed"] is True:
                    #Check if table exists - if not create it
                    if not "table_name" in scheme_data["db"]:
                        #Line Break for Pylint #C0301
                        logger.error("""Error while checking for table in schema %s.
                                      Key table_name is missing!""", scheme)
                        error_occured = True
                        continue
                    table_exists = check_table_exist(scheme_data["db"]["table_name"])

                    if not table_exists:
                        result = create_table(scheme_data["db"]["table_name"],
                                              scheme_data["db"]["columns"])

                        if not result:
                            #Line Break for Pylint #C0301
                            logger.error("""Error while creating table %s for scheme %s! -
                                          Check log""", scheme_data["db"]["table_name"], scheme)
                            error_occured = True
                            continue
                        #Line Break for Pylint #C0301
                        logger.info("""Table %s for scheme %s successfully created!""",
                                     scheme_data["db"]["table_name"], scheme)
                        #If table is created check if there are any default values and add these
                        if "rows" in scheme_data["db"]:
                            logger.info("""Found default values for scheme %s -
                                        Insert into table""",
                                        scheme)
                            for option in scheme_data["db"]["rows"]:
                                #Iterate over all default options and insert them to the config
                                #table
                                row_inserted = insert_value(
                                    scheme_data["db"]["table_name"],
                                    option)
                                if not row_inserted:
                                    logger.error("Error while inserting row: %s!", option)
                                    continue
                                logger.debug("Row inserted")
                        else:
                            logger.debug("There are no default rows in scheme %s", scheme)
                            continue
                else:
                    logger.debug("Scheme %s does not need a table - SKIP", scheme)
                    continue
            else:
                logger.debug("Scheme %s does not contain a db key - SKIP", scheme)
                continue
        except json.JSONDecodeError as e:
            logger.error("Error while initializing scheme %s! - JSON Error: %s", scheme, e)
            return False
    if not error_occured:
        return True
    return False

def load_scheme(url: str):
    """ This function loads a scheme needed to work with the url and save data correct.

        Return Values: dict
        {
            "status": False, -> Operation successfull? - Use it as probe
            "scheme": None,  -> The scheme file as dict
            "scheme_path": None -> The absolute path to the scheme file - can be used with open()
        }
    """
    return_scheme = {"status": False, "scheme": None, "scheme_path": None}
    #Search for scheme
    scheme_data = fetch_scheme_file(url)
    if not scheme_data["status"]:
        logger.error("Error while fetching scheme! - Check log")
        return return_scheme

    scheme_path = scheme_data["scheme_path"]

    #Load Scheme
    scheme = load_json_file(scheme_path)
    if not scheme:
        logger.error("Error while loading scheme! - Check log")
        return return_scheme

    #Check if scheme is valid
    if not validate_scheme(url, scheme):
        logger.error("Error while validating scheme! - Check log")
        return return_scheme

    return_scheme["status"] = True
    return_scheme["scheme"] = scheme
    return_scheme["scheme_path"] = scheme_path
    return return_scheme

def load_scheme_by_name(scheme_name:str):
    """
        This function loads a scheme by it's name.

        Return Values: dict
        {
            "status": False, -> Operation successfull? - Use it as probe
            "scheme": None,  -> The scheme file as dict
            "scheme_path": None -> The absolute path to the scheme file - can be used with open()
        }
    """
    return_scheme = {"status": False, "scheme": None, "scheme_path": None}

    logger.debug("Load Scheme %s", scheme_name)
    scheme_dir = os.path.join(pathlib.Path(__file__).parent.resolve(), "scheme")
    expected_scheme_path = os.path.join(scheme_dir, scheme_name + ".json")

    if not os.path.isfile(expected_scheme_path):
        logging.error("Can't load scheme file! - File not exist!")
        return return_scheme

    #Load Scheme
    scheme = load_json_file(expected_scheme_path)
    if not scheme:
        logger.error("Error while loading scheme! - Check log")
        return return_scheme

    return_scheme["status"] = True
    return_scheme["scheme"] = scheme
    return_scheme["scheme_path"] = expected_scheme_path
    return return_scheme

def fetch_scheme_file(url:str):
    """
        This function is used to fetch a matching scheme.
        There are in general 2 ways to fetch a scheme by an url.
        The function first tries to fetch a schem,e by trying to match
        the sld (second level domain like "reddit")
        with a scheme file name like "reddit.json".
        If the function can't find any matching file,
        it will iterate over all files and search for
        a scheme file where the url matches all conditions (subdomain, sld and tld).

        Return Value:dict
        {
            "status": False,  -> Operation successfull? - True if scheme file found,
                                False on error or no scheme file
            "scheme_path": None,  -> The absolute path to the scheme file
            "scheme_file": None -> The name of the file (e.g. reddit.json)
        }

    """
    return_val = {"status": False, "scheme_path": None, "scheme_file": None}
    script_dir = pathlib.Path(__file__).parent.resolve()

    if not os.path.isdir(os.path.join(script_dir, "scheme")):
        logger.error("The scheme folder does not exist in the script folder! - Please add it!")
        return return_val

    parsed_url = tldextract.extract(url)

    expected_scheme_path = os.path.join(script_dir, "scheme")
    expected_scheme_path = os.path.join(expected_scheme_path, str(parsed_url.domain + ".json"))
    if not os.path.isfile(expected_scheme_path):
        logger.info("No suitable file found by filename. Check per file...")
        scheme_check = fetch_scheme_file_by_file(url)

        if not scheme_check["status"]:
            logger.error("There is no matching scheme file for site %s!", parsed_url.domain)
            return return_val

        return scheme_check
    logger.debug("Scheme file for %s found", parsed_url.domain)
    logger.debug("Check if provided url %s is valid for scheme", parsed_url.domain)
    return_val["scheme_path"] = expected_scheme_path
    return_val["scheme_file"] = str(parsed_url.domain + ".json")
    return_val["status"] = True
    return return_val

def validate_scheme(url, scheme, silent=False):
    """ This function validates a scheme file and check for all needed keys that are needed to
        download a file and save it correctly. It is used for both system schemes and url schemes.
        Use this function for all validations!

        Return Values:bool
        - True (Scheme Valid)
        - False (Scheme misses keys)
    """
    #Check if the loaded template is a url template
    if not "url_template" in scheme or scheme["url_template"] is False:
        #Line Break for Pylint #C0301
        logger.error("""The laoded scheme is not marked as a url_template! -
                      Please mark it as url template (Add key 'url_template' with value 'true'
                      to json file)""")
        return False

    #validate the url scheme for the most basic keys
    if not validate_url_scheme(scheme):
        logger.error("Provided Scheme is not valid! - Check log")
        return False

    parsed_url = tldextract.extract(url)
    #Check if the provided url matches the filter of the given scheme
    if not parsed_url.suffix in scheme["url_scheme"]["tld"]:
        if not silent:
            #Line Break for Pylint #C0301
            logger.error("""Provided url does not match the requirements for the %s scheme! -
                          TLD '%s' is not supported! - scheme name: %s""",
                          parsed_url.domain, parsed_url.suffix, scheme["schema_name"])
        return False
    if not parsed_url.domain in scheme["url_scheme"]["sld"]:
        if not silent:
            #Line Break for Pylint #C0301
            logger.error("""Provided url does not match the requirements for the %s scheme! -
                          SLD '%s' is not supported! - scheme name: %s""",
                          parsed_url.domain, parsed_url.domain, scheme["schema_name"])
        return False
    if not parsed_url.subdomain in scheme["url_scheme"]["subd"]:
        if not silent:
            #Line Break for Pylint #C0301
            logger.error("""Provided url does not match the requirements for the %s scheme! -
                          Subdomain '%s' is not supported! - scheme name: %s""",
                          parsed_url.domain, parsed_url.subdomain, scheme["schema_name"])
        return False
    return True

####Scheme helper

def validate_url_scheme(scheme:json):
    """ This function is a helper for validate_scheme(). Every url scheme needs
        to have a defined set of keys. This function checks if every key exists.

         It is likly that this function will change in the future since
         there is a python module called json schemes which can do exactly this...

          Since this is a helper for another function you should not use this!
          Return Values:
          - True (Scheme is valid)
          - False (Some keys are missing)
    """
    #Check basic keys needed for general function
    last_faulty_category = None
    last_missing_key = None
    needed_keys = ["schema_name", "url_template", "url_scheme", "categories", "storage"]

    all_keys_exist = True
    for required_key in needed_keys:
        if not required_key in scheme:
            all_keys_exist = False

    if not all_keys_exist:
        #Line Break for Pylint #C0301
        logger.error("""Some required keys are missing in the given scheme file! -
                      Please check your scheme. - Required keys: %s""", needed_keys)
        return False

    #Check keys needed for url validation
    needed_url_scheme_keys = ["tld", "sld", "subd"]
    all_keys_exist = True
    for required_key in needed_url_scheme_keys:
        if not required_key in scheme["url_scheme"]:
            all_keys_exist = False

    if not all_keys_exist:
        #Line Break for Pylint #C0301
        logger.error("""Some required url_scheme keys are missing in the given scheme file! -
                      Please check your scheme.""")
        return False

    #Check minimum keys for categorizing
    needed_category_scheme_keys = ["available"]
    all_keys_exist = True
    for required_key in needed_category_scheme_keys:
        if not required_key in scheme["categories"]:
            all_keys_exist = False

    if not all_keys_exist:
        #Line Break for Pylint #C0301
        logger.error("""required category key 'available' is missing in the
                      given scheme file! - Please check your scheme.""")
        return False

    if scheme["categories"]["available"] is True:
        if not "needed" in scheme["categories"]:
            logger.error("""Required key 'needed' is missing in the categories
                         part of scheme!""")
            return False

    #Check if categories have all needed keys
    if "categories" in scheme["categories"]:
        #Categories are defined check if they match the requirements
        needed_keys = ["direct_download", "subscription",
                       "subscription_url", "storage_path"]
        all_keys_exist = True
        for category in scheme["categories"]["categories"]:
            for needed_key in needed_keys:
                if not needed_key in scheme["categories"]["categories"][category]:
                    all_keys_exist = False
                    last_faulty_category = category
                    last_missing_key = needed_key
        if not all_keys_exist:
            logger.error("""Category %s does not meet the minimum requirements!
                           - Key %s is missing!""",
                          last_faulty_category, last_missing_key)
            return False

    #Check for subscription keys
    if("subscription" in scheme and
       "availiable" in scheme["subscription"]
       and scheme["subscription"]["availiable"] is True):
        needed_subscription_scheme_keys = ["available",
                                           "subscription_name_locator",
                                           "url_blueprint"]
        all_keys_exist = True

        for required_key in needed_subscription_scheme_keys:
            if not required_key in scheme["subscription"]:
                last_missing_key = required_key
                all_keys_exist = False

        if not all_keys_exist:
            logger.error("""Category subscription does not meet the minimum requirements!
                           - Key %s is missing!""",
                          last_missing_key)
            return False
    return True

def fetch_scheme_file_by_file(url):
    """ This function is a helper for fetch_scheme_file().
        It iterates over all scheme files and try to find
        a matching scheme by checking the conditions an url needs to meet.
        This function is used as a second step if
        no filename matches the sld.

        Return Value: dict
            {
                "status": False,  -> Operation successfull? - Use it as probe
                "scheme_path": None,  -> The absolute path to the scheme file
                "scheme_file": None -> The name of the scheme file e.g reddit.json
            }
    """
    return_val = {"status": False, "scheme_path": None, "scheme_file": None}
    script_dir = pathlib.Path(__file__).parent.resolve()

    if not os.path.isdir(os.path.join(script_dir, "scheme")):
        logger.error("The scheme folder does not exist in the script folder! - Please add it!")
        return return_val

    #iterate over all files in directory
    scheme_folder = os.path.join(script_dir, "scheme")

    for scheme_file in os.listdir(scheme_folder):
        #Try to load json file
        scheme = load_json_file(os.path.join(scheme_folder, scheme_file))

        if not scheme:
            logger.error("Error while reading scheme file %s", scheme_file)
            continue

        #Check if the scheme file is a url template (used for websites) or
        #a system template (for local use)
        if "url_template" in scheme and scheme["url_template"] is True:
            if not validate_url_scheme(scheme):
                logger.error("Scheme %s is not a valid url scheme!", scheme_file)
                continue

            if validate_scheme(url, scheme):
                logger.info("Found suitable scheme file - Scheme used: %s", scheme_file)
                return_val["scheme_file"] = scheme_file
                return_val["scheme_path"] = os.path.join(scheme_folder, scheme_file)
                return_val["status"] = True
                return return_val
        else:
            continue
    return return_val

def prepare_scheme_dst_data(url, is_subscription=False):
    """
        This function prepares all data needed to download and save a file.
        It first checks if the fgiven url is aalive (reachable) and after that
        loads the matching scheme, validates it and give information where to save the file

        Return Value: dict

        {
            "status": 0, -> Possible values: int - 0 = Failed, 1 = Success,
                                                    2 = File already exist - use it as a probe!
            "scheme": None,  -> The scheme file as dict
            "scheme_path": None, -> The absolute path to the scheme
            "dst_path": None -> The absolute path where to sabve the file that will be downloaded
        }
    """

    return_val = {"status": 0, "scheme": None|dict, "scheme_path": None, "dst_path": None}
    #Check if the url is reachable
    url_alive = alive_check(url)
    #Check if the given url already exists in the items db
    url_already_exist = fetch_value("items", {"url": url}, ["url"], True)
    #Try to load a scheme matching the current url
    scheme = load_scheme(url)

    if not url_alive or url_already_exist is not None or not scheme["status"]:
        if not url_alive:
            logger.error("Can't download video! - Url can not be reached! - Check log above!")
        if url_already_exist is not None:
            logger.error("Video already exist in db!")
            return_val["status"] = 2
        if not scheme["status"]:
            logger.error("Error while loading scheme data! - Check log")
        return return_val

    #Check if laoded scheme is valid
    scheme_validated = validate_url_scheme(scheme["scheme"])

    if not scheme_validated:
        logger.error("Error while validating scheme!")
        return return_val

    return_val["scheme_path"] = scheme["scheme_path"]
    return_val["scheme"] = scheme["scheme"]

    #Scheme is valid. Decicde where to save the file (Check for categories). Read general config
    #and do the stuff...
    dst_path = decide_storage_path(url, scheme["scheme"], is_subscription)
    if not dst_path:
        logger.error("Error while defining storage path! - Check log")
        return return_val
    return_val["status"] = 1
    return_val["dst_path"] = dst_path

    return return_val

################# Validation

def validate(rehash=True):
    """ This function itereates over all folders from the root directory (base path in db)
        and checks

        Return Value: bool
            -> True - Success
            -> False -> Failed while validating
    """

    #fetch base path
    base_path = fetch_value("config", {"option_name": "base_location"}, ["option_value"], True)

    if not base_path:
        logger.error("Error while fetching base path!")
        return False
    base_path = base_path[0]

    base_path = os.path.abspath(base_path)

    error_happened = False
    error_files = []
    error_messages = []
    added_files = 0
    for current_dir, current_dir_directories, current_dir_files in os.walk(base_path):
        for file in current_dir_files:
            #Get the filepath of the current file
            abs_file_path = os.path.join(current_dir, file)

            path_data = fetch_path_data(abs_file_path)

            if not path_data["status"]:
                logger.error("Error while fetching path data for path %s", abs_file_path)
                error_happened = True
                error_files.append(abs_file_path)
                error_messages.append("Error while fetching Path Data!")
                continue

            if path_data["schema_name"] is None or path_data["schema_name"] == "custom":
                logger.warning("File %s can not be tested! - Schema \"%s\" is not valid", path_data["filename"], path_data["schema_name"])
                continue

            #Check if Video is in DB
            file_in_db = fetch_value("items", {"file_name": path_data["filename"]}, ["file_name", "scheme", "file_hash", "locked"], True)

            if file_in_db is None:
                #Add file to db
                file_hash = create_hash_from_file(abs_file_path)

                if not file_hash["status"]:
                    logger.error("Error while hashing file! - Can't add file to db!")
                    error_happened = True
                    error_files.append(abs_file_path)
                    error_messages.append("Error while creating hash for file!")
                    continue

                #File hash created add other stuff
                loaded_scheme = load_scheme_by_name(path_data["schema_name"])

                if not loaded_scheme["status"]:
                    error_happened = True
                    error_files.append(abs_file_path)
                    error_messages.append("Error while fetching scheme data for file!")

                file_saved = save_file_to_db(loaded_scheme, abs_file_path, file_hash["hash"], None, None)

                if not file_saved["status"]:
                    error_happened = True
                    error_files.append(abs_file_path)
                    error_messages.append("Error while saving video in db!")
                    continue
                elif file_saved["status"] and file_saved["hash_exist"]:
                    logger.debug("File already exist in db!")
                    add_duplicate_file(file_hash["hash"], path_data["filename"], os.path.abspath(current_dir), file_saved["file_id"], file_saved["file_name"], file_saved["file_path"])
                else:
                    logging.info("File %s added to DB!", file)
                    added_files += 1
    if not error_happened:
        logging.info("All files validated! - Added %i files", added_files)
        return True
    else:
        logger.error("Error while validating files. Errors:")
        for index, error_message in enumerate(error_messages):
            logger.error("Affected File: %s, Error: %s", error_files[index], error_message)
        return False

################# Helper
def fetch_path_data(path):
    '''
        This function returns the expected file scheme based on a defined rule set and the strict defined path syntax from this project.

        Expcected Syntax:

        <<base path>>/<<scheme_name>>/<<files / category>>/<<files - only category>>

        Return Value:
            {
                "status": False, -> Operation successfull? - Use it as probe!
                "schema_name": None,  -> Extracted / Assumed scheme name (could be empty) - but only for files in base bath
                "subscription": None, -> Extracted / Assumed subscription name (could be empty)
                "category": None,  -> Extracted / Assumed category (could be empty)
                "filename": None -> Extracted file name
            }
    '''
    return_val = {"status": False, "schema_name": None, "subscription": None, "category": None, "filename": None}

    base_path = fetch_value("config", {"option_name": "base_location"}, ["option_value"], True)

    if not base_path:
        logger.error("Error while fetching base path!")
        return return_val

    base_path = base_path[0]
    base_path = os.path.abspath(base_path)

    if not base_path in path:
        logger.error("Can't find basepath in passed path! - Unexpected event")
        return return_val

    #Remove the base path from the file path and strip the leading / or \ with os.sep => Separator for FS...
    prepare_path = str(path).replace(base_path, "").strip(os.sep)
    prepare_path = prepare_path.split(os.path.sep)

    #4 possible outcomes =>
    #   Array len = 1 -> Only File, File is in base path?
    #   Array len = 2 -> Only Scheme and file -> Scheme dont support categories or subscriptions (e.g. custom)
    #   Array len = 3 -> There is no category
    #   Array len = 4 -> Category exist

    if len(prepare_path) == 1:
        return_val["filename"] = prepare_path[0]
    elif len(prepare_path) == 2:
        return_val["schema_name"] = prepare_path[0]
        return_val["filename"] = prepare_path[1]
    elif len(prepare_path) == 3:
        return_val["schema_name"] = prepare_path[0]
        return_val["subscription"] = prepare_path[1]
        return_val["filename"] = prepare_path[2]
    elif len(prepare_path) == 4:
        return_val["schema_name"] = prepare_path[0]
        return_val["subscription"] = prepare_path[1]
        return_val["category"] = prepare_path[2]
        return_val["filename"] = prepare_path[3]
    else:
        logger.error("Unexcepted array length! - Please open an issue on Github and pass the folowwing output:")
        print("Passed Path: " + str(path))
        print("Array: " + str(prepare_path))
        exit()

    return_val["status"] = True
    return return_val

def show_help():
    """
        This function shows help
        Return Value: None
    """
    print("------------------------------ Help ------------------------------")
    #Line Break for Pylint #C0301
    print("""You asked for help... Here it is :) -
          Run YT-Manager with the following commands and you're good to go""")
    help_table = PrettyTable(['Command', 'argument', 'description'])
    help_table.align['Command'] = "l"
    help_table.align['argument'] = "l"
    help_table.align['description'] = "l"
    help_table.add_row(['--Subscriptions--', '', ''])
    help_table.add_row(['add-subscription', '<<url>> / batch <<file>>', 'Add a new subscription'])
    #Line Break for Pylint #C0301
    help_table.add_row(['del-subscription',
                        '<<number>> | <<Name>>, <<delete_content>>',
                        '''Delete a subscription. You can either provide the ID
                        of your subscription (use list-subscriptions)'''])
    #Line Break for Pylint #C0301
    help_table.add_row(['', '',
                        '''or the name of the subscription (Name of a channel).
                        The second parameter defines if all content of this channel also
                        should be removed (Default: False = NO)'''])
    #Line Break for Pylint #C0301
    help_table.add_row(['list-subscriptions',
                        '<<filter>>',
                        '''List all subscriptions - You can provide a Filter (Array) of schemes
                        you want to include'''])
    help_table.add_row(['import-subscriptions',
                        '<<file>>',
                        '''Import subscriptions from another instance (JSON File).
                        You can make backups using "export-subscriptions"'''])
    help_table.add_row(['export-subscriptions',
                        '',
                        '''Create a Backup of the subscription table. A JSON File is created in the base directory'''])
    help_table.add_row(['import-subscriptions',
                        '',
                        '''Import a Backup of the subscription table.'''])
    help_table.add_row(['', '', ''])
    help_table.add_row(['--Other--', '', ''])
    #Line Break for Pylint #C0301
    help_table.add_row(['validate',
                        '',
                        '''After any downloaded file a hash is generated and stored.
                        For both checking for any duplicate files (independent of the name) and
                        checking integrity of files (and maybe redownload them).'''])
    #Line Break for Pylint #C0301
    help_table.add_row(['',
                        '',
                        '''If you use this command all files will be revalidated and
                        a report will be generated if there are any mismatches. '''])
    #Line Break for Pylint #C0301
    help_table.add_row(['',
                        '',
                        '''But be aware -
                        This operation can take very long and consumes much power...
                        Use it with care or overnight :) -
                        At the end you will see a report and you can decide if mismatched files
                        should be redonwloaded'''])
    help_table.add_row(['backup',
                        '',
                        '''Create a backup and export all subscriptions and items into json files.'''])
    help_table.add_row(['export-items',
                        '',
                        '''Create a backup file with all items in the db.'''])
    help_table.add_row(['import-items',
                        '<<path>>',
                        '''Create a backup file with all items in the db.'''])
    help_table.add_row(['show-duplicates',
                        '',
                        '''Show duplicates (use command validate before!)'''])

    help_table.add_row(['', '', ''])
    help_table.add_row(['--Operation--', '', ''])
    #Line Break for Pylint #C0301
    help_table.add_row(['custom',
                        '<<url>> / batch <<file>>',
                        '''In case you want to download a video from a channel without
                        a subscription you can do it here...
                        The file will saved in the default scheme based folder under /custom'''])
    #Line Break for Pylint #C0301
    help_table.add_row(['start',
                        '',
                        '''Run the script -> Check all subscriptions for
                        new content and download it'''])
    print(help_table)
    print("Example: yt-manager.py add-subscription youtube-url")
    print("------------------------------------------------------------------")

def alive_check(url: str):
    """ This function is used to check if the provided url works (HTTP 200 - OK)
        if not the video can not be downloaded

        Return Value: bool
        - True (Url is alive)
        - False (Url is not reachable)
    """
    #Check if url is reachable
    try:
        requested_url = requests.get(url, timeout=30)
        if requested_url.status_code == 200:
            return True
        #Line Break for Pylint #C0301
        logger.warning("""The requested url %s can not be reached.
                        Excepted result is HTTP 200 but got HTTP %s""",
                        url, requested_url.status_code)
        return False
    except requests.ConnectionError as e:
        #Line Break for Pylint #C0301
        logger.error("""Error while checking if url is alive! -
                     Maybe you passed an invalid url? - Error: %s""", e)
        return False

def fetch_category_name(url:str, scheme:json):
    """
        This function will extract the category name out of an given url based on the scheme.

        Return values:str
        - category_name
        - None -> No category found

    """
    logger.debug("Fetch category for url %s", url)
    if "category_path" in scheme["categories"]:
        category_path = scheme["categories"]["category_path"]
    else:
        #This should not be used!
        category_path = 1
    try:
        parsed_url = urlparse.urlparse(url)
        category = parsed_url.path.split('/')[category_path]
    except IndexError:
        logger.error("No category found at index %s", category_path)
        return None
    return category

def load_json_file(path:str):
    """ Read a json file and return it as a dict

        Return Values:str|None
        - dict/str - your file
        - None -> Parsing error / Not found
    """
    if not os.path.isfile(path):
        logger.error("The provided file does not exist! - Can't open file %s", path)
        return None
    try:
        with open(path, "r", encoding="UTF-8") as file:
            json_file = json.loads(file.read())
    except json.JSONDecodeError as e:
        logger.error("Error while reading json file! - JSON Error: %s", e)
        return None
    except FileNotFoundError as e:
        logger.error("Error while reading json file! - Error: %s", e)
        return None
    return json_file

def decide_storage_path(url, scheme, is_subscription=False):
    """
        This function is used as a helper to set the intended storage
        path for a specific file/url.
        It uses the provided scheme to check if it defines
        any storage rules and add them to the final path.

        The path is absolute!

        Return Values:str|None
            - path -> Absolute path to dst storage
            - None -> No path could be set
    """
    #First fetch the base location...
    data = fetch_value("config",
                       {"option_name": "base_location"},
                       ["option_value"], True)
    if not data:
        logger.error("""Error while fetching data from config db! -
                     Please check log""")
        return None
    base_path = data[0]
    base_path = os.path.abspath(base_path)

    if "storage" in scheme:
        if not "base_path" in scheme["storage"]:
            #Line Break for Pylint #C0301
            logger.error("""Error while fetching scheme base path! - \"base_path\" is
                          not defined as key! - Ignore it and use base path from general config""")
        else:
            base_path = os.path.join(base_path, scheme["storage"]["base_path"])
            logger.debug("Base path of scheme is: %s", base_path)
    else:
        #Line Break for Pylint #C0301
        logger.warning("""Scheme %s does not provide it's own storage path! -
                        Save data to the base directory""", scheme["schema_name"])
    subscription_name = ""
    if is_subscription:
        subscription_name = fetch_subscription_name(url, scheme)

        if subscription_name is None:
            logger.error("Error while fetching subscription name!")
            return None

    #Line Break for Pylint #C0301
    if ("categories" in scheme and "available" in scheme["categories"] and
        scheme["categories"]["available"] is True):
        #Decide if categories are used
        #Check if categories are defined. If not categories can not be used
        categories_defined = False
        if "categories" in scheme["categories"]:
            categories_defined = True

        def inner_decide_path(base_path):
            category_name = fetch_category_name(url, scheme)

            #Check if the given category is in the categories list
            if not category_name in scheme["categories"]["categories"]:
                logger.error("Category %s is not defined!", category_name)
                return None
            #Line Break for Pylint #C0301
            logger.debug("""Provided category %s is known...
                          Check for custom storage path""", category_name)

            if "storage_path" in scheme["categories"]["categories"][category_name]:
                #Line Break for Pylint #C0301
                base_path = os.path.join(base_path,
                            scheme["categories"]["categories"][category_name]["storage_path"])
                logger.debug("Custom category path is defined. Storage path is %s", base_path)
            else:
                #Line Break for Pylint #C0301
                logger.info("""Category %s don't have an individual storage path! -
                             Use path %s""", category_name, base_path)
            return base_path

        if scheme["categories"]["needed"] is True:
            #if url don't have category -> Fail
            logger.debug("Scheme requires category")
            if not categories_defined:
                #Line Break for Pylint #C0301
                logger.error("""Scheme requires categories but none are defined.
                              Please define categories or set them as optional!""")
            #Line Break for Pylint #C0301
            if ("category_storage" in scheme["storage"] and
                scheme["storage"]["category_storage"] is False):
                if not is_subscription:
                    return base_path
                return os.path.join(base_path, subscription_name)
            category_dst_path =  inner_decide_path(base_path)

            if not category_dst_path:
                return None
            if not is_subscription:
                return category_dst_path
            return os.path.join(category_dst_path, subscription_name)
        #Line Break for Pylint #C0301
        if("category_storage" in scheme["storage"] and
           scheme["storage"]["category_storage"] is False):
            path_ext = inner_decide_path(base_path)
            if not path_ext:
                if not is_subscription:
                    return base_path
                return os.path.join(base_path, subscription_name)
            if not is_subscription:
                return path_ext
            return os.path.join(path_ext, subscription_name)
    if not is_subscription:
        return base_path
    return os.path.join(base_path, subscription_name)

def get_metadata(url, ydl_opts):
    """
        This function fetches metadata from a given url (file and playlist).
        It also sanitize the dict to make it convertible to json (YT DLP)

        Possible return Values:dict|None
        - dict -> metadata
        - None -> Failed to fetch data

        Important keys in result:
        - title
        - uploader
        - tags
    """
    try:
        with YoutubeDL(ydl_opts) as ydl:
            #We only need the metadata. So we don't need to download the whole file.
            #We will do this later...
            file_data = ydl.sanitize_info(ydl.extract_info(url, download=False))
    except DownloadError as e:
        logger.error("Error while fetching File information from target server! - Error: %s", e)
        return None

    #Check if result have any content
    try:
        if len(file_data) > 0:
            return file_data
        return None
    except ValueError as e:
        #Line Break for Pylint #C0301
        logger.error("Error result seems to have no content! - \n\n Result: %s \n Error: %s",
                     file_data, e)
        return None
    except TypeError as e:
        logger.error("Error while fetching metadata! - Type Error: %s", e)
        return None

def get_ydl_opts(path, addons:json=None):
    """
        #The standards options for yt dlp.
        These can be modified if the parameter addons is passed.
        Also the rewrite of settings is possible.
        For the save of functionality the outtmpl key can not
        be altered since other parts of the program
        rely on this!

        Return Value: dict
        - Youtube DLP opts dict
    """
    opts = {
                'format': 'best',
                'outtmpl': path + '/%(title)s.%(ext)s',
                'nooverwrites': True,
                'no_warnings': True,
                'ignoreerrors': True,
                'replace-in-metadata': True,
                'restrict-filenames': True
            }
    if addons is None:
        #Return default set
        return opts
    for key in addons:
        if key == "outtmpl":
            continue
        opts[key] = addons[key]
    return opts

def create_hash_from_file(file):
    """
        This function creates a hash from a given file.

        Return Value: dict
        {
            "status": False, -> Operation successfull? - Use it as probe
            "file": None,  -> Absolute file path
            "hash": None -> hash of the given file (The same value as passed)
        }

    """
    return_val = {"status": False, "file": None, "hash": None}

    if file is None:
        logger.error("File is NONE!")
        return return_val
    logger.debug("Create hash from file %s", file)
    #create hash and return the hex value
    hash_obj = hashlib.sha256()
    try:
        with open(file, 'rb') as f: # Open the file to read it's bytes
            fb = f.read(BUF_SIZE) # Read from the file. Take in the amount declared above
            while len(fb) > 0: # While there is still data being read from the file
                hash_obj.update(fb) # Update the hash
                fb = f.read(BUF_SIZE) # Read the next block from the file
        return_val["file"] = file
        return_val["hash"] = hash_obj.hexdigest()
        return_val["status"] = True
        return return_val
    except FileNotFoundError as e:
        logger.error("Error while creating hash of file! - Error: %s", e)
        return return_val
    except OSError as e:
        logger.error("Error while creating Hash from file! - Error: %s", e)
        return return_val

def error_post_processing(full_file_path):
    """ This function is used to remove downloaded files if anything fails during post processing

    Return Values: bool
    - True - File is removed or keeped (defined in config table)
    - False - Error while removing file
    """
    #Line Break for Pylint #C0301
    remove_file = fetch_value_as_bool("config", {"option_name":
                                                 "remove_file_on_post_process_error"},
                                        ["option_value"], True)
    if remove_file:
        logger.info("Remove file due to config setting.")
        os.remove(full_file_path)
        if os.path.exists(full_file_path):
            #Line Break for Pylint #C0301
            logger.error("""Error while removing video after post processing error! -
                          Check permissions""")
            return False
        logger.info("File removed")
        return True
    logger.warning("File will not be removed! - Be cautious, the file is not saved in the db!")
    return True

def get_current_time():
    """
    Returns the current time like 2024-02-12 12:45:33

    Return Value:str
        - -1 -> Failed to get current time
        - timeval -> Current time
    """
    try:
        user_tz = config.get("other", "timezone")

        timezone_data = pytz.timezone(user_tz)
        current_time = datetime.now(timezone_data).strftime("%Y-%m-%d %H:%M:%S")
        return current_time
    except pytz.UnknownTimeZoneError:
        logger.error("""Timezone not known! -
                     You can choose between the following: %s - current: %s""",
                      pytz.all_timezones, user_tz)
        return -1

def get_expected_filepath(metadata:dict, path:str):
    """
        This function is a simple helper used to get the expected full file path.
        The project wide default scheme is <<title>>.<<ext>>.

        Return Values:str|None
        - None -> Failed to get filename
        - str -> Filename
    """
    if not "title" in metadata or not "ext" in metadata:
        logger.error("Metadata does not contain title or ext key!")
        return None

    filename = YoutubeDL(get_ydl_opts(path)).prepare_filename(metadata,
                                                                  outtmpl=path +
                                                              '/%(title)s.%(ext)s')
    head, tail = os.path.split(filename)
    return {"filepath": head, "filename": tail}

def check_is_url_in_items_db(url, filename=None, file_path=None, filename_is_id=False):
    """
        This functions checks if a given url exists in the items table under "url".
        This can be done for the whole table (filename=None) or for a specific file
        filename=<<filename>>

        Return Val: dict
            {
                "status": False -> Operation successfull? - Use it as probe
                "url_exist": False -> Url exist in items table?
                "id": 1 -> ID of file entry in db
                "file_name": <<name>> -> Name of file in DB
                "file_path": <<file_path>> -> Filepath of file in DB
            }
    """
    return_val = {"status": False, "url_exist": False, "id": None, "file_name": None, "file_path": None}
    if filename is None:
        logger.debug("Check if url %s is already in items", url)
    else:
        logger.debug("Check if url %s is already saved as url for item %s", url, filename)

    if filename is None and file_path is None:
        #Load all urls from items table
        fetched_urls = fetch_value("items", None, ["id", "file_name", "file_path", "url"])
    else:
        #Load only entry for the defined file
        if filename is None and filename_is_id is False:
            logging.error("Filename and filepath need to be specified!")
            return return_val
        if not filename_is_id:
            logger.debug("Load file with name and path")
            fetched_urls = fetch_value("items", {"file_name": filename, "file_path": file_path}, ["id", "file_name", "file_path", "url"])
        else:
           logger.debug("Load file with id")
           fetched_urls = fetch_value("items", {"id": filename}, ["id", "file_name", "file_path", "url"])


    if fetched_urls is None or fetched_urls == [] or not isinstance(fetched_urls, list):
        logger.error("Error while loading urls!")
        return return_val
    for item_obj in fetched_urls:
        urls = item_obj[3]
        if urls is None or urls.strip() == "":
            #There are no urls provided for the current obj - SKIP
            continue
        try:
            urls = json.loads(urls)
            urls = urls["url"]
            for item_url in urls:
                if item_url == url:
                    logging.debug("Url is in DB!")
                    return_val["status"] = True
                    return_val["url_exist"] = True
                    return_val["id"] = item_obj[0]
                    return_val["file_name"] = item_obj[1]
                    return_val["file_path"] = item_obj[2]
                    return return_val

        except json.JSONDecodeError:
            logger.error("Error while loading url column from db entry %s", item_obj[1])
            continue
    #Url not found
    #Return Val must include the following keys
    return_val["status"] = True
    return_val["url_exist"] = False
    if filename is not None:
        #These data are only needed if the url dont exist in a specified query
        # Since we fetched a specified file (filename and path) there should be only one entry in the array
        return_val["id"] = fetched_urls[0][0]
        return_val["file_name"] = fetched_urls[0][1]
        return_val["file_path"] = fetched_urls[0][2]
    return return_val

def add_url_to_item_is_db(item_id, url):
    """
        This functions adds a new url to an already existing item in the db.
        Since the url column contains a JSON array it is done with this helper function

        Return Value: bool
            - True -> Success
            - False -> Failed
    """
    logger.debug("Add url to item with id %s", item_id)

    #Fetch item
    item = fetch_value("items", {"id": item_id}, ["url", "id"], True)

    if item is None:
        logging.error("Error while adding url to item! - Can't fetch item")
        return False

    #Item loaded - try to load url (json format)
    try:
        if item[0] is not None and item[0].strip() != "":
            #Urls already defined
            urls = json.loads(item[0])
            urls = urls["url"]

            urls.append(url)
        else:
            #No urls defined
            urls = [url]

        new_urls_obj = {
            "url": urls
        }

        item_updated = update_value("items", {"url": new_urls_obj}, {"id": item_id})

        if not item_updated:
            logging.error("Error while updatig item!")
            return False
        return True
    except json.JSONDecodeError as e:
        logger.error("Error while decoding url array! - Error : %s", e)
        return False

def add_duplicate_file(hash_value, c_filename, c_filepath= None, db_id=None, db_filename=None, db_filepath = None):
    """
        This function is used to identify double files on DB/FS.
        The function creates a new file (if not exist) and will create a JSON scheme including all duplicates in the following format

        {
            "<<hash>>": [{"file_id": None, "file_name": None, "file_path": None}, {...}],
            ...
        }

        Return Val: Bool
            - True -> Successfully added duplicate
            - False -> Failed while adding duplicate
    """

    #Fetch base path
    base_path = fetch_value("config", {"option_name": "base_location"}, ["option_value"], True)

    if base_path is None:
        logger.error("Can't fetch base path!")
        return False

    base_path = os.path.abspath(base_path[0])
    duplicate_file_path = os.path.join(base_path, "duplicates.json")

    content = None
    if os.path.isfile(duplicate_file_path):
        with open(duplicate_file_path, encoding="UTF-8") as file:
            content = file.read()

    duplicates_json = {}
    if content is not None and content is not "":
        try:
            duplicates_json = json.loads(content)
        except json.JSONDecodeError:
            duplicates_json = {}

    if duplicates_json == {}:
        if (os.path.isfile(os.path.abspath(os.path.join(db_filepath, db_filename))) or
            os.path.isfile(os.path.abspath(os.path.join(c_filepath, c_filename)))):
            duplicates_json[hash_value] = [
                {"file_id": db_id, "file_name": db_filename, "file_path": db_filepath},
                {"file_id": None, "file_name": c_filename, "file_path": c_filepath}
            ]
        else:
            logger.error("Can't add files to duplicate list - files does not exist on FS!")
            if not os.path.isfile(os.path.abspath(os.path.join(db_filepath, db_filename))):
                logger.info("Remove file from db - since it don't exist!")
                delete_value("items", {"id": db_id})

    else:
        if hash_value in duplicates_json:
            listing = duplicates_json[hash_value]
            found_same = False
            new_listing = []
            for entry in listing:
                if not os.path.isfile(os.path.abspath(os.path.join(entry["file_path"], entry["file_name"]))):
                    logger.info("Remove file from db - since it don't exist!")
                    delete_value("items", {"id": db_id})
                else:
                    new_listing.append({"file_id": entry["file_id"], "file_name": entry["file_name"], "file_path": entry["file_path"]})

                if entry["file_name"] == c_filename and entry["file_path"] == c_filepath:
                    found_same = True

            if not found_same:
                new_listing.append({"file_id": None, "file_name": c_filename, "file_path": c_filepath})
                duplicates_json[hash_value] = new_listing
            else:
                duplicates_json[hash_value] = new_listing
        else:
            if not os.path.isfile(os.path.abspath(os.path.join(db_filepath, db_filename))):
                    logger.info("Remove file from db - since it don't exist!")
                    delete_value("items", {"id": db_id})
            else:
                duplicates_json[hash_value] = [
                {"file_id": db_id, "file_name": db_filename, "file_path": db_filepath},
                {"file_id": None, "file_name": c_filename, "file_path": c_filepath}
                ]

    #Write into file
    duplicates_json = json.dumps(duplicates_json)
    with open(duplicate_file_path, "w", encoding="UTF-8") as file:
        file.write(duplicates_json)
    return True

def show_duplicate_files():
    """
        This function is used to print all duplicates to the cli

        Return Val: None
    """

    #Fetch base path
    base_path = fetch_value("config", {"option_name": "base_location"}, ["option_value"], True)

    if base_path is None:
        logger.error("Can't fetch base path!")
        return False

    base_path = os.path.abspath(base_path[0])
    duplicate_file_path = os.path.join(base_path, "duplicates.json")

    content = None
    if os.path.isfile(duplicate_file_path):
        with open(duplicate_file_path, encoding="UTF-8") as file:
            content = file.read()

    duplicates_json = {}
    if content is None or len(content) < 2:
        logging.info("No duplicates found!")
        return None
    if content is not None and content is not "":
        try:
            duplicates_json = json.loads(content)
        except json.JSONDecodeError:
            logger.error("Error while reading duplicate file!")
            return None

    print("------------------------------ Duplicates ------------------------------")
    number_of_duplicates = len(duplicates_json)

    #Line Break for Pylint #C0301
    duplicate_table = PrettyTable(['filename', 'hash', 'paths'])
    duplicate_table.align['filename'] = "l"
    duplicate_table.align['hash'] = "l"
    duplicate_table.align['paths'] = "l"
    for duplicate in duplicates_json:
        duplicate_entries = duplicates_json[duplicate]
        #Use the first entry as name (This is the saved db value)
        file_name = duplicate_entries[0]["file_name"]
        avail_paths:str = ""
        for entry in duplicate_entries:
            avail_paths += os.path.join(entry["file_path"], entry["file_name"]) + "\n"

        duplicate_table.add_row([file_name, duplicate, avail_paths])
        duplicate_table.add_row(['','',''])
    duplicate_table.add_row(['Found duplicates: ',number_of_duplicates,''])
    print(duplicate_table)
    return None

def insert_missing_file_data_in_db(file_id, url, metadata):
    """
        This function is used as a helper.
        If a file already exists in the database we need to check if
        all information availiable are already inserted
        mainly -> url, metadata and tags (if enabled)
    """

    #Fetch all data needed
    db_entry = fetch_value("items", {"id": file_id}, ["url", "tags", "data"], True)

    if db_entry is None:
        logger.info("Cant fetch db entry!")
        return False

    logger.debug("Check if tags are allowed")
    tags_enabled = fetch_value_as_bool("config",
                                       {"option_name": "use_tags_from_ydl"},
                                       ["option_value"], True)
    error_occured = False
    if tags_enabled:
        logger.debug("Tags are enabled add...")
        #Check if tags already added to db entry

        if db_entry[1] is None or db_entry[1].strip() == "":
            logger.debug("Tags not added - Add to db entry")

            added_tags = update_value("items", {"tags": metadata["tags"]},
                                      {"id": file_id})
            if not added_tags:
                logging.error("Error while adding tags to %s", file_id)
                error_occured = True

    #check if metadata added
    if db_entry[2] is None or db_entry[2].strip() == "":
        logger.debug("Metadata not added - Add to db entry")

        added_tags = update_value("items", {"data": metadata},
                                  {"id": file_id})
        if not added_tags:
            logging.error("Error while adding metadata to %s", file_id)
            error_occured = True

    #Check if url is in db
    url_in_entry = check_is_url_in_items_db(url, file_id, None, True)

    if not url_in_entry["status"]:
        logger.error("Error while fetching url information from item!")
        error_occured = True
    else:
        if not url_in_entry["url_exist"]:
            url_added = add_url_to_item_is_db(file_id, url)

            if not url_added:
                logger.error("Error while adding url to item!")
                error_occured = True

    if not error_occured:
        logging.info("No error during adding data")
        return True
    logging.error("Error while adding data")
    return False

def check_for_workdir(inner=False):
    """
        This function checks if the defined workdir in the db is existing
    
    """
    workdir = fetch_value("config", {"option_name": "base_location"}, ["option_value"], True)

    if workdir is None:
        logger.error("Can't fetch workdir!")
        return False
    workdir = workdir[0]
    workdir_exist = os.path.isdir(os.path.abspath(workdir))
    if workdir_exist is False and not inner:
        os.mkdir(os.path.abspath(workdir))
        return check_for_workdir(True)
    if workdir_exist is False and inner:
        logger.error("Error while creating workdir! - Check permissions")
        return False

    if workdir_exist:
        return True
    return False
