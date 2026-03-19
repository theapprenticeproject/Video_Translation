import subprocess

import frappe
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
# FONT_PATH = "/usr/share/fonts/truetype/noto/NotoSansDevanagari-Bold.ttf"  # for marathi
FRAME_DURATION = 0.1
FONT_SIZE = 48
PADDING_X = 35
PADDING_Y = 20

EXCLUDE_WORDS = [
	"THE APPRENTICE PROJECT",
	"BUDGET",
	"EDUCATION",
	"REGISTER NOW",
	"NOW",
	"FINANCIAL LITERACY COURSE",
]
translation_cache = {}
language_fonts_path = {
	"mr": "/usr/share/fonts/truetype/noto/NotoSansDevanagari-Bold.ttf",
	"pa": "/usr/share/fonts/truetype/noto/NotoSansGurmukhi-Bold.ttf",
}


def screen_txtoverlay(vid_filename: str, tar_langcode: str, processed_docname: str):
	FONT_PATH = language_fonts_path.get(tar_langcode)
	input_videopath = frappe.get_site_path("public", "files", "original", vid_filename)
	output_videopath = frappe.get_site_path("public", "files", "processed", f"labs_sts_{vid_filename}")
	filters_path = frappe.get_site_path("public", "files", "filter_overlay.txt")
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
	filters = []
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
			for frame in segment.frames:
				start_time = frame.time_offset.total_seconds()
				end_time = start_time + FRAME_DURATION

				box = frame.rotated_bounding_box.vertices

				# Convert normalized floats to absolute pixels
				xs = [v.x for v in box]
				ys = [v.y for v in box]

				x_min_px = int(min(xs) * VIDEO_WIDTH)
				y_min_px = int(min(ys) * VIDEO_HEIGHT)
				width_px = int((max(xs) - min(xs)) * VIDEO_WIDTH)
				height_px = int((max(ys) - min(ys)) * VIDEO_HEIGHT)

				# Apply padding for FFmpeg
				bx = x_min_px - PADDING_X
				by = y_min_px - PADDING_Y
				bw = width_px + (PADDING_X * 2)
				bh = height_px + (PADDING_Y * 2)

				# Drawbox filter
				box_cmd = f"drawbox=x={bx}:y={by}:w={bw}:h={bh}:color=white@1.0:t=fill:enable='between(t,{start_time:.2f},{end_time:.2f})'"

				# Drawtext filter (Auto-centered)
				txt_x = f"{bx}+({bw}-tw)/2"
				txt_y = f"{by}+({bh}-th)/2"
				txt_cmd = f"drawtext=fontfile='{FONT_PATH}':text='{translated_text}':x={txt_x}:y={txt_y}:fontsize={FONT_SIZE}:fontcolor=black:enable='between(t,{start_time:.2f},{end_time:.2f})'"

				filters.extend([box_cmd, txt_cmd])

	with open(filters_path, "w", encoding="utf-8") as out:
		out.write(",\n".join(filters))

	try:
		logger.info("Running subprocess command")
		subprocess.run(
			[
				"ffmpeg",
				"-y",
				"-nostdin",
				"i",
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
	except subprocess.CalledProcessError as e:
		logger.error(f"ffmpeg process error during onscreen text muxing: {e}")
		frappe.throw(f"Error during onscreen text muxing: {e}")


logger.info("Pipeline finished generated.")
