# Copyright (c) 2025, VT and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class ClientScriptLab(Document):
	def before_save(self):
		self.title=self.title.title()

	@frappe.whitelist()
	def get_discounted_price(self, price):
		discount=0.1
		return float(price) - (float(price)*discount)
	
	# for frappe.call, this function should be outside the class