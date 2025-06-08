import sys
import json
import os
import objc
from datetime import datetime
from Cocoa import (
    NSApplication, NSApp, NSObject,
    NSWindow, NSScrollView, NSTextView, NSTextField,
    NSButton, NSPopUpButton, NSSplitView, NSView, NSTableView, NSTableColumn,
    NSMenu, NSMenuItem,
    NSMakeRect, NSFont, NSApplicationActivationPolicyRegular, NSTableViewSelectionHighlightStyleRegular,
    NSWindowStyleMaskTitled, NSWindowStyleMaskClosable, NSWindowStyleMaskResizable,
    NSBackingStoreBuffered
)

from backend import ChatService

print("Murmur: starting")

NSLayoutConstraintPriorityRequired = 1000.0

PREFERENCES_PATH = os.path.expanduser("~/Library/Application Support/Murmur/preferences.json")

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
    def initWithAppDelegate_(self, app_delegate):
        self = objc.super(SettingsWindow, self).initWithContentRect_styleMask_backing_defer_(
            NSMakeRect(0, 0, 300, 100),
            NSWindowStyleMaskTitled | NSWindowStyleMaskClosable,
            NSBackingStoreBuffered,
            False
        )
        if self is None:
            return None

        self.setTitle_("Settings")
        self.setReleasedWhenClosed_(False)
        self.app_delegate = app_delegate

        self.mode_popup = NSPopUpButton.alloc().initWithFrame_(NSMakeRect(20, 40, 200, 26))
        self.mode_popup.addItemsWithTitles_(["System Default", "Light Mode", "Dark Mode"])
        self.mode_popup.setTarget_(self)
        self.mode_popup.setAction_("appearanceModeChanged:")
        self.contentView().addSubview_(self.mode_popup)

        prefs = load_preferences()
        selected = prefs.get("appearance", "System Default")
        self.mode_popup.selectItemWithTitle_(selected)

        return self

    def appearanceModeChanged_(self, sender):
        mode = sender.titleOfSelectedItem()
        prefs = load_preferences()
        prefs["appearance"] = mode
        save_preferences(prefs)
        self.app_delegate.apply_appearance(mode)

class LockedSplitView(NSSplitView):
    def isSubviewCollapsed_(self, subview):
        return False

    def canCollapseSubview_(self, subview):
        return False

    def isDividerHidden(self):
        return True

    def drawDividerInRect_(self, rect):
        pass

    def dividerThickness(self):
        return 0.5

    def constrainSplitPosition_ofSubviewAt_(self, proposedPosition, dividerIndex):
        return 300.0

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

HISTORY_PATH = os.path.expanduser("~/Library/Application Support/Murmur/chat_history.json")

class MurmurAppDelegate(NSObject):
    def applicationDidFinishLaunching_(self, notification):
        print("Murmur: applicationDidFinishLaunching_ started")
        print("Murmur: creating window...")
        self.chat_service = ChatService("openai")
        self.history = []

        prefs = load_preferences()
        self.apply_appearance(prefs.get("appearance", "System Default"))

        self.settings_window = SettingsWindow.alloc().initWithAppDelegate_(self)

        rect = NSMakeRect(100.0, 100.0, 900.0, 600.0)
        style = NSWindowStyleMaskTitled | NSWindowStyleMaskClosable | NSWindowStyleMaskResizable
        self.window = NSWindow.alloc().initWithContentRect_styleMask_backing_defer_(
            rect,
            style,
            NSBackingStoreBuffered,
            False
        )
        self.window.setTitle_("Murmur - Universal AI Chat Client")

        self.create_main_menu()

        self.split_view = LockedSplitView.alloc().initWithFrame_(NSMakeRect(0, 0, 800, 600))
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

        self.output_text = NSTextView.alloc().initWithFrame_(NSMakeRect(10, 260, 580, 320))
        self.output_text.setEditable_(False)
        self.output_text.setFont_(NSFont.systemFontOfSize_(13))

        output_scroll = NSScrollView.alloc().initWithFrame_(NSMakeRect(10, 260, 580, 320))
        output_scroll.setDocumentView_(self.output_text)
        output_scroll.setHasVerticalScroller_(True)
        self.right_view.addSubview_(output_scroll)

        self.input_field = NSTextField.alloc().initWithFrame_(NSMakeRect(10, 200, 580, 50))
        self.right_view.addSubview_(self.input_field)

        self.provider_popup = NSPopUpButton.alloc().initWithFrame_(NSMakeRect(10, 160, 200, 30))
        self.provider_popup.addItemsWithTitles_(["openai", "claude", "gemini"])
        self.provider_popup.setTarget_(self)
        self.provider_popup.setAction_("providerChanged:")
        self.right_view.addSubview_(self.provider_popup)

        self.send_button = NSButton.alloc().initWithFrame_(NSMakeRect(480, 160, 110, 30))
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
        settings_item = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
            "Settings...", "openSettings:", "",
        )
        settings_item.setTarget_(self)
        app_menu.addItem_(settings_item)
        app_menu_item.setSubmenu_(app_menu)

    def openSettings_(self, sender):
        main_frame = self.window.frame()
        x = main_frame.origin.x + (main_frame.size.width - 300) / 2
        y = main_frame.origin.y + (main_frame.size.height - 100) / 2
        self.settings_window.setFrameOrigin_((x, y))
        self.settings_window.makeKeyAndOrderFront_(None)

    def apply_appearance(self, mode):
        NSAppearance = objc.lookUpClass("NSAppearance")
        if mode == "Dark Mode":
            NSApp.setAppearance_(NSAppearance.appearanceNamed_("NSAppearanceNameDarkAqua"))
        elif mode == "Light Mode":
            NSApp.setAppearance_(NSAppearance.appearanceNamed_("NSAppearanceNameAqua"))
        else:
            NSApp.setAppearance_(None)

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

if __name__ == "__main__":
    app = NSApplication.sharedApplication()
    app.setActivationPolicy_(NSApplicationActivationPolicyRegular)
    delegate = MurmurAppDelegate.alloc().init()
    app.setDelegate_(delegate)
    app.run()
