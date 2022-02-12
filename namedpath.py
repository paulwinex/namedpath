# coding=utf-8
from __future__ import print_function, absolute_import
from os.path import join, normpath, exists, abspath, expanduser, expandvars
import os
import json
import copy
import logging
import getpass
import re
import sys

if sys.version_info.major < 3:
    string_types = basestring,
else:
    string_types = str,


def __setup_simple_logger(lg):      # type: (logging.Logger) -> logging.Logger
    lg.addHandler(logging.StreamHandler())
    lg.propagate = False
    return lg


logger = logging.getLogger(__name__)
if not logger.handlers:
    logger = __setup_simple_logger(logger)

if sys.version_info.major > 2:
    unicode = type


class NamedPathTree(object):
    """
    Class provide you to control folder structure paths
    """

    def __init__(self, root_path, path_list=None, default_context=None, **kwargs):
        self.kwargs = kwargs
        if not isinstance(root_path, string_types):
            raise ValueError('Root directory must be string type')
        self._root_path = abspath(expandvars(expanduser(root_path)))
        self._scope = {}
        self.default_context = {}
        if default_context:
            self.update_default_context(default_context)
        if path_list:
            self.update_patterns(path_list)

    def __str__(self):
        return self.path

    def __repr__(self):
        return '<NamedPathTree "{}">'.format(self.path)

    @classmethod
    def load_from_files(cls, root, files):
        patterns = {}
        for f in files:
            patterns.update(cls._load_commented_json(f))
        return cls(root, patterns)

    @staticmethod
    def _load_commented_json(path, **kwargs):
        text = open(path).read()
        regex = r'\s*(/{2}).*$'
        regex_inline = r'(:?(?:\s)*([A-Za-z\d.{}]*)|((?<=\").*\"),?)(?:\s)*(((/{2}).*)|)$'
        lines = text.split('\n')
        for index, line in enumerate(lines):
            if re.search(regex, line):
                if re.search(r'^' + regex, line, re.IGNORECASE):
                    lines[index] = ""
                elif re.search(regex_inline, line):
                    lines[index] = re.sub(regex_inline, r'\1', line)
        multiline = re.compile(r"/\*.*?\*/", re.DOTALL)
        cleaned_text = re.sub(multiline, "", '\n'.join(lines))
        return json.loads(cleaned_text, **kwargs)

    # props

    @property
    def path(self):
        """
        Root path of tree

        Returns
        -------
        str
        """
        return self._root_path

    def get_patterns(self):
        return {name: path.options for name, path in self._scope.items()}

    def get_context(self):
        return self.default_context

    def update_patterns(self, path_list):
        """
        Update pattern list

        Parameters
        ----------
        path_list: dict
        """
        to_remove = []
        option_presets = path_list.pop('option_presets', {})
        for path_name, options in path_list.items():    # type: str, str
            # skip empty and lowercase names
            if not path_name or not path_name.isupper():
                continue
            # None in options mean DELETE pattern
            if options is None:
                to_remove.append(path_name)
                continue
            # convert short path record to full options
            if isinstance(options, string_types):
                options = dict(path=options)
            # check options type
            if not isinstance(options, dict):
                raise TypeError('Wrong type of Pattern options')
            # apply preset
            preset_name = options.pop('preset', None)
            if preset_name:
                for k, v in option_presets[preset_name].items():
                    # merge dict
                    if all([k in options,
                            k in option_presets,
                            isinstance(options.get(k), dict),
                            isinstance(option_presets.get(k), dict)]):
                        for _k, _v in option_presets[k].items():
                            options[k].setdefault(_k, _v)
                    # just copy value
                    else:
                        options.setdefault(k, v)
            # additive mode
            if path_name.endswith('+'):
                path_name = path_name.strip('+')
                if path_name in self._scope:
                    self._scope[path_name].options.update(options)
                    continue
            # check options
            if 'path' not in options and path_name not in self._scope:
                raise ValueError('No "path" parameter in pattern options: {}'.format(path_name))
            self._scope[path_name] = NamedPath(self.path, path_name, options, self._scope,
                                               default_context=self.default_context, **self.kwargs)
        for name in to_remove:
            self._scope.pop(name, None)

    def update_default_context(self, context):
        """
        Update existing default context

        Parameters
        ----------
        context: dict
        """
        self.default_context.update(context)

    # get path

    def get_path(self, name, context=None, skip_context_errors=False, create=False, **kwargs):
        """
        Get full path by name and context

        Parameters
        ----------
        name: str
            Path name
        context: dict
            Variables
        skip_context_errors: bool
        create: bool
            Create path now if not exists

        Returns
        -------
        str
        """
        ctl = self.get_path_instance(name)    # type: NamedPath
        path = ctl.solve(context, skip_context_errors=skip_context_errors, **kwargs)
        if create and not exists(path):
            ctl.makedirs(context, skip_context_errors=skip_context_errors)
        return path

    def get_path_variables(self, name):
        """
        Get all variable names in pattern path

        Parameters
        ----------
        name: str

        Returns
        -------
        list
        """
        return self.get_path_instance(name).get_pattern_variables()

    def get_raw_path(self, name):
        """
        Raw path with unexpanded variables

        Parameters
        ----------
        name: str

        Returns
        -------
        str
        """
        return self.get_path_instance(name).get_relative()

    def get_raw_pattern(self, name):
        """
        Raw path with unexpanded variables and parent pattern

        Parameters
        ----------
        name: str

        Returns
        -------
        str
        """
        return self.get_path_instance(name).path

    def get_path_instance(self, name):
        """
        Get Path class instance by name

        Parameters
        ----------
        name: str

        Returns
        -------
        NamedPath
        """
        try:
            return self._scope[name.upper()]
        except KeyError:
            raise PathNameError('Pattern named {} not found'.format(name.upper()))

    def get_path_names(self):
        """
        List of all pattern names in current tree

        Returns
        -------
        tuple
        """
        # return tuple(sorted(self._scope.keys()))
        return tuple(self._scope.keys())

    def iter_patterns(self):
        """
        Generator for paths iteration
        """
        for name in self.get_path_names():
            yield self.get_path_instance(name)

    def parse(self, path, with_context=False):
        """
        Reverse existing path to a pattern name

        Parameters
        ----------
        path: str
        with_context: bool

        Returns
        -------
        str or list
        """
        match_names = []
        for name, path_instance in self._scope.items():  # type: NamedPath
            context = path_instance.parse(path)
            if context is not None:
                match_names.append((name, context, path_instance))
        if len(match_names) > 1:
            raise MultiplePatternMatchError(', '.join([x[0] for x in match_names]))
        if not match_names:
            raise NoPatternMatchError(path)
        name, context, instance = match_names[0]
        if with_context:
            return name, context
        else:
            return name

    def get_pattern_variables(self, name):
        return self.get_path_instance(name).get_pattern_variables()

    def get_all_required_variables(self):
        """
        Get all required variables for all patterns

        Returns
        -------
        list
        """
        variables = set()
        for pat in self.iter_patterns():
            variables.update(pat.get_pattern_variables())
        return list(variables)

    def is_empty(self):
        return len(self._scope) > 0

    # check

    def check_uniqueness_of_parsing(self, full_context):
        """
        Checking your patterns for uniques.
        Each path should be reversible without match with other patterns.
        This checking require full context with variables for all patterns.
        Use this method when you develop your structure.

        Parameters
        ----------
        full_context: dict

        Returns
        -------
        dict
        """
        result = dict(
            errors={},
            success=[]
        )
        for name in self.get_path_names():
            path = self.get_path(name, full_context)
            try:
                parsed_name = self.parse(path)
            except NoPatternMatchError as e:
                msg = 'Error {}: {}'.format(e.__class__.__name__, e)
                logger.warning(msg)
                result['errors'][name] = msg
            except MultiplePatternMatchError as e:
                msg = 'Error {}: {}'.format(e.__class__.__name__, e)
                logger.warning(msg)
                result['errors'][name] = msg
            else:
                if parsed_name != name:
                    msg = 'Generated and parsed names not match: {} -> {}'.format(name, parsed_name)
                    logger.warning(msg)
                    result['errors'][name] = msg
                else:
                    result['success'].append(name)
        logger.info('Total patterns: %s' % len(self._scope))
        logger.info('Success parsing: %s' % len(result['success']))
        logger.info('Errors: %s' % len(result['errors']))
        return result

    def check_paths_attributes(self, names=None, fix=False):
        """
        Recursive searching and checking all of existing paths and fix them attributes
        """
        if os.name == 'nt':
            raise NotImplementedError('Working with attributes on Windows not supported yet')
        names = names or self.get_path_names()
        for name in names:
            pass
        # TODO

    # attributes

    def update_attributes(self, names, context, **kwargs):
        raise NotImplementedError
        # TODO

    # utils

    def transfer_to(self, other_tree, names_map=None, move=False):
        """
        Move files from one tree to other.
        All names must be matched or have rename map.

        Parameters
        ----------
        other_tree: NamedPathTree
            Target tree
        names_map: dict
            rename map
        move: bool
            Copy or move files

        Returns
        -------
        dict
        """
        raise NotImplementedError

    # I/O

    def makedirs(self, context=None, names=None, root_path_name=None, skip_context_errors=True, **kwargs):
        """Create dirs"""
        names = names or self.get_path_names()
        paths = [self.get_path_instance(name) for name in names]
        if root_path_name:
            if root_path_name not in self.get_path_names():
                raise PathNameError
            paths = [path for path in paths if root_path_name in path.get_all_parent_names()]
        for path_ctl in paths:
            path_ctl.makedirs(context, skip_context_errors=skip_context_errors, **kwargs)

    def clear_empty_dirs(self, context=None, names=None):
        raise NotImplementedError

    def show_tree(self, **kwargs):
        """
        Print tree structure to console

        PATTERN_NAME| path

        """
        def _show(elements, print_path=True, print_name=True, max_name_width=0, indent=0, placeholder='-'):
            # for elem in sorted(elements, key=lambda x: x['inst'].name):
            for elem in elements:
                print(''.join(
                    [
                        placeholder*indent*2 if (not print_path and print_name) else '',
                        ('{:>{}}|'.format(elem['inst'].name, max_name_width+2) if print_name else '') if print_path else elem['inst'].name,
                        placeholder*indent*2 if print_path else '',
                        ('/'+elem['inst'].get_short()) if print_path else '']))
                if elem['ch']:
                    _show(elem['ch'], print_path=print_path, print_name=print_name, max_name_width=max_name_width,
                          indent=indent+1, placeholder=placeholder)
        tr = {x.name: {'inst': x, 'ch': []} for x in self.iter_patterns() if x.name}
        tr[''] = {'inst': None, 'ch': []}
        for name, item in tr.items():
            if not item['inst']:
                continue
            par = item['inst'].get_parent()
            if par:
                tr[par.name]['ch'].append(item)
            else:
                tr['']['ch'].append(item)
        print('ROOT: {}'.format(self.path))
        print('='*50)
        column_width = max([len(x) for x in tr.keys()])
        _show(tr['']['ch'], max_name_width=column_width, **kwargs)
        print('=' * 50)


