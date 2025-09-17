import frappe, base64, requests, subprocess, os

def lang_detection(audio_filename: str, processed_docname: str):
    processed_doc=frappe.get_doc("Processed Video Info", processed_docname)
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
def STS_pipe(video_filename: str, audio_filename: str, src_lang_code: str, tar_lang_code: str, processed_docname: str):
    languageCodes={
        "Marathi" : "mr",
        "Punjabi" : "pa"
    }
    tar_lang_code=languageCodes[tar_lang_code]

    processed_doc=frappe.get_doc("Processed Video Info", processed_docname)
    input_path=frappe.get_site_path("public", "files", "original" ,audio_filename)
    with open(input_path, "rb") as f:
        b=f.read()
    b64_aud=base64.b64encode(b).decode("utf-8")

    output_path=frappe.get_site_path("public", "files", "processed", f"sts_{audio_filename}")
    input_videopath=frappe.get_site_path("public", "files", "original", video_filename)
    output_videopath=frappe.get_site_path("public", "files", "processed", f"sts_{video_filename}")
    payload={
        "pipelineTasks": [
            {
                "taskType": "asr",
                "config": {
                    "language": {
                        "sourceLanguage": "hi"
                    },
                    "serviceId": "ai4bharat/conformer-hi-gpu--t4",
                    "audioFormat": "flac",
                    "samplingRate": 16000
                }
            },
            {
                "taskType": "translation",
                "config": {
                    "language": {
                        "sourceLanguage": "hi",
                        "targetLanguage": tar_lang_code
                    },
                    "serviceId": "ai4bharat/indictrans-v2-all-gpu--t4"
                }
            },
            {
                "taskType": "tts",
                "config": {
                    "language": {
                        "sourceLanguage": tar_lang_code
                    },
                    "serviceId": "ai4bharat/indic-tts-coqui-indo_aryan-gpu--t4",
                    "gender": "female",
                    "samplingRate": 16000
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
        if os.path.exists(output_path):
            subprocess.run(["ffmpeg", "-nostdin", "-i", input_videopath, "-i", output_path, "-c:v", "copy", "-c:a", "aac", "-map", "0:v:0", "-map", "1:a:0", output_videopath])
            processed_doc.localized_vid=f"/files/processed/sts_{video_filename}"
            # processed_doc.save(ignore_permissions=True)
            # frappe.db.commit()
        else:
            print("No output path found - cant run SUBPROCESS call")

        processed_doc.status=f"Translated speech generated from {src_lang_code} to {tar_lang_code}"
        processed_doc.save(ignore_permissions=True)
        frappe.db.commit()
        return {
            "audio_filename": f"sts_{audio_filename}",
            "audio_filepath": f"/files/processed/sts_{audio_filename}",
            "tar_lang_code": tar_lang_code
        }

    except requests.RequestException as err:
        processed_doc.status="Speech to Speech Translation failed -  Requests"
        processed_doc.save(ignore_permissions=True)
        frappe.db.commit()
        print(f"Error calling STS translation pipeline : {err}")
        frappe.throw("Error Calling Speech to Speech Translation Pipeline : ", err)
    
    except Exception as e:
        processed_doc.status="STS Translation failed"
        processed_doc.save(ignore_permissions=True)
        frappe.db.commit()
        print(f"exception occured during sts: {e}")
        frappe.throw(f"Exception occured during STS: {e}")
