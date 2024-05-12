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
from yt_dlp import YoutubeDL

import urllib.parse as urlparse

import os
import logging
import json
import requests
import pathlib
import tldextract
import hashlib

#own modules
from database_manager import check_table_exist, create_table, insert_value, fetch_value, fetch_value_as_bool

# init logger
logger = logging.getLogger(__name__)

#Define buffer per Thread in Bytes for filehashing - Default 2GB = 2147483648
BUF_SIZE = 2147483648 

def scheme_setup():
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
                if scheme_data["db"]["table_needed"] == True:
                    #Check if table exists - if not create it
                    if not "table_name" in scheme_data["db"]:
                        logging.error("Error while checking for table in schema %s. Key table_name is missing!", scheme)
                        error_occured = True
                        continue
                    table_exists = check_table_exist(scheme_data["db"]["table_name"])

                    if not table_exists:
                        result = create_table(scheme_data["db"]["table_name"], scheme_data["db"]["columns"])
        
                        if not result:
                            logging.error("Error while creating table %s for scheme %s! - Check log", scheme_data["db"]["table_name"], scheme)
                            error_occured = True
                            continue
                        logging.info("Table %s for scheme %s successfully created!", scheme_data["db"]["table_name"], scheme)
                        #If table is created check if there are any default values and add these
                        if "rows" in scheme_data["db"]:
                            logger.info("Found default values for scheme %s - Insert into table", scheme)
                            for option in scheme_data["db"]["rows"]:
                                #Iterate over all default options and insert them to the config table
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
        except json.JSONDecodeError:
            logger.error("Error while initializing scheme %s! - JSON Error: %s", scheme, e)
            return False
        except Exception as e:
            logger.error("Error while initializing scheme %s! - Error: %s", scheme, e)
            return False
    if not error_occured:
        return True
    return False

def check_dependencies():
    #Check if needed tables existing ("config", "items", "subscriptions")
    logger.info("Check if all tables exist..")
    if not check_table_exist("config"):
        #Create config table from scheme
        logger.info("Config table does not exist - Create Table...")
        try:
            with open("./scheme/project.json") as config_scheme: 
                config_data = config_scheme.read()
        except FileNotFoundError:
            logger.error("Error while reading Config Scheme! - Error: %s", e)
            exit()
        except Exception as e:
            logger.error("Error while reading Config Scheme! - Error: %s", e)
            exit()

        try:
            config_data_as_json = json.loads(config_data)
            logging.debug("Config Data loaded - create table..")
        except json.JSONDecodeError as e:
            logger.error("Error while parsing JSON from config Scheme! - Error: %s", e)
            exit()
        except Exception as e:
            logger.error("Error while parsing JSON from config Scheme! - Error: %s", e)
            exit()

        result = create_table(config_data_as_json["db"]["table_name"], config_data_as_json["db"]["columns"])
        if not result:
            logging.error("Error while creating table! - Check log")
            exit()
        
        #Check for default settings
        if "rows" in config_data_as_json["db"]:
            for option in config_data_as_json["db"]["rows"]:
                #Iterate over all default options and insert them to the config table
                inserted = insert_value()
    if not check_table_exist("items"):
        #Create items table from scheme
        #Create config table from scheme
        logger.info("Items table does not exist - Create Table...")
        try:
            with open("./scheme/saved_items.json") as table_scheme: 
                column_data = table_scheme.read()
        except FileNotFoundError as e:
            logger.error("Error while reading items table Scheme! - FILE Error: %s", e)
            exit()
        except Exception as e:
            logger.error("Error while reading items table Scheme! - Error: %s", e)
            exit()

        try:
            column_data_as_json = json.loads(column_data)
            logging.debug("Config Data loaded - create table..")
        except json.JSONDecodeError as e:
            logger.error("Error while parsing JSON from config Scheme! - JSON Error: %s", e)
            exit()
        except Exception as e:
            logger.error("Error while parsing JSON from config Scheme! - Error: %s", e)
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

    return True

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

