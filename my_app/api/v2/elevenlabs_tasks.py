import json
import os
import subprocess

import frappe
from elevenlabs import PronunciationDictionaryAliasRuleRequestModel, PronunciationDictionaryVersionLocator

from my_app.api.v1.bhashini_tasks import text_translation
from my_app.api.v2.dub_labs import labs_client

# from my_app.api.v1.subtitle import groq_client

frappe.utils.logger.set_log_level("DEBUG")
logger = frappe.logger("labsts")

"""Speech to text supports both video & audio upload for transcription"""


def populate_segments_table(segments_data: dict, tar_lang_code: str, processed_docname: str):
	try:
		processed_doc = frappe.get_doc("Processed Video Info", processed_docname)
		if segments_data:
			segments = segments_data.get("segments")
			source_texts = [seg["text"] for seg in segments]
			translated_texts = text_translation(source_texts, tar_lang_code, processed_docname)
			processed_doc.reload()
			logger.info("Received translated text from bhashini:")
			processed_doc.set("translated_segments", [])
			for segment, trans_text in zip(segments, translated_texts, strict=True):
				processed_doc.append(
					"translated_segments",
					{
						"text": segment["text"],
						"translated_text": trans_text,
						"start_time": segment["words"][0]["start"],
						"end_time": segment["words"][-1]["end"],
					},
				)
		processed_doc.activity = "Audio Transcript Translation Completed"
		processed_doc.percent = 45
		processed_doc.save(ignore_permissions=True)
		frappe.db.commit()
	except Exception as e:
		logger.error("Error populating text segments table", e)
		frappe.throw(f"Failed to populate text segments table: {e}")


def speech_to_text(
	tar_lang_code, vid_filename: str, processed_docname: str, key_terms: list[str], pro_dicts: dict[str, str]
):
	vid_filepath = frappe.get_site_path("public", "files", "original", vid_filename)
	with open(vid_filepath, "rb") as audio_file:
		if key_terms:
			response = labs_client.speech_to_text.convert(
				file=audio_file, model_id="scribe_v2", keyterms=key_terms
			)
		else:
			response = labs_client.speech_to_text.convert(
				file=audio_file,
				model_id="scribe_v2",
				diarize=True,
				additional_formats=[{"format": "segmented_json", "max_segment_chars": 84}],
			)

	logger.info(f"Received response from STT: {response}")
	segments_data = json.loads(response.additional_formats[0].content)
	populate_segments_table(segments_data, tar_lang_code, processed_docname)
	# tts_response = text_to_speech(translated_text, tar_lang_code, vid_filename, processed_docname, pro_dicts)
	# return tts_response


def text_to_speech(langcode: str, vid_filename: str, processed_docname: str, pro_dicts: dict[str, str]):
	processed_doc = frappe.get_doc("Processed Video Info", processed_docname)
	text_pieces = []
	for i in processed_doc.get("translated_segments", []):
		if i.translated_text:
			text_pieces.append(i.translated_text)
	entire_text = " ".join(text_pieces)
	output_audio_filename = f"labs_sts_{vid_filename}".replace("mp4", "mp3")
	output_audiopath = frappe.get_site_path("public", "files", "processed", output_audio_filename)
	output_videopath = frappe.get_site_path("public", "files", "processed", f"labs_sts_{vid_filename}")
	input_videopath = frappe.get_site_path("public", "files", "original", vid_filename)
	logger.info("Calling TTS model for voice output")
	voices = {"mr": "VT26nWaqgBmXtH6KAeQ3", "pa": "vT0wMbLG5dssaBsksrb6"}  # Vaidehi & Noor respectively
	lang_voice_id = voices.get("mr") if langcode == "mr" else voices.get("pa")
	if pro_dicts:
		pro_dict_ids = create_pronunciation_rules(pro_dicts)
		response = labs_client.text_to_speech.convert(
			text=entire_text,
			voice_id=lang_voice_id,
			model_id="eleven_v3",
			pronunciation_dictionary_locators=[
				PronunciationDictionaryVersionLocator(
					pronunciation_dictionary_id=pro_dict_ids.id, version_id=pro_dict_ids.version_id
				)
			],
		)
	else:
		response = labs_client.text_to_speech.convert(
			text=entire_text, voice_id=lang_voice_id, model_id="eleven_v3"
		)
	logger.info(f"Output audiopath: {output_audiopath}")
	logger.info(f"Response received from TTS model: {response}")
	with open(output_audiopath, "wb") as f:
		for chunk in response:
			if chunk:
				f.write(chunk)
	if os.path.exists(output_audiopath):
		logger.info("Running muxing command of output audio to input video")
		subprocess.run(
			[
				"ffmpeg",
				"-y",
				"-nostdin",
				"-i",
				input_videopath,
				"-i",
				output_audiopath,
				"-c:v",
				"copy",
				"-c:a",
				"aac",
				"-map",
				"0:v:0",
				"-map",
				"1:a:0",
				output_videopath,
			]
		)

		processed_doc.localized_vid = f"/files/processed/labs_sts_{vid_filename}"
		processed_doc.save(ignore_permissions=True)
		frappe.db.commit()
		logger.info("Video localized after subprocess command execution")
	return {
		"audio_filename": output_audio_filename,
		"audio_filepath": f"/files/processed/{output_audio_filename}",
	}


def create_pronunciation_rules(pro_dicts: dict[str, str]):
	rules = []
	for word, alias in pro_dicts.items():
		rule = PronunciationDictionaryAliasRuleRequestModel(string_to_replace=word, alias=alias)
		rules.append(rule)

	response = labs_client.pronunciation_dictionaries.create_from_rules(name="TAP Dictionary", rules=rules)

	return response
