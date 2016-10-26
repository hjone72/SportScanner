import re, time, os, datetime
from pprint import pprint
from difflib import SequenceMatcher

netLock = Thread.Lock()

# Keep track of success/failures in a row.
successCount = 0
failureCount = 0

MIN_RETRY_TIMEOUT = 2
RETRY_TIMEOUT = MIN_RETRY_TIMEOUT
TOTAL_TRIES = 1
BACKUP_TRIES = -1

SPORTSDB_API = "http://www.thesportsdb.com/api/v1/json/8123456712556/"

headers = {'User-agent': 'Plex/Nine'}


def similar(a, b):
    return round(SequenceMatcher(None, a, b).ratio(), 2)


def GetResultFromNetwork(url, fetchContent=True):
    global successCount, failureCount, RETRY_TIMEOUT

    url = url.replace(' ', '%20')

    try:
        netLock.acquire()
        #Log("SS: Retrieving URL: " + url)

        tries = TOTAL_TRIES
        while tries > 0:

            try:
                result = HTTP.Request(url, headers=headers, timeout=60)
                if fetchContent:
                    result = result.content

                failureCount = 0
                successCount += 1

                if successCount > 20:
                    RETRY_TIMEOUT = max(MIN_RETRY_TIMEOUT, RETRY_TIMEOUT / 2)
                    successCount = 0

                # DONE!
                return result

            except Exception, e:

                # Fast fail a not found.
                if e.code == 404:
                    return None

                failureCount += 1
                Log("Failure (%d in a row)" % failureCount)
                successCount = 0
                time.sleep(RETRY_TIMEOUT)

                if failureCount > 5:
                    RETRY_TIMEOUT = min(10, RETRY_TIMEOUT * 1.5)
                    failureCount = 0

    finally:
        netLock.release()

    return None

def GetLeagueDetails(id):
    url = "{0}lookupleague.php?id={1}".format(SPORTSDB_API, id)
    try:
        details = (JSON.ObjectFromString(GetResultFromNetwork(url, True)))['leagues'][0]
    except:
        Log("SS: Could not retrieve shows from thesportsdb.com")

    return details

def Start():
    # Let's put this up when things are all stable shall we?
    HTTP.CacheTime = 0
    # HTTP.CacheTime = CACHE_1HOUR * 24


