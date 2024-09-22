
[![GPLv3 License](https://img.shields.io/badge/License-GPL%20v2-green.svg)](https://opensource.org/licenses/)

[![CodeFactor](https://www.codefactor.io/repository/github/j54j6/youtubedl-downloader/badge)](https://www.codefactor.io/repository/github/j54j6/youtubedl-dowloader)


# Show some love <3
[!["Buy Me A Coffee"](https://www.buymeacoffee.com/assets/img/custom_images/orange_img.png)](https://www.buymeacoffee.com/j54j6)

# YoutubeDL-Dowloader
 This little program is supposed to help you to make a private copy of videos from sites supporting youtube-dl. Currently many sites like youtube, NYT, CNBC but also adult sites like Pornhub 91porn and much more support youtube-dl. Feel Free to use it but be aware about legal discussions - This Repo is jsut a project to show that this is in general working.^^
 I am not responsible for any damages or anything else. You can use this program on your OWN RISK


 # Architecure
 In General this program is built out of different modules. Each module handles some parts of the program needed to work as a whole.
 To ensure compatibility for different sites I utilize multiple files called "schemes". Every supporterd site has its own scheme. Please feel free to built your own and send it to me :) - We can help each other with these. I am not capable of providing a scheme for each supported site ;)
 I provide some of them when requested if I have spare time.

 # Schemes
 Schemes are heavily used inside this project. They utilize different functions and can be used to dynamically change the behaviour of the program without any code knowledge.
 Schemas are used for 2 types
    1. Configuration -> It is possible to create database blueprints with schemas (like the project.json file used to create the main configuration and all default values).
    2. Websites -> To ensure future compatibility all website specific stuff is located inside a scheme file per website. If anything changes on the website it should be possible to alter the file and make it work again (maybe due to a new header or something else...)

For Reference please look in the project.json section

# Currently Working
- Downloading videos => Subscriptions, direct and Batch
- Register Videos in DB
- Register (Single and Batch) / Deleting and List Subscriptions
- Create and import Backups
- Validate your FS
- Show duplicates
- Format profiles (globally and per custom download / subscription)

# Currently supported Sites
- Pinterest
- Reddit
- Pornhub
- YouTube

# TODO
- better documentation / Code Quality fixes
- FS Validator (rehash all files again and check if any file differs from the original state)

# Postponed todos
- Implementing support for both SQLite and MySQL
- Removing Problems with SQL Injection -> Currently I don't know how to dynamically pass non literals (like tablenames or selectors) since they are not supported for binding in python.
# Documentation


## Subscriptions
Subscriptions are used to automatically download new content if needed (You need to create a periodic job to do this!)

### List Subscriptions

```
        yt_manager.py list-Subscriptions <Filter:list>
```
To list subscriptions the command above is used. An example Output is listed below.

Options:
    - Filter (optional) -> A filter can be used to only return a specific subscriptiontype based on the scheme (for example "youtube".) The filter need to be passed as comma separated list. For example:

```
        yt_manager.py list-Subscriptions youtube,reddit
```
With the provided command only subscriptions created with the youtube or reddit scheme are shown.  If no filter is passed all subscriptions will be shown like below. If the scheme changes a divider is inserted
```
+----+----------------+---------+---------------+-------------------+---------------------+------------------------------------------------------+---------------
| ID | Name           | Scheme  | Avail. Videos | Downloaded Videos |     Last checked    | url                                                  |output-format |
+----+----------------+---------+---------------+-------------------+---------------------+------------------------------------------------------+--------------+
| 1  | test           | reddit  |       29      |         0         | 2024-05-19 11:59:55 | https://reddit.com/                                  |m4a           |
+----+----------------+---------+---------------+-------------------+---------------------+------------------------------------------------------+--------------+
| 2  | @AlexiBexi     | youtube |      828      |         0         | 2024-05-19 12:07:04 | https://www.youtube.com/@AlexiBexi/videos            |              |
| 3  | @Lohntsichdas  | youtube |      181      |         0         | 2024-05-19 14:28:50 | https://www.youtube.com/@Lohntsichdas/videos         |              |
| 4  | @Finanzfluss   | youtube |      635      |         0         | 2024-05-19 14:29:05 | https://www.youtube.com/@Finanzfluss/videos          |              |
| 5  | @DoktorWhatson | youtube |      288      |         0         | 2024-05-19 14:29:25 | https://www.youtube.com/@DoktorWhatson/videos        |              |
+----+----------------+---------+---------------+-------------------+---------------------+------------------------------------------------------+--------------+
```

### Add Subscriptions
To add a subscription the overview url of the channel/playlist is needed. For example:
```
        yt_manager.py add-subscription https://www.youtube.com/@AlexiBexi/ --output-format <<format>>
```
or if you want to add multiple
```
        yt_manager.py add-subscription batch <<Path to a file>>
```
The file is simply a list of links. Each link gets a new line (Enter Key)

After the command is issued all metadata are downloaded and saved to db.
IMPORTANT: This feature might change in the future! -  If you use the downlaoded metadata be cautious!

### Delete Subscriptions
To delete a subscription you can take multiple paths.
You can either pass the Name provided in the ``` list-subscriptions``` command or you can pass the url from the channel/playlist. For example:

#### Using the Name:
```
        yt_manager.py del-subscription @AlexiBexi
```

#### Using the Link:
```
        yt_manager.py del-subscription https://www.youtube.com/@AlexiBexi/videos
```
or
```
        yt_manager.py del-subscription https://www.youtube.com/@AlexiBexi
```

# Format handling
If you want to change the output format you can create profiles (or use the pre defined ones)... 
Currently you can only edit / add profiles in the db or add them manually inside the "formats.json" file. TZhe program will import the data automatically

You can define the output format in different ways:
  ## General Info
  In any case: If you define an output profile (for custom downlaods or subscriptions) they overrule all other settings!
  ### Subscriptions:
  If you create a new subscription you can pass the "--output-format" flag and pass a profile in which all data will be downloaded (list is possible)
  ### Custom downlaods
  For custom videos you can also pass the "--output-format" flag to define the output format

  ### Nothing passed (Global)
  If nothing is passed you need to use the global settings. Profiles can be enabled or disabled. If enabled
  all filedownloads without explicit output format passed will be downloaded using ALL enabled profiles. 
  You can have multiple profiles enabled at the same time!
  ### Fallback
  The fallback if something breaks is "best"... You can change it in the config.ini file!

  ## Commands
  ### Show defined profiles and states

  This command allows you to list all available profiles and see if profiles are enabled or disabled
  ```
        yt_manager.py show-format-profiles
  ```

  ### Disable a profile (globally)
  You can disable profiles for global use (not counted for subscriptions!)
  ```
        yt_manager.py disable-format-profile <<name>>
  ```

  ### Enable a profile (globally)
  You can enable profiles by using this command. Important: Multiple profiles can be active. You can use the 
  optional flag "only_active" to disable all other enabled profiles!
  ```
        yt_manager.py enable-format-profile <<name>> --only_active
  ```

## Backup functionalities
### Export Subscriptions
You can create a backup file of your subscriptions. The file will be saved in your base dir (defined in config scheme/db)

```
        yt_manager.py export-subscriptions
```

### Import Subscriptions
You can import a backup file of your subscriptions. Just pass a path to the json file.

```
        yt_manager.py import-subscriptions <<path>>
```

### Export Items
You can create a backup file of your saved items. The file will be saved in your base dir (defined in config scheme/db)

```
        yt_manager.py export-items
```

### Import items
You can import a backup file of your items. Just pass a path to the json file.

```
        yt_manager.py import-items <<path>>
```

### Create a full backup of work data
This will export the subscription table and all items. This command only calls export-items() and export-subscriptions()

```
        yt_manager.py backup
```

## Duplicate handling
### Show duplicates
This will show all duplicates found after a validate() run in CLI

```
        yt_manager.py show-duplicates
```

## Single download
If you want to download only one Video you can also use the ```custom``` command.
This command will download only the link you provide. It must be a valid video link! -  This means if you paste it into your browser a video should start.

Like in subscriptions the program will save this video in the db and if it detects changes (like corruption) through the ```check``` command, it will redownload the video (if enabled). But also if you move it or delete it from the expected storage path.

A batch mode is planned but not implemented yet!

Example use:
```
        yt_manager.py custom https://www.youtube.com/watch?v=gE_FuQuaKc0 --output-format <<format>>
```
or if you want to download multiple links
```
        yt_manager.py custom batch <<Path to a file>>
```
The file is simply a list of links. Each link gets a new line (Enter Key)

# Configuration

The configuration is done by different json files. These files contain default values and can be altered before the first run. After that only by CLI (not implemented yet) or by an SQLite Explorer.

The configuration is splitted in multiple files
## config.ini
This file is currently not heavily used. It contains only some database information since I want to make this project as portable as possible. It contains only the database information.
```
[db]
db_driver = sqlite -> The db Driver (currently only sqlite is supported. MySQL is planned)
db_path = ..\test.db -> SQLIte DB Path
db_name = database.db -> SQLite Db Name (will be created if not existing)
db_host = localhost -> MySQL Setting (not used)
db_user = username -> MySQL Setting (not used)
db_pass = password -> MySQL Setting (not used)
```
## project.json (Config Table) - Main Configuration
This file contains the most important configuration settings. It is like all other files a scheme file which can be used to alter the behaviour of the program.
In the following the *current* default file (may be changed later). Due to the comments it can not be copy/pasted!
```
{
    "schema_name": "project",
    "url_template": false,
    "db": {
        "table_needed": true,
        "table_name": "config",
        "columns": {
            "id": {"type": "integer", "primary_key": true, "auto_increment": true, "not_null": true, "unique": false},
            "option_name": {"type": "text", "not_null": true, "unique": true},
            "option_value": {"type": "text", "not_null": true},
            "datecreated": {"type": "DATETIME", "default": "CURRENT_TIMESTAMP"}
        },
        "rows": [
            {"option_name": "base_location", "option_value": "../ytdownloader"},
            {"option_name": "use_tags_from_ydl", "option_value": "false"},
            {"option_name": "remove_file_on_post_process_error", "option_value": "false"},
            {"option_name": "last_full_check", "option_value": "NONE"},
            {"option_name": "subscription_check_delay", "option_value": "24"}
        ]
    }
}
```
```
schema_name => This key only describes a "friendly name" used for logging and db stuff

url_template => If false the file is only used for system matters. For example to create tables in the db. It will not used for download/subscription stuff

db.table_needed => This key decides if a table is created for this scheme

db.table_name => Name of the table...

db.columns => This dict is used to create the table. You can define each column by using the following scheme:
{"key": {options}}
Multiple options are availiable:
    - type => Describes the column type (text/SQLite)
    - primary_key => DEcides if the given column is the primary key (bool)
    - auto_increment => auto increments the column for each new insert. Only for integer type! (bool)
    - not_null: Force content for each insert (bool)
    - unique: Each entry of this column needs to be unique (bool)
    - default: Define the default value if nothing is passed (text)

db.rows => This needs to be an array containing all default entries that should be inserted. Each entry is an dict containing all column names that should be filled.
You simply take all row names as keys and the corresponding values as values.
```

## saved_items.json - Items Table
This file is the blueprint for the items table. This table will contain all downloaded files. Be careful! I do NOT recommend any changes unless you know what you do. In the future this program will simply remove the table if not working or will try to migrate the table (to support updates). You could lose all data if you don't be careful...

```
{
    "schema_name": "items",
    "db": {
        "table_needed": true,
        "table_name": "items",
        "columns": {
            "id": {"type": "integer", "primary_key": true, "auto_increment": true, "not_null": true, "unique": false},
            "scheme": {"type": "text", "not_null": true},
            "file_name": {"type": "text", "not_null": true},
            "file_path": {"type": "text", "not_null": true},
            "file_hash": {"type": "text", "not_null": true, "unique": true},
            "url": {"type": "text", "not_null": true, "unique": true},
            "created": {"type": "DATETIME", "default": "CURRENT_TIMESTAMP"},
            "locked": {"type": "integer", "not_null": true, "default": "0"},
            "tags": {"type": "text", "not_null": false},
            "data": {"type": "text", "not_null": false}
        }
    }
}
```
```
The options are exactly the same as in the project.json file.
I will only explain the columns briefly. If you want to know more about the options and
general structure please read the project.json part or create an issue.

id => Just an identifier... Later you can use it maybe to remove files...

scheme => The scheme used to download the file

file_name => The filename on your false

file_path => The path to your file (excluding the filename. Please be aware these are STATIC paths! - If you move your files you need to modify the path column at one manually per scheme/category!)

file_hash => The file hash...

url => since your file could be corrupted the original file url
is saved to redownload the file if the check() command will
find a corrupt or missing file.
As a bonus you can find videos that are not available anymore -
you would wonder how often this is the case ^^
Also this field is contains a JSON array. This program tries to avoid any double saved videos. If you add a new url or iterate over all subscriptions at the end also the hash will be checked. If it is the same it is possible that multiple sites have published the same video. If so the new url will be appended to the array. With this approach it is less likly that you downlaod a video that you already have just to remove it afterwards...

created => Timestamp of the creatin time...

locked => This program will support multi threading to check all files.
Because all need to be rehashed to compare the current hashes to the saved ones.
Because of this Files will be locked to prevent double access.
Like in my auto_hash repository... The code will be mainly the same...

tags => Many video platforms support tags. You can save the tags if you want or add own tags. This is a feature for a future web gui...

data => This column contains the extracted metadata.
This field can be very large and bloating your SQLite db! -
Maybe this feature will be customizable and modified in the future.
In general this program only needs some values for correct operation.
The rest is for your stuff...
```

## subscriptions.json - Subscription table
```
{
    "schema_name": "subscriptions",
    "db": {
        "table_needed": true,
        "table_name": "subscriptions",
        "columns": {
            "id": {"type": "integer", "primary_key": true, "auto_increment": true, "not_null": true, "unique": false},
            "scheme": {"type": "text", "not_null": true},
            "subscription_name": {"type": "text", "not_null": true},
            "subscription_path": {"type": "text", "not_null": true},
            "passed_subscription_path": {"type": "text", "not_null": true},
            "subscription_last_checked": {"type": "DATETIME", "default": "CURRENT_TIMESTAMP"},
            "subscription_created": {"type": "DATETIME", "default": "CURRENT_TIMESTAMP"},
            "downloaded_content_count": {"type": "integer", "not_null": true, "default": "0"},
            "subscription_content_count": {"type": "integer", "not_null": true},
            "subscription_has_new_data": {"type": "integer", "not_null": true, "default": "1"},
            "subscription_data": {"type": "text", "not_null": true}
        }
    }
}
```
```
This table contains all subscription data. Like in the items table I only explain the columns of the table. For option reference look at the project.json part!

id => Just the identifier

scheme => The scheme used for this subscription (saves some time when iterating through hundreds of videos...)

subscription_name => friendly name (the channel/playlist name)

subscription_path => The url to the playlist / channel.
This url is prepared by the scheme.
This path is not necessarily the same as the url you passed (but could be the same...)

passed_subscription_path => This is the url you passed to add the subscription

subscription_last_checked => Contains the last time the subscription was checked.

subscription_created => Contains the time when you added the subscription (just for stats...)

downloaded_content_count => How many files have you downloaded from this subscription

subscription_content_count => Shows the number of items in your subscription during the last check

subscription_has_new_data => If the number btw. last check and new check is different this field is 1 else 0 (also after each cycle this ffield will be set to 0)

subscription_data => metadata of the subscription. This field can be very very large depending on the channels where you subscribe. This field can blow up your db!
```

## Authors

- [@j54j6](https://www.github.com/j54j6)


## Acknowledgements

 - [yt-dlp](https://github.com/yt-dlp/yt-dlp)
 - [PrettyTables](https://github.com/jazzband/prettytable)
 - [TLDExtract](https://github.com/john-kurkowski/tldextract)
 - [Validators](https://github.com/python-validators)
 - [Awesome Readme Templates](https://awesomeopensource.com/project/elangosundar/awesome-README-templates)