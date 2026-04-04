import json
import subprocess

import frappe
from frappe.utils import now_datetime
from google.cloud import videointelligence_v1 as videointelligence

from my_app.api.v1.bhashini_tasks import text_translation

frappe.utils.logger.set_log_level("DEBUG")
logger = frappe.logger("onscreen_gai")
video_client = videointelligence.VideoIntelligenceServiceClient.from_service_account_json(
	frappe.conf.service_acc_keypath
)


VIDEO_WIDTH = 1920
VIDEO_HEIGHT = 1080

# FFMPEG FILTER CONFIG
FRAME_DURATION = 0.1
FONT_SIZE = 48
PADDING_X = 35
PADDING_Y = 20

EXCLUDE_WORDS = ["THE APPRENTICE PROJECT"]
translation_cache = {}
language_fonts_path = {
	"hi": "/usr/share/fonts/truetype/noto/NotoSansDevanagari-Bold.ttf",
	"mr": "/usr/share/fonts/truetype/noto/NotoSansDevanagari-Bold.ttf",
	"pa": "/usr/share/fonts/truetype/noto/NotoSansGurmukhi-Bold.ttf",
}


def populate_text_table(processed_docname: str, extracted_texts: list):
	try:
		processed_doc = frappe.get_doc("Processed Video Info", processed_docname)
		processed_doc.set("onscreen_texts", [])

		for i in extracted_texts:
			processed_doc.append(
				"onscreen_texts",
				{
					"text": i["text"],
					"translated_text": i["translated_text"],
					"start_time": i["start_time"],
					"end_time": i["end_time"],
					"frame_layout_data": i["frame_layout_data"],
				},
			)

		processed_doc.save(ignore_permissions=True)
		frappe.db.commit()
		logger.info("Successfully populated onscreen text table ")
	except Exception as e:
		logger.error("Error populating onscreen text table", e)
		frappe.throw(f"Failed to populate onscreen text table: {e}")


def screen_txtoverlay(vid_filename: str, tar_langcode: str, processed_docname: str):
	input_videopath = frappe.get_site_path("public", "files", "original", vid_filename)
	with open(input_videopath, "rb") as f:
		input_content = f.read()

	logger.info("Analyzing video layout...")
	operation = video_client.annotate_video(
		request={
			"features": [videointelligence.Feature.TEXT_DETECTION],
			"input_content": input_content,
		}
	)

	result = operation.result(timeout=600)
	logger.info("Analysis complete. Generating FFmpeg filters...")

	# PARSE JSON & GENERATE FILTERS DIRECTLY
	extracted_table_data = []
	annotation_result = result.annotation_results[0]

	for annotation in annotation_result.text_annotations:
		original_text = annotation.text.replace("\n", " ").strip()

		if original_text.upper() in EXCLUDE_WORDS or original_text.isdigit():
			continue

		# Check cache to avoid re-translating the same word
		if original_text not in translation_cache:
			translation_cache[original_text] = text_translation(
				original_text, tar_langcode, processed_docname
			)

		translated_text = translation_cache[original_text]

		for segment in annotation.segments:
			if not segment.frames:
				continue

			seg_start = segment.frames[0].time_offset.total_seconds()

			frame_data_list = []

			# TRACKING VARIABLES FOR GROUPING
			current_box_params = None
			group_start_time = 0.0
			group_end_time = 0.0

			for frame in segment.frames:
				frame_start_time = frame.time_offset.total_seconds()
				frame_end_time = frame_start_time + FRAME_DURATION

				box = frame.rotated_bounding_box.vertices

				# Convert normalized floats to absolute pixels
				xs = [v.x for v in box]
				ys = [v.y for v in box]

				x_min_px = int(min(xs) * VIDEO_WIDTH)
				y_min_px = int(min(ys) * VIDEO_HEIGHT)
				width_px = int((max(xs) - min(xs)) * VIDEO_WIDTH)
				height_px = int((max(ys) - min(ys)) * VIDEO_HEIGHT)

				# Apply padding
				bx = x_min_px - PADDING_X
				by = y_min_px - PADDING_Y
				bw = width_px + (PADDING_X * 2)
				bh = height_px + (PADDING_Y * 2)

				new_box_params = (bx, by, bw, bh)

				if current_box_params is None:
					# First frame in the segment
					current_box_params = new_box_params
					group_start_time = frame_start_time
					group_end_time = frame_end_time
				elif current_box_params == new_box_params and abs(frame_start_time - group_end_time) < 0.05:
					# Same coordinates AND consecutive timeframe
					group_end_time = frame_end_time
				else:
					# Box moved or time gap, save the previous group to list
					bx_c, by_c, bw_c, bh_c = current_box_params
					frame_data_list.append(
						{
							"start": group_start_time,
							"end": group_end_time,
							"bx": bx_c,
							"by": by_c,
							"bw": bw_c,
							"bh": bh_c,
						}
					)

					# Start tracking the new group
					current_box_params = new_box_params
					group_start_time = frame_start_time
					group_end_time = frame_end_time

			# FLUSH THE FINAL GROUP
			if current_box_params is not None:
				bx_c, by_c, bw_c, bh_c = current_box_params
				frame_data_list.append(
					{
						"start": group_start_time,
						"end": group_end_time,
						"bx": bx_c,
						"by": by_c,
						"bw": bw_c,
						"bh": bh_c,
					}
				)

			# Define exact seg_end based on the last tracked group for accuracy
			seg_end = (
				group_end_time
				if current_box_params
				else segment.frames[-1].time_offset.total_seconds() + FRAME_DURATION
			)

			extracted_table_data.append(
				{
					"text": original_text,
					"translated_text": translated_text,
					"start_time": seg_start,
					"end_time": seg_end,
					"frame_layout_data": json.dumps(frame_data_list),
				}
			)

	if extracted_table_data:
		populate_text_table(processed_docname, extracted_table_data)


