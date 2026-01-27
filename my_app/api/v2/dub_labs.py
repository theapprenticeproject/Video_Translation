import time

import frappe
from elevenlabs import ElevenLabs

frappe.utils.logger.set_log_level("DEBUG")
logger = frappe.logger("dubbing")
labs_client = ElevenLabs(api_key=frappe.conf.elevenlabs_api_key)


def dubbing(video_filename: str, processed_docname: str):
	processed_doc = frappe.get_doc("Processed Video Info", processed_docname)
	processed_doc.activity = "Dubbing in progress..."
	processed_doc.save(ignore_permissions=True)
	frappe.db.commit()

	try:

		def wait_for_dubbing_completion(dubbing_id: str) -> bool:
			MAX_ATTEMPTS = 120
			CHECK_INTERVAL = 10  # In seconds

			for _ in range(MAX_ATTEMPTS):
				metadata = labs_client.dubbing.get(dubbing_id)
				if metadata.status == "dubbed":
					return True
				elif metadata.status == "dubbing":
					print("Dubbing in progress... Will check status again in", CHECK_INTERVAL, "seconds.")
					logger.info(
						f"Dubbing in progress... Will check status again in {CHECK_INTERVAL} seconds."
					)
					time.sleep(CHECK_INTERVAL)
				else:
					print("Dubbing failed:", metadata.error)
					logger.error(f"Dubbing failed : {metadata.error}")
					return False

			print("Dubbing timed out")
			return False

		filepath = frappe.get_site_path("public", "files", "original", video_filename)

		with open(filepath, "rb") as videofile:
			response = labs_client.dubbing.create(
				file=videofile, target_lang="hi", mode="automatic", watermark=True
			)
		dubbing_id = response.dubbing_id
		print("dubbing id: ", dubbing_id)
		if wait_for_dubbing_completion(dubbing_id):
			output_filename = f"dub_{video_filename}"
			output_videopath = frappe.get_site_path("public", "files", "processed", output_filename)
			stream = labs_client.dubbing.audio.get(dubbing_id, "hi")
			logger.info("Received streamed response from get dubbing")
			with open(output_videopath, "wb") as file:
				for chunk in stream:
					file.write(chunk)

			return f"/files/processed/{output_filename}"

		else:
			logger.info("Dubbing failed or timed out")
			processed_doc.activity = "Dubbing failed or timed out"
			processed_doc.save(ignore_permissions=True)
			frappe.db.commit()
			return {"status": "failed", "message": "Dubbing failed or timed out"}
	except Exception as e:
		logger.error(f"Error occurred during hindi dubbing : {e}")
		processed_doc.activity = "Error during dubbing"
		processed_doc.status = "failed"
		processed_doc.save(ignore_permissions=True)
		frappe.db.commit()
