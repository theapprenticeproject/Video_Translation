import frappe, subprocess

def audio_extraction(videofile: str):
    print("Input path in audio extraction:", videofile)

    split_file_list = videofile.replace("/files/", "").split("/")
    print("Split file list:", split_file_list)

    folder_suffix = split_file_list[0]
    video_filename = split_file_list[1]

    input_path = frappe.get_site_path("public", "files", folder_suffix, video_filename)
    print("Input path of video file:", input_path)

    audio_filename = video_filename.replace(".mp4", ".wav")
    output_path = frappe.get_site_path("public", "files", folder_suffix, audio_filename)
    print("Output path of audio file:", output_path)

    cmd = ["ffmpeg", "-nostdin", "-i", input_path, "-acodec", "pcm_s16le", "-ar", "16000", "-ac", "1", output_path]

    print("Preparing to run ffmpeg command...")

    try:
        print("Running subprocess command...")
        subprocess.run(cmd, text=True, check=True)

        audiofile_url = f"/files/{folder_suffix}/{audio_filename}"
        print("Audio file URL:", audiofile_url)

        if folder_suffix == "original":
            frappe.publish_realtime(
                event="audio_extraction_completed",
                message={"audiofile_url": audiofile_url, "audio_filename":audio_filename, "video_filename":video_filename}
            )
        elif folder_suffix == "processed":
            return {
                "audiofile_url": audiofile_url,
                "audio_filename": audio_filename,
                "video_filename": video_filename
            }            
    except subprocess.CalledProcessError as e:
        print("ffmpeg error:", e)
        frappe.throw("Video-audio extraction error")


@frappe.whitelist()
def trigger_audio_extract(videofile_url: str):
    frappe.enqueue(
        method="my_app.api.v1.audio_extract.audio_extraction",
        queue="short",
        videofile=videofile_url
    )
