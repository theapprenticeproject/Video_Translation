import os
import subprocess

import frappe
from elevenlabs import PronunciationDictionaryVersionLocator

from my_app.api.v1.bhashini_tasks import text_translation
from my_app.api.v1.subtitle import groq_client
from my_app.api.v2.dub_labs import labs_client
from my_app.api.v2.elevenlabs_tasks import create_pronunciation_rules

frappe.utils.logger.set_log_level("DEBUG")
logger = frappe.logger("segment_sts")


def stt_chunks(audio_filename: str):
	audio_filepath = frappe.get_site_path("public", "files", "original", audio_filename)
	logger.info("Before groq STT call")
	with open(audio_filepath, "rb") as file:
		transcription = groq_client.audio.transcriptions.create(
			file=file,
			model="whisper-large-v3",
			response_format="verbose_json",
		)
		big_chunks = merge_segments(transcription.segments, transcription.segments[-1]["end"])
	return big_chunks


def merge_segments(segments, total_duration, num_chunks=2):
	target_duration = total_duration / num_chunks
	merged = []

	current_start = segments[0]["start"]
	current_end = segments[0]["end"]
	current_text = segments[0]["text"]

	for i in range(1, len(segments)):
		seg = segments[i]

		current_duration = current_end - current_start
		if current_duration >= target_duration and len(merged) < num_chunks - 1:
			merged.append(current_text)
			current_start = seg["start"]
			current_end = seg["end"]
			current_text = seg["text"]
		else:
			current_text += " " + seg["text"]
			current_end = seg["end"]

	merged.append(current_text)

	return merged


def tts(text, idx, pro_dicts):
	seg_aud_path = frappe.get_site_path("public", "files", f"segment_{idx}.mp3")
	kwargs = {
		"text": text,
		"voice_id": "vT0wMbLG5dssaBsksrb6",
		"model_id": "eleven_v3",
	}

	if pro_dicts:
		pro_dict_ids = create_pronunciation_rules(pro_dicts)
		kwargs["pronunciation_dictionary_locators"] = [
			PronunciationDictionaryVersionLocator(
				pronunciation_dictionary_id=pro_dict_ids.id, version_id=pro_dict_ids.version_id
			)
		]
	response = labs_client.text_to_speech.convert(**kwargs)
	logger.info(f"Response from tts-{idx}")
	with open(seg_aud_path, "wb") as f:
		for chunk in response:
			if chunk:
				f.write(chunk)

	return seg_aud_path


def segment_main(vid_filename: str, tar_lang_code: str, processed_docname: str, pro_dicts: dict[str, str]):
	output_audio_filename = f"labs_sts_{vid_filename}".replace("mp4", "mp3")
	output_audiopath = frappe.get_site_path("public", "files", "processed", output_audio_filename)
	output_videopath = frappe.get_site_path("public", "files", "processed", f"labs_sts_{vid_filename}")
	input_videopath = frappe.get_site_path("public", "files", "original", vid_filename)

	big_chunks = stt_chunks(vid_filename.replace(".mp4", ".wav"))
	translated_chunks = text_translation(big_chunks, tar_lang_code, processed_docname)
	segmented_audio_filenames = []
	logger.info(f"Before Loop, received chunks: {translated_chunks}")
	for idx, segment in enumerate(translated_chunks):
		seg_aud_path = tts(segment, idx, pro_dicts)
		if seg_aud_path:
			segmented_audio_filenames.append(seg_aud_path)
	try:
		if segmented_audio_filenames:
			processed_doc = frappe.get_doc("Processed Video Info", processed_docname)
			concat_file = frappe.get_site_path("public", "files", "concat_list.txt")
			with open(concat_file, "w") as f:
				for filename in segmented_audio_filenames:
					abs_path = os.path.abspath(filename)
					f.write(f"file '{abs_path}'\n")
			logger.info("Before subprocess concat segmented audio files")
			subprocess.run(
				[
					"ffmpeg",
					"-y",
					"-nostdin",
					"-f",
					"concat",
					"-safe",
					"0",
					"-i",
					concat_file,
					"-c",
					"copy",
					output_audiopath,
				],
				check=True,
			)

		if os.path.exists(output_audiopath):
			logger.info("Running muxing of output audio to inp vid")
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
				],
				check=True,
			)

		processed_doc.localized_vid = f"/files/processed/labs_sts_{vid_filename}"
		processed_doc.save(ignore_permissions=True)
		frappe.db.commit()

		return {
			"audio_filename": output_audio_filename,
			"audio_filepath": f"/files/processed/{output_audio_filename}",
		}
	except subprocess.CalledProcessError as e:
		logger.error(f"ffmpeg failed: {e}")
		processed_doc.activity = "Command Failed - segments"
		processed_doc.status = "failed"
		processed_doc.save(ignore_permissions=True)
		frappe.db.commit()

		frappe.throw(f"Error during segment muxing: {e}")

	except Exception as err:
		logger.exception("Unexpected error in segment processing")
		processed_doc.status = "failed"
		processed_doc.activty = "Unexpected error in segment processing"
		processed_doc.save(ignore_permissions=True)
		frappe.db.commit()
		frappe.throw("Unexpected Error during segment processing: ", err)
