// Copyright (c) 2021, Abdo Hamoud and contributors
// For license information, please see license.txt

const sleep = (s) => new Promise((p) => setTimeout(p, (s * 1000) | 0));

async function runThemeSettings() {
    await sleep(1)
    $(document).trigger('run-theme-settings');
}

frappe.ui.form.on('Theme Settings', {
    setup() {
        let assets = [
            // '/assets/datavalue_theme_15/plugins/bootstrap-select/bootstrap-select.min.js',
            // '/assets/datavalue_theme_15/js/datavalue_theme.settings.min.js'
            // 'datavalue_theme.settings.bundle.js'
        ];
        frappe.require(assets, () => {
            setTimeout(runThemeSettings, 1000);
        });
    },
    refresh: function (frm) {
        $('[data-fieldname="font_family"] select').chosen({width: '50%'});
        setTimeout(() => {
            runThemeSettings().then(r => {
                // console.log('===custom_menu_json===', JSON.parse(frm.doc.custom_menu_json))
            });
        }, 1000);
    },
    before_save(frm) {
        let datavalue_settings = frappe.DataValueThemeSettings.datavalue_settings;
        console.log('datavalue_settings', datavalue_settings)
        frm.set_value("custom_menu_json", JSON.stringify(datavalue_settings));
    },
    after_save: function (frm) {
        frappe.dom.freeze(__('Save Settings ...'));
        frappe.ui.toolbar.clear_cache();
    }
});
