import numpy as np
import pandas as pd
import pickle
from tmdbv3api import Movie
from flask import Flask, render_template, request, redirect, url_for
import os
import requests
from tmdbv3api import TMDb
import json
import requests
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import bs4 as bs
import urllib.request
from flask_sqlalchemy import SQLAlchemy

tmdb = TMDb()
tmdb.api_key = '0a9ccd023e870968b2f2563dd65ae3ab'
game_api_key = 'c6bd8758ad1a41ebaac21c0f23bcc7eb'
tmdb_movie = Movie()


# PEOPLE_FOLDER = os.path.join('static', 'people_photo')

filename = 'nlp_model.pkl'
clf = pickle.load(open(filename, 'rb'))
vectorizer = pickle.load(open('tranform.pkl','rb'))

app = Flask(__name__)


movies_list = pickle.load(open('movies_data.pkl', 'rb'))
# taking movies data for autocomplete
movies_list = movies_list['movie_title'].values

#taking the movies and similarity data and using it to find similar movies
movies = pickle.load(open('movies_data.pkl', 'rb'))
similarity = pickle.load(open('similarity.pkl', 'rb'))

def recommend(movie):
    movie_index = movies[movies['movie_title'] == movie].index[0]
    distances = similarity[movie_index]
    movies_list = sorted(list(enumerate(distances)), reverse=True, key=lambda x:x[1])[1:11]
    
    recommend_movies = []
    for i in movies_list:
        recommend_movies.append(movies.iloc[i[0]].movie_title)

    return recommend_movies


#video games part
games_list = pickle.load(open('games_data.pkl', 'rb'))
game_titles = games_list['name'].values

games = pickle.load(open('games_data.pkl', 'rb'))
similarity_games = pickle.load(open('games_sim.pkl', 'rb'))

def recommend_game(game):
    game_index = games[games['name'] == game].index[0]
    distances = similarity_games[game_index]
    games_list = sorted(list(enumerate(distances)), reverse=True, key=lambda x:x[1])[1:11]
    
    recommended_games = []
    for i in games_list:
        recommended_games.append(games.iloc[i[0]]['name'])

    return recommended_games


#database for login/signup part
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

class user(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80))
    email = db.Column(db.String(120))
    password = db.Column(db.String(80))

@app.route('/', methods=['GET', 'POST'])
def logreg(): 
    if request.method == "POST":
        rname = request.form.get('rname', None)
        rmail = request.form.get('rmail', None)
        rpass = request.form.get('rpass', None)

        register = user(username = rname, email = rmail, password = rpass)
        print(rname)
        db.session.add(register)
        db.session.commit()

        sname = request.form.get('sname', None)
        spass = request.form.get('spass', None)
        
        login = user.query.filter_by(username=sname, password=spass).first()
        print(login)
        if login is not None:
            print('hehe boi')
            return redirect(url_for("mvg"))

    return render_template('login.html')
    

@app.route('/choose', methods=['GET', 'POST'])
def mvg(): 
    return render_template("index1.html")

#base page for the movie recommender system
@app.route('/home', methods=['GET', 'POST'])
def fetchTrendingMovies():      
    if request.method == "POST":
        searchedMovie = request.form['movie']
        # print(movie_name)
        # print(searchedMovie)
    # get the link
    #link for trending movies taken from tmdb api documentation
    response = requests.get(
        'https://api.themoviedb.org/3/trending/movie/week?api_key={}'.format(tmdb.api_key))
    data = response.json()
    # print(data)
    posters = []  # since we are fetching multiple posters, we need a list to append paths of all posters
    titles = []
    
    if data['results']:
        # iterating over results key of the json and getting poster_path from it
        for i in range(0, len(data['results'])):
            poster = "https://image.tmdb.org/t/p/original/" + \
                data['results'][i]['poster_path']
            title = data['results'][i]['title']
            posters.append(poster)  # appending to the list
            titles.append(title)
            # creating a dictionary to show poster and movie title more easily on webpage
            trendingMoviesDetails = {
                posters[i]: titles[i] for i in range(len(posters))}
    # rendering on home.html with help of jinja
    return render_template('home.html', trendingMoviesDetails=trendingMoviesDetails, movies_list=movies_list)

#here I Have created 4 searchedResult routes depending on what I need
#First there are movies that I will search in the search box and those movies are also available in my movies variable(At line 36)
#I am using /searchedResult route for this. I have all data in this route, information about searched movie, cast, reviews and similar recommended movies

#for the second case I am using /searchedResult2. This is mainly created for the recommended movies cards, when clicking on them it will
#take value of that button and use it to direct to show information about the movie same as /searchedResult

#for the third case, I m using /searchedResult3. This is needed for those trending movies that I m displaying at home page. Since I don't 
#have information related to similar movies of those trending movies, I have to skip the recommended movies dictionary in this route and 
#show other information only. It shows "NO RECORD FOUND FOR SIMILAR MOVIES" in this case

#the fourth case(/searchedResult4) is similar to /searchedResult3. The only difference is that it works for searched Movies entered in
#the search bar rather than the card button. In this case also we dont have similar movies hence it also shows "NO RECORD FOUND FOR SIMILAR MOVIES".

#for fourth case in jinja template in home.html and searchedAndRecommended.html, i have added a if condition to check if movie that I am
#searching is in the movies_list variable or not. If its there then call /searchedResult(because I already have information about similar movies)
#else run the /searchedResult4 which does not take recommend function into account