class SportScannerAgent(Agent.TV_Shows):
    name = 'SportScanner'
    languages = ['en']

    def search(self, results, media, lang, manual):
        # Get all leagues defined in thesportsdb and match this one
        show_title = media.show
        Log("SS: Attempting to match {0}".format(show_title))
        url = "{0}all_leagues.php".format(SPORTSDB_API)
        try:
            potential_leagues = (JSON.ObjectFromString(GetResultFromNetwork(url, True)))['leagues']
        except:
            Log("SS: Could not retrieve shows from thesportsdb.com")

        match = False

        # Check to see if there is a perfect match
        # Iterate through all of the sports primary names. If this fails then we can make a call for each sport and match against alternate names.
        # In my case this will match unless there has been a serious error!
        # https://github.com/hjone72/TheSportDB
        if potential_leagues is not None:
            for league in potential_leagues: #So far we've only made 1 API call to TSDB.
                if show_title == league['strLeague']:
                    Log("SS: Found a perfect match for {0}".format(show_title))
                    league_details = GetLeagueDetails(league['idLeague']) # Match found. Get the rest of the details.
                    results.Append(
                        MetadataSearchResult(
                            id=league_details['idLeague'],
                            name=show_title,
                            year=int(league_details['intFormedYear']),
                            lang='en',
                            score=100
                        )
                    )
                    match = True
                    break # Break. We've found the show we're looking for. Do we need to keep looking?
                    
        #Check if we can reverse match. This requires an API call for each sport.
        if not match:
            if potential_leagues is not None:
                cached_leagues = {} # We will use this in the next step. This will remove an additional API call for every sport.
                for i in range(0, len(potential_leagues)):
                    # Log("SS: Comparing {0] to {1}".format(x['strLeague'], show_title))
                    # Get the full details of the league
                    league_details = GetLeagueDetails(potential_leagues[i]['idLeague'])
                    cached_leagues[i] = league_details
                    # Match against the alternate names.
                    if league_details['strLeagueAlternate'] is not None:
                        if show_title in league_details['strLeagueAlternate'].split(","):
                            results.Append(
                                MetadataSearchResult(
                                    id=league_details['idLeague'],
                                    name=show_title,
                                    year=int(league_details['intFormedYear']),
                                    lang='en',
                                    score=100
                                )
                            )
                            match = True
                            break # Break. We've found the show we're looking for. Do we need to keep looking?

        # See if anything else comes close if we are doing a deeper manual search and haven't found anything already
        if not match and manual:
            Log("SS: Doing a comparison match, no exact matches found")
            for i in range(0, len(potential_leagues)):
                # Get league details
                # In my setup it won't ever get this far, but do we really need to make another API call to TSDB for each sport?
                # The values won't have changed since the first run through. We could create a dict that stores each sport.
                # This will greatly improve the speed of this step.
                if i in cached_leagues: #Check if a cached value exists.
                    #Cached value exists. Use it.
                    league_details = cached_leagues[i]
                else:
                    #Shouldn't ever reach here as we loaded every sport in the previous step.
                    league_details = GetLeagueDetails(potential_leagues[i]['idLeague'])
                    
                score = (similar(league_details['strLeague'], show_title) * 100)

                # Match with 60% similarity
                if score > 60:
                    Log("SS: Matched {0} with a score of {1}".format(league_details['strLeague'], score))
                    results.Append(
                        MetadataSearchResult(
                            id=league_details['idLeague'],
                            name=league_details['strLeague'],
                            year=int(league_details['intFormedYear']),
                            lang='en',
                            score=score
                        )
                    )

                # Match against alternate league names
                if league_details['strLeagueAlternate'] is not None:
                    alt_names = league_details['strLeagueAlternate'].split(",")
                    for j in range(0, len(alt_names)):
                        score = (similar(alt_names[j], show_title) * 100)
                        # Match with 60% similarity
                        if score > 60:
                            results.Append(
                                MetadataSearchResult(
                                    id=league_details['idLeague'],
                                    name=show_title,
                                    year=int(league_details['intFormedYear']),
                                    lang='en',
                                    score=score
                                )
                            )

    def update(self, metadata, media, lang):
        Log("SS: update for: {0}".format(metadata.id))

        # We're not trying to read cached ones for now - let's get the new stuff every time
        try:
            url = "{0}lookupleague.php?id={1}".format(SPORTSDB_API, metadata.id)
            league_metadata = JSON.ObjectFromString(GetResultFromNetwork(url, True))['leagues'][0]
        except:
            pass

        # Fill in any missing information for show and download posters/banners
        metadata.title = league_metadata['strLeague']
        metadata.summary = league_metadata['strDescriptionEN']
        if not league_metadata['strSport'] in metadata.genres:
            metadata.genres.add(league_metadata['strSport'])
        try:
            metadata.originally_available_at = league_metadata['intFormedYear']
        except:
            pass

        # Work out what episodes we have and match them to ones in the right season
        @parallelize
        def UpdateEpisodes():
            # Go through available episodes
            for s in media.seasons:
                for e in media.seasons[s].episodes:
                    episode = metadata.seasons[s].episodes[e]
                    episode_media = media.seasons[s].episodes[e]

                    @task
                    def UpdateEpisode(episode=episode, league_metadata=league_metadata, episode_media=episode_media, metadata=metadata):
                        # This is where opinions start to split. Some people put events as 'Home v Away' and others put it as 'Away v Home'.
                        # I'll change this section to work KNOWING how my files will look.
                        # https://github.com/hjone72/TheSportDB
                        Log("SS: Matching episode number {0}: {1}".format(e, episode_media.title))
                        matched_episode = None
                        # First try and match the filename exactly as it is
                        # Plus or minus a few changes ;)
                        # Input file looks like:
                        #    League Date Round # Away vs Home.ext
                        #    American NFL 2016-09-18 Round 2 San Diego Chargers vs Jacksonville Jaguars.mkv
                        #    League Date Away vs Home.ext
                        #    NHL 2016-10-18 San Jose Sharks vs New York Islanders.mkv
                        #    League Date Round.ext
                        #    Formula 1 2016-10-09 Round 17.mkv
                        
                        filename = os.path.splitext(os.path.basename(episode_media.items[0].parts[0].file))[0]
                        Log("SS: Matching episode with filename: {0}".format(filename))
                        if re.search(r'(Round \d{1,2})', filename) is not None:
                            Round = re.search(r'(Round \d{1,2})', filename).group(0)
                            filename = filename.replace(Round, '')
                            filename = filename.replace('  ', ' ')
                        
                        # Event MUST have a date.
                        eventDate = re.search(r'(\d{4}).(\d{2}).(\d{2})', filename).group(0)
                        
                        League = filename.split(" {0} ".format(eventDate))[0]
                        Event = filename.split(" {0} ".format(eventDate))[1]
                        Teams = Event.split(' vs ')
                           
                        #Rebuild.
                        # Formula 1 2016-10-09 Japanese Grand Prix
                        # American NFL 2016-10-02 Atlanta Falcons vs Carolina Panthers
                        # American NFL 2016-09-18 San Diego Chargers vs Jacksonville Jaguars
                        if len(Teams) != 2:
                            TSDBName = "{0} {1}".format(League, eventDate)
                            TSDBName = TSDBName.replace(' ', '_')
                            filename = TSDBName
                        else:
                            TSDBName = "{0} {1} {2} vs {3}".format(League, eventDate, Teams[1], Teams[0])
                            TSDBName = TSDBName.replace(' ', '_')
                            filename = TSDBName

                        try:
                            url = "{0}searchfilename.php?e={1}".format(SPORTSDB_API, filename)
                            results = JSON.ObjectFromString(GetResultFromNetwork(url, True))
                            matched_episode = results['event'][0]
                            Log("SS: Matched {0} using filename search".format(matched_episode['strEvent']))
                        except:
                            pass

                        '''
                        whackRx = ['([hHx][\.]?264)[^0-9].*', '[^[0-9](720[pP]).*', '[^[0-9](1080[pP]).*',
                                   '[^[0-9](480[pP]).*', '[^[0-9](540[pP]).*']
                        for rx in whackRx:
                            filename = re.sub(rx, "", filename)
                        
                        
                        
                        # Replace all '-' with '_'
                        filename = re.sub(r'[-\.]', '_', filename)
                        # Replace the date separators with '-'
                        filename = re.sub(r'(\d{4}).(\d{2}).(\d{2})', r'\1-\2-\3', filename)

                        try:
                            url = "{0}searchfilename.php?e={1}".format(SPORTSDB_API, filename)
                            results = JSON.ObjectFromString(GetResultFromNetwork(url, True))
                            matched_episode = results['event'][0]
                            Log("SS: Matched {0} using filename search".format(matched_episode['strEvent']))
                        except:
                            pass
                        '''

                        # Then try and generate a filename that might work
                        # Take the full name of the league, add on the date of the event
                        # Then chuck the title on the end and hope the home/away ordering is correct for this sport
                        if matched_episode is None:
                            try:
                                bastard_year = re.sub(r'(\d{4})(\d{2})(\d{2})', r'\1-\2-\3', episode_media.originally_available_at)
                                bastard_filename = '{0} {1} {2}'.format(metadata.title, bastard_year, episode_media.title)
                                # Replace all ' ' with '_'
                                bastard_filename = re.sub(r' ', '_', bastard_filename)
                                url = "{0}searchfilename.php?e={1}".format(SPORTSDB_API, bastard_filename)
                                results = JSON.ObjectFromString(GetResultFromNetwork(url, True))
                                matched_episode = results['event'][0]
                                Log("SS: Matched {0} using filename search".format(matched_episode['strEvent']))
                            except:
                                pass

                        if matched_episode is None:
                            Log("SS: Could not match on filename, trying dates and titles")
                            # If the file doesn't match perfectly, try and match based on dates and event titles
                            closest_event = None
                            best_score = 0
                            total_matches = 0

                            # Get all events in that sport/league/day
                            match = re.search(r'(?P<year>\d{4})-(?P<month>\d{1,2})-(?P<day>\d{1,2})', episode_media.originally_available_at, re.IGNORECASE)
                            if match:
                                # Replace all spaces with underscores for league name
                                league_name = re.sub(r' ', '_', league_metadata['strLeague'])
                                url = "{0}eventsday.php?d={1}-{2}-{3}&l={4}".format(SPORTSDB_API, match.group('year'), match.group('month'), match.group('day'), league_name)
                                day_events = JSON.ObjectFromString(GetResultFromNetwork(url, True))

                                Log("SS: Searching through {0} events".format(len(day_events['events'])))
                                for current_event in range(len(day_events['events'])):
                                    # Log("SS: Comparing {0} to {1}".format(season_metadata['events'][current_event]['strEvent'], episode_media.title))
                                    # Log("SS: Checking dateEvent: {0}".format(day_events['events'][current_event]['dateEvent']))
                                    if ("dateEvent" in day_events['events'][current_event]) and episode_media.originally_available_at:
                                        if day_events['events'][current_event]['dateEvent'] == episode_media.originally_available_at:
                                            total_matches += 1
                                            closeness = similar(episode_media.title,
                                                                day_events['events'][current_event]['strEvent'])
                                            # Take a second closeness with bastard name
                                            bastard_title = "{0} {1}".format(metadata.title, episode_media.title)
                                            bastard_closeness = similar(bastard_title,
                                                                day_events['events'][current_event]['strEvent'])
                                            if bastard_closeness > closeness:
                                                closeness = bastard_closeness
                                                Log("SS: Using {0} from match with {1}".format(closeness, bastard_title))

                                            Log("SS: Match ratio of {0} between {1} and {2}".format(closeness, episode_media.title, day_events['events'][current_event]['strEvent']))
                                            # If they are a perfect match then we are done
                                            if closeness == 1:
                                                best_score = 1
                                                closest_event = current_event
                                                break
                                            elif closeness > best_score:
                                                best_score = closeness
                                                closest_event = current_event
                                                continue

                            if total_matches == 0:
                                Log("SS: No events took place on {0}".format(episode_media.originally_available_at))

                            Log("SS: Best match was {0}".format(best_score))
                            # Only accept if the match is better than 80% or assume we have found the correct event if there is only one on that date
                            if best_score > 0.8 or total_matches == 1:
                                matched_episode = day_events['events'][closest_event]

                        if matched_episode is None:
                            Log("SS: Could not match {0}".format(episode_media.title))
                            return

                        Log("SS: Updating metadata for {0}".format(matched_episode['strEvent']))
                        # Create a filename.
                        if matched_episode['intRound'] is not None: #Does this sport have a round?
                            extraInfo = "" # Blank unless changed.
                            if matched_episode['strAwayTeam'] is not None and matched_episode['strHomeTeam'] is not None:
                                extraInfo = " - {0} vs {1}".format(matched_episode['strAwayTeam'], matched_episode['strHomeTeam'])
                            PlexName = "Round {0}{1}".format(matched_episode['intRound'], extraInfo)
                        else:
                            if matched_episode['strAwayTeam'] is not None and matched_episode['strHomeTeam'] is not None:
                                PlexName = "{0} vs {1}".format(matched_episode['strAwayTeam'], matched_episode['strHomeTeam'])
                            else:
                                PlexName = matched_episode['strEvent'] # This is pretty weird. Shouldn't get to this point.

                        episode.title = PlexName
                        #Generate a useful description based on the available fields
                        extra_details = ""
                        if matched_episode['strAwayTeam'] is not None and matched_episode['strHomeTeam'] is not None:
                            extra_details = "Away vs Home\n"
                            extra_details = "{0}{1} vs. {2}\n".format(extra_details, matched_episode['strAwayTeam'], matched_episode['strHomeTeam'])
                        if matched_episode['dateEvent'] is not None and matched_episode['strTime'] is not None:
                            extra_details = "{0}Played on {1} at {2}\n".format(extra_details, matched_episode['dateEvent'], matched_episode['strTime'])
                        if matched_episode['strCircuit'] is not None:
                            extra_details = "{0}Race venue: {1}".format(extra_details, matched_episode['strCircuit'])
                            if matched_episode['strCountry'] is not None:
                                if matched_episode['strCity'] is not None:
                                    extra_details = "{0} in {1}, {2}".format(extra_details, matched_episode['strCity'], matched_episode['strCountry'])
                                else:
                                    extra_details = "{0} in {1}".format(extra_details, matched_episode['strCountry'])
                        summary = "{0}\n\n{1}\n\nMatched by SportScanner.".format(extra_details, matched_episode['strDescriptionEN'])
                        Log("SS: summary: {0}".format(summary))
                        episode.summary = summary
                        episode.originally_available_at = datetime.datetime.strptime(
                            matched_episode['dateEvent'], "%Y-%m-%d").date()

                        # Download the episode thumbnail
                        valid_names = list()
                        if matched_episode['strThumb'] is not None:
                            thumb = matched_episode['strThumb']
                            if thumb not in episode.thumbs:
                                try:
                                    episode.thumbs[thumb] = Proxy.Media(GetResultFromNetwork(thumb, False))
                                    valid_names.append(thumb)
                                except:
                                    Log("SS: Failed to add thumbnail for {0}".format(episode.title))
                                    pass
                                else:
                                    Log("SS: No new thumbnails to download for {0}".format(episode.title))
                        else:
                            Log("SS: No thumbs to download for {0}".format(episode.title))

                        episode.thumbs.validate_keys(valid_names)

        @parallelize
        def DownloadImages():

            # Maintain a list of valid image names
            posters_to_dl = list()
            banners_to_dl = list()
            fanart_to_dl = list()

            Log("Downloading Images")
            # Each image is stored separately so we have to do something strange here
            # This looks through all the strPoster keys to see if they exist (strPoster, strPoster1 etc.)
            if league_metadata['strPoster'] is not None:
                posters_to_dl.append(league_metadata['strPoster'])
                for b in range(1, 10):
                    key_name = "strPoster{0}".format(b)
                    if key_name in league_metadata:
                        if league_metadata[key_name] is not None:
                            posters_to_dl.append(league_metadata[key_name])
                            # posters_to_dl.append("{0}/preview".format(league_metadata[key_name]))
                    else:
                        break
                # Now actually download the poster
                for i in range(len(posters_to_dl)):
                    poster_url = posters_to_dl[i]
                    if poster_url not in metadata.posters:
                        Log("SS: Downloading poster: {0}".format(poster_url))
                        
                        @task
                        def DownloadImage(metadata=metadata, poster_url=poster_url, i=i):
                            if poster_url not in metadata.posters:
                                Log("SS: Downloading poster {0}".format(poster_url))
                                try:
                                    metadata.posters[poster_url] = Proxy.Preview(GetResultFromNetwork(poster_url, False),
                                                                                 sort_order=(i + 1))
                                except:
                                    Log("SS: Failed to set poster for {0}".format(metadata.title))
                                    pass
            else:
                Log("SS: No posters to download for {0}".format(league_metadata['strLeague']))

            metadata.posters.validate_keys(posters_to_dl)

            # Each image is stored separately so we have to do something strange here
            if league_metadata['strBanner'] is not None:
                banners_to_dl.append(league_metadata['strBanner'])
                for b in range(1, 10):
                    key_name = "strBanner{0}".format(b)
                    if key_name in league_metadata:
                        if league_metadata[key_name] is not None:
                            banners_to_dl.append(league_metadata[key_name])
                            # banners_to_dl.append("{0}/preview".format(league_metadata[key_name]))
                for i in range(len(banners_to_dl)):
                    banner_url = banners_to_dl[i]
                    Log("SS: Downloading {0}".format(banner_url))

                    @task
                    def DownloadImage(metadata=metadata, banner_url=banner_url, i=i):
                        if banner_url not in metadata.banners:
                            Log("SS: Downloading banner {0}".format(banner_url))
                            try:
                                metadata.banners[banner_url] = Proxy.Preview(GetResultFromNetwork(banner_url, False),
                                                                             sort_order=(i + 1))
                            except:
                                Log("SS: Failed to set banner for {0}".format(metadata.title))
                                pass
            else:
                Log("SS: No banners to download for {0}".format(league_metadata['strLeague']))

            metadata.banners.validate_keys(banners_to_dl)

            for b in range(1, 10):
                key_name = "strFanart{0}".format(b)
                if key_name in league_metadata:
                    if league_metadata[key_name] is not None:
                        fanart_to_dl.append(league_metadata[key_name])
                        # fanart_to_dl.append("{0}/preview".format(league_metadata[key_name]))
            for i in range(len(fanart_to_dl)):
                fanart_url = fanart_to_dl[i]
                Log("SS: Downloading {0}".format(fanart_url))

                @task
                def DownloadImage(metadata=metadata, fanart_url=fanart_url, i=i):
                    if fanart_url not in metadata.posters:
                        Log("SS: Downloading art {0}".format(fanart_url))
                        try:
                            metadata.art[fanart_url] = Proxy.Preview(GetResultFromNetwork(fanart_url, False),
                                                                     sort_order=(i + 1))
                        except:
                            Log("SS: Failed to set art for {0}".format(metadata.title))
                            pass

            metadata.art.validate_keys(fanart_to_dl)
