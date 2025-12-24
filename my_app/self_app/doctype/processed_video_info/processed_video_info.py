# Copyright (c) 2025, VT and contributors
# For license information, please see license.txt

import frappe
import frappe.model.naming
from frappe.model.document import Document


class ProcessedVideoInfo(Document):
	def autoname(self):
		video_info = self.origin_vid_link
		if video_info:
			video_lang = frappe.db.get_value("Video Info", video_info, "target_lang")
			number = frappe.model.naming.make_autoname("VID-.#####")
			self.name = f"{video_lang}-{video_info}-{number.split('-')[-1]}"
