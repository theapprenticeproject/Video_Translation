# Copyright (c) 2025, VT and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from collections import defaultdict

class Review(Document):
	def after_insert(self):
		reviews=frappe.get_all(
			"Review",
			fields=["reviewer_prof","rating"]
		)

		if reviews:
			reviews_data=defaultdict(list)
			for r in reviews:
				reviewer=r["reviewer_prof"]
				if not reviewer:
					continue
				reviews_data[reviewer].append(r["rating"])
			
			for i, j in reviews_data.items():
				total_count=len(j)
				avg_rating=sum(j)/total_count
				frappe.db.set_value("Reviewer Profile", i, {"total_reviews": total_count, "avg_rate_given":avg_rating})
														

		articles_info=frappe.get_all("Review", filters={"article":self.article}, fields=["rating"])
		if articles_info:	
			total=sum([r["rating"] for r in articles_info])
			count=len(articles_info)
			avg=total/count
			frappe.db.set_value("Article", self.article, {"avg_rating": avg, "no_of_times_reviewed":count})		