@app.route('/searchedResult', methods=['GET', 'POST'])
def searchedAndRecommended():
    #reading the movie name typed in input bar using request.form method
    searchedMovie = ""
    if request.method == "POST":
        searchedMovie = request.form['movie']
        # print(searchedMovie)
    
    # getting the id of the searched movie
    result = tmdb_movie.search(searchedMovie)
    movie_id = result[0].id
    # getting that movie's data using its id and api key
    response = requests.get(
        'https://api.themoviedb.org/3/movie/{}?api_key={}'.format(movie_id, tmdb.api_key))
    data = response.json() #converting data to json

    # getting the required information about movie from the json
    searchedTitle = ""
    if data['original_title']:
        searchedTitle = data['original_title']

    searchedPoster = ""
    if data['poster_path']:
        searchedPoster = "https://image.tmdb.org/t/p/original/" + \
            data['poster_path']

    searchedOverview = ""
    if data['overview']:
        searchedOverview = data['overview']

    searchedVoteAverage = ""
    if data['vote_average']:
        searchedVoteAverage = data['vote_average']

    searchedVoteCount = ""
    if data['vote_count']:
        searchedVoteCount = data['vote_count']

    searchedGenres = []
    if data['genres']:
        for i in range(0, len(data['genres'])):
            searchedGenres.append(data['genres'][i]['name'])

    searchedReleaseDate = ""
    if data['release_date']:
        searchedReleaseDate = data['release_date']

    searchedRuntime = ""
    if data['runtime']:
        searchedRuntime = data['runtime']

    searchedStatus = ""
    if data['status']:
        searchedStatus = data['status']

    imdb_id = ""
    if data['imdb_id']:
        imdb_id = data['imdb_id']

    # now fetching the information of casts
    castResponse = requests.get(
        'https://api.themoviedb.org/3/movie/{}/credits?api_key={}&language=en-US'.format(movie_id, tmdb.api_key))
    castData = castResponse.json()
    # print(castData)
    # for key, value in castData.items():
    #     print("Key:")
    #     print(key)
    searchedActorNames = []
    searchedActorCharacters = []
    searchedActorIds = []
    searchedActorImages = []

    individualCastNames = []
    individualCastBirthdays = []
    individualCastPlaceOfBirths = []
    individualCastBiographies = []
    individualCastImages = []
    individualActorIds = []

    #here I'm just fetching information about 13 actors as it takes lot of time to fetch information 'bout each and every actor
    if castData['cast']:
        for i in range(0, 13):
            searchedActorNames.append(castData['cast'][i]['name'])
            searchedActorCharacters.append(castData['cast'][i]['character'])
            searchedActorIds.append(castData['cast'][i]['id']) #we will use this id later to get further information about each actor that would be presented in a bootstrap modal on html page
            if castData['cast'][i]['profile_path']:
                searchedActorImage = "https://image.tmdb.org/t/p/original/" + \
                    castData['cast'][i]['profile_path']
                searchedActorImages.append(searchedActorImage)

    #creating a dictionary so that data can be fetched with more ease using jinja template, we did that for length of searchActorImages because the json doesn't have images for few actors 
    #but it wont make much difference for us in most of the movies because we are presenting info of just 13 actors, and they might be popular faces, so their image might exist on database
    casts = {searchedActorNames[i]: [searchedActorIds[i], searchedActorCharacters[i],
                                     searchedActorImages[i]] for i in range(len(searchedActorImages))}

#looping over the ids previously stored to get further information about each actor that would be shown in bootstrap modal
    for id in searchedActorIds:
        individualCastResponse = requests.get(
            'https://api.themoviedb.org/3/person/{}?api_key={}&language=en-US'.format(id, tmdb.api_key))
        individualCastDetails = individualCastResponse.json()
        # individualCastName = ""
        # individualCastBirthday = ""
        # individualCastPlaceOfBirth = ""
        # individualCastBiography = ""

        # if individualCastDetails['name']:
        individualCastNames.append(individualCastDetails['name'])
        individualCastBirthdays.append(individualCastDetails['birthday'])
        individualCastPlaceOfBirths.append(
            individualCastDetails['place_of_birth'])
        individualCastBiographies.append(individualCastDetails['biography'])
        if individualCastDetails['profile_path']:
            individualCastImage = "https://image.tmdb.org/t/p/original/" + \
                individualCastDetails['profile_path']
            individualCastImages.append(individualCastImage)
        individualActorIds.append(id)

#again creating another dictionary for easier access of data
    cast_details = {individualCastNames[i]: [individualActorIds[i], individualCastImages[i], individualCastBirthdays[i],
                                             individualCastPlaceOfBirths[i], individualCastBiographies[i]] for i in range(len(individualCastImages))}


    sauce = urllib.request.urlopen('https://www.imdb.com/title/{}/reviews?ref_=tt_ov_rt'.format(imdb_id)).read()
    soup = bs.BeautifulSoup(sauce,'lxml')
    soup_result = soup.find_all("div",{"class":"text show-more__control"})

    reviews_list = [] # list of reviews
    reviews_status = [] # list of comments (good or bad)
    for reviews in soup_result:
        if reviews.string:
            reviews_list.append(reviews.string)
            # passing the review to our model
            movie_review_list = np.array([reviews.string])
            movie_vector = vectorizer.transform(movie_review_list)
            pred = clf.predict(movie_vector)
            reviews_status.append('Good' if pred else 'Bad')

    # combining reviews and comments into a dictionary
    movie_reviews = {reviews_list[i]: reviews_status[i] for i in range(len(reviews_list))}     

    recommended_movies = recommend(searchedMovie)

    rec_titles = []
    rec_posters = []
    for i in recommended_movies:
        # print(i)
        recommended_movie = tmdb_movie.search(i)
        recommended_movie_id = recommended_movie[0].id
    # getting that movie's data using its id and api key
        rec_response = requests.get(
        'https://api.themoviedb.org/3/movie/{}?api_key={}'.format(recommended_movie_id, tmdb.api_key))
        rec_data = rec_response.json()
        
        if rec_data['original_title']:
            rec_title = rec_data['original_title']
            rec_titles.append(rec_title)

        if data['poster_path']:
            rec_poster = "https://image.tmdb.org/t/p/original/" + \
            rec_data['poster_path']
            rec_posters.append(rec_poster)


    recMoviesDetails = {
                rec_posters[i]: rec_titles[i] for i in range(len(rec_posters))}


        

    return render_template('searchedAndRecommended.html', searchedPoster=searchedPoster, searchedTitle=searchedTitle,
                           searchedOverview=searchedOverview, searchedVoteAverage=searchedVoteAverage, searchedVoteCount=searchedVoteCount,
                           searchedGenres=searchedGenres, searchedReleaseDate=searchedReleaseDate, searchedRuntime=searchedRuntime, searchedStatus=searchedStatus,
                           movies_list=movies_list, searchedActorNames=searchedActorNames, searchedActorCharacters=searchedActorCharacters, casts=casts,
                           cast_details=cast_details, movie_reviews=movie_reviews, recMoviesDetails=recMoviesDetails,
                           searchedMovie=searchedMovie)


