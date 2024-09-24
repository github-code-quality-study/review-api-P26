import nltk
from nltk.sentiment.vader import SentimentIntensityAnalyzer
from nltk.corpus import stopwords
from urllib.parse import parse_qs, urlparse
import json
import pandas as pd
from datetime import datetime
import uuid
import os
from typing import Callable, Any
from wsgiref.simple_server import make_server

nltk.download('vader_lexicon', quiet=True)
nltk.download('punkt', quiet=True)
nltk.download('averaged_perceptron_tagger', quiet=True)
nltk.download('stopwords', quiet=True)

adj_noun_pairs_count = {}
sia = SentimentIntensityAnalyzer()
stop_words = set(stopwords.words('english'))

reviews = pd.read_csv('data/reviews.csv').to_dict('records')

class ReviewAnalyzerServer:
    def __init__(self) -> None:
        # This method is a placeholder for future initialization logic
        pass

    def analyze_sentiment(self, review_body):
        sentiment_scores = sia.polarity_scores(review_body)
        return sentiment_scores

    def __call__(self, environ: dict[str, Any], start_response: Callable[..., Any]) -> bytes:
        """
        The environ parameter is a dictionary containing some useful
        HTTP request information such as: REQUEST_METHOD, CONTENT_LENGTH, QUERY_STRING,
        PATH_INFO, CONTENT_TYPE, etc.
        """

        if environ["REQUEST_METHOD"] == "GET":
            # Create the response body from the reviews and convert to a JSON byte string
            response_body = json.dumps(reviews, indent=2).encode("utf-8")
            
            # Write your code here
            # 1. Extract the query parameters from the environ dictionary
            # 2. Filter the reviews based on the query parameters
            # 3. Return the filtered reviews as a JSON byte string
            query_string = environ["QUERY_STRING"]
            query_params = parse_qs(query_string)

            #extract path info
            path = environ["PATH_INFO"]
        

            #extract query parameters
            location=query_params.get("location", [""])[0]
            start_date=query_params.get("start_date", [""])[0]
            end_date=query_params.get("end_date", [""])[0]

            filtered_reviews = reviews
            #filter reviews based on location
            if location:
                filtered_reviews = [review for review in filtered_reviews if review["Location"] == location]

            #filter reviews based on start_date on filtered reviews
            if start_date:
                start_date = datetime.strptime(start_date, "%Y-%m-%d")
                filtered_reviews = [review for review in filtered_reviews if datetime.strptime(review["Timestamp"], "%Y-%m-%d %H:%M:%S") >= start_date]

            #filter reviews based on end_date on filtered_reviews
            if end_date:
                end_date = datetime.strptime(end_date, "%Y-%m-%d")
                filtered_reviews = [review for review in filtered_reviews if datetime.strptime(review["Timestamp"], "%Y-%m-%d %H:%M:%S") <= end_date]
            #get sentiment scores for each review
            sentimented_reviews = []
            for review in filtered_reviews:
                review["sentiment"] = self.analyze_sentiment(review["ReviewBody"])
                sentimented_reviews.append(review)
            
            #sort sentimented reviews in descending order based on compound value in sentiment 
            sentimented_reviews = sorted(sentimented_reviews, key=lambda x: x["sentiment"]["compound"], reverse=True)

            #convert sentimented reviews to json
            response_body = json.dumps(sentimented_reviews, indent=2).encode("utf-8")


            # Set the appropriate response headers
            start_response("200 OK", [
            ("Content-Type", "application/json"),
            ("Content-Length", str(len(response_body)))
             ])
            
            return [response_body]


        if environ["REQUEST_METHOD"] == "POST":
            # Write your code here
            # 1. Extract the request body from the environ dictionary
            
            # extract ReviewBody and Location 
            request_body_size = int(environ.get('CONTENT_LENGTH', 0))
            request_body = environ['wsgi.input'].read(request_body_size)
            
            #prase the request body
            post_parms=parse_qs(request_body.decode("utf-8"))
            review_body=post_parms.get("ReviewBody", [""])[0]
            location=post_parms.get("Location", [""])[0]

            # Define the allowed locations
            ALLOWED_LOCATIONS = {
                "Albuquerque, New Mexico",
                "Carlsbad, California",
                "Chula Vista, California",
                "Colorado Springs, Colorado",
                "Denver, Colorado",
                "El Cajon, California",
                "El Paso, Texas",
                "Escondido, California",
                "Fresno, California",
                "La Mesa, California",
                "Las Vegas, Nevada",
                "Los Angeles, California",
                "Oceanside, California",
                "Phoenix, Arizona",
                "Sacramento, California",
                "Salt Lake City, Utah",
                "San Diego, California",
                "Tucson, Arizona"
            }
            
            #check if location is allowed
            if location and location not in ALLOWED_LOCATIONS:
                response_body = json.dumps({"error": "Location not allowed"}).encode("utf-8")
                start_response("400 Bad Request", [
                    ("Content-Type", "application/json"),
                    ("Content-Length", str(len(response_body)))
                ])
                return [response_body]

            #add a Timestamp and reviewid  if the review was added 

            if review_body and location:
                reviewid=str(uuid.uuid4())
                timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                review = {
                    "ReviewId": reviewid,
                    "ReviewBody": review_body,
                    "Location": location,
                    "Timestamp": timestamp
                    
                }
                #add new reivew to the reviews list
                reviews.append(review)
                #convert   new review to json
                response_body = json.dumps(review, indent=2).encode("utf-8")
                # Set the appropriate response headers
                start_response("201 Created", [
                    ("Content-Type", "application/json"),
                    ("Content-Length", str(len(response_body)))
                ])

                return [response_body]
            
            response_body = json.dumps({"error": "ReviewBody and Location are required"}).encode("utf-8")
            start_response("400 Bad Request", [
                ("Content-Type", "application/json"),
                ("Content-Length", str(len(response_body)))
            ])
            return [response_body]
            
            

            
            

if __name__ == "__main__":
    app = ReviewAnalyzerServer()
    port = os.environ.get('PORT', 8000)
    with make_server("", port, app) as httpd:
        print(f"Listening on port {port}...")
        httpd.serve_forever()
