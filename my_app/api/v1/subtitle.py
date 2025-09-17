import frappe, math, os
from groq import Groq

client=Groq(
    api_key=frappe.conf.groq_api_key
)

def vtt_generate(audio_filename: str, lang_code: str, processed_docname: str):
    processed_doc=frappe.get_doc("Processed Video Info", processed_docname)
    audio_file_path=frappe.get_site_path("public", "files", "processed", audio_filename)
    # formatting time in HH:MM:SS.mmm ; 'm' denoting milliseconds
    def format_time(seconds):
        hours=math.floor(seconds/3600)
        seconds%=3600
        minutes=math.floor(seconds/60)
        seconds%=60
        milliseconds=math.floor((seconds - math.floor(seconds))*1000)   
        seconds=math.floor(seconds)
        formatted_time=f'{hours:02d}:{minutes:02d}:{seconds:02d}.{milliseconds:03d}'

        return formatted_time


    def generate_vtt_file(segments, audio_filename):
        timestamps_path=frappe.get_site_path("public", "files", "processed", f'{audio_filename.replace("wav", "vtt")}')
        with open(timestamps_path, "w") as f:
            text="WEBVTT\n\n"   
            for segment in segments:
                segment_start=format_time(segment["start"])
                segment_end=format_time(segment["end"])
                text+=f'{segment_start} --> {segment_end}\n'
                text+=f'{segment["text"].strip()}\n\n'
            f.write(text)

        try:
            processed_doc.translated_subs=f'/files/processed/{os.path.basename(timestamps_path)}'
            processed_doc.status="Subtitle added to translated video"
            processed_doc.save(ignore_permissions=True)
            frappe.db.commit()

        except Exception as err:
            processed_doc.status="Subtitle Generation Failed - exception"
            processed_doc.save(ignore_permissions=True)
            frappe.db.commit()
            
            frappe.throw("Error during Subtitling generation : ", err)            

    with open(audio_file_path, "rb") as file:
        transcription = client.audio.transcriptions.create(
            file = file,
            model = "whisper-large-v3-turbo",
            response_format = "verbose_json",
            language = lang_code, # optional
            timestamp_granularities = ["segment"] 
        )
        generate_vtt_file(transcription.segments, audio_filename)

 