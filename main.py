#!/usr/bin/python3
# -*- coding: utf-8 -*-
#Beth Zabinski wrote this

from tweepy import API
from tweepy import AppAuthHandler
from tweepy import OAuthHandler
from tweepy import Stream
from tweepy.streaming import StreamListener
import sys
import re
import json
from pymongo import MongoClient

def main(argv):

    global posts
    global consumer_key
    global consumer_secret
    global access_token
    global access_secret

    mode = -1
    geocode = False

    for arg in argv:
        if arg == "--test":
            mode = 0
        elif arg == "--cont":
            mode = 1
        elif arg == "--nyc":
            geocode = True
        elif arg == "--help":
            print("Usage: main.py (--test|--cont) [--nyc]")
            print("--test is used for a one time test of past tweets")
            print("--cont is used for continuous search of Twitter stream")
            print("--nyc will enable geocoding of tweets to NYC (default is everywhere)")
            return
        else:
            print("Not a valid argument: " + arg)
            return

    if mode < 0:
        print("Need to set a mode. Use --help to see commands")
        return

    #Opens the file containing the consumer key and secret associated with the Twitter app
    try:
        consumer_file = open('secrets.txt', 'r', encoding='utf-8')
        #[:-1] gets rid of the newline character
        consumer_key = consumer_file.readline()[:-1]
        consumer_secret = consumer_file.readline()[:-1]
        access_token = consumer_file.readline()[:-1]
        access_secret = consumer_file.readline()[:-1]
        consumer_file.close()
    except:
        print("Error opening/reading secrets.txt")
        print("Did you create the file and enter the info in the correct format?")
        raise

    if mode == 0:
        auth = AppAuthHandler(consumer_key, consumer_secret)
        auth.apply_auth()
        runTest(auth, geocode)
    elif mode == 1:
        #db stuff
        client = MongoClient()
        db = client.twitter
        posts = db.posts
        #tweepy stuff
        auth = OAuthHandler(consumer_key, consumer_secret)
        auth.set_access_token(access_token, access_secret)
        runCont(auth, geocode)
    return

def runTest(auth, geocode):
    searchText = "flash mob OR mobs OR flashmob"
    nycGeoCode = "40.714353,-74.00597299999998,20km"

    api = API(auth)

    if geocode is True:
        tweets = api.search(searchText, geocode=nycGeoCode, lang="en", rpp="100")
    else:
        #Note: This may cause a too many requests Twitter error
        tweets = api.search(searchText, lang="en", rpp="100")

    #basically find tweets that match the search criteria
    users_list = []
    i = 0
    for tweet in tweets:
        print(i)
        i = i + 1
        name = tweet.user.name.encode("utf-8", errors='ignore')
        user_id = tweet.user.id #.encode("utf-8", errors='ignore')
        tweet_text = tweet.text.encode("utf-8", errors='ignore')

        #Ignore users we have already checked
        if (users_list.count(name)):
            continue
        else:
            users_list.append(name)

        #Add number of times the user has used the search criteria in the past
        tweet_count = 0
        retweet_count = 0
        users_tweets = api.user_timeline(id=user_id, count="500")
        for users_tweet in users_tweets:
            if (re.search(r'flash[ ]?mob[s]?', users_tweet.text, flags=re.IGNORECASE)):
                tweet_count = tweet_count + 1
                #Check how many times the past tweets have been retweeted
                retweet_count = retweet_count + len(api.retweets(id=users_tweet.id))

        #Checks how many followers this person has
        followers_count = len(api.followers_ids(id=user_id))

        print("User ID:       ", user_id)
        print("Tweet count:   ", tweet_count)
        print("retweet_count: ", retweet_count)
        print()

    return

def runCont(auth, geocode):
    l = StdOutListener()
    stream = Stream(auth, l)

    if geocode is True:
        stream.filter(track=['flashmob', 'flashmobs', 'flash mob', 'flash mobs'], location=nycGeoCode)
    else:
        stream.filter(track=['flashmob', 'flashmobs', 'flash mob', 'flash mobs'])

    return

class StdOutListener(StreamListener):
    def on_data(self, data):
        print("Found something")
        try:
            decoded = json.loads(data)
        except:
            print("JSON couldn't be loaded")

        name = decoded['user']['name'].encode("utf-8", errors='ignore')
        user_id = decoded['user']['id'] #.encode("utf-8", errors='ignore')
        tweet_text = decoded['text'].encode("utf-8", errors='ignore')

        #Add number of times the user has used the search criteria in the past
        tweet_count = 0
        retweet_count = 0

        try:
            auth = AppAuthHandler(consumer_key, consumer_secret)
            auth.apply_auth()
            api = API(auth)

            users_tweets = api.user_timeline(id=user_id, count="500")
            for users_tweet in users_tweets:
                if (re.search(r'flash[ ]?mob[s]?', users_tweet.text, flags=re.IGNORECASE)):
                    tweet_count = tweet_count + 1
                    #Check how many times the past tweets have been retweeted
                    retweet_count = retweet_count + len(api.retweets(id=users_tweet.id))

            #Checks how many followers this person has
            followers_count = len(api.followers_ids(id=user_id))

        except:
            print("Something went wrong when gathering more data")
            return True

        print("User ID:       ", user_id)
        print("Tweet count:   ", tweet_count)
        print("retweet_count: ", retweet_count)
        print()

        post = {"user_id": user_id,
                "tweet": tweet_text.decode(encoding='utf-8',errors='ignore'),
                "tweet_count": tweet_count,
                "retweet_count": retweet_count}

        posts.insert(post)

        return True
    def on_error(self, status):
        print(status)

if __name__ == "__main__":
   main(sys.argv[1:])
