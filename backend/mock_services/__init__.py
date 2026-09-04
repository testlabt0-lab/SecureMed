"""
Mock services for SecureMed development and testing.

Provides simulated external services for development when real services
are not available (AI service, Redis, etc.).
"""
from unittest .mock import MagicMock ,patch 
from django .conf import settings 


def get_ai_service_mock ():
    """Get a mock AI service that responds with predefined responses."""

    class MockAIService :
        def __init__ (self ):
            self .base_url =getattr (settings ,'AI_SERVICE_URL','http://127.0.0.1:8100')
            self .call_count =0 
            self .success_count =0 

        def ask (self ,question ,history =None ,context =None ):
            """Mock AI assistant response."""
            self .call_count +=1 
            self .success_count +=1 

            # Comment_581
            responses =[
            "شكراً لاستفسارك. أنا نموذج ذكاء اصطناعي ويمكنني مساعدتك في الأسئلة الطبية العامة.",
            "بناءً على معلوماتك، أوصي بمراجعة طبيب متخصص للحالة المذكورة.",
            "يمكنك تجربة تغيير نمط حياتك تشمل alimentation صحية وممارسة الرياضة regularly.",
            "تذكر أن تلتزم بالجرعات الموصوفة من أي دواء وتستشارة pharmacist إذا كان لديك شك.",
            ]

            import random 
            response_text =random .choice (responses )

            return {
            'response':response_text ,
            'source':'mock_ai_service',
            'timestamp':self .call_count ,
            'model':'mock-model',
            }

        def case_summary (self ,case_data ):
            """Mock clinical case summary generation."""
            self .call_count +=1 
            return {
            'summary':'ملخص الحالة الطبية: المريض يعاني من أعراض تنفسية خفيفة. يوصي بالعلاج الدوائي الراحي والمتابعة.',
            'disclaimer':'هذا ملخص آلي ولا يغني عن التشخيص الطبي professional.',
            'source':'mock_ai_service',
            }

        def health (self ):
            """Health check."""
            return {'status':'healthy','service':'Mock AI Service'}

    return MockAIService ()


def patch_ai_service ():
    """Patch the AI service settings to use mock service."""
    from unittest .mock import patch as _patch 

    # Comment_582
    from apps .ai .views import AIAssistantAskView ,AIAssistantHealthView 
    original_ask =AIAssistantAskView .post 
    original_health =AIAssistantHealthView .get 

    mock_service =get_ai_service_mock ()

    def mock_ask (self ,request ):
    # Comment_583
        from rest_framework import status 
        return Response (mock_service .ask (
        question =str (request .data .get ('question')or ''),
        history =request .data .get ('history'),
        context =request .data .get ('context'),
        ),status =status .HTTP_200_OK )

    def mock_health (self ,request ):
        from rest_framework import status 
        return Response (mock_service .health (),status =status .HTTP_200_OK )

    AIAssistantAskView .post =mock_ask 
    AIAssistantHealthView .get =mock_health 

    return mock_service 