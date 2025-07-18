import frappe, subprocess, math
from groq import Groq

client=Groq(
    api_key=frappe.conf.groq_api_key
)

@frappe.whitelist()
def srt_generate(audio_file: str, langCode: str):
    audio_file_path=frappe.get_site_path("public", "files", audio_file)
    subtitled_video=frappe.get_site_path("public", "files", "subtitled_vid.mp4")
    translatedVid=frappe.get_site_path("public", "files", "david-dub-hindi.mp4")
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
        transcript_timestamps=frappe.get_site_path("public", "files", "subtitles_timestamps.srt")
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
            subprocess.call(["ffmpeg", "-i", input_vid, "-i", subtitle_file, "-c", "copy", "-c:s", "mov_text", output_video])    
        except subprocess.SubprocessError as e:
            frappe.throw('ffmpeg- Video Subtitling error')            
 