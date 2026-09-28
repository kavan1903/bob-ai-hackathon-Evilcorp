import os
from google.api_core.client_options import ClientOptions
from google.cloud import documentai

def process_document(
    file_path: str,
    mime_type: str,
    project_id: str = "686953960628",
    location: str = "us",
    processor_id: str = "4ce30a024132547"
) -> dict:
    """
    Processes a document using Google Cloud Document AI.
    """
    # You must set the GOOGLE_APPLICATION_CREDENTIALS environment variable.
    # If it is not set, this will fail.
    
    opts = ClientOptions(api_endpoint=f"{location}-documentai.googleapis.com")
    client = documentai.DocumentProcessorServiceClient(client_options=opts)
    
    name = client.processor_path(project_id, location, processor_id)

    # Read the file into memory
    with open(file_path, "rb") as image:
        image_content = image.read()

    raw_document = documentai.RawDocument(content=image_content, mime_type=mime_type)
    request = documentai.ProcessRequest(name=name, raw_document=raw_document)
    
    try:
        result = client.process_document(request=request)
        document = result.document
        
        # Extract the full text and any extracted entities (fields)
        text = document.text
        entities = []
        for entity in document.entities:
            entities.append({
                "type": entity.type_,
                "mention_text": entity.mention_text,
                "confidence": entity.confidence
            })
            
        return {
            "success": True,
            "text": text,
            "entities": entities
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }
