import frappe, os, subprocess

def audio_extraction(video_file_base: str, folder: str, output_folder: str, ):
    input_path=frappe.get_site_path("public", folder, video_file_base)
    if not os.path.exists(input_path):
        frappe.throw(f"{video_file_base} not found")

    output_file=f"{video_file_base}.wav"
    output_path=frappe.get_site_path("public", output_folder, output_file)

    cmd=["ffmpeg", "-i", input_path, "-acodec", "pcm_s16le", "-ar", "16000", "-ac", "1", output_path]

    try:
        subprocess.run(cmd, text=True, check=True)
        frappe.publish_realtime(event="audio_extraction_completed", message={"audiofile": output_file})
    except subprocess.CalledProcessError as e:
        frappe.log_error(f"Ffmpeg error: {e}")
        frappe.throw("Video-audio extraction error")
