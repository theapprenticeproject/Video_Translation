"""Server side APIs being called are queued all from this file. Each function is queued after each queued is successful/terminated"""

import json

import frappe

from my_app.api.v1.audio_extract import audio_extraction
from my_app.api.v1.bhashini_tasks import STS_pipe, lang_detection
from my_app.api.v1.subtitle import vtt_generate
from my_app.api.v2.dub_labs import dubbing
from my_app.api.v2.elevenlabs_tasks import speech_to_text
from my_app.api.v2.onscreen_txt import apply_onscreentext, screen_txtoverlay
from my_app.api.v2.segment_tasks import segment_main
from my_app.helper.options import normalize_keyterms, sanitize_pro_dicts

languages = {"Marathi": "mr", "Punjabi": "pa"}


@frappe.whitelist()
def trigger_pipeline(video_info_docname: str, audio_filename: str, video_filename: str):
	processed_doc = frappe.new_doc("Processed Video Info")
	processed_doc.origin_vid_link = video_info_docname
	processed_doc.status = "pending"
	processed_doc.processed_on = frappe.utils.now()
	processed_doc.insert(ignore_permissions=True)
	frappe.db.commit()
	frappe.enqueue(
		method="my_app.media-queues.tasks_pipe.language_detection",
		queue="default",
		audio_filename=audio_filename,
		processed_docname=processed_doc.name,
		video_filename=video_filename,
		user=frappe.session.user,
	)


def language_detection(audio_filename: str, processed_docname: str, video_filename: str, user: str):
	src_language = lang_detection(audio_filename, processed_docname)
	frappe.get_doc(
		{
			"doctype": "Notification Log",
			"for_user": user,
			"subject": "Language Detection",
			"email_content": f"Source language Detected: {src_language}",
			"type": "Alert",
		}
	).insert(ignore_permissions=True)
	docname = frappe.get_value("Video Info", {"original_vid": ["like", f"%{video_filename}%"]})
	if docname:
		original_doc = frappe.get_doc("Video Info", docname)
		target_language = original_doc.target_lang
		if target_language == "Hindi":
			frappe.enqueue(
				method="my_app.media-queues.tasks_pipe.hindi_dubbing",
				queue="long",
				video_filename=video_filename,
				processed_docname=processed_docname,
				user=user,
			)
		else:
			# bhashini API services for non-hindi translations
			# frappe.enqueue(
			# 	method="my_app.media-queues.tasks_pipe.sts_translation",
			# 	queue="long",
			# 	video_filename=video_filename,
			# 	audio_filename=audio_filename,
			# 	src_lang_code=src_language,
			# 	tar_lang_code=target_language,
			# 	processed_docname=processed_docname,
			# 	user=user,
			# )

			# elevenlab service for non-hindi
			tar_langcode = languages.get(target_language.strip())
			frappe.enqueue(
				method="my_app.media-queues.tasks_pipe.labs_sts_translation",
				queue="long",
				video_filename=video_filename,
				tar_lang_code=tar_langcode,
				processed_docname=processed_docname,
				user=user,
			)


def sts_translation(
	video_filename: str,
	audio_filename: str,
	src_lang_code: str,
	tar_lang_code: str,
	processed_docname: str,
	user: str,
):
	processed_audio_info = STS_pipe(
		video_filename, audio_filename, src_lang_code, tar_lang_code, processed_docname
	)
	processed_doc = frappe.get_doc("Processed Video Info", processed_docname)
	processed_doc.translated_aud = processed_audio_info["audio_filepath"]
	processed_doc.activity = "Video Translation Done - sts"
	processed_doc.save(ignore_permissions=True)
	frappe.db.commit()

	frappe.get_doc(
		{
			"doctype": "Notification Log",
			"for_user": user,
			"subject": "Translation Completed",
			"email_content": f"Translation done in {tar_lang_code}",
			"type": "Alert",
		}
	).insert(ignore_permissions=True)

	frappe.enqueue(
		method="my_app.media-queues.tasks_pipe.get_subtitles",
		queue="short",
		audio_filename=processed_audio_info["audio_filename"],
		lang_code=processed_audio_info["tar_lang_code"],
		processed_docname=processed_docname,
		user=user,
	)


@frappe.whitelist()
def retry_trigger(video_info_name: str, tar_lang: str, processed_docname: str, options):
	options = json.loads(options)
	key_terms = normalize_keyterms(options.get("keyterm_prompt"))
	pro_dicts = sanitize_pro_dicts(options.get("pronunciation_dict"))
	video_filename = (
		frappe.db.get_value("Video Info", video_info_name, "original_vid")
		.replace("/files/original", "")
		.split("/")[1]
	)
	tar_lang_code = languages.get(tar_lang.strip())
	processed_doc = frappe.get_doc("Processed Video Info", processed_docname)
	processed_doc.retry_count = (processed_doc.retry_count or 0) + 1
	processed_doc.status = "pending"
	processed_doc.activity = "Re-processing triggered"
	processed_doc.save(ignore_permissions=True)
	frappe.db.commit()
	frappe.enqueue(
		method="my_app.media-queues.tasks_pipe.labs_sts_translation",
		queue="long",
		video_filename=video_filename,
		tar_lang_code=tar_lang_code,
		processed_docname=processed_docname,
		user=frappe.session.user,
		key_terms=key_terms,
		pro_dicts=pro_dicts,
	)


