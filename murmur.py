import sys
import json
import os
import objc
from datetime import datetime
from Cocoa import (
    NSApplication, NSApp, NSObject,
    NSWindow, NSScrollView, NSTextView, NSTextField,
    NSButton, NSPopUpButton, NSSplitView, NSView, NSTableView, NSTableColumn,
    NSMenu, NSMenuItem, NSImage, NSImageView, NSBundle, NSSecureTextField,
    NSMakeRect, NSFont, NSApplicationActivationPolicyRegular, NSTableViewSelectionHighlightStyleRegular,
    NSWindowStyleMaskTitled, NSWindowStyleMaskClosable, NSWindowStyleMaskResizable,
    NSBackingStoreBuffered
)

from backend import ChatService
from preferences import SettingsWindow, load_preferences, show_about_panel

print("Murmur: starting")

NSLayoutConstraintPriorityRequired = 1000.0
HISTORY_PATH = os.path.expanduser("~/Library/Application Support/Murmur/chat_history.json")


class HistoryDataSource(NSObject):
    def initWithHistory_(self, history):
        self = objc.super(HistoryDataSource, self).init()
        self.history = history
        return self

    def numberOfRowsInTableView_(self, table):
        return len(self.history)

    def tableView_objectValueForTableColumn_row_(self, table, column, row):
        column_id = column.identifier()
        if column_id == "prompt":
            return self.history[row]["prompt"]
        elif column_id == "timestamp":
            iso = self.history[row].get("timestamp", "")
            return iso[11:16] if iso else ""

