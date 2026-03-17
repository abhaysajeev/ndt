# Copyright (c) 2026, abyhay and contributors
# For license information, please see license.txt
#
# gate.py — Res User Isolation Layer
#
# This module is the single gating function for the res role isolation layer.
# It is called on every HTTP request via the before_request hook.
#
# Design:
#   - If user has no 'res' role → pass through (admin, all other users unaffected)
#   - If user has 'res' role → check path against whitelist (Redis-cached)
#   - If path not whitelisted → abort with 404
#   - Fail open for infra/auth paths, fail closed for everything else

import frappe
from frappe import _
from werkzeug.exceptions import NotFound
from werkzeug.routing import RequestRedirect as WerkzeugRedirect

CACHE_KEY = "ndt_res_whitelist"

# ---------------------------------------------------------------------------
# These paths are ALWAYS allowed for res users regardless of config.
# Only true infrastructure paths belong here — NOT data-reading methods.
# ---------------------------------------------------------------------------
ALWAYS_ALLOWED_PREFIXES = [
	# Root-level browser auto-requests
	"/favicon.ico",
	"/favicon.png",
	"/manifest.json",
	"/robots.txt",
	"/service_worker.js",
	"/sw.js",
	"/api/method/frappe.ping",

	# Static assets
	"/assets/",
	"/files/",
	"/private/files/",

	# Auth & session
	"/login",
	"/update-password",
	"/api/method/login",
	"/api/method/logout",
	"/api/method/web_logout",
	"/api/method/frappe.auth.",
	"/api/method/frappe.client.get_password",
	"/api/method/frappe.core.doctype.user.",
	"/api/method/frappe.sessions.",
	"/api/method/frappe.website.",
	"/api/method/frappe.realtime.",

	# Desk infrastructure — UI-only, no data reads
	"/api/method/frappe.desk.desktop.",       # workspace sidebar/layout
	"/api/method/frappe.desk.desk_page.",     # desk page loader
	"/api/method/frappe.desk.listview.get_list_settings",  # UI config only
	"/api/method/frappe.desk.notifications.", # notification counts/list
	"/api/method/frappe.desk.tags.",          # tag UI
	"/api/method/frappe.desk.like.",          # like UI
	"/api/method/frappe.desk.comments.",      # comments UI
	"/api/method/frappe.desk.doctype.",       # doctype metadata
	"/api/method/frappe.model.",              # model metadata
	"/api/method/frappe.apps.",               # app list/metadata (needed for UI)

	# Number Card API - needed for workspace cards to load data
	"/api/method/frappe.desk.doctype.number_card.number_card.",

	# MT Inspection report PDF download
	"/api/method/alhoty.report_api.download_mt_report",

	# File management
	"/api/method/frappe.utils.file_manager.",
	"/api/method/frappe.core.api.file.",
	"/api/method/upload_file",
	
	# Search
	"/api/method/frappe.utils.global_search.",  # Ctrl+K awesome bar search

	# Background jobs & websocket
	"/api/method/frappe.utils.background_jobs.",
	"/socket.io",
	"/.well-known",
]

# ---------------------------------------------------------------------------
# These API methods carry the target doctype as a request param (POST body or
# query string), NOT in the URL path. We must inspect the doctype param and
# check it against the whitelist rather than letting them pass blindly.
# ---------------------------------------------------------------------------
DOCTYPE_PARAM_METHODS = [
	"/api/method/frappe.desk.form.load.",
	"/api/method/frappe.desk.form.save.",
	"/api/method/frappe.desk.form.utils.",
	"/api/method/frappe.desk.reportview.",
	"/api/method/frappe.desk.search.",
	"/api/method/frappe.client.get",
	"/api/method/frappe.client.get_list",
	"/api/method/frappe.client.get_count",
	"/api/method/frappe.client.set_value",
	"/api/method/frappe.client.save",
	"/api/method/frappe.client.submit",
	"/api/method/frappe.client.cancel",
	"/api/method/frappe.client.delete",
	"/api/method/frappe.client.bulk_insert",
	"/api/method/frappe.client.validate",
	"/api/method/frappe.client.attach_file",

	# Print / PDF — doctype is an explicit param
	"/api/method/frappe.utils.print_format.download_pdf",
	"/api/method/frappe.utils.weasyprint.",
]

# ---------------------------------------------------------------------------
# Query report methods carry report_name, not doctype. We look up the
# report's ref_doctype and check that against the whitelist.
# ---------------------------------------------------------------------------
REPORT_METHODS = [
	"/api/method/frappe.desk.query_report.run",
	"/api/method/frappe.desk.query_report.export_query",
	"/api/method/frappe.desk.query_report.get_script",
]

