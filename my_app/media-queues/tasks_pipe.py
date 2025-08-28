'''Server side APIs being called are queued all from this file. Each function is queued after each queued is successful/terminated'''

import frappe
from my_app.api.v1.bhashini_tasks import lang_detection
from my_app.api.v2.dub_labs import dubbing
from my_app.api.v2 import dub_sieve
from my_app.api.v1.audio_extract import audio_extraction
from my_app.api.v1.subtitle import vtt_generate

'''Not importing the function in dub_sieve.py directly because import sieve tries to set up signal handler which only works 
in main thread, thus avoiding signal error.
In frappe, imports can happen inside worker threads thus function calling inside a queue (managed by a worker).
'''
@frappe.whitelist()
def trigger_pipeline(video_info_docname: str, audio_filename: str, video_filename:str):
    print("before new processed doc created")
    processed_doc=frappe.new_doc("Processed Video Info")
    processed_doc.origin_vid_link=video_info_docname
    processed_doc.status="Pending"
    processed_doc.processed_on=frappe.utils.now()
    processed_doc.insert(ignore_permissions=True)
    frappe.db.commit()
    print("before lang detection queue")
    print(frappe.session.user)
    frappe.enqueue(
        method="my_app.media-queues.tasks_pipe.language_detection",
        queue="default",
        audio_filename= audio_filename,
        processed_docname=processed_doc.name,
        video_filename=video_filename,
        user=frappe.session.user
    )   

def language_detection(audio_filename: str, processed_docname: str, video_filename: str, user: str):
    print("before lang detection function call ")
    src_language=lang_detection(audio_filename, processed_docname)
    frappe.get_doc({
        "doctype":"Notification Log",
        "for_user": user,
        "subject": "Language Detection",
        "email_content": f"Source language Detected: {src_language}",
        "type": "Alert"
    }).insert(ignore_permissions=True)
    print("source language after lang detection is : ", src_language)
    docname=frappe.get_value("Video Info", {"original_vid":["like", f"%{video_filename}%"]})
    print("docname from video info: ", docname)
    if docname:
        original_doc=frappe.get_doc("Video Info", docname)
        target_language=original_doc.target_lang
        print("Video Info target language selected : ",target_language)
        if target_language=="Hindi":
            frappe.enqueue(
                method="my_app.media-queues.tasks_pipe.alt_hindi_dub",
                queue="long",
                video_filename=video_filename,
                processed_docname=processed_docname,
                user=user
            )   
        else:
            print("Target language is not hindi")

# path-1
def hindi_dubbing(video_filename: str, processed_docname: str, user: str):
    processed_videofile_url=dubbing(video_filename, processed_docname)
    processed_doc=frappe.get_doc("Processed Video Info", processed_docname)
    processed_doc.status="Dubbing Completed"
    processed_doc.localized_vid=processed_videofile_url
    processed_doc.save(ignore_permissions=True)
    frappe.db.commit()

    frappe.get_doc({
        "doctype":"Notification Log",
        "for_user": user,
        "subject": "Translation Compeleted",
        "email_content": f"Dubbing done in Hindi",
        "type": "Alert"
    }).insert(ignore_permissions=True)

# path-2 
def alt_hindi_dub(video_filename: str, processed_docname: str, user: str):
    processed_videofile_url=dub_sieve.dubbing_alt(video_filename, processed_docname)
    processed_doc=frappe.get_doc("Processed Video Info", processed_docname)
    processed_doc.status="Dubbing Completed"
    processed_doc.localized_vid=processed_videofile_url
    processed_doc.save(ignore_permissions=True)
    frappe.db.commit()

    frappe.get_doc({
        "doctype":"Notification Log",
        "for_user":user,
        "subject":"Translation Completed",
        "email_content":f"Dubbing Done in Hindi",
        "type":"Alert"
    }).insert(ignore_permissions=True)

    frappe.enqueue(
        method="my_app.media-queues.tasks_pipe.extract_audio",
        queue="short",
        videofile=processed_videofile_url, 
        processed_docname=processed_docname,
        user=user
    )

def extract_audio(videofile: str, processed_docname: str, user: str):
    extraction_info=audio_extraction(videofile)
    processed_doc=frappe.get_doc("Processed Video Info", processed_docname)
    processed_doc.status="Audio Extracted from Dubbed Vid"
    processed_doc.translated_aud=extraction_info.audiofile_url
    processed_doc.save(ignore_permissions=True)
    frappe.db.commit()

    frappe.enqueue(
        method="my_app.media-queues.tasks_pipe.get_subtitles",
        queue="short",
        audio_filename=extraction_info.audio_filename,
        processed_docname=processed_docname,
        user=user
    )

def get_subtitles(audio_filename: str, processed_docname: str, user: str):
    vtt_generate(audio_filename, processed_docname)

    frappe.get_doc({
        "doctype":"Notification Log",
        "for_user":user,
        "subject":"Subtitles Generated",
        "email_content":f"Subtitles File Created",
        "type":"Alert"
    }).insert(ignore_permissions=True)

    frappe.get_doc({
        "doctype":"Notification Log",
        "for_user": user,
        "subject":"Localization Process Completed",
        "email_content":f"Localization Successful",
        "type":"Alert"
    })