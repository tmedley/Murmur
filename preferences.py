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
    NSWindowStyleMaskTitled, NSWindowStyleMaskClosable, NSBackingStoreBuffered,
    NSObject, NSImageView, NSView, NSFont, NSImage, NSApplication, NSBundle
)


PREFERENCES_PATH = os.path.expanduser("~/Library/Application Support/Murmur/preferences.json")

NSLayoutConstraintPriorityRequired = 1000.0

ABOUT_VERSION = "1.0"
ABOUT_DESCRIPTION = """A universal AI chat client supporting multiple providers.
Developed by Tim Medley (tim@medley.us)"""

LOGO_PATH = os.path.expanduser("Resources/logo.png")

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
            NSMakeRect(0, 0, 700, 300),  # Main window size
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
        self.dark_mode_label = NSTextField.alloc().initWithFrame_(NSMakeRect(20, 220, 100, 20))
        self.dark_mode_label.setStringValue_("Theme")
        self.dark_mode_label.setBezeled_(False)
        self.dark_mode_label.setDrawsBackground_(False)
        self.dark_mode_label.setEditable_(False)
        self.dark_mode_label.setSelectable_(False)
        self.contentView().addSubview_(self.dark_mode_label)

        self.theme_popup = NSPopUpButton.alloc().initWithFrame_(NSMakeRect(130, 215, 200, 26))
        self.theme_popup.addItemsWithTitles_(["System Default", "Light Mode", "Dark Mode"])
        theme_map = {"light": 1, "dark": 2}
        self.theme_popup.selectItemAtIndex_(theme_map.get(prefs.get("theme"), 0))
        self.contentView().addSubview_(self.theme_popup)

        # api key fields
        self.api_labels = {}
        self.api_fields = {}
        apis = ["OpenAI", "Claude", "Gemini"]
        for i, name in enumerate(apis):
            y = 160 - (i * 50)
            label = NSTextField.alloc().initWithFrame_(NSMakeRect(20, y + 5, 100, 20))
            label.setStringValue_(f"{name} API Key")
            label.setBezeled_(False)
            label.setDrawsBackground_(False)
            label.setEditable_(False)
            label.setSelectable_(False)
            self.contentView().addSubview_(label)

            field = NSSecureTextField.alloc().initWithFrame_(NSMakeRect(130, y, 540, 36))
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

class AboutWindow(NSWindow):
    def init(self):
        self = objc.super(AboutWindow, self).initWithContentRect_styleMask_backing_defer_(
            NSMakeRect(0, 0, 400, 220),
            NSWindowStyleMaskTitled | NSWindowStyleMaskClosable,
            NSBackingStoreBuffered,
            False
        )
        if self is None:
            return None

        self.setTitle_("About Murmur")
        self.setReleasedWhenClosed_(False)
        self.setLevel_(3)  # Above normal windows

        content = NSView.alloc().initWithFrame_(NSMakeRect(0, 0, 400, 200))

        # Logo (update path to match your actual logo image name and bundle structure)
        image = NSImage.alloc().initWithContentsOfFile_(
            os.path.join(os.path.dirname(__file__), "Resources/logo.png")
        )
        image_view = NSImageView.alloc().initWithFrame_(NSMakeRect(10, 90, 128, 128))
        image_view.setImage_(image)
        content.addSubview_(image_view)

        # App Name
        name_field = NSTextField.alloc().initWithFrame_(NSMakeRect(150, 180, 280, 24))
        name_field.setStringValue_("Murmur - Universal AI Chat Client")
        name_field.setFont_(NSFont.boldSystemFontOfSize_(14))
        name_field.setBezeled_(False)
        name_field.setDrawsBackground_(False)
        name_field.setEditable_(False)
        name_field.setSelectable_(False)
        content.addSubview_(name_field)

        # Version
        version_field = NSTextField.alloc().initWithFrame_(NSMakeRect(150, 150, 280, 20))
        version_field.setStringValue_("Version 1.0")
        version_field.setBezeled_(False)
        version_field.setDrawsBackground_(False)
        version_field.setEditable_(False)
        version_field.setSelectable_(False)
        content.addSubview_(version_field)

        # Copyright
        copyright_field = NSTextField.alloc().initWithFrame_(NSMakeRect(150, 110, 280, 40))
        copyright_field.setStringValue_("© 2025 Tim Medley\nAll rights reserved.\n\ntim@medley.us")
        copyright_field.setBezeled_(False)
        copyright_field.setDrawsBackground_(False)
        copyright_field.setEditable_(False)
        copyright_field.setSelectable_(False)
        content.addSubview_(copyright_field)

        self.setContentView_(content)
        self.center()
        return self
    

def closeAboutWindow_(self, sender):
    self.close()

about_window_instance = None  # Global reference to keep it alive

def show_about_panel():
    global about_window_instance

    if about_window_instance is None:
        about_window_instance = AboutWindow.alloc().init()
        about_window_instance.retain()  # Prevent GC
        about_window_instance.setReleasedWhenClosed_(False)

    about_window_instance.makeKeyAndOrderFront_(None)



def get_api_keys():
    prefs = load_preferences()
    return {
        "openai": prefs.get("openai_api_key", ""),
        "claude": prefs.get("claude_api_key", ""),
        "gemini": prefs.get("gemini_api_key", "")
    }