@app.route('/searchedResult2', methods=['GET', 'POST'])
def searchedAndRecommended2():
    #reading the movie name typed in input bar using request.method, since here it's a card in this case so I have to get the movie title
    #from line 78 of home.html
    searchedMovie = ""
    if request.method == "POST":
        name = request.form['title']
        # print(searchedMovie)
    
    # getting the id of the searched movie
    result = tmdb_movie.search(name)
    movie_id = result[0].id
    # getting that movie's data using its id and api key
    response = requests.get(
        'https://api.themoviedb.org/3/movie/{}?api_key={}'.format(movie_id, tmdb.api_key))
    data = response.json() #converting data to json

    # getting the required information about movie from the json
    searchedTitle = ""
    if data['original_title']:
        searchedTitle = data['original_title']

    searchedPoster = ""
    if data['poster_path']:
        searchedPoster = "https://image.tmdb.org/t/p/original/" + \
            data['poster_path']

    searchedOverview = ""
    if data['overview']:
        searchedOverview = data['overview']

    searchedVoteAverage = ""
    if data['vote_average']:
        searchedVoteAverage = data['vote_average']

    searchedVoteCount = ""
    if data['vote_count']:
        searchedVoteCount = data['vote_count']

    searchedGenres = []
    if data['genres']:
        for i in range(0, len(data['genres'])):
            searchedGenres.append(data['genres'][i]['name'])

    searchedReleaseDate = ""
    if data['release_date']:
        searchedReleaseDate = data['release_date']

    searchedRuntime = ""
    if data['runtime']:
        searchedRuntime = data['runtime']

    searchedStatus = ""
    if data['status']:
        searchedStatus = data['status']

    imdb_id = ""
    if data['imdb_id']:
        imdb_id = data['imdb_id']

    # now fetching the information of casts
    castResponse = requests.get(
        'https://api.themoviedb.org/3/movie/{}/credits?api_key={}&language=en-US'.format(movie_id, tmdb.api_key))
    castData = castResponse.json()
    # print(castData)
    # for key, value in castData.items():
    #     print("Key:")
    #     print(key)
    searchedActorNames = []
    searchedActorCharacters = []
    searchedActorIds = []
    searchedActorImages = []

    individualCastNames = []
    individualCastBirthdays = []
    individualCastPlaceOfBirths = []
    individualCastBiographies = []
    individualCastImages = []
    individualActorIds = []

    #here I'm just fetching information about 13 actors as it takes lot of time to fetch information 'bout each and every actor
    if castData['cast']:
        for i in range(0, 13):
            searchedActorNames.append(castData['cast'][i]['name'])
            searchedActorCharacters.append(castData['cast'][i]['character'])
            searchedActorIds.append(castData['cast'][i]['id']) #we will use this id later to get further information about each actor that would be presented in a bootstrap modal on html page
            if castData['cast'][i]['profile_path']:
                searchedActorImage = "https://image.tmdb.org/t/p/original/" + \
                    castData['cast'][i]['profile_path']
                searchedActorImages.append(searchedActorImage)

    #creating a dictionary so that data can be fetched with more ease using jinja template, we did that for length of searchActorImages because the json doesn't have images for few actors 
    #but it wont make much difference for us in most of the movies because we are presenting info of just 13 actors, and they might be popular faces, so their image might exist on database
    casts = {searchedActorNames[i]: [searchedActorIds[i], searchedActorCharacters[i],
                                     searchedActorImages[i]] for i in range(len(searchedActorImages))}

#looping over the ids previously stored to get further information about each actor that would be shown in bootstrap modal
    for id in searchedActorIds:
        individualCastResponse = requests.get(
            'https://api.themoviedb.org/3/person/{}?api_key={}&language=en-US'.format(id, tmdb.api_key))
        individualCastDetails = individualCastResponse.json()
        # individualCastName = ""
        # individualCastBirthday = ""
        # individualCastPlaceOfBirth = ""
        # individualCastBiography = ""

        # if individualCastDetails['name']:
        individualCastNames.append(individualCastDetails['name'])
        individualCastBirthdays.append(individualCastDetails['birthday'])
        individualCastPlaceOfBirths.append(
            individualCastDetails['place_of_birth'])
        individualCastBiographies.append(individualCastDetails['biography'])
        if individualCastDetails['profile_path']:
            individualCastImage = "https://image.tmdb.org/t/p/original/" + \
                individualCastDetails['profile_path']
            individualCastImages.append(individualCastImage)
        individualActorIds.append(id)