def segmented_sts(
	video_filename: str,
	tar_lang_code: str,
	processed_docname: str,
	user: str,
	pro_dicts: dict[str, str] | None = None,
):
	processed_audio_info = segment_main(video_filename, tar_lang_code, processed_docname, pro_dicts)
	processed_doc = frappe.get_doc("Processed Video Info", processed_docname)
	processed_doc.translated_aud = processed_audio_info["audio_filepath"]
	processed_doc.activity = "Video Translation done - ElevenLabs STS"
	processed_doc.percent = 80
	processed_doc.save(ignore_permissions=True)
	frappe.db.commit()
	frappe.get_doc(
		{
			"doctype": "Notification Log",
			"for_user": user,
			"subject": "Translation Completed",
			"email_content": f"Translation done in {tar_lang_code}",
			"type": "Alert",
		}
	).insert(ignore_permissions=True)

	frappe.enqueue(
		method="my_app.media-queues.tasks_pipe.get_subtitles",
		queue="short",
		audio_filename=processed_audio_info["audio_filename"],
		lang_code=tar_lang_code,
		processed_docname=processed_docname,
		user=user,
	)


def labs_sts_translation(
	video_filename: str,
	tar_lang_code: str,
	processed_docname: str,
	user: str,
	key_terms: list[str] | None = None,
	pro_dicts: dict[str, str] | None = None,
):
	processed_audio_info = speech_to_text(
		tar_lang_code, video_filename, processed_docname, key_terms, pro_dicts
	)
	processed_doc = frappe.get_doc("Processed Video Info", processed_docname)
	processed_doc.translated_aud = processed_audio_info["audio_filepath"]
	processed_doc.activity = "Video Translation done - ElevenLabs STS"
	processed_doc.percent = 75
	processed_doc.save(ignore_permissions=True)
	frappe.db.commit()

	frappe.get_doc(
		{
			"doctype": "Notification Log",
			"for_user": user,
			"subject": "Translation Completed",
			"email_content": f"Translation done in {tar_lang_code}",
			"type": "Alert",
		}
	).insert(ignore_permissions=True)

	frappe.enqueue(
		method="my_app.media-queues.tasks_pipe.on_screen_txt_translation",
		queue="long",
		vid_filename=video_filename,
		audio_filename=processed_audio_info["audio_filename"],
		lang_code=tar_lang_code,
		processed_docname=processed_docname,
		user=user,
	)


def on_screen_txt_translation(
	vid_filename: str, audio_filename: str, lang_code: str, processed_docname: str, user: str
):
	screen_txtoverlay(vid_filename, lang_code, processed_docname)

	processed_doc = frappe.get_doc("Processed Video Info", processed_docname)
	processed_doc.activity = "Video Translation done - ElevenLabs STS"
	processed_doc.percent = 85
	processed_doc.save(ignore_permissions=True)
	frappe.db.commit()

	frappe.enqueue(
		method="my_app.media-queues.tasks_pipe.get_subtitles",
		queue="short",
		audio_filename=audio_filename,
		lang_code=lang_code,
		processed_docname=processed_docname,
		user=user,
	)


# path-1
def hindi_dubbing(video_filename: str, processed_docname: str, user: str):
	processed_videofile_url = dubbing(video_filename, processed_docname)
	processed_doc = frappe.get_doc("Processed Video Info", processed_docname)
	processed_doc.activity = "Dubbing Completed"
	processed_doc.localized_vid = processed_videofile_url
	processed_doc.percent = 75
	processed_doc.save(ignore_permissions=True)
	frappe.db.commit()

	frappe.get_doc(
		{
			"doctype": "Notification Log",
			"for_user": user,
			"subject": "Translation Compeleted",
			"email_content": "Dubbing done in Hindi",
			"type": "Alert",
		}
	).insert(ignore_permissions=True)

	frappe.enqueue(
		method="my_app.media-queues.tasks_pipe.extract_audio",
		queue="short",
		videofile=processed_videofile_url,
		processed_docname=processed_docname,
		user=user,
	)


def extract_audio(videofile: str, processed_docname: str, user: str):
	extraction_info = audio_extraction(videofile)
	processed_doc = frappe.get_doc("Processed Video Info", processed_docname)
	processed_doc.activity = "Audio Extracted from Dubbed Vid"
	processed_doc.translated_aud = extraction_info["audiofile_url"]
	processed_doc.save(ignore_permissions=True)
	frappe.db.commit()

	frappe.enqueue(
		method="my_app.media-queues.tasks_pipe.get_subtitles",
		queue="short",
		audio_filename=extraction_info["audio_filename"],
		lang_code="hi",
		processed_docname=processed_docname,
		user=user,
	)


def get_subtitles(audio_filename: str, lang_code: str, processed_docname: str, user: str):
	vtt_generate(audio_filename, lang_code, processed_docname)

	frappe.get_doc(
		{
			"doctype": "Notification Log",
			"for_user": user,
			"subject": "Subtitles Generated",
			"email_content": "Subtitles File Created",
			"type": "Alert",
		}
	).insert(ignore_permissions=True)


@frappe.whitelist()
def onscreentxt_trigger(trans_vid_info: str, tar_lang: str, processed_docname: str):
	tar_langcode = languages.get(tar_lang.strip())
	trans_vid_filename = trans_vid_info.replace("/files/processed", "").split("/")[1]
	frappe.enqueue(
		method="my_app.media-queues.tasks_pipe.onscreentxt_trans",
		queue="long",
		vid_filename=trans_vid_filename,
		processed_docname=processed_docname,
		tar_langcode=tar_langcode,
	)


def onscreentxt_trans(vid_filename: str, processed_docname: str, tar_langcode: str):
	apply_onscreentext(vid_filename, processed_docname, tar_langcode)

	frappe.get_doc(
		{
			"doctype": "Notification Log",
			"for_user": frappe.session.user,
			"subject": "Localization Process Completed",
			"email_content": "Localization Successful",
			"type": "Alert",
		}
	).insert(ignore_permissions=True)
