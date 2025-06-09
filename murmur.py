# murmur.py
#
# Murmur
# a universal AI chat app for macOS
# Tim Medley tim@medley.us
#
# Main application


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
    NSBackingStoreBuffered, NSEventModifierFlagCommand,NSBezelStyleRounded
)

from backend import ChatService, get_openai_models, get_claude_models, get_gemini_models
from preferences import SettingsWindow, load_preferences, show_about_panel, get_api_keys

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
        

        prefs = load_preferences()
        print(prefs)
        provider = prefs.get("provider", "openai")
        api_key = prefs.get(f"api_key_{provider}", "")
        self.chat_service = ChatService(provider, api_key)  
        
        #self.model_cache = {}

        prefs = load_preferences()
        provider = prefs.get("provider", "openai")
        api_key = prefs.get(f"api_key_{provider}", "")
        print(f"Initial provider: {provider}, API key: {api_key[:8]}...")
        self.chat_service = ChatService(provider, api_key)  

        self.history = []

        
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
        self.window.setTitle_("Murmur")
        self.window.setDelegate_(self)

        self.create_main_menu()

        self.split_view = NSSplitView.alloc().initWithFrame_(NSMakeRect(0, 0, 800, 600))
        self.split_view.setDividerStyle_(3)
        self.split_view.setVertical_(True)

        self.left_view = NSView.alloc().initWithFrame_(NSMakeRect(0, 0, 310, 600))
        self.left_view.setTranslatesAutoresizingMaskIntoConstraints_(True)

        scroll_view = NSScrollView.alloc().initWithFrame_(self.left_view.bounds())
        scroll_view.setAutoresizingMask_(1 << 1 | 1 << 3)

        print("Creating history table and panel")
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

        print("Creating Right panel")
        self.right_view = NSView.alloc().initWithFrame_(NSMakeRect(200, 0, 600, 600))
        self.right_view.setTranslatesAutoresizingMaskIntoConstraints_(True)

        print("Creating AI Provider Label and Dropdown")
        # --- AI Provider Label and Dropdown ---
        self.provider_label = NSTextField.alloc().initWithFrame_(NSMakeRect(20, 544, 80, 24)) #was 10 536 80 24
        self.provider_label.setStringValue_("AI Provider:")
        self.provider_label.setBezeled_(False)
        self.provider_label.setDrawsBackground_(False)
        self.provider_label.setEditable_(False)
        self.provider_label.setSelectable_(False)
        self.provider_label.setFont_(NSFont.systemFontOfSize_(13))
        self.right_view.addSubview_(self.provider_label)

        self.provider_popup = NSPopUpButton.alloc().initWithFrame_(NSMakeRect(92, 546, 150, 26)) #was 100 536 150 28
        self.provider_popup.addItemsWithTitles_(["OpenAI", "Claude", "Gemini"])
        self.provider_popup.setTarget_(self)
        self.provider_popup.setAction_("providerChanged:")
        self.right_view.addSubview_(self.provider_popup)

        print("Creating AI Model Label and Dropdown")
        # --- AI Model Select Label and Dropdown ---
        self.model_label = NSTextField.alloc().initWithFrame_(NSMakeRect(270, 544, 50, 24)) #was 350 210 100 20
        self.model_label.setStringValue_("Model:")
        self.model_label.setBezeled_(False)
        self.model_label.setDrawsBackground_(False)
        self.model_label.setEditable_(False)
        self.model_label.setSelectable_(False)
        self.model_label.setFont_(NSFont.systemFontOfSize_(13))
        self.right_view.addSubview_(self.model_label)

        self.model_popup = NSPopUpButton.alloc().initWithFrame_(NSMakeRect(312, 546, 180, 26)) #was 420 205 250 26
        #self.model_popup.addItemsWithTitles_(["gpt-3.5-turbo"])
        self.right_view.addSubview_(self.model_popup)
        
        print("Creating Output Window")
        # --- Prompt Response Output Window ---
        self.output_text = NSTextView.alloc().initWithFrame_(NSMakeRect(10, 200, 580, 320))
        self.output_text.setEditable_(False)
        self.output_text.setFont_(NSFont.systemFontOfSize_(13))

        output_scroll = NSScrollView.alloc().initWithFrame_(NSMakeRect(10, 220, 580, 300))
        output_scroll.setDocumentView_(self.output_text)
        output_scroll.setHasVerticalScroller_(True)
        self.right_view.addSubview_(output_scroll)

        self.input_field = NSTextField.alloc().initWithFrame_(NSMakeRect(10, 140, 565, 80))
        self.right_view.addSubview_(self.input_field)

        print("Creating Send Button")
        # --- Send Button ---
        self.send_button = NSButton.alloc().initWithFrame_(NSMakeRect(480, 100, 110, 30))
        self.send_button.setTitle_("Send")
        self.send_button.setBezelStyle_(NSBezelStyleRounded)
        self.send_button.setTarget_(self)
        self.send_button.setAction_("sendClicked:")
        #self.send_button.setAction_("testButtonClicked:") # test
        self.right_view.addSubview_(self.send_button)
        self.split_view.addSubview_(self.right_view)

        print("Murmur: adding content view...")
        self.window.setContentView_(self.split_view)
        self.window.makeKeyAndOrderFront_(None)
        NSApp.activateIgnoringOtherApps_(True)

        self.providerChanged_(self.provider_popup)  # trigger model update manually

        try:
            #self.provider_popup.selectItemWithTitle_(provider.capitalize())
            self.load_history()
            print("Murmur: history loaded")
        except Exception as e:
            print(f"Murmur: failed to load history - {e}")

        self.populate_model_dropdown(provider, api_key)
        
    def populate_model_dropdown(self, provider, api_key):
        print(f"Populating model dropdown for provider: {provider}")
        models = []
        if provider == "openai":
            models = get_openai_models(api_key)
        elif provider == "claude":
            models = get_claude_models(api_key)
        elif provider == "gemini":
            models = get_gemini_models(api_key)

        print("Updating model dropdown with:", models)
        self.model_popup.removeAllItems()
        self.model_popup.addItemsWithTitles_(models or ["gpt-3.5-turbo"])

    def providerChanged_(self, sender):
        selected = sender.titleOfSelectedItem().lower()
        self.chat_service.provider = selected
        api_key = self.chat_service.api_key
        #self.populate_model_dropdown(selected, api_key)

        print(f"Populating model dropdown for provider: {selected}")

        if selected == "openai" and api_key:
            print(f"Fetching models using API key: {api_key[:10]}...")
            models = get_openai_models(api_key)
            print(f"Found models: {models}")
            chat_models = [m for m in models if "gpt" in m and not any(x in m for x in ["tts", "image", "embedding", "dall-e", "whisper"])]
            self.model_popup.removeAllItems()
            self.model_popup.addItemsWithTitles_(chat_models or ["gpt-3.5-turbo"])
            print(f"Updating model dropdown with: {chat_models}")

        elif selected == "claude" and api_key:
            models = get_claude_models(api_key)
            chat_models = [m for m in models if m.startswith("claude-")]
            self.model_popup.removeAllItems()
            self.model_popup.addItemsWithTitles_(chat_models or ["claude-sonnet-4"])

        elif selected == "gemini" and api_key:
            models = get_gemini_models(api_key)
            chat_models = [m for m in models if m.startswith("gemini-")]
            self.model_popup.removeAllItems()
            self.model_popup.addItemsWithTitles_(chat_models or ["gemini-2.5-flash"])   

    def update_model_dropdown(self, models):
        self.model_dropdown.removeAllItems()
        for model in models:
            self.model_dropdown.addItemWithTitle_(model)

        if models:
            self.model_dropdown.selectItemAtIndex_(0)

    def testButtonClicked_(self, sender):
        print("Test button click!")

    @objc.IBAction
    def sendClicked_(self, sender):
        print("pressed send button")
        prompt = self.input_field.stringValue()
        if not prompt:
            return
        self.input_field.setStringValue_("")

        current_provider = str(self.provider_popup.titleOfSelectedItem())
        current_model = str(self.model_popup.titleOfSelectedItem())
    
        print(f"Provider: {current_provider}, Model: {current_model}, Prompt: {prompt}")

        active_chat_client = self.chat_service.get_client(current_provider)
        response_text = active_chat_client.send_message(prompt=prompt, model=current_model)

        # --- Display the new prompy and response in the output ---
        existing_content = self.output_text.string()
        new_display_content = f"{existing_content}\nYou: {prompt}\nMurmur: {response_text}\n"
        self.output_text.setString_(new_display_content)

        # --- Save the new chat interaction to history ---
        self.history.append({
            "prompt": prompt,
            "response": response_text,
            "timestamp": datetime.now().isoformat()
        })
        self.save_history() # Make sure this method is correctly implemented (it appears to be)
        self.history_data_source = HistoryDataSource.alloc().initWithHistory_(self.history)
        self.history_table.setDataSource_(self.history_data_source)
        self.history_table.reloadData()
        self.history_table.scrollRowToVisible_(len(self.history) - 1) # Scroll to the latest message

    
    def create_main_menu(self):
        main_menu = NSMenu.alloc().init()
        app_menu_item = NSMenuItem.alloc().init()
        main_menu.addItem_(app_menu_item)
        NSApp.setMainMenu_(main_menu)

        # --- Application Menu ---
        app_menu = NSMenu.alloc().init()

        # -- About Menu ---
        about_item = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
            "About Murmur", "openAbout:", ""
        )
        about_item.setTarget_(self)
        app_menu.addItem_(about_item)

         # --- Separator ---
        app_menu.addItem_(NSMenuItem.separatorItem())

        # --- Settings Menu ---
        settings_item = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
            "Settings...", "openSettings:", ",",
        )
        settings_item.setKeyEquivalentModifierMask_(NSEventModifierFlagCommand)
        settings_item.setTarget_(self)
        app_menu.addItem_(settings_item)

        app_menu_item.setSubmenu_(app_menu)

        # --- Separator ---
        app_menu.addItem_(NSMenuItem.separatorItem())

        # --- Hide Murmur ---
        hide_item = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
            f"Hide Murmur", "hide:", "h"
        )
        hide_item.setKeyEquivalentModifierMask_(NSEventModifierFlagCommand)
        app_menu.addItem_(hide_item)

        # --- Quit Murmur ---
        quit_item = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
            f"Quit Murmur", "terminate:", "q"
        )
        quit_item.setKeyEquivalentModifierMask_(NSEventModifierFlagCommand)
        app_menu.addItem_(quit_item)


        # --- Edit Menu ---
        edit_menu_item = NSMenuItem.alloc().init()
        main_menu.addItem_(edit_menu_item)

        edit_menu = NSMenu.alloc().initWithTitle_("Edit")

        shortcut_items = [
            ("Undo", "undo:", "z"),
            ("Redo", "redo:", "Z"),  # Shift + Cmd + Z
            (None, None, None),
            ("Cut", "cut:", "x"),
            ("Copy", "copy:", "c"),
            ("Paste", "paste:", "v"),
            (None, None, None),
            ("Select All", "selectAll:", "a"),
        ]

        for title, selector, key in shortcut_items:
            if title is None:
                edit_menu.addItem_(NSMenuItem.separatorItem())
            else:
                item = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
                    title, selector, key
                )
                edit_menu.addItem_(item)

        edit_menu_item.setSubmenu_(edit_menu)

        # --- Icon Bundle for app ---
        # not sure this is working until I package the app
        NSApp.setApplicationIconImage_(NSImage.imageNamed_("Resources/logo.png"))
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
    icon = NSImage.alloc().initWithContentsOfFile_("Resources/Murmur.icns")
    if icon:
        NSApp.setApplicationIconImage_(icon)

    delegate = MurmurAppDelegate.alloc().init()
    app.setDelegate_(delegate)
    app.run()
