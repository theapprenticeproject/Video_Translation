import frappe, subprocess, os, base64, requests

@frappe.whitelist()  
def audio_extraction(filename: str):
    input_path=frappe.get_site_path("public", "files", filename)
    if not os.path.exists(input_path):
        frappe.throw(f"{filename} not found")

    output_file=f"processed_video_aud.wav"
    output_path=frappe.get_site_path("public", "files", output_file)

    cmd=["ffmpeg", "-i", input_path, "-acodec", "pcm_s16le", "-ar", "16000", "-ac", "1", output_path]

    try:
        subprocess.run(cmd, text=True, check=True)
        return f"files/{output_file}"
    except subprocess.CalledProcessError as e:
        frappe.log_error(f"Ffmpeg error: {e}")
        frappe.throw("Video-audio extraction error")



@frappe.whitelist()
def lang_detection(filename: str):   
    input_path=frappe.get_site_path("public", "files", filename)
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
        print(response.json()["output"][0]["langPrediction"][0]["langCode"])
        
    except requests.RequestException as e:
        frappe.throw("Error Calling Detection API: ", e)

    
# for non-hindi native languages
@frappe.whitelist()
def STS_pipe(audio_file: str, lang_code: str, src_lang_code: str):
    input_path=frappe.get_site_path("public", "files", audio_file)
    with open(input_path, "rb") as f:
        b=f.read()
    b64_aud=base64.b64encode(b).decode("utf-8")

    output_path=frappe.get_site_path("public", "files", "david2_hi2.wav")
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
