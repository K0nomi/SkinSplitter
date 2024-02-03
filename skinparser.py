import configparser

class SkinParser(configparser.ConfigParser):
    def __init__(self, *args, comment_prefixes=('//', '#', ';'), delimiters=(': ', ':', '='), **kwargs):
        super().__init__(*args, comment_prefixes=comment_prefixes, delimiters=delimiters, **kwargs)
        self.optionxform = str

    def write(self, *args, space_around_delimiters=False, **kwargs):
        super().write(*args, space_around_delimiters=space_around_delimiters, **kwargs)

    def get_with_default(self, section, option, *, default='Default', **kwargs):
        #TODO: Recurse

        value = self.get(section, option, fallback=None, **kwargs)
        if value is not None: 
            return value
        
        # Option not found, fallback to Default and then None
        return self.get(default, option, fallback=None, **kwargs)

    def update_with_default(self, *args, **kwargs):
        raise NotImplementedError("TODO?")
