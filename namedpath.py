# coding=utf-8
from __future__ import print_function, absolute_import

import os.path
from os.path import join, normpath, exists, abspath, expanduser, expandvars
import copy
import logging
import re
import sys

logger = logging.getLogger(__name__)

if sys.version_info.major > 2:
    unicode = type


class PNTree(object):
    """
    Class provide you to control folder structure paths
    """

    def __init__(self, root_path, path_list, context=None, **kwargs):
        self.kwargs = kwargs
        self.context = context
        self._root_path = abspath(expandvars(expanduser(root_path)))
        self._scope = {}
        self._init_scope(path_list)

    def __str__(self):
        return self.path

    def __repr__(self):
        return '<FSTree "{}">'.format(self.path)

    @property
    def path(self):
        """
        Root path of tree

        Returns
        -------
        str
        """
        return self._root_path

    def _init_scope(self, path_list):
        """Init all paths instances"""
        for path_name, options in path_list.items():
            if isinstance(options, str):
                options = dict(path=options)
            self._scope[path_name] = PNPath(path_name, options, self._scope, context=self.context, **self.kwargs)

    def get_path(self, name, context=None, create=False):
        """
        Get full path by name and context

        Parameters
        ----------
        name: str
            Path name
        context: dict
            Variables
        create: bool
            Create path now if not exists

        Returns
        -------
        str
        """
        ctl = self.get_path_instance(name)    # type: PNPath
        path = normpath(join(self.path, ctl.solve(context).lstrip('\\/')))
        if create and not exists(path) and not os.path.splitext(path)[1]:
            os.makedirs(path)
        return path

    def iter_path(self, name, context=None):
        ctl = self.get_path_instance(name)    # type: PNPath
        for part in ctl.iter_parts(context):
            yield os.path.join(self.path, part)

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
        return self.get_path_instance(name).get_full_path()

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
        Get PNPath instance by name

        Parameters
        ----------
        name: str

        Returns
        -------
        PNPath
        """
        try:
            return self._scope[name]
        except KeyError:
            raise PathNameError('Pattern named {} not found'.format(name))

    def get_path_names(self):
        """
        List of all pattern names in current tree

        Returns
        -------
        tuple
        """
        return tuple(self._scope.keys())

    def parse(self, path, with_variables=False):
        """
        Reverse existing path to a pattern name

        Parameters
        ----------
        path: str
        with_variables: bool

        Returns
        -------
        str or list
        """
        match_names = []
        for name, p in self._scope.items():  # type: PNPath
            pattern = p.as_regex(self.path)
            m = re.match(pattern, path, re.IGNORECASE)
            if m:
                match_names.append((name, m.groupdict()))
        if len(match_names) > 1:
            raise MultiplePatternMatchError(', '.join([x[0] for x in match_names]))
        if not match_names:
            raise NoPatternMatchError
        if with_variables:
            return match_names[0]
        else:
            return match_names[0][0]

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
                print(str(e))
                result['errors'][name] = 'Error: '+str(e)
            except MultiplePatternMatchError as e:
                print(str(e))
                result['errors'][name] = 'Error: '+str(e)
            else:
                if parsed_name != name:
                    result['errors'][name] = 'Generated and parsed names not match: {} -> {}'.format(name, parsed_name)
                else:
                    result['success'].append(name)
        print('Total patterns:', len(self._scope))
        print('Success parsing:', len(result['success']))
        print('Errors:', len(result['errors']))
        return result

    def transfer_to(self, other_tree, names_map=None, move=False):
        """
        Move files from one tree to other.
        All names must be matched or have rename map.

        Parameters
        ----------
        other_tree: PNTree
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

    def check_paths_attributes(self, *names, fix=False):
        """
        Recursive searching and checking all of existing paths and fix them attributes
        """
        raise NotImplementedError

    def makedirs(self, *names, context=None):
        """Create dirs"""

    def update_attributes(self, *names, **kwargs):
        if os.name == 'nt':
            raise NotImplementedError('Change attributes on Windows not supported yet')
        names = names or self.get_path_names()
        for name in names:
            ok = True
            try:
                self.update_path_chown(name, **kwargs)
            except Exception as e:
                print(name, e)
                ok = False
            try:
                self.update_path_chmod(name, **kwargs)
            except Exception as e:
                print(name, e)
                ok = False
            if ok:
                print(name, 'OK')

    def update_path_chown(self, name, **kwargs):
        if os.name == 'nt':
            raise NotImplementedError('Change owner on Windows not supported yet')
        import pwd
        import grp

        path_ctl = self.get_path_instance(name)
        groups, users = path_ctl.get_group_list(**kwargs), path_ctl.get_user_list(**kwargs)
        if len(users) != len(groups):
            raise ValueError('Different length of parameters: {} and {}'.format(users, groups))
        for user, group, rel_path in zip(users, groups, path_ctl.iter_parts(kwargs)):
            path = os.path.normpath(os.path.join(self.path, rel_path))
            if os.path.exists(path):
                uid = pwd.getpwnam(user).pw_uid
                gid = grp.getgrnam(group).gr_gid
                os.chown(path, uid, gid)
            else:
                logger.warning('Path not exists: {}'.format(path))

    def update_path_chmod(self, name, **kwargs):
        if os.name == 'nt':
            raise NotImplementedError('Change mod on Windows not supported yet')
        path_ctl = self.get_path_instance(name)
        mod_list = path_ctl.get_chmod_list()
        for mod, rel_path in zip(mod_list, path_ctl.iter_parts(kwargs)):
            path = os.path.normpath(os.path.join(self.path, rel_path))
            if os.path.exists(path):
                os.chmod(path, mod)
            else:
                logger.warning('Path not exists: {}'.format(path))