#again creating another dictionary for easier access of data
    cast_details = {individualCastNames[i]: [individualActorIds[i], individualCastImages[i], individualCastBirthdays[i],
                                             individualCastPlaceOfBirths[i], individualCastBiographies[i]] for i in range(len(individualCastImages))}


    sauce = urllib.request.urlopen('https://www.imdb.com/title/{}/reviews?ref_=tt_ov_rt'.format(imdb_id)).read()
    soup = bs.BeautifulSoup(sauce,'lxml')
    soup_result = soup.find_all("div",{"class":"text show-more__control"})

    reviews_list = [] # list of reviews
    reviews_status = [] # list of comments (good or bad)
    for reviews in soup_result:
        if reviews.string:
            reviews_list.append(reviews.string)
            # passing the review to our model
            movie_review_list = np.array([reviews.string])
            movie_vector = vectorizer.transform(movie_review_list)
            pred = clf.predict(movie_vector)
            reviews_status.append('Good' if pred else 'Bad')

    # combining reviews and comments into a dictionary
    movie_reviews = {reviews_list[i]: reviews_status[i] for i in range(len(reviews_list))}     

    recommended_movies = recommend(name)

    rec_titles = []
    rec_posters = []
    for i in recommended_movies:
        # print(i)
        recommended_movie = tmdb_movie.search(i)
        recommended_movie_id = recommended_movie[0].id
    # getting that movie's data using its id and api key
        rec_response = requests.get(
        'https://api.themoviedb.org/3/movie/{}?api_key={}'.format(recommended_movie_id, tmdb.api_key))
        rec_data = rec_response.json()
        
        if rec_data['original_title']:
            rec_title = rec_data['original_title']
            rec_titles.append(rec_title)

        if data['poster_path']:
            rec_poster = "https://image.tmdb.org/t/p/original/" + \
            rec_data['poster_path']
            rec_posters.append(rec_poster)


    recMoviesDetails = {
                rec_posters[i]: rec_titles[i] for i in range(len(rec_posters))}

    return render_template('searchedAndRecommended.html', searchedPoster=searchedPoster, searchedTitle=searchedTitle,
                           searchedOverview=searchedOverview, searchedVoteAverage=searchedVoteAverage, searchedVoteCount=searchedVoteCount,
                           searchedGenres=searchedGenres, searchedReleaseDate=searchedReleaseDate, searchedRuntime=searchedRuntime, searchedStatus=searchedStatus,
                           movies_list=movies_list, searchedActorNames=searchedActorNames, searchedActorCharacters=searchedActorCharacters, casts=casts,
                           cast_details=cast_details, movie_reviews=movie_reviews, recMoviesDetails=recMoviesDetails)


@app.route('/searchedResult3', methods=['GET', 'POST'])
def searchedAndRecommended3():
    #reading the movie name typed in input bar using request.method
    searchedMovie = ""
    if request.method == "POST":
        name = request.form['title']
        # print(searchedMovie)
    
    # getting the id of the searched movie
    result = tmdb_movie.search(name)
    movie_id = result[0].id
    # getting that movie's data using its id and api key
    response = requests.get(
        'https://api.themoviedb.org/3/movie/{}?api_key={}'.format(movie_id, tmdb.api_key))
    data = response.json() #converting data to json

    # getting the required information about movie from the json
    searchedTitle = ""
    if data['original_title']:
        searchedTitle = data['original_title']

    searchedPoster = ""
    if data['poster_path']:
        searchedPoster = "https://image.tmdb.org/t/p/original/" + \
            data['poster_path']

    searchedOverview = ""
    if data['overview']:
        searchedOverview = data['overview']

    searchedVoteAverage = ""
    if data['vote_average']:
        searchedVoteAverage = data['vote_average']

    searchedVoteCount = ""
    if data['vote_count']:
        searchedVoteCount = data['vote_count']

    searchedGenres = []
    if data['genres']:
        for i in range(0, len(data['genres'])):
            searchedGenres.append(data['genres'][i]['name'])

    searchedReleaseDate = ""
    if data['release_date']:
        searchedReleaseDate = data['release_date']

    searchedRuntime = ""
    if data['runtime']:
        searchedRuntime = data['runtime']

    searchedStatus = ""
    if data['status']:
        searchedStatus = data['status']

    imdb_id = ""
    if data['imdb_id']:
        imdb_id = data['imdb_id']

    # now fetching the information of casts
    castResponse = requests.get(
        'https://api.themoviedb.org/3/movie/{}/credits?api_key={}&language=en-US'.format(movie_id, tmdb.api_key))
    castData = castResponse.json()
    # print(castData)
    # for key, value in castData.items():
    #     print("Key:")
    #     print(key)
    searchedActorNames = []
    searchedActorCharacters = []
    searchedActorIds = []
    searchedActorImages = []

    individualCastNames = []
    individualCastBirthdays = []
    individualCastPlaceOfBirths = []
    individualCastBiographies = []
    individualCastImages = []
    individualActorIds = []

    #here I'm just fetching information about 13 actors as it takes lot of time to fetch information 'bout each and every actor
    if castData['cast']:
        for i in range(0, 13):
            searchedActorNames.append(castData['cast'][i]['name'])
            searchedActorCharacters.append(castData['cast'][i]['character'])
            searchedActorIds.append(castData['cast'][i]['id']) #we will use this id later to get further information about each actor that would be presented in a bootstrap modal on html page
            if castData['cast'][i]['profile_path']:
                searchedActorImage = "https://image.tmdb.org/t/p/original/" + \
                    castData['cast'][i]['profile_path']
                searchedActorImages.append(searchedActorImage)

    #creating a dictionary so that data can be fetched with more ease using jinja template, we did that for length of searchActorImages because the json doesn't have images for few actors 
    #but it wont make much difference for us in most of the movies because we are presenting info of just 13 actors, and they might be popular faces, so their image might exist on database
    casts = {searchedActorNames[i]: [searchedActorIds[i], searchedActorCharacters[i],
                                     searchedActorImages[i]] for i in range(len(searchedActorImages))}