# ---------------------------------------------------------------------------
# Internal Frappe doctypes used by the desk UI itself. These are NOT user data
# — they're plumbing (filters, settings, etc.) that must always pass through
# the doctype-param check regardless of the whitelist.
# ---------------------------------------------------------------------------
INFRASTRUCTURE_DOCTYPES = {
	"List Filter",          # saved list-view filters
	"List View Settings",   # list-view column config
	"Notification Settings",
	"User Settings",
	"Energy Point Rule",
	"Comment",
	"Version",
	"Activity Log",
	"Communication",
	"File",
	"Tag",
	"Note",
	"Website Settings",     # read-only site config — needed for splash image, theming
	"User",                 # User doctype access for profile/settings (consistent with line 49 always-allowed path)
}


def before_request():
	"""
	Called on every HTTP request via hooks.py before_request.
	Gates access for res role users based on whitelist config.
	"""
	try:
		# Guard: only act if Frappe is fully initialized for this request
		if not getattr(frappe.local, "session", None):
			return
		if not getattr(frappe.local.session, "user", None):
			return

		user = frappe.local.session.user

		# Guest / unauthenticated — let Frappe handle normally
		if not user or user == "Guest":
			return

		# Administrator is always exempt — also, frappe.get_roles("Administrator")
		# returns ALL roles (including res), so we must check this explicitly first.
		if user == "Administrator":
			return

		# Check roles using in-memory session data (no DB call)
		user_roles = frappe.get_roles(user)

		# If user is not a res user → pass through completely
		if "res" not in user_roles:
			return

		# --- User has 'res' role. Apply gating. ---

		path = frappe.local.request.path

		# 1. Check hardcoded infra passthrough list first (fast, no cache)
		if _is_always_allowed(path):
			return

		# 2. Redirect res users away from Frappe's website/portal pages to the desk.
		#    Portal pages are any path that isn't /app, /api, or an asset.
		#    They serve no purpose in the res isolation layer.
		if not (
			path.startswith("/app")
			or path.startswith("/api")
			or path.startswith("/assets")
			or path.startswith("/files")
			or path.startswith("/private")
			or path.startswith("/socket.io")
		):
			raise WerkzeugRedirect("/app")

		# 3. Load whitelist from Redis (or DB if cache miss)
		whitelist = _get_whitelist()

		# 3. Check doctype-param methods — gate by the doctype in the request
		for method_prefix in DOCTYPE_PARAM_METHODS:
			if path.startswith(method_prefix):
				requested_doctype = _get_request_doctype()
				if not requested_doctype:
					# No doctype param → let the method handle it (e.g. ping, utils)
					return
				if _is_doctype_allowed(requested_doctype, whitelist):
					return
				frappe.logger("ndt.gate").warning(
					f"RES GATE BLOCKED (doctype param): user={user} path={path} doctype={requested_doctype}"
				)
				raise NotFound()

		# 4. Check report methods — report_name → ref_doctype → whitelist
		for method_prefix in REPORT_METHODS:
			if path.startswith(method_prefix):
				report_name = (
					frappe.local.form_dict.get("report_name")
					or frappe.local.request.args.get("report_name")
				)
				if not report_name:
					# No report_name → block (can't determine what data it reads)
					frappe.logger("ndt.gate").warning(
						f"RES GATE BLOCKED (report, no name): user={user} path={path}"
					)
					raise NotFound()
				# Look up the report's ref_doctype
				ref_doctype = frappe.db.get_value("Report", report_name, "ref_doctype")
				if ref_doctype and _is_doctype_allowed(ref_doctype, whitelist):
					return
				frappe.logger("ndt.gate").warning(
					f"RES GATE BLOCKED (report): user={user} path={path} report={report_name} ref_doctype={ref_doctype}"
				)
				raise NotFound()

		# 5. Check path against whitelist (URL-based routes + /api/resource/)
		if _is_path_allowed(path, whitelist):
			return

		# 6. Not allowed → 404
		frappe.logger("ndt.gate").warning(f"RES GATE BLOCKED: user={user} path={path}")
		raise NotFound()

	except (NotFound, WerkzeugRedirect):
		raise  # propagate up to frappe/app.py handler — both are HTTPException
	except Exception:
		# On any unexpected error, fail open (log but don't crash the app)
		frappe.logger("ndt.gate").exception("Unexpected error in res gating, failing open")


def _is_always_allowed(path: str) -> bool:
	"""Check if path matches any hardcoded infra passthrough prefix."""
	for prefix in ALWAYS_ALLOWED_PREFIXES:
		if path.startswith(prefix):
			return True
	return False


def _get_request_doctype() -> str | None:
	"""Extract doctype from request query string or POST form dict."""
	try:
		return (
			frappe.local.form_dict.get("doctype")
			or frappe.local.request.args.get("doctype")
		)
	except Exception:
		return None


