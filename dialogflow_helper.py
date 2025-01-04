import os
from google.cloud import dialogflow_v2 as dialogflow
from google.protobuf.json_format import MessageToDict

class DialogflowHelper:
    """
    A helper class to manage Dialogflow ES sessions, send queries, and parse responses.
    """

    def __init__(self, project_id, session_id, language_code="en"):
        """
        Initialize Dialogflow session.

        :param project_id: GCP project ID associated with the Dialogflow agent
        :param session_id: Unique ID for a given dialog session
        :param language_code: Language code, e.g. 'en'
        """
        self.project_id = project_id
        self.session_id = session_id
        self.language_code = language_code

        # Create a Sessions client
        self.sessions_client = dialogflow.SessionsClient()

        # Generate the session path
        self.session_path = self.sessions_client.session_path(
            project=project_id, session=session_id
        )

    def detect_intent_texts(self, text_list):
        """
        Sends a list of text queries to Dialogflow and returns the list of response objects.

        :param text_list: List of user text inputs
        :return: List of response objects from Dialogflow
        """
        responses = []
        for text in text_list:
            response = self._detect_intent_text(text)
            responses.append(response)
        return responses

    def _detect_intent_text(self, text):
        """
        Internal method to send a single text query to Dialogflow.

        :param text: User input text
        :return: Dialogflow DetectIntentResponse object
        """
        # Build the text input
        text_input = dialogflow.TextInput(text=text, language_code=self.language_code)
        query_input = dialogflow.QueryInput(text=text_input)

        # Make API request
        response = self.sessions_client.detect_intent(
            request={"session": self.session_path, "query_input": query_input}
        )
        return response

    def get_fulfillment_text(self, response):
        """
        Extract the fulfillment text from a DetectIntentResponse.

        :param response: Dialogflow DetectIntentResponse object
        :return: Fulfillment text (str)
        """
        return response.query_result.fulfillment_text

    def get_intent_name(self, response):
        """
        Extract the matched intent name from a DetectIntentResponse.

        :param response: Dialogflow DetectIntentResponse object
        :return: Intent name (str)
        """
        return response.query_result.intent.display_name

    def get_confidence(self, response):
        """
        Extract the intent detection confidence from a DetectIntentResponse.

        :param response: Dialogflow DetectIntentResponse object
        :return: Confidence score (float)
        """
        return response.query_result.intent_detection_confidence

    def get_parameters(self, response):
        """
        Extract parameters from a DetectIntentResponse.

        :param response: Dialogflow DetectIntentResponse object
        :return: Dictionary of parameters
        """
        return dict(response.query_result.parameters)

    def get_output_contexts(self, response):
        """
        Extract output contexts from a DetectIntentResponse.

        :param response: Dialogflow DetectIntentResponse object
        :return: List of context objects
        """
        return response.query_result.output_contexts

    def detect_intent_with_contexts(self, text, context_name, lifespan_count=5, parameters=None):
        """
        Detect intent for text with an input context.

        :param text: The user query text
        :param context_name: The context name to set
        :param lifespan_count: Number of conversational turns for which the context remains active
        :param parameters: Parameters for the context
        :return: Dialogflow DetectIntentResponse object
        """
        if context_name:
            context_path = self.sessions_client.context_path(
                self.project_id, self.session_id, context_name
            )
            context = dialogflow.Context(
                name=context_path,
                lifespan_count=lifespan_count,
                parameters=dialogflow.types.struct_pb2.Struct(fields=parameters) if parameters else None
            )
            # Create the context
            context_client = dialogflow.ContextsClient()
            context_client.create_context(parent=self.session_path, context=context)

        # Send text
        response = self._detect_intent_text(text)
        return response

    def clear_contexts(self):
        """
        Clears all active contexts for the current session.
        """
        context_client = dialogflow.ContextsClient()
        context_list = context_client.list_contexts(parent=self.session_path)
        for ctx in context_list:
            context_client.delete_context(name=ctx.name)

    def detect_intent_with_event(self, event_name, parameters=None):
        """
        Trigger a custom event to Dialogflow rather than sending user text.

        :param event_name: Name of the event
        :param parameters: Parameters to pass along with the event
        :return: Dialogflow DetectIntentResponse object
        """
        event_input = dialogflow.EventInput(name=event_name, 
                                            language_code=self.language_code,
                                            parameters=dialogflow.types.struct_pb2.Struct(
                                                fields=parameters) if parameters else None)
        query_input = dialogflow.QueryInput(event=event_input)
        response = self.sessions_client.detect_intent(
            request={"session": self.session_path, "query_input": query_input}
        )
        return response

    def parse_rich_responses(self, response):
        """
        Convert the entire response.query_result into a dict
        and then parse text and payload messages.
        
        :param response: Dialogflow DetectIntentResponse
        :return: dict -> {"text": [...], "payload": [...]}
        """
        
                
        
        # Convert the entire query_result to a dictionary
        query_result_dict = MessageToDict(
            response.query_result._pb,
            # including_default_value_fields=True,    # Optional, to include fields with default values
            # always_print_fields_with_no_presence=True, # Optional, to include fields with no data
            # preserving_proto_field_name=True        # Optional, keeps the original proto field names
        )

        text_responses = []
        payload_responses = []

        # Safely extract the fulfillment messages from the dict
        fulfillment_messages = query_result_dict.get("fulfillmentMessages", [])

        for fm in fulfillment_messages:
            # If there's a text field, it's typically fm["text"]["text"] = [ "some text" ]
            if "text" in fm:
                # "text" is an object that may contain {"text": ["Hello world", ...]}
                text_list = fm["text"].get("text", [])
                text_responses.extend(text_list)

            # If there's a payload field, it's a dictionary
            if "payload" in fm:
                payload_responses.append(fm["payload"])

        return {
            "text": text_responses,
            "payload": payload_responses
        }

    def _struct_to_dict(self, struct_obj):
        """
        Helper method to convert a Struct object to a Python dict.

        :param struct_obj: google.protobuf.struct_pb2.Struct
        :return: dict
        """
        return {k: self._value_to_python(v) for k, v in struct_obj.fields.items()}

    def _value_to_python(self, value_obj):
        """
        Convert a google.protobuf.struct_pb2.Value to a Python object.
        """
        kind = value_obj.WhichOneof("kind")
        if kind == "null_value":
            return None
        elif kind == "number_value":
            return value_obj.number_value
        elif kind == "string_value":
            return value_obj.string_value
        elif kind == "bool_value":
            return value_obj.bool_value
        elif kind == "struct_value":
            return self._struct_to_dict(value_obj.struct_value)
        elif kind == "list_value":
            return [self._value_to_python(v) for v in value_obj.list_value.values]
        else:
            return None