class MurmurAppDelegate(NSObject):
    def applicationDidFinishLaunching_(self, notification):
        print("Murmur: applicationDidFinishLaunching_ started")
        print("Murmur: creating window...")
        self.chat_service = ChatService("openai")
        self.history = []

        prefs = load_preferences()
        theme = prefs.get("theme", "system")
        if theme == "dark":
            NSApp.setAppearance_(objc.lookUpClass("NSAppearance").appearanceNamed_("NSAppearanceNameDarkAqua"))
        elif theme == "light":
            NSApp.setAppearance_(objc.lookUpClass("NSAppearance").appearanceNamed_("NSAppearanceNameAqua"))

        self.settings_window = SettingsWindow.alloc().init()

        rect = NSMakeRect(100.0, 100.0, 900.0, 600.0)
        style = NSWindowStyleMaskTitled | NSWindowStyleMaskClosable | NSWindowStyleMaskResizable
        self.window = NSWindow.alloc().initWithContentRect_styleMask_backing_defer_(
            rect,
            style,
            NSBackingStoreBuffered,
            False
        )
        self.window.setTitle_("Murmur - Universal AI Chat Client")
        self.window.setDelegate_(self)

        self.create_main_menu()

        self.split_view = NSSplitView.alloc().initWithFrame_(NSMakeRect(0, 0, 800, 600))
        self.split_view.setDividerStyle_(3)
        self.split_view.setVertical_(True)

        self.left_view = NSView.alloc().initWithFrame_(NSMakeRect(0, 0, 310, 600))
        self.left_view.setTranslatesAutoresizingMaskIntoConstraints_(True)

        scroll_view = NSScrollView.alloc().initWithFrame_(self.left_view.bounds())
        scroll_view.setAutoresizingMask_(1 << 1 | 1 << 3)

        self.history_table = NSTableView.alloc().initWithFrame_(self.left_view.bounds())

        column_prompt = NSTableColumn.alloc().initWithIdentifier_("prompt")
        column_prompt.setWidth_(200)
        column_prompt.headerCell().setStringValue_("Prompt")
        column_prompt.setResizingMask_(1)

        column_time = NSTableColumn.alloc().initWithIdentifier_("timestamp")
        column_time.setWidth_(80)
        column_time.headerCell().setStringValue_("Time")
        column_time.setResizingMask_(0)

        self.history_table.addTableColumn_(column_prompt)
        self.history_table.addTableColumn_(column_time)
        self.history_table.setDelegate_(self)
        self.history_data_source = HistoryDataSource.alloc().initWithHistory_(self.history)
        self.history_table.setDataSource_(self.history_data_source)
        self.history_table.setSelectionHighlightStyle_(NSTableViewSelectionHighlightStyleRegular)
        self.history_table.headerView().setAutoresizingMask_(0)

        scroll_view.setDocumentView_(self.history_table)
        scroll_view.setHasVerticalScroller_(False)
        self.left_view.addSubview_(scroll_view)
        self.split_view.addSubview_(self.left_view)

        self.right_view = NSView.alloc().initWithFrame_(NSMakeRect(200, 0, 600, 600))
        self.right_view.setTranslatesAutoresizingMaskIntoConstraints_(True)


        # Label to the left of provider dropdown
        self.provider_label = NSTextField.alloc().initWithFrame_(NSMakeRect(10, 536, 80, 24))
        self.provider_label.setStringValue_("AI Provider:")
        self.provider_label.setBezeled_(False)
        self.provider_label.setDrawsBackground_(False)
        self.provider_label.setEditable_(False)
        self.provider_label.setSelectable_(False)
        self.provider_label.setFont_(NSFont.systemFontOfSize_(13))
        self.right_view.addSubview_(self.provider_label)

        # Dropdown next to label
        self.provider_popup = NSPopUpButton.alloc().initWithFrame_(NSMakeRect(100, 536, 150, 28))
        self.provider_popup.addItemsWithTitles_(["OpenAI", "Claude", "Gemini"])
        self.provider_popup.setTarget_(self)
        self.provider_popup.setAction_("providerChanged:")
        self.right_view.addSubview_(self.provider_popup)

        self.output_text = NSTextView.alloc().initWithFrame_(NSMakeRect(10, 200, 580, 320))
        self.output_text.setEditable_(False)
        self.output_text.setFont_(NSFont.systemFontOfSize_(13))

        output_scroll = NSScrollView.alloc().initWithFrame_(NSMakeRect(10, 220, 580, 300))
        output_scroll.setDocumentView_(self.output_text)
        output_scroll.setHasVerticalScroller_(True)
        self.right_view.addSubview_(output_scroll)

        self.input_field = NSTextField.alloc().initWithFrame_(NSMakeRect(10, 140, 565, 80))
        self.right_view.addSubview_(self.input_field)

        self.send_button = NSButton.alloc().initWithFrame_(NSMakeRect(480, 100, 110, 30))
        self.send_button.setTitle_("Send")
        self.send_button.setTarget_(self)
        self.send_button.setAction_("sendClicked:")
        self.right_view.addSubview_(self.send_button)

        self.split_view.addSubview_(self.right_view)

        print("Murmur: adding content view...")
        self.window.setContentView_(self.split_view)
        self.window.makeKeyAndOrderFront_(None)
        NSApp.activateIgnoringOtherApps_(True)

        try:
            self.load_history()
            print("Murmur: history loaded")
        except Exception as e:
            print(f"Murmur: failed to load history - {e}")

    def create_main_menu(self):
        main_menu = NSMenu.alloc().init()
        app_menu_item = NSMenuItem.alloc().init()
        main_menu.addItem_(app_menu_item)
        NSApp.setMainMenu_(main_menu)

        app_menu = NSMenu.alloc().init()

        about_item = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
            "About Murmur", "openAbout:", ""
        )
        about_item.setTarget_(self)
        app_menu.addItem_(about_item)

        settings_item = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
            "Settings...", "openSettings:", "",
        )
        settings_item.setTarget_(self)
        app_menu.addItem_(settings_item)

        app_menu_item.setSubmenu_(app_menu)

        NSApp.setApplicationIconImage_(NSImage.imageNamed_("logo"))
        info_dict = NSBundle.mainBundle().infoDictionary()
        info_dict["CFBundleName"] = "Murmur"
        info_dict["NSHumanReadableCopyright"] = "A Universal AI Chat Client\n\nCopyright © 2025 Tim Medley\ntim@medley.us"
        info_dict["CFBundleShortVersionString"] = "1.0"

    def openAbout_(self, sender):
        show_about_panel()

    def openSettings_(self, sender):
        main_frame = self.window.frame()
        settings_frame = self.settings_window.frame()
        x = main_frame.origin.x + (main_frame.size.width - settings_frame.size.width) / 2
        y = main_frame.origin.y + (main_frame.size.height - settings_frame.size.height) / 2
        self.settings_window.setFrameOrigin_((x, y))
        self.settings_window.makeKeyAndOrderFront_(None)

    def providerChanged_(self, sender):
        selected = sender.titleOfSelectedItem()
        self.chat_service = ChatService(selected)

    def sendClicked_(self, sender):
        prompt = self.input_field.stringValue()
        if not prompt:
            return
        response = self.chat_service.chat(prompt)
        existing = self.output_text.string()
        new_content = f"{existing}\nYou: {prompt}\nMurmur: {response}\n"
        self.output_text.setString_(new_content)
        self.input_field.setStringValue_("")

        self.history.append({"prompt": prompt, "response": response, "timestamp": datetime.now().isoformat()})
        self.history_data_source = HistoryDataSource.alloc().initWithHistory_(self.history)
        self.history_table.setDataSource_(self.history_data_source)
        self.history_table.reloadData()
        self.save_history()

    def save_history(self):
        os.makedirs(os.path.dirname(HISTORY_PATH), exist_ok=True)
        with open(HISTORY_PATH, "w", encoding="utf-8") as f:
            json.dump(self.history, f)

    def load_history(self):
        if os.path.exists(HISTORY_PATH):
            with open(HISTORY_PATH, "r", encoding="utf-8") as f:
                self.history = json.load(f)
        else:
            self.history = []

        self.history_data_source = HistoryDataSource.alloc().initWithHistory_(self.history)
        self.history_table.setDataSource_(self.history_data_source)
        self.history_table.reloadData()

    def tableViewSelectionDidChange_(self, notification):
        row = self.history_table.selectedRow()
        if 0 <= row < len(self.history):
            item = self.history[row]
            display = f"You: {item['prompt']}\nMurmur: {item['response']}\n"
            self.output_text.setString_(display)

    def windowWillClose_(self, notification):
        if notification.object() == self.window:
            NSApp.terminate_(self)

if __name__ == "__main__":
    app = NSApplication.sharedApplication()
    app.setActivationPolicy_(NSApplicationActivationPolicyRegular)

    # Add your icon-setting code **after** NSApplication is initialized
    icon = NSImage.alloc().initWithContentsOfFile_("/full/path/to/MyIcon.icns")
    if icon:
        NSApp.setApplicationIconImage_(icon)

    delegate = MurmurAppDelegate.alloc().init()
    app.setDelegate_(delegate)
    app.run()
