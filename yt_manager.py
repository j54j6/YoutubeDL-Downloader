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
import argparse

# Own Modules
from project_functions import (show_help, direct_download, direct_download_batch,
                               scheme_setup, add_subscription, add_subscription_batch,
                               del_subscription, list_subscriptions, export_subscriptions,
                               import_subscriptions, start, validate, export_items, import_items,
                               show_duplicate_files, check_for_workdir, 
                               show_profiles, enable_profile, disable_profile)
from database_manager import check_db
from config_handler import check_for_config

#Version
CURRENT_VERSION = 20240921


# Init. Logging
logging.getLogger(__name__).addHandler(logging.StreamHandler(sys.stdout))
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

logger.info("Running startup checks...")

#Check for config File
CONFIG_LOADED = check_for_config()
if not CONFIG_LOADED:
    logger.error("Error while loading config! - Check log...")
    sys.exit()

#Check for database and init
DATABASE_CHECK_SUCCESSFULL = check_db()
if not DATABASE_CHECK_SUCCESSFULL:
    logging.error("Error while initializing DB! - Please check log...")
    sys.exit()

#Check database content
DEPENDENCIES = scheme_setup()

if not DEPENDENCIES:
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

#Check for workdir
WORKDIR_EXIST = check_for_workdir()
if not WORKDIR_EXIST:
    logger.info("Workdir can't be created!")
    sys.exit(-1)

def convert_to_list(val) -> list[str]:
    """ This function is used to convert the user input to a list of strings"""
    if isinstance(val, list):
        return val
    elif isinstance(val, str):
        return val.split(",")
    raise argparse.ArgumentTypeError(f"Invalid format: {val} . Expected a list or a comma-separated string.")



#CLI

def main():
    """ The main function provides the CLI"""
    parser = argparse.ArgumentParser(description="YT-Download Manager by j54j6")

    # Subcommands
    subparsers = parser.add_subparsers(dest="command")

    subparsers.add_parser("help", help="Show help information")

    # Add subscription command
    add_sub = subparsers.add_parser("add-subscription", help="Add a new subscription")
    add_sub.add_argument("url", help="URL of the subscription")
    add_sub.add_argument("--batch", help="Add subscriptions in batch mode", nargs="?", const=True)
    add_sub.add_argument(
        "--output-format",
        help="Specify the output format",
        nargs="?",  # Optional argument
        const=None,  # Default to 'NONE' if --output-profile is provided without a value
        type=convert_to_list
    )

    # Delete subscription command
    del_sub = subparsers.add_parser("del-subscription", help="Delete a subscription")
    del_sub.add_argument("url", help="URL of the subscription")

    # List subscriptions command
    list_sub = subparsers.add_parser("list-subscriptions", help="List all subscriptions")
    list_sub.add_argument("filter", help="Filter for subscription list", nargs="?")

    subparsers.add_parser("export-subscriptions", help="Export all subscriptions")

    import_sub = subparsers.add_parser("import-subscriptions", help="Import subscriptions")
    import_sub.add_argument("path", help="Path to the file")
    import_sub.add_argument("--overwrite", help="Overwrite existing subscriptions", nargs="?", const=True)

    subparsers.add_parser("export-items", help="Export all items")

    import_items_parser = subparsers.add_parser("import-items", help="Import items")
    import_items_parser.add_argument("path", help="Path to the file")

    subparsers.add_parser("backup", help="Create a backup of subscriptions and items")

    custom = subparsers.add_parser("custom", help="Download a custom item")
    custom.add_argument("url", help="URL of the item")
    custom.add_argument("--batch", help="Download in batch mode", nargs="?", const=True)
    custom.add_argument(
    "--output-format",
    help="Specify the output format",
    nargs="?",  # Optional argument
    const=None,  # Default to 'NONE' if --output-profile is provided without a value
    type=convert_to_list
    )

    subparsers.add_parser("start", help="Run the script to check for new content and download it")

    subparsers.add_parser("validate", help="Rehash all files and compare them to stored files")

    subparsers.add_parser("show-duplicates", help="Show duplicate files")

    subparsers.add_parser("show-format-profiles", help="Show all currently defined profiles to define the output format")
    
    en_format_profile = subparsers.add_parser("enable-format-profile", help="Enable a specific format profile (globally)")
    en_format_profile.add_argument("profile_name", help="Profilename of the intended profile")
    en_format_profile.add_argument("--only_active", help="If this is true, all other profiles will be disabled", const=False, nargs="?")

    dis_format_profile = subparsers.add_parser("disable-format-profile", help="Disable a specific format profile (globally)")
    dis_format_profile.add_argument("profile_name", help="Profilename of the intended profile")
    # Parse arguments
    args = parser.parse_args()

    # Command mapping to functions
    commands = {
        "help": show_help,
        "add-subscription": lambda: (
            add_subscription_batch(file=args.url, output_format=args.output_format) if args.batch else add_subscription(url=args.url, output_format=args.output_format)
        ) if args.output_format is not None else (
            add_subscription_batch(args.url) if args.batch else add_subscription(args.url)
        ),
        "del-subscription": lambda: del_subscription(args.url),
        "list-subscriptions": lambda: list_subscriptions(list(args.filter.split(",")) if args.filter else None),
        "export-subscriptions": export_subscriptions,
        "import-subscriptions": lambda: import_subscriptions(args.path, args.overwrite),
        "export-items": export_items,
        "import-items": lambda: import_items(args.path),
        "backup": lambda: export_subscriptions() and export_items(),
        "custom":  lambda: (
                                direct_download_batch(args.url, args.output_format) if args.batch 
                                else direct_download(args.url, None, args.output_format)
                            ) if args.output_format is not None else (
                                direct_download_batch(args.url) if args.batch 
                                else direct_download(args.url)
                            ),
        "start": start,
        "validate": validate,
        "show-duplicates": show_duplicate_files,
        "show-format-profiles": show_profiles,
        "enable-format-profile": lambda: enable_profile(args.profile_name, args.only_active),
        "disable-format-profile": lambda: disable_profile(args.profile_name),
    }

    # Execute the command
    command_func = commands.get(args.command)
    if command_func:
        NO_ERROR = command_func()
        if NO_ERROR:
            sys.exit(0)
        else:
            logging.error("Command execution failed.")
            sys.exit(1)
    else:
        logging.error("Invalid command. Showing help.")
        show_help()
        sys.exit(1)

if __name__ == "__main__":
    main()
