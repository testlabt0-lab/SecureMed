import logging

logger = logging.getLogger(__name__)

class HL7Parser:
    """
    A basic HL7 v2.x message parser for Medical Interoperability.
    Typically used to parse ADT (Admit/Discharge/Transfer) or ORU (Observation Result) messages.
    """
    
    @staticmethod
    def parse_message(hl7_message_text):
        """
        Parses a raw HL7 message into a dictionary.
        This is a basic structural parser.
        """
        parsed_data = {}
        segments = hl7_message_text.strip().split('\r') # HL7 segment separator is \r
        
        for segment in segments:
            if not segment:
                continue
            fields = segment.split('|')
            segment_type = fields[0]
            
            parsed_data[segment_type] = fields
            
        return parsed_data

    @staticmethod
    def process_oru_message(parsed_data):
        """
        Process Observation Result (ORU) message to update lab results.
        """
        if 'MSH' not in parsed_data or 'PID' not in parsed_data or 'OBX' not in parsed_data:
            raise ValueError("Invalid ORU message. Missing MSH, PID, or OBX segments.")
            
        # Extract patient ID from PID segment
        # In a real scenario, this involves complex mapping
        patient_mrn = parsed_data['PID'][3]
        
        # Extract observation results
        obx_fields = parsed_data['OBX']
        observation_id = obx_fields[3]
        observation_value = obx_fields[5]
        units = obx_fields[6]
        
        logger.info(f"HL7 Processed ORU: MRN {patient_mrn}, Test {observation_id}, Result {observation_value} {units}")
        
        return {
            "patient_mrn": patient_mrn,
            "test_id": observation_id,
            "result": observation_value,
            "units": units
        }