#This function is used to check if the provided url works (HTTP 200 - OK) if not the video can not be downloaded
def alive_check(url: str):
    #Check if url is reachable
    try:
        requested_url = requests.get(url)
        if requested_url.status_code == 200:
            return True
        else:
            logging.warning(f"The requested url {url} can not be reached. Excepted result is HTTP 200 but got HTTP {requested_url.status_code}")
            return False
    except requests.ConnectionError as e:
        logger.error("Error while checking if url is alive! - Maybe you passed an invalid url? - Error: %s", e)
        return False
    except Exception as e:
        logger.error("Error while checking if url is alive! - Maybe you passed an invalid url? - Error: %s", e)
        return False

#This function is used to validate loaded url schemes. It ensures that a defined set of instructions are availiable
def validate_url_scheme(scheme:json):
    #Check basic keys needed for general function
    needed_keys = ["schema_name", "url_template", "url_scheme", "categories", "storage"]

    all_keys_exist = True
    for required_key in needed_keys:
        if not required_key in scheme:
            all_keys_exist = False

    if not all_keys_exist:
        logging.error("Some required keys are missing in the given scheme file! - Please check your scheme. - Required keys: %s", needed_keys)
        return False

    #Check keys needed for url validation
    needed_url_scheme_keys = ["tld", "sld", "subd"]
    all_keys_exist = True
    for required_key in needed_url_scheme_keys:
        if not required_key in scheme["url_scheme"]:
            all_keys_exist = False

    if not all_keys_exist:
        logging.error("Some required url_scheme keys are missing in the given scheme file! - Please check your scheme.")
        return False
    
    #Check minimum keys for categorizing
    needed_category_scheme_keys = ["available"]
    all_keys_exist = True
    for required_key in needed_category_scheme_keys:
        if not required_key in scheme["categories"]:
            all_keys_exist = False

    if not all_keys_exist:
        logging.error("required category key 'available' is missing in the given scheme file! - Please check your scheme.")
        return False

    if scheme["categories"]["available"] == True:
        if not "needed" in scheme["categories"]:
            logger.error("Required key 'needed' is missing in the categories part of scheme!")
            return False
    return True

def fetch_category_name(url:str, scheme:json):
    logging.debug(f"Fetch category for url {url}")
    category_path = 1
    if "category_path" in scheme["categories"]:
        category_path = scheme["categories"]["category_path"]
    
    #if category path = "" -> First path descriptor is used (e.g. sld.tld/<<username>>) is used
    parsed_url = urlparse.urlparse(url)
    category = parsed_url.path.split('/')[1]
    return category

def fetch_scheme_file_by_file(url):
    script_dir = pathlib.Path(__file__).parent.resolve()

    if not os.path.isdir(os.path.join(script_dir, "scheme")):
        logging.error("The scheme folder does not exist in the script folder! - Please add it!")
        return False
    
    parsed_url = tldextract.extract(url)

    #iterate over all files in directory
    scheme_folder = os.path.join(script_dir, "scheme")

    for scheme_file in os.listdir(scheme_folder):
        #Try to load json file
        scheme = load_json_file(os.path.join(scheme_folder, scheme_file))

        if not scheme:
            logging.error(f"Error while reading scheme file {scheme_file}")
            continue
        
        #Check if the scheme file is a url template (used for websites) or a system template (for local use)
        if "url_template" in scheme and scheme["url_template"] == True:
            if not validate_url_scheme(scheme):
                logging.error(f"Scheme {scheme_file} is not a valid url scheme!")
                continue

            if(validate_scheme(url, scheme)):
                logging.info(F"Found suitable scheme file - Scheme used: {scheme_file}")
                return [os.path.join(scheme_folder, scheme_file), scheme_file]
        else:
            continue

