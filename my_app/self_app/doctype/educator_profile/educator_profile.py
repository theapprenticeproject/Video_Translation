# Copyright (c) 2025, VT and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
import frappe.model.naming


class EducatorProfile(Document):
	def autoname(self):
		initials=''.join(i[0].upper() for i in self.full_name.split())
		number=frappe.model.naming.make_autoname("EDU-.####")

		self.name=f'{initials}-{number.split("-")[-1]}'

	