#looping over the ids previously stored to get further information about each actor that would be shown in bootstrap modal
    for id in searchedActorIds:
        individualCastResponse = requests.get(
            'https://api.themoviedb.org/3/person/{}?api_key={}&language=en-US'.format(id, tmdb.api_key))
        individualCastDetails = individualCastResponse.json()
        # individualCastName = ""
        # individualCastBirthday = ""
        # individualCastPlaceOfBirth = ""
        # individualCastBiography = ""

        # if individualCastDetails['name']:
        individualCastNames.append(individualCastDetails['name'])
        individualCastBirthdays.append(individualCastDetails['birthday'])
        individualCastPlaceOfBirths.append(
            individualCastDetails['place_of_birth'])
        individualCastBiographies.append(individualCastDetails['biography'])
        if individualCastDetails['profile_path']:
            individualCastImage = "https://image.tmdb.org/t/p/original/" + \
                individualCastDetails['profile_path']
            individualCastImages.append(individualCastImage)
        individualActorIds.append(id)

#again creating another dictionary for easier access of data
    cast_details = {individualCastNames[i]: [individualActorIds[i], individualCastImages[i], individualCastBirthdays[i],
                                             individualCastPlaceOfBirths[i], individualCastBiographies[i]] for i in range(len(individualCastImages))}


    sauce = urllib.request.urlopen('https://www.imdb.com/title/{}/reviews?ref_=tt_ov_rt'.format(imdb_id)).read()
    soup = bs.BeautifulSoup(sauce,'lxml')
    soup_result = soup.find_all("div",{"class":"text show-more__control"})

    reviews_list = [] # list of reviews
    reviews_status = [] # list of comments (good or bad)
    for reviews in soup_result:
        if reviews.string:
            reviews_list.append(reviews.string)
            # passing the review to our model
            movie_review_list = np.array([reviews.string])
            movie_vector = vectorizer.transform(movie_review_list)
            pred = clf.predict(movie_vector)
            reviews_status.append('Good' if pred else 'Bad')

    # combining reviews and comments into a dictionary
    movie_reviews = {reviews_list[i]: reviews_status[i] for i in range(len(reviews_list))}     


    return render_template('searchedAndRecommended.html', searchedPoster=searchedPoster, searchedTitle=searchedTitle,
                           searchedOverview=searchedOverview, searchedVoteAverage=searchedVoteAverage, searchedVoteCount=searchedVoteCount,
                           searchedGenres=searchedGenres, searchedReleaseDate=searchedReleaseDate, searchedRuntime=searchedRuntime, searchedStatus=searchedStatus,
                           movies_list=movies_list, searchedActorNames=searchedActorNames, searchedActorCharacters=searchedActorCharacters, casts=casts,
                           cast_details=cast_details, movie_reviews=movie_reviews)



@app.route('/homeVG', methods=['GET', 'POST'])
def homeVG():
    response = requests.get('https://api.rawg.io/api/games?key={}'.format(game_api_key))
    data = response.json()
    for key, value in data.items():
        print("Key:")
        print(key)
    game_names = []
    background_images = []
    for i in range(0, len(data['results'])):
        game_names.append(data['results'][i]['name'])
        background_images.append(data['results'][i]['background_image'])
        # game_names.append('GTA V')

    print("name:", data['results'][1]['name'])
    
    for j in game_names:
        print(j)

    popularGamesDetails = {
                background_images[i]: game_names[i] for i in range(len(background_images))}


    return render_template('homeVG.html', popularGamesDetails=popularGamesDetails, game_titles=game_titles)


