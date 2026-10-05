# To-do list application. Doesn't depend on any third party GUI framework.
# The user interface is written in HTML/CSS/Javascript and the application
# logic and storage are in Python. It shows how to:
# - pass Javascript bindings to CreateBrowserSync, so that they are
#   available to page scripts from the start (window.onload)
# - call Python methods from Javascript and return results to
#   Javascript using callbacks
# - call Javascript functions from Python using ExecuteFunction
#
# Items are saved in a JSON file, by default ~/.cefpython3_todo.json.
# Pass a different path as an argument: python todo_app.py items.json
#
# Tested with CEF Python v154+ and Python 3.12+.

from cefpython3 import cefpython as cef
import json
import os
import platform
import sys

HTML_CODE = """
<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>To-do list</title>
<style>
    body {
        font-family: system-ui, sans-serif;
        font-size: 15px;
        margin: 0;
        padding: 24px 32px;
        background: #f6f7f9;
        color: #1f2328;
    }
    h1 { font-size: 22px; margin: 0 0 16px 0; }
    form { display: flex; gap: 8px; margin-bottom: 16px; }
    input[type=text] {
        flex: 1;
        padding: 8px 10px;
        font-size: 15px;
        border: 1px solid #c8ccd1;
        border-radius: 6px;
    }
    button {
        padding: 8px 14px;
        font-size: 15px;
        border: none;
        border-radius: 6px;
        background: #2f6feb;
        color: white;
        cursor: pointer;
    }
    ul { list-style: none; padding: 0; margin: 0; }
    li {
        display: flex;
        align-items: center;
        gap: 10px;
        padding: 8px 10px;
        margin-bottom: 6px;
        background: white;
        border: 1px solid #e1e4e8;
        border-radius: 6px;
    }
    li span { flex: 1; }
    li.done span { text-decoration: line-through; color: #8b949e; }
    li .remove {
        background: none;
        color: #8b949e;
        padding: 0 6px;
        font-size: 18px;
    }
    li .remove:hover { color: #cf222e; }
    #status { margin-top: 12px; font-size: 13px; color: #57606a; }
</style>
<script>
    // "todo" is an object bound from Python, see TodoApi class.
    // Bindings passed to CreateBrowserSync are already available
    // in window.onload.
    window.onload = function() {
        todo.get_items(render);
        document.getElementById("form").onsubmit = function(event) {
            event.preventDefault();
            var input = document.getElementById("text");
            if (input.value.trim()) {
                todo.add_item(input.value, render);
                input.value = "";
            }
        };
    };

    // Called by Python with the current list of items
    function render(items) {
        var list = document.getElementById("items");
        list.innerHTML = "";
        items.forEach(function(item) {
            var li = document.createElement("li");
            if (item.done) {
                li.className = "done";
            }
            var checkbox = document.createElement("input");
            checkbox.type = "checkbox";
            checkbox.checked = item.done;
            checkbox.onchange = function() {
                todo.toggle_item(item.id, render);
            };
            var text = document.createElement("span");
            text.textContent = item.text;
            var remove = document.createElement("button");
            remove.className = "remove";
            remove.title = "Remove";
            remove.textContent = "\\u00d7";
            remove.onclick = function() {
                todo.remove_item(item.id, render);
            };
            li.appendChild(checkbox);
            li.appendChild(text);
            li.appendChild(remove);
            list.appendChild(li);
        });
    }

    // Called by Python using Browser.ExecuteFunction
    function show_status(message) {
        document.getElementById("status").textContent = message;
    }
</script>
</head>
<body>
    <h1>To-do list</h1>
    <form id="form">
        <input id="text" type="text" placeholder="What needs to be done?"
               autofocus>
        <button type="submit">Add</button>
    </form>
    <ul id="items"></ul>
    <div id="status"></div>
</body>
</html>
"""


def main():
    check_versions()
    sys.excepthook = cef.ExceptHook  # To shutdown all CEF processes on error
    if len(sys.argv) > 1:
        path = sys.argv[1]
    else:
        path = os.path.join(os.path.expanduser("~"), ".cefpython3_todo.json")
    api = TodoApi(path)
    bindings = cef.JavascriptBindings()
    bindings.SetObject("todo", api)
    cef.Initialize()
    browser = cef.CreateBrowserSync(url=cef.GetDataUrl(HTML_CODE),
                                    window_title="To-do list",
                                    javascript_bindings=bindings)
    api.browser = browser
    cef.MessageLoop()
    del browser
    api.browser = None
    cef.Shutdown()


def check_versions():
    ver = cef.GetVersion()
    print("[todo_app.py] CEF Python {ver}".format(ver=ver["version"]))
    print("[todo_app.py] Chromium {ver}".format(ver=ver["chrome_version"]))
    print("[todo_app.py] Python {ver} {arch}".format(
           ver=platform.python_version(),
           arch=platform.architecture()[0]))


class TodoApi:
    """Methods of this object are called from Javascript. Calls are
    asynchronous, so results are returned by calling js_callback."""

    def __init__(self, path):
        self.path = path
        self.browser = None  # Set after the browser was created
        self.items = []
        self.next_id = 1
        self.load()

    def get_items(self, js_callback):
        js_callback.Call(self.items)
        self.show_status("{0} item(s) loaded from {1}"
                         .format(len(self.items), self.path))

    def add_item(self, text, js_callback):
        self.items.append({"id": self.next_id, "text": text.strip(),
                           "done": False})
        self.next_id += 1
        self.save()
        js_callback.Call(self.items)

    def toggle_item(self, item_id, js_callback):
        for item in self.items:
            if item["id"] == item_id:
                item["done"] = not item["done"]
        self.save()
        js_callback.Call(self.items)

    def remove_item(self, item_id, js_callback):
        self.items = [item for item in self.items if item["id"] != item_id]
        self.save()
        js_callback.Call(self.items)

    def load(self):
        if not os.path.exists(self.path):
            return
        with open(self.path, encoding="utf-8") as fp:
            self.items = json.load(fp)
        self.next_id = max([item["id"] for item in self.items] + [0]) + 1

    def save(self):
        with open(self.path, "w", encoding="utf-8") as fp:
            json.dump(self.items, fp, indent=2)
        done = len([item for item in self.items if item["done"]])
        self.show_status("Saved {0} item(s), {1} done"
                         .format(len(self.items), done))

    def show_status(self, message):
        # Call a Javascript function from Python
        if self.browser:
            self.browser.ExecuteFunction("show_status", message)


if __name__ == '__main__':
    main()
