import frappe, base64, requests

def lang_detection(audio_filename: str):   
    input_path=frappe.get_site_path("public", "files", "original", audio_filename)
    with open(input_path, "rb") as aud_file:
        bin_aud=aud_file.read()
    aud_b64_data=base64.b64encode(bin_aud).decode("utf-8")

    try:
        headers={
            "Authorization": frappe.conf.api_auth_value,
            "Content-Type":"application/json"
        }

        body= {
            "config": {
                "serviceId": "bhashini/iitmandi/audio-lang-detection/gpu"
            },
            "audio": [
                {
                    "audioContent" : aud_b64_data
                }
            ]
        }
        
        response=requests.post("https://dhruva-api.bhashini.gov.in/services/inference/audiolangdetection", json=body, headers=headers)
        detected_lang=response.json()["output"][0]["langPrediction"][0]["langCode"]
        print(detected_lang)
        return detected_lang
        
    except requests.RequestException as e:
        frappe.throw("Error Calling Detection API: ", e)

    
# for non-hindi native languages
def STS_pipe(audio_filename: str, lang_code: str, src_lang_code: str):
    input_path=frappe.get_site_path("public", "files", audio_filename)
    with open(input_path, "rb") as f:
        b=f.read()
    b64_aud=base64.b64encode(b).decode("utf-8")

    output_path=frappe.get_site_path("public", "files", "processed", f"sts_{audio_filename}")
    payload={
        "pipelineTasks": [
            {
                "taskType": "asr",
                "config": {
                    "language": {
                        "sourceLanguage": lang_code
                    },
                    "serviceId": "ai4bharat/whisper-medium-en--gpu--t4",
                    "audioFormat": "flac",
                    "samplingRate": 16000
                }
            },
            {
                "taskType": "translation",
                "config": {
                    "language": {
                        "sourceLanguage": lang_code,
                        "targetLanguage": src_lang_code
                    },
                    "serviceId": "ai4bharat/indictrans-v2-all-gpu--t4"
                }
            },
            {
                "taskType": "tts",
                "config": {
                    "language": {
                        "sourceLanguage": src_lang_code
                    },
                    "serviceId": "Bhashini/IITM/TTS",
                    "gender": "male",
                    "samplingRate": 8000
                }
            }
        ],
        "inputData": {
            "audio": [
                {
                    "audioContent": b64_aud
                }
            ]
        }
    }

    try:
        headers={
            "Authorization": frappe.conf.api_auth_value,
            "Content-Type":"application/json"
        }

        response=requests.post("https://dhruva-api.bhashini.gov.in/services/inference/pipeline", json=payload, headers=headers)
        b64_output=response.json()["pipelineResponse"][2]["audio"][0]["audioContent"]
        with open(output_path, "wb") as fo:
            decoded_aud=base64.b64decode(b64_output)
            fo.write(decoded_aud)

    except requests.RequestException as err:
        frappe.throw("Error Calling Speech to Speech Translation Pipeline : ", err)
