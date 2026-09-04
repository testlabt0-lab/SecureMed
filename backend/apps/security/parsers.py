import bleach 
from rest_framework .parsers import JSONParser 

class SanitizedJSONParser (JSONParser ):
    """
    Parses JSON-encoded data and sanitizes all string values using Bleach
    to prevent Stored XSS.
    """
    def parse (self ,stream ,media_type =None ,parser_context =None ):
        parsed_data =super ().parse (stream ,media_type ,parser_context )
        return self ._sanitize_data (parsed_data )

    def _sanitize_data (self ,data ):
        if isinstance (data ,dict ):
            return {k :self ._sanitize_data (v )for k ,v in data .items ()}
        elif isinstance (data ,list ):
            return [self ._sanitize_data (item )for item in data ]
        elif isinstance (data ,str ):
        # Comment_348
            return bleach .clean (
            data ,
            tags =bleach .sanitizer .ALLOWED_TAGS ,
            attributes =bleach .sanitizer .ALLOWED_ATTRIBUTES ,
            strip =True 
            )
        return data 
