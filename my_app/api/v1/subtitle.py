import os

import frappe
from groq import Groq

from my_app.api.v2.dub_labs import labs_client

groq_client = Groq(api_key=frappe.conf.groq_api_key)


def vtt_generate(audio_filename: str, lang_code: str, processed_docname: str):
	processed_doc = frappe.get_doc("Processed Video Info", processed_docname)
	audio_file_path = frappe.get_site_path("public", "files", "processed", audio_filename)

	def srt_to_webvtt(content: str, audio_filename: str):
		timestamps_path = frappe.get_site_path(
			"public", "files", "processed", f"{os.path.splitext(audio_filename)[0]}.vtt"
		)

		try:
			with open(timestamps_path, "w") as f:
				lines = content.splitlines()
				vtt_lines = ["WEBVTT", ""]
				for line in lines:
					if line.isdigit():
						continue

					if "-->" in line:
						line = line.replace(",", ".")
					vtt_lines.append(line)
				f.write("\n".join(vtt_lines))

			processed_doc.translated_subs = f"/files/processed/{os.path.basename(timestamps_path)}"
			processed_doc.activity = "Subtitle added to translated video"
			processed_doc.status = "success"
			processed_doc.save(ignore_permissions=True)
			frappe.db.commit()

		except Exception as err:
			processed_doc.activity = "Subtitle Generation Failed - exception"
			processed_doc.save(ignore_permissions=True)
			processed_doc.status = "failed"
			frappe.db.commit()

			frappe.throw("Error during Subtitling generation : ", err)

	with open(audio_file_path, "rb") as file:
		transcription = labs_client.speech_to_text.convert(
			file=file,
			model_id="scribe_v2",
			diarize=True,
			additional_formats=[{"format": "srt", "max_segment_duration_s": 5}],
		)
		srt_to_webvtt(transcription.additional_formats[0].content, audio_filename)
