# Lark - DialogFlow ES Bot

Building a chatbot for Lark powered by DialogFlow ES.

More details can be found at the Medium [story]().

## Setup
### Google SDK
Note that in order for the Google DialogFlow API to work, you must set up the python dialogflow sdk. Which can be done in a few steps.
1. Install [google cloud cli](https://cloud.google.com/sdk/docs/install#linux)
2. Set up [ADC](https://cloud.google.com/docs/authentication/set-up-adc-local-dev-environment) with google cloud cli 
3. Run `gcloud auth application-default login` 
3. Work with the [api](https://cloud.google.com/dialogflow/es/docs/quick/api)

### Python
This is built using Python 3.12. Below is how to set up a virtual environment for the project.
1. `python -m venv venv`
2. `source venv/bin/activate`
3. `pip install -r requirements.txt`
3. To leave, `deactivate`

### Redis
Install redis to handle deduplication.
1. `apt-get update`
2. `apt-get install redis-server`
3. Check if redis is running with `redis-cli ping`. Should return `PONG`

## Project Files
- `.env.example` 
- `bot_v1` - initial app that simply echos the message recieved from the lark server
- `bot_v2` - app thatintegrates dialogflow es agent to handle messages received from lark server
- `dialogflow_helper.py` - a simple wrapper for the dialogflow python sdk
- `use_dialogflow_helper.py` - a minimum way to use the wrapper

## Run
First create the `.env` file (refer to `.env.example`), and fill out the required variables. Then run `python bot_v2.py` to start the app server. Note that the app listens to port 8000, so the server that's hosting this app must have port 8000 open.
