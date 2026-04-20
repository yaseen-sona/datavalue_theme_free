# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: MIT. See LICENSE

no_cache = 1

import json
import os
import re
import secrets
import colorsys
from dataclasses import fields
import frappe
import frappe.sessions
from frappe import _
from frappe.utils.jinja_globals import is_rtl
from frappe.model.utils.user_settings import get_user_settings, update_user_settings

SCRIPT_TAG_PATTERN = re.compile(r"\<script[^<]*\</script\>")
CLOSING_SCRIPT_TAG_PATTERN = re.compile(r"</script\>")


def get_context(context):
    if frappe.session.user == "Guest":
        frappe.throw(_("Log in to access this page."), frappe.PermissionError)
    elif (
            frappe.db.get_value("User", frappe.session.user, "user_type", order_by=None) == "Website User"
    ):
        frappe.throw(_("You are not permitted to access this page."), frappe.PermissionError)

    hooks = frappe.get_hooks()
    try:
        boot = frappe.sessions.get()
    except Exception as e:
        boot = frappe._dict(status="failed", error=str(e))
        print(frappe.get_traceback())

    # this needs commit
    csrf_token = frappe.sessions.get_csrf_token()

    boot_json = frappe.as_json(boot, indent=None, separators=(",", ":"))

    # remove script tags from boot
    boot_json = SCRIPT_TAG_PATTERN.sub("", boot_json)

    # get theme settings
    frappe.db.commit()

    theme_settings_list = {}

    theme_settings = frappe.db.sql(""" SELECT *
                                       FROM tabSingles
                                       WHERE doctype = 'Theme Settings'; """, as_dict=True)
    for theme_setting in theme_settings:
        theme_settings_list[theme_setting['field']] = theme_setting['value']
        if (theme_settings_list.get('language_switcher_type') and theme_settings_list.get('language_switcher_type') == 'Custom List'):
            languges_list = []
            get_languages = frappe.db.get_all('Theme Settings Languages', filters={'parent': 'Theme Settings'}, fields=["idx", "language", "language_icon"], order_by='idx asc')
            for language in get_languages:
                language.label = frappe.db.get_value('Language', language.language, 'language_name')
                languges_list.append(language);
            theme_settings_list['languages_list'] = languges_list
        if (theme_settings_list.get('add_custom_colors') and theme_settings_list.get('add_custom_colors') == "1"):
            custom_colors = []
            get_custom_colors = frappe.db.get_all('Theme Settings Colors', filters={'parent': 'Theme Settings'}, fields=["idx", "color_code", "color_name"], order_by='idx asc')
            for color in get_custom_colors:
                color.name = color.color_name.replace(' ', '-').lower()
                custom_colors.append(color);
            theme_settings_list['custom_colors'] = custom_colors
            if (theme_settings_list.get('add_custom_colors')):
                theme_settings_list['default_color_code'] = frappe.db.get_value('Theme Settings Colors', {'color_name': theme_settings_list.get('default_custom_color')}, 'color_code')

    # TODO: Find better fix
    boot_json = CLOSING_SCRIPT_TAG_PATTERN.sub("", boot_json)
    boot_json = json.dumps(boot_json)
    desk_theme = frappe.db.get_value("User", frappe.session.user, "desk_theme")
    theme = 'light'
    menu_type = 'default'

    if (theme_settings_list.get('apply_dark_mode') and theme_settings_list.get('apply_dark_mode') == '1'):
        theme = 'dark'
    else:
        theme = 'light'

    if (desk_theme == 'Dark'):
        theme = 'dark'

    if ('menu_type' in theme_settings_list):
        menu_type = (theme_settings_list['menu_type']).replace(' ', '-').lower()

    # Theme Color By User
    user_settings = json.loads(get_user_settings('User'))
    theme_color = (theme_settings_list['theme_color'] or 'Blue') if 'theme_color' in theme_settings_list else 'Blue';
    if ('theme_color' in user_settings):
        theme_color = user_settings['theme_color']

    include_icons = hooks.get("app_include_icons", [])
    frappe.local.preload_assets["icons"].extend(include_icons)

    context.update(
        {
            "no_cache": 1,
            "app_version": get_first_item(hooks.version),
            "build_version": frappe.utils.get_build_version(),
            "build_version_dev": secrets.randbits(50),
            "include_js": hooks["app_include_js"],
            "include_css": hooks["app_include_css"],
            "include_icons": include_icons,
            "layout_direction": "rtl" if is_rtl() else "ltr",
            "lang": frappe.local.lang,
            "sounds": hooks["sounds"],
            "boot": boot if context.get("for_mobile") else boot_json,
            "desk_theme": boot.get("desk_theme") or "Light",
            "csrf_token": csrf_token,
            "google_analytics_id": frappe.conf.get("google_analytics_id"),
            "google_analytics_anonymize_ip": frappe.conf.get("google_analytics_anonymize_ip"),
            "mixpanel_id": frappe.conf.get("mixpanel_id"),
            "theme_settings": theme_settings_list,
            "default_workspace": frappe.db.get_value("User", frappe.session.user, 'default_workspace'),
            "theme_color": (theme_color),
            "theme_color_name": (theme_color).replace(' ', '-').lower(),
            "theme_menu_type": menu_type,
            "theme_color_on_navbar": 'layout-navbar-color-style' if ('apply_on_navbar' in theme_settings_list and theme_settings_list['apply_on_navbar'] == '1') else '',
            "apply_on_menu": 'layout-menu-color-style' if ('apply_on_menu' in theme_settings_list and theme_settings_list['apply_on_menu'] == '1') else '',
            "apply_on_dashboard": 'layout-dashboard-color-style' if ('apply_on_dashboard' in theme_settings_list and theme_settings_list['apply_on_dashboard'] == '1') else '',
            "apply_on_workspace": 'layout-workspace-color-style' if ('apply_on_workspace' in theme_settings_list and theme_settings_list['apply_on_workspace'] == '1') else '',
            "dark_theme": theme,
            "generate_color_scale": generate_color_scale,
        }
    )

    return context


