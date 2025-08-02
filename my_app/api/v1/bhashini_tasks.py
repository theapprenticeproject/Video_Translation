import frappe, base64, requests

def lang_detection(audio_filename: str, processed_docname: str):
    processed_doc=frappe.get_doc("Processed Video Info", processed_docname)
    input_path=frappe.get_site_path("public", "files", "original", audio_filename)
    print("input path for lang detection: ", input_path)
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
        print("detected language is : ",detected_lang)
        processed_doc.status=f"Language Detected: {detected_lang}, Dubbing Pending"
        processed_doc.save(ignore_permissions=True)
        frappe.db.commit()

        return detected_lang

    except requests.RequestException as e:
        processed_doc.status="Language Detection Failed -  Requests"
        processed_doc.save(ignore_permissions=True)
        frappe.db.commit()

        frappe.throw("Error Calling Detection API: ", e)

    except Exception as e:
        processed_doc.status="Language Detection Failed -  exception"
        processed_doc.save(ignore_permissions=True)
        frappe.db.commit()
        frappe.throw("Error with exception : ", e)
    
# for non-hindi native languages
def STS_pipe(audio_filename: str, lang_code: str, src_lang_code: str, processed_docname: str):
    processed_doc=frappe.get_doc("Processed Video Info", processed_docname)
    input_path=frappe.get_site_path("public", "files", "original" ,audio_filename)
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

        processed_doc.status=f"Translated speech generated from {lang_code} to {src_lang_code}"
        processed_doc.save(ignore_permissions=True)
        frappe.db.commit()

    except requests.RequestException as err:
        processed_doc.status="Speech to Speech Translation failed -  Requests"
        processed_doc.save(ignore_permissions=True)
        frappe.db.commit()
        frappe.throw("Error Calling Speech to Speech Translation Pipeline : ", err)
    
    except Exception as e:
        processed_doc.status="STS Translation failed"
        processed_doc.save(ignore_permissions=True)
        frappe.db.commit()
        frappe.throw("Exception occured during STS :", e)
