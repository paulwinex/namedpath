# coding=utf-8
from __future__ import print_function, absolute_import
import os.path
import glob
from os.path import join, normpath, exists, abspath, expanduser, expandvars
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

    def __init__(self, root_path, path_list, **kwargs):
        self.kwargs = kwargs
        self._root_path = abspath(expandvars(expanduser(root_path)))
        self._scope = {}
        self._init_scope(path_list)

    def __str__(self):
        return self.path

    def __repr__(self):
        return '<NamedPathTree "{}">'.format(self.path)

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

    def _init_scope(self, path_list):
        """Init all paths instances"""
        for path_name, options in path_list.items():
            if isinstance(options, str):
                options = dict(path=options)
            path_name = path_name.upper()
            self._scope[path_name] = NamedPath(self.path, path_name, options, self._scope, **self.kwargs)

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
        Get PNPath instance by name

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
        return tuple(sorted(self._scope.keys()))

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
        for name, p in self._scope.items():  # type: NamedPath
            pattern = p.as_regex(self.path)
            m = re.match(pattern, path, re.IGNORECASE)
            if m:
                match_names.append((name, m.groupdict()))
        if len(match_names) > 1:
            raise MultiplePatternMatchError(', '.join([x[0] for x in match_names]))
        if not match_names:
            raise NoPatternMatchError(path)
        if with_variables:
            return match_names[0]
        else:
            return match_names[0][0]

    def filter_paths(self, root_path=None, name_in=None):
        pass

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

    def makedirs(self, root_path=None, names=None, context=None):
        """Create dirs"""
        names = names or self.get_path_names()
        paths = [self.get_path_instance(name) for name in names]
        if root_path:
            if root_path not in self.get_path_names():
                raise PathNameError
            paths = [path for path in paths if root_path in path.get_all_parent_names()]
        for path_ctl in paths:
            path_ctl.makedirs(context, skip_context_errors=True)


class NamedPath(object):
    """Class provide logic of one single named path"""
    _default_dir_permission = 0o755
    _default_file_permission = 0o644

    def __init__(self, base_dir, name, options, scope, **kwargs):
        self.name = name
        self.options = options
        self._scope = scope
        self.kwargs = kwargs
        self.base_dir = base_dir

    def __str__(self):
        return self.path

    def __repr__(self):
        return '<FSPath %s "%s">' % (self.name, self.path)

    def get_context(self, context=None):
        ctx = copy.deepcopy(context)
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

    def solve(self, context, skip_context_errors=False, relative=False):
        """
        Resolve path from pattern with context to relative path

        Parameters
        ----------
        context: dict
        skip_context_errors: bool
        relative: bool

        Returns
        -------
        str
        """
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
                    for part in parent.iter_path(context, solve=solve,
                                                 dirs_only=dirs_only,
                                                 full_path=full_path,
                                                 skip_context_errors=skip_context_errors,
                                                 include_parents=include_parents):
                        yield part
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
                variables = [val.split(':')[0].upper() for val in re.findall(r"{(.*?)}", part)]
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

    def get_pattern_variables(self):
        """
        Extract variables names from pattern

        Returns
        -------
        list
        """
        variables = []
        for val in re.findall(r"{(.*?)}", self.get_relative()):
            variables.append(val.split(':')[0])
        return variables

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
                raise PathNameError

    def get_all_parent_names(self):
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

    def as_glob(self, prefix=None):
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
        path = self.get_relative()
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
        path = self.get_relative()
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

    def makedirs(self, context, skip_context_errors=True, **kwargs):
        parent = self.get_parent()
        if parent:
            parent.makedirs(context, skip_context_errors)
        for path, perm, group, user in zip(
                self.iter_path(context, solve=True, dirs_only=True,
                               skip_context_errors=skip_context_errors, full_path=True),
                self.get_permission_list(),
                self.get_group_list(),
                self.get_user_list()):
            if not os.path.exists(path):
                # permission
                perm = kwargs.get('default_permission') or perm
                if not perm:
                    perm = self.default_dir_permission
                # user
                user = user or kwargs.get('default_user') or self.default_user
                # group
                group = group or kwargs.get('default_group') or self.default_group
                os.makedirs(path)
                chmod(path, perm)
                chown(path, user, group)

    def remove_empty_dirs(self, context):
        pass

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
    import pwd, grp
    uid = pwd.getpwnam(user).pw_uid
    gid = grp.getgrnam(group).gr_gid
    try:
        os.chown(path, uid, gid)
    except Exception as e:
        raise type(e)("%s %s:%s (%s:%s)" % (e, user, group, uid, gid))


def chmod(path, mode):
    if isinstance(mode, basestring):
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
            super(CustomException, self).__init__("{} {}".format(self.msg, args[0]).strip())


class PathNameError(CustomException):
    msg = 'Path name error'


class MultiplePatternMatchError(CustomException):
    msg = 'Multiple pattern match'


class NoPatternMatchError(CustomException):
    msg = 'No patterns names match'


class PathContextError(CustomException):
    msg = 'Wrong context for pattern'
