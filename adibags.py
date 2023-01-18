import os
import tomllib

from colorama import Fore

import blizzardapi


class AdiBagsAddon:
    def __init__(self, config_file_path: str, access_token: str, itemname_cache: dict):
        with open(config_file_path, "rb") as f:
            config = tomllib.load(f)
        self.filter_name = config["filter_name"]
        self.replacers = config["replacers"]  # key: string to replace, value: replacement
        self.prefixes = config["prefixes"]
        self._add_default_replacers(config)
        self.access_token = access_token
        self.itemname_cache = itemname_cache
        self.categories = set()
        self._getforms({"main.lua": None, "toc.toc": None, "locale.lua": None})

    def get_item_name(self, itemid: int | str) -> str:
        itemid = str(itemid)
        if self.access_token == "DEBUG":
            return ""
        if self.itemname_cache is None:
            self.itemname_cache = {}
        if itemid in self.itemname_cache:  # Check if we have the name cached
            item_name = self.itemname_cache[itemid]
            print(f"\t\t{Fore.CYAN}Found Item in Item Cache: {itemid} ➡ {item_name}{Fore.RESET}")
            return item_name
        else:
            item_name = blizzardapi.fetch_itemname(itemid, self.access_token)
            self.itemname_cache[itemid] = item_name
        return item_name

    def add_category(self, config_file_path):
        category = AdiBagsCategory(config_file_path)
        self.categories.add(category)
        print(f"\n{category}")

    def build(self):
        print(self.replacers)
        print("Building AdiBags Addon.")
        print("Building Item Maps.")
        self._build_itemmaps()
        print("Building Partials.")
        self._getpartials()
        print("Saving Files.")
        self._save_files()

    def _build_itemmaps(self):
        for category in self.categories:
            for subcategory in category.subcategories:
                print(f"Getting Names for: {Fore.YELLOW}{category.name}/{subcategory.name}{Fore.RESET}")
                for item_id in subcategory.item_ids:
                    item_name = self.get_item_name(item_id)
                    subcategory.item_map[item_id] = item_name

    def _replace(self, text: str) -> str:
        for key in self.replacers:
            text = text.replace(f"%{key}%", str(self.replacers[key]))
        return text

    def _save_files(self):
        # TOC
        print("Creating TOC file.")
        str_toc = self._replace(self.forms["toc.toc"])
        with open(
                f"out/AdiBags_{self.filter_name}.toc", "w", encoding="utf8"
        ) as f:
            f.write(str_toc)
        # Main Addon
        print("Creating Main Addon file.")
        str_main = self.forms["main.lua"]
        for partial in self.partials.keys():
            str_main = str_main.replace(f"--!!{partial}!!--", self.partials[partial])
        str_main = self._replace(str_main)
        with open(
                f"out/AdiBags_{self.filter_name}.lua", "w", encoding="utf8"
        ) as f:
            f.write(str_main)
        # Markdown
        print("Creating Markdown file.")
        str_md = "# How to Read this\n\nAll items are broken down into categories, with itemID followed by the Item name.\n\nLatest version: @project-version@\n\n"
        for category in sorted(self.categories):
            str_md += f"## {category.name}\n\n{category.markdown_description_overwrite or category.description}\n\n" \
                      f"Default Color: ![{category.color:06x}](https://via.placeholder.com/16/{category.color:06x}/{''.join(['{:x}'.format(15 - int(c, 16)) if c.isalnum() else c for c in str(f'{category.color:06x}')])}?text={category.color:06x})\n\n"
            for subcategory in sorted(category.subcategories):
                str_md += f"### {subcategory.name}\n\n{subcategory.markdown_description_overwrite or subcategory.description}\n\n" \
                          f"Default Color: ![{subcategory.color:06x}](https://via.placeholder.com/16/{subcategory.color:06x}/{''.join(['{:x}'.format(15 - int(c, 16)) if c.isalnum() else c for c in str(f'{subcategory.color:06x}')])}?text={subcategory.color:06x})\n\n"
                for item_id in sorted(subcategory.item_map.keys()):
                    str_md += f"* {item_id} - {subcategory.item_map[item_id]}\n"
                str_md += "\n"
        with open(
                f"out/supported_items.md", "w", encoding="utf8"
        ) as f:
            f.write(str_md)
        # Todo: Locale

    def _getpartials(self):
        # TODO: maybe instead of trying to read from files build live?
        self.partials = {"MatchIDs": "", "Matching": "", "DefaultOptions": "", "Prefixes": "", "ConfigMenu": ""}

        # Prefixes are defined on an addon base
        for prefix in self.prefixes:
            if prefix.startswith("icon:"):
                prefix = prefix.replace("icon:", "")
                self.partials["Prefixes"] += f'\t\t\t\t\t["|T:{prefix}" .. AdiBags.HEADER_SIZE .. ":" .. AdiBags.HEADER_SIZE .. ":-2:-10|t"] = "|T{prefix}:" .. AdiBags.HEADER_SIZE .. "|t",\n'
            else:
                self.partials["Prefixes"] += f'\t\t\t\t\t["{prefix}"] = "{prefix}",\n'

        e_order = 5
        # Working through the categories
        for category in self.categories:
            self.partials["ConfigMenu"] += f'\t\t{category.simple_name}_config = {{\n' \
                                           f'\t\t\ttype = "group",\n' \
                                           f'\t\t\tname = "|cff{category.color:06x}{category.name}|r",\n' \
                                           f'\t\t\tdesc = "{category.addon_description_overwrite or category.description}",\n' \
                                           f'\t\t\tinline = true,\n' \
                                           f'\t\t\torder = {e_order},\n' \
                                           f'\t\t\targs = {{\n'
            e_order += 5
            i_order = 10
            for subcategory in category.subcategories:
                self.partials["MatchIDs"] += f"{subcategory.simple_name}_IDs = {{\n"
                for item in subcategory.item_map.keys():
                    self.partials["MatchIDs"] += f"{item}, -- {subcategory.item_map[item]}\n"
                self.partials["MatchIDs"] += "}\n\n"
                self.partials["Matching"] += f'\n\tif self.db.profile.move{subcategory.simple_name} then\n' \
                                             f'\t\tResult[formatBagTitle(self, "{subcategory.name}", "{subcategory.color:06x}")] = AddToSet({subcategory.simple_name}_IDs)\n' \
                                             f'\tend'
                self.partials["DefaultOptions"] += f"\t\t\tmove{subcategory.simple_name} = {str(subcategory.enabled_by_default).lower()},\n"
                self.partials["ConfigMenu"] += f'\t\t\t\tmove{subcategory.simple_name} = {{\n' \
                                               f'\t\t\t\t\tname = "{subcategory.name}",\n' \
                                               f'\t\t\t\t\tdesc = "{subcategory.addon_description_overwrite or subcategory.description}",\n' \
                                               f'\t\t\t\t\ttype = "toggle",\n' \
                                               f'\t\t\t\t\torder = {i_order}\n' \
                                               f'\t\t\t\t}},\n'
                i_order += 10
            self.partials["ConfigMenu"] += f'\t\t\t}},\n\t\t}},\n'
        if os.environ.get("DEBUG") == "1":
            print(f"{Fore.RED}### DEBUG ###{Fore.RESET}")
            print(f"{Fore.BLUE}{self.partials['MatchIDs']}")
            print(f"{Fore.YELLOW}{self.partials['Matching']}")
            print(f"{Fore.GREEN}{self.partials['DefaultOptions']}")
            print(f"{Fore.MAGENTA}{self.partials['Prefixes']}")
            print(f"{Fore.CYAN}{self.partials['ConfigMenu']}")
            print(f"{Fore.RED}### DEBUG ###{Fore.RESET}")

    def _getforms(self, forms: dict):
        self.forms = forms
        for form in self.forms.keys():
            with open(f"forms/{form}", "r", encoding="utf8") as f:
                self.forms[form] = f.read()

    def _add_default_replacers(self, config: dict):
        self.replacers["FILTER_NAME"] = self.filter_name
        self.replacers["FILTER_DESCRIPTION"] = config["filter_description"]
        self.replacers["FILTER_AUTHOR"] = config["filter_author"]
        self.replacers["ADDON_COLOR"] = f"{self.replacers['ADDON_COLOR']:06x}"


