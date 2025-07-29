import frappe
from my_app.api.v1.bhashini_tasks import lang_detection
from my_app.api.v2.dub_labs import dubbing

@frappe.whitelist()
def trigger_pipeline(video_info_docname: str, audio_file_url: str, video_file_url:str):
    print("before new processed doc created")
    processed_doc=frappe.new_doc("Processed Video Info")
    print("just after creation of new processed video info record")
    processed_doc.origin_vid_link=video_info_docname
    processed_doc.status="Pending"
    processed_doc.processed_on=frappe.utils.now()
    processed_doc.insert(ignore_permissions=True)
    frappe.db.commit()
    print("before lang detection queue")
    frappe.enqueue(
        method="my_app.media-queues.tasks_pipe.language_detection",
        queue="default",
        audio_filename= audio_file_url.lstrip("/"),
        processed_docname=processed_doc.name,
        video_filename=video_file_url.lstrip("/"),
    )   

def language_detection(audio_filename: str, processed_docname: str, video_filename: str):
    print("before lang detection function call ")
    src_language=lang_detection(audio_filename, processed_docname)
    print("before publishing real time event for lang detection")
    frappe.publish_realtime(
        event="language_detection_completed",
        message={"text":f"source language detected :  {src_language}"}
    )    

    # original_doc=frappe.get_doc("Video Info")
    # print("Video Info target language selected : ",original_doc.target_lang)
#     if original_doc.target_lang=="Hindi":
#         frappe.enqueue(
#             method="my_app.media-queues.tasks_pipe.hindi_dubbing",
#             queue="long",
#             video_filename=video_filename,
#             processed_docname=processed_docname
#         )   
#     else:
#         print("Target language is not hindi")

# def hindi_dubbing(video_filename: str, processed_docname: str):
#     processed_videofile_url=dubbing(video_filename, processed_docname)
#     processed_doc=frappe.get_doc("Processed Video Info", processed_docname)
#     processed_doc.status="Dubbing Completed"
#     processed_doc.localized_vid=processed_videofile_url
#     processed_doc.save(ignore_permissions=True)
#     frappe.db.commit()

#     frappe.publish_realtime(
#         event="hindi_dubbing_completed",
#         message={"text":f"Video Localized message after dubbing: {processed_videofile_url}"}
#     )
