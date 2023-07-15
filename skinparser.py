import configparser
import os
import re

import errors

class SkinParser(configparser.ConfigParser):
    # skin.ini uses // as comments because peppy is silly
    # also set ": " as first delimiter so that is what gets used when written
    def __init__(self, *args, comment_prefixes=('//', '#', ';'), delimiters=(': ', ':', '='), **kwargs):
        super().__init__(*args, comment_prefixes=comment_prefixes, delimiters=delimiters, **kwargs)
        # I forgot why this is important
        self.optionxform = str

    # No space around delimiters for correctly formattet output ini
    def write(self, *args, space_around_delimiters=False, **kwargs):
        super().write(*args, space_around_delimiters=space_around_delimiters, **kwargs)

    def get_with_default(self, section, option, *, default='Default', fallback=None, **kwargs):
        #TODO: Recurse

        value = self.get(section, option, fallback=None, **kwargs)
        if value is not None:
            return value

        # Option not found, fallback to Default and then fallback
        return self.get(default, option, fallback=fallback, **kwargs)

    def update_with_default(self, *args, **kwargs):
        raise NotImplementedError("TODO?")

def parse_ini(input_path, ini_name):
    ini_path = os.path.join(input_path, ini_name)

    if not os.path.exists(ini_path):
        raise errors.ConfigurationNotFound(f"INI file '{ini_path}' does not exist.")

    config = SkinParser()
    config.read(ini_path)

    return config

def parse_inis(input_path):
    # Parse the input INI files
    skin_config = parse_ini(input_path, 'skin.ini')
    variants_config = parse_ini(input_path, 'variants.ini')
    styles_config = parse_ini(input_path, 'styles.ini')
    notesets_config = parse_ini(input_path, 'notesets.ini')
    notes_config = parse_ini(input_path, 'notes.ini')

    return skin_config, variants_config, styles_config, notesets_config, notes_config

def write_ini(config, output_file, watermark=None):
    # Check if the directory of the file exists, and create it if necessary
    directory = os.path.dirname(output_file)
    if not os.path.exists(directory):
        os.makedirs(directory)

    # Write the config into a new INI file
    with open(output_file, 'w+', encoding='utf-8') as f:
        # Write watermark at the beginning of the file if one is set
        if watermark:
            for line in watermark:
                f.write(f'// {line}\n')
            f.write('\n')

        # Write skin config
        config.write(f)

        # Re-read file contents
        f.seek(0)
        file_content = f.read()

        # Replace [Mania\d+] with [Mania] due to configparser duplicate section issue
        modified_content = re.sub(r'\[Mania\d+\]', '[Mania]', file_content)

        # Rewrite and truncate
        f.seek(0)
        f.write(modified_content)
        f.truncate()
