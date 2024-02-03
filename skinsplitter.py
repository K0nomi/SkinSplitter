import os
import time
import re
import shutil
from distutils.dir_util import copy_tree
import configparser

import skinparser
import exceptions

ALL_KEYS = {'Keys1': 1, 'Keys2': 2, 'Keys3': 3, 'Keys4': 4, 'Keys5': 5, 'Keys6': 6, 'Keys7': 7, 'Keys8': 8, 'Keys9': 9, 'Keys10': 10, 'Keys12': 12, 'keys14': 14, 'keys16': 16, 'Keys18': 18}
NOTE_PROPERTIES = [('NoteImage', 'NoteImage{}'), ('NoteImageH', 'NoteImage{}H'), ('NoteImageL', 'NoteImage{}L'), ('NoteImageT', 'NoteImage{}T')]

def sanitise(filename):
    return re.sub(r'[<>:"/\\|?*]', '_', filename).strip('. ').strip()

def parse_ini(input_path, ini_name):
    ini_path = os.path.join(input_path, ini_name)

    if not os.path.exists(ini_path):
        raise exceptions.MissingConfiguration(f"INI file '{ini_path}' does not exist.")

    config = skinparser.SkinParser()
    config.read(ini_path)

    return config

def parse_inis(input_path):
    # Parse the input INI files
    skin_config = parse_ini(input_path, 'skinsplitter.ini')
    variants_config = parse_ini(input_path, 'maniavariants.ini')
    styles_config = parse_ini(input_path, 'maniastyles.ini')
    notesets_config = parse_ini(input_path, 'manianotesets.ini')
    notes_config = parse_ini(input_path, 'manianotes.ini')

    return skin_config, variants_config, styles_config, notesets_config, notes_config

def write_ini(config, output_file, watermark=None):
    # Check if the directory of the file exists, and create it if necessary
    directory = os.path.dirname(output_file)
    if not os.path.exists(directory):
        os.makedirs(directory)

    # Write the config into a new INI file
    with open(output_file, 'w+') as f:
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

        # Replace [Mania\d+] with [Mania]
        modified_content = re.sub(r'\[Mania\d+\]', '[Mania]', file_content)

        # Rewrite and truncate
        f.seek(0)
        f.write(modified_content)
        f.truncate()

def process_config(skin_config, variants_config, styles_config, notesets_config, notes_config):
    # Create base config for variants to build from
    base_config = skinparser.SkinParser()
    base_config.update(skin_config)
    base_config.remove_section('Variants')

    processed_configs = []
    for variant in skin_config['Variants']:
        # Change variant name
        processed_variant = skinparser.SkinParser()
        processed_variant.update(base_config)
        processed_variant.set('General', 'Name', skin_config.get('Variants', variant))

        # Get variant noteset
        noteset = variants_config.get_with_default(variant, 'NoteSet', fallback='Default')

        # Process the different styles
        for keymode, keymode_keycount in ALL_KEYS.items():
            style = variants_config.get_with_default(variant, keymode)
            
            if style is None:
                # Keymode not defined, skip
                # TODO: let it set defaults even when keymode is not defined
                continue

            # Get style's keycount and compare it to variant's style keycount
            style_keycount = int(styles_config.get_with_default(style, 'Keys'))
            if style_keycount != keymode_keycount:
                # Keycounts dont match, throw
                raise exceptions.UnmatchedKeycounts(f'Style keycount "{keymode}" in variant "[{variant}]" does not match keycount "Keys: {style_keycount}" in style "[{style}]".')

            # Create new mania section
            style_section_name = 'Mania'+str(style_keycount)
            processed_variant.add_section(style_section_name)

            # Set defaults then section configs
            processed_variant[style_section_name].update(styles_config['Default'])
            processed_variant[style_section_name].update(styles_config[style])

            # Update notes
            for note_id in range(style_keycount):
                note_key = f'Note{note_id}'

                # Get which type this note is
                raw_note_type = styles_config.get_with_default(style, note_key)

                note_type = notesets_config.get_with_default(noteset, raw_note_type, fallback=raw_note_type)

                # Remove old notes thing from new config
                processed_variant.remove_option(style_section_name, note_key)

                # Get and set note images
                # TODO: set noteimages before rest of style configs, so they can be overwritten
                for prop in NOTE_PROPERTIES:
                    note_image_prop = notes_config.get_with_default(note_type, prop[0])
                    if note_image_prop is None:
                        # Skip if property not defined in note or default
                        continue
                    processed_variant.set(style_section_name, prop[1].format(note_id), note_image_prop)

        # Finally, add it to the list
        processed_configs.append(processed_variant)

    return processed_configs

