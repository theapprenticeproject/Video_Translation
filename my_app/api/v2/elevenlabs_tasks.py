import os
import subprocess

import frappe

from my_app.api.v1.bhashini_tasks import text_translation

# from my_app.api.v1.subtitle import groq_client
from my_app.api.v2.dub_labs import labs_client

frappe.utils.logger.set_log_level("DEBUG")
logger = frappe.logger("labs")

"""Speech to text supports both video & audio upload for transcription"""


def speech_to_text(tar_lang_code, vid_filename: str, processed_docname: str):
	vid_filepath = frappe.get_site_path("public", "files", "original", vid_filename)
	with open(vid_filepath, "rb") as audio_file:
		response = labs_client.speech_to_text.convert(
			file=audio_file,
			model_id="scribe_v1",
			language_code="hi",
		)
	logger.info(f"Received response from STT: {response}")
	print("receieved response from STT: ", response)
	transcript = response.text
	translated_text = text_translation(transcript, tar_lang_code, processed_docname)
	logger.info(f"Received translated text from bhashini: {translated_text}")
	tts_response = text_to_speech(translated_text, vid_filename, processed_docname)
	return tts_response


# def text_translate(text: str, lang_code):

#     system_prompt='''You are a professional Translator. Your sole purpose is to translate the user's text to the specified language accurately. Do not add any extra elements, notes, or explanations.'''
#     user_prompt=f"Translate the following text into {lang_code}"
#     response = groq_client.chat.completions.create(
#         messages=[
#             {"role": "system", "content": system_prompt},
#             {"role": "user", "content": text},
#         ],
#         model="openai/gpt-oss-120b",
#     )
#     translated_text = response.choices[0].message.content
#     print(translated_text)


def text_to_speech(text: str, vid_filename: str, processed_docname: str):
	processed_doc = frappe.get_doc("Processed Video Info", processed_docname)
	output_audio_filename = f"labs_sts_{vid_filename}"
	output_audiopath = frappe.get_site_path("public", "files", "processed", output_audio_filename.replace("mp4", "mp3"))
	output_videopath = frappe.get_site_path("public", "files", "processed", f"labs_sts_{vid_filename}")
	input_videopath = frappe.get_site_path("public", "files", "original", vid_filename)
	print("Calling TTS model for voice output")
	logger.info("Calling TTS model for voice output")
	response = labs_client.text_to_speech.convert(
		text=text,
		voice_id="VT26nWaqgBmXtH6KAeQ3",  # Vaidehi
		model_id="eleven_v3",
	)
	logger.info(f"Output audipath: {output_audiopath}")
	logger.info(f"Response received from TTS model: {response}")
	with open(output_audiopath, "wb") as f:
		for chunk in response:
			if chunk:
				f.write(chunk)
	if os.path.exists(output_audiopath):
		logger.info("Running muxing command of output audio to input video")
		print("before subprocess run")
		subprocess.run(
			[
				"ffmpeg",
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
		logger.info("Video localized after subprocess command execution")
	return {
		"audio_filename": output_audio_filename,
		"audio_filepath": f"/files/processed/{output_audio_filename}",
	}