def fetch_scheme_file(url:str):
    script_dir = pathlib.Path(__file__).parent.resolve()

    if not os.path.isdir(os.path.join(script_dir, "scheme")):
        logging.error("The scheme folder does not exist in the script folder! - Please add it!")
        return False
    
    parsed_url = tldextract.extract(url)
    
    expected_scheme_path = os.path.join(script_dir, "scheme")
    expected_scheme_path = os.path.join(expected_scheme_path, str(parsed_url.domain + ".json"))
    if not os.path.isfile(expected_scheme_path):
        logging.info("No suitable file found by filename. Check per file...")
        scheme_check = fetch_scheme_file_by_file(url)

        if not scheme_check:
            logging.error(f"There is no matching scheme file for site {parsed_url.domain}!")
            return False
        else:
            return scheme_check
    logging.info("Scheme file for %s found", parsed_url.domain)
    logging.info("Check if provided url is valid for scheme", parsed_url.domain)
    return [expected_scheme_path, str(parsed_url.domain + ".json")]

def load_json_file(path:str):
    if not os.path.isfile(path):
        logging.error("The provided file does not exist! - Can't open file %s", path)
        return False
    try:
        with open(path, "r") as file:
            json_file = json.loads(file.read())
    except json.JSONDecodeError as e:
        logging.error("Error while reading json file! - JSON Error: %s", e)
        return False
    except Exception as e:
        logging.error("Error while reading json file! - Error: %s", e)
        return False
    return json_file

def validate_scheme(url, scheme, silent=False):
    #Check if the loaded template is a url template
    if not "url_template" in scheme or scheme["url_template"] == False:
        logging.error("The laoded scheme is not marked as a url_template! - Please mark it as url template (Add key 'url_template' with value 'true' to json file)")
        return False

    #validate the url scheme for the most basic keys
    if not validate_url_scheme(scheme):
        logging.error("Provided Scheme is not valid! - Check log")
        return False

    parsedUurl = tldextract.extract(url)
    #Check if the provided url matches the filter of the given scheme
    if not parsedUurl.suffix in scheme["url_scheme"]["tld"]:
        if not silent:
            logging.error(f"Provided url does not match the requirements for the {parsedUurl.domain} scheme! - TLD '{parsedUurl.suffix}' is not supported! - scheme name: {scheme["schema_name"]}")
        return False
    if not parsedUurl.domain in scheme["url_scheme"]["sld"]:
        if not silent:
            logging.error(f"Provided url does not match the requirements for the {parsedUurl.domain} scheme! - SLD '{parsedUurl.domain}' is not supported! - scheme name: {scheme["schema_name"]}")
        return False
    if not parsedUurl.subdomain in scheme["url_scheme"]["subd"]:
        if not silent:
            logging.error(f"Provided url does not match the requirements for the {parsedUurl.domain} scheme! - Subdomain '{parsedUurl.subdomain}' is not supported! - scheme name: {scheme["schema_name"]}")
        return False
    return True

def decide_storage_path(url, scheme):
    #General configuration db table (config) provides a base location where all stuff from this script needs to be saved... 
    #First fetch this...
    data = fetch_value("config", "option_name", "base_location", ["option_value"], True)
    if not data:
        logging.error("Error while fetching data from config db! - Please check log")
        return False
    base_path = data[0]
    base_path = os.path.abspath(base_path)

    if "storage" in scheme:
        if not "base_path" in scheme["storage"]:
            logging.error("Error while fetching scheme base path! - \"base_path\" is not defined as key! - Ignore it and use base path from general config")
        else:
            base_path = os.path.join(base_path, scheme["storage"]["base_path"])
            logging.debug("Base path of scheme is: %s", base_path)
    else:
        logging.warning("Scheme does not provide it's own storage path! - Save data to the base directory")


    if "categories" in scheme and "available" in scheme["categories"] and scheme["categories"]["available"] == True:
        #Decide if categories are used 
        #Check if categories are defined. If not categories can not be used
        categories_defined = False
        if "categories" in scheme["categories"]:
            categories_defined = True
        
        def inner_decide_path(base_path):
            category_name = fetch_category_name(url, scheme)

            #Check if the given category is in the categories list
            if not category_name in scheme["categories"]["categories"]:
                logging.error(f"Category {category_name} is not defined!")
                return False
            
            logging.debug(f"Provided category {category_name} is known... Check for custom storage path")

            if "storage_path" in scheme["categories"]["categories"][category_name]:
                base_path = os.path.join(base_path, scheme["categories"]["categories"][category_name]["storage_path"])
                logging.debug(f"Custom category path is defined. Storage path is {base_path}")
            else:
                logging.info(f"Category {category_name} don't have an individual storage path! - Use path {base_path}")
            return base_path


        if scheme["categories"]["needed"] == True:
            #if url don't have category -> Fail
            logging.debug("Scheme requires category")
            if not categories_defined:
                logging.error("Scheme requires categories but none are defined. Please define categories or set them as optional!")
            if "category_storage" in scheme["storage"] and scheme["storage"]["category_storage"] == False:
                return base_path
            else:
                return inner_decide_path(base_path)
        else:
            if "category_storage" in scheme["storage"] and scheme["storage"]["category_storage"] == False:
                path_ext = inner_decide_path(base_path)
                if not path_ext:
                    return base_path
                else:
                    return path_ext
            else:
                return base_path    
    else:
        #No categories avail 
        return base_path

