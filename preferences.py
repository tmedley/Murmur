# preferences.py
#
# Murmur
# a universal AI chat app for macOS
# Tim Medley tim@medley.us
#



import os
import json
import objc
from Cocoa import (
    NSWindow, NSTextField, NSSecureTextField, NSPopUpButton, NSButton, NSMakeRect,
    NSWindowStyleMaskTitled, NSWindowStyleMaskClosable, NSBackingStoreBuffered
)

PREFERENCES_PATH = os.path.expanduser("~/Library/Application Support/Murmur/preferences.json")

NSLayoutConstraintPriorityRequired = 1000.0


def load_preferences():
    if os.path.exists(PREFERENCES_PATH):
        with open(PREFERENCES_PATH, "r") as f:
            return json.load(f)
    return {}


def save_preferences(prefs):
    os.makedirs(os.path.dirname(PREFERENCES_PATH), exist_ok=True)
    with open(PREFERENCES_PATH, "w") as f:
        json.dump(prefs, f)


class SettingsWindow(NSWindow):
    def init(self):
        self = objc.super(SettingsWindow, self).initWithContentRect_styleMask_backing_defer_(
            NSMakeRect(0, 0, 700, 250),  # You can tweak size
            NSWindowStyleMaskTitled | NSWindowStyleMaskClosable,
            NSBackingStoreBuffered,
            False
        )
        if self is None:
            return None

        self.setTitle_("Settings")
        self.setReleasedWhenClosed_(False)

        prefs = load_preferences()

        # theme drop down
        self.dark_mode_label = NSTextField.alloc().initWithFrame_(NSMakeRect(20, 190, 100, 20))
        self.dark_mode_label.setStringValue_("Theme")
        self.dark_mode_label.setBezeled_(False)
        self.dark_mode_label.setDrawsBackground_(False)
        self.dark_mode_label.setEditable_(False)
        self.dark_mode_label.setSelectable_(False)
        self.contentView().addSubview_(self.dark_mode_label)

        self.theme_popup = NSPopUpButton.alloc().initWithFrame_(NSMakeRect(130, 185, 200, 26))
        self.theme_popup.addItemsWithTitles_(["System Default", "Light Mode", "Dark Mode"])
        theme_map = {"light": 1, "dark": 2}
        self.theme_popup.selectItemAtIndex_(theme_map.get(prefs.get("theme"), 0))
        self.contentView().addSubview_(self.theme_popup)

        # api key fields
        self.api_labels = {}
        self.api_fields = {}
        apis = ["OpenAI", "Claude", "Gemini"]
        for i, name in enumerate(apis):
            y = 140 - (i * 40)
            label = NSTextField.alloc().initWithFrame_(NSMakeRect(20, y + 5, 100, 20))
            label.setStringValue_(f"{name} API Key")
            label.setBezeled_(False)
            label.setDrawsBackground_(False)
            label.setEditable_(False)
            label.setSelectable_(False)
            self.contentView().addSubview_(label)

            field = NSSecureTextField.alloc().initWithFrame_(NSMakeRect(130, y, 540, 24))
            field.setStringValue_(prefs.get(f"api_key_{name.lower()}", ""))
            self.contentView().addSubview_(field)

            self.api_labels[name] = label
            self.api_fields[name] = field

        self.save_button = NSButton.alloc().initWithFrame_(NSMakeRect(575, 10, 100, 30))
        self.save_button.setTitle_("Save")
        self.save_button.setTarget_(self)
        self.save_button.setAction_("savePreferences:")
        self.contentView().addSubview_(self.save_button)

        return self

    def savePreferences_(self, sender):
        selected_index = self.theme_popup.indexOfSelectedItem()
        theme = {0: "system", 1: "light", 2: "dark"}.get(selected_index, "system")

        prefs = load_preferences()
        prefs["theme"] = theme

        for name, field in self.api_fields.items():
            prefs[f"api_key_{name.lower()}"] = field.stringValue()

        save_preferences(prefs)

        # Dynamically apply theme
        from Cocoa import NSApp
        if theme == "dark":
            NSApp.setAppearance_(objc.lookUpClass("NSAppearance").appearanceNamed_("NSAppearanceNameDarkAqua"))
        elif theme == "light":
            NSApp.setAppearance_(objc.lookUpClass("NSAppearance").appearanceNamed_("NSAppearanceNameAqua"))
        else:
            NSApp.setAppearance_(None)

        self.orderOut_(None)
