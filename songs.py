import json
import os
from pymongo import MongoClient
from bson import ObjectId
from flask import Flask, render_template, request
from math import ceil

app = Flask(__name__)

client = MongoClient()
db = client['songs_task']
song_collection = db['songs']

APP_ROOT = os.path.dirname(os.path.abspath(__file__))
APP_STATIC = os.path.join(APP_ROOT, 'static')
JSON_FILENAME = 'songs.json'
PER_PAGE = 5
ERROR_DEFAULT = "What on earth are you trying to do? Try Again."

# get all the available songs and paginate through them
@app.route('/')
@app.route('/songs/')
@app.route('/songs/<page>/')
def show_songs(all_songs = None, page = 1):
    if all_songs == None:
        all_songs = get_songs()

    total_pages = ceil(len(all_songs) / PER_PAGE)
    try:
        page = int(page)
    except:
        return render_template("index.html", page="message", message = ERROR_DEFAULT)

    if page == 0 or page > total_pages:
        page = 1

    songs = extract_per_page_data(all_songs, page, PER_PAGE)

    return render_template('index.html', songs=songs, page='songs', total_pages = total_pages, current_page = page, path = "/songs/")

# get per page data
def extract_per_page_data(data, current_page, per_page):
    total_count = len(data)

    last_item_index = per_page * current_page - 1
    first_item_index = last_item_index - per_page + 1

    new_data = []
    i = first_item_index

    while i <= last_item_index:
        if i == total_count and total_count % per_page != 0:
            break

        new_data.append(data[i])
        i += 1

    return new_data

# get the average difficulty of the songs based on level
@app.route('/songs/avg/difficulty/')
@app.route('/songs/avg/difficulty/<level>/')
def avg_difficulty(level = 0):
    try:
        level = int(level)
    except:
        return render_template('index.html', page='message', message=ERROR_DEFAULT)

    songs = get_songs()
    difficulties = []

    levels = [song['level'] for song in songs if 'level' in song]

    if level not in levels or level == 0:
        difficulties = [song['difficulty'] for song in songs if 'difficulty' in song]
        avg = round(sum(difficulties) / len(difficulties))
        response = "There are {} songs on all levels with difficulties of {} (sum is {}), and their average is rounded {}" \
            .format(len(difficulties), ', '.join(map(str, difficulties)), sum(difficulties), avg)
    else:
        for song in songs:
            if level == song['level']:
                difficulties.append(song['difficulty'])

        avg = round(sum(difficulties) / len(difficulties))
        response = "There are {} songs on the level number {}, with difficulties of {} (sum is {}), and their average is rounded {}" \
            .format(len(difficulties), level, ', '.join(map(str, difficulties)), sum(difficulties), avg)

    return render_template('index.html', page='message', message = response)

# search for songs based on artist name or the title, add pagination
@app.route('/songs/search/<message>')
@app.route('/songs/search/<message>/<page>')
def search_song(message, page = 1):
    all_searched_songs = []
    song_object = song_collection.find({"$text": {"$search": message}})
    for song in song_object:
        all_searched_songs.append(song)

    total_pages = ceil(len(all_searched_songs) / PER_PAGE)
    try:
        page = int(page)
    except:
        return render_template("index.html", page="message", message=ERROR_DEFAULT)

    if page == 0 or page > total_pages:
        page = 1

    songs = extract_per_page_data(all_searched_songs, page, PER_PAGE)

    return render_template('index.html', songs=songs, page='songs', total_pages=total_pages, current_page=page, path = "/songs/search/" + message + "/")

# add rating to a song
@app.route('/songs/rating/', methods = ['GET', 'POST'])
def rate_song():
    if request.method == 'POST':
        song_id = request.form['song_id']
        rating = request.form['rating']

        try:
            rating = int(rating)
        except:
            return render_template("index.html", page="message", message=ERROR_DEFAULT)

        songs = get_songs()

        try:
            song_data = [song for song in songs if song['_id'] == ObjectId(song_id)][0]
        except:
            return render_template("index.html", page="message", message=ERROR_DEFAULT)

        ids = [song['_id'] for song in songs]

        if ObjectId(song_id) not in ids:
            response = "Such song does not exist!"
        elif rating < 1 or rating > 5:
            response = "Rating has to be between 1 and 5!"
        else:
            add_rating(song_id, rating)
            response = "Rating {} to the song {} by {} has been added".format(rating, song_data['title'],
                                                                              song_data['artist'])
        return render_template("index.html", page="message", message=response)
    else:
        return render_template("index.html", page="rating")

def add_rating(song_id, rating):
    song_collection.update({"_id": ObjectId(song_id)}, {"$set": {"rating": rating}})

# get all the songs
def get_songs():
    songs = []
    song_object = song_collection.find()
    for song in song_object:
        songs.append(song)

    return songs

# load db from the json file, create indexes for the search
def inital_db():
    if song_collection.count() != 0:
        return True

    db_songs = []
    song_file = open(os.path.join(APP_STATIC, JSON_FILENAME), "r")
    with song_file as f:
        for line in f:
            song = json.loads(line)
            db_songs.append(song)

    song_collection.insert_many(db_songs)
    song_collection.ensure_index([('artist', 'text'),('title', 'text')])

if __name__ == '__main__':
    inital_db()
    app.run()