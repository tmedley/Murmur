import sys
from AppKit import (
    NSApplication, NSWindow, NSMakeRect,
    NSWindowStyleMaskTitled, NSWindowStyleMaskClosable, NSWindowStyleMaskResizable,
    NSBackingStoreBuffered, NSApplicationActivationPolicyRegular
)

print("Starting test app")

app = NSApplication.sharedApplication()
app.setActivationPolicy_(NSApplicationActivationPolicyRegular)

window = NSWindow.alloc().initWithContentRect_styleMask_backing_defer_(
    NSMakeRect(200, 300, 600, 400),
    NSWindowStyleMaskTitled | NSWindowStyleMaskClosable | NSWindowStyleMaskResizable,
    NSBackingStoreBuffered,
    False
)
window.setTitle_("PyObjC Test Window")
window.makeKeyAndOrderFront_(None)

print("Running app loop")
app.activateIgnoringOtherApps_(True)
app.run()