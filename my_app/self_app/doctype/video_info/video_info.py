# Copyright (c) 2025, VT and contributors
# For license information, please see license.txt

import os

import frappe
from frappe.model.document import Document

from my_app.helper.file_naming import file_retitling


class VideoInfo(Document):
	def on_update(self):
		if self.original_vid and not self.original_audio_extracted and "original/" not in self.original_vid:
			try:
				num_name = self.name.replace(self.title + "-", "")

				file_info = file_retitling(
					self.original_vid, "original", num_name
				)  # passing the record's number

				self.db_set("original_vid", file_info["new_file_url_doc"], commit=True)

				frappe.publish_realtime(
					event="video_file_structured",
					message={
						"videofile_url": file_info["new_file_url_doc"],
						"video_info_docname": self.name,
					},
				)

			except Exception as e:
				frappe.throw(f"Error updating video info process: {e}")

	def on_trash(self):
		# Delete original video file
		if self.original_vid:
			file_path = frappe.get_site_path("public", self.original_vid.lstrip("/"))
			if os.path.exists(file_path):
				try:
					os.remove(file_path)
					frappe.msgprint(f"Deleted video file: {file_path}")
				except Exception as e:
					frappe.log_error(f"Failed to delete video file {file_path}: {e}", frappe.get_traceback())
					frappe.msgprint(f"Warning: Could not delete video file {self.original_vid}", alert=True)

		# Delete extracted audio file
		if self.original_audio_extracted:
			audio_path = frappe.get_site_path("public", self.original_audio_extracted.lstrip("/"))
			if os.path.exists(audio_path):
				try:
					os.remove(audio_path)
					frappe.msgprint(f"Deleted audio file: {audio_path}")
				except Exception as e:
					frappe.log_error(f"Failed to delete audio file {audio_path}: {e}", frappe.get_traceback())
					frappe.msgprint(
						f"Warning: Could not delete audio file {self.original_audio_extracted}", alert=True
					)
