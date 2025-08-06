import frappe, subprocess, math
from groq import Groq

client=Groq(
    api_key=frappe.conf.groq_api_key
)

def srt_generate(video_filename: str, audio_filename: str, langCode: str, processed_docname: str):
    processed_doc=frappe.get_doc("Processed Video Info", processed_docname)
    audio_file_path=frappe.get_site_path("public", "files", "processed", audio_filename)
    subtitled_video=frappe.get_site_path("public", "files", "processed",f"sub_{video_filename}")
    translatedVid=frappe.get_site_path("public", "files", "processed",video_filename)

    # formatting time in HH:MM:SS,mmm ; 'm' denoting milliseconds
    def format_time(seconds):
        hours=math.floor(seconds/3600)
        seconds%=3600
        minutes=math.floor(seconds/60)
        seconds%=60
        milliseconds=math.floor((seconds - math.floor(seconds))*1000)   
        seconds=math.floor(seconds)
        formatted_time=f'{hours:02d}:{minutes:02d}:{seconds:02d},{milliseconds:03d}'

        return formatted_time


    def generate_srt_file(segments):
        transcript_timestamps=frappe.get_site_path("public", "files", "processed","subtitles_timestamps.srt")
        with open(transcript_timestamps, "w") as f:
            text=""
            for idx, segment in enumerate(segments):
                segment_start=format_time(segment["start"])
                segment_end=format_time(segment["end"])
                text+=f'{str(idx+1)}\n'
                text+=f'{segment_start} --> {segment_end}\n'
                text+=f'{segment["text"].strip()}\n'
                text+='\n'
            f.write(text)
        add_subtitle_vid(translatedVid, transcript_timestamps, subtitled_video)

    with open(audio_file_path, "rb") as file:
        transcription = client.audio.transcriptions.create(
            file = file,
            model = "whisper-large-v3",
            response_format = "verbose_json",
            language = langCode,
            timestamp_granularities = ["segment"] 
        )
        generate_srt_file(transcription.segments)

    def add_subtitle_vid(input_vid, subtitle_file, output_video):
        try:
            # adding 'soft subtitle' to the original video
            subprocess.call(["ffmpeg", "-i", input_vid, "-i", subtitle_file, "-c", "copy", "-c:s", "mov_text", output_video])

            processed_doc.status="Subtitle added to translated video"
            processed_doc.save(ignore_permissions=True)
            frappe.db.commit()
                
        except subprocess.SubprocessError as e:
            processed_doc.status="Subtitle Generation Failed - subprocess"
            processed_doc.save(ignore_permissions=True)
            frappe.db.commit()

            frappe.throw('ffmpeg- Video Subtitling error : ', e)

        except Exception as err:
            processed_doc.status="Subtitle Generation Failed - exception"
            processed_doc.save(ignore_permissions=True)
            frappe.db.commit()
            
            frappe.throw("Error during Subtitling generation : ", err)            

 