class NamedPath(object):
    """Class provide logic of one single named path"""
    _default_dir_permission = 0o755
    _default_file_permission = 0o644

    def __init__(self, base_dir, name, options, scope, **kwargs):
        if 'path' not in options:
            raise ValueError('No parameter "path" in options: {}'.format(name))
        self.name = name
        self.options = options
        self._scope = scope
        self.kwargs = kwargs
        self.base_dir = base_dir
        self.default_context = kwargs.get('default_context', {})

    def __str__(self):
        return self.path

    def __repr__(self):
        return '<FSPath %s "%s">' % (self.name, self.path)

    def get_context(self, context=None):
        """
        Collect context values

        Parameters
        ----------
        context: dict

        Returns
        -------
        dict
        """
        ctx = copy.deepcopy(self.default_context)
        ctx.update(context)
        for k, v in self.options.get('defaults', {}).items():
            ctx.setdefault(k, v)
        ctx.setdefault('user', getpass.getuser())
        return ctx

    @property
    def path(self):
        """
        Raw path

        Returns
        -------
        str
        """
        return self.options['path']

    @property
    def default_dir_permission(self):
        return self.kwargs.get('default_dir_permission') or self._default_dir_permission

    @property
    def default_file_permission(self):
        return self.kwargs.get('default_file_permission') or self._default_dir_permission

    @property
    def default_user(self):
        return getpass.getuser()

    @property
    def default_group(self):
        return self.kwargs.get('default_group') or self.default_user

    # solve

    def solve(self, context, skip_context_errors=False, relative=False, local=False):
        """
        Resolve path from pattern with context to relative path

        Parameters
        ----------
        context: dict
        skip_context_errors: bool
        relative: bool
        local: bool

        Returns
        -------
        str
        """
        if local:
            parent_path = ''
        else:
            parent = self.get_parent()
            if parent:
                parent_path = parent.solve(context, skip_context_errors, relative)
            else:
                if relative:
                    parent_path = ''
                else:
                    parent_path = self.base_dir
        parts = self.get_parts(context, solve=True, dirs_only=False, skip_context_errors=skip_context_errors)
        if parts:
            rel_path = os.path.join(*parts)
        else:
            rel_path = ''
        return os.path.join(parent_path, rel_path)

    def iter_path(self, context=None, solve=True, dirs_only=True,
                  skip_context_errors=False, full_path=False, include_parents=False):
        """
        Iterate path by parts
        """
        base = ''
        if full_path:
            parent = self.get_parent()
            if parent:
                base = parent.solve(context, skip_context_errors=skip_context_errors) if solve else parent.path
                if include_parents:
                    try:
                        for part in parent.iter_path(context, solve=solve,
                                                     dirs_only=dirs_only,
                                                     full_path=full_path,
                                                     skip_context_errors=False,
                                                     include_parents=include_parents):
                            yield part
                    except PathContextError:
                        return
            else:
                base = self.base_dir
        p = ''
        for part in self.get_parts(context, solve, dirs_only, skip_context_errors):
            p = os.path.join(p, part)
            yield os.path.join(base, p)

    def get_parts(self, context=None, solve=False, dirs_only=False, skip_context_errors=False):
        context = self.get_context(context or {})
        context_variables = [x.upper() for x in context.keys()]
        parts = []
        for part in self.get_short().split(os.path.sep):
            if dirs_only and os.path.splitext(part)[1]:
                continue
            if solve:
                # variables = [val.split(':')[0].split('|')[0].upper() for val in re.findall(r"{(.*?)}", part)]
                variables = self.get_pattern_variables(part)
                miss = [x for x in variables if x not in context_variables]
                if miss:
                    if skip_context_errors:
                        break
                    else:
                        raise PathContextError(str(miss))
                part = self.expand_variables(part, context)
            parts.append(part)
        return parts

    def expand_variables(self, text, context):
        """
        Resolve variables in pattern

        Parameters
        ----------
        text: str
        context: dict

        Returns
        -------
        str
        """
        ctx = self.get_context(context or {})
        return CustomFormatString(text).format(**{k.upper(): v for k, v in ctx.items()})

    def convert_types(self, context):
        """
        Convert context types after parsing
        """
        types = self.options.get('types')
        if not types:
            return context
        for name, tp in types.items():
            if name.lower() in context:
                expr = '{}({})'.format(tp, repr(context[name.lower()]))
                context[name.lower()] = eval(expr)
        return context

    def get_pattern_variables(self, pattern=None):
        """
        Extract variables names from pattern

        Returns
        -------
        list
        """
        variables = []
        for val in re.findall(r"{(.*?)}", pattern or self.get_relative()):
            variables.append(val.split(':')[0].split('|')[0])
        return sorted(list(set(variables)))

    # paths

    def get_relative(self):
        """
        Relative to base dir

        Returns
        -------
        str
        """
        par = self.get_parent()
        if par:
            return normpath(join(
                par.get_relative(),
                self.get_short())
            )
        else:
            return self.path

    def get_short(self):
        """
        Relative to parent

        Returns
        -------
        str
        """
        return normpath(self.path.split(']', 1)[-1].lstrip('\\/'))

    def get_absolute(self):
        """
        Absolute path
        """
        return os.path.normpath(os.path.join(self.base_dir, self.get_relative()))

    # parent

    def get_parent_name(self):
        """
        Get name of parent pattern

        Returns
        -------
        str
        """
        match = re.search(r"^\[(\w+)]/?(.*)", self.path)
        if match:
            return match.group(1)

    def get_parent(self):
        """
        Get controller of parent pattern

        Returns
        -------
        NamedPath
        """
        parent_name = self.get_parent_name()
        if parent_name:
            try:
                return self._scope[parent_name]
            except KeyError:
                raise PathNameError('No path named {}'.format(parent_name))

    def get_all_parent_names(self):
        """
        Get list of all parent patterns

        Returns
        -------
        list
        """
        names = []
        p = self
        while True:
            parent_name = p.get_parent_name()
            if not parent_name:
                break
            names.append(parent_name)
            p = p.get_parent()
        names.reverse()
        return names

    # patterns

    def as_glob(self, prefix=None, context=None):
        """
        Convert pattern to glob-pattern

        Parameters
        ----------
        prefix: str
            Root path
        context: dict

        Returns
        -------
        str
        """
        path = self.get_relative()
        if prefix:
            path = normpath(join(prefix, path.lstrip('\\/')))

        def get_context_val(match):
            val = match.group(0)
            if context:
                try:
                    return self.expand_variables(val, context)
                except KeyError:
                    pass
            return '*'

        return re.sub(r"{.*?}", get_context_val, path)

    def as_regex(self, prefix=None, named_values=True, context=None):
        """
        Convert pattern to regex

        Parameters
        ----------
        prefix: str
            Root path
        named_values: bool
            Make named groups in regex
        context: dict

        Returns
        -------
        str
        """
        simple_pattern = r'[^/\\]+'
        named_pattern = r'(?P<%s>[^/\\]+)'
        path = self.get_relative()
        if prefix:
            path = normpath(join(prefix, path.lstrip('\\/')))
        names = set()

        def get_subpattern(match):
            v = match.group(0)
            name = v.strip('{}').split(':')[0].split('|')[0].lower()
            if context:
                try:
                    expanded = self.expand_variables(v, context)
                    names.add(name)
                    return expanded
                except KeyError:
                    pass
            if name in names:
                return simple_pattern
            names.add(name)
            if named_values:
                return named_pattern % name
            else:
                return simple_pattern

        pattern = re.sub(r"{.*?}", get_subpattern, path.replace('\\', '\\\\'))
        pattern = pattern.replace('.', '\\.')
        pattern = '^%s$' % pattern
        return pattern

    def parse(self, path):
        """
        Extract context from path

        Returns
        -------
        dict
        """
        pattern = self.as_regex(self.base_dir)
        m = re.match(pattern, path, re.IGNORECASE)
        if m:
            context = self.convert_types(m.groupdict())
            return context

    def get_permission_list(self, **kwargs):
        """chmod parameter"""
        mode_list = self._get_list(self.options.get('perm'))
        mode_list = [self._valid_mode(x) for x in mode_list]
        for i in range(len(mode_list)):
            if not mode_list[i]:
                mode_list[i] = kwargs.get('default_permission') or self.default_dir_permission
        return mode_list

    def get_group_list(self, default_group=None, **kwargs):
        return self._get_option_list_by_value_name('groups', 'default_group', default_group, **kwargs)

    def get_user_list(self, default_user=None, **kwargs):
        return self._get_option_list_by_value_name('users', 'default_user', default_user, **kwargs)

    # I/O

    def makedirs(self, context, skip_context_errors=False, **kwargs):
        parent = self.get_parent()
        if parent:
            try:
                if not parent.makedirs(context, skip_context_errors=False, **kwargs):
                    return False
            except PathContextError:
                if skip_context_errors:
                    return False
        parts = list(zip(
                self.iter_path(context, solve=True, dirs_only=True,
                               skip_context_errors=skip_context_errors, full_path=True),
                self.get_permission_list(),
                self.get_group_list(),
                self.get_user_list()))
        parts_count = len(parts)
        for i, (path, perm, group, user) in enumerate(parts):
            # итерация по частям пути от начала к концу
            if not os.path.exists(path):
                # если путь еще не существует, то создаём его
                # permission
                perm = kwargs.get('default_permission') or perm
                if not perm:
                    perm = self.default_dir_permission
                # user
                user = user or kwargs.get('default_user') or self.default_user
                # group
                group = group or kwargs.get('default_group') or self.default_group
                if i == parts_count-1 and self.options.get('symlink_to'):
                    # если это последняя часть пути и есть опция линковки, то делаем линк
                    link_source = self.expand_variables(self.options.get('symlink_to'), context)
                    if not os.path.exists(link_source):
                        raise IOError('Source path for link not exists: {}'.format(link_source))
                    os.symlink(link_source, path)
                else:
                    os.makedirs(path)
                    chmod(path, perm)
                    chown(path, user, group)
                logger.info('Make {}: {}'.format(self.name, path))
            elif i == parts_count-1 and self.options.get('symlink_to'):
                # если путь уже существует
                if not os.path.islink(path):
                    # и это не линк, то выбрасываем ошибку
                    raise IOError('Path for symlink already exists and it is not a symlink: {}'.format(path))
                link_source = self.expand_variables(self.options.get('symlink_to'), context)
                real_path = os.readlink(path)
                if real_path != link_source:
                    raise IOError('Linked path {} referenced to different source: {}, correct source: {}'.format(
                        path, real_path, link_source))
        return True

    def remove_empty_dirs(self, context):
        raise NotImplementedError

    # attributes

    def update_attributes(self, context, **kwargs):
        self.update_permissions(context, **kwargs)
        self.update_owner(context, **kwargs)

    def update_permissions(self, context, skip_context_errors=False, parents=False,
                           skip_non_exists=False, **kwargs):
        if parents:
            parent = self.get_parent()
            if parent:
                parent.update_permissions(context, skip_context_errors, parents, skip_non_exists, **kwargs)

        for path, perm in zip(self.iter_path(context, dirs_only=False, skip_context_errors=True, full_path=True),
                              self.get_permission_list(**kwargs)):
            if skip_non_exists and not os.path.exists(path):
                continue
            perm = perm or kwargs.get('default_permission') or (
                self.default_dir_permission if not os.path.splitext(path)[1] else self.default_file_permission)
            chmod(path, perm)

    def update_owner(self, context, skip_context_errors=False,
                     parents=False, skip_non_exists=False, **kwargs):
        if parents:
            parent = self.get_parent()
            if parent:
                parent.update_owner(context, skip_context_errors, parents, skip_non_exists)

        for path, user, group in zip(self.iter_path(context, dirs_only=False, skip_context_errors=True, full_path=True),
                                     self.get_user_list(**kwargs),
                                     self.get_group_list(**kwargs)):
            # user
            user = user or kwargs.get('default_user') or self.default_user
            # group
            group = group or kwargs.get('default_group') or self.default_group
            os.makedirs(path)
            chown(path, user, group)

    # utils

    def _get_option_list_by_value_name(self, value, default_value_key=None, default_value=None, **kwargs):
        default_value = default_value or (self.kwargs.get(default_value_key) if default_value_key else None)
        list_length = len(self.get_parts())
        value_list = self._get_list(self.options.get(value))
        value_list = [x if x is not None else default_value for x in value_list]
        if len(value_list) < list_length:
            value_list.extend([default_value]*(list_length-list_length))
        return [self.expand_variables(x, kwargs) if x else x for x in value_list]

    def _get_list(self, values, default=None):
        list_length = len(self.get_parts())
        if not isinstance(values, (list, tuple)):
            values = [values]*list_length
        values = [x if x is not None else default for x in values]
        return values

    def _valid_mode(self, value):
        if value is None:
            return None
        if isinstance(value, int):
            return oct(value)
        if isinstance(value, bytes):
            value = value.decode()
        if isinstance(value, string_types):
            if value.isdigit():
                # '0755'
                return oct(int('0o%s' % value, 8))
            elif re.match(r"^\do\d+$", value):
                # '0o755'
                return oct(int(value, 8))
        raise ValueError('Wrong mode: {} ({})'.format(value, type(value)))


