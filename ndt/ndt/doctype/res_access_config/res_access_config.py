# Copyright (c) 2026, abyhay and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class ResAccessConfig(Document):
	def on_update(self):
		from ndt.gate import clear_cache
		clear_cache()

	def on_trash(self):
		from ndt.gate import clear_cache
		clear_cache()
