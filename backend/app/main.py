from datetime import datetime
from typing import Union
from fastapi import FastAPI, Security, HTTPException, Depends
from .core import *
from fastapi.security.api_key import APIKeyHeader
from starlette.status import HTTP_403_FORBIDDEN
from fastapi.security.api_key import APIKey

# This is the model of data for the API. Cf model.py file
from .models import (
    EnrichInputModel,
    Entry,
    HTTPValidationError,
    MessageOutputModel,
    ResultModel,
    EnrichModel
)

# Full API specifications. 
app = FastAPI(
    title='BigProfiles API Frontend Test',
    description="# Introduction\nQueste API sono state sviluppate da BigProfiles per il test tecnico FrontEnd. E' vietato il riutilizzo o la riproduzione di esse\nPer quanto riguarda l'autenticazione usare il parametro `x-api-key` all'interno dell'header ed impostare come valore `BigProfiles-API`",
    version='1.0.0'

)

## Security 
api_key_header = APIKeyHeader(name="access_token", auto_error=False)

API_KEY = "BigProfiles-API" # In a real-case scenario this code should not be hard-coded here but passed as a parameter taken from an external non-versioned file.

async def get_api_key(api_key_header: str = Security(api_key_header)):
    if api_key_header == API_KEY:
        return api_key_header   
    else:
        raise HTTPException(
            status_code=HTTP_403_FORBIDDEN, detail="Could not validate API KEY"
        )

@app.post(
    '/api/v1/ingest',
    response_model=MessageOutputModel,
    responses={
        '500': {'model': MessageOutputModel},
        '422': {'model': HTTPValidationError},
    },
)
def ingest_endpoint(
    body: EnrichInputModel,
    api_key: APIKey = Depends(get_api_key)
) -> Union[MessageOutputModel, HTTPValidationError]:
    """
    This is the ingestion endpoint. We take data, make some enrichment and post it to MongoDB.
    """

    request_dict = dict(body.__dict__) # use dict() in order to make it editable and add other fields
    response_code = ingest_data_aux(request_dict) # Enrich the request in order to get the data
    return MessageOutputModel(status_code=response_code, message="Request saved correctly.")

@app.get(
    '/api/v1/retrieve',
    response_model=ResultModel,
    responses={'422': {'model': HTTPValidationError}},
)
def retrieve_data(
    date_from: datetime, date_to: datetime = ...,
    api_key: APIKey = Depends(get_api_key)
) -> Union[ResultModel, HTTPValidationError]:
    """
    Retrieves statistics and last 10 entries for requests made in a given time interval
    """
    mongo_stats_requests, mongo_last_10_requests = retrieve_data_aux(date_from, date_to)

    # Now, convert data to the expected output format
    result = ResultModel(
        values = [
            EnrichModel(key = row['_id']['key'], creation_datetime=row['_id']['response_time_minute'], 
                        total_response_time_ms = row['total_response_time_ms'], total_requests = row['total_requests'], total_errors = row['total_errors'])
            for row in mongo_stats_requests
        ],
        logs = [
            Entry(key = row['key'], payload = row['payload'], creation_datetime = row['creation_datetime'], 
                    response_time = row['response_time'], response_code = row['response_code'] )
            for row in mongo_last_10_requests
        ]
    )
    return result