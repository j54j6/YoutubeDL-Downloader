

[![GPLv3 License](https://img.shields.io/badge/License-GPL%20v2-green.svg)](https://opensource.org/licenses/)

[![CodeFactor](https://www.codefactor.io/repository/github/j54j6/youtubedl-dowloader/badge)](https://www.codefactor.io/repository/github/j54j6/youtubedl-dowloader)



# !!! STILL IN PROGRESS !!!
# Show some love <3
[!["Buy Me A Coffee"](https://www.buymeacoffee.com/assets/img/custom_images/orange_img.png)](https://www.buymeacoffee.com/j54j6)

# YoutubeDL-Dowloader
 This little program is supposed to help you to make a private copy of videos from sites supporting youtube-dl. Currently many sites like youtube, NYT, CNBC but also adult sites like Pornhub 91porn and much more support youtube-dl. Feel Free to use it but be aware about legal discussions - This Repo is jsut a project to show that this is in general working.^^
 I am not responsible for any damages or anything else. You can use this program on your OWN RISK


 # Architecure
 In General this program is built out of different modules. Each module handles some parts of the program needed to work as a whole.
 To ensure compatibility for different sites I utilize multiple files called "schemes". Every supporterd site has its own scheme. Please feel free to built your own and send it to me :) - We can help each other with these. I am not capable of providing a scheme for each supported site ;)
 I provide some of them when requested if I have spare time.

 #Schemes
 Schemes are heavily used inside this project. They utilize different functions and can be used to dynamically change the behaviour of the program without any code knowledge.
 Schemas are used for 2 types
    1. Configuration -> It is possible to create database blueprints with schemas (like the project.json file used to create the main configuration and all default values).
    2. Websites -> To ensure future compatibility all website specific stuff is located inside a scheme file per website. If anything changes on the website it should be possible to alter the file and make it work again (maybe due to a new header or something else...)

Supported values:
    Database Configuration:
        If you want to create a table inside the main database you can utilize the "db" key. If defined the program will create a table with the given columns and if you want also default rows.
        For reference please check the project.json file as a reference :)



# Currently Working
- Downloading videos (Custom) => Single link
- Register Video in db including tags and important information (also metadata for later use...)
- Register / Deleting / List Subscriptions

# Currently supported Sites
- Pinterest
- Reddit
- Pornhub
- YouTube

# TODO
- implementing db functions
- implementing user interface/cli
- implementing downloader
- implementing scheme reader
- creating requirements.txt
- complete ReadME

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
    - FIlter (optional) -> A filter can be used to only return a specific subscriptiontype based on the scheme (for example "youtube".) The filter need to be passed as comma separated list. For example:

```
        yt_manager.py list-Subscriptions youtube,reddit
```
With the provided command only subscriptions created with the youtube or reddit scheme are shown.  If no filter is passed all subscriptions will be shown like below. If the scheme changes a divider is inserted
```
+----+----------------+---------+---------------+-------------------+---------------------+------------------------------------------------------+
| ID | Name           | Scheme  | Avail. Videos | Downloaded Videos |     Last checked    | url                                                  |
+----+----------------+---------+---------------+-------------------+---------------------+------------------------------------------------------+
| 1  | test           | reddit  |       29      |         0         | 2024-05-19 11:59:55 | https://reddit.com/                                  |
+----+----------------+---------+---------------+-------------------+---------------------+------------------------------------------------------+
| 2  | @AlexiBexi     | youtube |      828      |         0         | 2024-05-19 12:07:04 | https://www.youtube.com/@AlexiBexi/videos            |
| 3  | @Lohntsichdas  | youtube |      181      |         0         | 2024-05-19 14:28:50 | https://www.youtube.com/@Lohntsichdas/videos         |
| 4  | @Finanzfluss   | youtube |      635      |         0         | 2024-05-19 14:29:05 | https://www.youtube.com/@Finanzfluss/videos          |
| 5  | @DoktorWhatson | youtube |      288      |         0         | 2024-05-19 14:29:25 | https://www.youtube.com/@DoktorWhatson/videos        |
+----+----------------+---------+---------------+-------------------+---------------------+------------------------------------------------------+
```

### Add Subscriptions
To add a subscription the overview url of the channel/playlist is needed. For example:
```
        yt_manager.py add-subscription https://www.youtube.com/@AlexiBexi/
```

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

## Single download
If you want to download only one Video you can also use the ```custom``` command.
This command will download only the link you provide. It must be a valid video link! -  This means if you paste it into your browser a video should start.

Like in subscriptions the program will save this video in the db and if it detects changes (like corruption) through the ```check``` command, it will redownload the video. But also if you move it or delete it from the expected storage path.

A batch mode is planned but not implemented yet!

Example use:
```
        yt_manager.py custom https://www.youtube.com/watch?v=gE_FuQuaKc0
```

## Authors

- [@j54j6](https://www.github.com/j54j6)


## Acknowledgements

 - [yt-dlp](https://github.com/yt-dlp/yt-dlp)
 - [PrettyTables](https://github.com/jazzband/prettytable)
 - [TLDExtract](https://github.com/john-kurkowski/tldextract)
 - [Validators](https://github.com/python-validators)
 - [Awesome Readme Templates](https://awesomeopensource.com/project/elangosundar/awesome-README-templates)
