app_name = "ndt"
app_title = "NDT"
app_publisher = "abyhay"
app_description = "NDT"
app_email = "abhay@gmail.com"
app_license = "mit"

# Apps
# ------------------

# required_apps = []

# Each item in the list will be shown as an app in the apps page
# add_to_apps_screen = [
# 	{
# 		"name": "ndt",
# 		"logo": "/assets/ndt/logo.png",
# 		"title": "NDT",
# 		"route": "/ndt",
# 		"has_permission": "ndt.api.permission.has_app_permission"
# 	}
# ]

# Includes in <head>
# ------------------

# include js, css files in header of desk.html
# app_include_css = "/assets/ndt/css/ndt.css"
app_include_js = "/assets/ndt/js/res_ui.js"

# Fixtures
# --------
# Records that are automatically synced to the database on bench migrate.
# Custom DocPerm: gives 'res' role read access to Website Settings
# so the desk splash image renders correctly for res users.
fixtures = [
    # The 'res' role — gate.py checks for this role on every request
    {"dt": "Role", "filters": [["role_name", "=", "res"]]},
    # res role read access to Website Settings (splash screen renders correctly)
    {"dt": "Custom DocPerm", "filters": [["parent", "=", "Website Settings"], ["role", "=", "res"]]},
    # Whitelist of doctypes and routes accessible to res role users
    {"dt": "Res Access Config"},
]

# include js, css files in header of web template
# web_include_css = "/assets/ndt/css/ndt.css"
# web_include_js = "/assets/ndt/js/ndt.js"

# include custom scss in every website theme (without file extension ".scss")
# website_theme_scss = "ndt/public/scss/website"

# include js, css files in header of web form
# webform_include_js = {"doctype": "public/js/doctype.js"}
# webform_include_css = {"doctype": "public/css/doctype.css"}

# include js in page
# page_js = {"page" : "public/js/file.js"}

# include js in doctype views
# doctype_js = {"doctype" : "public/js/doctype.js"}
# doctype_list_js = {"doctype" : "public/js/doctype_list.js"}
# doctype_tree_js = {"doctype" : "public/js/doctype_tree.js"}
# doctype_calendar_js = {"doctype" : "public/js/doctype_calendar.js"}

# Svg Icons
# ------------------
# include app icons in desk
# app_include_icons = "ndt/public/icons.svg"

# Home Pages
# ----------

# application home page (will override Website Settings)
# home_page = "login"

# website user home page (by Role)
# role_home_page = {
# 	"Role": "home_page"
# }

# Generators
# ----------

# automatically create page for each record of this doctype
# website_generators = ["Web Page"]

# Jinja
# ----------

# add methods and filters to jinja environment
# jinja = {
# 	"methods": "ndt.utils.jinja_methods",
# 	"filters": "ndt.utils.jinja_filters"
# }

# Installation
# ------------

# before_install = "ndt.install.before_install"
# after_install = "ndt.install.after_install"

# Uninstallation
# ------------

# before_uninstall = "ndt.uninstall.before_uninstall"
# after_uninstall = "ndt.uninstall.after_uninstall"

# Integration Setup
# ------------------
# To set up dependencies/integrations with other apps
# Name of the app being installed is passed as an argument

# before_app_install = "ndt.utils.before_app_install"
# after_app_install = "ndt.utils.after_app_install"

# Integration Cleanup
# -------------------
# To clean up dependencies/integrations with other apps
# Name of the app being uninstalled is passed as an argument

# before_app_uninstall = "ndt.utils.before_app_uninstall"
# after_app_uninstall = "ndt.utils.after_app_uninstall"

# Desk Notifications
# ------------------
# See frappe.core.notifications.get_notification_config

# notification_config = "ndt.notifications.get_notification_config"

# Permissions
# -----------
# Permissions evaluated in scripted ways

# permission_query_conditions = {
# 	"Event": "frappe.desk.doctype.event.event.get_permission_query_conditions",
# }
#
# has_permission = {
# 	"Event": "frappe.desk.doctype.event.event.has_permission",
# }

# DocType Class
# ---------------
# Override standard doctype classes

# override_doctype_class = {
# 	"ToDo": "custom_app.overrides.CustomToDo"
# }

# Document Events
# ---------------
# Hook on document methods and events

# doc_events = {
# 	"*": {
# 		"on_update": "method",
# 		"on_cancel": "method",
# 		"on_trash": "method"
# 	}
# }

# Scheduled Tasks
# ---------------

# scheduler_events = {
# 	"all": [
# 		"ndt.tasks.all"
# 	],
# 	"daily": [
# 		"ndt.tasks.daily"
# 	],
# 	"hourly": [
# 		"ndt.tasks.hourly"
# 	],
# 	"weekly": [
# 		"ndt.tasks.weekly"
# 	],
# 	"monthly": [
# 		"ndt.tasks.monthly"
# 	],
# }

# Testing
# -------

# before_tests = "ndt.install.before_tests"

# Overriding Methods
# ------------------------------
#
# override_whitelisted_methods = {
# 	"frappe.desk.doctype.event.event.get_events": "ndt.event.get_events"
# }
#
# each overriding function accepts a `data` argument;
# generated from the base implementation of the doctype dashboard,
# along with any modifications made in other Frappe apps
# override_doctype_dashboards = {
# 	"Task": "ndt.task.get_dashboard_data"
# }

# exempt linked doctypes from being automatically cancelled
#
# auto_cancel_exempted_doctypes = ["Auto Repeat"]

# Ignore links to specified DocTypes when deleting documents
# -----------------------------------------------------------

# ignore_links_on_delete = ["Communication", "ToDo"]

# Request Events
# ----------------
before_request = ["ndt.gate.before_request"]
boot_session = ["ndt.gate.boot_session"]
after_request = ["ndt.gate.after_request"]

# Job Events
# ----------
# before_job = ["ndt.utils.before_job"]
# after_job = ["ndt.utils.after_job"]

# User Data Protection
# --------------------

# user_data_fields = [
# 	{
# 		"doctype": "{doctype_1}",
# 		"filter_by": "{filter_by}",
# 		"redact_fields": ["{field_1}", "{field_2}"],
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_2}",
# 		"filter_by": "{filter_by}",
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_3}",
# 		"strict": False,
# 	},
# 	{
# 		"doctype": "{doctype_4}"
# 	}
# ]

# Authentication and authorization
# --------------------------------

# auth_hooks = [
# 	"ndt.auth.validate"
# ]

# Automatically update python controller files with type annotations for this app.
# export_python_type_annotations = True

# default_log_clearing_doctypes = {
# 	"Logging DocType Name": 30  # days to retain logs
# }

# Translation
# ------------
# List of apps whose translatable strings should be excluded from this app's translations.
# ignore_translatable_strings_from = []