def apply_onscreentext(vid_filename: str, processed_docname: str, tar_langcode: str):
	processed_doc = frappe.get_doc("Processed Video Info", processed_docname)
	FONT_PATH = language_fonts_path.get(tar_langcode)
	input_videopath = frappe.get_site_path("public", "files", "processed", vid_filename)
	output_videopath = frappe.get_site_path("public", "files", f"onscreen_{vid_filename}")
	logger.info(output_videopath)
	filter_name = (f"filters_{vid_filename}").replace("mp4", "txt")
	filters_path = frappe.get_site_path("public", "files", filter_name)
	logger.info(f"filters path: {filters_path}")

	filters = []

	for row in processed_doc.onscreen_texts:
		final_text = row.translated_text
		if not final_text:
			continue

		frame_data_list = json.loads(row.frame_layout_data)

		for frame in frame_data_list:
			bx, by, bw, bh = frame["bx"], frame["by"], frame["bw"], frame["bh"]
			st, et = frame["start"], frame["end"]

			# Drawbox filter
			box_cmd = f"drawbox=x={bx}:y={by}:w={bw}:h={bh}:color=white@1.0:t=fill:enable='between(t,{st:.2f},{et:.2f})'"

			# Drawtext filter (Auto-centered)
			txt_x = f"{bx}+({bw}-tw)/2"
			txt_y = f"{by}+({bh}-th)/2"
			txt_cmd = f"drawtext=fontfile='{FONT_PATH}':text='{final_text}':x={txt_x}:y={txt_y}:fontsize={FONT_SIZE}:fontcolor=black:enable='between(t,{st:.2f},{et:.2f})'"

			filters.extend([box_cmd, txt_cmd])

	with open(filters_path, "w", encoding="utf-8") as out:
		out.write(",\n".join(filters))

	try:
		if filters_path:
			logger.info("Running subprocess command")
			subprocess.run(
				[
					"ffmpeg",
					"-y",
					"-nostdin",
					"-i",
					input_videopath,
					"-filter_complex_script",
					filters_path,
					"-c:a",
					"copy",
					output_videopath,
				],
				check=True,
				capture_output=True,
				text=True,
			)
			processed_doc.localized_vid = f"/files/onscreen_{vid_filename}"
			processed_doc.activity = "Onscreen text translation Completed"
			processed_doc.status = "success"
			processed_doc.percent = 100
			processed_doc.processed_on = now_datetime()
			processed_doc.save(ignore_permissions=True)
			frappe.db.commit()
	except subprocess.CalledProcessError as e:
		logger.error(f"ffmpeg process error during onscreen text muxing: {e}")
		frappe.throw(f"Error during onscreen text muxing: {e}")