def chown(path, user, group):
    if os.name == 'nt':
        raise OSError('Not implemented for Windows OS')
    # TODO: implement for windows
    import pwd, grp
    uid = pwd.getpwnam(user).pw_uid
    gid = grp.getgrnam(group).gr_gid
    try:
        os.chown(path, uid, gid)
    except Exception as e:
        raise type(e)("%s %s:%s (%s:%s)" % (e, user, group, uid, gid))


def chmod(path, mode):
    if os.name == 'nt':
        raise OSError('Not implemented for Windows OS')
    # TODO: implement for windows
    if isinstance(mode, string_types):
        mode = int(mode, 8)
    try:
        os.chmod(path, mode)
    except Exception as e:
        raise type(e)("%s %s" % (e, mode))


class CustomFormatString(str):
    """
    Extended string with advanced formatting.
    You can use this class as generic string object
    You can set multiple methods using character |
    Define arguments like in usual code

    >>> CustomFormatString('NAME_{value()|upper()}').format(value='e01s03')
    >>> 'NAME_E01S03'
    Multiple methods
    >>> CustomFormatString('name_{value|lower()|strip()}').format(value=' E01S03  ')
    >>> 'name_e01s03'
    Methods with arguments
    >>> CustomFormatString('{value|strip()|center(10, "-")}').format(value=' E01S03  ')
    >>> '--E01S03--'

    """
    sep = '|'

    def format(self, *args, **kwargs):
        context = copy.deepcopy(kwargs)
        variables = re.findall(r"({([\w\d_:]+)([%s\w]+\(.*?\))?})" % self.sep, self)
        for full_pat, var, expr in variables:
            var_name = var.split(':')[0].split(self.sep)[0]
            if context.get(var_name) == '*':
                self = CustomFormatString(str.replace(self, full_pat, '*'))
            if self.sep in expr:
                methods = expr.split(self.sep)
                _self = CustomFormatString(str.replace(self, full_pat, '{%s}' % var))
                val = context.get(var.split(':')[0])
                if not val:
                    raise ValueError('No value {} in {}'.format(var, context.keys()))
                if val == '*':
                    continue
                for m in methods:
                    if not m:
                        continue
                    expression_to_eval = 'val.%s' % m
                    # print(expression_to_eval)
                    val = eval(expression_to_eval)
                context[var] = val
                self = _self
        return str.format(self, **context)


class CustomException(Exception):
    msg = ''

    def __init__(self, *args, **kwargs):
        if not args:
            super(CustomException, self).__init__(*args)
        else:
            super(CustomException, self).__init__("{} {}".format(self.msg, args[0]).strip())


class PathNameError(CustomException):
    msg = 'Path name error'


class MultiplePatternMatchError(CustomException):
    msg = 'Multiple pattern match'


class NoPatternMatchError(CustomException):
    msg = 'No patterns names match'


class PathContextError(CustomException):
    msg = 'Wrong context for pattern'
