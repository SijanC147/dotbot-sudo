import json
import subprocess
from io import open
from os import path, remove

import dotbot
from dotbot.util import module


class Sudo(dotbot.Plugin):
    _directive = "sudo"

    def can_handle(self, directive):
        return self._directive == directive

    def handle(self, directive, data):
        if directive != self._directive:
            raise ValueError(f"sudo cannot handle directive {directive}")

        app = self._find_dotbot()
        base_directory = self._context.base_directory()
        data = [{"defaults": self._context.defaults()}] + data
        plugins = self._collect_plugins()
        sudo_conf = path.join(path.dirname(__file__), "sudo.conf.json")

        preserve_env_vals = [
            item.pop("preserve-env") for item in data if "preserve-env" in item
        ]
        preserve_env = preserve_env_vals[0] if preserve_env_vals else None
        if isinstance(preserve_env, bool) and preserve_env:
            env_args = "--preserve-env"
        elif isinstance(preserve_env, list) and all(
            isinstance(i, str) for i in preserve_env
        ):
            env_args = f'--preserve-env="{",".join(preserve_env)}"'
        else:
            env_args = ""

        self._write_conf_file(sudo_conf, data)

        proc_args = [
            "sudo",
            env_args,
            app,
            "--base-directory",
            base_directory,
            "--config-file",
            sudo_conf,
        ] + plugins
        self._log.debug(f"sudo: args to pass: {proc_args}")

        try:
            self._log.lowinfo("sudo: begin subprocess")
            subprocess.check_call(proc_args, stdin=subprocess.PIPE)
            self._log.lowinfo("sudo: end subprocess")
            self._delete_conf_file(sudo_conf)
            return True
        except subprocess.CalledProcessError as e:
            self._log.lowinfo("sudo: end subprocess")
            self._log.error(e)
            return False

    def _collect_plugins(self):
        ret = []
        for plugin in module.loaded_modules:
            # HACK should we compare to something other than _directive?
            if plugin.__name__ != self._directive:
                ret.extend(
                    iter(
                        ["--plugin", path.splitext(plugin.__file__)[0] + ".py"]
                    )
                )
        return ret

    def _delete_conf_file(self, conf_file):
        if path.exists(conf_file):
            remove(conf_file)

    def _find_dotbot(self):
        base = path.dirname(path.dirname(dotbot.__file__))
        ret = path.join(base, "bin", "dotbot")
        self._log.debug(f"sudo: dotbot app path: {ret}")
        return ret

    def _write_conf_file(self, conf_file, data):
        self._delete_conf_file(conf_file)
        with open(conf_file, "w", encoding="utf-8") as jfile:
            my_json_str = json.dumps(data, ensure_ascii=False)
            if isinstance(my_json_str, str):
                my_json_str = my_json_str.encode().decode("utf-8")

            jfile.write(my_json_str)
