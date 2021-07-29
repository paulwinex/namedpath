# coding=utf-8
from __future__ import print_function, absolute_import
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

    def __init__(self, root_path, path_list):
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
            self._scope[path_name] = PNPath(path_name, options, self._scope)

    def get_path(self, name, context, create=False):
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
        if create and not exists(path):
            ctl.makedirs()
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

    def check_paths_attributes(self, fix=False):
        """
        Recursive searching and checking all of existing paths and fix them attributes
        """
        raise NotImplementedError


class PNPath(object):
    """Class provide logic of one single named path"""
    default_chmod = 0o755

    def __init__(self, name, options, scope, **kwargs):
        self.name = name
        self.options = options
        self._scope = scope
        self.kwargs = kwargs

    def __str__(self):
        return self.path

    def __repr__(self):
        return '<FSPath %s>' % self.path

    @property
    def path(self):
        """
        Raw path

        Returns
        -------
        str
        """
        return self.options['path']

    def solve(self, context):
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

    def expand_variables(self, text, variables):
        """
        Resolve variables in pattern

        Parameters
        ----------
        text: str
        variables: dict

        Returns
        -------
        str
        """
        ctx = copy.deepcopy(variables)
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
        return self.path.split(']', 1)[-1].lstrip('\\/')

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

    @property
    def chmod(self):
        """chmod parameter"""
        return self.options.get('chmod', self.default_chmod)

    @property
    def chown(self):
        """chown parameter"""
        return self.options.get('chown', [])

    @property
    def groups(self):
        """groups parameter"""
        return self.options.get('chmod', [])

    def makedirs(self, *args):
        """Create dirs"""


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

