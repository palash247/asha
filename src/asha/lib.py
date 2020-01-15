import jinja2
import markdown2
import htmlmin
import os, shutil
import json
from .utils import Utils
from .hacks import md_to_code

class Asha:
    @staticmethod
    def _check_setup(dir_name, files):
        for item in ["asha", ".gitignore", "asha.egg-info", "__pycache__", "__init__.py"]:
            if item in files: files.remove(item)
        return dir_name, files

    @staticmethod
    def _setup():
        cwd = os.getcwd()
        dir_path = os.path.dirname(__file__)
        Utils.copytree(dir_path, cwd, ignore=Asha._check_setup) 

    def __init__(self):
        with open("./config.json") as fp:
            global_config = json.loads(fp.read())
        self.theme = global_config.get("theme")
        self.rt = {
                    "pages":[],
                    "posts":[]
                  }
        self.minimal_rt = {
                    "pages":[],
                    "posts":[],
                    **global_config
                  }

    def _build(self):
        for item_type in ("posts", "pages"):
            for root, dirs, files in os.walk(item_type):
                for name in files:
                    if (
                         (len(name) > 3 and name[-3:] == ".md") \
                         or (len(name) > 9 and name[-9:] == ".markdown")
                       ) and name[0] != '.':
                        self._append_to_resource_table(item_type, os.path.join(root, name))
        self._minimal_rt_from_rt()
        self._clean_and_build_static_site_folders()
        self._buiild_from_rt()
    
    def _create_final_path(self, item_type, file_path):
        if item_type == "posts":
            file_path = os.path.splitext(file_path)[0] +".html"
        else:
            file_path = os.path.splitext(os.path.split(file_path)[-1])[0] + ".html"
        return file_path

    def _minimal_rt_from_rt(self):
        for k,v in self.rt.items():
            for item in v:
                d_ = {"url":self._create_final_path(k, item["file_path"])}
                d_.update(item["html"].metadata)
                self.minimal_rt[k].append(d_)
        self.minimal_rt["pages"].sort(key=lambda x:x['sort_order'])
        with open(os.path.join("themes", self.theme, "./config.json")) as fp:
            self.minimal_rt.update(json.loads(fp.read()))

    def _buiild_from_rt(self):
        for k,v in self.rt.items():
            for item in v:
                self._build_from_path(k, item)

    def _clean(self, path):
        if os.path.exists(path): shutil.rmtree(path)

    def _create_folders_if_needed(self, path, folders):
        for folder in folders:
            path = os.path.join(path, folder)
            if not os.path.exists(path): os.mkdir(path)

    def _build_folders(self, path):
        os.mkdir(path)
        static_path = os.path.join(path, "static")
        os.mkdir(static_path)
        Utils.copytree(os.path.join("themes", self.theme, "static"), static_path) 
        for item in self.rt["posts"]:
            file_path = item.get("file_path")
            self._create_folders_if_needed(path, file_path.split("/")[:-1])

    def _clean_and_build_static_site_folders(self):
        path = "_static_site"
        self._clean(path)
        self._build_folders(path)

    def _page_post_config(self, file_path):
        theme_config_path = os.path.splitext(os.path.join("themes", self.theme, file_path))[0] +".json"
        if os.path.exists(theme_config_path):
            with open(theme_config_path) as fp:
                return json.loads(fp.read())
        return {}

    def _append_to_resource_table(self, item_type, file_path):
        with open(file_path) as fp:
            file_content = md_to_code(fp.read())
        html = markdown2.markdown(file_content, extras=["metadata"])
        html.metadata.update(self._page_post_config(file_path))
        self.rt[item_type].append({"file_path":file_path, "html":html})

    def _build_from_path(self, item_type, item_details):
        file_path = item_details.get("file_path")
        html = item_details.get("html")
        jinja_vars = html.metadata
        jinja_vars["html_content"] = html
        jinja_vars["g"] = self.minimal_rt
        return self._jinja_render(item_type, file_path, jinja_vars)

    def _jinja_render(self, item_type, file_path, jinja_vars):
            if item_type == "posts":
                template_name = "post.jinja"
            elif jinja_vars.get("list", "false") == "true":
                template_name = jinja_vars["template"]
            else:
                template_name = "page.jinja"
            jinja_file_path = os.path.join("themes", self.theme, template_name)
            #pp_config = self._page_post_config(file_path)
            html = self._jinja_render_from_path(jinja_file_path, jinja_vars)
            self._create_html_file(item_type, file_path, html)
    
    def _jinja_render_from_path(self, jinja_file_path, jinja_vars):
        template_dir, template_file = os.path.split(jinja_file_path)
        template_loader = jinja2.FileSystemLoader(searchpath=template_dir)
        template_env = jinja2.Environment(loader=template_loader)

        template = template_env.get_template(template_file)
        
        html = template.render(**jinja_vars)
        return htmlmin.minify(html, remove_empty_space=True)

    def _create_html_file(self, item_type, file_path, html):
        file_path = os.path.join("_static_site", self._create_final_path(item_type, file_path))
        with open(file_path, "w+") as fp: fp.write(html)
