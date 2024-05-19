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

import urllib.parse as urlparse

import requests
import tldextract
import validators

from prettytable import PrettyTable
from yt_dlp import YoutubeDL, DownloadError

#own modules
from database_manager import (check_table_exist, create_table,
                insert_value, fetch_value, fetch_value_as_bool, delete_value)

# init logger
logger = logging.getLogger(__name__)

#Define buffer per Thread in Bytes for filehashing - Default 2GB = 2147483648
BUF_SIZE = 2147483648

def scheme_setup():
    """ Check all schemes if tables are needed in the db"""
    script_dir = pathlib.Path(__file__).parent.resolve()

    if not os.path.isdir(os.path.join(script_dir, "scheme")):
        logging.error("The scheme folder does not exist in the script folder! - Please add it!")
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
                        logging.error("""Error while checking for table in schema %s.
                                      Key table_name is missing!""", scheme)
                        error_occured = True
                        continue
                    table_exists = check_table_exist(scheme_data["db"]["table_name"])

                    if not table_exists:
                        result = create_table(scheme_data["db"]["table_name"],
                                              scheme_data["db"]["columns"])

                        if not result:
                            #Line Break for Pylint #C0301
                            logging.error("""Error while creating table %s for scheme %s! -
                                          Check log""", scheme_data["db"]["table_name"], scheme)
                            error_occured = True
                            continue
                        #Line Break for Pylint #C0301
                        logging.info("""Table %s for scheme %s successfully created!""",
                                     scheme_data["db"]["table_name"], scheme)
                        #If table is created check if there are any default values and add these
                        if "rows" in scheme_data["db"]:
                            logger.info("""Found default values for scheme %s -
                                        Insert into table""",
                                        scheme)
                            for option in scheme_data["db"]["rows"]:
                                #Iterate over all default options and insert them to the config
                                #table
                                row_inserted = insert_value(scheme_data["db"]["table_name"], option)
                                if not row_inserted:
                                    logger.error("Error while inserting row: %s!", option)
                                    continue
                                logger.debug("Row inserted")
                        else:
                            logging.debug("There are no default rows in scheme %s", scheme)
                            continue
                else:
                    logging.debug("Scheme %s does not need a table - SKIP", scheme)
                    continue
            else:
                logging.debug("Scheme %s does not contain a db key - SKIP", scheme)
                continue
        except json.JSONDecodeError as e:
            logger.error("Error while initializing scheme %s! - JSON Error: %s", scheme, e)
            return False
    if not error_occured:
        return True
    return False