@app.route('/searchedVG', methods=['GET', 'POST'])
def searchedVG():
    searchedGame=''
    if request.method == "POST":
        searchedGame = request.form['game']
    vg = 'Grand Theft Auto V'
    vg_id = games_list[games_list.name==searchedGame]['id'].values
    vg_id = vg_id.item(0)
    # print('id is: ', vg_id)

    responseVG = requests.get('https://api.rawg.io/api/games/{}?key={}'.format(vg_id, game_api_key))
    dataVG = responseVG.json()

    tommy = "/static/people_photo/leomord.jpg"

    searchedGameName = ''
    if dataVG['name']:
        searchedGameName = dataVG['name']

    searchedGameRating = ''
    if dataVG['rating']:
        searchedGameRating = dataVG['rating']

    searchedGameRatingsCount = ''
    if dataVG['ratings_count']:
        searchedGameRatingsCount = dataVG['ratings_count']

    searchedGameGenres = []
    if dataVG['genres']:
        for i in range(0, len(dataVG['genres'])):
            searchedGameGenres.append(dataVG['genres'][i]['name'])

    # searchedGameBG = ''
    if dataVG['background_image']:
        tommy = dataVG['background_image']
    else:
        tommy = dataVG['background_image_additional']

    searchedGameDesc = ''
    if dataVG['description']:
        searchedGameDesc = dataVG['description']

    searchedGameReleaseDate = ''
    if dataVG['released']:
        searchedGameReleaseDate = dataVG['released']

    searchedGamePlayTime = ''
    if dataVG['playtime']:
        searchedGamePlayTime = dataVG['playtime']

    searchedGamePlatforms = []
    if dataVG['platforms']:
        for i in range(0, len(dataVG['platforms'])):
            searchedGamePlatforms.append(dataVG['platforms'][i]['platform']['name'])


    searchedGameDesc = searchedGameDesc.replace('<p>', '') 
    searchedGameDesc = searchedGameDesc.replace('</p>', '') 
    searchedGameDesc = searchedGameDesc.replace('<br />', '') 
    searchedGameDesc = searchedGameDesc.replace('&#39;', '\'') 
    searchedGameDesc = searchedGameDesc.replace('<h3>', '')
    searchedGameDesc = searchedGameDesc.replace('</h3>', '') 

    


    devResponse = requests.get('https://api.rawg.io/api/games/{}/development-team?key={}'.format(vg_id, game_api_key))
    devData = devResponse.json()

    devId = []
    if devData['results']:
        for i in range(0, len(devData['results'])):
            devId.append(devData['results'][i]['id'])

    devName = []
    if devData['results']:
        for i in range(0, len(devData['results'])):
            devName.append(devData['results'][i]['name'])

    devPic = []
    if devData['results']:
        for i in range(0, len(devData['results'])):
            if devData['results'][i]['image']:
                devPic.append(devData['results'][i]['image'])
            else:
                devPic.append(devData['results'][i]['image_background'])

    devs = {devName[i]: [devId[i], devPic[i]] for i in range(len(devPic))}

    clickedDevName = []
    clickedDevId = []
    clickedDevPic = []
    clickedDevGames = []
    clickedDevBio = []
    clickedDevRating = []
    for id in devId:
        searchedDevResponse = requests.get('https://api.rawg.io/api/creators/{}?key={}'.format(id, game_api_key))
        searchedDevData = searchedDevResponse.json()

        clickedDevId.append(id)

        if searchedDevData['name']:
            clickedDevName.append(searchedDevData['name'])
        
        if searchedDevData['image']:
            clickedDevPic.append(searchedDevData['image'])
        else:
            clickedDevPic.append(searchedDevData['image_background'])

        if searchedDevData['description']:
            clickedDevBio.append(searchedDevData['description'])

        if searchedDevData['games_count']:
            clickedDevGames.append(searchedDevData['games_count'])

        if searchedDevData['rating']:
            clickedDevRating.append(searchedDevData['rating'])

    clickedDevBio = [i.replace('<p>', '') for i in clickedDevBio]
    clickedDevBio = [i.replace('</p>', '') for i in clickedDevBio]
    clickedDevBio = [i.replace('<h3>', '') for i in clickedDevBio]
    clickedDevBio = [i.replace('</h3>', '') for i in clickedDevBio]
    clickedDevBio = [i.replace('&#39;', '\'') for i in clickedDevBio]

    dev_details = {clickedDevName[i]: [clickedDevId[i], clickedDevPic[i], clickedDevGames[i],
                                             clickedDevRating[i], clickedDevBio[i]] for i in range(len(clickedDevPic))}

    responseSS = requests.get('https://api.rawg.io/api/games/{}/screenshots?key={}'.format(vg_id, game_api_key))
    dataSS = responseSS.json()


    gameSS = []
    if dataSS['results']:
        for i in range(0, len(dataSS['results'])):
            gameSS.append(dataSS['results'][i]['image'])

    recommended_games = recommend_game(searchedGame)

    recVgTitle = []
    recVgBg = []

    for i in recommended_games:
        rec_vg_id = games_list[games_list.name==i]['id'].values
        rec_vg_id = rec_vg_id.item(0)

        recResponseVG = requests.get('https://api.rawg.io/api/games/{}?key={}'.format(rec_vg_id, game_api_key))
        recDataVG = recResponseVG.json()


        if recDataVG['name']:
            recVgTitle.append(recDataVG['name'])

        
        searchedGameBG = ''
        if recDataVG['background_image']:
            recVgBg.append(recDataVG['background_image'])

        recGamesDetails = {
                recVgBg[i]: recVgTitle[i] for i in range(len(recVgBg))}
        print(tommy)

    return render_template('searchedVideoGame.html', searchedGameName=searchedGameName, searchedGameRating=searchedGameRating, 
    searchedGameRatingsCount=searchedGameRatingsCount, searchedGameGenres=searchedGameGenres, searchedGameReleaseDate=searchedGameReleaseDate,
    searchedGamePlayTime=searchedGamePlayTime, searchedGamePlatforms=searchedGamePlatforms, searchedGameDesc=searchedGameDesc
    , game_titles=game_titles, devs=devs, dev_details=dev_details, gameSS=gameSS, recGamesDetails=recGamesDetails, tommy=tommy)