def _is_doctype_allowed(doctype: str, whitelist: dict) -> bool:
	"""Check if a specific doctype is in the whitelist or is infrastructure."""
	dt = doctype.strip()
	if dt in INFRASTRUCTURE_DOCTYPES:
		return True
	return dt in set(whitelist.get("doctypes", []))


def _get_whitelist() -> dict:
	"""
	Load whitelist from Redis. On cache miss, read from DB and cache it.
	Returns a dict with keys: 'doctypes' (list), 'extra_routes' (list of prefixes)
	"""
	cached = frappe.cache.get_value(CACHE_KEY)
	if cached:
		return cached

	return _rebuild_cache()


def _rebuild_cache() -> dict:
	"""Read config from DB, build whitelist, store in Redis, return it."""
	try:
		config = frappe.get_single("Res Access Config")

		allowed_doctypes = {
			row.doctype_name.strip()
			for row in (config.allowed_doctypes or [])
			if row.doctype_name
		}

		extra_routes = [
			row.route_prefix.strip()
			for row in (config.allowed_routes or [])
			if row.route_prefix
		]

	except Exception:
		# Config doesn't exist or can't be read → deny everything
		allowed_doctypes = set()
		extra_routes = []

	whitelist = {
		"doctypes": list(allowed_doctypes),
		"extra_routes": extra_routes,
	}

	frappe.cache.set_value(CACHE_KEY, whitelist, expires_in_sec=3600)
	return whitelist


def _is_path_allowed(path: str, whitelist: dict) -> bool:
	"""
	Check if the requested path is allowed for a res user.

	Matching order:
	  1. Exact root / /app paths
	  2. Extra explicit route prefixes from config
	  3. Auto-derived /app/<doctype-route> from allowed doctypes
	  4. Auto-derived /api/resource/<DocType> from allowed doctypes
	"""
	allowed_doctypes = whitelist.get("doctypes", [])
	extra_routes = whitelist.get("extra_routes", [])

	# 1. Always allow root and ALL /app/* paths.
	#    Frappe's desk is a SPA — the server serves the same desk.html for every
	#    /app/* path. Blocking here causes 404 on direct URL entry or page refresh.
	#    Security is enforced at the API layer (doctype-param checks + /api/resource/).
	if path == "/" or path.startswith("/app"):
		return True

	# 2. Extra explicit routes (admin-configured)
	for prefix in extra_routes:
		if path.startswith(prefix):
			return True

	# 3. Auto-derive from allowed doctypes
	for doctype_name in allowed_doctypes:
		# /app/<frappe-route> — Frappe converts "My DocType" → "my-doctype"
		app_route = "/app/" + _doctype_to_route(doctype_name)
		if path.startswith(app_route):
			return True

		# /api/resource/<DocType>
		api_route = "/api/resource/" + doctype_name
		if path.startswith(api_route):
			return True

		# /api/resource/<DocType%20Name> — URL-encoded version
		api_route_encoded = "/api/resource/" + doctype_name.replace(" ", "%20")
		if path.startswith(api_route_encoded):
			return True

	return False


def _doctype_to_route(doctype_name: str) -> str:
	"""Convert a DocType name to its Frappe desk route slug.
	e.g. 'Sales Invoice' → 'sales-invoice'
	     'NDT Report'    → 'ndt-report'
	"""
	return doctype_name.lower().replace(" ", "-")


def clear_cache():
	"""Clear the res whitelist cache. Called from Res Access Config on_update/on_trash."""
	frappe.cache.delete_value(CACHE_KEY)