#This function downloads a file (url) and saves it to a defined path (path)
def download_file(url):
    logging.info("Downloading file from server")
    try:
        ydl_opts = {
    'format': 'best',
    'outtmpl': path + '/%(title)s.%(ext)s',
    'nooverwrites': True,
    'no_warnings': False,
    'ignoreerrors': True,
    'replace-in-metadata': True,
    'restrict-filenames': True
}
        with YoutubeDL(ydl_opts) as ydl:
            value = ydl.download([url])

        if value == 0:
            return True
        else:
            logger.error(f"YDL reported code {value}")
            return False
    except Exception as e:
        logger.error(f"Error while downloading video!- Error: {e}")
        return False

#This function is used to fetch all needed information about the requested file to save it later into db.
def get_file_data(url, path):
    try:
        ydl_opts = {
    'format': 'best',
    'outtmpl': path + '/%(title)s.%(ext)s',
    'nooverwrites': True,
    'no_warnings': False,
    'ignoreerrors': True,
    'replace-in-metadata': True,
    'restrict-filenames': True
}
        with YoutubeDL(ydl_opts) as ydl:
            #We only need the metadata. So we don't need to download the whole file. We will do this later...
            file_data = ydl.extract_info(url, download=False)
    except Exception as e:
        logging.error(f"Error while fetching File information from target server! - Error: {e}")
        return False

    #Check if result have any content
    try:
        if len(file_data) > 0:
            return file_data
        else:
            return False
    except Exception as e:
        logger.error(f"Error result seems to have no content! - \n\n Result: {file_data} \n Error: {e}")
        return False

#Create a hash from a given file
def create_hash_from_file(file):
    #create hash and return the hex value
    hash_obj = hashlib.sha256()
    try:
        with open(file, 'rb') as f: # Open the file to read it's bytes
            fb = f.read(BUF_SIZE) # Read from the file. Take in the amount declared above
            while len(fb) > 0: # While there is still data being read from the file
                hash_obj.update(fb) # Update the hash
                fb = f.read(BUF_SIZE) # Read the next block from the file
        return [file, hash_obj.hexdigest()]
    except Exception as e:
        logging.error(f"Error while creating hash of file! - Error: {e}")
        return False

