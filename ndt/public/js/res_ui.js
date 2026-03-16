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
        ".menu-btn-group { display: none !important; }"
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

        // ── 3. Client-side boot cleanup ──────────────────────────────
        // Some boot fields are set AFTER boot_session hook runs.
        if (frappe.boot) {
            frappe.boot.frequently_visited_links = [];
            frappe.boot.link_preview_doctypes = [];
        }

        // ── 4. Hide "Toggle Sidebar" from dropdown menus ─────────────
        var observer = new MutationObserver(function () {
            document.querySelectorAll(".dropdown-item").forEach(function (el) {
                if (el.textContent.trim().indexOf("Toggle Sidebar") > -1) {
                    el.style.display = "none";
                }
            });
        });
        observer.observe(document.body, { childList: true, subtree: true });
    }

    $(document).on("startup_setup_complete", setup_res_user);
    $(function () { setTimeout(setup_res_user, 300); });
})();