def show_help():
    """ Show help """
    print("------------------------------ Help ------------------------------")
    #Line Break for Pylint #C0301
    print("""You asked for help... Here it is :) -
          Run YT-Manager with the following commands and you're good to go""")
    help_table = PrettyTable(['Command', 'argument', 'description'])
    help_table.align['Command'] = "l"
    help_table.align['argument'] = "l"
    help_table.align['description'] = "l"
    help_table.add_row(['--Subscriptions--', '', ''])
    help_table.add_row(['add-subscription', '<<url>>', 'Add a new subscription'])
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
    help_table.add_row(['', '', ''])
    help_table.add_row(['--Operation--', '', ''])
    #Line Break for Pylint #C0301
    help_table.add_row(['custom',
                        '<<url>>',
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
    """ #This function is used to check if the provided url works (HTTP 200 - OK)
        #if not the video can not be downloaded """
    #Check if url is reachable
    try:
        requested_url = requests.get(url, timeout=30)
        if requested_url.status_code == 200:
            return True
        #Line Break for Pylint #C0301
        logging.warning("""The requested url %s can not be reached.
                        Excepted result is HTTP 200 but got HTTP %s""",
                        url, requested_url.status_code)
        return False
    except requests.ConnectionError as e:
        #Line Break for Pylint #C0301
        logger.error("""Error while checking if url is alive! -
                     Maybe you passed an invalid url? - Error: %s""", e)
        return False

def validate_url_scheme(scheme:json):
    """ This function is used to validate loaded url schemes.
    It ensures that a defined set of keys are availiable """
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
        logging.error("""Some required keys are missing in the given scheme file! -
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
        logging.error("""Some required url_scheme keys are missing in the given scheme file! -
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
        logging.error("""required category key 'available' is missing in the
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
            logging.error("""Category %s does not meet the minimum requirements!
                           - Key %s is missing!""",
                          last_faulty_category, last_missing_key)
            return False

    #Check for subscription keys
    if("subscription" in scheme and
       "availiable" in scheme["subscription"]
       and scheme["subscription"]["availiable"] is True):
        needed_subscription_scheme_keys = ["available", "subscription_name_locator", "url_blueprint"]
        all_keys_exist = True

        for required_key in needed_subscription_scheme_keys:
            if not required_key in scheme["subscription"]:
                last_missing_key = required_key
                all_keys_exist = False

        if not all_keys_exist:
            logging.error("""Category subscription does not meet the minimum requirements!
                           - Key %s is missing!""",
                          last_missing_key)
            return False
    return True

def fetch_category_name(url:str, scheme:json):
    """ This function is used to extract specific parts from an url describing a category """
    logging.debug("Fetch category for url %s", url)
    if "category_path" in scheme["categories"]:
        category_path = scheme["categories"]["category_path"]
    else:
        #This should not be used!
        category_path = 1
    #if category path = "" -> First path descriptor is used (e.g. sld.tld/<<username>>) is used
    parsed_url = urlparse.urlparse(url)
    category = parsed_url.path.split('/')[category_path]
    return category

def fetch_subscription_name(url:str, scheme:json):
    """ This function is used to extract specific parts from an url describing the subscription object """
    logging.debug("Fetch subscription name for url %s", url)
    if "subscription" in scheme:
        subscription_path = scheme["subscription"]["subscription_name_locator"]
    else:
        #This should not be used!
        subscription_path = 2
    #if category path = "" -> First path descriptor is used (e.g. sld.tld/<<username>>) is used
    parsed_url = urlparse.urlparse(url)
    subscription_name = parsed_url.path.split('/')[subscription_path]
    return subscription_name

def fetch_scheme_file_by_file(url):
    """ internal function used to iterate over all schemes in a dictionary and find a
    matching scheme by reading the scheme files"""
    return_val = {"status": False, "scheme_path": None, "scheme_file": None}
    script_dir = pathlib.Path(__file__).parent.resolve()

    if not os.path.isdir(os.path.join(script_dir, "scheme")):
        logging.error("The scheme folder does not exist in the script folder! - Please add it!")
        return return_val

    #iterate over all files in directory
    scheme_folder = os.path.join(script_dir, "scheme")

    for scheme_file in os.listdir(scheme_folder):
        #Try to load json file
        scheme = load_json_file(os.path.join(scheme_folder, scheme_file))

        if not scheme:
            logging.error("Error while reading scheme file %s", scheme_file)
            continue

        #Check if the scheme file is a url template (used for websites) or
        #a system template (for local use)
        if "url_template" in scheme and scheme["url_template"] is True:
            if not validate_url_scheme(scheme):
                logging.error("Scheme %s is not a valid url scheme!", scheme_file)
                continue

            if validate_scheme(url, scheme):
                logging.info("Found suitable scheme file - Scheme used: %s", scheme_file)
                return_val["scheme_file"] = scheme_file
                return_val["scheme_path"] = os.path.join(scheme_folder, scheme_file)
                return_val["status"] = True
                return return_val
        else:
            continue
    return return_val

def fetch_scheme_file(url:str):
    """ FInd a matching scheme file for a given url by testing the filename. If not working
    iterate over all files and try to find a scheme matching the sld and tld"""
    return_val = {"status": False, "scheme_path": None, "scheme_file": None}
    script_dir = pathlib.Path(__file__).parent.resolve()

    if not os.path.isdir(os.path.join(script_dir, "scheme")):
        logging.error("The scheme folder does not exist in the script folder! - Please add it!")
        return return_val

    parsed_url = tldextract.extract(url)

    expected_scheme_path = os.path.join(script_dir, "scheme")
    expected_scheme_path = os.path.join(expected_scheme_path, str(parsed_url.domain + ".json"))
    if not os.path.isfile(expected_scheme_path):
        logging.info("No suitable file found by filename. Check per file...")
        scheme_check = fetch_scheme_file_by_file(url)

        if not scheme_check["status"]:
            logging.error("There is no matching scheme file for site %s!", parsed_url.domain)
            return return_val

        return scheme_check
    logging.debug("Scheme file for %s found", parsed_url.domain)
    logging.debug("Check if provided url %s is valid for scheme", parsed_url.domain)
    return_val["scheme_path"] = expected_scheme_path
    return_val["scheme_file"] = str(parsed_url.domain + ".json")
    return_val["status"] = True
    return return_val

def load_json_file(path:str):
    """ Read a file and return it as json dict """
    if not os.path.isfile(path):
        logging.error("The provided file does not exist! - Can't open file %s", path)
        return False
    try:
        with open(path, "r", encoding="UTF-8") as file:
            json_file = json.loads(file.read())
    except json.JSONDecodeError as e:
        logging.error("Error while reading json file! - JSON Error: %s", e)
        return False
    except FileNotFoundError as e:
        logging.error("Error while reading json file! - Error: %s", e)
        return False
    return json_file

def validate_scheme(url, scheme, silent=False):
    """ Check if the given scheme contains all information needed to download and save a file"""
    #Check if the loaded template is a url template
    if not "url_template" in scheme or scheme["url_template"] is False:
        #Line Break for Pylint #C0301
        logging.error("""The laoded scheme is not marked as a url_template! -
                      Please mark it as url template (Add key 'url_template' with value 'true'
                      to json file)""")
        return False

    #validate the url scheme for the most basic keys
    if not validate_url_scheme(scheme):
        logging.error("Provided Scheme is not valid! - Check log")
        return False

    parsed_url = tldextract.extract(url)
    #Check if the provided url matches the filter of the given scheme
    if not parsed_url.suffix in scheme["url_scheme"]["tld"]:
        if not silent:
            #Line Break for Pylint #C0301
            logging.error("""Provided url does not match the requirements for the %s scheme! -
                          TLD '%s' is not supported! - scheme name: %s""",
                          parsed_url.domain, parsed_url.suffix, scheme["schema_name"])
        return False
    if not parsed_url.domain in scheme["url_scheme"]["sld"]:
        if not silent:
            #Line Break for Pylint #C0301
            logging.error("""Provided url does not match the requirements for the %s scheme! -
                          SLD '%s' is not supported! - scheme name: %s""",
                          parsed_url.domain, parsed_url.domain, scheme["schema_name"])
        return False
    if not parsed_url.subdomain in scheme["url_scheme"]["subd"]:
        if not silent:
            #Line Break for Pylint #C0301
            logging.error("""Provided url does not match the requirements for the %s scheme! -
                          Subdomain '%s' is not supported! - scheme name: %s""",
                          parsed_url.domain, parsed_url.subdomain, scheme["schema_name"])
        return False
    return True

def decide_storage_path(url, scheme):
    """General configuration db table (config) provides a base location where all stuff
    from this script needs to be saved..."""
    #First fetch the base location...
    data = fetch_value("config", {"option_name": "base_location"}, ["option_value"], True)
    if not data:
        logging.error("Error while fetching data from config db! - Please check log")
        return False
    base_path = data[0]
    base_path = os.path.abspath(base_path)

    if "storage" in scheme:
        if not "base_path" in scheme["storage"]:
            #Line Break for Pylint #C0301
            logging.error("""Error while fetching scheme base path! - \"base_path\" is
                          not defined as key! - Ignore it and use base path from general config""")
        else:
            base_path = os.path.join(base_path, scheme["storage"]["base_path"])
            logging.debug("Base path of scheme is: %s", base_path)
    else:
        #Line Break for Pylint #C0301
        logging.warning("""Scheme does not provide it's own storage path! -
                        Save data to the base directory""")

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
                logging.error("Category %s is not defined!", category_name)
                return False
            #Line Break for Pylint #C0301
            logging.debug("""Provided category %s is known...
                          Check for custom storage path""", category_name)

            if "storage_path" in scheme["categories"]["categories"][category_name]:
                #Line Break for Pylint #C0301
                base_path = os.path.join(base_path,
                            scheme["categories"]["categories"][category_name]["storage_path"])
                logging.debug("Custom category path is defined. Storage path is %s", base_path)
            else:
                #Line Break for Pylint #C0301
                logging.info("""Category %s don't have an individual storage path! -
                             Use path %s""", category_name, base_path)
            return base_path

        if scheme["categories"]["needed"] is True:
            #if url don't have category -> Fail
            logging.debug("Scheme requires category")
            if not categories_defined:
                #Line Break for Pylint #C0301
                logging.error("""Scheme requires categories but none are defined.
                              Please define categories or set them as optional!""")
            #Line Break for Pylint #C0301
            if ("category_storage" in scheme["storage"] and
                scheme["storage"]["category_storage"] is False):
                return base_path
            return inner_decide_path(base_path)
        #Line Break for Pylint #C0301
        if("category_storage" in scheme["storage"] and
           scheme["storage"]["category_storage"] is False):
            path_ext = inner_decide_path(base_path)
            if not path_ext:
                return base_path
            return path_ext
    return base_path

def get_metadata(url, ydl_opts):
    """ This function is used to fetch all needed information about the requested file
    to save it later into db."""
    try:
        with YoutubeDL(ydl_opts) as ydl:
            #We only need the metadata. So we don't need to download the whole file.
            #We will do this later...
            file_data = ydl.sanitize_info(ydl.extract_info(url, download=False))
    except DownloadError as e:
        logging.error("Error while fetching File information from target server! - Error: %s", e)
        return False

    #Check if result have any content
    try:
        if len(file_data) > 0:
            return file_data
        return False
    except ValueError as e:
        #Line Break for Pylint #C0301
        logger.error("Error result seems to have no content! - \n\n Result: %s \n Error: %s",
                     file_data, e)
        return False
    except TypeError as e:
        logger.error("Error while fetching metadata! - Type Error: %s", e)
        return False

def get_ydl_opts(path, addons:json=None):
    """ This function returns the standard settings for YT DLP"""
    opts = {
                'format': 'best',
                'outtmpl': path + '/%(title)s.%(ext)s',
                'nooverwrites': True,
                'no_warnings': False,
                'ignoreerrors': True,
                'replace-in-metadata': True,
                'restrict-filenames': True
            }
    if addons is None:
        #Return default set
        return opts
    for key in addons:
        opts[key] = addons[key]
    return opts

#This function downloads a file (url) and saves it to a defined path (path)
def download_file(url, path):
    """This function downloads the file specified in url and also provides the prepared
        file path from ydl"""
    logging.info("Downloading file from server")
    return_val = {"status": False, "full_file_path": None, "metadata": None}

    try:
        ydl_opts = get_ydl_opts(path)

        metadata = get_metadata(url, ydl_opts)
        if not metadata or not "title" in metadata or not "ext" in metadata:
            #Line Break for Pylint #C0301
            logger.error("""Error while fetching metadata from target server! -
                         Metadata could not be fetched or key \"title\" / \"ext\" is missing""")
            return return_val

        with YoutubeDL(ydl_opts) as ydl:
            value = ydl.download([url])

        if value == 0:
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

def create_hash_from_file(file):
    """ Create a hash from a given file and returns a JSON Dict"""
    return_val = {"status": False, "file": None, "hash": None}

    if file is None:
        logging.error("File is NONE!")
        return False
    logging.debug("Create hash from file %s", file)
    #create hash and return the hex value
    hash_obj = hashlib.sha256()
    try:
        with open(file, 'rb') as f: # Open the file to read it's bytes
            fb = f.read(BUF_SIZE) # Read from the file. Take in the amount declared above
            while len(fb) > 0: # While there is still data being read from the file
                hash_obj.update(fb) # Update the hash
                fb = f.read(BUF_SIZE) # Read the next block from the file
        return_val["hash"] = hash_obj.hexdigest()
        return_val["status"] = True
        return return_val
    except FileNotFoundError as e:
        logging.error("Error while creating hash of file! - Error: %s", e)
        return return_val

def load_scheme(url: str):
    """ This function is used to load the correct scheme based on an url """
    return_scheme = {"status": False, "scheme": None, "scheme_path": None}
    #Search for scheme
    scheme_data = fetch_scheme_file(url)
    if not scheme_data["status"]:
        logging.error("Error while fetching scheme! - Check log")
        return return_scheme

    scheme_path = scheme_data["scheme_path"]

    #Load Scheme
    scheme = load_json_file(scheme_path)
    if not scheme:
        logging.error("Error while loading scheme! - Check log")
        return return_scheme

    #Check if scheme is valid
    if not validate_scheme(url, scheme):
        logging.error("Error while validating scheme! - Check log")
        return return_scheme

    return_scheme["status"] = True
    return_scheme["scheme"] = scheme
    return_scheme["scheme_path"] = scheme_path
    return return_scheme

def prepare_scheme_dst_data(url):
    """This function checks if the given url is alive and can be used to download a file
        using the defined templates

        Possible return Values:
        0 => Failed
        1 => Success
        2 => File already exists
    """

    return_val = {"status": 0, "scheme": None, "scheme_path": None, "dst_path": None}
    #Check if the url is reachable
    url_alive = alive_check(url)
    #Check if the given url already exists in the items db
    url_already_exist = fetch_value("items", {"url": url}, ["url"], True)
    #Try to load a scheme matching the current url
    scheme = load_scheme(url)

    if not url_alive or url_already_exist is not None or not scheme["status"]:
        if not url_alive:
            logging.error("Can't download video! - Url can not be reached! - Check log above!")
        if url_already_exist is not None:
            logging.error("Video already exist in db!")
            return_val["status"] = 2
        if not scheme["status"]:
            logging.error("Error while loading scheme data! - Check log")
        return return_val

    #Check if laoded scheme is valid
    scheme_validated = validate_url_scheme(scheme["scheme"])

    if not scheme_validated:
        logging.error("Error while validating scheme!")
        return return_val

    return_val["scheme_path"] = scheme["scheme_path"]
    return_val["scheme"] = scheme["scheme"]

    #Scheme is valid. Decicde where to save the file (Check for categories). Read general config
    #and do the stuff...
    dst_path = decide_storage_path(url, scheme["scheme"])
    if not dst_path:
        logging.error("Error while defining storage path! - Check log")
        return False
    return_val["status"] = 1
    return_val["dst_path"] = dst_path

    return return_val

def save_file_to_db(scheme_data, full_file_path, file_hash, url, metadata):
    """ This function is used to save a file into the items table. It is basically
    an SQL Insert wrapper"""
    #Video hash not exist as saved item add it...
    logger.info("Add Video to DB")
    scheme_path = scheme_data["scheme_path"]

    head, tail = os.path.split(full_file_path)
    logging.debug("Scheme Data: %s", scheme_path)
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
    if use_tags_ydl:
        logging.info("Also insert tags from ydl metadata")
        if "tags" in metadata:
            logging.debug("Found key 'tags'")
            if len(metadata["tags"]) > 0:
                logging.debug("Tags found...")
                video_data["tags"] = metadata["tags"]
            else:
                logging.debug("Tags array is empty!")
        else:
            logger.debug("No tags key found in metadata")
    else:
        logging.info("Tags are not inserted from ydl")
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
                logging.error("""Error while removing video after post processing error! -
                              Check permissions""")
            return False
        logger.warning("File will not be removed! - Be cautious, the file is not saved in the db!")
        return False
    logger.info("Video successfully saved. - Finished")
    return True

def error_post_processing(full_file_path):
    """ This function is used to remove downloaded files if anything fails during post processing"""
    #Line Break for Pylint #C0301
    remove_file = fetch_value_as_bool("config", {"option_name":
                                                 "remove_file_on_post_process_error"},
                                        ["option_value"], True)
    if remove_file:
        logger.info("Remove file due to config setting.")
        os.remove(full_file_path)
        if os.path.exists(full_file_path):
            #Line Break for Pylint #C0301
            logging.error("""Error while removing video after post processing error! -
                          Check permissions""")
            return False
        logger.info("File removed")
        return False
    logger.warning("File will not be removed! - Be cautious, the file is not saved in the db!")
    return False

def direct_download(url:str):
    """ This function represents the "manual" video download approach """
    #Line Break for Pylint #C0301
    logger.info("""Directly download content from %s -
                Check prerequisites and prepare download data""", url)

    prepared_data = prepare_scheme_dst_data(url)


    if prepared_data["status"] != 1:
        logging.error("Error while preparing download! - Check log.")
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
            logging.info("File successfully downlaoded.")
            return True
        logging.error("Error while register Video to db!")
        error_post_processing(full_file_path)
        return False
    #TODO
    #hash already exist - check if url is the same. If not add it to url
    return False

def create_subscription_url(url:str, scheme:json):
    """ This function creates the subscription url which will used to subscribe to a channel or anything else"""
    logging.debug("Create subscription url for url %s", url)
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
            logging.info("Scheme %s does not support subscriptions!", scheme["schema_name"])
            return_val["subscribable"] = False
            return return_val
        logging.error("Scheme does not contain a subscription key or url blueprint!")
        return return_val

    #Check which parts are needed
    url_blueprint:str = scheme["subscription"]["url_blueprint"]

    blueprint_data = re.findall(r'{\w*}',url_blueprint)

    tld_url_parts = tldextract.extract(url)
    parsed_url_parts = urlparse.urlparse(url)

    if parsed_url_parts.scheme is not None:
        logging.debug("Key scheme is in parsed urls")
        if "{scheme}" in blueprint_data:
            logging.debug("Key scheme is in the blueprint subscription link. Add it...")
            return_val["scheme"] = parsed_url_parts.scheme

    if tld_url_parts.subdomain is not None:
        logging.debug("Key subdomain is in parsed urls")
        if "{subd}" in blueprint_data:
            logging.debug("Key subd is in the blueprint subscription link. Add it...")
            return_val["subd"] = tld_url_parts.subdomain

    if tld_url_parts.domain is not None:
        logging.debug("Key domain is in parsed urls")
        if "{sld}" in blueprint_data:
            logging.debug("Key sld is in the blueprint subscription link. Add it...")
            return_val["sld"] = tld_url_parts.domain

    if tld_url_parts.suffix is not None:
        logging.debug("Key suffix is in parsed urls")
        if "{tld}" in blueprint_data:
            logging.debug("Key tld is in the blueprint subscription link. Add it...")
            return_val["tld"] = tld_url_parts.suffix

    #Check if the scheme supports categories
    if("categories" in scheme and
       "available" in scheme["categories"] and
       scheme["categories"]["available"] is True):
        logging.debug("Categories are available. Fetch data...")
        #extract the category from the url
        category = fetch_category_name(url, scheme)

        #Check if a category was fetched
        if category is not None:
            logging.debug("Category found")
            if "{category}" in blueprint_data:
                logging.debug("Key category is in the blueprint subscription link. Add it...")
                return_val["category_avail"] = True
                return_val["category"] = category

    subscription_name = fetch_subscription_name(url, scheme)

    if not subscription_name:
        logging.error("Can't fetch subscription name! - Maybe you cannot subscribe to the url?")
        return False
    if "{subscription_name}" in blueprint_data:
        logging.debug("Key subscription_name is in the blueprint subscription link. Add it...")
        return_val["subscription_name"] = subscription_name

    if "{subscription_url}" in blueprint_data:
        logging.debug("Key subscription_url is in the blueprint subscription link. Add it...")
        if(return_val["category_avail"] and
           category in scheme["categories"]["categories"] and
           "subscription_url" in scheme["categories"]["categories"][category]):

            if(scheme["categories"]["categories"][category]["subscription_url"] is not False and
               scheme["categories"]["categories"][category]["subscription_url"] is not None and
               scheme["categories"]["categories"][category]["subscription_url"] != ""):
                logging.debug("Subscription url added...")
                return_val["subscription_url"] = scheme["categories"]["categories"][category]["subscription_url"]

    logging.debug("All url data prepared. Create Link")

    supported_keys = ["scheme", "subd", "sld", "tld", "category", "subscription_name", "subscription_url"]

    for part in supported_keys:
        if return_val[part] is not None and return_val[part] is not False:
            url_blueprint = url_blueprint.replace(f"{{{part}}}", return_val[part])
        else:
            url_blueprint = url_blueprint.replace(f"/{{{part}}}", "")

    if url_blueprint.find("{") != -1 or url_blueprint.find("}") != -1:
        logging.error("Error while creating correct subscription url! - Not all placeholders were replaced! - Url: %s", url_blueprint)
        return return_val

    logging.debug("Url successfully created")
    return_val["formed_subscription_url"] = url_blueprint
    return_val["status"] = True
    return return_val

def add_subscription(url:str):
    """ Add a subscription to the database """
    #Check if the url is supported by any scheme
    data = prepare_scheme_dst_data(url)

    if data["status"] is False or data["scheme"] is None:
        logger.error("The provided url is not supported!")
        return False

    logger.debug("Used scheme for url is: %s", data["scheme"])

    subscription_data = create_subscription_url(url, data["scheme"])

    if not subscription_data["status"]:
        if subscription_data["subscribable"] is False:
            logging.info("Can't add subscription - Scheme %s does not support subscriptions", data["scheme"]["schema_name"])
            return False
        logging.error("Error while fetching subscription data!")
        return False

    #Check if subscription already exist
    subscription_exist = fetch_value("subscriptions",
                                     {"subscription_path": subscription_data["formed_subscription_url"]},
                                       ["id"], True)

    if subscription_exist is not None:
        logging.info("%s subscription for %s already exists!", data["scheme"]["schema_name"], subscription_data["subscription_name"])
        return True

    metadata = get_metadata(subscription_data["formed_subscription_url"],
                            get_ydl_opts(data["dst_path"], {'quiet': False, 'extract_flat': 'in_playlist'}))

    if not metadata:
        logging.error("Error while fetching metadata for subscription! - Please check the log.")
        return False

    if("playlist_count" not in metadata or
       "entries" not in metadata or
       "_type" not in metadata):
        logging.error("Fetched metadata does not contain all information needed! - Data: %s", metadata)
        return False

    subscription_entry = {
        "scheme": data["scheme"]["schema_name"],
        "passed_subscription_path": url,
        "subscription_name": subscription_data["subscription_name"],
        "subscription_path": subscription_data["formed_subscription_url"],
        "subscription_content_count": metadata["playlist_count"],
        "subscription_data": metadata
    }

    added_subscr = insert_value("subscriptions", subscription_entry)

    if not added_subscr:
        logging.error("Error while inserting subscription for %s into db! - Check log", subscription_data["subscription_name"])
        return False
    logging.info("Subscription for %s successfully created.", subscription_data["subscription_name"])
    return True

def del_subscription(identifier:str):
    """ This function removes a passed subscription from the database (This function does NOT remove the files!)"""
    if validators.url(identifier):
        #Remove with url as ident

        subscription_exist_1 = fetch_value("subscriptions", {"subscription_path": identifier}, ["id"], True)
        subscription_exist_2 = fetch_value("subscriptions", {"passed_subscription_path": identifier}, ["id"], True)

        if subscription_exist_1 is None and subscription_exist_2 is None:
            logger.info("Subscription does not exist!")
            return True

        subscription_deleted = delete_value("subscriptions", [
            {"subscription_path": identifier},
            {"passed_subscription_path": identifier}])
    else:
        subscription_exist = fetch_value("subscriptions", {"subscription_name": identifier}, ["id"], True)

        if subscription_exist is None:
            logger.info("Subscription does not exist!")
            return True

        subscription_deleted = delete_value("subscriptions", {"subscription_name": identifier})

    if not subscription_deleted:
        logging.error("Error while removing subscription!")
        return False
    logging.info("Subscription removed.")
    return True

def list_subscriptions(scheme_filter:list=None):
    """This function list all subscriptions with prettyTables"""
    if scheme_filter is None:
        logging.debug("List all subscriptions")
        #List all subscriptions
        subscriptions = fetch_value("subscriptions",
                                    None,
                                    [
                                        "scheme",
                                        "subscription_name",
                                        "subscription_path",
                                        "subscription_last_checked",
                                        "downloaded_content_count",
                                        "subscription_content_count"
                                    ], extra_sql="ORDER BY scheme")

    else:
        logging.debug("List subscriptions with Filter")
        conditions = []
        for condition in scheme_filter:
            conditions.append({"scheme": condition})

        subscriptions = fetch_value("subscriptions",
                                    conditions,
                                    [
                                        "scheme",
                                        "subscription_name",
                                        "subscription_path",
                                        "subscription_last_checked",
                                        "downloaded_content_count",
                                        "subscription_content_count"
                                    ], extra_sql="ORDER BY scheme")
    
    print(subscriptions)