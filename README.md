# !!! STILL IN PROGRESS !!!
# Show some love <3
[!["Buy Me A Coffee"](https://www.buymeacoffee.com/assets/img/custom_images/orange_img.png)](https://www.buymeacoffee.com/j54j6)

# YoutubeDL-Dowloader
 This little program is supposed to help you to make a private copy of videos from sites supporting youtube-dl. Currently many sites like youtube, NYT, CNBC but also adult sites like Pornhub 91porn and much more support youtube-dl. Feel Free to use it but be aware about legal discussions - This Repo is jsut a project to show that this is in general working.^^
 I am not responsible for any damages or anything else. You use this program on your OWN RISK


 # Architecure
 In General this program is built out of different modules. Each module handles some parts of the program needed to work as a whole.
 To ensure compatibility for different sites I utilize so called "schemes". Every supporterd site has its own scheme. Please feel free to built your own and send it to me :) - We can help each other with these and I am not capable of providing a scheme for each supported site ;)
 I provide some of then when requested and I have spare time.

 #Schemas
 Schemas are heavily used inside this project. They utilize different functions and can be used to dynamically change the behaviour of the program without any code knowledge.
 Schemas are used for 2 types
    1. Configuration -> It is possible to create database blueprints with schemas (like project.json file). 
    2. Websites -> To ensure future compatibility all website specific stuff is located inside a schema per website. If anything changes on the website it should be possible to alter the file and make iot work again (maybe due to a new header or something else...)

Supported values:
    Database Configuration:
        If you want to create a table inside the main database you can utilize the "db" key. If defined the program will create a table with the given columns and if you want also default rows. 
        For reference please check the project.json file as a reference :)


# TODO
- implementing db functions
- implementing user interface/cli
- implementing downloader
- implementing scheme reader
- creating requirements.txt
- complete ReadME

# Postponed todos
- Implementing support for both SQLite and MySQL