def hex_to_rgb(hex_color):
    hex_color = hex_color.lstrip("#")
    return tuple(int(hex_color[i:i + 2], 16) / 255.0 for i in (0, 2, 4))


def rgb_to_hex(rgb):
    return "#{:02x}{:02x}{:02x}".format(
        int(rgb[0] * 255),
        int(rgb[1] * 255),
        int(rgb[2] * 255)
    )


def generate_color_scale(hex_color):
    base_rgb = hex_to_rgb(hex_color)
    h, l, s = colorsys.rgb_to_hls(*base_rgb)

    lightness_values = {
        50: 1,
        100: 0.95,
        200: 0.85,
        300: 0.75,
        400: 0.65,
        500: l,  # base
        600: 0.45,
        700: 0.35,
        800: 0.25,
        900: 0.07,
    }

    shades = {}
    for key, new_l in lightness_values.items():
        new_rgb = colorsys.hls_to_rgb(h, new_l, s)
        shades[key] = rgb_to_hex(new_rgb)

    return shades


def get_first_item(array):
    if isinstance(array, list) and len(array) > 0:
        return array[0]
    else:
        return ''


@frappe.whitelist()
def get_desk_assets(build_version):
    """Get desk assets to be loaded for mobile app"""
    data = get_context({"for_mobile": True})
    assets = [{"type": "js", "data": ""}, {"type": "css", "data": ""}]

    if build_version != data["build_version"]:
        # new build, send assets
        for path in data["include_js"]:
            # assets path shouldn't start with /
            # as it points to different location altogether
            if path.startswith("/assets/"):
                path = path.replace("/assets/", "assets/")
            try:
                with open(os.path.join(frappe.local.sites_path, path)) as f:
                    assets[0]["data"] = assets[0]["data"] + "\n" + frappe.safe_decode(f.read(), "utf-8")
            except OSError:
                pass

        for path in data["include_css"]:
            if path.startswith("/assets/"):
                path = path.replace("/assets/", "assets/")
            try:
                with open(os.path.join(frappe.local.sites_path, path)) as f:
                    assets[1]["data"] = assets[1]["data"] + "\n" + frappe.safe_decode(f.read(), "utf-8")
            except OSError:
                pass

    return {"build_version": data["build_version"], "boot": data["boot"], "assets": assets}