class AdiBagsCategory:
    def __init__(self, config_file_path: str):
        self.subcategories = set()
        with open(config_file_path, "rb") as f:
            config = tomllib.load(f)
        for key, value in config.items():
            if type(value) is dict and key != "category_description":
                self.subcategories.add(AdiBagsSubCategory(value))

        self.name = config["category_name"]
        self.simple_name = ''.join(e for e in self.name if e.isalnum())
        self.color = config["category_color"]
        description = config["category_description"]
        self.description = description.get("_", None)
        self.markdown_description_overwrite = description.get("markdown", None)
        self.addon_description_overwrite = description.get("addon", None)
        self.item_map = {}

    @property
    def item_ids(self):
        item_ids = set()
        for subcategory in self.subcategories:
            item_ids.update(subcategory.item_ids)
        return item_ids

    def __str__(self):
        return f"""Category '{self.name}' (with {len(self.subcategories)} subcategories) with a total of {len(self.item_ids)} items.
        Color: {hex(self.color)}
        Markdown Description: {self.markdown_description_overwrite or self.description}
        Addon Description: {self.addon_description_overwrite or self.description}
        """

    def __lt__(self, other):
        return self.name < other.name


class AdiBagsSubCategory:
    def __init__(self, subcategory_config: dict):
        self.name = subcategory_config["name"]
        self.simple_name = ''.join(e for e in self.name if e.isalnum())
        self.color = subcategory_config["color"]
        self.enabled_by_default = subcategory_config.get("enabled_by_default", True)
        description = subcategory_config["description"]
        self.description = description.get("_", None)
        self.markdown_description_overwrite = description.get("markdown", None)
        self.addon_description_overwrite = description.get("addon", None)
        self.item_ids = set(subcategory_config.get("items", []))
        self.item_map = {}
        self.bonus_condition = subcategory_config.get("bonus_condition", None)
        self.override_method = subcategory_config.get("override_method", None)

    def __str__(self):
        return f"""SubCategory '{self.name}' with {len(self.item_ids)} items.
        Color: {hex(self.color)}
        disabled_by_default: {self.disabled_by_default}
        Markdown Description: {self.markdown_description_overwrite or self.description}
        Addon Description: {self.addon_description_overwrite or self.description}
        Bonus Condition: {self.bonus_condition}
        Override Method: {self.override_method}
        """

    def __lt__(self, other):
        return self.name < other.name