#This function represents the "manual" video download approach
def direct_download(url:str):
    global path

    logger.info(f"Directly download content from {url}")
    url_alive = alive_check(url)

    if not url_alive:
        logging.error("Can't download video! - Url can not be reached! - Check log above!")
        return False
    
    #Check if url is already in db (this can only detect if a video was already downloaded from the same source). A reuploaded video will be downlaoded again (url is different) - later when the hash is checked it will be dropped again
    url_already_exist = fetch_value("items", "url", url, ["url"], True)

    logger.info("Check if file already exist...")
    if url_already_exist != None:
        logging.info("File already exist! - Skip download")
        return True
    logger.info("File dont exist. Start download...")
    #Any videoplatform could need some special handling in order to use youtube_dl. Things like age verification. This can be done with templates to add headers for example
    logger.info("Check for suitable template to download video")

    #Search for scheme
    scheme_path = fetch_scheme_file(url)
    if not scheme_path:
        logging.error("Error while fetching scheme! - Check log")
        return False
    
    #Load Scheme
    scheme = load_json_file(scheme_path[0])
    if not scheme:
        logging.error("Error while loading scheme! - Check log")
        return False

    #Check if scheme is valid
    if not validate_scheme(url, scheme):
        logging.error("Error while validating scheme! - Check log")
        return False

    #Scheme is valid. Decicde where to save the file (Check for categories). Read general config and do the stuff...
    path = decide_storage_path(url, scheme)
    if not path:
        logging.error("Error while defining storage path! - Check log")
        return False
    
    logger.info(F"File will be saved under: {path}")
    metadata = get_file_data(url, path)
    if not metadata:
        logger.error("Error while fetching metadata from target server! - Please check log")
        return False

    logger.info(F"Fetched all metadata for file")

    #Check if title and extension are availiable for further processing
    if not "title" in metadata or not "ext" in metadata:
        logger.error("Metadata does not contain necessary \"title\" and \"ext\" key!")
        return False

    downloaded = download_file(url)

    if not downloaded:
        logger.error(f"Error while downloading file from {url} - Please check log!")
        return False
    ydl_opts = {
    'format': 'best',
    'outtmpl': path + '/%(title)s.%(ext)s',
    'nooverwrites': True,
    'no_warnings': False,
    'ignoreerrors': True,
    'replace-in-metadata': True,
    'restrict-filenames': True
}
    
    full_file_path = YoutubeDL(ydl_opts).prepare_filename(metadata, outtmpl=path + '/%(title)s.%(ext)s')
    full_file_path = os.path.abspath(full_file_path)
    logger.debug(f"Full File path is: {full_file_path}")

    #Compute hash from file
    hash = create_hash_from_file(full_file_path)
    
    #Check if hash created successfully
    if not hash or len(hash) != 2:
        logger.error("Error while creating hash from file! - Please check log.")
        remove_file = fetch_value_as_bool("config", "option_name", "remove_file_on_post_process_error", ["option_value"], True)
        if remove_file:
            logger.info("Remove file due to config setting.")
            os.remove(full_file_path)
            if os.path.exists(full_file_path):
                logging.error("Error while removing video after post processing error! - Check permissions")
                return False
            else:
                logger.info("File removed")
                return False
        else:
            logger.warning("File will not be removed! - Be cautious, the file is not saved in the db!")
            return False
    
    
    #Check if hash is already in database
    #If hash is not in db -> Video is new - If hash is in db video already exist. Check if the url is the same
    hash_exist = fetch_value("items", "file_hash", hash[1], None, True)

    if not hash_exist:
        #Video hash not exist as saved item add it...
        logger.info("Add Video to DB")
        head, tail = os.path.split(full_file_path)
        logging.debug(f"Scheme Data: {scheme_path}")

        use_tags_ydl = fetch_value_as_bool("config", "option_name", "use_tags_from_ydl", ["option_value"], True)

        #Define base data 
        video_data = {
            "scheme": scheme_path[1],
            "file_name": tail, 
            "file_path": head,
            "file_hash": hash[1],
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
            remove_file = fetch_value_as_bool("config", "option_name", "remove_file_on_post_process_error", ["option_value"], True)
            if remove_file:
                logger.info("Remove file due to config setting.")
                os.remove(full_file_path)
                if os.path.exists(full_file_path):
                    logging.error("Error while removing video after post processing error! - Check permissions")
                    return False
                else:
                    logger.info("File removed")
                    return False
            else:
                logger.warning("File will not be removed! - Be cautious, the file is not saved in the db!")
                return False
    else:
        #hash already exist - check if url is the same. If not add it to url
        exit()


    