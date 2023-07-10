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

def parse_inis(input_dir):
    # Parse the input INI files
    skin_config = skinparser.SkinParser()
    skin_config.read(os.path.join(input_dir, 'skin.ini'))

    variants_config = skinparser.SkinParser()
    variants_config.read(os.path.join(input_dir, 'maniavariants.ini'))

    styles_config = skinparser.SkinParser()
    styles_config.read(os.path.join(input_dir, 'maniastyles.ini'))

    notes_config = skinparser.SkinParser()
    notes_config.read(os.path.join(input_dir, 'manianotes.ini'))

    return skin_config, variants_config, styles_config, notes_config

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

def process_config(skin_config, variants_config, styles_config, notes_config):
    # Create base config for variants to build from
    base_config = skinparser.SkinParser()
    base_config.update(skin_config)
    base_config.remove_section('Mania')

    processed_configs = []
    for variant in skin_config['Mania']:
        # Change variant name
        processed_variant = skinparser.SkinParser()
        processed_variant.update(base_config)
        processed_variant.set('General', 'Name', skin_config.get('Mania', variant))

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
                note_type = styles_config.get_with_default(style, note_key)

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

def build_skin(input_skin, watermark=None, ini_directory='SkinSplitter', input_dir = None, output_dir='output', temp_dir='_temp', auto_execute=False):
    ini_dir = os.path.join(input_skin, ini_directory)
    temp_skin_dir = os.path.join(temp_dir, 'skin')
    # If automatically executing, use temp output
    output_dir = os.path.join(temp_dir, 'output') if auto_execute else output_dir

    # Warn user if non-skinsplitter skin.ini exists
    if os.path.exists(os.path.join(input_skin, 'skin.ini')):
        print("Warning: Normal skin.ini exists in input directory, this will be ignored.")

    # Reset temp dir
    if os.path.exists(temp_dir):
        shutil.rmtree(temp_dir)
    os.mkdir(temp_dir)
    # Add skin files to temp skin dir
    copy_tree(input_skin, temp_skin_dir)

    # Parse the INI files
    configs = parse_inis(ini_dir)

    # Process the config objects
    processed_configs = process_config(*configs)

    # write to new INI files
    for c in processed_configs:
        variant_name = c['General']['Name']

        #Create skin.ini in temp skin dir
        write_ini(c, os.path.join(temp_skin_dir,'skin.ini'), watermark=watermark)

        # Create .osk
        output_filename = os.path.join(output_dir, variant_name+'.osk')
        skin_file = shutil.make_archive(os.path.join(output_dir, variant_name), 'zip', temp_skin_dir) 
        os.replace(skin_file, output_filename)

        # Run .osk if auto executing. TODO: add option to not zip and just copy the files over if osu path specified.
        if auto_execute:
            os.startfile(output_filename)

        print(f'{variant_name} done.')

    if auto_execute:
        # Give time for osu to import, TODO: make this mor rigorous
        time.sleep(1)
    # Cleanup temp dir
    shutil.rmtree(temp_dir)

# Below here is unfinished code
if __name__ == '__main__':
    input_skin = 'Konomix v3 Gamma'
    ini_directory = 'SkinSplitter'
    #output_dir = 'output'
    watermark = [
        'This skin.ini was automatically generated using SkinSplitter (made by Konomi).', 
        'https://github.com/K0nomi/SkinSplitter/', 
        'The contents of this skin.ini are not designed to be readable.',
        f'check the `{ini_directory}` folder in this skin\'s directory for the original configs.'
    ]

    build_skin(input_skin, watermark, ini_directory=ini_directory, auto_execute=True)

#note?: "specify osu path to automatically add skins, set path to auto to autodetect (check default location,start menu things installed programs. give warning if not able to detect)"
#note2: another arg, "in_place" will update just 1 variant for the skin the inis are in. when doing or not doing this, have the generated skin.ini watermark include the variant code.
#note3: add a service that autodetects changes in files in the skin folder and rebuilds the skin.ini

#TODO: add support for custom defaults