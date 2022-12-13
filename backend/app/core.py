import random
import datetime
import pymongo
import threading
import os

from datetime import datetime, timedelta


MONGO_URL = os.environ["MONGODB_URL"]
MAX_BULK_INSERT = 1000 # after 1000 requests, we flush the buffer and bulk insert them.
NUMBER_LOGS_TO_RETURN = 10 # Number of requests to return in log section in retrieve response.


# Connection to MongoDB. We create and use a "requests" collection.
_mongo_client = pymongo.MongoClient(MONGO_URL)
_mongo_database = _mongo_client["main"]
_requests_collection = _mongo_database["requests"]

# We keep a list of requests to bulk insert

_buffer_requests_to_bulk_insert = []
_buffer_lock = threading.Lock()

def retrieve_data_aux(date_from, date_to):
    """
    Auxiliary method for retrieve API
    Provide stats and last 10 requests in selected period
    """

    # First, we need to flush the buffer in order to get all data correctly
    with _buffer_lock:
        if len(_buffer_requests_to_bulk_insert) > 0:
            _flush_buffer_to_mongo()


    # Then, we get the two data we need. First, the stats on the requests
    mongo_stats_requests = _requests_collection.aggregate([
        {
            '$match': {
                'creation_datetime': {'$gte': date_from, '$lte': date_to}
            }
        },
        {
            '$group': {
                '_id': {'key': '$key', 'response_time_minute': '$response_time_minute' },
                'total_response_time_ms': {'$sum': '$response_time'},
                'total_requests': { '$sum' : 1 },
                'total_errors': {'$sum': '$count_error'}
            }
        }
    ])

    # Then, the logs: last 10 requests
    mongo_last_10_requests = _requests_collection.aggregate([
        {
            '$match': {
                'creation_datetime': {'$gte': date_from, '$lte': date_to}
            }
        },
        {
            '$sort': {'creation_datetime': -1}
        },
        {
            '$limit': NUMBER_LOGS_TO_RETURN
        }
    ])

    return mongo_stats_requests, mongo_last_10_requests

def ingest_data_aux(request_dict):
    """
    Auxiliary method for ingestion API.
    Takes a dictionary with key and payload, enrich with additional data and adds it to mongo. 
    """
    response_time = random.randint(10,50)
    is_error = random.random() < 0.1
    response_code = 500 if is_error else 200
    request_timestamp = datetime.utcnow() # utcnow must be used and not now, as from pymongo documentation

    request_dict.update({'creation_datetime': request_timestamp,
                        'response_time': response_time,
                        'response_code': response_code,
                        'count_error' : 1 if is_error else 0, # This is to simplify the further "nb_errors" stat to return.
                        'response_time_minute': _round_dt(request_timestamp, 1)})
    
    _add_request_buffer_insert_mongo(request_dict)
    return response_code

## Private methods

def _add_request_buffer_insert_mongo(request_dict):
    """
    Add the request to a list, insert the list only if we have more than 1000 elements
    """
    with _buffer_lock:
        _buffer_requests_to_bulk_insert.append(request_dict)
        if len(_buffer_requests_to_bulk_insert) >= MAX_BULK_INSERT :
            _flush_buffer_to_mongo()

def _flush_buffer_to_mongo():
    """
    Inserts all requests in the buffer to mongo, and clears the buffer
    """
    try:   
        _requests_collection.insert_many(_buffer_requests_to_bulk_insert)
        _buffer_requests_to_bulk_insert.clear()
    except:
        print("ERROR while inserting data in mongo")


def _round_dt(dt, delta):
    """
    Round to lowest minute
    """
    return dt - timedelta(minutes=0,
                             seconds=dt.second,
                             microseconds=dt.microsecond)