class PNPath(object):
    """Class provide logic of one single named path"""
    default_dir_chmod = 0o755
    default_file_chmod = 0o644

    def __init__(self, name, options, scope, context=None, **kwargs):
        self.name = name
        self.options = options
        self._scope = scope
        self.kwargs = kwargs
        self.context = context or {}

    def __str__(self):
        return self.path

    def __repr__(self):
        return '<FSPath %s>' % self.path

    def get_context(self, context=None):
        ctx = copy.deepcopy(self.context)
        ctx.update(context or {})
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

    def solve(self, context=None):
        """
        Resolve path from pattern with context to relative path

        Parameters
        ----------
        context: dict

        Returns
        -------
        str
        """
        path = self.get_full_path()
        return self.expand_variables(path, context)

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
        for k, v in self.options.get('defaults', {}).items():
            ctx.setdefault(k, v)
        return CustomFormatString(text).format(**{k.upper(): v for k, v in ctx.items()})

    def get_full_path(self):
        """
        Full path include parent patterns

        Returns
        -------
        str
        """
        par = self.get_parent()
        if par:
            return normpath(join(
                par.get_full_path(),
                self.relative())
            )
        else:
            return self.path

    def relative(self):
        """
        Relative path without parent pattern

        Returns
        -------
        str
        """
        return normpath(self.path.split(']', 1)[-1].lstrip('\\/'))

    def variables(self):
        """
        Extract variables names from pattern

        Returns
        -------
        list
        """
        variables = []
        for val in re.findall(r"{(.*?)}", self.get_full_path()):
            variables.append(val.split(':')[0])
        return variables

    def get_parent(self):
        """
        Get controller of parent pattern

        Returns
        -------
        PNPath
        """
        match = re.search(r"^\[(\w+)]/?(.*)", self.path)
        if match:
            try:
                return self._scope[match.group(1)]
            except KeyError:
                raise PathNameError

    def as_pattern(self, prefix=None):
        """
        Convert pattern to glob-pattern

        Parameters
        ----------
        prefix: str
            Root path

        Returns
        -------
        str
        """
        path = self.get_full_path()
        if prefix:
            path = normpath(join(prefix, path.lstrip('\\/')))
        return re.sub(r"{.*?}", '*', path)

    def as_regex(self, prefix=None, named_values=True):
        """
        Convert pattern to regex

        Parameters
        ----------
        prefix: str
            Root path
        named_values: bool
            Make named groups in regex

        Returns
        -------
        str
        """
        # simple_pattern = r'[\w\d\s:|"\'-]+'
        simple_pattern = r'[^\/\\]+'
        # named_pattern = r'(?P<%s>[\w\d\s:|"\'-]+)'
        named_pattern = r'(?P<%s>[^\/\\]+)'
        path = self.get_full_path()
        if prefix:
            path = normpath(join(prefix, path.lstrip('\\/')))

        names = []

        def get_subpattern(match):
            v = match.group(0)
            name = v.strip('{}').split(':')[0].split('|')[0].lower()
            if name in names:
                return simple_pattern
            names.append(name)
            if named_values:
                return named_pattern % name
            else:
                return simple_pattern
        pattern = re.sub(r"{.*?}", get_subpattern, path.replace('\\', '\\\\'))
        pattern = '^%s$' % pattern
        return pattern

    def get_parts(self):
        return self.relative().split(os.path.sep)

    def iter_parts(self, context=None):
        path = os.path.normpath(self.expand_variables(self.relative(), self.get_context(context)))
        par = self.get_parent()
        par_path = par.solve(self.get_context(context)) if par else ''
        tail = ''
        for part in path.split(os.path.sep):
            tail = os.path.join(tail, part)
            yield os.path.join(par_path, tail)

    def get_chmod_list(self):
        """chmod parameter"""
        mode_list = self._get_list(self.options.get('chmod'))
        mode_list = [self._valid_mode(x) for x in mode_list]
        return mode_list

    def get_group_list(self, default_group=None, **kwargs):
        return self.get_list_by_value_name('groups', 'default_group', default_group, **kwargs)

    def get_user_list(self, default_user=None, **kwargs):
        return self.get_list_by_value_name('users', 'default_user', default_user, **kwargs)

    def get_list_by_value_name(self, value, default_value_key=None, default_value=None, **kwargs):
        default_value = default_value or (self.kwargs.get(default_value_key) if default_value_key else None)
        list_length = len(self.get_parts())
        value_list = self._get_list(self.options.get(value))
        value_list = [x if x is not None else default_value for x in value_list]
        if len(value_list) < list_length:
            value_list.extend([default_value]*(list_length-list_length))
        return [self.expand_variables(x, kwargs) for x in value_list]

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
        if isinstance(value, str):
            if value.isdigit():
                # '0755'
                return oct(int('0o%s' % value, 8))
            elif re.match(r"^\do\d+$", value):
                # '0o755'
                return oct(int(value, 8))
        raise ValueError('Wrong mode: {}'.format(value))


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
            if self.sep in expr:
                methods = expr.split(self.sep)
                _self = CustomFormatString(str.replace(self, full_pat, '{%s}' % var))
                val = context.get(var.split(':')[0])
                if not val:
                    raise ValueError('No value {} in {}'.format(var, context.keys()))
                for m in methods:
                    if not m:
                        continue
                    expression_to_eval = 'val.%s' % m
                    print(expression_to_eval)
                    val = eval(expression_to_eval)
                context[var] = val
                self = _self
        return str.format(self, **context)


class CustomException(Exception):
    msg = ''

    def __init__(self, *args, **kwargs):
        if args:
            super(CustomException, self).__init__(*args)
        else:
            super(CustomException, self).__init__(self.msg)


class PathNameError(CustomException):
    msg = 'Path name error'


class MultiplePatternMatchError(CustomException):
    msg = 'Multiple pattern match'


class NoPatternMatchError(CustomException):
    msg = 'No patterns names match'

