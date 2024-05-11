#!/usr/bin/env python

#
# Project by j54j6
# This file provides a simple abstraction layer to handle ini configuration files 
#

# Python Modules
import logging
import pathlib
from pathlib import Path
import os
from configparser import ConfigParser

# init logger
logger = logging.getLogger(__name__)

# init configParser
config:ConfigParser = ConfigParser()
loaded:bool = False

#default config_name
default_config_name:str = "config.ini"



def create_default_config(path=Path.joinpath(pathlib.Path(__file__).parent.resolve(), "config.ini")):
    #Add Default configuration for values needed for the whole project
    config.add_section('main')

    config.add_section('db')
    config.set('db', 'db_driver', 'sqlite')
    config.set('db', 'db_path', './')
    config.set('db', 'db_name', 'database.db')
    config.set('db', 'db_host', 'localhost')
    config.set('db', 'db_user', 'username')
    config.set('db', 'db_pass', 'password')


    try:
        with open(path, 'w') as f:
            config.write(f)
        return True
    except Exception as e:
        logger.error(f"Error while creating default config! - Error: {e}")
        return False

def check_for_config(path=False):
    #As fallback (per Default) the config is located in the same folder as the main.py. Set the default search path to the current file dir.
    check_path:Path = pathlib.Path(__file__).parent.resolve()
    check_path = Path.joinpath(check_path, default_config_name)

    #Check if a path is provided (Path != False). If so change the check_path to the given path and not to the current dir
    if(path != False):
        try:
            if path.lower().endwith(".ini"):
                check_path = Path(path)
            else:
                logger.error("The given file %s does not end with \".ini\". Only INI Files are supported")
                exit()
        except Exception as e:
            logger.error(f"Error while converting given configuration path to Path Object. Error: {e}")
            exit()
        
    logger.info("Check for config file. Provided path: %s", path)

    #Check if check_path exists on the filesystem
    if not os.path.exists(check_path):
        logger.error("Config file does not exist! - Create default config...")
        config_created:bool = create_default_config()

        if(not config_created):
            exit()
        
    #Config File exists - check if it is valid json (load file)
    try:
        config.read(check_path)
    except Exception as e:
        logger.error("Error while reading configuration file! - Error: %s", e)
        exit()
    return True

    