@app.route('/searchedVG2', methods=['GET', 'POST'])
def searchedVG2():
    clickedName=''
    if request.method == "POST":
        clickedName = request.form['game_name']
    vg = 'Grand Theft Auto V'
    vg_id = games_list[games_list.name==clickedName]['id'].values
    vg_id = vg_id.item(0)
    # print('id is: ', vg_id)

    responseVG = requests.get('https://api.rawg.io/api/games/{}?key={}'.format(vg_id, game_api_key))
    dataVG = responseVG.json()


    tommy = "/static/people_photo/leomord.jpg"

    searchedGameName = ''
    if dataVG['name']:
        searchedGameName = dataVG['name']

    searchedGameRating = ''
    if dataVG['rating']:
        searchedGameRating = dataVG['rating']

    searchedGameRatingsCount = ''
    if dataVG['ratings_count']:
        searchedGameRatingsCount = dataVG['ratings_count']

    searchedGameGenres = []
    if dataVG['genres']:
        for i in range(0, len(dataVG['genres'])):
            searchedGameGenres.append(dataVG['genres'][i]['name'])

    searchedGameBG = ''
    if dataVG['background_image']:
        tommy = dataVG['background_image']
    elif dataVG['background_image_additional']:
        tommy = dataVG['background_image_additional']

    searchedGameDesc = ''
    if dataVG['description']:
        searchedGameDesc = dataVG['description']

    searchedGameReleaseDate = ''
    if dataVG['released']:
        searchedGameReleaseDate = dataVG['released']

    searchedGamePlayTime = ''
    if dataVG['playtime']:
        searchedGamePlayTime = dataVG['playtime']

    searchedGamePlatforms = []
    if dataVG['platforms']:
        for i in range(0, len(dataVG['platforms'])):
            searchedGamePlatforms.append(dataVG['platforms'][i]['platform']['name'])


    searchedGameDesc = searchedGameDesc.replace('<p>', '') 
    searchedGameDesc = searchedGameDesc.replace('</p>', '') 
    searchedGameDesc = searchedGameDesc.replace('<br />', '') 
    searchedGameDesc = searchedGameDesc.replace('&#39;', '\'') 
    searchedGameDesc = searchedGameDesc.replace('<h3>', '')
    searchedGameDesc = searchedGameDesc.replace('</h3>', '') 

    


    devResponse = requests.get('https://api.rawg.io/api/games/{}/development-team?key={}'.format(vg_id, game_api_key))
    devData = devResponse.json()

    devId = []
    if devData['results']:
        for i in range(0, len(devData['results'])):
            devId.append(devData['results'][i]['id'])

    devName = []
    if devData['results']:
        for i in range(0, len(devData['results'])):
            devName.append(devData['results'][i]['name'])

    devPic = []
    if devData['results']:
        for i in range(0, len(devData['results'])):
            if devData['results'][i]['image']:
                devPic.append(devData['results'][i]['image'])
            else:
                devPic.append(devData['results'][i]['image_background'])

    devs = {devName[i]: [devId[i], devPic[i]] for i in range(len(devPic))}

    clickedDevName = []
    clickedDevId = []
    clickedDevPic = []
    clickedDevGames = []
    clickedDevBio = []
    clickedDevRating = []
    for id in devId:
        searchedDevResponse = requests.get('https://api.rawg.io/api/creators/{}?key={}'.format(id, game_api_key))
        searchedDevData = searchedDevResponse.json()

        clickedDevId.append(id)

        if searchedDevData['name']:
            clickedDevName.append(searchedDevData['name'])
        
        if searchedDevData['image']:
            clickedDevPic.append(searchedDevData['image'])
        else:
            clickedDevPic.append(searchedDevData['image_background'])

        if searchedDevData['description']:
            clickedDevBio.append(searchedDevData['description'])

        if searchedDevData['games_count']:
            clickedDevGames.append(searchedDevData['games_count'])

        if searchedDevData['rating']:
            clickedDevRating.append(searchedDevData['rating'])

    clickedDevBio = [i.replace('<p>', '') for i in clickedDevBio]
    clickedDevBio = [i.replace('</p>', '') for i in clickedDevBio]
    clickedDevBio = [i.replace('<h3>', '') for i in clickedDevBio]
    clickedDevBio = [i.replace('</h3>', '') for i in clickedDevBio]
    clickedDevBio = [i.replace('&#39;', '\'') for i in clickedDevBio]

    dev_details = {clickedDevName[i]: [clickedDevId[i], clickedDevPic[i], clickedDevGames[i],
                                             clickedDevRating[i], clickedDevBio[i]] for i in range(len(clickedDevPic))}

    responseSS = requests.get('https://api.rawg.io/api/games/{}/screenshots?key={}'.format(vg_id, game_api_key))
    dataSS = responseSS.json()


    gameSS = []
    if dataSS['results']:
        for i in range(0, len(dataSS['results'])):
            gameSS.append(dataSS['results'][i]['image'])

    recommended_games = recommend_game(clickedName)

    recVgTitle = []
    recVgBg = []

    for i in recommended_games:
        rec_vg_id = games_list[games_list.name==i]['id'].values
        rec_vg_id = rec_vg_id.item(0)

        recResponseVG = requests.get('https://api.rawg.io/api/games/{}?key={}'.format(rec_vg_id, game_api_key))
        recDataVG = recResponseVG.json()


        if recDataVG['name']:
            recVgTitle.append(recDataVG['name'])

        
        searchedGameBG = ''
        if recDataVG['background_image']:
            recVgBg.append(recDataVG['background_image'])

        recGamesDetails = {
                recVgBg[i]: recVgTitle[i] for i in range(len(recVgBg))}
        
       

    return render_template('searchedVideoGame.html', searchedGameName=searchedGameName, searchedGameRating=searchedGameRating, 
    searchedGameRatingsCount=searchedGameRatingsCount, searchedGameGenres=searchedGameGenres, searchedGameReleaseDate=searchedGameReleaseDate,
    searchedGamePlayTime=searchedGamePlayTime, searchedGamePlatforms=searchedGamePlatforms, searchedGameDesc=searchedGameDesc
    , game_titles=game_titles, devs=devs, dev_details=dev_details, gameSS=gameSS, recGamesDetails=recGamesDetails, tommy=tommy)

