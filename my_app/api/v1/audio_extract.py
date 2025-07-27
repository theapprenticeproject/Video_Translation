import frappe, os, subprocess, time

def audio_extraction(videofile_base: str, videofile_path: str, output_folder_suffix: str, docname: str, videofile_url: str):
    print("starting extraction, before input_path")
    input_path=videofile_path
    print("input Path", input_path)
    if not os.path.exists(input_path):
        frappe.throw(f"{input_path} not found")

    output_filename=f"{videofile_base}.wav"
    output_path=os.path.join(frappe.get_site_path("public", "files", output_folder_suffix), output_filename)
    print("Output path : ", output_path)

    time.sleep(0.6)

    cmd=["ffmpeg", "-i", input_path, "-acodec", "pcm_s16le", "-ar", "16000", "-ac", "1", output_path]
    print("before try block")
    try:
        print("before subprocess runs")
        subprocess.run(cmd, text=True, check=True)
        print(f'Audio extraction done Output:  {output_path}\n')

        video_info_doc=frappe.get_doc("Video Info", docname) # getting the doctype instance
        audiofile_url=f'/files/{output_folder_suffix}/{output_filename}'
        video_info_doc.original_audio_extracted=audiofile_url
        frappe.db.commit()

        frappe.publish_realtime(event="audio_extraction_completed", message={"audiofile_url": audiofile_url, "videopath_url": videofile_url})
    except subprocess.CalledProcessError as e:
        frappe.log_error(f"Ffmpeg error: {e}")
        frappe.throw("Video-audio extraction error")
