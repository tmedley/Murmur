# murmur.py
#
# Murmur
# a universal AI chat app for macOS
# Tim Medley tim@medley.us
#



import sys
import json
import os
import objc
from datetime import datetime
from Cocoa import (
    NSApplication, NSApp, NSObject,
    NSWindow, NSScrollView, NSTextView, NSTextField,
    NSButton, NSPopUpButton, NSSplitView, NSView, NSTableView, NSTableColumn,
    NSMakeRect, NSFont, NSApplicationActivationPolicyRegular, NSTableViewSelectionHighlightStyleRegular,
    NSWindowStyleMask, NSBackingStoreBuffered
)

from backend import ChatService

print("Murmur: starting")

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
        print("Murmur: applicationDidFinishLaunching_ FORCE window test")

        window_rect = NSMakeRect(100.0, 100.0, 800.0, 600.0)
        style_mask = (
            NSWindowStyleMask.titled
            | NSWindowStyleMask.closable
            | NSWindowStyleMask.resizable
        )

        self.window = NSWindow.alloc().initWithContentRect_styleMask_backing_defer_(
            window_rect,
            style_mask,
            NSBackingStoreBuffered,
            False
        )
        self.window.retain()
        
        self.window.setTitle_("Murmur - Test Window")
        self.window.makeKeyAndOrderFront_(None)
        self.window.center()
        self.window.orderFrontRegardless()

        NSApp.activateIgnoringOtherApps_(True)

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

    def tableView_toolTipForCell_rect_tableColumn_row_mouseLocation_(
        self, tableView, cell, rect, tableColumn, row, mouseLocation):
        if 0 <= row < len(self.history):
            ts = self.history[row].get("timestamp")
            if ts:
                return ts.replace("T", " ")
        return None

    def tableViewSelectionDidChange_(self, notification):
        row = self.history_table.selectedRow()
        if 0 <= row < len(self.history):
            item = self.history[row]
            display = f"You: {item['prompt']}\nMurmur: {item['response']}\n"
            self.output_text.setString_(display)

if __name__ == "__main__":
    # Ensure app context is initialized FIRST
    app = NSApplication.sharedApplication()
    app.setActivationPolicy_(NSApplicationActivationPolicyRegular)

    # Now initialize delegate + run
    delegate = MurmurAppDelegate.alloc().init()
    app.setDelegate_(delegate)
    app.activateIgnoringOtherApps_(True)  # Force macOS to bring it forward
    app.run()
