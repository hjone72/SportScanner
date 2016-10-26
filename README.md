# SportScanner

[![Join the chat at https://gitter.im/mmmmmtasty/SportScanner](https://badges.gitter.im/Join%20Chat.svg)](https://gitter.im/mmmmmtasty/SportScanner?utm_source=badge&utm_medium=badge&utm_campaign=pr-badge&utm_content=badge)

Scanner and Metadata Agent for Plex that uses www.thesportsdb.com

#Installation

Plex main folder location:

    * '%LOCALAPPDATA%\Plex Media Server\'                                        # Windows Vista/7/8
    * '%USERPROFILE%\Local Settings\Application Data\Plex Media Server\'         # Windows XP, 2003, Home Server
    * '$HOME/Library/Application Support/Plex Media Server/'                     # Mac OS
    * '$PLEX_HOME/Library/Application Support/Plex Media Server/',               # Linux
    * '/var/lib/plexmediaserver/Library/Application Support/Plex Media Server/', # Debian,Fedora,CentOS,Ubuntu
    * '/usr/local/plexdata/Plex Media Server/',                                  # FreeBSD
    * '/usr/pbi/plexmediaserver-amd64/plexdata/Plex Media Server/',              # FreeNAS
    * '${JAIL_ROOT}/var/db/plexdata/Plex Media Server/',                         # FreeNAS
    * '/c/.plex/Library/Application Support/Plex Media Server/',                 # ReadyNAS
    * '/share/MD0_DATA/.qpkg/PlexMediaServer/Library/Plex Media Server/',        # QNAP
    * '/volume1/Plex/Library/Application Support/Plex Media Server/',            # Synology, Asustor
    * '/raid0/data/module/Plex/sys/Plex Media Server/',                          # Thecus
    * '/raid0/data/PLEX_CONFIG/Plex Media Server/'                               # Thecus Plex community

 - Download the latest release from https://github.com/mmmmmtasty/SportScanner/releases
 - Extract files
 - Copy the extracted directory "Scanners" into your Plex main folder location - check the list above for more clues
 - Copy the extracted directory "SportScanner.bundle" into the Plug-ins directory in your main folder location - check the list above for more clues
 - You may need to restart Plex
 - Create a new library and under Advanced options you should be able to select "SportScanner" as both your scanner and metadata agent.
 - Copy SportScanner.py into your newly created folder

#Media Format

The SportScanner scanner requires one of two folder structures to work correctly, the first of which matches Plex's standard folder structure.

##RECOMMENDED METHOD

Follow the Plex standards for folder structure - TV Show\Season\<files>. For SportScanner, TV Shows = League Name. For example for 2016/2017 NHL and American NFL you would do something like the following:

 - ~LibraryRoot/NHL/1516/NHL 2016-10-18 San Jose Sharks vs New York Islanders.mkv
 - ~LibraryRoot/American NFL/2016/American NFL 2016-10-24 Round 7 Houston Texans vs Denver Broncos.mkv
 
This for is optimized for specific naming. Use the following formats:
 - `League YYYY-MM-DD Round X Away vs Home.ext`
 - "American NFL 2016-09-11 Round 1 San Diego Chargers vs Kansas City Chiefs"
 - "NHL 2016-10-18 San Jose Sharks vs New York Islanders"
 - "Formula 1 2016-10-09 Round 17"
 - "MotoGP 2016-10-23 Round 16"

Naming can be made be made easier using [SportRenamer](https://github.com/hjone72/TheSportDB)

In this scenario you still need all the information in the file name, I aim to remove that requirement down the line. The only information that comes only from the folder structure is the season. 

##Alternative naming standard

You can also choose to ignore the season directory and have the scanner work it out with a folder structure like so:

 - ~LibraryRoot/Ice Hockey/NHL/NHL.2015.09.25.New-York-Islanders.vs.Philadelphia-Flyers.720p.HDTV.60fps.x264-Reborn4HD_h.mp4

 THERE IS A DOWN SIDE TO THIS! For this to work you must include a file in each league directory called "SportScanner.txt" that contains information about how the seasons work for this sport. The first line in the file will always be "XXXX" or "XXYY". "XXXX" means that the seasons happens within one calendar year and will therefore be named "2015" of "1999" for example. "XXYY" means that a season occurs across two seasons and will take the format "1516" or "9899" for example. When you define the season as "XXYY" you MUST then on the next line write the integer values of a month and a day in the form "month,day". This should be a a month and a day somewhere in the off-season for that sport. This tells the scanner when one season has finished and the next one is beginning to ensure that it puts files in the correct season based off the date the event happened. As an example, if you are trying to add NHL you would create a file at the following path:

  - ~LibraryRoot/Ice Hockey/NHL/SportScanner.txt

In this instance the contents of this file would be as follows, saying that seasons should be in "XXYY" format and a date in the middle of the off-season is 1st July:

XXYY
7,1

## NOT RECOMMENDED (but works for now)

SportScanner does not actually pay attention to the name of the League directory when it comes to matching events - all info has to be in the filename. This means that you can still group all sports together and as long as they share a season format you can create a SportScanner.txt file as outlined above and everything will work.

This is rubbish, it kind of accidentally works, I don't recommend it as I will cut it out as part of improvement works in future.

#Known Issues
 - No posters for seasons
 - Can only handle individual files, not multipart or those in folders
 - All information must be in the filename regardless of the directory structure.