def boot_session(bootinfo):
	"""
	boot_session hook — filters frappe.boot payload for res-only users.
	Called by Frappe once per login after the boot dict is fully built.

	What this filters for res users:
	  - bootinfo.user.can_read / can_write / can_create / can_export / can_import / can_print
	    → drives the awesome bar and all link-field autocomplete
	  - bootinfo.allowed_workspaces
	    → drives the desk sidebar (Frappe v15 workspace-based navigation)
	  - bootinfo.module_wise_workspaces
	    → secondary grouping used by the sidebar

	Edge cases:
	  - Administrator   → always full boot (skip)
	  - System Manager  → always full boot (skip, covers other admins)
	  - No 'res' role   → unused hook, return immediately
	  - Empty whitelist → all permission lists become empty (nothing visible)
	  - 'Res Home' workspace missing → fallback: clear sidebar rather than crash
	  - Any exception   → fail open, log, never crash the login
	"""
	try:
		if not bootinfo:
			return

		user = frappe.session.user

		# Administrator always gets the full unfiltered boot
		if user == "Administrator":
			return

		user_roles = frappe.get_roles(user)

		# System Manager = admin — always full boot
		if "System Manager" in user_roles:
			return

		# Only apply to res users
		if "res" not in user_roles:
			return

		# ── res user: apply filtering ─────────────────────────────────────────

		whitelist = _get_whitelist()
		allowed_doctypes = set(whitelist.get("doctypes", []))
		
		# Include infrastructure doctypes in the allowed set for boot filtering
		allowed_doctypes_with_infra = allowed_doctypes | INFRASTRUCTURE_DOCTYPES

		# 1. Permission lists — drive the awesome bar and link-field autocomplete
		#    bootinfo.user is a frappe._dict / object, use .get() safely
		user_boot = bootinfo.get("user") or frappe._dict()
		for perm_key in ("can_read", "can_write", "can_create", "can_export", "can_import", "can_print"):
			raw = user_boot.get(perm_key)
			if isinstance(raw, (list, tuple)):
				user_boot[perm_key] = [dt for dt in raw if dt in allowed_doctypes_with_infra]

		# 2. Workspace sidebar (Frappe v15)
		#    allowed_workspaces is a list of dicts like [{"name": "Welcome Workspace", ...}]
		#    We keep only "NDT Portal" for res users, fallback to "Welcome Workspace"
		if "allowed_workspaces" in bootinfo:
			all_ws = bootinfo.get("allowed_workspaces") or []
			# Look for NDT Portal first
			ndt_portal = [ws for ws in all_ws if ws.get("name") == "NDT Portal"]
			if ndt_portal:
				bootinfo["allowed_workspaces"] = ndt_portal
			else:
				# Fallback: keep Welcome Workspace
				fallback = [ws for ws in all_ws if ws.get("name") == "Welcome Workspace"]
				bootinfo["allowed_workspaces"] = fallback

		# 3. Module-wise workspace grouping — not needed for res users
		if "module_wise_workspaces" in bootinfo:
			bootinfo["module_wise_workspaces"] = {}

		# 4. Page info — pages like "user-profile", "leaderboard" show in awesome bar
		if "page_info" in bootinfo:
			bootinfo["page_info"] = {}

		# 5. Frequently visited links — stale history from before gating
		if "frequently_visited_links" in bootinfo:
			bootinfo["frequently_visited_links"] = []

		# 6. Single types — filter to only whitelisted + infrastructure
		if "single_types" in bootinfo:
			bootinfo["single_types"] = [
				dt for dt in bootinfo["single_types"]
				if dt in allowed_doctypes_with_infra
			]

		# 7. Doctype layouts
		if "doctype_layouts" in bootinfo:
			bootinfo["doctype_layouts"] = [
				dl for dl in bootinfo["doctype_layouts"]
				if dl.get("document_type") in allowed_doctypes_with_infra
			]

	except Exception:
		# Fail open — log the error but never crash the login flow
		frappe.logger("ndt.gate").exception(
			"boot_session: unexpected error filtering boot for res user, failing open"
		)


def after_request(response):
	"""
	after_request hook — converts 403 (Forbidden) → 404 (Not Found) for res users.

	Why: Frappe's client-side 403 handler shows "Not permitted" with detailed
	role/doctype info (leaks internal structure). The 404 handler shows a clean
	"Not found" message. By converting server-side, we avoid the info leak entirely.

	Edge cases:
	  - Administrator → never touched
	  - System Manager → never touched
	  - Non-res users → never touched
	  - Login/session 403 → not converted (session user is Guest)
	  - Only API/method JSON calls are converted (not page-level HTML responses)
	"""
	try:
		if not response or response.status_code != 403:
			return

		user = getattr(frappe.session, "user", None)
		if not user or user == "Administrator":
			return

		user_roles = frappe.get_roles(user)
		if "res" not in user_roles or "System Manager" in user_roles:
			return

		# Only convert JSON API responses (not full page loads)
		content_type = response.headers.get("Content-Type", "")
		if "application/json" not in content_type:
			return

		# Log the 403 being converted for debugging
		path = getattr(frappe.local.request, "path", "unknown")
		frappe.logger("ndt.gate").warning(
			f"RES GATE 403→404 conversion: user={user} path={path}"
		)

		# Convert to 404 with clean message
		import json
		response.status_code = 404
		try:
			data = json.loads(response.get_data(as_text=True))
			# Remove all server messages that mention permissions
			data.pop("_server_messages", None)
			data.pop("_error_message", None)
			data.pop("exc", None)
			data.pop("exc_type", None)
			response.set_data(json.dumps(data))
		except Exception:
			pass  # if we can't parse, just change the status code

	except Exception:
		# Fail open — never break the response
		pass
