import sublime, sublime_plugin
import re
import os

from Default import history_list

COMMON_PATHS = {
    "HashMap": "std::collections::HashMap",
    "HashSet": "std::collections::HashSet",
    "BTreeMap": "std::collections::BTreeMap",
    "BTreeSet": "std::collections::BTreeSet",
    "VecDeque": "std::collections::VecDeque",

    "Range": "std::ops::Range",

    "Path": "std::path::Path",
    "PathBuf": "std::path::PathBuf",
    "File": "std::fs::File",

    "Reader": "std::io::Reader",
    "BufReader": "std::io::BufReader",
    "Writer": "std::io::Writer",
    "BufWriter": "std::io::BufWriter",

    "mem": "std::mem",
    "io": "std::io",

    "Rc": "std::rc::Rc",
    "RefCell": "std::cell::RefCell",
    "Cell": "std::cell::Cell",

    "Arc": "std::sync::Arc",
    "Mutex": "std::sync::Mutex",
    "RwLock": "std::sync::RwLock",
    "Once": "std::sync::Once",

    "Sender": "std::sync::mpsc::Sender",
    "Receiver": "std::sync::mpsc::Receiver",
    "channel": "std::sync::mpsc::channel",

    "from_str": "std::str::FromStr",
    "borrow": "std::str::Borrow",
    "borrow_mut": "std::str::BorrowMut",
    "read_line": "std::io::BufRead",
    "read_to_end": "std::io::Read",
    "read_to_string": "std::io::Read",
}

def extract_path(loc, symbol):
    plain_path = os.path.splitext(loc[1])[0]
    split = plain_path.split("/")

    if split[-1] == "mod" or split[-1] == "lib":
        split.pop()

    return ["crate"] + split[1:] + [symbol]

def find_common_path(symbol):
    base_path = COMMON_PATHS.get(symbol)
    if base_path is None:
        return ["std", "x", symbol]

    return base_path.split("::")

def matchiness(a,b):
    m = 0
    for sa, sb in zip(a,b):
        if sa != sb:
            return m
        m += 1
    return m

class RustAutoImportCommand(sublime_plugin.TextCommand):
    def _existing_insert_point(self, import_path, edit):
        stem = "::".join(import_path[:-1])
        query = "^use {}::\\{{[^}}]+\\}};$".format(stem)

        use_statements = self.view.find_all(query)

        if len(use_statements) > 0:
            # inside the brackets
            return use_statements[0].b - 2

        query = "^use {}::\\w+;$".format(stem)
        use_statements = self.view.find_all(query)

        if len(use_statements) == 0:
            return None

        r = use_statements[0]
        self.view.insert(edit, r.b - 1, "}")
        self.view.insert(edit, r.a + len("use {}::".format(stem)), "{")
        return r.b


    def _new_insert_point(self, import_path):
        paths = []
        use_statements = self.view.find_all("^use ((?:\w|:)+)(?:;|::\\{|::\\*)", 0, "\\1", paths)

        if len(use_statements) == 0:
            return 0

        best_i = 0
        best_m = 0
        for i,path_s in enumerate(paths):
            path = path_s.split("::")
            m = matchiness(path, import_path)
            if m >= best_m:
                best_i, best_m = i,m

        use_start = use_statements[best_i].a
        r,c = self.view.rowcol(use_start)
        return self.view.text_point(r+1,c)

    def run(self, edit, **args):
        history_list.get_jump_history_for_view(self.view).push_selection(self.view)
        symbol = self.view.substr(self.view.word(self.view.sel()[0]))

        locs = self.view.window().lookup_symbol_in_index(symbol)
        locs = [l for l in locs if l[1].endswith(".rs")]

        if len(locs) > 0:
            import_path = extract_path(locs[0], symbol)
        else:
            import_path = find_common_path(symbol)

        if import_path is None:
            return

        existing_insert_pt = self._existing_insert_point(import_path, edit)
        if existing_insert_pt is not None:
            new_import = ", {}".format(import_path[-1])
            self.view.insert(edit, existing_insert_pt, new_import)
            sel_i = existing_insert_pt + 2
        else:
            # insert the new use statement
            insert_pt = self._new_insert_point(import_path)
            new_import = "use {};\n".format("::".join(import_path))
            self.view.insert(edit, insert_pt, new_import)
            sel_i = insert_pt + len(new_import) - 2 - len(import_path[-1])

        # Select just after the end of the statement
        sel = self.view.sel()
        sel.clear()
        sel.add(sublime.Region(sel_i, sel_i))

        # scroll t show it
        self.view.show(sel_i)