@app.route('/searchedVG3', methods=['GET', 'POST'])
def searchedVG3():
    clickedName=''
    if request.method == "POST":
        clickedName = request.form['game_name']
    vg = 'Grand Theft Auto V'
    vg_id = games_list[games_list.name==clickedName]['id'].values
    vg_id = vg_id.item(0)
    # print('id is: ', vg_id)

    responseVG = requests.get('https://api.rawg.io/api/games/{}?key={}'.format(vg_id, game_api_key))
    dataVG = responseVG.json()

    tommy = "/static/people_photo/leomord.jpg"

    searchedGameName = ''
    if dataVG['name']:
        searchedGameName = dataVG['name']

    searchedGameRating = ''
    if dataVG['rating']:
        searchedGameRating = dataVG['rating']

    searchedGameRatingsCount = ''
    if dataVG['ratings_count']:
        searchedGameRatingsCount = dataVG['ratings_count']

    searchedGameGenres = []
    if dataVG['genres']:
        for i in range(0, len(dataVG['genres'])):
            searchedGameGenres.append(dataVG['genres'][i]['name'])

    searchedGameBG = ''
    if dataVG['background_image']:
        tommy = dataVG['background_image']
    else:
        tommy = dataVG['background_image_additional']

    searchedGameDesc = ''
    if dataVG['description']:
        searchedGameDesc = dataVG['description']

    searchedGameReleaseDate = ''
    if dataVG['released']:
        searchedGameReleaseDate = dataVG['released']

    searchedGamePlayTime = ''
    if dataVG['playtime']:
        searchedGamePlayTime = dataVG['playtime']

    searchedGamePlatforms = []
    if dataVG['platforms']:
        for i in range(0, len(dataVG['platforms'])):
            searchedGamePlatforms.append(dataVG['platforms'][i]['platform']['name'])


    searchedGameDesc = searchedGameDesc.replace('<p>', '') 
    searchedGameDesc = searchedGameDesc.replace('</p>', '') 
    searchedGameDesc = searchedGameDesc.replace('<br />', '') 
    searchedGameDesc = searchedGameDesc.replace('&#39;', '\'') 
    searchedGameDesc = searchedGameDesc.replace('<h3>', '')
    searchedGameDesc = searchedGameDesc.replace('</h3>', '') 

    


    devResponse = requests.get('https://api.rawg.io/api/games/{}/development-team?key={}'.format(vg_id, game_api_key))
    devData = devResponse.json()

    devId = []
    if devData['results']:
        for i in range(0, len(devData['results'])):
            devId.append(devData['results'][i]['id'])

    devName = []
    if devData['results']:
        for i in range(0, len(devData['results'])):
            devName.append(devData['results'][i]['name'])

    devPic = []
    if devData['results']:
        for i in range(0, len(devData['results'])):
            if devData['results'][i]['image']:
                devPic.append(devData['results'][i]['image'])
            else:
                devPic.append(devData['results'][i]['image_background'])

    devs = {devName[i]: [devId[i], devPic[i]] for i in range(len(devPic))}

    clickedDevName = []
    clickedDevId = []
    clickedDevPic = []
    clickedDevGames = []
    clickedDevBio = []
    clickedDevRating = []
    for id in devId:
        searchedDevResponse = requests.get('https://api.rawg.io/api/creators/{}?key={}'.format(id, game_api_key))
        searchedDevData = searchedDevResponse.json()

        clickedDevId.append(id)

        if searchedDevData['name']:
            clickedDevName.append(searchedDevData['name'])
        
        if searchedDevData['image']:
            clickedDevPic.append(searchedDevData['image'])
        else:
            clickedDevPic.append(searchedDevData['image_background'])

        if searchedDevData['description']:
            clickedDevBio.append(searchedDevData['description'])

        if searchedDevData['games_count']:
            clickedDevGames.append(searchedDevData['games_count'])

        if searchedDevData['rating']:
            clickedDevRating.append(searchedDevData['rating'])

    clickedDevBio = [i.replace('<p>', '') for i in clickedDevBio]
    clickedDevBio = [i.replace('</p>', '') for i in clickedDevBio]
    clickedDevBio = [i.replace('<h3>', '') for i in clickedDevBio]
    clickedDevBio = [i.replace('</h3>', '') for i in clickedDevBio]
    clickedDevBio = [i.replace('&#39;', '\'') for i in clickedDevBio]

    dev_details = {clickedDevName[i]: [clickedDevId[i], clickedDevPic[i], clickedDevGames[i],
                                             clickedDevRating[i], clickedDevBio[i]] for i in range(len(clickedDevPic))}

    responseSS = requests.get('https://api.rawg.io/api/games/{}/screenshots?key={}'.format(vg_id, game_api_key))
    dataSS = responseSS.json()


    gameSS = []
    if dataSS['results']:
        for i in range(0, len(dataSS['results'])):
            gameSS.append(dataSS['results'][i]['image'])

    recommended_games = recommend_game(clickedName)

    recVgTitle = []
    recVgBg = []

    for i in recommended_games:
        rec_vg_id = games_list[games_list.name==i]['id'].values
        rec_vg_id = rec_vg_id.item(0)

        recResponseVG = requests.get('https://api.rawg.io/api/games/{}?key={}'.format(rec_vg_id, game_api_key))
        recDataVG = recResponseVG.json()


        if recDataVG['name']:
            recVgTitle.append(recDataVG['name'])

        
        searchedGameBG = ''
        if recDataVG['background_image']:
            recVgBg.append(recDataVG['background_image'])

        recGamesDetails = {
                recVgBg[i]: recVgTitle[i] for i in range(len(recVgBg))}
        
        

    return render_template('searchedVideoGame.html', searchedGameName=searchedGameName, searchedGameRating=searchedGameRating, 
    searchedGameRatingsCount=searchedGameRatingsCount, searchedGameGenres=searchedGameGenres, searchedGameReleaseDate=searchedGameReleaseDate,
    searchedGamePlayTime=searchedGamePlayTime, searchedGamePlatforms=searchedGamePlatforms, searchedGameDesc=searchedGameDesc
    , game_titles=game_titles, devs=devs, dev_details=dev_details, gameSS=gameSS, recGamesDetails=recGamesDetails, tommy=tommy)

if __name__ == "__main__":
    app.run(debug=True)


