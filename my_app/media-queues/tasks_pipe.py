import frappe, os
from my_app.api.v1.bhashini_tasks import lang_detection
from my_app.api.v2.dub_labs import dubbing

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
        "email_content": f"Source language is: {src_language}",
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
                method="my_app.media-queues.tasks_pipe.hindi_dubbing",
                queue="long",
                video_filename=video_filename,
                processed_docname=processed_docname,
                user=user
            )   
        else:
            print("Target language is not hindi")

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
