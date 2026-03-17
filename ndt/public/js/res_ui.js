// res_ui.js — Client-side UI cleanup for res role users

(function () {
    "use strict";

    // ── 1. Hide unwanted UI elements immediately (before DOM paint) ──
    var style = document.createElement("style");
    style.id = "ndt-res-hide";
    style.innerHTML = [
        ".dropdown-help { display: none !important; }",
        ".layout-side-section { display: none !important; }",
        ".sidebar-toggle-btn { display: none !important; }",
        ".col-lg-2.layout-side-section { display: none !important; }",
        ".layout-main-section-wrapper.col-lg-10 { flex: 0 0 100%; max-width: 100%; }",
        ".layout-main-section-wrapper { flex: 0 0 100%; max-width: 100%; }",
        ".menu-btn-group { display: none !important; }",
        // Print icon in form toolbar
        // Bootstrap tooltip moves title → data-original-title, so target both
        ".page-icon-group button[data-original-title='Print'] { display: none !important; }",
        ".page-icon-group button[title='Print'] { display: none !important; }",
        // Print preview and printview pages
        ".page-container[data-page-route='print'] { display: none !important; }",
        ".page-container[data-page-route='printview'] { display: none !important; }",
        // Inline print buttons (print_layout.html)
        ".btn-print-print { display: none !important; }",
        ".btn-download-pdf { display: none !important; }",
        ".btn-print-preview { display: none !important; }"
    ].join("\n");
    document.head.appendChild(style);

    // ── 2. Restore UI for non-res users once roles are known ─────────
    function setup_res_user() {
        var roles = frappe.user_roles || [];
        var user = frappe.session && frappe.session.user;

        var isResUser = roles.includes("res") &&
            user !== "Administrator" &&
            !roles.includes("System Manager");

        if (!isResUser) {
            var el = document.getElementById("ndt-res-hide");
            if (el) el.parentNode.removeChild(el);
            return;
        }

        // ── 3. Mark body so CSS can scope all res-user overrides ─────
        document.body.classList.add("res-user");

        // ── 4. Client-side boot cleanup ──────────────────────────────
        if (frappe.boot) {
            frappe.boot.frequently_visited_links = [];
            frappe.boot.link_preview_doctypes = [];
        }

        // ── 5. Hide text-matched items from dropdown menus ───────────
        // CSS cannot match by text content, so we use MutationObserver.
        // Targets: "Toggle Sidebar" and "Print" in any dropdown.
        var HIDDEN_LABELS = ["Toggle Sidebar", "Print"];

        var observer = new MutationObserver(function () {
            document.querySelectorAll(".dropdown-item").forEach(function (el) {
                var text = el.textContent.trim();
                HIDDEN_LABELS.forEach(function (label) {
                    if (text.indexOf(label) > -1) {
                        el.style.display = "none";
                    }
                });
            });
        });
        observer.observe(document.body, { childList: true, subtree: true });
    }

    $(document).on("startup_setup_complete", setup_res_user);
    $(function () { setTimeout(setup_res_user, 300); });
})();
