# example_usage.py

import os
from os import path, environ
from dotenv import load_dotenv
from dialogflow_helper import DialogflowHelper
import time

load_dotenv()

def main():
    # Set your Google Application Credentials
    # The JSON file you downloaded from Google Cloud console that holds your service account key
    # os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "service_account.json"
    # OR
    # Set up google cli tool, adc with `gcloud auth application-default login`

    project_id = os.getenv("DIALOGFLOW_PROJECT_ID")
    session_id = os.getenv("DIALOGFLOW_SESSION_ID")
    language_code = "en"

    df_helper = DialogflowHelper(project_id, session_id, language_code)

    # Example: Single text query
    user_input = "Hi"
    
    # Time the response
    
    start_time = time.time()
    single_response = df_helper._detect_intent_text(user_input)
    end_time = time.time()
    
    print("Single Response:", f'[Time: {end_time - start_time}]', single_response)
    
    
    print("[Intent]", df_helper.get_intent_name(single_response))
    print("[Fulfillment Text]:", df_helper.get_fulfillment_text(single_response))
    
    rich_payloads = df_helper.parse_rich_responses(single_response)
    print("Rich Payloads:", rich_payloads)
    

    # Example: Multiple text queries
    # texts = ["Hello", "What can you do?", "Thanks, bye!"]
    # batch_responses = df_helper.detect_intent_texts(texts)
    # for i, res in enumerate(batch_responses):
    #     print(f"User: {texts[i]}")
    #     print("Response:", df_helper.get_fulfillment_text(res))

    # Example: Event-based trigger
    # event_response = df_helper.detect_intent_with_event("WELCOME_EVENT")
    # print("Event response text:", df_helper.get_fulfillment_text(event_response))

    # Example: Add a context and send text
    # We'll add a context named 'test_context' that lasts 5 turns
    # context_response = df_helper.detect_intent_with_contexts(
    #     text="I have a question about my order",
    #     context_name="test_context",
    #     lifespan_count=5,
    #     parameters={"orderNumber": "123456"}  # e.g. pass order number as a parameter
    # )
    # print("Contextful response:", df_helper.get_fulfillment_text(context_response))

    # Parse rich responses
    # rich_payloads = df_helper.parse_rich_responses(context_response)
    # print("Rich Payloads:", rich_payloads)

    # Clear contexts
    df_helper.clear_contexts()

if __name__ == "__main__":
    main()