def build_skin(skin_path, watermark=None, ini_path='SkinSplitter', input_path=None, output_path='output', temp_path='_temp', auto_execute=False):
    # Sanitise file paths, just in case
    if skin_path is not None: skin_path = sanitise(skin_path)
    if ini_path is not None: ini_path = sanitise(ini_path)
    if input_path is not None: input_path = sanitise(input_path)
    if output_path is not None: output_path = sanitise(output_path)
    if temp_path is not None: temp_path = sanitise(temp_path)

    temp_skin_path = os.path.join(temp_path, 'skin')
    # If automatically executing, use temp output
    if auto_execute:
        output_path = os.path.join(temp_path, 'output')
    # If input dir set, use that dir
    if input_path is not None: 
        skin_path = os.path.join(input_path, skin_path)

    # Throw if no skin directory
    if not os.path.exists(skin_path):
        raise exceptions.SkinNotFound(f"Skin {skin_path} was not found!")
    
    # The ini path is inside the skin directory
    ini_path = os.path.join(skin_path, ini_path)

    # Warn user if non-skinsplitter skin.ini exists
    if os.path.exists(os.path.join(skin_path, 'skin.ini')):
        print("Warning: Default skin.ini exists in skin directory, this will be ignored.")

    # Reset temp dir
    if os.path.exists(temp_path):
        shutil.rmtree(temp_path)
    os.mkdir(temp_path)
    # Add skin files to temp skin dir
    copy_tree(skin_path, temp_skin_path)

    # Parse the INI files
    configs = parse_inis(ini_path)

    # Process the config objects
    processed_configs = process_config(*configs)

    # write to new INI files
    for c in processed_configs:
        variant_name = sanitise(c['General']['Name'])

        #Create skin.ini in temp skin dir
        write_ini(c, os.path.join(temp_skin_path,'skin.ini'), watermark=watermark)

        # Create .osk
        output_filename = os.path.join(output_path, variant_name+'.osk')
        skin_file = shutil.make_archive(os.path.join(output_path, variant_name), 'zip', temp_skin_path) 
        os.replace(skin_file, output_filename)

        # Run .osk if auto executing. 
        # TODO: add option to not zip and just copy the files over if osu path specified.
        if auto_execute:
            os.startfile(output_filename)

        print(f'{variant_name} done.')

    if auto_execute:
        # Give time for osu to import
        # TODO: make this more rigorous
        time.sleep(len(processed_configs) // 1.5)
    # Cleanup temp dir
    shutil.rmtree(temp_path)

# Below here is unfinished code
if __name__ == '__main__':
    input_skin = 'Konomix v3 Gamma'
    ini_path = 'SkinSplitter'
    #output_path = 'output'
    watermark = [
        'This skin.ini was automatically generated using SkinSplitter (made by Konomi).', 
        'https://github.com/K0nomi/SkinSplitter/', 
        'The contents of this skin.ini are not designed to be readable.',
        f'check the `{ini_path}` folder in this skin\'s directory for the original configs.'
    ]

    build_skin(input_skin, watermark, ini_path=ini_path, auto_execute=True)

#note?: "specify osu path to automatically add skins, set path to auto to autodetect (check default location,start menu things installed programs. give warning if not able to detect)"
#note2: another arg, "in_place" will update just 1 variant for the skin the inis are in. when doing or not doing this, have the generated skin.ini watermark include the variant code.
#note3: add a service that autodetects changes in files in the skin folder and rebuilds the skin.ini

#TODO: add support for custom defaults (copying other skins)
